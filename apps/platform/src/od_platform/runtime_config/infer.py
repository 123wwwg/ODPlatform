#!/usr/bin/env python
# -*- coding:utf-8 -*-
# @FileName  : infer.py
# @Project   : ODPlatform
# @Function  : runtime_config 子系统——YOLO 推理配置类
"""YOLO 推理配置: YOLOInferConfig.

继承 BaseConfig + 24 个推理特有字段.
conf 默认 0.25(推理要"只出靠谱的"), 与 val 的 0.001(全量召回)语义相反.
"""
from __future__ import annotations

import warnings
from pathlib import Path
from typing import ClassVar, List, Optional, Union

from pydantic import Field, field_validator, model_validator

from od_platform.common.constants import Task
from od_platform.runtime_config.base import BaseConfig


class YOLOInferConfig(BaseConfig):
    """YOLO 推理配置: 继承 BaseConfig + 24 个推理特有字段."""

    FRAMEWORK_ONLY_FIELDS: ClassVar[set[str]] = (
        BaseConfig.FRAMEWORK_ONLY_FIELDS | {"experiment_name", "task"}
    )

    # ============================================================
    # 核心参数
    # ============================================================

    task: str = Field(
        default=Task.DETECT,
        description="任务类型(SSoT)",
        json_schema_extra={
            "group":    "核心参数",
            "examples": list(Task.all()),
            "tips": [
                "限定取值: " + " / ".join(Task.all()),
                "决定模型加载方式",
                "注意: task 不传给 ultralytics (model.predict() 从权重推断)",
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
            "tips": ["推理输出子目录 runs/predict/<name>/"],
            "yaml_comment": "实验名(None=自动生成)",
        },
    )

    source: Optional[Union[str, Path]] = Field(
        default=None,
        description="推理输入源",
        json_schema_extra={
            "group":    "核心参数",
            "examples": [
                "image.jpg",
                "video.mp4",
                "path/to/images/",
                "rtsp://example.com/live.sdp",
                "0",
                "https://example.com/img.jpg",
            ],
            "tips": [
                "支持: 图像 / 视频 / 目录 / URL / 摄像头索引 / RTSP 流",
                "目录: 自动遍历所有图像文件",
                "0 / '0' / 1: 摄像头编号",
                "None: 必须通过 CLI 传 --source (运行时)",
            ],
            "yaml_comment": "推理输入源(图/视频/目录/URL/摄像头/流)",
        },
    )

    # ============================================================
    # 推理控制
    # ============================================================

    conf: float = Field(
        default=0.25, gt=0, le=1.0,
        description="置信度阈值",
        json_schema_extra={
            "group":    "推理控制",
            "examples": [0.2, 0.25, 0.5, 0.7],
            "tips": [
                "★ 默认 0.25: 推理要'只出靠谱的', 与验证 0.001 语义相反",
                "工业质检建议: 0.5+",
            ],
            "yaml_comment": "置信度阈值(默认 0.25)",
        },
    )

    iou: float = Field(
        default=0.7, gt=0, le=1.0,
        description="NMS IoU 阈值",
        json_schema_extra={
            "group":    "推理控制",
            "examples": [0.5, 0.6, 0.7],
            "tips": ["NMS 去重阈值", "密集场景调低"],
            "yaml_comment": "NMS IoU 阈值",
        },
    )

    imgsz: int = Field(
        default=640,
        ge=32,
        description="推理图像尺寸",
        json_schema_extra={
            "group":    "推理控制",
            "examples": [320, 640, 1280],
            "tips": ["推理分辨率", "越大越准越慢"],
            "yaml_comment": "推理图像尺寸(像素)",
        },
    )

    max_det: int = Field(
        default=300, ge=1,
        description="最大检测数",
        json_schema_extra={
            "group":    "推理控制",
            "examples": [100, 300, 1000],
            "tips": ["单图最多保留的检测框数"],
            "yaml_comment": "单图最大检测数",
        },
    )

    vid_stride: int = Field(
        default=1, ge=1,
        description="视频抽帧步长",
        json_schema_extra={
            "group":    "推理控制",
            "examples": [1, 2, 5],
            "tips": ["视频推理每隔 N 帧处理一帧", "提高速度"],
            "yaml_comment": "视频抽帧步长",
        },
    )

    line_width: Optional[Union[int, float]] = Field(
        default=None,
        description="标注线宽",
        json_schema_extra={
            "group":    "推理控制",
            "examples": [1, 2, 3, None],
            "tips": ["预测框线宽, None=自动按图大小"],
            "yaml_comment": "标注线宽(None=自动)",
        },
    )

    visualize: bool = Field(
        default=False,
        description="特征可视化",
        json_schema_extra={
            "group":    "推理控制",
            "examples": [False, True],
            "tips": ["可视化模型特征图", "调试用"],
            "yaml_comment": "是否可视化特征图",
        },
    )

    augment: bool = Field(
        default=False,
        description="测试时增强(TTA)",
        json_schema_extra={
            "group":    "推理控制",
            "examples": [False, True],
            "tips": ["True: TTA, 精度更高但更慢", "通常推理保持 False"],
            "yaml_comment": "是否使用测试时增强(TTA)",
        },
    )

    agnostic_nms: bool = Field(
        default=False,
        description="跨类 NMS",
        json_schema_extra={
            "group":    "推理控制",
            "examples": [False, True],
            "tips": ["True: NMS 不分类别(可抑制类别间重叠)"],
            "yaml_comment": "是否跨类别 NMS",
        },
    )

    retina_masks: bool = Field(
        default=False,
        description="高分辨率 Mask(分割)",
        json_schema_extra={
            "group":    "推理控制",
            "examples": [False, True],
            "tips": ["仅 segment 任务", "True: 高质量 mask 但更慢"],
            "yaml_comment": "高分辨率 mask(仅分割)",
        },
    )

    # ============================================================
    # 视频流
    # ============================================================

    stream: bool = Field(
        default=False,
        description="视频流模式",
        json_schema_extra={
            "group":    "视频流",
            "examples": [False, True],
            "tips": ["True: 流式处理(不一次读完整视频)"],
            "yaml_comment": "视频流模式",
        },
    )

    stream_buffer: bool = Field(
        default=False,
        description="流缓冲",
        json_schema_extra={
            "group":    "视频流",
            "examples": [False, True],
            "tips": ["True: 缓冲帧避免丢帧"],
            "yaml_comment": "是否缓冲视频流",
        },
    )

    # ============================================================
    # 输出控制
    # ============================================================

    save: bool = Field(
        default=True,
        description="保存结果图",
        json_schema_extra={
            "group":    "输出控制",
            "examples": [True, False],
            "tips": ["保存带标注的结果图/视频"],
            "yaml_comment": "是否保存结果",
        },
    )

    save_txt: bool = Field(
        default=False,
        description="保存 TXT 标签",
        json_schema_extra={
            "group":    "输出控制",
            "examples": [False, True],
            "tips": ["将预测保存为 YOLO 格式 txt"],
            "yaml_comment": "是否保存 TXT 标签",
        },
    )

    save_conf: bool = Field(
        default=True,
        description="标签显示置信度",
        json_schema_extra={
            "group":    "输出控制",
            "examples": [True, False],
            "tips": ["输出图上显示置信度数值"],
            "yaml_comment": "标签是否显示置信度",
        },
    )

    save_crop: bool = Field(
        default=False,
        description="保存预测裁剪",
        json_schema_extra={
            "group":    "输出控制",
            "examples": [False, True],
            "tips": ["保存每个预测框的裁剪图"],
            "yaml_comment": "是否保存预测裁剪图",
        },
    )

    show: bool = Field(
        default=False,
        description="显示结果窗口",
        json_schema_extra={
            "group":    "输出控制",
            "examples": [False, True],
            "tips": ["True: 弹窗实时显示"],
            "yaml_comment": "是否实时显示结果",
        },
    )

    show_labels: bool = Field(
        default=True,
        description="显示类别标签",
        json_schema_extra={
            "group":    "输出控制",
            "examples": [True, False],
            "tips": ["输出图上显示类别名"],
            "yaml_comment": "是否显示类别标签",
        },
    )

    show_conf: bool = Field(
        default=True,
        description="显示置信度数值",
        json_schema_extra={
            "group":    "输出控制",
            "examples": [True, False],
            "tips": ["输出图上显示置信度"],
            "yaml_comment": "是否显示置信度",
        },
    )

    show_boxes: bool = Field(
        default=True,
        description="显示检测框",
        json_schema_extra={
            "group":    "输出控制",
            "examples": [True, False],
            "tips": ["输出图上画检测框"],
            "yaml_comment": "是否显示检测框",
        },
    )

    # ============================================================
    # 任务特定
    # ============================================================

    crop_nms: bool = Field(
        default=False,
        description="裁剪后 NMS",
        json_schema_extra={
            "group":    "任务特定",
            "examples": [False, True],
            "tips": ["裁剪推理后是否 NMS"],
            "yaml_comment": "裁剪后是否 NMS",
        },
    )

    # ============================================================
    # 验证器
    # ============================================================

    @field_validator("source", mode="before")
    @classmethod
    def _validate_source(cls, v):
        """int 摄像头索引 → 标准化为 str (mode='before' 让 int 不被类型检查先拒)"""
        if isinstance(v, int) and not isinstance(v, bool):
            return str(v)
        return v

    @field_validator("task")
    @classmethod
    def _validate_task(cls, v: str) -> str:
        if v not in Task.all():
            raise ValueError(
                f"task 必须是 {sorted(Task.all())} 之一, 当前值: {v!r}. "
                f"若想给本次实验取名, 请使用 experiment_name 字段."
            )
        return v

    @model_validator(mode="after")
    def _cross_field_validation(self) -> "YOLOInferConfig":
        if self.save_conf and not self.save_txt:
            warnings.warn(
                "save_conf=True 但 save_txt=False, 置信度只会画在图上, 不会进 txt.",
                UserWarning,
            )
        if self.stream_buffer and not self.stream:
            warnings.warn(
                "stream_buffer=True 但 stream=False, stream_buffer 不会生效.",
                UserWarning,
            )
        if self.retina_masks and self.task != Task.SEGMENT:
            warnings.warn(
                "retina_masks=True 仅对 segment 任务有效, 当前 task=detect, 不会生效.",
                UserWarning,
            )
        if self.augment and self.stream:
            warnings.warn(
                "augment(TTA) 与 stream 同时开启会显著降低吞吐, 请确认意图.",
                UserWarning,
            )
        return self