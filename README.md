# ODPlatform

通用目标检测开发平台（Monorepo）。

## 布局

- `apps/platform/` — 核心引擎（od-platform 包，Python）
- `apps/web-backend/` — Web 后端服务（占位，V1.1 启动）
- `apps/desktop/` — 桌面端（占位）
- `tests/` — 跨端 E2E 测试
- `data/` — 数据集（raw / processed）
- `models/` — 模型权重（pretrained / trained）
- `runs/` — 训练运行现场
- `docs/architecture/` — 架构决策记录（ADR）

## 快速开始

```powershell
conda activate ODP
pip install -e "./apps/platform[dev]"
odp-init
```

详见各子项目 README 与 `docs/architecture/ADR-001-monorepo.md`。
