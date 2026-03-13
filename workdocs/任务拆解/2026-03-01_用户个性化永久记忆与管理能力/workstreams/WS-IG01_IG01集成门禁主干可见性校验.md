# WS-IG01 IG01 集成门禁主干可见性校验

> WS 编号: WS-IG01  
> 对应卡片: `IG01`  
> 类型: `gate`  
> 对应 `feature_id`: `IG-1`

## 0. 关联与来源

- 对应 `task_key`: `PP-20260301-USER-MEMORY-ADMIN`
- 来源主计划: `workdocs/归档/正文/实施计划/用户个性化永久记忆与管理能力_implementation_plan.md`
- 来源并行计划: `workdocs/任务拆解/2026-03-01_用户个性化永久记忆与管理能力/parallel_plan.md`

## 1. 目标

- 校验所有实现卡已输出 `merge_result.json` 且 `merged=true`
- 校验实现卡 `merge_commit` 对 `master` 基线可见
- 阻断“worktree done 但主干不可见”的假完成态

### 1.1 功能机制（必填）

- 触发条件: 前置依赖 `G01` 完成
- 输入: `.artifacts/states/task_splits/2026-03-01_用户个性化永久记忆与管理能力/<task_key>/task-runner-state.json.merge_results.<card_id>` + `master` 基线
- 输出: `IG01` 门禁验收结果
- 状态流转（含异常分支）: `Backlog -> Doing -> Review -> Gate -> Done`，失败则标记 blocked
- 与上/下游 WS 的契约关系: 仅在 `G01` 通过后执行；失败时阻断最终完成

### 1.2 代码锚点与样例（必填）

- 代码锚点（函数/类级）:
  - `scripts/coder4/check_integration_gate.py::run_check`
  - `.artifacts/states/task_splits/2026-03-01_用户个性化永久记忆与管理能力/<task_key>/task-runner-state.json.merge_results.<card_id>`
  - `workdocs/归档/正文/实施计划/用户个性化永久记忆与管理能力_implementation_plan.md::planning_contract`
- 最小样例（可伪代码）:

```python
result = run_check(task_split_dir=task_split_dir, baseline="master")
if result["ok"]:
    mark_done("IG01")
else:
    block_final_delivery(result["errors"])
```

- 来源证据（output/专题文档）:
  - `workdocs/归档/正文/实施计划/用户个性化永久记忆与管理能力_implementation_plan.md`

## 2. 文件边界

### 可修改（白名单）
- `scripts/coder4/check_integration_gate.py`
- `workdocs/任务拆解/2026-03-01_用户个性化永久记忆与管理能力/parallel_plan.md`
- `workdocs/任务拆解/2026-03-01_用户个性化永久记忆与管理能力/contracts/vk_cards.json`
- `workdocs/归档/正文/实施计划/用户个性化永久记忆与管理能力_implementation_plan.md`

### 禁止修改（黑名单）
- `workdocs/归档/正文/实施计划/openclaw迁移重建基线_implementation_plan.md`

## 3. 状态与契约

- 可写字段: `card.status`、`evidence_entry`、`gate_result`
- 只读字段: `card_id`、`feature_ids`、`depends_on`
- 外部契约: `planning_contract` 与 `vk_cards.json` 一致

## 4. 实施步骤

1. 验证前置 `G01` 已通过。
2. 执行 `python3 scripts/coder4/check_integration_gate.py --task-split-dir "2026-03-01_用户个性化永久记忆与管理能力" --state-dir ".artifacts/states/task_splits/2026-03-01_用户个性化永久记忆与管理能力" --baseline master`。
3. 记录校验结果；失败时回溯缺失 `merge_results.<card_id>` 的实现卡。

### 4.1 串行门禁（serial 模式必填）

- 前置卡: `G01`
- 解锁条件: `G01` 通过
- 本 WS 不得推进条件: 任一实现卡缺少 merge 证据或 `master` 不可见

## 5. 测试与验收

- 最小测试集:
- `cd /Users/jijingkun/bojxAI/fastapi && python3 scripts/coder4/check_integration_gate.py --task-split-dir "2026-03-01_用户个性化永久记忆与管理能力" --state-dir ".artifacts/states/task_splits/2026-03-01_用户个性化永久记忆与管理能力" --baseline master`
- 验收标准:
- 所有实现卡 merge 证据完整且 `merged=true`
- 所有实现卡 `merge_commit` 对 `master` 可见

### 5.0 验收门禁映射（必填）

- 对应 implementation plan `done_gate`: `实现卡已合并且主干可见`
- 本 WS 负责的门禁子项: `IG01:IG-1`
- 证据回填位置（文档节）: `workdocs/归档/正文/实施计划/用户个性化永久记忆与管理能力_implementation_plan.md#9`

## 6. 风险与回滚

- 主要风险: `merge_results.<card_id>` 漏写、直接在 `master` 提交绕过每卡 merge 证据
- 回滚点:
- 保持最终状态在 `G01 done / IG01 blocked`
- 回到缺失证据的实现卡补齐 merge 账本
- 回滚开关/策略: 不允许跳过 IG01 直接宣称完成

## 7. 协作者自检卡（提交必填）

- 实际修改文件列表: 见白名单
- 是否修改了白名单外文件（是/否）: 否
- 测试命令与结果: 见 acceptance_checks
- 已知风险点: 实现卡历史遗留未落 merge_results 时会阻断
- 回滚建议: 先补 merge 账本，再重跑 IG01
- 证据绑定检查（target_task_id == evidence_task_id）: 必填

## 8. card_export（机读，必填）

```yaml
card_export:
  id: WS-IG01
  feature_id: IG-1
  card_key: PP-20260301-USER-MEMORY-ADMIN::WS-IG01
  title: IG01 集成门禁主干可见性校验
  type: gate
  task_mode: inspection-card
  merge_required: false
  execution_mode: serial
  lane: lane-gate
  hard_depends_on: [G01]
  soft_depends_on: []
  depends_on: [G01]
  file_whitelist:
    - scripts/coder4/check_integration_gate.py
    - workdocs/任务拆解/2026-03-01_用户个性化永久记忆与管理能力/parallel_plan.md
    - workdocs/任务拆解/2026-03-01_用户个性化永久记忆与管理能力/contracts/vk_cards.json
    - workdocs/归档/正文/实施计划/用户个性化永久记忆与管理能力_implementation_plan.md
  readonly_scope: []
  owner_fields: []
  mechanism_summary:
    - 校验实现卡 merge_result 证据完整且 merged=true
    - 校验 merge_commit 对 master 基线可见
    - 失败则阻断最终完成态
  code_anchor_refs:
    - scripts/coder4/check_integration_gate.py::run_check
    - .artifacts/states/task_splits/2026-03-01_用户个性化永久记忆与管理能力/<task_key>/task-runner-state.json.merge_results.<card_id>
    - workdocs/归档/正文/实施计划/用户个性化永久记忆与管理能力_implementation_plan.md::planning_contract
  example_refs:
    - docs/开发文档/流程与工具/AI协作速查表.md#串行主干状态流最小路径
  acceptance_checks:
    - cd /Users/jijingkun/bojxAI/fastapi && python3 scripts/coder4/check_integration_gate.py --task-split-dir "2026-03-01_用户个性化永久记忆与管理能力" --state-dir ".artifacts/states/task_splits/2026-03-01_用户个性化永久记忆与管理能力" --baseline master
  rollback_anchors:
    - 保持最终状态在 G01 done / IG01 blocked
    - 回到缺失证据的实现卡补齐 merge 账本
  evidence_entry: workdocs/归档/正文/实施计划/用户个性化永久记忆与管理能力_implementation_plan.md#9
  check_cmd:
    - cd /Users/jijingkun/bojxAI/fastapi && python3 scripts/coder4/check_integration_gate.py --task-split-dir "2026-03-01_用户个性化永久记忆与管理能力" --state-dir ".artifacts/states/task_splits/2026-03-01_用户个性化永久记忆与管理能力" --baseline master
  handoff_artifacts:
    - workdocs/任务拆解/2026-03-01_用户个性化永久记忆与管理能力/contracts/sse_events_v1.json
  done_gate:
    - 实现卡 merge 证据齐全且 merged=true
    - merge_commit 全部对 baseline(master) 可见
```
