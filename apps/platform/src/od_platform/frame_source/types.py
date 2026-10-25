#!/usr/bin/env python
# @FileName  : types.py
# @Project   : ODPlatform
# @Function  : 帧源公共类型 —— SourceType / FrameInfo / Frame
"""一帧长什么样 + 帧源类型枚举。所有源都吐同一种 Frame, 下游只认这一种。"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

import numpy as np


class SourceType(str, Enum):
    """帧源类型(派发轴)。"""
    IMAGE = "image"       # 单图 或 图片目录
    VIDEO = "video"       # 视频文件 / 网络流
    CAMERA = "camera"     # 摄像头(按编号)

    def __str__(self) -> str:      # 日志里直接读
        return self.value


# 判"这是不是图片"的唯一标准
IMAGE_EXTENSIONS: tuple[str, ...] = (
    ".jpg", ".jpeg", ".png", ".bmp", ".webp", ".tif", ".tiff",
)


@dataclass
class FrameInfo:
    """一帧的元数据(不含像素)。"""
    frame_index: int = 0                     # 0-based 帧序号
    filename: str = ""                       # 原始文件名(图片/视频帧)
    fps: float | None = None                 # 源帧率(摄像头/视频知道, 图片为 None)
    source_type: SourceType | None = None
    timestamp: float | None = None           # 采集时刻(time.perf_counter)
    total_frames: int | None = None          # 总帧数(视频知道, 摄像头 None)
    extra: dict[str, Any] = field(default_factory=dict)


@dataclass
class Frame:
    """一帧 = 像素 + 元数据。"""
    image: np.ndarray
    info: FrameInfo = field(default_factory=FrameInfo)

    @property
    def shape(self) -> tuple[int, ...]:
        return self.image.shape

    @property
    def filename(self) -> str:
        return self.info.filename
