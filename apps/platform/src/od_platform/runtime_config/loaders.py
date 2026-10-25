#!/usr/bin/env python
# -*- coding:utf-8 -*-
# @FileName  : loaders.py
# @Author    : 雨霓同学 (ODPlatform team)
# @Project   : ODPlatform
# @Function  : 配置源加载器(YAML / CLI / 汇总)
"""配置源加载器: YAMLLoader / CLILoader / load_all_sources.

哲学:
  1. Loader 只负责"把外部数据变成 dict", 不做合并、不设优先级.
  2. Fail-fast: 缺文件报错就要带修复指引(odp-gen-config), 绝不静默.
  3. _drop_none 只过滤 None, 绝不误杀 False / 0 / ''.
"""
from __future__ import annotations

import re
import shlex
from argparse import Namespace
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Union

import yaml


# ============================================================
# _drop_none: 只过滤 None, 不误杀 falsy 值
# ============================================================

def _drop_none(d: Mapping[str, Any]) -> Dict[str, Any]:
    """移除值为 None 的键.

    ★ 经典坑: 不能写 `if v` — 那会连 False / 0 / '' 一起过滤.
      必须显式 `is None`.
    """
    return {k: v for k, v in d.items() if v is not None}


# ============================================================
# YAMLLoader
# ============================================================

class YAMLLoader:
    """YAML 配置文件加载器.

    Args:
        config_dir: 相对路径解析的基准目录(默认 None = 当前工作目录).
    """

    def __init__(self, config_dir: Optional[Union[str, Path]] = None):
        self.config_dir = Path(config_dir) if config_dir else None

    # ------------------------------------------------------------
    # 路径解析
    # ------------------------------------------------------------

    def _resolve_path(self, yaml_path: Union[str, Path]) -> Path:
        p = Path(yaml_path)
        if p.is_absolute():
            return p                       # 绝对路径: 无视 config_dir
        if self.config_dir is not None:
            return self.config_dir / p
        return p                           # 没有 config_dir: 基于当前目录

    # ------------------------------------------------------------
    # 加载
    # ------------------------------------------------------------

    def load(self, yaml_path: Union[str, Path]) -> Dict[str, Any]:
        """加载 YAML → dict.

        Raises:
            FileNotFoundError: 文件不存在(带 odp-gen-config 修复指引)
            ValueError:        YAML 格式错误 / 顶层不是字典(保留 __cause__ 链)
        """
        resolved = self._resolve_path(yaml_path)
        if not resolved.exists():
            template_name = resolved.stem            # 修复指引里的模板名
            raise FileNotFoundError(
                f"配置文件不存在: {resolved}\n"
                f"    → 请先生成默认配置模板: odp-gen-config {template_name}\n"
                f"    → 或检查路径是否正确"
            )

        try:
            data = yaml.safe_load(resolved.read_text(encoding="utf-8"))
        except Exception as e:
            err = ValueError(
                f"YAML 格式错误: {resolved}\n"
                f"    → 检查缩进(用空格, 不要用 Tab)\n"
                f"    → 检查引号 / 冒号是否正确闭合\n"
                f"原始错误: {type(e).__name__}: {e}"
            )
            err.__cause__ = e
            raise err from e

        if data is None:
            return {}                          # 空文件 / 全是注释
        if not isinstance(data, dict):
            raise ValueError(
                f"YAML 顶层必须是字典(mapping), 当前是: {type(data).__name__}\n"
                f"    → 检查文件是否被误导出成 list / 标量"
            )

        return _drop_none(data)                # yaml null → 过滤(显式 false/0 保留)


# ============================================================
# CLILoader
# ============================================================

class CLILoader:
    """命令行参数加载器: argparse.Namespace / dict → dict.

    Args:
        exclude:    额外的排除字段(并入 DEFAULT_EXCLUDE)
        mapping:    CLI 参数名 → Pydantic 字段名 的映射
    """

    # 控制/元字段: 不可能是配置, 进 merge 只会污染
    DEFAULT_EXCLUDE: List[str] = [
        "help", "config", "cfg", "yaml_path", "debug", "version", "verbose",
    ]

    def __init__(
        self,
        exclude: Optional[List[str]] = None,
        mapping: Optional[Dict[str, str]] = None,
    ):
        self._exclude = set(self.DEFAULT_EXCLUDE) | set(exclude or [])
        self._mapping = dict(mapping or {})

    def load(
        self,
        args: Optional[Union[Namespace, Dict[str, Any]]],
        filter_none: bool = True,
    ) -> Dict[str, Any]:
        """解析 args → 配置 dict.

        Raises:
            TypeError: args 类型不是 Namespace / dict / None
        """
        if args is None:
            return {}

        if isinstance(args, dict):
            raw = dict(args)
        elif isinstance(args, Namespace):
            raw = {k: v for k, v in vars(args).items()}
        else:
            raise TypeError(
                f"args 必须是 argparse.Namespace / dict / None, "
                f"当前: {type(args).__name__}"
            )

        # 1. 映射 CLI 名 → 字段名 (如 learning_rate → lr0)
        raw = {self._mapping.get(k, k): v for k, v in raw.items()}

        # 2. 排除控制字段 + 私有字段(下划线开头)
        result = {
            k: v for k, v in raw.items()
            if k not in self._exclude and not k.startswith("_")
        }

        # 3. 过滤 None(可选; 默认过滤)
        if filter_none:
            result = _drop_none(result)

        return result


# ============================================================
# load_all_sources: 汇总各源
# ============================================================

def load_all_sources(
    yaml_path: Optional[Union[str, Path]] = None,
    yaml_dir: Optional[Union[str, Path]] = None,
    cli_args: Optional[Union[Namespace, Dict[str, Any]]] = None,
    cli_exclude: Optional[List[str]] = None,
    cli_mapping: Optional[Dict[str, str]] = None,
) -> Dict[str, Dict[str, Any]]:
    """一次性加载所有配置源.

    Returns:
        {"yaml": {...}, "cli": {...}}  — 未提供的源返回空 dict.
    """
    sources: Dict[str, Dict[str, Any]] = {}

    if yaml_path is not None:
        loader = YAMLLoader(config_dir=yaml_dir)
        sources["yaml"] = loader.load(yaml_path)
    else:
        sources["yaml"] = {}

    if cli_args is not None:
        loader = CLILoader(exclude=cli_exclude, mapping=cli_mapping)
        sources["cli"] = loader.load(cli_args)
    else:
        sources["cli"] = {}

    return sources