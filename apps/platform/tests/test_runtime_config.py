"""runtime_config 生成器测试: 把"能生成"变成"知道什么情况下生成成什么样"。

覆盖老师点名的 5 个场景:
    正常生成 / 文件已存在跳过 / 覆盖+备份 / 空字段 / 特殊字符转义
"""

from __future__ import annotations

from pathlib import Path

import yaml

from od_platform.runtime_config import (
    build_infer_config,
    build_train_config,
    build_val_config,
)
from od_platform.runtime_config.generator import ConfigGenerator
from od_platform.runtime_config.infer import YOLOInferConfig
from od_platform.runtime_config.train import YOLOTrainConfig
from od_platform.runtime_config.val import YOLOValConfig


def test_generate_creates_file(tmp_path: Path) -> None:
    """正常生成: 返回 True, 文件存在且能被 yaml 解析。"""
    out = tmp_path / "train.yaml"
    assert ConfigGenerator().generate(YOLOTrainConfig, out) is True
    assert out.is_file()
    data = yaml.safe_load(out.read_text(encoding="utf-8"))
    assert isinstance(data, dict) and data  # 非空
    assert "epochs" in data  # 核心字段在


def test_generate_skips_existing_without_overwrite(tmp_path: Path) -> None:
    """已存在且 overwrite=False: 返回 False(不是错误), 原文件一个字节都不动。"""
    out = tmp_path / "train.yaml"
    out.write_text("# 我手动改过, 别覆盖\n", encoding="utf-8")
    assert ConfigGenerator().generate(YOLOTrainConfig, out) is False
    assert out.read_text(encoding="utf-8") == "# 我手动改过, 别覆盖\n"


def test_generate_overwrite_makes_backup(tmp_path: Path) -> None:
    """覆盖时先备份: 原内容进了 .bak.<时间戳>, 新文件是生成结果。"""
    out = tmp_path / "train.yaml"
    out.write_text("# 旧内容\n", encoding="utf-8")
    assert ConfigGenerator().generate(YOLOTrainConfig, out, overwrite=True) is True
    backups = list(tmp_path.glob("train.yaml.bak.*"))
    assert len(backups) == 1, f"应恰好一个备份, 实际: {backups}"
    assert backups[0].read_text(encoding="utf-8") == "# 旧内容\n"
    assert "epochs" in yaml.safe_load(out.read_text(encoding="utf-8"))


def test_generate_overwrite_can_disable_backup(tmp_path: Path) -> None:
    """backup=False: 覆盖但不留备份。"""
    out = tmp_path / "train.yaml"
    out.write_text("# 旧内容\n", encoding="utf-8")
    assert ConfigGenerator().generate(
        YOLOTrainConfig, out, overwrite=True, backup=False
    ) is True
    assert list(tmp_path.glob("train.yaml.bak.*")) == []


def test_generate_handles_empty_fields(tmp_path: Path) -> None:
    """字段为 None 时照常落盘(None 是合法取值, 如 model/data), 不能炸。"""
    out = tmp_path / "train.yaml"
    ConfigGenerator().generate(YOLOTrainConfig, out)
    data = yaml.safe_load(out.read_text(encoding="utf-8"))
    assert data["model"] is None
    assert data["data"] is None


def test_generate_escapes_special_chars_in_title(tmp_path: Path) -> None:
    """标题含冒号/井号/中文/引号时, 生成的 YAML 仍能被解析回来。"""
    nasty = '训练: 第一版 #1 "重点"'
    out = tmp_path / "train.yaml"
    assert ConfigGenerator().generate(YOLOTrainConfig, out, title=nasty) is True
    text = out.read_text(encoding="utf-8")
    assert nasty in text  # 原样出现在注释里
    yaml.safe_load(text)  # 关键: 能解析, 说明没把 YAML 弄坏


def test_build_config_functions_share_one_impl() -> None:
    """三个 build_* 共用同一实现, 只传不同配置类 —— 行为应完全对称。"""
    for builder, cfg_cls in (
        (build_train_config, YOLOTrainConfig),
        (build_val_config, YOLOValConfig),
        (build_infer_config, YOLOInferConfig),
    ):
        config, merger = builder(yaml_path=None)
        assert isinstance(config, cfg_cls)
        assert merger is not None
