# 工作包说明

> WS 编号: WS-G1
> 名称: 集成回归门禁
> 类型: gate

---

## 0. 关联与来源

- 对应 `task_key`: `PP-20260215-ASKDATA-DUAL-ROLE-PERMISSION`
- 来源主计划：`docs/内部参考/迭代需求/askdata_dual_role_permission_implementation_plan.md`
- 来源并行计划：`docs/内部参考/任务拆解/2026-02-15_问数双角色权限并行拆解/parallel_plan.md`

---

## 1. 目标

- 本包目标：执行双角色权限全链路门禁，并完成失败项归因。
- 完成定义（DoD）：
  1. 核心单测与 API 测试通过。
  2. 失败项具备责任 WS 映射。
  3. 回填 `parallel_plan.md` Gate 状态。

---

## 2. 文件边界

### 可修改（白名单）

- `docs/内部参考/任务拆解/2026-02-15_问数双角色权限并行拆解/parallel_plan.md`
- `docs/内部参考/任务拆解/2026-02-15_问数双角色权限并行拆解/workstreams/WS-G1_集成回归门禁.md`

### 禁止修改（黑名单）

- `app/**`
- `web/**`

---

## 3. 状态与契约

- 可写字段：`gate.g1.status`、`gate.g1.tc_matrix`、`gate.g1.owner_mapping`。
- 只读字段：业务实现内容。

---

## 4. 实施步骤

1. 执行 WS-01/WS-02/WS-03 的最小测试命令。
2. 执行权限回归命令集。
3. 汇总失败项并映射责任 WS。
4. 回填 Gate 状态与结论。

---

## 5. 测试与验收

- 最小测试集：
  - `venv/bin/python -m pytest -q tests/unit/test_sql_policy_decision.py tests/unit/test_sql_rewriter.py`
  - `venv/bin/python -m pytest -q tests/api/test_access_admin_api.py`
  - `python3 scripts/docs_guard.py --strict`

验收标准：

1. 门禁命令全部通过，或失败项均可归因。
2. 不存在“无法归属责任 WS”的阻塞项。

### 5.1 TC-ID 映射表（Gate WS 必填）

| TC-ID | 门禁命令/检查项 | 自动化脚本或 nodeid | 本次结果 | 责任 WS | 豁免/缺陷单 |
|---|---|---|---|---|---|
| DP-GATE-001 | 权限策略决策回归 | `tests/unit/test_sql_policy_decision.py` | PASS | WS-02 | - |
| DP-GATE-002 | SQL 重写与默认隔离回归 | `tests/unit/test_sql_rewriter.py` | PASS | WS-02 | - |
| DP-GATE-003 | 权限配置 API 回归 | `tests/api/test_access_admin_api.py` | PASS | WS-03 | - |
| DP-GATE-004 | 文档门禁 | `python3 scripts/docs_guard.py --strict` | PASS | WS-G2 | - |

### 5.2 浏览器测试（触发式）

- 是否触发浏览器测试（是/否）：否
- 触发依据（命中项）：本轮 gate 仅覆盖后端与文档门禁。
- 执行命令：N/A
- 结果与证据路径：N/A
- 未执行原因：未包含前端页面交付。

---

## 6. 风险与回滚

- 主要风险：门禁未覆盖关键拒绝路径导致带病上线。
- 回滚点：按 WS 粒度回退，并阻断后续 Gate。

---

## 7. 协作者自检卡（提交必填）

- 实际修改文件列表：
  - `docs/内部参考/任务拆解/2026-02-15_问数双角色权限并行拆解/parallel_plan.md`
  - `docs/内部参考/任务拆解/2026-02-15_问数双角色权限并行拆解/workstreams/WS-G1_集成回归门禁.md`
- 是否修改了白名单外文件（是/否）：否
- 测试命令与结果：
  - `set -a; source .env.dev; set +a; .vibe/venv/bin/python -m pytest -q tests/unit/test_sql_policy_decision.py tests/unit/test_sql_rewriter.py`（PASS）
  - `set -a; source .env.dev; set +a; .vibe/venv/bin/python -m pytest -q tests/api/test_access_admin_api.py`（PASS）
  - `python3 scripts/docs_guard.py --strict`（PASS）
  - `python3 scripts/backfill_gate_status.py --plan docs/内部参考/任务拆解/2026-02-15_问数双角色权限并行拆解/parallel_plan.md --pytest-cmd "set -a; source .env.dev; set +a; .vibe/venv/bin/python -m pytest -q tests/unit/test_sql_policy_decision.py tests/unit/test_sql_rewriter.py tests/api/test_access_admin_api.py" --tsc-cmd ":" --lint-cmd ":" --docs-cmd "python3 scripts/docs_guard.py --strict"`（PASS）
- 已知风险点：`tsc/lint` 在本 Gate 按非前端场景以 no-op 执行，已在回填命令中显式声明。
- 回滚建议：回滚 `parallel_plan.md` 与本 WS 文档后，重新执行 Gate 命令并自动回填。

---

## 8. card_export（/vk 机读，必填）

```yaml
card_export:
  id: WS-G1
  card_key: PP-20260215-ASKDATA-DUAL-ROLE-PERMISSION::WS-G1
  title: 集成回归门禁
  type: gate
  lane: lane-gate
  hard_depends_on:
    - WS-01
    - WS-02
    - WS-03
  soft_depends_on: []
  depends_on:
    - WS-01
    - WS-02
    - WS-03
  file_whitelist:
    - docs/内部参考/任务拆解/2026-02-15_问数双角色权限并行拆解/parallel_plan.md
    - docs/内部参考/任务拆解/2026-02-15_问数双角色权限并行拆解/workstreams/WS-G1_集成回归门禁.md
  readonly_scope:
    - app/
    - web/
  owner_fields:
    - gate.g1.status
    - gate.g1.tc_matrix
    - gate.g1.owner_mapping
  check_cmd:
    - venv/bin/python -m pytest -q tests/unit/test_sql_policy_decision.py tests/unit/test_sql_rewriter.py
    - venv/bin/python -m pytest -q tests/api/test_access_admin_api.py
    - python3 scripts/docs_guard.py --strict
  handoff_artifacts:
    - docs/内部参考/任务拆解/2026-02-15_问数双角色权限并行拆解/parallel_plan.md
  dod:
    - G1 门禁执行并完成责任 WS 归因
```
