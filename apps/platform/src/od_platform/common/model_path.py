#!/usr/bin/env python
# @FileName  : model_path.py
# @Project   : ODPlatform
# @Function  : 模型引用 → 磁盘路径(找不到就原样返回, 交给 ultralytics 自动下载)
"""模型引用解析.

'best' / 'best.pt' / 'runs/training/xxx/weights/best.pt' / 'yolov8n.pt' → 真实路径.
本地没有就原样返回 —— 让 ultralytics 自己按名字下载, 不在这里报错.
"""
from __future__ import annotations

from pathlib import Path

from od_platform.common.paths import MODELS_DIR


def resolve_model_path(
    ref: str | Path,
    search_dirs: list[Path] | None = None,
) -> str:
    """把模型引用解析成可用字符串: 本地命中给绝对路径, 否则原样返回。"""
    raw = str(ref).strip()
    p = Path(raw)

    # 1. 直接是存在的路径(绝对/相对)
    if p.exists():
        return str(p.resolve())

    # 2. 补 .pt 再试
    if p.suffix == "":
        p_pt = p.with_suffix(".pt")
        if p_pt.exists():
            return str(p_pt.resolve())

    # 3. 在各搜索目录里按文件名找
    name = p.name if p.suffix else f"{p.name}.pt"
    for d in (search_dirs or []):
        candidate = Path(d) / name
        if candidate.exists():
            return str(candidate.resolve())

    # 4. 兜底: 官方预训练权重目录
    candidate = MODELS_DIR / "pretrained" / name
    if candidate.exists():
        return str(candidate.resolve())

    return raw
