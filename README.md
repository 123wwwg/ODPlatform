# ODPlatform

通用目标检测开发平台（Object Detection Platform）。

**定位**：算法是可替换的变量，工程链路是稳定的常量。本仓库沉淀的是数据接入、超参管理、训练产物归档、推理加速、输入源切换这套工程骨架。

## 目录结构（Monorepo）

```
ODPlatform/
├── .odp-workspace          # 根标记文件（paths.py 靠它定位 ROOT_DIR）
├── pyproject.toml          # 仓库根：只放全仓共享的工具配置（ruff/mypy/pytest）
├── apps/
│   └── platform/           # 今天唯一的端：训练 + 推理引擎
│       ├── pyproject.toml  # 端内：依赖 + 命令入口（可安装包）
│       ├── src/od_platform/
│       │   ├── common/     # 基础层：paths / logging / string / system / performance
│       │   └── cli/        # 入口层：init_project / reset_project
│       ├── tests/
│       ├── configs/
│       └── logging/
├── data/{raw,processed}
├── models/{pretrained,trained}
├── runs/
├── scripts/                # 装包前的开发期入口
├── tests/                  # 跨端测试占位
└── docs/                   # 项目文档 + ADR
```

## 快速开始

```bash
python -m venv .venv
.venv\Scripts\Activate.ps1          # Windows
pip install -e ./apps/platform

odp-init                            # 创建运行时目录 + 环境快照
odp-reset                           # 默认 dry-run，先看计划
odp-reset --yes                     # 真删除（需手打 RESET 确认）
```

## 命令一览

| 命令 | 作用 | 默认行为 |
|---|---|---|
| `odp-init` | 创建运行时目录 | 直接执行（创建无害） |
| `odp-reset` | 清理运行时产物 | dry-run（删除危险） |

`odp-reset` 永不删除：`data/raw/`（原始数据）、`models/pretrained/`（预训练权重）、任何进 git 的代码/文档/配置。
审计日志写在 `.odp-meta/logs/`，不会被 reset 自身清理。

## 文档

- `docs/architecture/ADR-001-monorepo.md`
