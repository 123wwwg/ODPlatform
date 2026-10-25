#!/usr/bin/env python
# -*- coding:utf-8 -*-
# @FileName  : log_rename.py
# @Project   : ODPlatform
# @Function  : 把本次运行的项目日志复制一份到输出目录, 与产物对齐
"""日志对齐输出目录。

D8 InferService 收尾阶段调用: 把项目根 logger 当前日志文件复制到推理输出目录,
命名 <model_stem>.log —— 于是 output_dir 里"结果 + 日志 + 审计"三件套齐全, 复盘不用
回头翻 logging/ 目录猜是哪次.

★ 复制而非移动: 源日志文件可能正被 FileHandler 占用(Windows 移动会失败),
  且 logging/ 目录的完整时间线仍应保留. 磁盘比排查时间便宜.
"""
from __future__ import annotations

import logging
import shutil
from pathlib import Path
from typing import Optional

from od_platform.common.logging_utils import ROOT_LOGGER_NAME

logger = logging.getLogger(__name__)


def _find_project_log_path() -> Optional[Path]:
    """从项目根 logger 找 FileHandler 的实际文件路径 (只读)."""
    root = logging.getLogger(ROOT_LOGGER_NAME)
    for h in root.handlers:
        if isinstance(h, logging.FileHandler):
            return Path(h.baseFilename)
    return None


def rename_log_to_save_dir(output_dir: Path, model_stem: str) -> Optional[Path]:
    """把当前项目日志复制到 output_dir/<model_stem>.log.

    Args:
        output_dir: 推理/训练输出目录
        model_stem: 模型主干名 (如 'yolo11n')

    Returns:
        目标日志路径; 找不到当前日志文件时返回 None (不抛).
    """
    src = _find_project_log_path()
    if src is None:
        logger.warning("未找到项目日志文件, 跳过日志对齐: %s", output_dir)
        return None
    output_dir.mkdir(parents=True, exist_ok=True)
    dst = output_dir / f"{model_stem}.log"
    try:
        shutil.copy2(src, dst)
        logger.info("日志已对齐到输出目录: %s", dst)
        return dst
    except OSError as e:
        logger.warning("日志复制失败 (不影响结果): %s", e)
        return None