# ODPlatform D3 数据流水线 —— 执行记录

> 对应讲义：《D3 数据流水线（精简实操版）》，1946 行
> 执行日期：2026-10-23
> 代码提交：`17140a8` → `28ea361`（8 次）+ yaml 提交 1 次，累计 26 次

---

## 一、交付物（25 个新文件 + 3 处增量）

```
apps/platform/src/od_platform/
├── common/
│   ├── constants.py            ← 新增：格式/任务/策略/阈值（无三方依赖）
│   ├── lineage.py              ← 新增：SampleLineage / SplitManifest / 契约指纹
│   ├── registry_utils.py       ← 新增：子模块自动发现
│   ├── refs.py                 ← 新增：名字 ↔ 路径解析
│   ├── run_context.py          ← 新增：runs/<subsystem>/<run_id>/ 审计目录
│   ├── paths.py                ← 增量：DATASET_CONFIGS_DIR + 3 个拼路径函数
│   └── string_utils.py         ← 增量：表格列放宽为 Sequence[object]
├── data_pipeline/              ← 新增子系统
│   ├── __init__.py
│   ├── report.py               ← 类别平衡报告（只读）
│   ├── orchestrator.py         ← DatasetPipeline 编排 + 覆盖率闸门
│   ├── convert/
│   │   ├── __init__.py
│   │   ├── registry.py         ← 注册表 + 能力声明 supported_tasks
│   │   ├── service.py          ← 能力门禁（门口拦一次）
│   │   └── converters/
│   │       ├── __init__.py
│   │       ├── _geometry.py    ← 归一化（内部工具，不被自动发现）
│   │       ├── pascal_voc.py   ← detect only
│   │       ├── coco.py         ← detect + segment
│   │       └── yolo.py         ← detect + segment（直通 + 路由校验）
│   └── split/
│       ├── __init__.py
│       ├── registry.py         ← 策略注册表 + requires_labels
│       ├── split_service.py    ← 依赖校验 + 组装参数包
│       ├── materializer.py     ← copy2 + 删除围栏 + 符号链接拒绝
│       ├── yaml_writer.py      ← Ultralytics yaml + odp_meta 合格证
│       └── strategies/
│           ├── __init__.py
│           ├── _common.py      ← 比例校验/三方计数/带种子洗牌
│           ├── random_split.py
│           └── stratified_multilabel.py   ← Sechidis 2011 简化实现
└── cli/transform_data.py       ← odp-transform（退出码 0/1/2）

apps/platform/tests/test_data_pipeline.py   ← 7 项回归测试
scripts/demo_data/{make_demo,make_coco_demo,make_yolo_demo,make_broken_demo}.py
```

---

## 二、验证结果

### 2.1 演示数据生成 ✅

| 数据集 | 图像 | 标注 | 埋的设计 |
|---|---|---|---|
| `demo`（VOC） | 63 | 75 | 12 张含稀有类 反光衣；`classes.txt` 乱序；`c_050` 埋越界框 |
| `demococo`（COCO） | 8 | 10 | 带 `segmentation` 多边形 |
| `demoyolo`（YOLO） | 6 | — | 5 列格式，无类名 |
| `broken`（VOC） | 10 | 1 | 覆盖率 10%，用于验证闸门 |

### 2.2 转换器注册表 ✅（懒加载自动发现生效）

```text
coco:        tasks=('detect', 'segment')
pascal_voc:  tasks=('detect',)
yolo:        tasks=('detect', 'segment')
```

### 2.3 端到端四条成功路径 ✅

| 命令 | 结果 | exit |
|---|---|---|
| `--dataset demo --format pascal_voc --split-strategy stratified_multilabel` | train 51 / val 6 / test 6 | 0 |
| `--dataset demococo --format coco` | 6 / 1 / 1 | 0 |
| `--dataset demococo --format coco --task segment --classes head 反光衣` | 6 / 1 / 1（指纹与原任务不同） | 0 |
| `--dataset demoyolo --format yolo --classes head 反光衣` | 5 / 1 / 0 | 0 |

**产物隔离**：`data/processed/` 下只有 `demo` / `demococo` / `demoyolo` —— 失败的数据集**没有留下半成品**。

### 2.4 两条失败路径 ✅

| 场景 | 报错 | exit |
|---|---|---|
| YOLO 不给 `--classes` | `yolo 格式不含类名,必须通过 options.classes 显式提供类别顺序` | **1** |
| `broken` 数据集 | `图像-标注覆盖率 10.0% 低于硬阈值 50%...疑似标注导出中断` | **1** |

### 2.5 yaml 合格证 + 幂等 ✅

```text
yaml: apps/platform/configs/datasets/demo.yaml
names: {0: head, 1: 反光衣}  nc: 2
strategy: stratified_multilabel  counts: {'train': 51, 'val': 6, 'test': 6}
fingerprint: 08c9616b...
train: images=51 labels=51
val:   images=6  labels=6
test:  images=6  labels=6
```

**幂等验证**：同参数重跑，`contract_fingerprint` 完全一致（`08c9616b...`）——
证明"划分配方 + 样本内容"确定，与时间戳无关。

> 分层划分确实把 12 张稀有类分散到了三个 split（`test_stratified_rescues_rare_class` 断言每个 split ≥1 张）。

### 2.6 三项工具 ✅

```text
ruff check .                    → All checks passed!
mypy apps/platform/src          → Success: no issues found in 37 source files
pytest apps/platform/tests -q   → 7 passed in 0.23s
```

---

## 三、为通过工具链所做的修正（真实清单）

### 3.1 ruff：134 个 → 0

`ruff check . --fix` 自动修掉 132 个，主要是 `UP006/UP035`（`Dict`/`List`/`Tuple` → `dict`/`list`/`tuple`）、
`UP045`（`Optional[X]` → `X | None`）、`UP009`（多余的 `# -*- coding:utf-8 -*-`）。
剩 2 个手工改：

| 文件 | 规则 | 修正 |
|---|---|---|
| `random_split.py` | F841 `test_rate` 未使用 | 改为 `validate_rates(...)` 只取副作用 |
| `yaml_writer.py` | C416 字典推导多余 | `{i: n for i, n in enumerate(classes)}` → `dict(enumerate(classes))` |

### 3.2 mypy：20 个 → 0

| 文件 | 问题 | 修正 |
|---|---|---|
| `run_context.py` | `__exit__ -> bool` 让 mypy 怀疑会吞异常，连带 `orchestrator.run` 报 Missing return | `-> Literal[False]` |
| `string_utils.py` | 表格列声明 `list[str]`，但实际传了 `int` 类 id | `Sequence[object]` |
| `pascal_voc.py` | `size` / `bndbox` 可能为 `None` | 显式判空抛 `ValueError` + `findtext(..., "0")` 带默认值 |
| `stratified_multilabel.py` | `fold_label_counts` 缺泛型注解；`dict[str,int]` 传给 `dict[str,float]`（dict 不变） | `list[Counter[str]]`；参数改 `Mapping[str, float]`（协变） |
| `yaml_writer.py` | 缺 `yaml` 类型存根 | `pip install types-PyYAML` |

### 3.3 讲义代码的一个文案 bug

`report.py` 的稀有类预警原文传了 `report.min_split_rate`（0.1），日志会打印
"期望样本量低于 0.1"——而表格里实际期望是 1.2、阈值是 3.0，数字对不上。

**修正**：`BalanceReport` 增加 `warn_min_expected` 字段，预警打印真实阈值 `3.0`。

---

## 四、设计要点（本课真正要记住的）

1. **注册表 + 装饰器自注册 + 懒加载发现**：新增格式/策略只加一个文件，注册表代码零改动。
2. **能力声明而非能力猜测**：`supported_tasks` 在注册时声明，门禁在 `service.py` 统一拦，
   转换器内部只写自己会赢的分支（COCO 写 detect/segment 两支，VOC 只写 detect）。
3. **参数包 `*Options`**：横切参数变化时函数签名不动（`ConvertOptions` / `SplitOptions`）。
4. **前置闸门在编排层**：覆盖率检查放在转换**之前**，坏数据不进流水线。
5. **契约指纹**：`排序后的样本 sha256 + 配方`，对集合序免疫、对时间戳免疫 —— 这是"可复现"的机器可读证明。
6. **物化三原则**：`copy2` 不用 hardlink；删除前 `_assert_within` 围栏；符号链接一律拒绝。
7. **三处产物分家**：`processed/`（生产）、`runs/`（审计 manifest）、`configs/`（yaml 合格证）。

---

## 五、D4 / D5 状态

| 讲义 | 行数 | 状态 |
|---|---|---|
| D3 数据流水线 | 1946 | ✅ 完成并全绿 |
| D4 数据验证 | 1417 | ⏳ 未开始（依赖 D3 的 yaml + manifest，接口已就绪） |
| D5 运行配置 | 4295 | ⏳ 未开始 |

D4 可直接消费本次产物：
- `apps/platform/configs/datasets/demo.yaml`（含 `odp_meta.contract_fingerprint` / `manifest_path`）
- `runs/data_pipeline/<run_id>/manifest.json`（含全量样本 sha256，用于验账）
