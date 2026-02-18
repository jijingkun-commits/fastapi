# 工作包说明

> WS 编号: WS-G2
> 名称: 文档终稿门禁
> 类型: gate

---

## 0. 关联与来源

- 对应 `task_key`: `PP-20260216-TOOL-GOVERNANCE`
- 来源主计划：`docs/内部参考/迭代需求/ai_tools_governance_implementation_plan.md`
- 来源并行计划：`docs/内部参考/任务拆解/2026-02-16_AI工具治理架构并行拆解/parallel_plan.md`

---

## 1. 目标

- 本包目标：完成治理改造相关文档同步、索引收口与门禁回填。
- 完成定义（DoD）：
  1. 架构文档、配置文档、示例环境变量与实现保持一致。
  2. `SUMMARY` 覆盖新增拆解目录与关键文档入口。
  3. `docs_guard --strict` 通过并回填 Gate 结论。

---

## 2. 文件边界

### 可修改（白名单）

- `docs/开发文档/架构设计/AI模块设计.md`
- `docs/开发文档/快速入门/配置说明.md`
- `.env.example`
- `docs/SUMMARY.md`
- `docs/内部参考/迭代需求/ai_tools_governance_implementation_plan.md`
- `docs/内部参考/任务拆解/2026-02-16_AI工具治理架构并行拆解/parallel_plan.md`
- `docs/内部参考/任务拆解/2026-02-16_AI工具治理架构并行拆解/workstreams/WS-G2_文档终稿门禁.md`

### 禁止修改（黑名单）

- `app/**`
- `web/**`

---

## 3. 状态与契约

- 可写字段：`gate.g2.docs_sync`、`gate.g2.summary_index`、`gate.g2.final_status`。
- 只读字段：业务代码实现、G0 契约冻结 required 字段。

---

## 4. 实施步骤

1. 按代码改造范围同步 `AI模块设计.md` 与 `配置说明.md`。
2. 校准 `.env.example` 中治理相关开关与默认值。
3. 在 `docs/SUMMARY.md` 补齐本轮拆解目录入口。
4. 回填 `parallel_plan.md` 的 Gate 收口状态并记录证据。

---

## 5. 测试与验收

- 最小测试集：
  - `python3 scripts/docs_guard.py --strict`
- 验收标准：
  1. 文档路径、配置键、开关命名一致。
  2. 索引入口可达，`summary_coverage` 不下降。

### 5.1 TC-ID 映射表（Gate WS 必填）

| TC-ID | 门禁命令/检查项 | 自动化脚本或 pytest nodeid | 本次结果 | 责任 WS | 豁免/缺陷单 |
|---|---|---|---|---|---|
| TG-DOC-001 | 文档严格门禁 | `python3 scripts/docs_guard.py --strict` | 待执行 | WS-G2 | - |
| TG-DOC-002 | 文档同步检查 | `docs/开发文档/架构设计/AI模块设计.md` 人工审阅 | 待执行 | WS-G2 | - |
| TG-DOC-003 | 索引可达性 | `docs/SUMMARY.md` 人工审阅 | 待执行 | WS-G2 | - |

### 5.2 浏览器测试（触发式）

- 是否触发浏览器测试（是/否）：否
- 触发依据（命中项）：文档终稿门禁，无前端交互变更。
- 执行命令：N/A
- 结果与证据路径：N/A
- 未执行原因：非浏览器测试范围。

---

## 6. 风险与回滚

- 主要风险：文档与实现版本漂移，影响后续评审与交接。
- 回滚点：按文档文件粒度回退并重跑 `docs_guard`。

---

## 7. 协作者自检卡（提交必填）

- 实际修改文件列表：
- 是否修改了白名单外文件（是/否）：
- 测试命令与结果：
- 已知风险点：
- 回滚建议：

---

## 8. card_export（机读，必填）

```yaml
card_export:
  id: WS-G2
  card_key: PP-20260216-TOOL-GOVERNANCE::WS-G2
  title: 文档终稿门禁
  type: gate
  lane: lane-gate
  hard_depends_on:
    - WS-G1
  soft_depends_on: []
  depends_on:
    - WS-G1
  file_whitelist:
    - docs/开发文档/架构设计/AI模块设计.md
    - docs/开发文档/快速入门/配置说明.md
    - .env.example
    - docs/SUMMARY.md
    - docs/内部参考/迭代需求/ai_tools_governance_implementation_plan.md
    - docs/内部参考/任务拆解/2026-02-16_AI工具治理架构并行拆解/parallel_plan.md
    - docs/内部参考/任务拆解/2026-02-16_AI工具治理架构并行拆解/workstreams/WS-G2_文档终稿门禁.md
  readonly_scope:
    - app/
    - web/
  owner_fields:
    - gate.g2.docs_sync
    - gate.g2.summary_index
    - gate.g2.final_status
  check_cmd:
    - python3 scripts/docs_guard.py --strict
  handoff_artifacts:
    - docs/SUMMARY.md
    - docs/开发文档/架构设计/AI模块设计.md
  dod:
    - 文档终稿门禁通过并完成收口回填
```
