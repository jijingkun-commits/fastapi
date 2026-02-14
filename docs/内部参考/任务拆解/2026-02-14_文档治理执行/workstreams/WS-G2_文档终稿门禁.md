# 工作包说明

> WS 编号: WS-G2
> 名称: 文档终稿门禁
> 类型: gate

---

## 0. 关联与来源

- 对应 `task_key`: `PP-20260214-DOCS-GOVERNANCE`
- 来源主计划：`docs/内部参考/迭代需求/docs_governance_implementation_plan.md`
- 来源并行计划：`docs/内部参考/任务拆解/2026-02-14_文档治理执行/parallel_plan.md`

---

## 1. 目标

- 本包目标：完成文档终稿收口，确保策略、索引、门禁三位一体闭环。
- 完成定义（DoD）：
  1. `文档梳理与重构方案` 已回填执行结果。
  2. `迭代需求` 计划文档与并行拆解结果可追溯。
  3. `SUMMARY` 与任务拆解目录索引一致。

---

## 2. 文件边界

### 可修改（白名单）

- `docs/文档梳理与重构方案_2026-02-13.md`
- `docs/SUMMARY.md`
- `docs/内部参考/迭代需求/docs_governance_requirements.md`
- `docs/内部参考/迭代需求/docs_governance_implementation_plan.md`
- `docs/内部参考/任务拆解/2026-02-14_文档治理执行/parallel_plan.md`
- `docs/内部参考/任务拆解/2026-02-14_文档治理执行/workstreams/WS-G2_文档终稿门禁.md`

### 禁止修改（黑名单）

- `app/**`
- `web/**`

---

## 3. 状态与契约

- 可写字段：终稿状态、追溯索引、发布摘要。
- 只读字段：已冻结的治理规则定义。

---

## 4. 实施步骤

1. 对照 `WS-01..WS-04` 回填治理方案执行状态。
2. 核对 `SUMMARY` 与拆解目录入口完整性。
3. 执行 docs_guard 并确认终稿可发布。

---

## 5. 测试与验收

- 最小测试集：
  - `python3 scripts/docs_guard.py --strict`
- 验收标准：
  1. 文档矩阵可追溯。
  2. 索引、策略、执行状态无冲突。

### 5.1 TC-ID 映射表（Gate WS 必填）

| TC-ID | 门禁命令/检查项 | 自动化脚本或 nodeid | 本次结果 | 责任 WS | 豁免/缺陷单 |
|---|---|---|---|---|---|
| DOC-FINAL-001 | 终稿门禁 | `python3 scripts/docs_guard.py --strict` | 待执行 | WS-G2 | |
| DOC-FINAL-002 | 执行状态回填 | `docs/文档梳理与重构方案_2026-02-13.md` 人工审阅 | 待执行 | WS-G2 | |
| DOC-FINAL-003 | 拆解索引完整性 | `docs/SUMMARY.md` 人工审阅 | 待执行 | WS-G2 | |

### 5.2 浏览器测试（触发式）

- 是否触发浏览器测试（是/否）：否
- 触发依据（命中项）：终稿仅文档收口，无 UI 流程。
- 执行命令：N/A
- 结果与证据路径：N/A
- 未执行原因：非浏览器测试范围。

---

## 6. 风险与回滚

- 主要风险：终稿阶段遗漏索引，导致门禁失败。
- 回滚点：回退终稿回填内容并重跑门禁。

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
  id: WS-G2
  card_key: PP-20260214-DOCS-GOVERNANCE::WS-G2
  title: 文档终稿门禁
  type: gate
  lane: lane-gate
  hard_depends_on:
    - WS-G1
  soft_depends_on: []
  depends_on:
    - WS-G1
  file_whitelist:
    - docs/文档梳理与重构方案_2026-02-13.md
    - docs/SUMMARY.md
    - docs/内部参考/迭代需求/docs_governance_requirements.md
    - docs/内部参考/迭代需求/docs_governance_implementation_plan.md
    - docs/内部参考/任务拆解/2026-02-14_文档治理执行/parallel_plan.md
    - docs/内部参考/任务拆解/2026-02-14_文档治理执行/workstreams/WS-G2_文档终稿门禁.md
  readonly_scope:
    - app/
    - web/
  owner_fields:
    - gate.g2.status
    - docs.final.summary_index
    - docs.final.traceability
  check_cmd:
    - python3 scripts/docs_guard.py --strict
  handoff_artifacts:
    - docs/文档梳理与重构方案_2026-02-13.md
    - docs/SUMMARY.md
  dod:
    - 文档终稿门禁通过并完成收口回填
```
