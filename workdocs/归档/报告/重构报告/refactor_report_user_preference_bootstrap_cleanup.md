### 1) 重构摘要
- task_id: `none`
- card_id: `none`
- pr_id: `none`
- scope: `app/services/user_preference_memory_service.py, tests/unit/test_user_preference_memory_service.py`
- execution_mode: `single`
- final_decision: `PASS`
- markers: `TEAM_UNAVAILABLE_FALLBACK`

### 2) 重构切片清单
| slice_id | target | refactor_goal | key_change | status |
|---|---|---|---|---|
| `RF-01` | `app/services/user_preference_memory_service.py#bootstrap_user_preferences` | `删除旧入口` | `删除仅在测试中存活的 KV bootstrap 入口` | `done` |
| `RF-02` | `tests/unit/test_user_preference_memory_service.py` | `删除对应测试孤岛` | `删除只覆盖已退役 bootstrap helper 的测试` | `done` |

### 3) 行为等价证据
| contract | verification | result | evidence |
|---|---|---|---|
| `新用户偏好初始化 owner 已迁移到文档记忆链路` | `rg -n "bootstrap_preference_documents|bootstrap_user_preferences" app tests app/tests scripts docs` | `PASS` | `user_service 走 document_memory_service.bootstrap_preference_documents` |
| `user_preference_memory_service 现行行为保持不变` | `VK_RUNTIME_VENV=/Users/jijingkun/bojxAI/fastapi/venv bash scripts/pytest_targeted.sh tests/unit/test_user_preference_memory_service.py tests/unit/test_user_service_memory_bootstrap.py` | `PASS` | `定向回归通过` |

### 4) 风险与遗留
- unresolved_items:
  - `历史 requirements/implementation_plan 文档仍会提到 user_preference_memory_service 作为迁移参与模块，这是历史语境，当前不做清理。`
- followup_tasks:
  - `继续清理剩余 test-only/helper-only 残留。`
- refactor_report_path: `workdocs/归档/报告/重构报告/refactor_report_user_preference_bootstrap_cleanup.md`

### 5) 下一步
1. `进入 /jjk-review`
2. `进入 /jjk-verify`
