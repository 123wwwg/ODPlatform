#!/usr/bin/env python
# @FileName  : style.py
# @Project   : ODPlatform
# @Function  : DrawStyle —— 绘制样式(随图像尺寸自适应)
"""绘制样式.

尺寸相关的量(线宽 / 字号)按短边比例算: 4K 图和 480p 图用同一份样式, 视觉比例一致.
"""
from __future__ import annotations

from dataclasses import dataclass

BGR = tuple[int, int, int]


@dataclass(frozen=True)
class DrawStyle:
    """一次绘制用到的全部样式量(不可变, 可安全跨线程共享)."""

    box_thickness: int = 2
    text_scale: float = 0.5
    text_thickness: int = 1
    text_color: BGR = (255, 255, 255)
    text_bg_color: BGR = (40, 40, 40)
    text_bg_alpha: float = 0.6
    text_padding: int = 4
    corner_ratio: float = 0.18           # 圆角/折角比例(相对框短边)

    @classmethod
    def from_image_size(cls, height: int, width: int, **overrides) -> DrawStyle:
        """按图像短边自适应出样式; overrides 里给的字段优先(yaml 可覆盖)."""
        short = max(1, min(int(height), int(width)))
        base = {
            "box_thickness": max(1, round(short / 320)),
            "text_scale": max(0.35, short / 1280),
            "text_thickness": max(1, round(short / 640)),
            "text_padding": max(2, round(short / 320)),
        }
        # 只接受本 dataclass 认识的键, 未知键忽略(yaml 里写错不致命)
        valid = {k: v for k, v in overrides.items() if k in cls.__dataclass_fields__}
        return cls(**{**base, **valid})
