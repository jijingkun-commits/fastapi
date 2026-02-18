# 工作包说明（模板）

> WS 编号: WS-XX  
> 名称: <工作包名称>  
> 负责人: <姓名>  
> 类型: <parallel|gate|foundation>

## 0. 关联与来源

- 对应 `task_key`:
- 来源主计划：`docs/内部参考/迭代需求/<topic>_implementation_plan.md`
- 来源并行计划：`docs/内部参考/任务拆解/<YYYY-MM-DD_主题>/parallel_plan.md`

## 1. 目标

- 本包目标：
- 完成定义（DoD）：

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

## 5. 测试与验收

- 最小测试集：
- 验收标准：

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

## 7. 协作者自检卡（提交必填）

- 实际修改文件列表：
- 是否修改了白名单外文件（是/否）：
- 测试命令与结果：
- 已知风险点：
- 回滚建议：

## 8. card_export（机读，必填）

```yaml
card_export:
  id: WS-XX
  card_key: <task_key>::WS-XX
  title: <工作包名称>
  type: parallel
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
  check_cmd:
    - venv/bin/python -m pytest -q tests/unit/test_x.py
  handoff_artifacts:
    - docs/内部参考/任务拆解/<YYYY-MM-DD_主题>/contracts/sse_events_v1.json
  dod:
    - DoD-1
```
