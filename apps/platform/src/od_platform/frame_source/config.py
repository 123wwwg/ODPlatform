#!/usr/bin/env python
# @FileName  : config.py
# @Project   : ODPlatform
# @Function  : CameraConfig —— 摄像头参数(配置类型是派发轴)
"""摄像头配置.

extra='forbid': yaml 里拼错的键立刻报错, 而不是被静默忽略.
摄像头号是 dispatch 依据: 同一份配置 + 换 camera_id = 换设备.
"""
from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class CameraConfig(BaseModel):
    """摄像头(或 RTSP 流)的采集参数。"""

    model_config = ConfigDict(extra="forbid")

    camera_id: int = Field(default=0, ge=0, description="摄像头编号(0/1/2...)")
    width: int = Field(default=1280, ge=1, description="期望采集宽度")
    height: int = Field(default=720, ge=1, description="期望采集高度")
    fps: int = Field(default=30, ge=1, le=240, description="期望帧率")
    backend: str = Field(
        default="auto",
        description="采集后端: auto / dshow(Win) / v4l2(Linux) / avfoundation(Mac)",
    )
    auto_focus: bool | None = Field(default=None, description="是否自动对焦(None=不干预)")
    buffer_size: int | None = Field(default=None, ge=1, description="驱动内部缓冲帧数")
