#!/usr/bin/env python
# @FileName  : base.py
# @Project   : ODPlatform
# @Function  : FrameSource 抽象协议 —— 下游只认 read()/release()
"""帧源抽象.

所有源(图片/视频/摄像头/第三方)都实现同一套三件事:
    get_source_type() -> SourceType
    read()            -> Frame | None     (None = 源耗尽)
    release()         -> None             (幂等)

再加上迭代协议 + 上下文管理 —— 调用方 for frame in src: 即可.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Iterator

from .types import Frame, SourceType


class FrameSource(ABC):
    """帧源协议。子类至少实现 read / release / get_source_type。"""

    def __init__(self) -> None:
        self._released = False

    # ---- 必须实现 ----
    @abstractmethod
    def get_source_type(self) -> SourceType:
        """返回本源的类型(决定下游按流还是按图处理)。"""

    @abstractmethod
    def read(self) -> Frame | None:
        """读下一帧; 源耗尽返回 None。"""

    @abstractmethod
    def release(self) -> None:
        """释放底层资源(幂等)。"""

    # ---- 通用能力 ----
    @property
    def is_live(self) -> bool:
        """是否实时源(摄像头/网络流)。默认 False。"""
        return False

    def __iter__(self) -> Iterator[Frame]:
        while True:
            frame = self.read()
            if frame is None:
                break
            yield frame

    def __enter__(self) -> FrameSource:
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.release()

    def __len__(self) -> int:
        """可枚举的源(图片集合/视频)可以给总数; 实时源不支持。"""
        raise TypeError(f"{type(self).__name__} 没有已知帧数")
