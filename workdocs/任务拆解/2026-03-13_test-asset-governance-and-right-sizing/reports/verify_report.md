# 测试资产治理与单元测试收口 Verify Report

> 日期：2026-03-14  
> 主题：`2026-03-13_test-asset-governance-and-right-sizing`

## 1. 总结结论

| 项 | 结果 | 说明 |
| --- | --- | --- |
| 最终验收 | PASS | 需求、设计、任务、UAT 与当前证据可以闭环对齐 |
| 建议动作 | merge | 当前没有阻断放行的问题 |
| 放行前提 | 已满足 | canonical pytest 入口、脚本型验证入口、治理门禁、文档同步都已对齐 |

## 2. Context Check

| 项 | 期望上下文 | 实际上下文 | 结论 |
| --- | --- | --- | --- |
| worktree 路径 | `/Users/jijingkun/.codex/worktrees/999a/fastapi` | `/Users/jijingkun/.codex/worktrees/999a/fastapi` | PASS |
| 目标分支 | `codex/单元测试` | `codex/单元测试` | PASS |
| 目标主题 | `2026-03-13_test-asset-governance-and-right-sizing` | `workdocs/任务拆解/2026-03-13_test-asset-governance-and-right-sizing` | PASS |
| 仓库根 | `/Users/jijingkun/.codex/worktrees/999a/fastapi` | `/Users/jijingkun/.codex/worktrees/999a/fastapi` | PASS |
| HEAD | 当前工作提交 | `b038e5c812da9c2de68389936670b33d908e9e47` | PASS |

比对结论：`VERIFY_CONTEXT_MATCH`

## 3. 需求覆盖情况

| Requirement | 设计项 | 任务 | UAT | 关键证据 | 结果 |
| --- | --- | --- | --- | --- | --- |
| `FR-01` 资产角色可判定 | `D-01`、`D-03` | `T-01`、`T-03` | `TC-01`、`TC-03` | 测试治理文档出现 `formal_regression/scripted_flow/canonical`；`collect-only` 仅收 `tests/` | PASS |
| `FR-02` 正式回归必须有失败语义 | `D-04`、`D-05` | `T-04`、`T-05` | `TC-04`、`TC-05` | 兼容壳删除；治理 contract test 通过；`tests/unit/test_todo_nodes.py` 通过 | PASS |
| `FR-03` 真实依赖脚本退出默认 pytest | `D-02` | `T-02` | `TC-02` | `scripts/verify/*.py` 收口；`rg '^if __name__|def test_' scripts/verify/*.py` 无 `def test_` | PASS |
| `FR-04` 兼容入口不再双轨存活 | `D-04` | `T-04` | `TC-04` | `tests/unit/test_todo_graph_semantic_guard.py` 已删除；master runner 改指向新路径 | PASS |
| `FR-05` 文档与入口对齐 | `D-01`、`D-05` | `T-01`、`T-05` | `TC-01`、`TC-05` | 产品文档、测试指南、测试用例库、脚本注册表都改成新入口 | PASS |
| `FR-06` 默认正式回归入口收敛 | `D-03`、`D-05` | `T-03`、`T-05` | `TC-03` | `pyproject.toml` 为 `testpaths = ["tests"]`；`collect-only` 收 `196` 文件 / `1290` 用例 | PASS |
| `FR-07` 门禁资产与观察性资产可区分 | `D-01`、`D-05` | `T-01`、`T-05` | `TC-01`、`TC-05` | 测试用例库和脚本链路注册表分别承载正式回归与脚本型验证 | PASS |

## 4. 设计符合情况

| 设计判断 | 结果 | 说明 |
| --- | --- | --- |
| `tests/` 是唯一 canonical pytest 主入口 | PASS | `pyproject.toml` 与 `collect-only` 结果一致 |
| `scripts/verify/` 承接脚本型验证 | PASS | 当前收口 `11` 个脚本，且仍可独立执行 |
| 重复兼容壳被清理 | PASS | `tests/unit/test_todo_graph_semantic_guard.py` 不存在 |
| 旧 runner 不再反向引用旧路径 | PASS | `tests/run_master_test_suite.py` 已改为 `scripts/verify/*` |
| 文档不再把旧路径当 canonical | PASS | 稳定文档已统一改口径；历史归档未纳入真理源 |

## 5. Review 结论消费情况

| Review 项 | 最终状态 | 说明 |
| --- | --- | --- |
| `architecture_conformance` | PASS | 未出现新的双入口或错层 owner |
| `touched_scope_architecture` | PASS | 目录边界更清楚，没有回流到 `app/tests` |
| `complexity_conformance` | PASS | 多数改动是迁移、删除和路径收口，没有再堆 wrapper/fallback |
| `simplification_conformance` | PASS | review 发现的 `master runner` 残留与文档历史口径残留已关闭 |
| `duplicate_cleanup_conformance` | PASS | 旧兼容壳、旧路径引用和脚本伪装路径都被清掉或降级 |

## 6. 追溯链闭合情况

| 链路 | 结果 | 说明 |
| --- | --- | --- |
| requirements -> design | PASS | 需求与设计文档均存在且主题一致 |
| design -> implementation_plan | PASS | `T-01` 到 `T-05` 完整覆盖本轮设计项 |
| implementation_plan -> UAT | PASS | `TC-01` 到 `TC-05` 均能对上任务与证据 |
| code/doc changes -> evidence | PASS | 当前有 collect-only、定向回归、脚本执行、文档 grep 证据 |
| review -> verify | PASS | review 中识别的真实问题已在 verify 前关闭 |

## 7. UAT 结果

| UAT | 结果 | 证据 |
| --- | --- | --- |
| `TC-01` 三类资产角色对人可见 | PASS | `rg "formal_regression|scripted_flow|compatibility_entry|canonical"` 命中治理文档；产品文档命中 `TODO-TC-004` / `QS-TC-001` |
| `TC-02` 脚本型资产退出默认 pytest 发现路径 | PASS | `rg "scripts/verify|前置条件|期望产物|失败判定"` 命中；`rg '^if __name__|def test_' scripts/verify/*.py` 仅剩脚本入口 |
| `TC-03` 正式回归默认只认 canonical suite | PASS | `bash scripts/repo_python.sh` 命中仓库解释器；`collect-only` 结果只来自 `tests/` |
| `TC-04` 重复壳和弱测试已收口 | PASS | `tests/unit/test_todo_nodes.py` collect-only=`43` / run=`43 passed`；`todo_multiround.py` 已具备退出码并实际 `exit_code=0` |
| `TC-05` 治理门禁能阻止坏模式回流 | PASS | `tests/unit/test_test_asset_governance_contract.py` 当前 `5 passed` |

## 8. 关键证据

- `VK_RUNTIME_VENV=/Users/jijingkun/bojxAI/fastapi/venv bash scripts/repo_python.sh`  
  命中解释器：`/Users/jijingkun/bojxAI/fastapi/venv/bin/python`
- `VK_RUNTIME_VENV=/Users/jijingkun/bojxAI/fastapi/venv bash scripts/pytest_targeted.sh --collect-only -q tests`  
  结果：`196` 文件 / `1290` 用例
- `VK_RUNTIME_VENV=/Users/jijingkun/bojxAI/fastapi/venv bash scripts/pytest_targeted.sh tests/unit/test_test_asset_governance_contract.py tests/unit/test_handoff_detection.py tests/unit/test_data_agent.py tests/integration/test_todo_graph_integration.py tests/api/test_health.py tests/api/test_middlewares.py tests/api/test_user.py -q`  
  结果：`40 passed`
- `VK_RUNTIME_VENV=/Users/jijingkun/bojxAI/fastapi/venv bash scripts/pytest_targeted.sh tests/unit/test_test_asset_governance_contract.py tests/integration/test_model_switch.py tests/integration/test_skill_retrieval_smoke.py tests/integration/test_todo_db_integration.py -q`  
  结果：`18 passed`
- `VK_RUNTIME_VENV=/Users/jijingkun/bojxAI/fastapi/venv bash scripts/pytest_targeted.sh tests/unit/test_todo_nodes.py -q`  
  结果：`43 passed`
- `python scripts/verify/todo_multiround.py`  
  结果：`exit_code=0`

## 9. 残余风险

- `web/e2e` 的用例数这轮没有用 `pnpm test --list` 重新核对，因为当前 worktree 缺 `web/node_modules`；文档里已明确标成“待刷新”，没有伪装成最新实测值。
- 本轮没有做 full pytest 全仓重跑；当前放行依据是 canonical 入口收口证据、治理门禁、关键迁移回归与脚本型验证证据。
- 仍有一些非本轮引入的 warning，例如 `passlib` 的 `crypt` 弃用警告与部分 Pydantic v2 `config` 警告。

## 10. 下一步建议

- 建议动作：`merge`
- 若要继续强化证据完整度，下一步优先补两件事：
  1. 安装前端依赖后执行 `cd web && pnpm test --list`，把 Playwright 条目数刷新到文档。
  2. 未来若把更多脚本型验证转成正式门禁，再补一轮 full pytest / coverage 收口。
