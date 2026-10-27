"""隔离真实数据执行浏览器冒烟测试；额外安装 playwright 后运行。

python scripts/check_data_web.py --output-dir runs/web_data_smoke
支持本机 Edge / Chrome，或已安装的 Playwright Chromium。
只对无关的模型、训练、识别 API 提供测试响应，所有数据工程 API 使用真实后端。
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
import threading
from contextlib import ExitStack
from pathlib import Path
from unittest.mock import patch
from urllib.parse import urlsplit
from wsgiref.simple_server import WSGIRequestHandler, make_server

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "apps/web-backend"), str(ROOT / "apps/platform/src")]
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")


class QuietHandler(WSGIRequestHandler):
    def log_message(self, *_args):
        pass


def main() -> None:
    import django
    from PIL import Image
    from playwright.sync_api import expect, sync_playwright

    django.setup()
    from defect.data_jobs import data_jobs
    from django.core.wsgi import get_wsgi_application

    from od_platform.common import paths, stamp
    from od_platform.data_pipeline.orchestrator import DatasetPipeline
    from od_platform.data_validation.service import validate_dataset

    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, default=ROOT / "runs/web_data_smoke")
    args = parser.parse_args()
    output = args.output_dir.resolve()
    output.mkdir(parents=True, exist_ok=True)
    errors = []
    with tempfile.TemporaryDirectory(prefix="odp_browser_") as temporary, ExitStack() as stack:
        root = Path(temporary)
        stack.enter_context(
            patch.multiple(
                paths,
                ROOT_DIR=root,
                RAW_DATA_DIR=root / "data/raw",
                PROCESSED_DATA_DIR=root / "data/processed",
                RUNS_DIR=root / "runs",
                DATASET_CONFIGS_DIR=root / "apps/platform/configs/datasets",
                VALIDATION_RUNS_DIR=root / "runs/data_validation",
            )
        )
        stack.enter_context(patch.object(stamp, "LINEAGE_DIR", root / "runs/lineage"))
        raw = paths.raw_dataset_root("web_smoke")
        (raw / "images").mkdir(parents=True)
        (raw / "labels").mkdir()
        for number in range(24):
            Image.new("RGB", (64, 48), (70, 150, 130)).save(raw / "images" / f"sample_{number}.jpg")
            (raw / "labels" / f"sample_{number}.txt").write_text(
                "0 0.5 0.5 0.2 0.2\n", encoding="utf-8"
            )
        DatasetPipeline("web_smoke", "yolo", classes=["paper"]).run()
        validate_dataset(
            paths.dataset_yaml_path("web_smoke"), run_id="browser-baseline", compare_previous=False
        )
        image = next(paths.dataset_processed_dir("web_smoke").glob("images/train/*.jpg"))
        original = image.read_bytes()
        image.write_bytes(b"broken image")
        server = make_server("127.0.0.1", 0, get_wsgi_application(), handler_class=QuietHandler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            with sync_playwright() as playwright:
                executable = next(
                    (
                        str(path)
                        for path in (
                            Path("C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe"),
                            Path("C:/Program Files/Google/Chrome/Application/chrome.exe"),
                        )
                        if path.is_file()
                    ),
                    None,
                )
                browser = playwright.chromium.launch(headless=True, executable_path=executable)
                context = browser.new_context(
                    viewport={"width": 1440, "height": 1080}, accept_downloads=True
                )
                page = context.new_page()
                page.on("pageerror", lambda error: errors.append(str(error)))

                def unrelated_api(route):
                    endpoint = urlsplit(route.request.url).path
                    fixtures = {
                        "/api/dashboard/": {
                            "defects": {},
                            "recognition": {},
                            "model": {},
                            "dataset": {},
                        },
                        "/api/model/": {"status": "not_found"},
                        "/api/recognition/": [],
                        "/api/video-recognition/": [],
                        "/api/training/": {"status": "idle", "progress": 0, "logs": []},
                    }
                    if endpoint in fixtures:
                        route.fulfill(
                            status=200,
                            content_type="application/json",
                            body=json.dumps(fixtures[endpoint]),
                        )
                    else:
                        route.continue_()

                page.route("**/api/**", unrelated_api)
                page.goto(f"http://127.0.0.1:{server.server_port}/?module=understanding")
                expect(page.get_by_role("heading", name="数据工程工作台")).to_be_visible()
                expect(page.locator(".dataset-select select")).to_have_value("web_smoke")
                expect(page.locator(".quality-check")).to_have_count(16)
                page.get_by_role("button", name="运行 16 项质检", exact=True).click()
                expect(page.get_by_role("progressbar")).to_be_visible()
                page.screenshot(path=str(output / "data-task-running.png"))
                expect(page.get_by_role("heading", name="质检完成", exact=True)).to_be_visible(
                    timeout=30000
                )
                expect(page.get_by_role("button", name="ERROR 1", exact=True)).to_be_visible(
                    timeout=10000
                )
                broken_run_id = page.locator(".report-select select").input_value()
                page.get_by_role("button", name="ERROR 1", exact=True).click()
                expect(page.locator(".quality-check")).to_have_count(1)
                expect(page.locator(".quality-check summary")).to_contain_text("图片完整性")
                page.locator(".quality-check summary").click()
                expect(page.locator(".check-evidence")).to_contain_text(image.name)
                page.locator(".quality-report").screenshot(
                    path=str(output / "data-quality-report.png")
                )
                with page.expect_download() as download:
                    page.get_by_role("link", name="下载对比 CSV", exact=True).click()
                download.value.save_as(output / "comparison.csv")
                assert (output / "comparison.csv").read_bytes().startswith(b"\xef\xbb\xbf")

                page.locator(".report-select select").select_option("browser-baseline")
                expect(page.get_by_role("button", name="ERROR 0", exact=True)).to_be_visible()
                page.locator(".data-settings > summary").click()
                page.get_by_label("对比方式").select_option("specific")
                page.get_by_label("历史基线").select_option(broken_run_id)
                image.write_bytes(original)
                page.get_by_role("button", name="运行 16 项质检", exact=True).click()
                expect(page.get_by_role("heading", name="质检完成", exact=True)).to_be_visible(
                    timeout=30000
                )
                expect(page.locator(".comparison-group").filter(has_text="已修复")).to_be_visible(
                    timeout=10000
                )

                page.get_by_label("随机种子").fill("17")
                page.once("dialog", lambda dialog: dialog.accept())
                page.get_by_role("button", name="构建数据集", exact=True).click()
                expect(
                    page.get_by_role("heading", name="数据集构建完成", exact=True)
                ).to_be_visible(timeout=30000)
                page.locator(".data-workbench").screenshot(
                    path=str(output / "data-pipeline-controls.png")
                )
                import yaml

                config = yaml.safe_load(
                    paths.dataset_yaml_path("web_smoke").read_text(encoding="utf-8")
                )
                assert config["odp_meta"]["split"]["seed"] == 17
                for sample in page.locator(".sample-grid img").all():
                    sample.scroll_into_view_if_needed()
                    expect(sample).to_have_js_property("complete", True)
                    assert sample.evaluate("image => image.naturalWidth > 0"), (
                        "重建后的样本图片没有刷新"
                    )
                page.locator(".data-settings > summary").click()
                page.set_viewport_size({"width": 390, "height": 844})
                page.screenshot(path=str(output / "data-workbench-mobile.png"), full_page=True)
                assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth"), (
                    "小屏布局存在横向溢出"
                )
                assert not errors, errors
                print(
                    json.dumps(
                        {
                            "status": "passed",
                            "browser_errors": errors,
                            "verified": [
                                "real transform",
                                "live progress",
                                "16 checks",
                                "corrupt image",
                                "history baseline",
                                "resolved issue",
                                "report download",
                                "mobile layout",
                            ],
                            "artifacts": str(output),
                        },
                        ensure_ascii=False,
                    )
                )
                context.close()
                browser.close()
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=5)
            if data_jobs._process is not None:
                if data_jobs._process.poll() is None:
                    data_jobs._process.terminate()
                    data_jobs._process.wait(timeout=10)
                data_jobs._log.close()


if __name__ == "__main__":
    main()
