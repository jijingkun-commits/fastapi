# 工作包说明

> WS 编号: WS-G1  
> 名称: 集成回归门禁  
> 类型: gate

---

## 0. 关联与来源

- 对应 `task_key`: `PP-20260213-ADMIN-OVERVIEW-COCKPIT`
- 来源主计划：`docs/内部参考/迭代需求/implementation_plan.md`
- 来源并行计划：`docs/内部参考/任务拆解/2026-02-13_管理后台总览驾驶舱/parallel_plan.md`

---

## 1. 目标

- 本包目标：统一执行后端、前端、E2E 与契约校验门禁，并定位责任 WS。
- 完成定义（DoD）：
  1. 所有门禁命令执行完成并记录结果。
  2. 失败项可追溯到责任 WS（WS-01~WS-04）。
  3. Gate 结果回填 `parallel_plan.md`。

---

## 2. 文件边界

### 可修改（白名单）

- `docs/内部参考/任务拆解/2026-02-13_管理后台总览驾驶舱/parallel_plan.md`
- `docs/内部参考/任务拆解/2026-02-13_管理后台总览驾驶舱/workstreams/WS-G1_集成回归门禁.md`
- `docs/内部参考/任务拆解/2026-02-13_管理后台总览驾驶舱/merge_checklist.md`（按需）

### 禁止修改（黑名单）

- 功能实现文件（`app/**`、`web/src/**`）

---

## 3. 状态与契约

- 可写字段：Gate 结果状态、责任 WS 归因。
- 只读字段：业务实现逻辑、SSE 契约定义。

---

## 4. 实施步骤

1. 依次执行 WS-01~WS-04 的最小验证命令。
2. 执行跨层联调与 E2E 验证。
3. 记录失败项并映射责任 WS。
4. 回填 Gate 状态到 `parallel_plan.md`。

---

## 5. 测试与验收

- 最小测试集：
  - `venv/bin/python -m pytest -q tests/unit/test_admin_overview_service.py`
  - `venv/bin/python -m pytest -q tests/api/test_admin_overview_api.py`
  - `cd web && pnpm tsc --noEmit`
  - `cd web && pnpm playwright test e2e/features/admin-overview.feature.cjs`
  - `venv/bin/python scripts/docs_guard.py --strict`

验收标准：
1. 核心命令通过，或失败项有责任 WS 与处置建议。
2. 不存在未归因门禁失败。

### 5.1 TC-ID 映射表（Gate WS 必填）

| TC-ID | 门禁命令/检查项 | 自动化脚本或 pytest nodeid | 本次结果 | 责任 WS | 豁免/缺陷单 |
|---|---|---|---|---|---|
| ADMIN-OV-TC-001 | 首屏 8 块渲染 | `web/e2e/features/admin-overview.feature.cjs` | 待执行 | WS-04 | |
| ADMIN-OV-TC-002 | 实时更新与降级轮询 | `web/e2e/features/admin-overview.feature.cjs` | 待执行 | WS-03, WS-04 | |
| ADMIN-OV-TC-003 | 健康分阈值映射 | `tests/unit/test_admin_overview_service.py` | 待执行 | WS-02 | |
| ADMIN-OV-TC-004 | 模块跳转链路 | `web/e2e/features/admin-overview.feature.cjs` | 待执行 | WS-04 | |
| ADMIN-OV-TC-005 | 成本预算占比口径 | `tests/api/test_admin_overview_api.py` | 待执行 | WS-02, WS-03 | |
| ADMIN-OV-TC-006 | 权限与接口契约 | `tests/api/test_admin_overview_api.py` | 待执行 | WS-03 | |

### 5.2 浏览器测试（触发式）

- 是否触发浏览器测试（是/否）：是
- 触发依据（命中项）：存在前端驾驶舱改造与跨端实时契约消费。
- 执行命令：`cd web && pnpm playwright test e2e/features/admin-overview.feature.cjs`
- 结果与证据路径：`web/playwright-report/`（执行后回填）
- 未执行原因（如不触发则必填）：N/A

---

## 6. 风险与回滚

- 主要风险：Gate 仅验证单点命令，遗漏端到端性能风险。
- 回滚点：若 Gate 失败，阻断 `WS-G2`，回退至对应责任 WS 修复。

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
  id: WS-G1
  card_key: PP-20260213-ADMIN-OVERVIEW-COCKPIT::WS-G1
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
    - docs/内部参考/任务拆解/2026-02-13_管理后台总览驾驶舱/parallel_plan.md
    - docs/内部参考/任务拆解/2026-02-13_管理后台总览驾驶舱/workstreams/WS-G1_集成回归门禁.md
  readonly_scope:
    - app/
    - web/src/
  owner_fields:
    - gate.g1.status
    - gate.g1.tc_matrix
  check_cmd:
    - venv/bin/python -m pytest -q tests/unit/test_admin_overview_service.py
    - venv/bin/python -m pytest -q tests/api/test_admin_overview_api.py
    - cd web && pnpm tsc --noEmit
    - cd web && pnpm playwright test e2e/features/admin-overview.feature.cjs
    - venv/bin/python scripts/docs_guard.py --strict
  handoff_artifacts:
    - docs/内部参考/任务拆解/2026-02-13_管理后台总览驾驶舱/parallel_plan.md
  dod:
    - G1 门禁命令执行并完成失败项责任 WS 归因
```
