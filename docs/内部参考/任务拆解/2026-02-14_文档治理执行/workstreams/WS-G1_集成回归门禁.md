# 工作包说明

> WS 编号: WS-G1
> 名称: 集成回归门禁
> 类型: gate

---

## 0. 关联与来源

- 对应 `task_key`: `PP-20260214-DOCS-GOVERNANCE`
- 来源主计划：`docs/内部参考/迭代需求/docs_governance_implementation_plan.md`
- 来源并行计划：`docs/内部参考/任务拆解/2026-02-14_文档治理执行/parallel_plan.md`

---

## 1. 目标

- 本包目标：统一执行文档门禁与关键路径抽检，完成失败项责任 WS 归因。
- 完成定义（DoD）：
  1. G1 门禁命令完整执行。
  2. 失败项（若有）可映射责任 WS。
  3. Gate 结果回填 `parallel_plan.md`。

---

## 2. 文件边界

### 可修改（白名单）

- `docs/内部参考/任务拆解/2026-02-14_文档治理执行/parallel_plan.md`
- `docs/内部参考/任务拆解/2026-02-14_文档治理执行/workstreams/WS-G1_集成回归门禁.md`

### 禁止修改（黑名单）

- 功能实现文件：`app/**`、`web/**`
- 非门禁文档正文（除责任归因回填外）

---

## 3. 状态与契约

- 可写字段：`gate.g1.status`、`gate.g1.tc_matrix`、`gate.g1.owner_mapping`。
- 只读字段：业务实现内容与权威规则定义。

---

## 4. 实施步骤

1. 执行 `WS-01..WS-04` 对应最小验证命令。
2. 执行全量门禁命令 `docs_guard --strict`。
3. 汇总失败项并归因到责任 WS。
4. 回填并行计划 Gate 状态。

---

## 5. 测试与验收

- 最小测试集：
  - `python3 scripts/docs_guard.py --strict`
  - `rg -n 'app/ai/workflow/data_graph.py' docs/开发文档/代码解读/多智能体工作流.md`
  - `rg -n '示例占位' docs/开发文档/工作流/开发工作流.md`

验收标准：

1. 门禁通过，或失败项有明确责任 WS。
2. 不存在“无法归因”的阻塞项。

### 5.1 TC-ID 映射表（Gate WS 必填）

| TC-ID | 门禁命令/检查项 | 自动化脚本或 nodeid | 本次结果 | 责任 WS | 豁免/缺陷单 |
|---|---|---|---|---|---|
| DOC-GATE-001 | docs_guard 严格门禁 | `python3 scripts/docs_guard.py --strict` | 待执行 | WS-04 | |
| DOC-GATE-002 | 多智能体路径引用抽检 | `rg -n 'app/ai/workflow/data_graph.py' .../多智能体工作流.md` | 待执行 | WS-03 | |
| DOC-GATE-003 | 模板占位标记抽检 | `rg -n '示例占位' .../开发工作流.md` | 待执行 | WS-04 | |
| DOC-GATE-004 | 迭代需求索引完整性 | `docs/SUMMARY.md` 人工审阅 | 待执行 | WS-04 | |

### 5.2 浏览器测试（触发式）

- 是否触发浏览器测试（是/否）：否
- 触发依据（命中项）：仅文档治理门禁，无 UI 功能变更。
- 执行命令：N/A
- 结果与证据路径：N/A
- 未执行原因：非浏览器场景。

---

## 6. 风险与回滚

- 主要风险：抽检命令口径不统一造成误判。
- 回滚点：回退 Gate 状态回填，仅保留执行记录。

---

## 7. 协作者自检卡（提交必填）

- 实际修改文件列表：
- 是否修改了白名单外文件（是/否）：
- 测试命令与结果：
- 已知风险点：
- 回滚建议：

---

## 8. card_export（/vk 机读，必填）

```yaml
card_export:
  id: WS-G1
  card_key: PP-20260214-DOCS-GOVERNANCE::WS-G1
  title: 集成回归门禁
  type: gate
  lane: lane-gate
  hard_depends_on:
    - WS-01
    - WS-02
    - WS-03
    - WS-04
  soft_depends_on: []
  depends_on:
    - WS-01
    - WS-02
    - WS-03
    - WS-04
  file_whitelist:
    - docs/内部参考/任务拆解/2026-02-14_文档治理执行/parallel_plan.md
    - docs/内部参考/任务拆解/2026-02-14_文档治理执行/workstreams/WS-G1_集成回归门禁.md
  readonly_scope:
    - app/
    - web/
  owner_fields:
    - gate.g1.status
    - gate.g1.tc_matrix
    - gate.g1.owner_mapping
  check_cmd:
    - python3 scripts/docs_guard.py --strict
    - rg -n 'app/ai/workflow/data_graph.py' docs/开发文档/代码解读/多智能体工作流.md
    - rg -n '示例占位' docs/开发文档/工作流/开发工作流.md
  handoff_artifacts:
    - docs/内部参考/任务拆解/2026-02-14_文档治理执行/parallel_plan.md
  dod:
    - G1 门禁执行并完成责任 WS 归因
```
