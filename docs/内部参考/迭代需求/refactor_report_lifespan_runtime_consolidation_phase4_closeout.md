### 1) 重构摘要
- phase_scope: `Phase 4 收尾重构`
- task_id: `lifespan-runtime-consolidation-phase4-closeout`
- card_id: `none`
- pr_id: `none`
- scope: `app/ai/workflow/runtime_graph_provider.py`, `app/ai/workflow/multi_agent_graph.py`, `app/ai/workflow/__init__.py`, `app/core/runtime.py`, `app/services/permission_service.py`, `app/services/result_enrichment_rule_service.py`, `app/api/v1/endpoints/data_admin_api.py`, `tests/unit/test_multi_agent_graph_runtime_registry.py`, `tests/unit/test_permission_service_runtime_registry.py`, `tests/unit/test_result_enrichment_rule_service_runtime_registry.py`
- execution_mode: `single`
- final_decision: `PASS`
- markers: `TEAM_UNAVAILABLE_FALLBACK`, `APPLY_PATCH_TOOL_UNAVAILABLE_FALLBACK`

### 2) 重构切片清单
| slice_id | target | refactor_goal | key_change | status |
|---|---|---|---|---|
| `RF4-CLOSEOUT-01` | `app/ai/workflow/runtime_graph_provider.py`, `app/ai/workflow/multi_agent_graph.py` | 拆分 graph runtime owner | getter / reset / cache / lock 外移到 provider，大文件只保留图定义与编译 | `done` |
| `RF4-CLOSEOUT-02` | `app/services/permission_service.py` | 删除双 owner | 删除 `__new__`、类级共享缓存/锁、模块级 `_permission_service`，改为 registry-backed getter | `done` |
| `RF4-CLOSEOUT-03` | `app/services/result_enrichment_rule_service.py` | 删除模块级 singleton | 删除 `_service_singleton`，保留实例级 TTL cache，改为 registry-backed getter | `done` |
| `RF4-CLOSEOUT-04` | `app/api/v1/endpoints/data_admin_api.py` | 删除导入期实例化 | 删除 `_rule_service = get_result_enrichment_rule_service()`，改为 handler 按需取用共享实例 | `done` |
| `RF4-CLOSEOUT-05` | `tests/unit/test_multi_agent_graph_runtime_registry.py`, `tests/unit/test_permission_service_runtime_registry.py`, `tests/unit/test_result_enrichment_rule_service_runtime_registry.py` | 锁定 owner 收口行为 | 验证 registry 复用与 reset 重建行为稳定 | `done` |

### 3) 行为等价证据
| contract | verification | result | evidence |
|---|---|---|---|
| `workflow package 继续导出 get_multi_agent_graph，对外调用不变` | `VK_RUNTIME_VENV=/tmp/codex-py311 bash scripts/pytest_targeted.sh tests/unit/test_app_runtime_bootstrap.py` | `PASS` | `2 passed（包含 warmup 顺序校验）` |
| `PermissionService 共享实例改由 registry 持有，reset 后可重建` | `VK_RUNTIME_VENV=/tmp/codex-py311 bash scripts/pytest_targeted.sh tests/unit/test_permission_service.py tests/unit/test_permission_service_runtime_registry.py` | `PASS` | `25 passed` |
| `ResultEnrichmentRuleService 共享实例改由 registry 持有，导入期不再偷建实例` | `VK_RUNTIME_VENV=/tmp/codex-py311 bash scripts/pytest_targeted.sh tests/unit/test_result_enrichment_rule_service.py tests/unit/test_result_enrichment_rule_service_runtime_registry.py tests/api/test_access_admin_api.py` | `PASS` | `32 passed` |
| `Phase 4 收尾相关回归无行为漂移` | `VK_RUNTIME_VENV=/tmp/codex-py311 bash scripts/pytest_targeted.sh tests/unit/test_permission_service.py tests/unit/test_permission_service_runtime_registry.py tests/unit/test_result_enrichment_rule_service.py tests/unit/test_result_enrichment_rule_service_runtime_registry.py tests/unit/test_app_runtime_bootstrap.py tests/unit/test_cache_registry.py tests/unit/test_sql_rewriter.py tests/api/test_access_admin_api.py` | `PASS` | `79 passed` |
| `差异格式正确` | `git diff --check` | `PASS` | `无输出` |

### 4) 风险与遗留
- unresolved_items:
  - `app/ai/workflow/multi_agent_graph.py` 仍然偏大，但已不再混入 runtime owner；后续若继续治理，应只做图定义/节点职责拆分。
  - `.venv -> venv` 断链仍未修复，当前验证继续依赖 `VK_RUNTIME_VENV=/tmp/codex-py311`。
- followup_tasks:
  - 若后续发现新的应用级共享实例 owner，继续按 `Phase 4` 口径并入 registry，而不是新开阶段编号。
  - 若未来引入显式依赖注入，可让 request/service 从 `app.state.runtime` 读取共享实例，但在那之前禁止回退到模块全局 singleton。
- refactor_report_path: `docs/内部参考/迭代需求/refactor_report_lifespan_runtime_consolidation_phase4_closeout.md`

### 5) 下一步
1. 进入 `/jjk-review` 做结构复审。
2. 进入 `/jjk-verify` 做最终验收与运行态确认。
