#!/usr/bin/env python
# @FileName  : __init__.py
# @Project   : ODPlatform
# @Function  : visualization 对外面板
"""美化绘制子系统.

    from od_platform.visualization import BeautifyVisualizer, DrawStyle

    vis = BeautifyVisualizer(labels=names, label_mapping={"person": "人员"})
    dets = BeautifyVisualizer.from_yolo_results(boxes, confs, labels)
    annotated = vis.draw(frame, dets, style=DrawStyle.from_image_size(h, w))
"""
from od_platform.visualization.style import DrawStyle
from od_platform.visualization.visualizer import BeautifyVisualizer, Detection

__all__ = ["BeautifyVisualizer", "DrawStyle", "Detection"]
