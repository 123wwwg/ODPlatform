# ODPlatform D4 数据验证 —— 执行记录

> 对应讲义：《D4 数据验证（精简实操版）》，1808 行
> 执行日期：2026-10-23
> 代码提交：`17bb53a` → `cfcd35e`（6 次）

---

## 一、交付物（26 个新文件 + 2 处增量）

```
apps/platform/src/od_platform/
├── common/
│   ├── constants.py            ← 增量：13 个质检阈值（PAIR_* / BBOX_* / DEGENERATE_* ...）
│   └── paths.py                ← 增量：VALIDATION_RUNS_DIR + validation_run_dir()
├── data_validation/            ← 新增子系统（只读）
│   ├── __init__.py
│   ├── registry.py             ← CheckSeverity(rank) / CheckResult / CheckContext / @check
│   ├── labels.py               ← parse_label_line：全框架唯一权威
│   ├── snapshot.py             ← DatasetSnapshot + SplitStats（结构层 + 内容层）
│   ├── service.py              ← run_all_checks + validate_dataset（单 check 崩溃护栏）
│   ├── report.py               ← ValidationReport：logger / json / csv(utf-8-sig)
│   └── checks/
│       ├── __init__.py
│       ├── _lineage.py         ← 内部件：从 yaml.odp_meta 加载 D3 契约
│       ├── yaml_schema.py          pair_existence.py
│       ├── fingerprint_match.py    manifest_lineage.py
│       ├── label_format.py         bbox_within_image.py
│       ├── box_geometry.py         duplicate_annotations.py
│       ├── annotation_coverage.py  orphan_labels.py
│       ├── stem_collision.py       split_presence.py
│       ├── split_uniqueness.py     class_presence.py
│       └── class_balance.py
└── cli/validate_data.py        ← odp-validate（退出码 0/1/2）

apps/platform/tests/conftest.py            ← 8 个夹具（全部基于真实产物拷贝）
apps/platform/tests/test_data_validation.py ← 10 项回归测试
```

---

## 二、验证结果

### 2.1 干净集：15 项 check 真实输出 ✅

```text
数据质检报告 run_id=20261023-082449  总评: WARNING(1.46s)
[PASS   ] annotation_coverage: 全部 63 张图均有有效标注
[WARNING] bbox_within_image: 1/75 个框出界(1.3%)— 少量,建议修源数据
[PASS   ] box_geometry: 全部 75 个框几何正常(无退化框/极端宽高比)
[PASS   ] class_balance: 各类别实例数未见显著失衡
[PASS   ] class_presence: 2 个类别在各划分均有出现
[PASS   ] duplicate_annotations: 无完全重复的标注行
[PASS   ] fingerprint_match: 契约指纹三方一致
[PASS   ] label_format: 全部 75 行标签结构与取值合法
[PASS   ] manifest_lineage: 63 个样本逐条核验通过
[PASS   ] orphan_labels: 无孤儿标签
[PASS   ] pair_existence: 全部 63 张图均有标签
[INFO   ] split_presence: test 划分共 6 张,低于 30,评估方差偏大(提示)
[PASS   ] split_uniqueness: 全部 63 个样本分属唯一 split
[PASS   ] stem_collision: 无同名多扩展名冲突
[PASS   ] yaml_schema: yaml 结构合法
契约指纹: 08c961623071605a5b0d17b14f94d3fe9f97a12a3e936d5f1858720caa43d275
样本数: 63  策略: stratified_multilabel  种子: 42
exit=1
```

**关键闭环**：`bbox_within_image` 抓到的 1/75 越界框，正是 D3 在 `make_demo.py` 里
故意埋在 `c_050.xml` 的 `xmax=700 > 640`。跨两课的埋雷—捕获链条成立。

### 2.2 契约对账：篡改一行 → exit 2 ✅

```powershell
# 往 data/processed/demo/labels/train/c_000.txt 追加一行
odp-validate apps/platform/configs/datasets/demo.yaml --no-report
# 总评: ERROR(0.12s)
# [ERROR  ] manifest_lineage: 契约核验失败: changed=1 moved=0 missing=0
#          —— 与 D3 产出不一致,重跑 odp-transform 或查谁动了 processed
# exit=2
```

**恢复**：重跑 `odp-transform` → 指纹仍为 `08c9616...`（幂等），质检回到 `总评: WARNING` / `exit=1`。

### 2.3 三项工具 ✅

```text
ruff check .                    → All checks passed!
mypy apps/platform/src          → Success: no issues found in 61 source files
pytest apps/platform/tests -q   → 17 passed in 5.36s（D3 的 7 项 + D4 的 10 项）
```

---

## 三、为通过工具链所做的修正

### 3.1 ruff：125 个 → 0（全部自动修复）

`--fix` 一次清零，均为 `UP006/UP035`（`Dict/List/Tuple` → 内置泛型）、
`UP045`（`Optional[X]` → `X | None`）、`UP009`（多余 coding 声明）。

### 3.2 mypy：19 个 → 0

| 文件 | 问题 | 修正 |
|---|---|---|
| `fingerprint_match.py` | `load_manifest_from_yaml` 返回 `SplitManifest \| None`，`if err:` 无法让 mypy 收窄 | `if err or manifest is None:` |
| `manifest_lineage.py` | 同上 + `lbl = disk.get(...)` 与循环变量 `lbl: Path` 类型冲突 | 同上，并把局部变量改名 `found` |

> 根因：`_lineage.py` 的返回类型是 `Tuple[Optional[SplitManifest], Optional[str], dict]`，
> 两者的非空性没有类型层面的关联。要么在调用处显式收窄，要么把返回值改成
> `Union[tuple[SplitManifest, None, dict], tuple[None, str, dict]]`。本次选前者（改动最小）。

---

## 四、设计要点

1. **只读纪律**：15 个 check 全部零写操作；发现问题改源头或重跑 D3，质检永不"顺手修一下"。
2. **分级而非二元**：`CheckSeverity.rank()` 支持"全场最严"聚合，退出码 ERROR→2 / WARNING→1 / PASS·INFO→0。
3. **判断与解析分离**：`labels.py` 只说"这行是什么"（`kind`），严不严重由 check 定 ——
   所以 `label_format` 报 ERROR 的行，几何类 check 只记 `skipped_structure_errors`，不重复报。
4. **契约不互信**：D4 不 import 任何 D3 业务模块，只认 `common/lineage.py`；
   自己重算指纹、自己重读每个标签算 sha256。
5. **快照分层**：结构层（路径清单）+ 内容层（`SplitStats` 有界聚合）。
   统计类 check 零 I/O，几何类 check 按需重读 —— 内存占用与样本数无关。
6. **唯一宽异常**：`service._safe_run_one` 是全场唯一的 `except Exception`，
   单 check 崩溃降级为 ERROR 结果，不拖垮整场。
7. **阈值进 constants**：check 里没有魔法数，`details.thresholds` 把判定依据一并写进报告。
8. **报告三出口**：logger（人看）/ json（机器读）/ csv（`utf-8-sig`，Excel 直接开不打码）。

---

## 五、D5 状态

| 讲义 | 行数 | 状态 |
|---|---|---|
| D3 数据流水线 | 1946 | ✅ 完成 |
| D4 数据验证 | 1808 | ✅ 完成 |
| D5 运行配置 | 4295 | ⏳ 未开始（含 base/train/val/infer + loaders/merger/generator） |

D5 可直接复用本轮产物：`configs/datasets/demo.yaml` 已通过 15 项质检
（唯一 WARNING 是刻意埋的越界框，不影响训练链路验证）。
