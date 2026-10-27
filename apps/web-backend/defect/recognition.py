from __future__ import annotations

import threading
import time
from collections import Counter
from io import BytesIO
from pathlib import Path
from typing import Any

from django.conf import settings

_MODEL_LOCK = threading.Lock()
_MODEL_CACHE: dict[str, tuple[float, Any]] = {}


def latest_trained_weight() -> Path:
    models_dir = settings.BASE_DIR.parents[1] / "models" / "trained"
    candidates = sorted(
        models_dir.glob("*-best.pt"),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )
    if not candidates:
        raise FileNotFoundError("尚未找到训练完成的 best.pt 权重。")
    return candidates[0]


def _get_model(model_path: Path):
    from ultralytics import YOLO

    key = str(model_path.resolve())
    modified = model_path.stat().st_mtime
    cached = _MODEL_CACHE.get(key)
    if cached and cached[0] == modified:
        return cached[1]
    model = YOLO(key)
    _MODEL_CACHE[key] = (modified, model)
    return model


def _jpeg_bytes(image, quality: int = 92) -> bytes:
    buffer = BytesIO()
    image.convert("RGB").save(buffer, format="JPEG", quality=quality, optimize=True)
    return buffer.getvalue()


def recognize_image_file(
    uploaded_file,
    *,
    confidence: float = 0.25,
    iou: float = 0.7,
) -> dict[str, Any]:
    import numpy as np
    from PIL import Image, ImageOps, UnidentifiedImageError

    if not 0 <= confidence <= 1:
        raise ValueError("置信度阈值必须在 0 到 1 之间。")
    if not 0 <= iou <= 1:
        raise ValueError("IoU 阈值必须在 0 到 1 之间。")

    try:
        image = Image.open(uploaded_file)
        image = ImageOps.exif_transpose(image).convert("RGB")
    except (UnidentifiedImageError, OSError) as exc:
        raise ValueError("上传文件不是有效的图片。") from exc

    original_buffer = BytesIO()
    image.save(original_buffer, format="JPEG", quality=93, optimize=True)
    original_bytes = original_buffer.getvalue()
    bgr_image = np.asarray(image)[:, :, ::-1].copy()

    model_path = latest_trained_weight()
    with _MODEL_LOCK:
        model = _get_model(model_path)
        started = time.perf_counter()
        results = model.predict(
            source=bgr_image,
            conf=confidence,
            iou=iou,
            imgsz=640,
            device="cpu",
            verbose=False,
        )
        inference_ms = (time.perf_counter() - started) * 1000

    result = results[0]
    names = result.names or {}
    boxes = result.boxes
    detections: list[dict[str, Any]] = []
    class_counts: Counter[str] = Counter()
    if boxes is not None:
        coordinates = boxes.xyxy.cpu().numpy()
        confidences = boxes.conf.cpu().numpy()
        classes = boxes.cls.int().cpu().tolist()
        for bbox, score, class_id in zip(coordinates, confidences, classes):
            label = str(names.get(int(class_id), f"class_{class_id}"))
            detections.append(
                {
                    "class_id": int(class_id),
                    "label": label,
                    "confidence": round(float(score), 4),
                    "bbox": [round(float(value), 1) for value in bbox],
                }
            )
            class_counts[label] += 1

    # 用平台自己的可视化模块出图: 类别自动配色 + 右上角图例
    from od_platform.visualization import BeautifyVisualizer, Detection, DrawStyle

    palette = [
        (56, 56, 255), (151, 157, 255), (31, 112, 255), (29, 178, 255),
        (49, 210, 207), (10, 249, 72), (23, 204, 146), (134, 219, 61),
        (52, 147, 26), (187, 212, 0), (168, 153, 44), (255, 194, 0),
    ]
    color_mapping = {
        str(name): palette[i % len(palette)]
        for i, name in enumerate(names.values())
    }
    visualizer = BeautifyVisualizer(
        labels=[str(v) for v in names.values()],
        color_mapping=color_mapping,
    )
    dets = [
        Detection(
            xyxy=tuple(item["bbox"]),
            confidence=float(item["confidence"]),
            label=str(item["label"]),
        )
        for item in detections
    ]
    style = DrawStyle.from_image_size(*bgr_image.shape[:2], show_legend=True)
    annotated_bgr = visualizer.draw(bgr_image, dets, style=style)

    annotated_rgb = annotated_bgr[:, :, ::-1]
    annotated_image = Image.fromarray(annotated_rgb.astype(np.uint8))

    return {
        "original_bytes": original_bytes,
        "annotated_bytes": _jpeg_bytes(annotated_image),
        "object_count": len(detections),
        "model_name": model_path.name,
        "confidence_threshold": confidence,
        "iou_threshold": iou,
        "inference_ms": round(inference_ms, 2),
        "detections": detections,
        "class_counts": dict(sorted(class_counts.items())),
        "width": image.width,
        "height": image.height,
    }
