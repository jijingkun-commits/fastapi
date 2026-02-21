# 工作包说明（模板）

> WS 编号: WS-XX  
> 名称: <工作包名称>  
> 负责人: <姓名>  
> 类型: <parallel|gate|foundation>
> 对应 `feature_id`: <P1-03 / P2-01 ...>

## 0. 关联与来源

- 对应 `task_key`:
- 来源主计划：`docs/内部参考/迭代需求/<topic>_implementation_plan.md`
- 来源并行计划：`docs/内部参考/任务拆解/<YYYY-MM-DD_主题>/parallel_plan.md`

## 1. 目标

- 本包目标：
- 完成定义（DoD）：

### 1.1 功能机制（必填）

- 触发条件：
- 输入：
- 输出：
- 状态流转（含异常分支）：
- 与上/下游 WS 的契约关系：

### 1.2 代码锚点与样例（必填）

- 代码锚点（函数/类级）：
  - `path::symbol`
- 最小样例（可伪代码）：

```python
# 示例：仅展示本 WS 核心机制，不要贴完整实现
```

- 来源证据（output/专题文档）：
  - `path#anchor`

## 2. 文件边界

### 可修改（白名单）
- `path/to/file_a`
- `path/to/file_b`

### 禁止修改（黑名单）
- `path/to/file_x`

## 3. 状态与契约

- 可写字段：
- 只读字段：
- 外部契约：

## 4. 实施步骤

1.
2.
3.

### 4.1 串行门禁（serial 模式必填）

- 前置卡：
- 解锁条件：
- 本 WS 不得推进条件：

## 5. 测试与验收

- 最小测试集：
- 验收标准：

### 5.0 验收门禁映射（必填）

- 对应 implementation plan `done_gate`：
- 本 WS 负责的门禁子项：
- 证据回填位置（文档节）：

### 5.1 TC-ID 映射表（Gate WS 必填）

> 非 Gate WS 可按需填写；Gate WS 必须维护并随复测更新。

| TC-ID | 门禁命令/检查项 | 自动化脚本或 pytest nodeid | 本次结果 | 责任 WS | 豁免/缺陷单 |
|------|------------------|----------------------------|----------|---------|-------------|
| TC-TBD-001 |  |  |  |  |  |

### 5.2 浏览器测试（触发式）

- 是否触发浏览器测试（是/否）：
- 触发依据（命中项）：
- 执行命令：
- 结果与证据路径：
- 未执行原因（如不触发则必填）：

## 6. 风险与回滚

- 主要风险：
- 回滚点：
- 回滚开关/策略：

## 7. 协作者自检卡（提交必填）

- 实际修改文件列表：
- 是否修改了白名单外文件（是/否）：
- 测试命令与结果：
- 已知风险点：
- 回滚建议：
- 证据绑定检查（target_task_id == evidence_task_id）：

## 8. card_export（机读，必填）

```yaml
card_export:
  id: WS-XX
  feature_id: P1-03
  card_key: <task_key>::WS-XX
  title: <工作包名称>
  type: parallel  # parallel | gate | foundation
  task_mode: implementation-card
  merge_required: true
  execution_mode: serial
  lane: lane-backend
  hard_depends_on: []
  soft_depends_on: []
  depends_on: []
  file_whitelist:
    - path/to/file_a
  readonly_scope:
    - path/to/readonly
  owner_fields:
    - field_a
  mechanism_summary:
    - 触发条件: ...
    - 状态流转: ...
  code_anchor_refs:
    - path/to/file.py::function_name
  example_refs:
    - docs/内部参考/迭代需求/<topic>_implementation_plan.md#L1
  acceptance_checks:
    - venv/bin/python -m pytest -q tests/unit/test_x.py
    - python3 scripts/docs_guard.py --strict
  rollback_anchors:
    - ENABLE_X=true|false
  evidence_entry: docs/内部参考/迭代需求/<topic>_implementation_plan.md#...
  check_cmd:
    - venv/bin/python -m pytest -q tests/unit/test_x.py
  handoff_artifacts:
    - docs/内部参考/任务拆解/<YYYY-MM-DD_主题>/contracts/sse_events_v1.json
  dod:
    - DoD-1
```
