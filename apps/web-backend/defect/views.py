from __future__ import annotations

from django.shortcuts import get_object_or_404, redirect, render

from .forms import DefectForm
from .models import DefectRecord


def defect_list(request):
    records = DefectRecord.objects.select_related("defect_type").all()
    return render(request, "defect/list.html", {"records": records})


def defect_add(request):
    if request.method == "POST":
        form = DefectForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            return redirect("defect_list")
    else:
        form = DefectForm()
    return render(request, "defect/add.html", {"form": form})


def defect_detail(request, defect_id: int):
    record = get_object_or_404(DefectRecord, id=defect_id)
    return render(request, "defect/detail.html", {"record": record})


def defect_edit(request, defect_id: int):
    record = get_object_or_404(DefectRecord, id=defect_id)
    if request.method == "POST":
        form = DefectForm(request.POST, request.FILES, instance=record)
        if form.is_valid():
            form.save()
            return redirect("defect_detail", defect_id=record.id)
    else:
        form = DefectForm(instance=record)
    return render(request, "defect/edit.html", {"form": form, "record": record})


def defect_delete(request, defect_id: int):
    record = get_object_or_404(DefectRecord, id=defect_id)
    if request.method == "POST":
        record.delete()
        return redirect("defect_list")
    return render(request, "defect/delete_confirm.html", {"record": record})
