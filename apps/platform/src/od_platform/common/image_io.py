#!/usr/bin/env python
# @FileName  : image_io.py
# @Project   : ODPlatform
# @Function  : 中文/非 ASCII 路径安全的图像读写
"""图像 IO 兜底.

OpenCV 的 cv2.imread / cv2.imwrite 在 Windows 上遇到非 ASCII 路径(如 "D:/大三实训课/...")
会【静默失败】—— imread 返回 None, imwrite 返回 False, 不报异常.
本模块用 np.fromfile / tofile + imdecode / imencode 绕开该限制, 行为与 cv2 一致.
"""
from __future__ import annotations

import logging
from pathlib import Path

import numpy as np

logger = logging.getLogger(__name__)


def imread(path: str | Path) -> np.ndarray | None:
    """读图(路径安全). 失败返回 None, 与 cv2.imread 语义一致."""
    import cv2

    p = Path(path)
    try:
        buf = np.fromfile(str(p), dtype=np.uint8)
        if buf.size == 0:
            return None
        img = cv2.imdecode(buf, cv2.IMREAD_COLOR)
        return img
    except Exception as e:      # noqa: BLE001
        logger.warning("读取图片失败 %s: %s", p, e)
        return None


def imwrite(path: str | Path, image: np.ndarray) -> bool:
    """写图(路径安全). 失败返回 False, 与 cv2.imwrite 语义一致."""
    import cv2

    p = Path(path)
    try:
        p.parent.mkdir(parents=True, exist_ok=True)
        ext = p.suffix or ".jpg"
        ok, buf = cv2.imencode(ext, image)
        if not ok:
            return False
        buf.tofile(str(p))
        return True
    except Exception as e:      # noqa: BLE001
        logger.warning("写入图片失败 %s: %s", p, e)
        return False
