#!/usr/bin/env python
# @FileName  : camera.py
# @Project   : ODPlatform
# @Function  : 摄像头源(跨平台后端协商)
"""摄像头源: 按编号打开, 尽量按配置协商分辨率/帧率, 失败就退回默认值。"""
from __future__ import annotations

import logging
import time

from od_platform.frame_source.base import FrameSource
from od_platform.frame_source.config import CameraConfig
from od_platform.frame_source.types import Frame, FrameInfo, SourceType

logger = logging.getLogger(__name__)

_BACKENDS = {
    "dshow": "CAP_DSHOW",          # Windows
    "v4l2": "CAP_V4L2",            # Linux
    "avfoundation": "CAP_AVFOUNDATION",   # macOS
    "auto": None,
}


class CameraSource(FrameSource):
    """摄像头。配置协商失败不是错误 —— 用驱动给的默认参数继续跑。"""

    def __init__(self, config: CameraConfig | int, *, stride: int = 1) -> None:
        super().__init__()
        import cv2

        self._cfg = config if isinstance(config, CameraConfig) else CameraConfig(camera_id=config)
        self._stride = max(1, int(stride))

        backend_attr = _BACKENDS.get(str(self._cfg.backend).lower(), None)
        api = getattr(cv2, backend_attr) if backend_attr else cv2.CAP_ANY
        self._cap = cv2.VideoCapture(self._cfg.camera_id, api)
        if not self._cap.isOpened():
            raise RuntimeError(
                f"摄像头打不开: camera_id={self._cfg.camera_id} backend={self._cfg.backend}"
            )

        self._cap.set(cv2.CAP_PROP_FRAME_WIDTH, self._cfg.width)
        self._cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self._cfg.height)
        self._cap.set(cv2.CAP_PROP_FPS, self._cfg.fps)
        if self._cfg.buffer_size:
            self._cap.set(cv2.CAP_PROP_BUFFERSIZE, self._cfg.buffer_size)

        real_fps = self._cap.get(cv2.CAP_PROP_FPS) or None
        logger.info(
            "摄像头已打开: id=%s 后端=%s 实际=%dx%d@%s",
            self._cfg.camera_id, self._cfg.backend,
            int(self._cap.get(cv2.CAP_PROP_FRAME_WIDTH)),
            int(self._cap.get(cv2.CAP_PROP_FRAME_HEIGHT)), real_fps,
        )
        self._fps = real_fps
        self._idx = 0

    def get_source_type(self) -> SourceType:
        return SourceType.CAMERA

    @property
    def is_live(self) -> bool:
        return True

    def read(self) -> Frame | None:
        if self._released:
            return None
        for _ in range(self._stride - 1):
            self._cap.grab()
        ok, image = self._cap.read()
        if not ok or image is None:
            logger.warning("摄像头读帧失败(设备断开?), 视为结束")
            return None
        index = self._idx
        self._idx += 1
        return Frame(
            image=image,
            info=FrameInfo(
                frame_index=index, filename=f"camera_{self._cfg.camera_id}",
                fps=self._fps, source_type=SourceType.CAMERA,
                timestamp=time.perf_counter(),
            ),
        )

    def release(self) -> None:
        if self._released:
            return
        self._released = True
        try:
            self._cap.release()
        except Exception as e:      # noqa: BLE001
            logger.warning("摄像头释放失败 (已吞): %s", e)
