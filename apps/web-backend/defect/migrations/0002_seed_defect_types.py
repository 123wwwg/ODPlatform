from __future__ import annotations

from django.db import migrations


DEFAULT_TYPES = [
    ("划痕", "表面线性擦伤或刮痕"),
    ("污渍", "油污、水渍或其他表面污染"),
    ("缺角", "工件边缘缺失或破损"),
    ("尺寸偏差", "尺寸超出允许公差范围"),
    ("其他", "尚未归类的缺陷"),
]


def create_default_types(apps, schema_editor):
    DefectType = apps.get_model("defect", "DefectType")
    for type_name, description in DEFAULT_TYPES:
        DefectType.objects.get_or_create(
            type_name=type_name,
            defaults={"description": description},
        )


def remove_default_types(apps, schema_editor):
    DefectType = apps.get_model("defect", "DefectType")
    DefectType.objects.filter(
        type_name__in=[name for name, _ in DEFAULT_TYPES],
        records__isnull=True,
    ).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("defect", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(create_default_types, remove_default_types),
    ]
