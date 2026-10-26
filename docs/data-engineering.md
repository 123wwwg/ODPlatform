# D3 / D4 数据工程协作说明

在仓库根目录执行下列命令。只开发数据功能时可安装轻量依赖；无需安装 torch 或下载模型。

```powershell
python -m pip install -r requirements-data-dev.txt
python -m pre_commit install
python -m pytest -c pyproject.toml apps/platform/tests/test_data_pipeline.py apps/platform/tests/test_data_validation.py apps/platform/tests/test_data_engineering.py apps/platform/tests/test_data_identity.py
```

已安装核心引擎的环境也可以使用 `python -m pip install -e "./apps/platform[dev]"`。
根目录和 `apps/platform` 内均配置了 pytest 源码发现路径；数据测试从零生成临时
VOC / COCO / YOLO / 残缺数据，临时目录中构建成品、manifest、历史报告及审计章。
不再要求预先执行 checkpoint 或准备本地演示集，也不改动真实 raw / processed。

pre-commit 使用当前 Python 环境内的 Ruff，自动整理暂存 Python 文件的 import、修复
可自动处理的 lint 问题并统一格式，规则继承根目录 `pyproject.toml`。自动修复后需重新
`git add`。可用 `python -m pre_commit run` 提前检查暂存文件；仓库其他模块尚有历史
风格问题，`--all-files` 会把这些也列出来。本次未批量改写其他成员的模块。
GitHub Actions 在 Windows / Ubuntu、Python 3.10 / 3.12 上自动运行数据回归测试。

## 流水线与核验进度

```powershell
odp-transform --dataset demo --format pascal_voc --split-strategy stratified_multilabel
odp-validate apps/platform/configs/datasets/demo.yaml
# 自动化日志可关闭进度条
odp-transform --dataset demo --format pascal_voc --no-progress
odp-validate apps/platform/configs/datasets/demo.yaml --no-progress
```

转换、类别发现、扫描、分层划分、标签哈希和图/标签复制按实际完成的样本更新进度，
显示总数、速度及预计剩余时间。D4 的快照扫描、检查总进度、图片解码、标签格式与
manifest 逐样本 SHA256 校验也有进度反馈。所有进度写到 stderr。

Python 调用默认安静，按需传 `DatasetPipeline(...).run(show_progress=True)` 或
`validate_dataset(..., show_progress=True)`。开关按运行上下文隔离，异常退出后恢复。
SHA256 流式分块读取；每次质检仍重新核验磁盘内容，保证可以发现被篡改的标签。

## 16 项质检与异常数据

保留原有 15 项检查，并新增 `image_integrity`。每张图片先执行 Pillow `verify()`，
再重开并 `load()` 实际解码像素，捕获空文件、伪造图片、截断、不可读和超大图片保护
异常；任一坏图为 ERROR，逐图继续检查，其预览数量受统一上限约束。
演示生成器现生成真实 640×480 JPEG，保留 `c_050` 的刻意越界标注供质检演示。
这些脚本用于新建或重建演示数据，不要对真实数据集运行生成器。

标签内容检查使用现有统一解析器：`label_format` 校验检测/分割列数、整数类别 ID、
`0 <= class_id < nc` 和 `[0, 1]` 归一化坐标。新增 NaN / Inf 拒绝逻辑，读取/编码
失败记录为结构化 ERROR。`bbox_within_image` 继续检查 `cx ± w/2`、`cy ± h/2`
是否越界，退化框由 `box_geometry` 提示。结构无效行不会进入几何检查。

退出码仍为：ERROR → 2，WARNING → 1，PASS / INFO → 0；不修改数据来消除问题。

## 本次与上次报告对比

```powershell
# 默认自动选相同 yaml 路径、数据根目录和 task 的最近有效报告
odp-validate apps/platform/configs/datasets/demo.yaml
# 指定某次基线
odp-validate apps/platform/configs/datasets/demo.yaml --compare-to runs/data_validation/<上次run_id>/report.json
# 禁用对比 / 只在终端显示，不写报告
odp-validate apps/platform/configs/datasets/demo.yaml --no-compare
odp-validate apps/platform/configs/datasets/demo.yaml --no-report
```

报告保存在 `runs/data_validation/<run_id>/`：`report.json` 包含 `comparison`，
`results.csv` 保留原有结果表，存在基线时另写带 UTF-8 BOM 的 `comparison.csv`。
日志显示新增、修复、变化和持续问题数。Python API 可传 `compare_to=Path(...)` 或
`compare_previous=False`。

对比粒度是**质检项**，INFO / WARNING / ERROR 均视为非通过项：

- `new_issues`：上次 PASS 或没有此检查，本次出现问题。
- `resolved_issues`：上次有问题，本次同一项 PASS。
- `changed_issues`：问题持续，但严重度、摘要或结构化证据变化；同级别数量变化也会记录。
- `unchanged_issues`：仍是相同的问题结果。
- `added_checks` / `removed_checks`：检测能力的增删；删除检查不会误记为修复。

首跑 `comparison` 为 null。自动选择会跳过损坏、缺少数据身份信息的旧版、其他数据集
和其他 task 的报告；显式指定无效或不匹配基线会报错。明细预览有界，因此不声称完成
所有问题样本的逐条新增/修复追踪。默认运行 ID 精确到微秒，显式重复 ID 拒绝覆盖。

## 从现有演示集升级

旧生成器的空图片现在会被正确识别为 ERROR。若使用的确为仓库演示数据，请先运行
对应的 `scripts/demo_data/make_*.py`，然后重跑 `odp-transform` 重建成品及契约。
真实数据集应修复源图片或标注后重跑流水线。
