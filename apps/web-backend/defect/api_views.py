from __future__ import annotations

from django.db.models import Count, Q
from django.utils import timezone
from rest_framework import filters, permissions, viewsets
from rest_framework.decorators import api_view
from rest_framework.response import Response

from .models import DefectRecord, DefectType
from .serializers import DefectRecordSerializer, DefectTypeSerializer


class DefectTypeViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = DefectType.objects.annotate(record_count=Count("records"))
    serializer_class = DefectTypeSerializer
    authentication_classes = []
    permission_classes = [permissions.AllowAny]


class DefectRecordViewSet(viewsets.ModelViewSet):
    queryset = DefectRecord.objects.select_related("defect_type").all()
    serializer_class = DefectRecordSerializer
    authentication_classes = []
    permission_classes = [permissions.AllowAny]
    filter_backends = [filters.SearchFilter]
    search_fields = ["defect_type__type_name", "detect_person", "device_id", "remark"]

    def get_queryset(self):
        queryset = super().get_queryset()
        defect_type = self.request.query_params.get("defect_type")
        if defect_type:
            queryset = queryset.filter(defect_type_id=defect_type)
        return queryset


@api_view(["GET"])
def dashboard_stats(request):
    records = DefectRecord.objects.all()
    today = timezone.localdate()
    type_counts = (
        DefectType.objects.annotate(
            count=Count("records"),
        )
        .values("type_name", "count")
        .order_by("-count", "type_name")
    )
    return Response(
        {
            "total_records": records.count(),
            "today_records": records.filter(detect_time__date=today).count(),
            "high_confidence": records.filter(
                Q(confidence__gte=0.8),
            ).count(),
            "total_types": DefectType.objects.count(),
            "average_confidence": round(
                (
                    sum(records.values_list("confidence", flat=True))
                    / max(records.count(), 1)
                ),
                3,
            ),
            "type_counts": list(type_counts),
        }
    )
