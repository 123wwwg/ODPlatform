#!/usr/bin/env python
# @FileName  : image.py
# @Project   : ODPlatform
# @Function  : 单图 + 图片目录源
"""图片源: 一个文件 or 一个目录(按文件名排序遍历)。"""
from __future__ import annotations

import logging
from pathlib import Path

from od_platform.frame_source.base import FrameSource
from od_platform.frame_source.types import (
    IMAGE_EXTENSIONS,
    Frame,
    FrameInfo,
    SourceType,
)

logger = logging.getLogger(__name__)


class ImageSource(FrameSource):
    """单图 / 图片目录。坏图跳过并 warn, 不让一张脏图毁掉整批推理。"""

    def __init__(self, source: str | Path, *, stride: int = 1) -> None:
        super().__init__()
        self._path = Path(source)
        self._stride = max(1, int(stride))
        self._files: list[Path] = self._collect()
        self._idx = 0

    def _collect(self) -> list[Path]:
        if self._path.is_dir():
            files = sorted(
                p for p in self._path.iterdir()
                if p.is_file() and p.suffix.lower() in IMAGE_EXTENSIONS
            )
        elif self._path.is_file():
            files = [self._path]
        else:
            raise FileNotFoundError(f"图片源不存在: {self._path}")
        if not files:
            raise FileNotFoundError(f"目录里没有图片文件: {self._path}")
        return files

    def get_source_type(self) -> SourceType:
        return SourceType.IMAGE

    def read(self) -> Frame | None:
        from od_platform.common.image_io import imread

        while self._idx < len(self._files):
            path = self._files[self._idx]
            index = self._idx
            self._idx += self._stride
            image = imread(path)
            if image is None:
                logger.warning("图片读取失败, 跳过: %s", path)
                continue
            return Frame(
                image=image,
                info=FrameInfo(
                    frame_index=index, filename=path.name,
                    fps=None, source_type=SourceType.IMAGE,
                    total_frames=len(self._files),
                ),
            )
        return None

    def release(self) -> None:
        self._released = True

    def __len__(self) -> int:
        return len(range(0, len(self._files), self._stride))
