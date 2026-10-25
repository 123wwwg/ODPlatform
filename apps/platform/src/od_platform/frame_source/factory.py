#!/usr/bin/env python
# @FileName  : factory.py
# @Project   : ODPlatform
# @Function  : create_frame_source —— str|CameraConfig → 具体帧源
"""工厂: 只做派发, 不含任何采集逻辑.

派发顺序(先具体后一般):
    CameraConfig        → 摄像头
    "0" / 纯数字         → 摄像头
    rtsp/rtmp/http(s)   → 视频(网络流)
    存在的目录/图片文件    → 图片(单图或目录)
    其它                 → 视频文件
"""
from __future__ import annotations

from pathlib import Path

from od_platform.frame_source.base import FrameSource
from od_platform.frame_source.config import CameraConfig
from od_platform.frame_source.sources.camera import CameraSource
from od_platform.frame_source.sources.image import ImageSource
from od_platform.frame_source.sources.video import VideoSource
from od_platform.frame_source.types import IMAGE_EXTENSIONS

_LIVE_PREFIXES = ("rtsp://", "rtmp://", "http://", "https://", "udp://", "tcp://")

# 视频文件后缀(决定"不存在的路径"该报哪种错)
_VIDEO_EXTENSIONS: tuple[str, ...] = (
    ".mp4", ".avi", ".mov", ".mkv", ".flv", ".wmv", ".m4v", ".ts", ".webm",
)


def create_frame_source(
    source: str | Path | CameraConfig,
    *,
    stride: int = 1,
) -> FrameSource:
    """按源的类型/形态造出对应帧源。"""
    if isinstance(source, CameraConfig):
        return CameraSource(source, stride=stride)

    text = str(source).strip()

    if text.isdigit():
        return CameraSource(CameraConfig(camera_id=int(text)), stride=stride)

    if text.lower().startswith(_LIVE_PREFIXES):
        return VideoSource(text, stride=stride)

    path = Path(text)
    if path.is_dir():
        return ImageSource(path, stride=stride)
    if path.suffix.lower() in IMAGE_EXTENSIONS:
        return ImageSource(path, stride=stride)

    # 显式视频后缀: 交给 VideoSource(它会给出"视频源打不开"的具体错误)
    if path.suffix.lower() in _VIDEO_EXTENSIONS:
        return VideoSource(path, stride=stride)

    # 既不是目录/图片/视频, 也不存在 → 直接说清"没有这个源"
    if not path.exists():
        raise FileNotFoundError(
            f"帧源不存在: {path}\n"
            f"支持: 图片/图片目录({', '.join(IMAGE_EXTENSIONS)}), "
            f"视频({', '.join(_VIDEO_EXTENSIONS)}), rtsp/rtmp 流, 摄像头号(0/1/...)"
        )

    return VideoSource(path, stride=stride)
