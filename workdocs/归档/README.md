# 过程归档目录

> `workdocs/归档/` 只放**已经结束、但仍需要追溯**的过程材料。
> 这里不是最终文档，也不是当前还在推进的工作目录。

## 一句话规则

- 当前进行中的需求、设计、任务拆解，继续放 `workdocs/需求/`、`workdocs/设计/`、`workdocs/任务拆解/`
- 已结束的过程正文、过程报告、历史测试报告、治理专题，统一迁到 `workdocs/归档/`
- 运行态状态、锁文件、jsonl 仍然只进 `.artifacts/`

## 当前分层

| 路径 | 角色 | 典型内容 |
|---|---|---|
| `workdocs/归档/设计/` | 历史设计正文 | 已结束专题的 design、设计草案、设计清单 |
| `workdocs/归档/需求/` | 历史需求正文 | 已结束专题的 `*_requirements.md` |
| `workdocs/归档/实施计划/` | 历史实施正文 | 已结束专题的 `*_implementation_plan.md` |
| `workdocs/归档/任务拆解/` | 历史 task_split bundle | 已结束专题的 `parallel_plan/workstreams/contracts/reports` 追溯包 |
| `workdocs/归档/完成报告/` | 历史收口记录 | completion report、阶段完成说明 |
| `workdocs/归档/研究报告/` | 历史研究与参考材料 | 依赖分析、交叉验证、融合参考报告 |
| `workdocs/归档/调试报告/` | 历史问题排查 | debug report、链路排障记录 |
| `workdocs/归档/审查报告/` | 历史审查结果 | review report、结构化发现清单 |
| `workdocs/归档/验收报告/` | 历史验收结论 | verify report、历史验收回执 |
| `workdocs/归档/重构报告/` | 历史重构说明 | refactor report、等价收口记录 |
| `workdocs/归档/修复计划/` | 历史修复方案 | fix plan、问题修复对比方案 |
| `workdocs/归档/机读校验/` | 历史机读过程产物 | clarify/plan 对齐 JSON、temporal gate JSON |
| `workdocs/归档/测试报告/` | 历史测试过程 | 测试报告、专项回归报告、历史 JSON 报告 |
| `workdocs/归档/治理专题/` | 历史治理过程 | 体检报告、治理看板、阶段性治理计划 |
| `workdocs/归档/工作流规划/` | 历史流程规划 | Vibe Kanban 计划、阶段性执行计划 |
| `workdocs/归档/架构历史/` | 历史设计备份 | 旧架构备份、已退役实现模式 |

## 进入归档的条件

1. 这份文档已经不再指导当前实现
2. 它的价值主要是“以后查历史”
3. 它不应该再出现在 `docs/` 最终文档主导航

## 不应该放这里的内容

1. 当前有效的产品需求或技术设计
2. 当前仍在推进的 task bundle
3. `.state`、`.lock`、`.jsonl` 等运行态文件
