# apps/desktop/main.py
#!/usr/bin/env python
# -*- coding:utf-8 -*-
"""ODPlatform Desktop demo (PySide6).

验证 D8 接缝设计:
- 不修改 inference/ 任何代码
- 通过 QtSignalSink / InferHooks / CancelToken 三个接缝跟 InferService 集成
- UI 不冻 (推理跑在 QThread)
- Stop < 2s 响应 (CancelToken 4 个查询点)
"""
from __future__ import annotations

import logging
import os
import sys
from pathlib import Path

import numpy as np
from PySide6.QtCore import QThread, QTimer, Qt, Signal
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtWidgets import (
    QApplication, QFileDialog, QHBoxLayout, QLabel, QLineEdit, QMainWindow,
    QMessageBox, QProgressBar, QPushButton, QVBoxLayout, QWidget,
)

# 让 desktop app 能 import platform 包 (monorepo 跑法, 见 README)
THIS = Path(__file__).resolve()
sys.path.insert(0, str(THIS.parents[1] / "platform" / "src"))

from infer_worker import InferWorker
from qt_sink import QtSignalSink

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
)
logger = logging.getLogger("desktop")


class MainWindow(QMainWindow):
    """最小桌面 demo:
      - 模型 / 源 两个文本框 + Browse 按钮
      - Start / Stop 按钮
      - 实时画面 QLabel
      - 进度条 + 状态栏
    """

    request_start = Signal(str, str)    # model_path, source

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("ODPlatform Desktop Demo")
        self.resize(1280, 800)
        self._build_ui()
        self._build_worker()

    def _build_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)
        v = QVBoxLayout(central)

        # 模型行
        row_model = QHBoxLayout()
        row_model.addWidget(QLabel("Model:"))
        default_model = THIS.parents[2] / "models" / "pretrained" / "yolov8n.pt"
        self.le_model = QLineEdit(str(default_model))
        row_model.addWidget(self.le_model, 1)
        btn_browse_model = QPushButton("Browse...")
        btn_browse_model.clicked.connect(self._browse_model)
        row_model.addWidget(btn_browse_model)
        v.addLayout(row_model)

        # 源行
        row_src = QHBoxLayout()
        row_src.addWidget(QLabel("Source:"))
        self.le_source = QLineEdit("0")
        self.le_source.setPlaceholderText("摄像头号 (0/1...) 或 视频文件路径 或 图片目录")
        row_src.addWidget(self.le_source, 1)
        btn_browse_src = QPushButton("Browse...")
        btn_browse_src.clicked.connect(self._browse_source)
        row_src.addWidget(btn_browse_src)
        v.addLayout(row_src)

        # Start / Stop 行
        row_btn = QHBoxLayout()
        self.btn_start = QPushButton("Start")
        self.btn_start.clicked.connect(self._on_start)
        self.btn_stop = QPushButton("Stop")
        self.btn_stop.setEnabled(False)
        self.btn_stop.clicked.connect(self._on_stop)
        row_btn.addWidget(self.btn_start)
        row_btn.addWidget(self.btn_stop)
        v.addLayout(row_btn)

        # 进度条
        self.progress = QProgressBar()
        self.progress.setRange(0, 0)           # 启动时 indeterminate
        self.progress.setVisible(False)
        v.addWidget(self.progress)

        self.lbl_frame = QLabel("等待推理画面")
        self.lbl_frame.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_frame.setMinimumSize(640, 360)
        self.lbl_frame.setStyleSheet(
            "QLabel { background: #111; color: #bbb; border: 1px solid #444; }"
        )
        v.addWidget(self.lbl_frame, 1)

        self.statusBar().showMessage("就绪")
        self._last_pixmap: QPixmap | None = None

    def _build_worker(self) -> None:
        self.sink = QtSignalSink(self)
        self.worker_thread = QThread(self)
        self.worker = InferWorker()
        self.worker.set_sink(self.sink)
        self.worker.moveToThread(self.worker_thread)

        self.request_start.connect(self.worker.start_infer)
        # Sink 对象本身属于主线程，但 write() 从渲染线程调用；显式排队，
        # 防止 AutoConnection 因对象亲和性误判为 DirectConnection。
        self.sink.frame_ready.connect(
            self._on_frame,
            Qt.ConnectionType.QueuedConnection,
        )
        self.worker.progress_changed.connect(self._on_progress)
        self.worker.inference_finished.connect(self._on_finished)
        self.worker.inference_failed.connect(self._on_failed)
        self.worker_thread.finished.connect(self.worker.deleteLater)
        self.worker_thread.start()

    def _browse_model(self) -> None:
        start_dir = str(THIS.parents[2] / "models")
        path, _ = QFileDialog.getOpenFileName(
            self,
            "选择模型",
            start_dir,
            "模型文件 (*.pt *.onnx *.engine);;所有文件 (*)",
        )
        if path:
            self.le_model.setText(path)

    def _browse_source(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "选择图片或视频",
            str(THIS.parents[2]),
            "媒体文件 (*.jpg *.jpeg *.png *.bmp *.mp4 *.avi *.mov);;所有文件 (*)",
        )
        if path:
            self.le_source.setText(path)

    def _on_start(self) -> None:
        model = self.le_model.text().strip()
        source = self.le_source.text().strip()
        if not model:
            QMessageBox.warning(self, "缺少模型", "请先选择模型文件。")
            return
        if not source:
            QMessageBox.warning(self, "缺少输入源", "请输入摄像头编号或选择媒体文件。")
            return

        self._set_running(True)
        self._last_pixmap = None
        self.lbl_frame.setText("正在加载模型和输入源...")
        self.progress.setRange(0, 0)
        self.progress.setVisible(True)
        self.statusBar().showMessage(f"启动推理：{source}")
        self.request_start.emit(model, source)

    def _on_stop(self) -> None:
        self.statusBar().showMessage("正在停止并释放输入源...")
        self.btn_stop.setEnabled(False)
        # 直接调用线程安全令牌，避免 worker 阻塞时无法处理排队到它线程的事件。
        self.worker.cancel()

    def _on_progress(self, frame_idx: int, total: int, fps: float) -> None:
        if total > 0:
            self.progress.setRange(0, total)
            self.progress.setValue(min(frame_idx, total))
            progress_text = f"{frame_idx}/{total}"
        else:
            self.progress.setRange(0, 0)
            progress_text = str(frame_idx)
        self.statusBar().showMessage(
            f"已处理 {progress_text} 帧 | {fps:.1f} FPS"
        )

    def _on_finished(self, result) -> None:
        self._set_running(False)
        self.progress.setVisible(False)
        frames = result.stats.get("frames", 0)
        detections = result.stats.get("detections", 0)
        if result.error:
            self.lbl_frame.setText(f"推理失败：{result.error}")
            self.statusBar().showMessage("推理失败")
            QMessageBox.critical(self, "推理失败", result.error)
        else:
            self.statusBar().showMessage(
                f"推理结束：{frames} 帧，{detections} 个检测目标"
            )

    def _on_failed(self, message: str) -> None:
        self._set_running(False)
        self.progress.setVisible(False)
        self.lbl_frame.setText(f"推理失败：{message}")
        self.statusBar().showMessage("推理失败")
        QMessageBox.critical(self, "推理失败", message)

    def _set_running(self, running: bool) -> None:
        self.btn_start.setEnabled(not running)
        self.btn_stop.setEnabled(running)

    def _on_frame(self, frame: np.ndarray) -> None:
        if not isinstance(frame, np.ndarray) or frame.ndim != 3 or frame.shape[2] != 3:
            logger.warning("收到非 BGR 三通道画面，已忽略")
            return
        rgb = np.ascontiguousarray(frame[:, :, ::-1])
        height, width, _ = rgb.shape
        image = QImage(
            rgb.data,
            width,
            height,
            rgb.strides[0],
            QImage.Format.Format_RGB888,
        ).copy()
        self._last_pixmap = QPixmap.fromImage(image)
        self._display_pixmap()

    def _display_pixmap(self) -> None:
        if self._last_pixmap is None:
            return
        self.lbl_frame.setPixmap(
            self._last_pixmap.scaled(
                self.lbl_frame.size(),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
        )

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._display_pixmap()

    def closeEvent(self, event) -> None:
        if self.worker_thread.isRunning():
            self.worker.cancel()
            self.worker_thread.quit()
            if not self.worker_thread.wait(5000):
                logger.error("推理线程未在 5 秒内退出，继续关闭窗口")
        super().closeEvent(event)


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("ODPlatform Desktop")
    window = MainWindow()
    window.show()
    if os.environ.get("ODP_DESKTOP_SMOKE_TEST") == "1":
        QTimer.singleShot(500, window.close)
        QTimer.singleShot(1000, app.exit)
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
