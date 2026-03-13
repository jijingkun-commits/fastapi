# 过程文档目录

> `workdocs/` 是过程层根目录，负责承载**当前过程**和**历史过程归档**。
> 这里不承担最终真理源，也不承担运行态状态文件。

## 先记住一句话

- 给人读的过程文档放 `workdocs/` 的正文目录
- 给机器读的过程文档放对应主题下的 `contracts/`、`reports/`
- 已完成但仍需追溯的过程材料，统一进入 `workdocs/归档/`
- 真正运行中的状态、锁文件、jsonl 进 `.artifacts/`

## 目录职责

| 目录 | 角色 | 典型内容 |
|---|---|---|
| `workdocs/需求/` | 过程文档 / 给人读 | requirements、范围、约束、验收门槛 |
| `workdocs/设计/` | 过程文档 / 给人读 | design、取舍、结构图、实施思路 |
| `workdocs/_templates/` | 过程模板资产 | 项目覆盖模板、命令输出模板差异层 |
| `workdocs/任务拆解/` 根目录与 `workstreams/` | 过程文档 / 给人读 | `parallel_plan.md`、工作包说明 |
| `workdocs/**/contracts/` | 过程文档 / 给机器读 | 输入合同、映射 JSON、规划契约、`implementation_plan.md`、`uat_cases.md` |
| `workdocs/**/reports/` | 过程文档 / 给机器读或半机器读 | 校验结果、消费报告、`review/test/verify/debug` 报告 |
| `workdocs/归档/` | 历史过程文档 | `正文/`、`报告/`、`任务拆解/`、`专题/` 四类历史材料 |

## task_split 特例

`task_split` 已完成 canonical 收口：

- 正文在 `workdocs/任务拆解/<task_split_dir>/`
- 机器契约在 `workdocs/任务拆解/<task_split_dir>/contracts/`
- 过程报告在 `workdocs/任务拆解/<task_split_dir>/reports/`
- 真实运行态在 `.artifacts/states/task_splits/`

常见功能级过程 bundle：

- `workdocs/任务拆解/<YYYY-MM-DD_主题>/contracts/implementation_plan.md`
- `workdocs/任务拆解/<YYYY-MM-DD_主题>/contracts/uat_cases.md`
- `workdocs/任务拆解/<YYYY-MM-DD_主题>/reports/review_report.md`
- `workdocs/任务拆解/<YYYY-MM-DD_主题>/reports/test_report.md`
- `workdocs/任务拆解/<YYYY-MM-DD_主题>/reports/verify_report.md`
- `workdocs/任务拆解/<YYYY-MM-DD_主题>/reports/debug_report.md`

## 过渡说明

当前仓库里仍保留少量旧入口说明页，但它们只负责：

1. 迁移期追溯
2. 历史兼容入口

已经迁出的历史材料，优先按下面的桶去找：

- `workdocs/_templates/`
- `workdocs/归档/正文/`：需求、设计、实施计划
- `workdocs/归档/报告/`：测试、验收、审查、调试、重构、修复、完成、机读校验
- `workdocs/归档/任务拆解/`：历史 task bundle
- `workdocs/归档/专题/`：治理专题、研究报告、工作流规划、架构历史

新的过程文档，不再默认写回旧入口页所在目录。
