#!/usr/bin/env python
# @FileName  : hooks.py
# @Project   : ODPlatform
# @Function  : 推理生命周期钩子 (InferHooks + FrameEvent + ProgressEvent)
"""推理生命周期回调.

  on_frame    : 每帧推理 + 绘制完成 (高频, renderer 线程)
  on_progress : 每 N 帧 (低频, 主线程)
  on_complete : 推理收尾 (1 次)
  on_error    : 异常发生 (0 或 1 次)

★ 核心纪律: 所有 fire_* 用 try/except 包住 —— 业务回调抛异常绝不允许炸掉 pipeline.
CLI 默认不传 hooks → 全空回调 → short-circuit 零开销, 行为与改造前一致.
"""
from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class FrameEvent:
    """每帧推理完后的事件数据(image/annotated 是视图, 异步处理需先 copy)."""
    frame_idx: int
    image: np.ndarray
    annotated: np.ndarray
    n_detections: int
    detections: list | None = None


@dataclass
class ProgressEvent:
    """周期性进度事件(每 progress_interval_frames 帧触发)."""
    frame_idx: int
    total_frames: int | None
    elapsed_sec: float
    fps_loop: float
    fps_infer: float
    detections_total: int


@dataclass
class InferHooks:
    """所有回调钩子. None 表示空回调."""

    on_frame: Callable[[FrameEvent], None] | None = None
    on_progress: Callable[[ProgressEvent], None] | None = None
    on_complete: Callable[[Any], None] | None = None
    on_error: Callable[[Exception], None] | None = None

    progress_interval_frames: int = 30

    # ---- 触发 helper: 全部 try/except 包住 ----
    def fire_frame(self, evt: FrameEvent) -> None:
        if self.on_frame is not None:
            try:
                self.on_frame(evt)
            except Exception as e:      # noqa: BLE001
                logger.warning(f"on_frame 回调异常 (已吞): {e}")

    def fire_progress(self, evt: ProgressEvent) -> None:
        if self.on_progress is not None:
            try:
                self.on_progress(evt)
            except Exception as e:      # noqa: BLE001
                logger.warning(f"on_progress 回调异常 (已吞): {e}")

    def fire_complete(self, result: Any) -> None:
        if self.on_complete is not None:
            try:
                self.on_complete(result)
            except Exception as e:      # noqa: BLE001
                logger.warning(f"on_complete 回调异常 (已吞): {e}")

    def fire_error(self, exc: Exception) -> None:
        if self.on_error is not None:
            try:
                self.on_error(exc)
            except Exception as e:      # noqa: BLE001
                logger.warning(f"on_error 回调异常 (已吞): {e}")
