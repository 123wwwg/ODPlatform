#!/usr/bin/env python
# @FileName  : make_disaster_data.py
# @Function  : 为 odp-reset 验证造测试现场(跨平台,无需管理员权限)
#
# 为什么用 Python 而不是文档里的 .ps1:
#   文档 PowerShell 版用 `fsutil file createnew` 生成 2GB 大文件,
#   而 fsutil 需要管理员权限。改用 Python 的 seek+write,
#   任何普通终端都能跑,且 NTFS 不会为中间的空洞实际分配磁盘。
"""造一批 reset 验证用的假数据。"""

import shutil
import sys
from pathlib import Path

# Windows 控制台/管道默认是 GBK(cp936),emoji 会直接 UnicodeEncodeError。
# 显式把 stdout 切成 UTF-8,让脚本在任何终端都能跑。
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

REPO_ROOT = Path(__file__).resolve().parent.parent

RAW = REPO_ROOT / "data" / "raw" / "precious_dataset"
PROCESSED = REPO_ROOT / "data" / "processed" / "demo"
RUNS = REPO_ROOT / "runs" / "exp_2026_05_10"
TRAINED = REPO_ROOT / "models" / "trained"
LOGDIR = REPO_ROOT / "apps" / "platform" / "logging" / "training" / "2026-05-10"

BIG_FILE_SIZE = 1200 * 1024 * 1024  # 1.2 GiB, > 1 GiB 触发"可能需要一会"预警


def _clean() -> None:
    """清残骸(精准清理,不用 git checkout)"""
    for p in (RAW, PROCESSED, RUNS, LOGDIR):
        shutil.rmtree(p, ignore_errors=True)
    for f in TRAINED.glob("*.pt"):
        f.unlink(missing_ok=True)


def main() -> int:
    print("🎬 准备测试现场...")
    _clean()

    # 1. data/raw/ —— 珍贵原始数据(reset 绝不能碰)
    for sub in ("images", "labels"):
        (RAW / sub).mkdir(parents=True, exist_ok=True)
    for i in range(1, 201):
        (RAW / "images" / f"img_{i}.jpg").write_text(f"fake image {i}", encoding="utf-8")
        (RAW / "labels" / f"img_{i}.txt").write_text("0 0.5 0.5 0.3 0.4", encoding="utf-8")
    print("  ✅ data/raw/precious_dataset/ — 400 个文件(模拟珍贵标注)")

    # 2. data/processed/ —— 划分后的派生数据集(reset 清理目标)
    for split, n in (("train", 120), ("val", 20), ("test", 20)):
        (PROCESSED / split).mkdir(parents=True, exist_ok=True)
        for i in range(1, n + 1):
            (PROCESSED / split / f"img_{i}.txt").write_text(f"img {i}", encoding="utf-8")
    print("  ✅ data/processed/demo/ — 160 个文件(模拟划分后的派生数据集)")

    # 3. runs/ —— 一个 >1GiB 的大文件
    RUNS.mkdir(parents=True, exist_ok=True)
    big = RUNS / "best.pt"
    with big.open("wb") as f:
        f.seek(BIG_FILE_SIZE - 1)
        f.write(b"\0")
    print(f"  ✅ runs/{RUNS.name}/best.pt — {BIG_FILE_SIZE / 1024 ** 3:.2f} GiB")

    # 4. runs/ —— 5000 个小文件
    tb = RUNS / "tb_logs"
    tb.mkdir(parents=True, exist_ok=True)
    for i in range(1, 5001):
        (tb / f"event.{i}").write_text(f"step {i} loss 0.{i}", encoding="utf-8")
    print("  ✅ runs/exp_2026_05_10/tb_logs/ — 5000 个小文件")

    # 5. models/trained/ —— 训练产出的权重
    TRAINED.mkdir(parents=True, exist_ok=True)
    for i in range(1, 4):
        (TRAINED / f"model_v{i}.pt").write_text(f"fake weights {i}", encoding="utf-8")
    print("  ✅ models/trained/ — 3 个训练权重")

    # 6. 已存在的业务日志
    LOGDIR.mkdir(parents=True, exist_ok=True)
    for i in range(1, 51):
        (LOGDIR / f"run-{i}.log").write_text(f"training run {i} log", encoding="utf-8")
    print("  ✅ apps/platform/logging/ — 50 份训练日志")

    print("🎬 测试现场准备就绪(总文件约 5810,名义约 1.2 GiB)。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
