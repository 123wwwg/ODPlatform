from __future__ import annotations

from django.apps import AppConfig


class DefectConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "defect"
    verbose_name = "缺陷检测台账"
