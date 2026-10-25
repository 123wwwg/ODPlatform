#!/usr/bin/env python
# -*- coding:utf-8 -*-
# @FileName  : val.py
# @Project   : ODPlatform
# @Function  : runtime_config 子系统——YOLO 验证配置类
"""YOLO 验证配置: YOLOValConfig.

继承 BaseConfig + 13 个验证特有字段.
默认值与 infer 拉开差异(conf 0.001 vs 0.25), 因为评估要全量召回.
"""
from __future__ import annotations

import warnings
from typing import ClassVar, Optional

from pydantic import Field, field_validator, model_validator

from od_platform.common.constants import Task
from od_platform.runtime_config.base import BaseConfig


class YOLOValConfig(BaseConfig):
    """YOLO 验证配置: 继承 BaseConfig + 13 个验证特有字段."""

    # task 只用来选模型, 不传给 ultralytics (model.val() 从权重推断)
    FRAMEWORK_ONLY_FIELDS: ClassVar[set[str]] = (
        BaseConfig.FRAMEWORK_ONLY_FIELDS | {"experiment_name", "task"}
    )

    task: str = Field(
        default=Task.DETECT,
        description="任务类型(SSoT)",
        json_schema_extra={
            "group":    "核心参数",
            "examples": list(Task.all()),
            "tips": [
                "限定取值: " + " / ".join(Task.all()),
                "决定模型加载方式",
                "注意: task 不传给 ultralytics (model.val() 从权重推断)",
            ],
            "yaml_comment": "任务类型(只能是 detect / segment)",
        },
    )

    experiment_name: Optional[str] = Field(
        default=None,
        description="实验名(目录组织用)",
        json_schema_extra={
            "group":    "核心参数",
            "examples": ["baseline", "helmet_v1", None],
            "tips": [
                "None: 由 ultralytics 自动生成 exp / exp2...",
                "验证输出子目录 runs/val/<name>/",
            ],
            "yaml_comment": "实验名(None=自动生成)",
        },
    )

    # ============================================================
    # 验证特有字段
    # ============================================================

    val_imgsz: int = Field(
        default=640,
        ge=32,
        description="验证图像尺寸",
        json_schema_extra={
            "group":    "验证控制",
            "examples": [480, 640, 800],
            "tips": [
                "验证时单独指定尺寸(默认与 imgsz 一致)",
                "通常比训练尺寸大, 提升 mAP",
            ],
            "yaml_comment": "验证图像尺寸(默认同 imgsz)",
        },
    )

    batch: int = Field(
        default=16,
        ge=1,
        description="验证批次大小",
        json_schema_extra={
            "group":    "验证控制",
            "examples": [8, 16, 32],
            "tips": [
                "验证时批次大小",
                "显存不足时减小",
            ],
            "yaml_comment": "验证批次大小",
        },
    )

    conf: float = Field(
        default=0.001, gt=0, le=1.0,
        description="置信度阈值",
        json_schema_extra={
            "group":    "验证控制",
            "examples": [0.001, 0.01, 0.05],
            "tips": [
                "★ 验证模式: 低阈值(0.001) 保留所有候选框, 计算完整 mAP",
                "推理模式默认 0.25 — 语义不同, 勿混用",
            ],
            "yaml_comment": "置信度阈值(验证=0.001, 全量召回)",
        },
    )

    iou: float = Field(
        default=0.6, gt=0, le=1.0,
        description="IoU 阈值(NMS + 评估)",
        json_schema_extra={
            "group":    "验证控制",
            "examples": [0.5, 0.6, 0.7],
            "tips": [
                "评估时 NMS 的 IoU 阈值",
                "mAP50-95 中 50-95 是另一维度, 别混",
            ],
            "yaml_comment": "IoU 阈值(NMS)",
        },
    )

    half: bool = Field(
        default=False,
        description="FP16 半精度验证",
        json_schema_extra={
            "group":    "验证控制",
            "examples": [False, True],
            "tips": [
                "True: 用 FP16 验证(更快省显存)",
                "与训练 amp 独立控制",
            ],
            "yaml_comment": "是否 FP16 半精度验证",
        },
    )

    dnn: bool = Field(
        default=False,
        description="ONNX 推理引擎",
        json_schema_extra={
            "group":    "验证控制",
            "examples": [False, True],
            "tips": ["True: 使用 ONNX Runtime 验证导出模型"],
            "yaml_comment": "是否用 ONNX 引擎验证",
        },
    )

    split: str = Field(
        default="val",
        description="验证数据划分",
        json_schema_extra={
            "group":    "验证控制",
            "examples": ["train", "val", "test"],
            "tips": [
                "★ 从 yaml 里选哪个 split 来验证",
                "只有 val/test 是诚实的; train 只适合调试",
                "最终交报告必须用 test",
            ],
            "yaml_comment": "验证划分(train / val / test)",
        },
    )

    # ============================================================
    # 输出控制
    # ============================================================

    save_json: bool = Field(
        default=True,
        description="保存 JSON 结果",
        json_schema_extra={
            "group":    "输出控制",
            "examples": [True, False],
            "tips": ["保存预测结果到 JSON 文件", "后续分析/对比用"],
            "yaml_comment": "是否保存 JSON 结果",
        },
    )

    save_hybrid: bool = Field(
        default=False,
        description="混合标签保存",
        json_schema_extra={
            "group":    "输出控制",
            "examples": [False, True],
            "tips": ["标签 + 预测同时保存到输出图", "检查错检漏检用"],
            "yaml_comment": "是否保存混合标签",
        },
    )

    save_txt: bool = Field(
        default=False,
        description="保存 TXT 标签",
        json_schema_extra={
            "group":    "输出控制",
            "examples": [False, True],
            "tips": ["将预测结果保存为 YOLO 格式 txt"],
            "yaml_comment": "是否保存 TXT 预测结果",
        },
    )

    save_conf: bool = Field(
        default=True,
        description="标签显示置信度",
        json_schema_extra={
            "group":    "输出控制",
            "examples": [True, False],
            "tips": ["输出图上显示置信度数值", "需配合 save_txt/save_json 等才可见"],
            "yaml_comment": "标签是否显示置信度",
        },
    )

    save_crop: bool = Field(
        default=False,
        description="保存预测裁剪",
        json_schema_extra={
            "group":    "输出控制",
            "examples": [False, True],
            "tips": ["保存每个预测框的裁剪图", "方便人工复核"],
            "yaml_comment": "是否保存预测裁剪图",
        },
    )

    max_det: int = Field(
        default=300, ge=1,
        description="最大检测数",
        json_schema_extra={
            "group":    "输出控制",
            "examples": [100, 300, 1000],
            "tips": ["单图最多保留的检测框数", "防止密集场景失控"],
            "yaml_comment": "单图最大检测数",
        },
    )

    # ============================================================
    # 验证器
    # ============================================================

    @field_validator("task")
    @classmethod
    def _validate_task(cls, v: str) -> str:
        if v not in Task.all():
            raise ValueError(
                f"task 必须是 {sorted(Task.all())} 之一, 当前值: {v!r}. "
                f"若想给本次实验取名, 请使用 experiment_name 字段."
            )
        return v

    @field_validator("split")
    @classmethod
    def _validate_split(cls, v: str) -> str:
        if v not in ("train", "val", "test"):
            raise ValueError(
                f"split 必须是 'train' / 'val' / 'test' 之一, 当前值: {v!r}"
            )
        return v

    @model_validator(mode="after")
    def _cross_field_validation(self) -> "YOLOValConfig":
        if self.save_conf and not self.save_txt and not self.save_json:
            warnings.warn(
                "save_conf=True 但 save_txt=False 且 save_json=False, "
                "置信度数值不会出现在任何输出中.",
                UserWarning,
            )
        return self