#!/usr/bin/env python
# -*- coding:utf-8 -*-
# @FileName  : __init__.py
# @Project   : ODPlatform
# @Function  : 帧源捕获 —— 图片/图片夹/视频/摄像头/RTSP 统一成"可迭代帧源"
"""帧源捕获子系统.

把不同输入源(图片 / 图片夹 / 视频文件 / 摄像头 / RTSP 流)统一成
一个【可迭代的上下文管理器】:

    with create_frame_source(source) as src:
        print(src.get_source_type())
        for frame in src:
            cv2.imshow("x", frame.image)      # frame.image: BGR ndarray
            print(frame.info.fps, frame.info.frame_index)

★ 设计契约 (D8 推理子系统依赖):
  - create_frame_source(source, *, stride=1)  工厂, source 是路径/数字/URL
  - 返回对象有 get_source_type() / __iter__ / __enter__ / __exit__
  - Frame.image   : BGR ndarray
  - Frame.info    : FrameInfo(fps, filename, frame_index, total_frames)
  - stride=N      : 每 N 帧取 1 帧 (跳帧)
  - 摄像头/RTSP   : latest 语义由上游(pipeline)决定, 这里只负责读出

★ 实现纪律:
  - cv2 延迟 import (不读帧的路径不吃重依赖)
  - __exit__ 保证释放 VideoCapture (不会泄露句柄)
  - 图片夹按文件名排序, 顺序稳定可复现
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterator, List, Optional, Union

from pydantic import BaseModel, ConfigDict, field_validator

from od_platform.common.constants import IMAGE_EXTENSIONS as _IMAGE_EXTENSIONS

logger = logging.getLogger(__name__)

# 对外暴露的图片扩展名(与 constants 同一份真相)
IMAGE_EXTENSIONS = _IMAGE_EXTENSIONS

# 摄像头后端(字符串枚举值, 给 CameraConfig.backend)
_BACKENDS = ("auto", "dshow", "v4l2", "avfoundation")


class CameraConfig(BaseModel):
    """摄像头采集参数. extra=forbid: 拼错的键名当场报错.

    backend: auto / dshow(Win) / v4l2(Linux) / avfoundation(Mac)
    buffer_size: 驱动内部缓冲, 越小延迟越低 (部分后端支持)
    """
    model_config = ConfigDict(extra="forbid")

    camera_id: int = 0
    width: int = 1280
    height: int = 720
    fps: int = 30
    backend: str = "auto"
    auto_focus: bool = False
    buffer_size: int = 1

    @field_validator("backend")
    @classmethod
    def _check_backend(cls, v: str) -> str:
        v = (v or "auto").lower()
        if v not in _BACKENDS:
            raise ValueError(f"backend 必须是 {_BACKENDS}, 收到 {v!r}")
        return v


class SourceType:
    """源类型枚举(类常量风格, 与课程文档一致)."""
    IMAGE = "image"            # 单张图片
    IMAGE_FOLDER = "image_folder"   # 图片目录
    VIDEO = "video"            # 视频文件
    CAMERA = "camera"          # 摄像头号 / RTSP 流


@dataclass
class FrameInfo:
    """单帧元数据."""
    fps: float = 0.0            # 视频/摄像头源的帧率, 图片 0
    filename: Optional[str] = None    # 图片文件名(图片源), 视频/摄像头 None
    frame_index: int = 0        # 帧序号 (从 0 开始)
    total_frames: Optional[int] = None  # 视频源总帧数, 摄像头/图片 None


@dataclass
class Frame:
    """一帧: 图像 + 元数据."""
    image: Any                     # BGR ndarray
    info: FrameInfo = field(default_factory=FrameInfo)


def _camera_backend_flag(backend: str) -> Any:
    """backend 字符串 → cv2.CAP_* 常量. auto → 0 (cv2.CAP_ANY)."""
    import cv2
    mapping = {
        "auto": cv2.CAP_ANY,
        "dshow": cv2.CAP_DSHOW,
        "v4l2": cv2.CAP_V4L2,
        "avfoundation": cv2.CAP_AVFOUNDATION,
    }
    return mapping.get(backend, cv2.CAP_ANY)


# ============================================================================
# 各源实现
# ============================================================================

class _ImageFolderSource:
    """图片目录源: 扫描目录内所有图片, 按文件名排序逐张读."""

    def __init__(self, directory: Path, *, stride: int):
        self.directory = directory
        self.stride = stride
        self._paths: List[Path] = []

    def get_source_type(self) -> str:
        return SourceType.IMAGE_FOLDER

    def __enter__(self) -> "_ImageFolderSource":
        self._paths = sorted(
            p for p in self.directory.iterdir()
            if p.suffix.lower() in IMAGE_EXTENSIONS and p.is_file()
        )
        if not self._paths:
            raise FileNotFoundError(f"目录里没有图片: {self.directory}")
        return self

    def __exit__(self, *exc) -> bool:
        return False

    def __iter__(self) -> Iterator[Frame]:
        import cv2
        for i, path in enumerate(self._paths):
            if i % self.stride != 0:
                continue
            img = cv2.imread(str(path), cv2.IMREAD_COLOR)
            if img is None:
                logger.warning(f"图片读取失败, 跳过: {path}")
                continue
            yield Frame(image=img, info=FrameInfo(
                filename=path.name, frame_index=i, total_frames=len(self._paths),
            ))


class _ImageSource:
    """单张图片源: 一张图当 1 帧源."""

    def __init__(self, path: Path, *, stride: int):
        self.path = path
        self.stride = stride

    def get_source_type(self) -> str:
        return SourceType.IMAGE

    def __enter__(self) -> "_ImageSource":
        if not self.path.exists():
            raise FileNotFoundError(f"图片不存在: {self.path}")
        return self

    def __exit__(self, *exc) -> bool:
        return False

    def __iter__(self) -> Iterator[Frame]:
        import cv2
        img = cv2.imread(str(self.path), cv2.IMREAD_COLOR)
        if img is None:
            raise ValueError(f"图片读取失败: {self.path}")
        yield Frame(image=img, info=FrameInfo(
            filename=self.path.name, frame_index=0, total_frames=1,
        ))


class _VideoSource:
    """视频文件源: cv2.VideoCapture 逐帧读, fps/总帧数来自文件."""

    def __init__(self, path: Path, *, stride: int):
        self.path = path
        self.stride = stride
        self._cap = None

    def get_source_type(self) -> str:
        return SourceType.VIDEO

    def __enter__(self) -> "_VideoSource":
        import cv2
        self._cap = cv2.VideoCapture(str(self.path))
        if not self._cap.isOpened():
            raise ValueError(f"视频打开失败: {self.path}")
        return self

    def __exit__(self, *exc) -> bool:
        if self._cap is not None:
            try:
                self._cap.release()
            except Exception:
                pass
            self._cap = None
        return False

    def __iter__(self) -> Iterator[Frame]:
        if self._cap is None:
            raise RuntimeError("源未打开, 请用 with 语句进入")
        import cv2
        fps = self._cap.get(cv2.CAP_PROP_FPS) or 0.0
        total = int(self._cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0) or None
        idx = 0
        while True:
            ok, img = self._cap.read()
            if not ok or img is None:
                break
            if idx % self.stride != 0:
                idx += 1
                continue
            yield Frame(image=img, info=FrameInfo(
                fps=fps, frame_index=idx, total_frames=total,
            ))
            idx += 1


class _CameraSource:
    """摄像头 / RTSP 流源. camera_id 可以是 int 或 '0' 或 'rtsp://...'."""

    def __init__(self, camera_id: Union[int, str], *, stride: int, config: Optional[CameraConfig]):
        self.camera_id = camera_id
        self.stride = stride
        self.config = config
        self._cap = None

    def get_source_type(self) -> str:
        return SourceType.CAMERA

    def __enter__(self) -> "_CameraSource":
        import cv2
        cap: Any = cv2.VideoCapture(self.camera_id)
        if self.config is not None:
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.config.width)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.config.height)
            cap.set(cv2.CAP_PROP_FPS, self.config.fps)
            cap.set(cv2.CAP_PROP_AUTOFOCUS, int(self.config.auto_focus))
            cap.set(cv2.CAP_PROP_BUFFERSIZE, self.config.buffer_size)
        if not cap.isOpened():
            raise ValueError(f"摄像头/流打开失败: {self.camera_id!r}")
        self._cap = cap
        return self

    def __exit__(self, *exc) -> bool:
        if self._cap is not None:
            try:
                self._cap.release()
            except Exception:
                pass
            self._cap = None
        return False

    def __iter__(self) -> Iterator[Frame]:
        if self._cap is None:
            raise RuntimeError("源未打开, 请用 with 语句进入")
        import cv2
        fps = self._cap.get(cv2.CAP_PROP_FPS) or 0.0
        idx = 0
        while True:
            ok, img = self._cap.read()
            if not ok or img is None:
                break
            if idx % self.stride != 0:
                idx += 1
                continue
            yield Frame(image=img, info=FrameInfo(
                fps=fps, frame_index=idx, total_frames=None,
            ))
            idx += 1


# ============================================================================
# 工厂
# ============================================================================

def create_frame_source(source, *, stride: int = 1) -> Any:
    """按 source 类型创建帧源(上下文管理器, 可迭代).

    Args:
        source: 图片路径 / 目录路径 / 视频路径 / 摄像头号(int 或 '0') / 'rtsp://...'
        stride: 每 N 帧取 1 帧 (1 = 全取)

    Returns:
        上下文管理器 + 迭代器, 有 get_source_type() 方法.
        摄像头配置由调用方在需要时通过 CameraConfig 显式传入 ——
        D8 pipeline 的 _Reader 会按源类型把 camera_id 注入 CameraConfig 再传进来.
    """
    stride = max(1, int(stride or 1))

    # 摄像头号 / RTSP: 交给摄像头源 (config 由调用方持有, 这里传 None 走默认)
    if isinstance(source, int) or (isinstance(source, str) and source.isdigit()):
        return _CameraSource(int(source), stride=stride, config=None)
    if isinstance(source, str) and source.lower().startswith(("rtsp://", "rtmp://")):
        return _CameraSource(source, stride=stride, config=None)

    # 其余: 字符串 → Path
    p = Path(source)
    if p.is_dir():
        return _ImageFolderSource(p, stride=stride)
    if p.suffix.lower() in IMAGE_EXTENSIONS:
        return _ImageSource(p, stride=stride)
    if p.suffix.lower() in (".mp4", ".avi", ".mov", ".mkv", ".webm", ".flv", ".m4v"):
        return _VideoSource(p, stride=stride)
    raise ValueError(f"无法识别的输入源: {source!r} (支持: 图片/目录/视频/摄像头号/RTSP)")