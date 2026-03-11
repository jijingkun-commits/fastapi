# WS-G01 G01 Gate 全链路验收门禁

> WS 编号: WS-G01  
> 对应卡片: `G01`  
> 类型: `gate`  
> 对应 `feature_id`: `G-1`

## 0. 关联与来源

- 对应 `task_key`: `PP-20260301-CHAT-RUN-STOP`
- 来源主计划: `docs/内部参考/迭代需求/聊天断页续跑与强停止_implementation_plan.md`
- 来源并行计划: `workdocs/任务拆解/2026-03-01_聊天断页续跑与强停止/parallel_plan.md`
- card_key: `PP-20260301-CHAT-RUN-STOP::WS-G01`
## 1. 目标

- 聚合 C01-C03 验收结果，确认硬门禁全绿
- 校验 docs_guard 与关键测试，阻断带病进入 vktodo
- 核验 active_task 作用域三元组一致

### 1.1 功能机制（必填）

- 触发条件: 前置依赖 `C03` 完成
- 输入: 上游卡片 done gate 证据 + 当前 feature 配置
- 输出: 卡片验收证据、回滚锚点、状态更新
- 状态流转（含异常分支）: `Backlog -> Doing -> Review -> Gate -> Done`，失败则回滚并标记 blocked
- 与上/下游 WS 的契约关系: 仅在 `depends_on` 满足后推进

### 1.2 代码锚点与样例（必填）

- 代码锚点（函数/类级）:
  - `workdocs/任务拆解/2026-03-01_聊天断页续跑与强停止/contracts/_active_task.json::scope`
  - `scripts/docs_guard.py::strict`
  - `docs/内部参考/迭代需求/聊天断页续跑与强停止_implementation_plan.md::planning_contract`
- 最小样例（可伪代码）:

```python
if checks_passed:
    mark_done(card_id)
else:
    rollback_to_anchor()
```

## 2. 文件边界

### 可修改（白名单）
- `workdocs/任务拆解/2026-03-01_聊天断页续跑与强停止/parallel_plan.md`
- `workdocs/任务拆解/2026-03-01_聊天断页续跑与强停止/contracts/vk_cards.json`
- `docs/内部参考/迭代需求/聊天断页续跑与强停止_implementation_plan.md`

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

- 前置卡: `C03`
- 解锁条件: `depends_on` 对应卡片全部通过
- 本 WS 不得推进条件: 任一 `acceptance_checks` 失败

## 5. 测试与验收

- 最小测试集:
- `python3 scripts/docs_guard.py --strict`
- `venv/bin/python -m pytest tests/unit/test_chat_stop_cancel_semantics.py tests/unit/test_chat_service_disconnect_continue.py -q`
- 验收标准:
- 文档索引与关键验收命令全绿

### 5.0 验收门禁映射（必填）

- 对应 implementation plan `done_gate`: `文档索引与关键验收命令全绿`
- 本 WS 负责的门禁子项: `G01:G-1`
- 证据回填位置（文档节）: `docs/内部参考/迭代需求/聊天断页续跑与强停止_implementation_plan.md#7`

## 6. 风险与回滚

- 主要风险: 前置卡未完成、字段契约漂移、测试结果不稳定
- 回滚点:
- 暂停 /jjk-vktodo
- 回退到 C03 前状态并复测
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
  card_key: PP-20260301-CHAT-RUN-STOP::WS-G01
  title: G01 Gate 全链路验收门禁
  type: gate
  task_mode: inspection-card
  merge_required: false
  execution_mode: serial
  lane: lane-gate
  hard_depends_on: ['C03']
  soft_depends_on: []
  depends_on: ['C03']
  file_whitelist:
    - workdocs/任务拆解/2026-03-01_聊天断页续跑与强停止/parallel_plan.md
    - workdocs/任务拆解/2026-03-01_聊天断页续跑与强停止/contracts/vk_cards.json
    - docs/内部参考/迭代需求/聊天断页续跑与强停止_implementation_plan.md
  mechanism_summary:
    - 聚合 C01-C03 验收结果，确认硬门禁全绿
    - 校验 docs_guard 与关键测试，阻断带病进入 vktodo
    - 核验 active_task 作用域三元组一致
  code_anchor_refs:
    - workdocs/任务拆解/2026-03-01_聊天断页续跑与强停止/contracts/_active_task.json::scope
    - scripts/docs_guard.py::strict
    - docs/内部参考/迭代需求/聊天断页续跑与强停止_implementation_plan.md::planning_contract
  acceptance_checks:
    - python3 scripts/docs_guard.py --strict
    - venv/bin/python -m pytest tests/unit/test_chat_stop_cancel_semantics.py tests/unit/test_chat_service_disconnect_continue.py -q
  rollback_anchors:
    - 暂停 /jjk-vktodo
    - 回退到 C03 前状态并复测
  evidence_entry: docs/内部参考/迭代需求/聊天断页续跑与强停止_implementation_plan.md#7
  check_cmd:
    - python3 scripts/docs_guard.py --strict
    - venv/bin/python -m pytest tests/unit/test_chat_stop_cancel_semantics.py tests/unit/test_chat_service_disconnect_continue.py -q
  done_gate:
    - 文档索引与关键验收命令全绿
  source_ws_file: workdocs/任务拆解/2026-03-01_聊天断页续跑与强停止/workstreams/WS-G01_G01Gate全链路验收门禁.md
```
