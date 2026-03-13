### 1) 重构摘要
- task_id: `none`
- card_id: `none`
- pr_id: `none`
- scope: `app/services/response_policy_service.py, tests/unit/test_response_policy_service.py`
- execution_mode: `single`
- final_decision: `PASS`
- markers: `TEAM_UNAVAILABLE_FALLBACK`

### 2) 重构切片清单
| slice_id | target | refactor_goal | key_change | status |
|---|---|---|---|---|
| `RF-01` | `app/services/response_policy_service.py#build_router_blocked_system_context` | `删除 test-only helper` | `删除仅包装 build_multi_intent_recovery_system_context 的无调用函数` | `done` |
| `RF-02` | `tests/unit/test_response_policy_service.py` | `删除对应测试孤岛` | `删除只覆盖已退役 helper 的测试` | `done` |

### 3) 行为等价证据
| contract | verification | result | evidence |
|---|---|---|---|
| `router blocked helper 无生产调用` | `rg -n "build_router_blocked_system_context" app tests app/tests scripts` | `PASS` | `仅旧测试与已删除函数自身命中` |
| `response policy 现行行为保持不变` | `VK_RUNTIME_VENV=/Users/jijingkun/bojxAI/fastapi/venv bash scripts/pytest_targeted.sh tests/unit/test_response_policy_service.py` | `PASS` | `定向回归通过` |

### 4) 风险与遗留
- unresolved_items:
  - `workdocs/归档/正文/设计/2026-03-09-memory-intent-lean-cleanup-design.md` 等历史设计文档仍会提到该 helper，作为历史证据保留。
- followup_tasks:
  - `继续清理其他 test-only/helper-only 残留。`
- refactor_report_path: `workdocs/归档/报告/重构报告/refactor_report_response_policy_test_only_cleanup.md`

### 5) 下一步
1. `进入 /jjk-review`
2. `进入 /jjk-verify`
