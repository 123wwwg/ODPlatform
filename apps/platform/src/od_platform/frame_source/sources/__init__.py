"""内置帧源(import 即可用)."""
from od_platform.frame_source.sources.camera import CameraSource
from od_platform.frame_source.sources.image import ImageSource
from od_platform.frame_source.sources.video import VideoSource

__all__ = ["ImageSource", "VideoSource", "CameraSource"]
