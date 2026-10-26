from __future__ import annotations

from django.contrib import admin

from .models import DefectRecord, DefectType


@admin.register(DefectType)
class DefectTypeAdmin(admin.ModelAdmin):
    list_display = ["id", "type_name", "description"]
    search_fields = ["type_name"]


@admin.register(DefectRecord)
class DefectRecordAdmin(admin.ModelAdmin):
    list_display = [
        "id",
        "defect_type",
        "detect_person",
        "device_id",
        "confidence",
        "detect_time",
    ]
    list_filter = ["defect_type", "detect_person"]
    search_fields = ["device_id", "detect_person"]
    readonly_fields = ["detect_time"]
