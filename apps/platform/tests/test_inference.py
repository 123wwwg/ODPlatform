#!/usr/bin/env python
"""推理子系统测试(沙箱: ultralytics 用替身, 验证契约而非精度).

★ ultralytics 替身必须在 import inference 之前塞进 sys.modules ——
  service.py 在模块顶层 `from ultralytics import YOLO`, 晚了就绑到真包(还慢).
"""
from __future__ import annotations

import json
import sys
import types
from pathlib import Path

import numpy as np
import pytest

from od_platform.common.image_io import imwrite


# ---------------------------------------------------------------------------
# 假 ultralytics
# ---------------------------------------------------------------------------
class _T:
    def __init__(self, v):
        self._v = np.asarray(v)

    def cpu(self):
        return self

    def numpy(self):
        return self._v

    def int(self):
        return _T(self._v.astype(int))

    def tolist(self):
        return self._v.tolist()


class _Boxes:
    def __init__(self, n):
        self._n = n

    def __len__(self):
        return self._n

    @property
    def xyxy(self):
        return _T([[10.0, 20.0, 60.0, 90.0]] * self._n)

    @property
    def conf(self):
        return _T([0.9] * self._n)

    @property
    def cls(self):
        return _T([0] * self._n)


class _Result:
    speed = {"preprocess": 1.0, "inference": 5.0, "postprocess": 1.5}

    def __init__(self, n, image):
        self.boxes = _Boxes(n)
        self._image = image

    def plot(self):
        return self._image.copy()


class _FakeYOLO:
    """每帧固定 1 个检测(tumor), 2 类名字."""

    def __init__(self, model_path):
        self.model_path = str(model_path)
        self.names = {0: "tumor", 1: "lesion"}

    def __call__(self, images, **kwargs):
        return [_Result(1, img) for img in images]


_fake_ultralytics = types.ModuleType("ultralytics")
_fake_ultralytics.YOLO = _FakeYOLO
sys.modules.setdefault("ultralytics", _fake_ultralytics)

from od_platform.inference import (  # noqa: E402
    CancelToken,
    FrameEvent,
    InferHooks,
    LocalFileSink,
    NullSink,
    OutputSink,
    ProgressEvent,
    infer_yolo,
    load_pipeline_config,
)
from od_platform.inference import service as service_module  # noqa: E402
from od_platform.inference.overlay import FPSCounter, Metrics, draw_hud, draw_pause  # noqa: E402


# ---------------------------------------------------------------------------
# fixtures
# ---------------------------------------------------------------------------
@pytest.fixture
def image_dir(tmp_path: Path) -> Path:
    d = tmp_path / "imgs"
    d.mkdir()
    for i in range(3):
        assert imwrite(d / f"img_{i}.jpg", np.full((120, 160, 3), 50 + i * 20, np.uint8))
    return d


@pytest.fixture
def runs_dir(tmp_path, monkeypatch):
    """把推理输出重定向到 tmp, 不污染仓库 runs/."""
    d = tmp_path / "runs"
    monkeypatch.setattr(service_module, "RUNS_DIR", d)
    monkeypatch.setattr(service_module, "log_device_info", lambda *a, **kw: {})
    return d


@pytest.fixture
def pipeline_yaml(tmp_path: Path) -> Path:
    p = tmp_path / "infer_pipeline.yaml"
    p.write_text(
        "frame_source:\n"
        "  camera:\n"
        "    width: 640\n"
        "    height: 480\n"
        "    fps: 15\n"
        "visualization:\n"
        "  enabled: true\n"
        "  use_label_mapping: true\n"
        "  label_mapping:\n"
        "    tumor: 肿瘤\n"
        "  color_mapping:\n"
        "    tumor: [0, 255, 0]\n"
        "  default_color: [0, 0, 255]\n"
        "  style:\n"
        "    text_scale: 0.8\n",
        encoding="utf-8",
    )
    return p


# ============================================================
# pipeline_config
# ============================================================
class TestPipelineConfig:
    def test_loads_camera_and_style(self, pipeline_yaml):
        pc = load_pipeline_config(pipeline_yaml)
        assert pc.viz_enabled is True
        assert pc.label_mapping == {"tumor": "肿瘤"}
        assert pc.color_mapping["tumor"] == (0, 255, 0)      # list → tuple
        assert pc.default_color == (0, 0, 255)
        assert pc.style_overrides == {"text_scale": 0.8}
        cam = pc.build_camera_config()
        assert cam.width == 640 and cam.fps == 15

    def test_missing_file_returns_defaults(self, tmp_path):
        pc = load_pipeline_config(tmp_path / "nope.yaml")
        assert pc.viz_enabled is True and pc.camera_raw == {}
        assert pc.build_camera_config() is None          # 非摄像头源用不到

    def test_broken_yaml_falls_back(self, tmp_path):
        bad = tmp_path / "bad.yaml"
        bad.write_text("visualization: [unclosed\n", encoding="utf-8")
        assert load_pipeline_config(bad).viz_enabled is True

    def test_invalid_color_raises(self, tmp_path):
        p = tmp_path / "c.yaml"
        p.write_text("visualization:\n  default_color: [1, 2]\n", encoding="utf-8")
        with pytest.raises(ValueError, match="B, G, R"):
            load_pipeline_config(p)

    def test_to_audit_is_plain_dict(self, pipeline_yaml):
        d = load_pipeline_config(pipeline_yaml).to_audit()
        assert d["color_mapping_n"] == 1 and d["label_mapping_n"] == 1
        assert d["default_color"] == [0, 0, 255]
        json.dumps(d)          # 必须可 JSON 化(进 audit)


# ============================================================
# overlay
# ============================================================
class TestOverlay:
    def test_fps_counter_window(self):
        fps = FPSCounter(window_size=3)
        for ms in [10, 10, 10, 20]:
            fps.update(ms)
        # 窗口只剩 10/10/20 → 均值 13.33ms → 75 FPS(第一个 10 已被挤出)
        assert fps.fps == pytest.approx(75.0)
        assert fps.inst == pytest.approx(50.0)     # 最近一帧 20ms

    def test_fps_counter_ignores_nonpositive(self):
        fps = FPSCounter()
        fps.update(0)
        fps.update(-1)
        assert fps.fps == 0.0 and fps.inst == 0.0

    def test_metrics_snapshot(self):
        m = Metrics()
        m.capture.update(33.3)
        m.add_speed({"preprocess": 1.5, "inference": 8.0, "postprocess": 2.0})
        m.add_speed({"preprocess": 1.6, "inference": 8.5, "postprocess": 2.1})
        m.loop.update(50.0)
        snap = m.snapshot()
        assert snap["capture_fps"] == pytest.approx(30.0, abs=0.2)
        assert snap["infer_fps"] > 100
        assert snap["speed_ms"]["inference"] == pytest.approx(8.25)
        json.dumps(snap)

    def test_add_speed_none_is_noop(self):
        m = Metrics()
        m.add_speed(None)
        assert m.speed_avg_ms() == {}

    def test_draw_hud_respects_show_info(self):
        frame = np.zeros((240, 320, 3), np.uint8)
        m = Metrics()
        before = frame.copy()
        draw_hud(frame, m, n_dets=2, show_info=False)
        assert np.array_equal(frame, before), "show_info=False 不该改像素"
        draw_hud(frame, m, n_dets=2, recording=True, show_info=True)
        assert not np.array_equal(frame, before), "show_info=True 应该画上面板"

    def test_draw_pause_dims_frame(self):
        frame = np.full((120, 160, 3), 200, np.uint8)
        draw_pause(frame)
        assert frame.mean() < 200


# ============================================================
# 三个接缝
# ============================================================
class TestSeams:
    def test_cancel_token_idempotent(self):
        t = CancelToken()
        assert not t.is_cancelled()
        t.cancel()
        t.cancel()
        assert t.is_cancelled()

    def test_cancel_token_visible_across_threads(self):
        import threading
        t = CancelToken()
        seen = threading.Event()

        def watcher():
            if t.wait(1.0):
                seen.set()

        threading.Thread(target=watcher, daemon=True).start()
        t.cancel()
        assert seen.wait(1.0)

    def test_hooks_default_silent(self):
        h = InferHooks()
        assert h.progress_interval_frames == 30
        evt = FrameEvent(0, np.zeros((1, 1, 3), np.uint8), np.zeros((1, 1, 3), np.uint8), 0)
        h.fire_frame(evt)
        h.fire_progress(ProgressEvent(1, 10, 0.1, 1.0, 1.0, 1))
        h.fire_complete("r")
        h.fire_error(RuntimeError())

    def test_hooks_swallow_user_exception(self):
        def boom(*a, **kw):
            raise RuntimeError("user bug")

        h = InferHooks(on_frame=boom, on_progress=boom, on_complete=boom, on_error=boom)
        evt = FrameEvent(0, np.zeros((1, 1, 3), np.uint8), np.zeros((1, 1, 3), np.uint8), 0)
        # 四个 fire_* 都不该把异常漏出来
        h.fire_frame(evt)
        h.fire_progress(ProgressEvent(1, 10, 0.1, 1.0, 1.0, 1))
        h.fire_complete("r")
        h.fire_error(RuntimeError())

    def test_output_sink_is_abstract(self):
        with pytest.raises(TypeError):
            OutputSink()

    def test_null_sink_writes_nothing(self, tmp_path):
        from od_platform.frame_source import SourceType

        sink = NullSink()
        sink.open(tmp_path, SourceType.VIDEO)
        for _ in range(3):
            sink.write(None, np.zeros((8, 8, 3), np.uint8))
        sink.close()
        sink.close()                       # 幂等
        assert list(tmp_path.iterdir()) == []

    def test_local_sink_writes_jpg_for_image_source(self, tmp_path, image_dir):
        from od_platform.frame_source import SourceType, create_frame_source

        sink = LocalFileSink()
        sink.open(tmp_path, SourceType.IMAGE)
        for frame in create_frame_source(image_dir):
            sink.write(frame, frame.image)
        sink.close()

        jpgs = sorted(p.name for p in tmp_path.glob("*.jpg"))
        assert jpgs == ["img_0.jpg", "img_1.jpg", "img_2.jpg"]

    def test_local_sink_video_branch_uses_fps(self, tmp_path, monkeypatch):
        import cv2

        written = {}

        class _FakeWriter:
            def __init__(self, path, fourcc, fps, size):
                written.update(path=path, fps=fps, size=size, frames=0)

            def write(self, img):
                written["frames"] += 1

            def release(self):
                written["released"] = True

        monkeypatch.setattr(cv2, "VideoWriter", _FakeWriter)
        monkeypatch.setattr(cv2, "VideoWriter_fourcc", lambda *a: 0)

        from od_platform.frame_source import SourceType

        class _Info:
            fps = 12.0
            filename = "v.mp4"
            frame_index = 0

        class _Frame:
            info = _Info()

        sink = LocalFileSink()
        sink.open(tmp_path, SourceType.VIDEO)
        for _ in range(3):
            sink.write(_Frame(), np.zeros((32, 48, 3), np.uint8))
        sink.close()

        assert written["path"].endswith("output.mp4")
        assert written["fps"] == 12.0
        assert written["size"] == (48, 32)
        assert written["frames"] == 3 and written["released"] is True


# ============================================================
# 端到端 service(假模型)
# ============================================================
class TestInferServiceE2E:
    def _run(self, image_dir, runs_dir, name, **kwargs):
        hooks = kwargs.pop("hooks", None)
        return infer_yolo(
            cli_args={"source": str(image_dir), "model": "fake.pt",
                      "experiment_name": name, **kwargs.pop("cli_extra", {})},
            hooks=hooks,
            **kwargs,
        )

    def test_full_run_outputs_and_audit(self, image_dir, runs_dir):
        seen_frames, progress, done = [], [], []
        hooks = InferHooks(
            on_frame=lambda e: seen_frames.append(e.n_detections),
            on_progress=lambda e: progress.append(e.frame_idx),
            on_complete=lambda r: done.append(r.success),
            progress_interval_frames=1,
        )
        res = self._run(image_dir, runs_dir, "e2e", hooks=hooks, cli_extra={"save": True})

        assert res.success is True and res.error is None
        assert res.stats["frames"] == 3
        assert res.stats["detections"] == 3
        assert res.stats["per_class"] == {"tumor": 3}
        assert len(seen_frames) == 3 and len(progress) == 3 and done == [True]

        # 落盘 + 审计
        assert len(list(res.output_dir.glob("*.jpg"))) == 3
        assert res.audit_path is not None and res.audit_path.exists()
        audit = json.loads(res.audit_path.read_text(encoding="utf-8"))
        assert audit["mode"] == "infer"
        assert audit["stats"]["frames"] == 3
        assert audit["result_summary"]["beautified"] is True
        assert "config" in audit and "merger" in audit and "pipeline" in audit

    def test_output_dir_autoincrements(self, image_dir, runs_dir):
        first = self._run(image_dir, runs_dir, "dup")
        second = self._run(image_dir, runs_dir, "dup")
        assert first.output_dir.name == "dup"
        assert second.output_dir.name == "dup2"

    def test_cancelled_before_start_does_nothing(self, image_dir, runs_dir):
        token = CancelToken()
        token.cancel()
        res = self._run(image_dir, runs_dir, "cancel", cancel_token=token)
        assert res.success is True and res.stats["frames"] == 0

    def test_beautify_off_falls_back_to_plot(self, image_dir, runs_dir):
        res = self._run(image_dir, runs_dir, "noviz", beautify=False, cli_extra={"save": False})
        assert res.success is True and res.stats["frames"] == 3
        audit = json.loads(res.audit_path.read_text(encoding="utf-8"))
        assert audit["result_summary"]["beautified"] is False

    def test_missing_source_never_raises(self, runs_dir):
        res = infer_yolo(cli_args={"model": "fake.pt"})
        assert res.success is False
        assert "未指定推理输入源" in (res.error or "")

    def test_caller_sink_is_used(self, image_dir, runs_dir):
        class _CountingSink(OutputSink):
            def __init__(self):
                self.n = 0

            def open(self, output_dir, source_type):
                self.output_dir = output_dir

            def write(self, frame, annotated):
                self.n += 1

            def close(self):
                pass

        sink = _CountingSink()
        res = self._run(image_dir, runs_dir, "sink", output_sink=sink)
        assert res.success is True and sink.n == 3
        assert not list(res.output_dir.glob("*.jpg")), "自定义 sink 不该写本地文件"


# ============================================================
# CLI
# ============================================================
class TestInferCli:
    def test_cli_args_mapping_excludes_own_switches(self, image_dir):
        from od_platform.cli.infer import _build_parser, _ns_to_cli_args

        ns = _build_parser().parse_args([
            "--source", str(image_dir), "--model", "fake.pt",
            "--conf", "0.5", "--no-save", "--no-viz", "--warmup", "1",
        ])
        args = _ns_to_cli_args(ns)
        assert args == {"source": str(image_dir), "model": "fake.pt",
                        "conf": 0.5, "save": False}
        for own in ("no_viz", "no_hud", "warmup", "yaml", "pipeline_yaml", "log_level"):
            assert own not in args

    def test_main_missing_source_returns_1(self, tmp_path, monkeypatch):
        from od_platform.cli import infer as cli_infer

        monkeypatch.setattr(cli_infer, "get_logger", lambda *a, **kw: None)
        monkeypatch.setattr(service_module, "log_device_info", lambda *a, **kw: {})
        assert cli_infer.main(["--model", "fake.pt"]) == 1

    def test_main_success_returns_0(self, image_dir, runs_dir, monkeypatch):
        from od_platform.cli import infer as cli_infer

        monkeypatch.setattr(cli_infer, "get_logger", lambda *a, **kw: None)
        rc = cli_infer.main(["--source", str(image_dir), "--model", "fake.pt",
                             "--no-save", "--name", "cli_run"])
        assert rc == 0
