#!/usr/bin/env python
# -*- coding:utf-8 -*-
# @FileName  : model_path.py
# @Project   : ODPlatform
# @Function  : 模型引用 -> 实际路径 (本地优先, 缺失交给 ultralytics 下载)
"""模型路径解析.

规则 (跟 refs.resolve_ref 同构, 但多目录搜索):
  - 显式路径 (含分隔符 / 绝对路径): 直接用
  - 纯名字 ('yolo11n' / 'best'): 在 search_dirs 里找 <name>.pt, 找到返回绝对路径
  - 都找不到: 原样返回名字字符串, 交给 ultralytics 自动下载
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import List, Optional, Union

logger = logging.getLogger(__name__)


def resolve_model_path(
    model: str,
    *,
    search_dirs: Optional[List[Union[str, Path]]] = None,
) -> str:
    """模型引用 -> 给 ultralytics 的字符串 (本地路径 or 原样名字).

    Args:
        model: 'yolo11n' / 'yolo11n.pt' / 'best' / 显式路径
        search_dirs: 搜索目录列表 (默认空 → 只识别显式路径)

    Returns:
        绝对路径字符串; 找不到时原样返回 model.
    """
    p = Path(model)
    if p.is_absolute() or len(p.parts) > 1:
        # 显式路径: 文件不存在也原样返回, 让 ultralytics 报错(信息更准)
        return str(p)

    name = p.name if p.suffix else f"{p.name}.pt"
    for d in (search_dirs or []):
        candidate = Path(d) / name
        if candidate.exists():
            logger.info("模型(解析): %s", candidate)
            return str(candidate)

    logger.info("本地无 %s, 原样交给 ultralytics: %s", name, model)
    return model