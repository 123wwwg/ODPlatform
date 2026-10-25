#!/usr/bin/env python
# -*- coding:utf-8 -*-
# @FileName  : config_log.py
# @Project   : ODPlatform
# @Function  : 配置溯源日志 — 把 D5 merger 痕迹打成日志(D6/D8 共用)
"""配置溯源日志 helper.

把 D6 runtime_config.report 的两张表打到 logger; log_override_chains 额外
逐字段打印完整改写链 (给推理/训练开跑前的"参数从哪来"复盘).

★ 本模块只做"渲染→logger"的转发, 表格渲染逻辑住在 runtime_config.report(单一真相).
"""
from __future__ import annotations

import logging
from typing import Any, Optional

from od_platform.runtime_config.report import (
    render_effective, render_overrides,
)

logger = logging.getLogger(__name__)


def log_effective_config(config: Any, merger: Any, *,
                         logger: Optional[logging.Logger] = None) -> None:
    """打印反查表: 每字段当前值 + 来源."""
    log = logger or logging.getLogger(__name__)
    for line in render_effective(config, merger):
        log.info(line)


def log_override_chains(config: Any, merger: Any, *,
                        logger: Optional[logging.Logger] = None) -> None:
    """打印追因表 + 完整改写链 (每字段一行)."""
    log = logger or logging.getLogger(__name__)
    for line in render_overrides(config, merger):
        log.info(line)