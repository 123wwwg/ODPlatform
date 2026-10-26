from __future__ import annotations

from django import forms

from .models import DefectRecord


class DefectForm(forms.ModelForm):
    class Meta:
        model = DefectRecord
        fields = [
            "defect_type",
            "detect_person",
            "device_id",
            "confidence",
            "original_img",
            "defect_img",
            "remark",
        ]
        widgets = {
            "remark": forms.Textarea(attrs={"rows": 3}),
            "confidence": forms.NumberInput(attrs={"min": 0, "max": 1, "step": 0.01}),
        }
