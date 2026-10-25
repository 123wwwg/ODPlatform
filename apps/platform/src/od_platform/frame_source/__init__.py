#!/usr/bin/env python
# @FileName  : __init__.py
# @Project   : ODPlatform
# @Function  : frame_source 对外面板
"""可插拔多模态帧输入源.

    from od_platform.frame_source import create_frame_source, SourceType

    with create_frame_source("data/demo/video.mp4") as src:
        for frame in src:            # Frame(image, info)
            ...
"""
from od_platform.frame_source.base import FrameSource
from od_platform.frame_source.config import CameraConfig
from od_platform.frame_source.factory import create_frame_source
from od_platform.frame_source.sources import CameraSource, ImageSource, VideoSource
from od_platform.frame_source.types import IMAGE_EXTENSIONS, Frame, FrameInfo, SourceType

__all__ = [
    "create_frame_source",
    "FrameSource",
    "ImageSource",
    "VideoSource",
    "CameraSource",
    "CameraConfig",
    "SourceType",
    "Frame",
    "FrameInfo",
    "IMAGE_EXTENSIONS",
]
