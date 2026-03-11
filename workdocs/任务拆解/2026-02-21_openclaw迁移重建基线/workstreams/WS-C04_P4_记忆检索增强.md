# 工作包说明

> WS 编号: WS-C04
> 名称: P4 记忆检索增强
> 类型: parallel
> 对应 feature_id: P4-01

## 0. 关联与来源

- 对应 task_key: PP-20260221-OPENCLAW-REBUILD-BASELINE
- 对应 card_id: C04
- 来源主计划: `docs/内部参考/迭代需求/openclaw迁移重建基线_implementation_plan.md`
- 来源并行计划: `workdocs/任务拆解/2026-02-21_openclaw迁移重建基线/parallel_plan.md`

## 1. 目标

- 本包目标: P4 记忆检索增强 的可执行落地。
- 完成定义（DoD）:
  - C04a（recall MVP）回归通过：用户隔离检索 + 降级可用
  - C04b（flush 增强）回归通过：pre-compaction flush 可控开启
  - 记忆异常不阻断主对话

### 1.1 功能机制

  - Hybrid recall + pre-compaction flush 记忆闭环（分阶段）
  - C04a: recall MVP（先打通用户隔离与召回接线）
  - C04b: pre-compaction flush（在 recall 稳定后增量接入）
  - 用户隔离与降级路径保底
  - 记忆异常不阻断主对话

### 1.2 代码锚点

  - app/services/user_preference_memory_service.py::build_user_preference_context
  - app/services/user_preference_memory_service.py::persist_explicit_preferences_from_input
  - app/services/chat_service.py::stream

- 本卡新增实体目标（C04 实现阶段创建）:
  - app/services/user_preference_memory_service.py（recall）
  - app/services/user_preference_memory_service.py（flush）
  - app/services/chat_service.py（inject_memory_context）

- 来源证据:
  - docs/内部参考/迭代需求/openclaw迁移重建基线_implementation_plan.md#4.9

## 2. 文件边界

### 可修改（白名单）
  - app/services/user_preference_memory_service.py
  - app/services/chat_service.py
  - app/models/user_memory.py
  - app/repositories/user_memory_repo.py
  - alembic/versions
  - tests/unit/test_user_preference_memory_service.py
  - tests/unit/test_multi_intent_queue_flow.py

### 禁止修改（黑名单）
- 其他 card_id 对应白名单外文件

## 3. 串行门禁

- 前置卡: C03
- 解锁条件: 前置卡 `done_gate` 全部通过
- 本 WS 不得推进条件: 前置卡存在 `TODO/IN_PROGRESS/BLOCKED`

## 4. 测试与验收

- 验收命令:
  - PYTHONPATH=. pytest tests/unit/test_user_preference_memory_service.py -k "context or persist"
  - PYTHONPATH=. pytest tests/unit/test_multi_intent_queue_flow.py

## 5. 风险与回滚

- 回滚锚点:
  - ENABLE_MEMORY_RECALL
  - ENABLE_PRE_COMPACTION_FLUSH

## 6. card_export

```yaml
card_export:
  id: WS-C04
  card_id: C04
  feature_ids: [P4-01]
  card_key: PP-20260221-OPENCLAW-REBUILD-BASELINE::WS-C04
  title: P4 记忆检索增强
  type: parallel
  task_mode: implementation-card
  merge_required: true
  execution_mode: serial
  hard_depends_on: [C03]
  depends_on: [C03]
  file_whitelist:
  - app/services/user_preference_memory_service.py
  - app/services/chat_service.py
  - app/models/user_memory.py
  - app/repositories/user_memory_repo.py
  - alembic/versions
  - tests/unit/test_user_preference_memory_service.py
  - tests/unit/test_multi_intent_queue_flow.py
  mechanism_summary:
  - Hybrid recall + pre-compaction flush 记忆闭环（分阶段）
  - C04a: recall MVP（先打通用户隔离与召回接线）
  - C04b: pre-compaction flush（在 recall 稳定后增量接入）
  - 用户隔离与降级路径保底
  - 记忆异常不阻断主对话
  code_anchor_refs:
  - app/services/user_preference_memory_service.py::build_user_preference_context
  - app/services/user_preference_memory_service.py::persist_explicit_preferences_from_input
  - app/services/chat_service.py::stream
  acceptance_checks:
  - PYTHONPATH=. pytest tests/unit/test_user_preference_memory_service.py -k "context or persist"
  - PYTHONPATH=. pytest tests/unit/test_multi_intent_queue_flow.py
  rollback_anchors:
  - ENABLE_MEMORY_RECALL
  - ENABLE_PRE_COMPACTION_FLUSH
  evidence_entry: docs/内部参考/迭代需求/openclaw迁移重建基线_implementation_plan.md#4.9
  done_gate:
  - C04a（recall MVP）回归通过
  - C04b（flush 增强）回归通过
  - 记忆异常不阻断主对话
```
