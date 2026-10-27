from __future__ import annotations

from collections import Counter
from pathlib import Path
from urllib.parse import quote

from od_platform.common.constants import IMAGE_EXTENSIONS
from od_platform.data_validation.labels import parse_label_line

from .data_catalog import DEFAULT_DATASET, class_names, data_root, dataset_yaml, read_yaml
from .data_reports import latest_validation

DATASET_NAME = DEFAULT_DATASET


def get_dataset_understanding(name: str = DEFAULT_DATASET) -> dict:
    config = dataset_yaml(name)
    data = read_yaml(name)
    metadata = data.get("odp_meta") or {}
    split_meta = metadata.get("split") or {}
    classes = class_names(data)
    root = data_root(name, data)
    class_counts = Counter()
    samples = []
    split_stats = {}
    for split in ("train", "val", "test"):
        images_dir = root / "images" / split if root else None
        labels_dir = root / "labels" / split if root else None
        image_files = (
            sorted(
                path
                for path in images_dir.iterdir()
                if path.is_file() and path.suffix.lower() in IMAGE_EXTENSIONS
            )
            if images_dir and images_dir.is_dir()
            else []
        )
        label_files = sorted(labels_dir.glob("*.txt")) if labels_dir and labels_dir.is_dir() else []
        split_counts = Counter()
        box_count = 0
        for label in label_files:
            try:
                text = label.read_text(encoding="utf-8")
            except (OSError, UnicodeError):
                continue
            for line in text.splitlines():
                box, _ = parse_label_line(line, metadata.get("task", "detect"))
                if box is None:
                    continue
                class_id = box[0]
                label_name = (
                    classes[class_id] if 0 <= class_id < len(classes) else f"class_{class_id}"
                )
                box_count += 1
                class_counts[label_name] += 1
                split_counts[label_name] += 1
        split_stats[split] = {
            "images": len(image_files),
            "boxes": box_count,
            "class_counts": dict(split_counts),
        }
        for image in image_files[:3]:
            try:
                version = image.stat().st_mtime_ns
            except OSError:
                continue
            samples.append(
                {
                    "split": split,
                    "name": image.name,
                    "url": f"/api/data/sample/{split}/{quote(image.name)}?dataset={quote(name)}&v={version}",
                }
            )
    return {
        "name": name,
        "classes": classes,
        "class_count": len(classes),
        "splits": {
            split: {"images": value["images"], "boxes": value["boxes"]}
            for split, value in split_stats.items()
        },
        "class_counts": dict(class_counts),
        "split_class_counts": {
            split: value["class_counts"] for split, value in split_stats.items()
        },
        "total_images": sum(value["images"] for value in split_stats.values()),
        "total_boxes": sum(value["boxes"] for value in split_stats.values()),
        "strategy": split_meta.get("strategy"),
        "seed": split_meta.get("seed"),
        "validation": latest_validation(name),
        "samples": samples,
        "yaml_path": str(config),
        "available": bool(root and root.is_dir()),
        "message": ""
        if root and root.is_dir()
        else "本机尚未找到配置指向的成品数据，请准备原始数据后运行流水线。",
    }


def dataset_sample_path(split: str, filename: str, name: str = DEFAULT_DATASET) -> Path | None:
    if split not in {"train", "val", "test"} or Path(filename).name != filename:
        return None
    root = data_root(name, read_yaml(name))
    if root is None:
        return None
    candidate = root / "images" / split / filename
    try:
        candidate.resolve().relative_to((root / "images" / split).resolve())
    except ValueError:
        return None
    return candidate if candidate.is_file() else None
