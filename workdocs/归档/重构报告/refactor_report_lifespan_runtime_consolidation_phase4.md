### 1) 重构摘要
- task_id: `lifespan-runtime-consolidation-phase4`
- card_id: `none`
- pr_id: `none`
- scope: `app/core/cache_registry.py`, `app/core/runtime.py`, `app/ai/workflow/multi_agent_graph.py`, `app/services/asset_service.py`, `tests/unit/test_*runtime_registry.py`
- execution_mode: `single`
- final_decision: `PASS`
- markers: `TEAM_UNAVAILABLE_FALLBACK`

### 2) 重构切片清单
| slice_id | target | refactor_goal | key_change | status |
|---|---|---|---|---|
| `RF4-01` | `app/core/cache_registry.py` | 让 registry 承接非 dict 共享资源 | 新增 `get/set/get_or_create`，不再只支持 dict cache | `done` |
| `RF4-02` | `app/ai/workflow/multi_agent_graph.py` | 收口 graph cache owner | 图实例缓存迁移到 registry；保留 `get_multi_agent_graph()` API；补 `reset_multi_agent_graph_runtime()` | `done` |
| `RF4-03` | `app/services/asset_service.py` | 收口 asset service owner | 删除模块级 `_asset_service` owner，改为 registry-backed getter | `done` |
| `RF4-04` | `app/core/runtime.py` | 统一 runtime 启动/清理顺序 | 启动前显式 reset graph runtime；关闭时加入 graph reset cleanup callback | `done` |
| `RF4-05` | `tests/unit/*` | 锁定行为等价 | 新增 graph / asset runtime owner 测试，更新 bootstrap 断言 | `done` |

### 3) 行为等价证据
| contract | verification | result | evidence |
|---|---|---|---|
| `graph cache owner 改为 runtime registry，getter API 不变` | `VK_RUNTIME_VENV=/tmp/codex-py311 bash scripts/pytest_targeted.sh tests/unit/test_multi_agent_graph_runtime_registry.py -q` | `PASS` | `2 passed` |
| `asset service owner 改为 runtime registry，getter API 不变` | `VK_RUNTIME_VENV=/tmp/codex-py311 bash scripts/pytest_targeted.sh tests/unit/test_asset_service_runtime_registry.py app/tests/test_chat_assets.py -q` | `PASS` | `相关用例通过` |
| `runtime 启动顺序包含 graph reset，仍能完成 warmup` | `VK_RUNTIME_VENV=/tmp/codex-py311 bash scripts/pytest_targeted.sh tests/unit/test_app_runtime_bootstrap.py tests/unit/test_app_runtime.py tests/unit/test_app_runtime_lifespan.py -q` | `PASS` | `相关用例通过` |
| `Phase 1~4 相关回归无行为漂移` | `VK_RUNTIME_VENV=/tmp/codex-py311 bash scripts/pytest_targeted.sh tests/unit/test_cache_registry.py tests/unit/test_asset_service_runtime_registry.py tests/unit/test_multi_agent_graph_runtime_registry.py tests/unit/test_data_graph_intent_policy_cache_registry.py tests/unit/test_access_admin_key_compat.py tests/unit/test_db_session_runtime.py tests/unit/test_metric_service_engine_sharing.py tests/unit/test_app_runtime.py tests/unit/test_app_runtime_bootstrap.py tests/unit/test_app_runtime_lifespan.py tests/unit/test_postgres_checkpointer_pooling.py tests/unit/test_observability.py tests/unit/test_vision_tool_api_wire.py app/tests/test_chat_assets.py -q` | `PASS` | `56 passed` |
| `差异格式正确` | `git diff --check` | `PASS` | `无输出` |

### 4) 风险与遗留
- unresolved_items:
  - `app/ai/workflow/multi_agent_graph.py` 仍是超大文件；本轮只收口 owner，没有继续拆业务图构建切片。
  - `.venv -> venv` 断链仍未修复，当前验证继续依赖 `VK_RUNTIME_VENV=/tmp/codex-py311`。
- followup_tasks:
  - graph provider 外移已在 `workdocs/归档/重构报告/refactor_report_lifespan_runtime_consolidation_phase4_closeout.md` 收口，不再单列新阶段。
  - 若未来全面引入 request 级注入，再把深层 service/tool 从 getter 过渡到 `request.app.state.runtime` 显式取依赖。
- refactor_report_path: `workdocs/归档/重构报告/refactor_report_lifespan_runtime_consolidation_phase4.md`

### 5) 下一步
1. 进入 `/jjk-review` 做结构复审。
2. 进入 `/jjk-verify` 做最终验收与运行态确认。
