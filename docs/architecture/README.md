# 架构决策记录(ADR)

本目录存放项目的架构决策记录(Architecture Decision Record)。

## 什么是 ADR

一份 ADR 记录**一个**重要技术决策:背景、备选方案、最终选择、理由、后果、撤销条件。
它不是设计文档,而是"当初为什么这么定"的证据——半年后接手的人最需要的就是这个。

## 命名约定

`ADR-<三位序号>-<短横线小写主题>.md`,例如:

- `ADR-001-monorepo.md`
- `ADR-002-src-layout.md`

## 索引

| 编号 | 标题 | 状态 |
|---|---|---|
| [ADR-001](ADR-001-monorepo.md) | 采用 Monorepo + apps/ 布局 | ✅ Accepted |
