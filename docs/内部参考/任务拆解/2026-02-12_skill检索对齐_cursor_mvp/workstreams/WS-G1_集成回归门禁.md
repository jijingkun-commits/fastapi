# 工作包说明

> WS 编号: WS-G1  
> 名称: 集成回归门禁  
> 类型: Gate（串行）

---

## 1. 目标与完成定义

### 1.1 目标

1. 对并行层产物执行统一集成回归。
2. 给出按 TC-ID 可追溯的门禁结论。
3. 完成 Gate 自动回填。

### 1.2 DoD

1. 门禁命令执行完成。
2. TC-ID 映射表完整。
3. `parallel_plan.md` Gate 区块已自动回填。

---

## 2. 文件边界

### 2.1 可修改（白名单）

- `docs/内部参考/任务拆解/2026-02-12_skill检索对齐_cursor_mvp/parallel_plan.md`
- `docs/内部参考/任务拆解/2026-02-12_skill检索对齐_cursor_mvp/workstreams/WS-G1_集成回归门禁.md`

### 2.2 禁止修改（黑名单）

- 业务实现文件

---

## 3. 实施步骤

1. 执行门禁命令并记录结果。
2. 维护 TC-ID 映射表并归属责任 WS。
3. 执行自动回填脚本更新 Gate 区块。

---

## 4. 门禁命令

1. `venv/bin/python -m pytest -q app/tests/test_skill_retrieval_smoke.py`
2. `venv/bin/python -m pytest -q tests -k "skill"`
3. `venv/bin/python scripts/docs_guard.py --strict`
4. `venv/bin/python scripts/backfill_gate_status.py --plan docs/内部参考/任务拆解/2026-02-12_skill检索对齐_cursor_mvp/parallel_plan.md`

---

## 5. TC-ID 映射表

| TC-ID | 门禁命令/检查项 | 自动化脚本或 pytest nodeid | 本次结果 | 责任 WS | 豁免/缺陷单 |
|---|---|---|---|---|---|
| TC-SKILL-META-01 | 元数据迁移验证 | `tests/unit -k "agent_skill"` | TBD | WS-01 | - |
| TC-SKILL-INGEST-01 | 导入与解析验证 | `tests/unit -k "skill and ingest"` | TBD | WS-02 | - |
| TC-SKILL-RET-01 | 检索链路冒烟 | `app/tests/test_skill_retrieval_smoke.py` | TBD | WS-03 | - |
| TC-SKILL-OBS-01 | 观测与回归验证 | `tests -k "skill"` | TBD | WS-04 | - |
| TC-GATE-DOC-01 | 文档治理 strict | `scripts/docs_guard.py --strict` | TBD | WS-G2 | - |

---

## 6. 浏览器测试触发评估

- 是否触发浏览器测试：否
- 原因：本轮仅后端/文档/测试资产改动，未改 `web/src/**` 交互链路。

---

## 7. 协作者自检卡（提交必填）

- 实际修改文件列表：
- 是否修改白名单外文件（是/否）：
- 测试命令与结果：
- 已知风险点：
- 回滚建议：

---

## card_export

```yaml
id: WS-G1
title: 集成回归门禁
type: gate
lane: gate
depends_on:
  - WS-01
  - WS-02
  - WS-03
  - WS-04
file_whitelist:
  - docs/内部参考/任务拆解/2026-02-12_skill检索对齐_cursor_mvp/parallel_plan.md
  - docs/内部参考/任务拆解/2026-02-12_skill检索对齐_cursor_mvp/workstreams/WS-G1_集成回归门禁.md
readonly_scope:
  - app/
owner_fields:
  - gate_g1_status
check_cmd: venv/bin/python scripts/backfill_gate_status.py --plan docs/内部参考/任务拆解/2026-02-12_skill检索对齐_cursor_mvp/parallel_plan.md
dod: G1门禁通过并完成自动回填
```

