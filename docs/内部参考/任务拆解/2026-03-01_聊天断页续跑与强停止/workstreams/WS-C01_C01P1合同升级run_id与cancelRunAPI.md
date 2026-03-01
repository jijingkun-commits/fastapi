# WS-C01 C01 P1 合同升级（run_id 与 cancelRun API）

> WS 编号: WS-C01  
> 对应卡片: `C01`  
> 类型: `parallel`  
> 对应 `feature_id`: `P1-01,P1-02`

## 0. 关联与来源

- 对应 `task_key`: `PP-20260301-CHAT-RUN-STOP`
- 来源主计划: `docs/内部参考/迭代需求/聊天断页续跑与强停止_implementation_plan.md`
- 来源并行计划: `docs/内部参考/任务拆解/2026-03-01_聊天断页续跑与强停止/parallel_plan.md`
- card_key: `PP-20260301-CHAT-RUN-STOP::WS-C01`
- PR 归属: `PR-01` / `codex/chat-run-stop-pr-01`
- PR 依赖: `[]`

## 1. 目标

- 扩展 init 事件契约，前端接收并缓存 activeRunId
- 新增 cancelRun API 封装，打通强停止前置能力
- 保持 SSE 主事件语义兼容，不引入破坏性字段变更

### 1.1 功能机制（必填）

- 触发条件: 前置依赖 `无` 完成
- 输入: 上游卡片 done gate 证据 + 当前 feature 配置
- 输出: 卡片验收证据、回滚锚点、状态更新
- 状态流转（含异常分支）: `Backlog -> Doing -> Review -> Gate -> Done`，失败则回滚并标记 blocked
- 与上/下游 WS 的契约关系: 仅在 `depends_on` 满足后推进

### 1.2 代码锚点与样例（必填）

- 代码锚点（函数/类级）:
  - `web/src/types/message.ts::InitEventData`
  - `web/src/lib/backend.ts::dispatchSSEEvent`
  - `web/src/lib/backend.ts::cancelRun`
- 最小样例（可伪代码）:

```python
if checks_passed:
    mark_done(card_id)
else:
    rollback_to_anchor()
```

## 2. 文件边界

### 可修改（白名单）
- `web/src/types/message.ts`
- `web/src/lib/backend.ts`

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

- 前置卡: `无`
- 解锁条件: `depends_on` 对应卡片全部通过
- 本 WS 不得推进条件: 任一 `acceptance_checks` 失败

## 5. 测试与验收

- 最小测试集:
- `cd web && pnpm exec eslint src/types/message.ts src/lib/backend.ts`
- 验收标准:
- init run_id 契约打通
- cancelRun API 封装可用

### 5.0 验收门禁映射（必填）

- 对应 implementation plan `done_gate`: `init run_id 契约打通; cancelRun API 封装可用`
- 本 WS 负责的门禁子项: `C01:P1-01,P1-02`
- 证据回填位置（文档节）: `docs/内部参考/迭代需求/聊天断页续跑与强停止_implementation_plan.md#7`

## 6. 风险与回滚

- 主要风险: 前置卡未完成、字段契约漂移、测试结果不稳定
- 回滚点:
- 回退 InitEventData run_id 字段扩展
- 删除 cancelRun API 封装，恢复旧调用链
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
  id: WS-C01
  feature_id: P1-01,P1-02
  card_key: PP-20260301-CHAT-RUN-STOP::WS-C01
  title: C01 P1 合同升级（run_id 与 cancelRun API）
  type: parallel
  task_mode: implementation-card
  merge_required: true
  execution_mode: serial
  lane: lane-frontend-contract
  hard_depends_on: []
  soft_depends_on: []
  depends_on: []
  file_whitelist:
    - web/src/types/message.ts
    - web/src/lib/backend.ts
  mechanism_summary:
    - 扩展 init 事件契约，前端接收并缓存 activeRunId
    - 新增 cancelRun API 封装，打通强停止前置能力
    - 保持 SSE 主事件语义兼容，不引入破坏性字段变更
  code_anchor_refs:
    - web/src/types/message.ts::InitEventData
    - web/src/lib/backend.ts::dispatchSSEEvent
    - web/src/lib/backend.ts::cancelRun
  acceptance_checks:
    - cd web && pnpm exec eslint src/types/message.ts src/lib/backend.ts
  rollback_anchors:
    - 回退 InitEventData run_id 字段扩展
    - 删除 cancelRun API 封装，恢复旧调用链
  evidence_entry: docs/内部参考/迭代需求/聊天断页续跑与强停止_implementation_plan.md#7
  check_cmd:
    - cd web && pnpm exec eslint src/types/message.ts src/lib/backend.ts
  done_gate:
    - init run_id 契约打通
    - cancelRun API 封装可用
  source_ws_file: docs/内部参考/任务拆解/2026-03-01_聊天断页续跑与强停止/workstreams/WS-C01_C01P1合同升级run_id与cancelRunAPI.md
```
