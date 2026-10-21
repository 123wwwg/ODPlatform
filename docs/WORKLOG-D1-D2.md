# ODPlatform D1 + D2 执行记录（工作日志）

> 对应讲义：《D1 项目初始化（精简实操版）》《D2 项目重置（精简实操版）》
> 执行日期：2026-10-21
> 执行方式：自动执行 + 逐步验证，文中数据均来自真实命令输出

---

## 一、环境基线

| 项 | 值 |
|---|---|
| 项目路径 | `D:\大三实训课\ODPlatform` |
| 虚拟环境 | `ODPlatform\.venv`（Python 3.14.6，venv 非 conda） |
| 包 | `od-platform 0.1.0`（editable，`pip install -e ./apps/platform --no-deps`） |
| 工具 | ruff 0.17.1 / mypy 2.4.0 / pytest 9.1.1 |
| git | 2.53.0.windows.1，分支 `main`，共 **17 次提交**（D1 11 + D2 6） |
| 运行依赖 | colorlog / psutil / pyyaml / pydantic（已装） |
| **未装** | torch / ultralytics（见"踩坑 1"，属软依赖，不影响 D1/D2 功能） |

---

## 二、D1 项目初始化 —— 11 次提交落地

```
cbb534e docs: add ADR-001 documenting Monorepo decision
b777112 docs: add platform README + placeholder READMEs for future apps
dbca934 feat: add workspace-level pyproject.toml with shared tool config
26bb132 feat(platform): add pyproject.toml (hatchling) with odp-init entry-point
c8ded00 feat(cli): add init_project.py to bootstrap workspace
1f8bd66 feat(common): add performance_utils.py with @time_it decorator
8429bf7 feat(common): add system_utils.py for environment snapshot
0a2d210 feat(common): add string_utils.py for CJK-aware text alignment
ff161ab feat(common): add logging_utils.py with colored console + file output
2429b66 feat(common): add paths.py with marker-file ROOT_DIR + APP_DIR
b4dd8f8 chore: initial commit with .gitignore + .odp-workspace marker
```

### 2.1 交付物清单

| 层 | 文件 | 职责 |
|---|---|---|
| 根标记 | `.odp-workspace` | marker file，`paths.py` 向上查找定位仓库根 |
| 根配置 | `pyproject.toml` | **只有 `[tool.*]`**，不是包、不被安装，全仓共用 ruff/mypy/pytest 规则 |
| 端配置 | `apps/platform/pyproject.toml` | hatchling 可安装包 + `odp-init` 入口 + 动态版本 |
| 基础层 | `common/paths.py` | 路径真相源：ROOT_DIR / APP_DIR / 共享与私产分离 |
| | `common/logging_utils.py` | 根 logger 装配，彩色控制台 + 文件双 handler，幂等 |
| | `common/string_utils.py` | CJK 显示宽度、表格对齐（中文占 2 列） |
| | `common/system_utils.py` | 环境快照（torch/ultralytics 为软依赖） |
| | `common/performance_utils.py` | `@time_it` 装饰器，支持多轮平均与运行期取名 |
| 入口层 | `cli/init_project.py` | 装配 logger → 快照 → 建目录 → 查 raw → 表格汇总 |
| 过渡 | `scripts/init_project.py` | 装包前的 `sys.path` 桥接入口 |
| 文档 | `docs/architecture/ADR-001-monorepo.md` + 8 份占位 README | — |

### 2.2 验证结果

```text
$ python -c "import od_platform; print(od_platform.__version__)"
0.1.0

$ Get-Command odp-init         # → .venv\Scripts\odp-init.exe

$ odp-init
======================== 检查并创建项目核心目录 ========================
成功创建: data\raw
成功创建: data\processed
成功创建: apps\platform\configs
成功创建: apps\platform\tests
目录已存在: data / runs / models / models\pretrained / models\trained
目录已存在: apps\platform\logging / scripts / docs
======================== 项目初始化汇总 =========================
（按显示宽度对齐的 目录|状态 双列表）
性能报告: '项目初始化' 执行 1 次 ,  耗时: 137.288 毫秒
```

| 检查项 | 命令 | 结果 |
|---|---|---|
| 包可 import | `python -c "import od_platform"` | ✅ 0.1.0 |
| 命令入口 | `Get-Command odp-init` | ✅ `.venv\Scripts\odp-init.exe` |
| marker 定位 | `odp-init` 输出的 `项目根目录` | ✅ 指向仓库根 |
| 目录创建 | `odp-init` | ✅ 12 个目录，幂等（复跑全"已存在"） |
| ruff | `ruff check .` | ✅ All checks passed |
| mypy | `mypy apps/platform/src` | ✅ no issues in 11 source files |

---

## 三、D2 项目重置 —— 6 次提交落地

```
14f0524 chore: add test-data generator for reset verification
251a655 chore: bump mypy target to 3.12 (shutil.rmtree onexc)
a1a2c16 feat(platform): register odp-reset console script
6c72d04 feat(cli): add reset_project.py with dry-run + confirmation + progress + audit
78e8577 chore: gitignore .odp-meta/ (local meta-tool history)
2854370 feat(common): add reset target list, protection mechanism and META_DIR in paths.py
```

### 3.1 三道安全设计（全部落地）

| 层 | 实现 | 验证 |
|---|---|---|
| 白名单 | `get_dirs_to_reset()` 只列 4 个运行时目录 | ✅ 绝不从 init 清单反推 |
| 黑名单兜底 | `PROTECTED_DIRS` + `is_protected()` 双向检查（含"祖先"判定） | ✅ ROOT_DIR 也删不掉 |
| 默认安全 | 默认 dry-run；`--yes` 才删；需手打 `RESET`；`--force` 供 CI | ✅ 见 3.3 |

**元数据命名空间**：`.odp-meta/logs/reset_project/` 存 reset 自身审计日志，永不被 reset 清理——破解"自指 bug"。

### 3.2 造测试现场

`scripts/make_disaster_data.py`（Python 版，替代文档的 `fsutil` 方案）：

- `data/raw/precious_dataset/` 400 个文件（**reset 绝不该碰**）
- `data/processed/demo/` 160 个文件
- `runs/exp_2026_05_10/best.pt` **1.17 GiB**
- `runs/exp_2026_05_10/tb_logs/` 5000 个小文件
- `models/trained/` 3 个权重
- `apps/platform/logging/` 50 份日志

### 3.3 三种模式验证

**模式 1 —— 默认 dry-run ✅ 完全通过**

```text
======================= 📋 [DRY-RUN] 计划如下(未实际删除) ========================
目录                                           文件数           大小
--------------------------------------------------------------------
data\processed                                    160          954 B
runs                                             5002       1.17 GiB
models\trained                                      4          326 B
apps\platform\logging                              52      22.10 KiB
--------------------------------------------------------------------
【合计】                                         5218       1.17 GiB

✅ 以下重要目录【不会】被动:
  - 原始数据: data\raw/
  - 预训练权重: models\pretrained/
  - 所有代码、文档、配置(进 git 的)
💡 这是 dry-run(默认行为)。要真正执行删除,请加 --yes:
```

**模式 2 —— `--yes` 交互确认 ✅ 拒绝路径通过**

| 输入 | 结果 |
|---|---|
| 小写 `reset` | ❌ 用户取消，未执行删除（数据完好） |
| 大写 `RESET` | ✅ 进入删除流程 |

**模式 3 —— `--yes --force` 部分完成 ⚠️ 见第四节**

- `[1/4] data\processed (954 B, 160 个文件)` → ✅ 已删除（真实生效）
- `[2/4] runs (1.17 GiB, 5002 个文件)——这可能需要一会...` → 触发大目录预警 ✅，但删除被**执行环境的删除守卫**中断

### 3.4 审计追踪

```
.odp-meta/logs/reset_project/   共 6 份日志
reset-project_20261021-233236-55471.log
reset-project_20261021-233303-07840.log
...
```

日志内含完整审计上下文：

```text
审计: user=王刚  pid=36636  git=cbb534e76077236b852e5acb56621a2385dccb3b
审计: cwd=D:\大三实训课\ODPlatform
审计: argv=D:\大三实训课\ODPlatform\.venv\Scripts\odp-reset --yes --force
```

`data/raw/precious_dataset/` 400 个文件在多次 delete 尝试后**始终完好** —— 白名单设计生效。

---

## 四、⚠️ 唯一未在本次自动化中完成的一步

**真实批量删除被 IDE 的 Safe Delete 守卫拦截**，不是代码问题：

```text
[safe-delete][SAFE_DELETE_BULK_GUARD_ERROR] guard exited with 2
Remove-Item : Safe delete could not verify this bulk deletion. Nothing was deleted.
...
File "...\genie\out\vendor\shim\sitecustomize.py", line 1205, in _flush_bulk_pending
    result.stderr.strip()
AttributeError: 'NoneType' object has no attribute 'strip'
```

即：IDE 注入的 `sitecustomize.py` 把 `shutil.rmtree` 改写成"先转回收站"，其批量守卫程序自身崩了，导致 `runs` / `models/trained` / `apps/platform/logging` 三个目录未删。

**这是环境级保护，不做绕过。请在你自己的终端补跑一次**（普通 PowerShell 不加载该守卫）：

```powershell
cd d:\大三实训课\ODPlatform
.venv\Scripts\Activate.ps1
odp-reset                 # 先看 dry-run 计划
odp-reset --yes           # 手打 RESET 执行
```

预期：`完成: 成功 4 个,失败 0 个`，且 `data/raw/precious_dataset/` 仍在。

> 顺带说明：这个拦截本身正是 D2 想教的东西——**危险操作周围永远该有守卫**。守卫拦下你，不一定是坏事。

---

## 五、踩坑记录（真实发生）

### 坑 1｜torch / ultralytics 未安装
Python 3.14 安装 torch 2.x 需下载数 GB 且轮子兼容性不确定。改用:
```powershell
pip install colorlog psutil pyyaml pydantic
pip install -e "./apps/platform" --no-deps
```
`system_utils.py` 的软依赖设计正好兜住——环境快照显示 `PyTorch版本: Unknown (torch 未安装)` 而流程不中断。需要全量时再 `pip install -e ./apps/platform`。

### 坑 2｜ruff 一次报 24 个问题
`ruff check . --fix` 自动修掉 23 个：
- `UP009`：`# -*- coding:utf-8 -*-` 在 Python 3 已多余
- `UP045`：`Optional[X]` → `X | None`
- `UP006/UP035`：`List`/`Tuple` → `list`/`tuple`
剩 1 个需手改：`B905` `zip()` 缺 `strict=`，改为 `strict=True`（前面有 assert 保证等长）。

### 坑 3｜mypy 目标版本必须提到 3.12
`shutil.rmtree(onexc=...)` 是 3.12 才有的参数（3.14 已移除 `onerror`）。顶层 `[tool.mypy] python_version` 从 `"3.10"` 改为 `"3.12"`，否则按 3.10 的 typeshed 报错。

### 坑 4｜Windows 控制台 GBK 装不下 emoji
`scripts/make_disaster_data.py` 首跑直接崩：
```text
UnicodeEncodeError: 'gbk' codec can't encode character '\U0001f3ac'
```
修正：脚本开头 `sys.stdout.reconfigure(encoding="utf-8")`。同理跑 CLI 时设 `$env:PYTHONIOENCODING="utf-8"`。

### 坑 5｜PowerShell 管道会塞 BOM 给 Python
`"RESET" | odp-reset --yes` 读进来是 `'\ufeff\ufeffRESET\n'`，`strip()` 去不掉 BOM，导致大写 RESET 也被判为"取消"。
修正：`input("> ").strip().lstrip("\ufeff")`（人工输入不受影响，但自动化/重定向需要）。

### 坑 6｜文档的造数据脚本依赖 fsutil
`fsutil file createnew` 需要管理员权限。改用 Python `seek + write`，普通终端可跑，NTFS 不为中间空洞分配磁盘。

---

## 六、命令速查

```powershell
cd d:\大三实训课\ODPlatform
.venv\Scripts\Activate.ps1

odp-init                    # 创建运行时目录 + 环境快照
odp-reset                   # 默认 dry-run
odp-reset --yes             # 手打 RESET 确认后删除
odp-reset --yes --force     # CI 用，跳过交互

python scripts\make_disaster_data.py   # 重造测试现场
ruff check . ; ruff format --check .
mypy apps/platform/src
pytest
```

---

## 七、D1 / D2 设计要点回顾

| | `odp-init` | `odp-reset` |
|---|---|---|
| 目的 | 创建运行时目录 | 删除运行时目录 |
| 数据源 | `get_dirs_to_initialize()` | `get_dirs_to_reset()`（独立白名单） |
| 默认行为 | 直接执行（创建无害） | dry-run（删除危险） |
| 防护 | `mkdir(exist_ok=True)` | `is_protected` 双重检查 + 手打 `RESET` |
| 日志位置 | `apps/platform/logging/` | `.odp-meta/logs/`（永不自删） |
| 命令 | `odp-init` | `odp-reset` |

**核心两条**：危险程度决定默认行为；销毁操作的记录不能被该操作销毁。
