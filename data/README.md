# data — 数据集目录

> 🚧 **状态**: 运行时目录,内容 gitignored(仅本 README 进 git)

| 子目录 | 含义 | 生命周期 |
|---|---|---|
| `data/raw/` | 原始数据集(只读,绝不就地改) | 外部提供,不自动再生 |
| `data/processed/` | 派生数据集(含冻结后的 train/val/test) | 由数据处理流程可再生 |

结构约定:

```
data/raw/<数据集名>/
├── images/
└── annotations/
```
