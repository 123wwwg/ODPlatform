#!/usr/bin/env python
# @FileName  : sinks.py
# @Project   : ODPlatform
# @Function  : 推理结果输出适配器 (OutputSink 抽象 + LocalFileSink + NullSink)
"""推理结果输出适配器.

  - OutputSink     : 抽象基类 (open/write/close)
  - LocalFileSink  : 本地 mp4 / jpg (CLI 默认行为)
  - NullSink       : 不写任何东西 (web 推流 / 只跑统计 / --no-save)

实现纪律: write() 内部 try/except(单帧失败 warn + 跳过), close() 幂等.
"""
from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from pathlib import Path

import numpy as np

from od_platform.frame_source import SourceType

logger = logging.getLogger(__name__)


class OutputSink(ABC):
    """推理结果输出适配器. 生命周期: open() → write() × N → close()."""

    @abstractmethod
    def open(self, output_dir: Path, source_type: SourceType) -> None:
        """初始化. 由 ThreadedPipeline 在首批帧到达后调用."""

    @abstractmethod
    def write(self, frame, annotated: np.ndarray) -> None:
        """写一帧画好的图."""

    @abstractmethod
    def close(self) -> None:
        """收尾. 必须幂等."""


class LocalFileSink(OutputSink):
    """本地文件 sink — 视频源写 mp4, 图片源写 jpg."""

    def __init__(self) -> None:
        self.output_dir: Path | None = None
        self._is_stream: bool = False
        self._video = None      # cv2.VideoWriter, lazy
        self._count: int = 0

    def open(self, output_dir: Path, source_type: SourceType) -> None:
        self.output_dir = output_dir
        self._is_stream = source_type in (SourceType.VIDEO, SourceType.CAMERA)

    def write(self, frame, annotated) -> None:
        import cv2
        try:
            if self._is_stream:
                if self._video is None:
                    h, w = annotated.shape[:2]
                    fps = float(frame.info.fps) if getattr(frame.info, "fps", None) else 30.0
                    out = self.output_dir / "output.mp4"
                    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
                    self._video = cv2.VideoWriter(str(out), fourcc, fps, (w, h))
                self._video.write(annotated)
            else:
                from od_platform.common.image_io import imwrite
                fname = frame.info.filename or f"frame_{frame.info.frame_index:06d}"
                imwrite(self.output_dir / f"{Path(fname).stem}.jpg", annotated)
            self._count += 1
        except Exception as e:      # noqa: BLE001 - 单帧写失败不该毁掉整条流水线
            logger.warning(f"LocalFileSink.write 失败, 跳过: {e}")

    def close(self) -> None:
        if self._video is not None:
            try:
                self._video.release()
            except Exception as e:      # noqa: BLE001
                logger.warning(f"LocalFileSink.close release 失败 (已吞): {e}")
            finally:
                self._video = None


class NullSink(OutputSink):
    """什么也不写(web 推流 / desktop / 基准测试 / --no-save)."""

    def open(self, output_dir: Path, source_type: SourceType) -> None:
        pass

    def write(self, frame, annotated) -> None:
        pass

    def close(self) -> None:
        pass
