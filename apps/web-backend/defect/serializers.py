from __future__ import annotations

from rest_framework import serializers

from .models import DefectRecord, DefectType


class DefectTypeSerializer(serializers.ModelSerializer):
    record_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = DefectType
        fields = ["id", "type_name", "description", "record_count"]


class DefectRecordSerializer(serializers.ModelSerializer):
    defect_type_name = serializers.CharField(
        source="defect_type.type_name",
        read_only=True,
    )
    original_img_url = serializers.SerializerMethodField()
    defect_img_url = serializers.SerializerMethodField()

    class Meta:
        model = DefectRecord
        fields = [
            "id",
            "defect_type",
            "defect_type_name",
            "detect_person",
            "device_id",
            "confidence",
            "original_img",
            "original_img_url",
            "defect_img",
            "defect_img_url",
            "detect_time",
            "remark",
        ]
        read_only_fields = ["id", "detect_time"]

    def _absolute_url(self, field) -> str:
        if not field:
            return ""
        request = self.context.get("request")
        return request.build_absolute_uri(field.url) if request else field.url

    def get_original_img_url(self, obj: DefectRecord) -> str:
        return self._absolute_url(obj.original_img)

    def get_defect_img_url(self, obj: DefectRecord) -> str:
        return self._absolute_url(obj.defect_img)
