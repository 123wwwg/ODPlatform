#!/usr/bin/env python
# @FileName  : video.py
# @Project   : ODPlatform
# @Function  : 视频文件 / 网络流源
"""视频源: 本地文件或 rtsp/rtmp/http 流。"""
from __future__ import annotations

import logging
import time
from pathlib import Path

from od_platform.frame_source.base import FrameSource
from od_platform.frame_source.types import Frame, FrameInfo, SourceType

logger = logging.getLogger(__name__)

_LIVE_PREFIXES = ("rtsp://", "rtmp://", "http://", "https://", "udp://", "tcp://")


class VideoSource(FrameSource):
    """视频文件 / 网络流。stride>1 时跳帧(只影响吐出的帧, 不改变播放速度)。"""

    def __init__(self, source: str | Path, *, stride: int = 1) -> None:
        super().__init__()
        import cv2

        self._src = str(source)
        self._stride = max(1, int(stride))
        self._live = self._src.lower().startswith(_LIVE_PREFIXES)
        self._cap = cv2.VideoCapture(self._src)
        if not self._cap.isOpened():
            raise RuntimeError(f"视频源打不开: {self._src}")
        self._fps = self._cap.get(cv2.CAP_PROP_FPS) or None
        total = int(self._cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
        self._total = total if total > 0 else None
        self._idx = 0

    def get_source_type(self) -> SourceType:
        return SourceType.VIDEO

    @property
    def is_live(self) -> bool:
        return self._live

    def read(self) -> Frame | None:
        if self._released:
            return None
        # 跳帧: 只在需要时 grab, 减少解码开销
        for _ in range(self._stride - 1):
            if not self._cap.grab():
                return None
        ok, image = self._cap.read()
        if not ok or image is None:
            return None
        index = self._idx
        self._idx += 1
        name = Path(self._src).name if not self._live else self._src
        return Frame(
            image=image,
            info=FrameInfo(
                frame_index=index, filename=name, fps=self._fps,
                source_type=SourceType.VIDEO, timestamp=time.perf_counter(),
                total_frames=self._total,
            ),
        )

    def release(self) -> None:
        if self._released:
            return
        self._released = True
        try:
            self._cap.release()
        except Exception as e:      # noqa: BLE001
            logger.warning("视频源释放失败 (已吞): %s", e)
