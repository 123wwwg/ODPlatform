#!/usr/bin/env python
"""frame_source 帧源契约测试(图片/视频/摄像头派发)."""
from __future__ import annotations

import numpy as np
import pytest

from od_platform.common.image_io import imwrite
from od_platform.frame_source import (
    IMAGE_EXTENSIONS,
    CameraConfig,
    Frame,
    ImageSource,
    SourceType,
    create_frame_source,
)


def _make_images(directory, n: int = 3):
    directory.mkdir(parents=True, exist_ok=True)
    for i in range(n):
        assert imwrite(directory / f"img_{i}.jpg",
                       np.full((32, 48, 3), 40 + i, np.uint8))
    return directory


class _FakeCap:
    """假 VideoCapture: 只够让 VideoSource/CameraSource 跑起来."""

    def __init__(self, *args, **kwargs):
        self._left = 2
        self.released = False

    def isOpened(self):
        return True

    def set(self, prop, value):
        return True

    def get(self, prop):
        import cv2
        if prop == cv2.CAP_PROP_FPS:
            return 25.0
        if prop == cv2.CAP_PROP_FRAME_COUNT:
            return 2
        if prop in (cv2.CAP_PROP_FRAME_WIDTH, cv2.CAP_PROP_FRAME_HEIGHT):
            return 640
        return 0

    def grab(self):
        return self._left > 0

    def read(self):
        if self._left <= 0:
            return False, None
        self._left -= 1
        return True, np.zeros((16, 24, 3), np.uint8)

    def release(self):
        self.released = True


# ============================================================
# 工厂派发
# ============================================================

def test_directory_dispatches_to_image(tmp_path):
    src = create_frame_source(_make_images(tmp_path / "imgs"))
    assert isinstance(src, ImageSource)
    assert src.get_source_type() is SourceType.IMAGE


def test_image_file_dispatches_to_image(tmp_path):
    d = _make_images(tmp_path / "imgs", n=1)
    src = create_frame_source(d / "img_0.jpg")
    assert isinstance(src, ImageSource)


def test_numeric_source_dispatches_to_camera(monkeypatch):
    import cv2
    monkeypatch.setattr(cv2, "VideoCapture", _FakeCap)
    src = create_frame_source("0")
    assert src.get_source_type() is SourceType.CAMERA
    assert src.is_live is True


def test_camera_config_dispatches_to_camera(monkeypatch):
    import cv2
    monkeypatch.setattr(cv2, "VideoCapture", _FakeCap)
    src = create_frame_source(CameraConfig(camera_id=2, width=640, height=480, fps=15))
    assert src.get_source_type() is SourceType.CAMERA


def test_video_path_dispatches_to_video(monkeypatch):
    import cv2
    monkeypatch.setattr(cv2, "VideoCapture", _FakeCap)
    src = create_frame_source("demo.mp4")
    assert src.get_source_type() is SourceType.VIDEO
    src.release()


# ============================================================
# 图片源行为
# ============================================================

def test_image_source_iterates_in_name_order(tmp_path):
    d = _make_images(tmp_path / "imgs", n=3)
    frames = list(create_frame_source(d))
    assert len(frames) == 3
    assert [f.info.filename for f in frames] == ["img_0.jpg", "img_1.jpg", "img_2.jpg"]
    assert all(isinstance(f, Frame) for f in frames)
    assert frames[0].image.shape == (32, 48, 3)
    assert frames[0].info.frame_index == 0
    assert frames[0].info.total_frames == 3
    assert frames[0].info.source_type is SourceType.IMAGE


def test_image_source_stride(tmp_path):
    d = _make_images(tmp_path / "imgs", n=4)
    frames = list(create_frame_source(d, stride=2))
    assert [f.info.filename for f in frames] == ["img_0.jpg", "img_2.jpg"]
    assert len(create_frame_source(d, stride=2)) == 2


def test_empty_directory_raises(tmp_path):
    empty = tmp_path / "empty"
    empty.mkdir()
    with pytest.raises(FileNotFoundError, match="没有图片文件"):
        create_frame_source(empty)


def test_missing_path_raises(tmp_path):
    with pytest.raises(FileNotFoundError):
        create_frame_source(tmp_path / "nope")


def test_release_is_idempotent(tmp_path):
    src = create_frame_source(_make_images(tmp_path / "imgs", n=1))
    list(src)
    src.release()
    src.release()          # 多次释放不炸
    assert src.read() is None


def test_context_manager_releases(tmp_path):
    d = _make_images(tmp_path / "imgs", n=1)
    with create_frame_source(d) as src:
        assert next(iter(src)).info.filename == "img_0.jpg"


# ============================================================
# 视频 / 摄像头(假后端)
# ============================================================

def test_video_source_reads_and_reports_metadata(monkeypatch):
    import cv2
    monkeypatch.setattr(cv2, "VideoCapture", _FakeCap)
    src = create_frame_source("demo.mp4")
    frames = list(src)
    assert len(frames) == 2
    assert frames[0].info.fps == 25.0
    assert frames[0].info.total_frames == 2
    assert frames[0].info.source_type is SourceType.VIDEO


def test_video_open_failure_raises(monkeypatch):
    import cv2

    class _Closed(_FakeCap):
        def isOpened(self):
            return False

    monkeypatch.setattr(cv2, "VideoCapture", _Closed)
    with pytest.raises(RuntimeError, match="视频源打不开"):
        create_frame_source("demo.mp4")


def test_rtsp_treated_as_video_and_live(monkeypatch):
    import cv2
    monkeypatch.setattr(cv2, "VideoCapture", _FakeCap)
    src = create_frame_source("rtsp://example.com/live")
    assert src.get_source_type() is SourceType.VIDEO
    assert src.is_live is True
    src.release()


# ============================================================
# CameraConfig 校验
# ============================================================

class TestCameraConfig:
    def test_defaults(self):
        c = CameraConfig()
        assert c.camera_id == 0 and c.width == 1280 and c.fps == 30
        assert c.backend == "auto"

    def test_extra_forbid(self):
        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            CameraConfig(resolution="1080p")      # 拼错的键

    def test_fps_range(self):
        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            CameraConfig(fps=0)

    def test_model_copy_injects_camera_id(self):
        cfg = CameraConfig(width=640)
        assert cfg.model_copy(update={"camera_id": 3}).camera_id == 3


def test_image_extensions_are_lowercase_suffix():
    assert all(ext.startswith(".") and ext.islower() for ext in IMAGE_EXTENSIONS)
    assert ".jpg" in IMAGE_EXTENSIONS and ".png" in IMAGE_EXTENSIONS
