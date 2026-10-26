from __future__ import annotations

from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models


class DefectType(models.Model):
    type_name = models.CharField(
        max_length=50,
        unique=True,
        verbose_name="缺陷类型名称",
    )
    description = models.TextField(blank=True, verbose_name="类型说明")

    class Meta:
        ordering = ["id"]
        verbose_name = "缺陷类型"
        verbose_name_plural = "缺陷类型"

    def __str__(self) -> str:
        return self.type_name


class DefectRecord(models.Model):
    defect_type = models.ForeignKey(
        DefectType,
        on_delete=models.PROTECT,
        related_name="records",
        verbose_name="缺陷类型",
    )
    detect_person = models.CharField(max_length=50, verbose_name="检测人员")
    device_id = models.CharField(max_length=50, verbose_name="检测设备编号")
    confidence = models.FloatField(
        validators=[MinValueValidator(0.0), MaxValueValidator(1.0)],
        verbose_name="检测置信度",
        help_text="0~1 之间",
    )
    original_img = models.ImageField(upload_to="original/", verbose_name="原图")
    defect_img = models.ImageField(
        upload_to="defect_img/",
        blank=True,
        verbose_name="缺陷标注图",
    )
    detect_time = models.DateTimeField(auto_now_add=True, verbose_name="检测时间")
    remark = models.TextField(blank=True, verbose_name="备注")

    class Meta:
        ordering = ["-detect_time", "-id"]
        verbose_name = "缺陷检测记录"
        verbose_name_plural = "缺陷检测记录"

    def __str__(self) -> str:
        return f"{self.defect_type.type_name} - {self.detect_person}"
