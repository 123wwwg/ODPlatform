#!/usr/bin/env python
# @FileName  : config_log.py
# @Project   : ODPlatform
# @Function  : 配置日志 —— D5 溯源报告的薄别名(D8 命名)
"""配置日志门面.

真正的渲染在 runtime_config/report.py(D5 的家), 这里只是给推理服务一个
"按 D8 习惯命名"的入口, 避免 service 直接依赖 runtime_config 的内部结构.
"""
from __future__ import annotations

import logging
from typing import Any

from od_platform.runtime_config.report import render_effective, render_overrides


def log_effective_config(
    config: Any, merger: Any, *, logger: logging.Logger | None = None
) -> None:
    """反向查询: 每个字段当前值 + 来源。"""
    log = logger or logging.getLogger(__name__)
    for line in render_effective(config, merger):
        log.info(line)


def log_override_chains(
    config: Any, merger: Any, *, logger: logging.Logger | None = None
) -> None:
    """追因: 合并过程中被改写的字段及其完整链路。"""
    log = logger or logging.getLogger(__name__)
    for line in render_overrides(config, merger):
        log.info(line)
