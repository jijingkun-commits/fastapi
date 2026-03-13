# 工作包说明：WS-G01 G01 Gate 统一质量门禁

> WS 编号: WS-G01  
> 名称: G01 Gate 统一质量门禁  
> 类型: gate  
> 对应 `feature_id`: G-1

## 0. 关联与来源

- 对应 `task_key`: PP-20260301-KB-RETRIEVAL-P2
- 对应 `task_id`: 无（Gate 卡）
- 来源主计划: `workdocs/归档/正文/实施计划/知识库检索P2分阶段治理_implementation_plan.md`
- 来源并行计划: `workdocs/任务拆解/2026-03-01_知识库检索P2分阶段治理/parallel_plan.md`

## 1. 目标

- 本包目标:
- 统一放行标准：相关性@5 >= 80%，错误引用率 <= 5%
- 未达标阻断进入下游落卡与实施
- 输出阶段评审结论与回滚决议

## 2. 文件边界

### 可修改（白名单）
- scripts/data/kb_offline_evaluation.py
- workdocs/任务拆解/2026-03-01_知识库检索P2分阶段治理/reports/preflight_status.json

### 禁止修改（黑名单）
- 白名单外文件

## 3. 状态与契约

- 可写字段: 当前卡片 `feature_ids` 对应实现字段
- 只读字段: 上一阶段已冻结契约与下游未解锁字段
- 外部契约: `depends_on=['C07']`

## 4. 实施步骤

1. 按 `mechanism_summary` 完成核心改造。
2. 绑定并执行 `acceptance_checks`。
3. 回填证据到 `evidence_entry`。

### 4.1 串行门禁

- 前置卡: C07
- 解锁条件: 当前卡 `acceptance_checks` 全部通过
- 本 WS 不得推进条件: 前置卡未通过或 Gate 阻断

## 5. 测试与验收

- 最小测试集:
  - venv/bin/python scripts/data/kb_offline_evaluation.py --stage gate
  - python3 scripts/docs_guard.py --strict

### 5.0 验收门禁映射

- 对应 implementation plan `done_gate`:
- 人工相关性@5 >= 80%
- 错误引用率 <= 5%
- 证据回填位置: `workdocs/归档/正文/实施计划/知识库检索P2分阶段治理_implementation_plan.md`

## 6. 风险与回滚

- 主要风险: 契约偏移或回归失败导致串行阻塞
- 回滚点:
- 冻结放量并回退到上一稳定阶段配置

## 7. card_export（机读）

```yaml
card_export:
  id: WS-G01
  feature_id: G-1
  card_key: PP-20260301-KB-RETRIEVAL-P2::WS-G01
  title: G01 Gate 统一质量门禁
  type: gate
  task_mode: inspection-card
  merge_required: false
  execution_mode: serial
  hard_depends_on: ['C07']
  soft_depends_on: []
  depends_on: ['C07']
  file_whitelist:
    - scripts/data/kb_offline_evaluation.py
    - workdocs/任务拆解/2026-03-01_知识库检索P2分阶段治理/reports/preflight_status.json
  mechanism_summary:
    - 统一放行标准：相关性@5 >= 80%，错误引用率 <= 5%
    - 未达标阻断进入下游落卡与实施
    - 输出阶段评审结论与回滚决议
  code_anchor_refs:
    - scripts/data/kb_offline_evaluation.py::evaluate_cases
    - workdocs/归档/正文/实施计划/知识库检索P2分阶段治理_implementation_plan.md::planning_contract
  example_refs:
    - workdocs/归档/正文/实施计划/知识库检索P2分阶段治理_implementation_plan.md#L1
  acceptance_checks:
    - venv/bin/python scripts/data/kb_offline_evaluation.py --stage gate
    - python3 scripts/docs_guard.py --strict
  rollback_anchors:
    - 冻结放量并回退到上一稳定阶段配置
  evidence_entry: workdocs/归档/正文/实施计划/知识库检索P2分阶段治理_implementation_plan.md#8
  check_cmd:
    - venv/bin/python scripts/data/kb_offline_evaluation.py --stage gate
    - python3 scripts/docs_guard.py --strict
  done_gate:
    - 人工相关性@5 >= 80%
    - 错误引用率 <= 5%
  pr_id: PR-07
  pr_branch: codex/kb-retrieval-p2-pr-07
  pr_depends_on: ['PR-05', 'PR-06']
  pr_subject: Gate 质量门禁与放量决议
```
