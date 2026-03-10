### 1) 重构摘要
- task_id: `lifespan-runtime-consolidation-phase3`
- card_id: `none`
- pr_id: `none`
- scope: `app/main.py`, `app/core/runtime.py`, `app/core/cache_registry.py`, `app/db/session.py`, `app/services/metric_service.py`, `app/ai/workflow/data_graph.py`, `app/ai/semantic/data_access_control.py`
- execution_mode: `single`
- final_decision: `PASS`
- markers: `TEAM_UNAVAILABLE_FALLBACK`

### 2) 重构切片清单
| slice_id | target | refactor_goal | key_change | status |
|---|---|---|---|---|
| `RF-01` | `app/main.py#lifespan` | 缩短生命周期编排链路 | 仅保留 `build_runtime()` + `runtime.aclose()` | `done` |
| `RF-02` | `app/core/runtime.py` | 收敛应用级 owner | 提取 runtime owner，集中启动/清理 DB、checkpointer、tracer、warmup 状态 | `done` |
| `RF-03` | `app/db/session.py`, `app/services/metric_service.py` | 统一数据库资源 owner | metric service 复用共享 engine；DB dispose 下沉到 runtime | `done` |
| `RF-04` | `app/core/cache_registry.py`, `app/ai/workflow/data_graph.py`, `app/ai/semantic/data_access_control.py` | 收敛进程级缓存 | 新增命名缓存注册表，迁移 data_graph 与 askdata 配置缓存 | `done` |
| `RF-05` | `tests/unit/*` | 锁定行为等价 | 补 runtime / DB / cache registry 回归测试 | `done` |

### 3) 行为等价证据
| contract | verification | result | evidence |
|---|---|---|---|
| `lifespan 仅做编排，runtime 接管启动/清理` | `VK_RUNTIME_VENV=/tmp/codex-py311 bash scripts/pytest_targeted.sh tests/unit/test_app_runtime.py tests/unit/test_app_runtime_bootstrap.py tests/unit/test_app_runtime_lifespan.py -q` | `PASS` | `7 passed` |
| `cache registry 承接 data_graph / askdata 进程级缓存` | `VK_RUNTIME_VENV=/tmp/codex-py311 bash scripts/pytest_targeted.sh tests/unit/test_cache_registry.py tests/unit/test_data_graph_intent_policy_cache_registry.py tests/unit/test_access_admin_key_compat.py -q` | `PASS` | `相关用例通过` |
| `Phase 1~3 相关回归无行为漂移` | `VK_RUNTIME_VENV=/tmp/codex-py311 bash scripts/pytest_targeted.sh tests/unit/test_cache_registry.py tests/unit/test_data_graph_intent_policy_cache_registry.py tests/unit/test_access_admin_key_compat.py tests/unit/test_db_session_runtime.py tests/unit/test_metric_service_engine_sharing.py tests/unit/test_app_runtime.py tests/unit/test_app_runtime_bootstrap.py tests/unit/test_app_runtime_lifespan.py tests/unit/test_postgres_checkpointer_pooling.py tests/unit/test_observability.py app/tests/test_chat_assets.py -q` | `PASS` | `47 passed` |
| `差异格式正确` | `git diff --check` | `PASS` | `无输出` |

### 4) 风险与遗留
- unresolved_items:
  - 本地仓库默认 `.venv -> venv` 断链，当前验证依赖 `VK_RUNTIME_VENV=/tmp/codex-py311` 临时解释器。
  - `app/ai/workflow/data_graph.py` 仍是超大文件；这次只把进程级缓存 owner 外移，没有继续切业务切片。
- followup_tasks:
  - 后续可继续把 `data_graph` 的 warmup/intent policy 读取与图构建职责拆出独立模块。
  - 若准备上线，再补一次真实进程启动验证，确认 lifespan 清理顺序在服务退出时符合预期。
- refactor_report_path: `docs/内部参考/迭代需求/refactor_report_lifespan_runtime_consolidation_phase3.md`

### 5) 下一步
1. 进入 `/jjk-review` 做结构复审。
2. 进入 `/jjk-verify` 做最终验收与运行态确认。
