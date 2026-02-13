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

### 4.1 本次执行说明（2026-02-13）

- 本地 `venv` 为 Windows 目录结构（`venv/Scripts`），不存在 `venv/bin/python`。
- 为保证门禁命令可执行，本次等价替换为 `python3` 执行对应命令，并在 pytest 增加 `-o addopts=''` 避免环境缺少 `pytest-cov` 插件导致参数错误。
- 回填命令实际执行：
  - `python3 scripts/backfill_gate_status.py --plan docs/内部参考/任务拆解/2026-02-12_skill检索对齐_cursor_mvp/parallel_plan.md --pytest-cmd "python3 -m pytest -q app/tests/test_skill_retrieval_smoke.py tests -k \"skill\" -o addopts=''" --docs-cmd "python3 scripts/docs_guard.py --strict"`

---

## 5. TC-ID 映射表

| TC-ID | 门禁命令/检查项 | 自动化脚本或 pytest nodeid | 本次结果 | 责任 WS | 豁免/缺陷单 |
|---|---|---|---|---|---|
| TC-SKILL-META-01 | 元数据迁移验证 | `tests/unit -k "agent_skill"` | 通过（包含于 `tests -k "skill"` 回归，整体 21 passed） | WS-01 | - |
| TC-SKILL-INGEST-01 | 导入与解析验证 | `tests/unit -k "skill and ingest"` | 通过（包含于 `tests -k "skill"` 回归，整体 21 passed） | WS-02 | - |
| TC-SKILL-RET-01 | 检索链路冒烟 | `app/tests/test_skill_retrieval_smoke.py` | 跳过（1 skipped；`t_agent_skills` 缺少 `is_enabled/auto_enabled/priority/scope/trigger_phrases/conflicts_with`） | WS-03 | 缺少迁移后列，需补齐数据库状态后复跑 |
| TC-SKILL-OBS-01 | 观测与回归验证 | `tests -k "skill"` | 通过（21 passed, 354 deselected） | WS-04 | - |
| TC-GATE-DOC-01 | 文档治理 strict | `scripts/docs_guard.py --strict` | 失败（4 error：`docs/SUMMARY.md` 指向 `内部参考/迭代需求/requirements.md` 与 `implementation_plan.md` 断链） | WS-G2 | 待 WS-G2 修复文档链接后重跑 |

---

## 6. 浏览器测试触发评估

- 是否触发浏览器测试：否
- 原因：本轮仅后端/文档/测试资产改动，未改 `web/src/**` 交互链路。

---

## 7. 协作者自检卡（提交必填）

- 实际修改文件列表：
  - `docs/内部参考/任务拆解/2026-02-12_skill检索对齐_cursor_mvp/parallel_plan.md`
  - `docs/内部参考/任务拆解/2026-02-12_skill检索对齐_cursor_mvp/workstreams/WS-G1_集成回归门禁.md`
- 是否修改白名单外文件（是/否）：否
- 测试命令与结果：
  - `python3 -m pytest -q app/tests/test_skill_retrieval_smoke.py -o addopts='' -rs` -> `1 skipped`
  - `python3 -m pytest -q tests -k "skill" -o addopts=''` -> `21 passed, 354 deselected`
  - `python3 scripts/docs_guard.py --strict` -> `4 error`
  - `python3 scripts/backfill_gate_status.py --plan ... --pytest-cmd ... --docs-cmd ...` -> 回填成功，命令以 `docs_guard` 失败退出
- 已知风险点：
  - 文档断链未修复前，`docs_guard --strict` 持续阻塞 Gate 通过。
  - Smoke 用例当前因数据库列缺失被跳过，无法证明检索链路在真实库结构下可用。
- 回滚建议：
  - 回滚 `parallel_plan.md` 与本文件到回填前版本，重新执行 Gate 命令。

---

## 8. Gate 结论

- `WS-G1` 已完成门禁命令执行与状态回填。
- 当前结论：**未通过**（阻塞项为文档断链与 smoke 用例跳过）。
- 建议流转：由 `WS-G2` 先修复 `docs/SUMMARY.md` 断链；由 `WS-03`/`WS-01` 补齐 smoke 依赖列后复跑 G1。

---

## card_export

```yaml
card_export:
  id: WS-G1
  card_key: PP-20260213-SKILL-RETRIEVAL-MVP::WS-G1
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
    - docs/内部参考/任务拆解/2026-02-12_skill检索对齐_cursor_mvp/parallel_plan.md
    - docs/内部参考/任务拆解/2026-02-12_skill检索对齐_cursor_mvp/workstreams/WS-G1_集成回归门禁.md
  readonly_scope:
    - app/
  owner_fields:
    - gate.g1.status
    - gate.g1.report
  check_cmd:
    - venv/bin/python -m pytest -q app/tests/test_skill_retrieval_smoke.py
    - venv/bin/python -m pytest -q tests -k "skill"
    - venv/bin/python scripts/docs_guard.py --strict
    - venv/bin/python scripts/backfill_gate_status.py --plan docs/内部参考/任务拆解/2026-02-12_skill检索对齐_cursor_mvp/parallel_plan.md
  handoff_artifacts:
    - docs/内部参考/任务拆解/2026-02-12_skill检索对齐_cursor_mvp/parallel_plan.md
    - docs/内部参考/任务拆解/2026-02-12_skill检索对齐_cursor_mvp/workstreams/WS-G1_集成回归门禁.md
  dod:
    - G1 门禁命令通过并完成自动回填
```
