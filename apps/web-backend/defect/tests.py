from __future__ import annotations

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from PIL import Image
from rest_framework.test import APIClient

from .models import DefectRecord, DefectType


def make_test_image() -> SimpleUploadedFile:
    from io import BytesIO

    buffer = BytesIO()
    Image.new("RGB", (80, 60), (32, 96, 160)).save(buffer, format="JPEG")
    return SimpleUploadedFile(
        "sample.jpg",
        buffer.getvalue(),
        content_type="image/jpeg",
    )


class DefectApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.defect_type, _ = DefectType.objects.get_or_create(
            type_name="测试划痕",
            defaults={"description": "自动化测试使用的类型"},
        )

    def test_record_crud(self):
        create_response = self.client.post(
            "/api/defect-record/",
            {
                "defect_type": self.defect_type.id,
                "detect_person": "张工",
                "device_id": "CAM-01",
                "confidence": 0.92,
                "original_img": make_test_image(),
                "remark": "自动创建测试",
            },
            format="multipart",
        )
        self.assertEqual(create_response.status_code, 201, create_response.data)
        record_id = create_response.data["id"]

        list_response = self.client.get("/api/defect-record/")
        self.assertEqual(list_response.status_code, 200)
        self.assertEqual(len(list_response.data), 1)

        update_response = self.client.patch(
            f"/api/defect-record/{record_id}/",
            {"confidence": 0.88, "remark": "已复核"},
            format="json",
        )
        self.assertEqual(update_response.status_code, 200, update_response.data)
        self.assertEqual(update_response.data["confidence"], 0.88)

        detail_response = self.client.get(f"/api/defect-record/{record_id}/")
        self.assertEqual(detail_response.status_code, 200)
        self.assertEqual(detail_response.data["defect_type_name"], "测试划痕")

        delete_response = self.client.delete(f"/api/defect-record/{record_id}/")
        self.assertEqual(delete_response.status_code, 204)
        self.assertFalse(DefectRecord.objects.filter(id=record_id).exists())

    def test_stats_and_type_list(self):
        stats_response = self.client.get("/api/stats/")
        self.assertEqual(stats_response.status_code, 200)
        self.assertEqual(stats_response.data["total_records"], 0)
        self.assertEqual(
            stats_response.data["total_types"],
            DefectType.objects.count(),
        )

        type_response = self.client.get("/api/defect-type/")
        self.assertEqual(type_response.status_code, 200)
        type_names = {item["type_name"] for item in type_response.data}
        self.assertIn("测试划痕", type_names)

    def test_model_overview_endpoint(self):
        response = self.client.get("/api/model/")
        self.assertEqual(response.status_code, 200)
        self.assertIn(
            response.data["status"],
            {"completed", "training", "not_found"},
        )
