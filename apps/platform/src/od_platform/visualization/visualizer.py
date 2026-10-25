#!/usr/bin/env python
# @FileName  : visualizer.py
# @Project   : ODPlatform
# @Function  : BeautifyVisualizer —— 比 YOLO 原生 plot() 好看一档的绘制器
"""美化绘制.

输入归一化成 Detection 列表, 与 ultralytics 的具体结果类解耦:
    BeautifyVisualizer.from_yolo_results(...) 负责"从 YOLO 结果里抠字段"
    visualizer.draw(image, dets, style=...)   负责"画"

为什么不用 result.plot(): 原生绘制字号/配色不可控, 中文标签会乱码;
这里字号随图自适应、类别配色可按 yaml 配、支持 TTF 中文字体.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass

import numpy as np

from od_platform.visualization.style import BGR, DrawStyle

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class Detection:
    """一个检测框(与框架无关的最小事实)。"""
    label: str
    confidence: float
    xyxy: tuple[float, float, float, float]


class BeautifyVisualizer:
    """画框 + 标签牌。线程安全(无状态绘制)。"""

    def __init__(
        self,
        *,
        labels: list[str] | None = None,
        label_mapping: dict[str, str] | None = None,
        color_mapping: dict[str, BGR] | None = None,
        default_color: BGR = (0, 255, 0),
        font_path: str | None = None,
    ) -> None:
        self.labels = list(labels or [])
        self.label_mapping = dict(label_mapping or {})
        self.color_mapping = dict(color_mapping or {})
        self.default_color = default_color
        self.font_path = font_path
        self._pil_font_cache: dict[int, object] = {}

    # ------------------------------------------------------------------
    # 输入归一化
    # ------------------------------------------------------------------
    @staticmethod
    def from_yolo_results(
        boxes: np.ndarray,
        confidences: np.ndarray,
        labels: list[str],
    ) -> list[Detection]:
        """YOLO 的 (xyxy, conf, cls名) → Detection 列表。"""
        dets: list[Detection] = []
        for xyxy, conf, label in zip(
            np.asarray(boxes), np.asarray(confidences), labels, strict=False
        ):
            dets.append(Detection(
                label=str(label),
                confidence=float(conf),
                xyxy=(float(xyxy[0]), float(xyxy[1]), float(xyxy[2]), float(xyxy[3])),
            ))
        return dets

    # ------------------------------------------------------------------
    # 绘制
    # ------------------------------------------------------------------
    def draw(
        self,
        image: np.ndarray,
        detections: list[Detection],
        *,
        style: DrawStyle | None = None,
        use_label_mapping: bool = True,
    ) -> np.ndarray:
        """在 image 的副本上画, 返回新图(不改调用方数据)。"""
        import cv2

        st = style or DrawStyle.from_image_size(*image.shape[:2])
        canvas = image.copy()

        for det in detections:
            color = self.color_mapping.get(det.label, self.default_color)
            x1, y1, x2, y2 = (int(round(v)) for v in det.xyxy)
            cv2.rectangle(canvas, (x1, y1), (x2, y2), color, st.box_thickness)

            text = self.label_mapping.get(det.label, det.label) if use_label_mapping else det.label
            self._draw_label(canvas, f"{text} {det.confidence:.2f}", x1, y1,
                             color, st)
        return canvas

    # ------------------------------------------------------------------
    def _draw_label(self, canvas, text: str, x: int, y: int, color: BGR,
                    st: DrawStyle) -> None:
        """在框上方画一块底色牌 + 文字; 越界自动翻到框内。"""
        import cv2

        (tw, th), baseline = cv2.getTextSize(
            text, cv2.FONT_HERSHEY_SIMPLEX, st.text_scale, st.text_thickness
        )
        pad = st.text_padding
        box_h = th + baseline + pad
        top = y - box_h if y - box_h >= 0 else y

        # 半透明底牌
        overlay = canvas.copy()
        cv2.rectangle(overlay, (x, top), (x + tw + pad * 2, top + box_h), color, -1)
        cv2.addWeighted(overlay, st.text_bg_alpha, canvas, 1 - st.text_bg_alpha, 0, canvas)

        if self._is_ascii(text) or not self.font_path:
            cv2.putText(
                canvas, text, (x + pad, top + th + pad // 2),
                cv2.FONT_HERSHEY_SIMPLEX, st.text_scale, st.text_color,
                st.text_thickness, cv2.LINE_AA,
            )
        else:
            self._put_text_pil(canvas, text, x + pad, top + pad // 2, st)

    def _put_text_pil(self, canvas, text: str, x: int, y: int, st: DrawStyle) -> None:
        """中文标签走 PIL(TTF 字体); 出错就退回 cv2, 不让绘制失败传染整条流水线。"""
        try:
            from PIL import Image, ImageDraw, ImageFont
        except Exception as e:      # noqa: BLE001
            logger.warning("PIL 不可用, 中文标签退回 cv2: %s", e)
            return

        size = max(10, int(st.text_scale * 32))
        font = self._pil_font_cache.get(size)
        if font is None:
            font = ImageFont.truetype(self.font_path, size)
            self._pil_font_cache[size] = font

        pil = Image.fromarray(canvas[:, :, ::-1])
        draw = ImageDraw.Draw(pil)
        draw.text((x, y), text, font=font, fill=st.text_color[::-1])
        canvas[:, :, ::-1] = np.asarray(pil)

    @staticmethod
    def _is_ascii(text: str) -> bool:
        return all(ord(c) < 128 for c in text)
