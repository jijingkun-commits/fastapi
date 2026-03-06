# WS-G01 G01 Gate 全链路验收门禁

> WS 编号: WS-G01  
> 对应卡片: `G01`  
> 类型: `gate`  
> 对应 `feature_id`: `G-1`

## 0. 关联与来源

- 对应 `task_key`: `PP-20260301-USER-MEMORY-ADMIN`
- 来源主计划: `docs/内部参考/迭代需求/用户个性化永久记忆与管理能力_implementation_plan.md`
- 来源并行计划: `docs/内部参考/任务拆解/2026-03-01_用户个性化永久记忆与管理能力/parallel_plan.md`

## 1. 目标

- 聚合执行卡验收结果，确认 implementation hard gate 全绿
- 校验 docs_guard、关键测试、active_task 作用域一致性
- 门禁失败时禁止进入 /jjk-vktodo 自动落卡执行

### 1.1 功能机制（必填）

- 触发条件: 前置依赖 `C06` 完成
- 输入: 上游卡片 done gate 证据 + 当前 feature 配置
- 输出: 卡片验收证据、回滚锚点、审计结果
- 状态流转（含异常分支）: `Backlog -> Doing -> Review -> Gate -> Done`，失败则回滚并标记 blocked
- 与上/下游 WS 的契约关系: 仅在 `depends_on` 满足后推进

### 1.2 代码锚点与样例（必填）

- 代码锚点（函数/类级）:
  - `docs/内部参考/任务拆解/2026-03-01_用户个性化永久记忆与管理能力/_active_task.json::scope`
  - `scripts/docs_guard.py::strict mode`
  - `docs/内部参考/迭代需求/用户个性化永久记忆与管理能力_implementation_plan.md::planning_contract`
- 最小样例（可伪代码）:

```python
if checks_passed:
    mark_done(card_id)
else:
    rollback_to_anchor()
```

- 来源证据（output/专题文档）:
  - `docs/内部参考/迭代需求/用户个性化永久记忆与管理能力_implementation_plan.md`

## 2. 文件边界

### 可修改（白名单）
- `docs/内部参考/任务拆解/2026-03-01_用户个性化永久记忆与管理能力/parallel_plan.md`
- `docs/内部参考/任务拆解/2026-03-01_用户个性化永久记忆与管理能力/vk_cards.json`
- `docs/内部参考/迭代需求/用户个性化永久记忆与管理能力_implementation_plan.md`

### 禁止修改（黑名单）
- `docs/内部参考/迭代需求/openclaw迁移重建基线_implementation_plan.md`

## 3. 状态与契约

- 可写字段: `card.status`、`evidence_entry`、`gate_result`
- 只读字段: `card_id`、`feature_ids`、`depends_on`
- 外部契约: `planning_contract` 与 `vk_cards.json` 一致

## 4. 实施步骤

1. 拉取前置卡完成状态并执行本卡前置检查。
2. 运行 `acceptance_checks` 并记录输出。
3. 回填证据与回滚锚点结果。

### 4.1 串行门禁（serial 模式必填）

- 前置卡: `C06`
- 解锁条件: `depends_on` 对应卡片全部通过
- 本 WS 不得推进条件: 任一 `acceptance_checks` 失败

## 5. 测试与验收

- 最小测试集:
- `cd /Users/jijingkun/bojxAI/fastapi && venv/bin/python -m pytest -q tests/api/test_memory_admin_api.py tests/unit/test_memory_admin_audit_service.py`
- `cd /Users/jijingkun/bojxAI/fastapi && python3 scripts/docs_guard.py --strict`
- 验收标准:
- 所有 acceptance_checks 通过
- active_task 作用域绑定正确

### 5.0 验收门禁映射（必填）

- 对应 implementation plan `done_gate`: `所有 acceptance_checks 通过; active_task 作用域绑定正确`
- 本 WS 负责的门禁子项: `G01:G-1`
- 证据回填位置（文档节）: `docs/内部参考/迭代需求/用户个性化永久记忆与管理能力_implementation_plan.md#9`

## 6. 风险与回滚

- 主要风险: 前置卡未完成、字段契约漂移、测试结果不稳定
- 回滚点:
- 暂停 /jjk-vktodo
- 回退到 C06 前状态并复测
- 回滚开关/策略: 仅在本卡范围回滚，禁止跨卡改动

## 7. 协作者自检卡（提交必填）

- 实际修改文件列表: 见白名单
- 是否修改了白名单外文件（是/否）: 否
- 测试命令与结果: 见 acceptance_checks
- 已知风险点: 串行链路断裂导致阻塞
- 回滚建议: 先回滚本卡，再评估下游
- 证据绑定检查（target_task_id == evidence_task_id）: 必填

## 8. card_export（机读，必填）

```yaml
card_export:
  id: WS-G01
  feature_id: G-1
  card_key: PP-20260301-USER-MEMORY-ADMIN::WS-G01
  title: G01 Gate 全链路验收门禁
  type: gate
  task_mode: inspection-card
  merge_required: false
  execution_mode: serial
  lane: lane-gate
  hard_depends_on: [C06]
  soft_depends_on: []
  depends_on: [C06]
  file_whitelist:
    - docs/内部参考/任务拆解/2026-03-01_用户个性化永久记忆与管理能力/parallel_plan.md
    - docs/内部参考/任务拆解/2026-03-01_用户个性化永久记忆与管理能力/vk_cards.json
    - docs/内部参考/迭代需求/用户个性化永久记忆与管理能力_implementation_plan.md
  readonly_scope: []
  owner_fields: []
  mechanism_summary:
    - 聚合执行卡验收结果，确认 implementation hard gate 全绿
    - 校验 docs_guard、关键测试、active_task 作用域一致性
    - 门禁失败时禁止进入 /jjk-vktodo 自动落卡执行
  code_anchor_refs:
    - docs/内部参考/任务拆解/2026-03-01_用户个性化永久记忆与管理能力/_active_task.json::scope
    - scripts/docs_guard.py::strict mode
    - docs/内部参考/迭代需求/用户个性化永久记忆与管理能力_implementation_plan.md::planning_contract
  example_refs:
    - docs/内部参考/迭代需求/用户个性化永久记忆与管理能力_implementation_plan.md#4
  acceptance_checks:
    - cd /Users/jijingkun/bojxAI/fastapi && venv/bin/python -m pytest -q tests/api/test_memory_admin_api.py tests/unit/test_memory_admin_audit_service.py
    - cd /Users/jijingkun/bojxAI/fastapi && python3 scripts/docs_guard.py --strict
  rollback_anchors:
    - 暂停 /jjk-vktodo
    - 回退到 C06 前状态并复测
  evidence_entry: docs/内部参考/迭代需求/用户个性化永久记忆与管理能力_implementation_plan.md#9
  check_cmd:
    - cd /Users/jijingkun/bojxAI/fastapi && venv/bin/python -m pytest -q tests/api/test_memory_admin_api.py tests/unit/test_memory_admin_audit_service.py
    - cd /Users/jijingkun/bojxAI/fastapi && python3 scripts/docs_guard.py --strict
  handoff_artifacts:
    - docs/内部参考/任务拆解/2026-03-01_用户个性化永久记忆与管理能力/contracts/sse_events_v1.json
  done_gate:
    - 所有 acceptance_checks 通过
    - active_task 作用域绑定正确
```
