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
| `RF-01` | `app/services/user_preference_memory_service.py#recall` | `删除旧 KV 召回链` | `删除已被 document_memory_service 替代的偏好上下文/召回入口与内部 helper` | `done` |
| `RF-02` | `tests/unit/test_user_preference_memory_service.py` | `删除对应测试孤岛` | `删除只覆盖旧 KV 召回链的测试` | `done` |

### 3) 行为等价证据
| contract | verification | result | evidence |
|---|---|---|---|
| `KV 偏好上下文旧入口已无生产调用` | `rg -n "build_user_preference_context|user_preference_memory_service\\.recall" app tests app/tests scripts` | `PASS` | `代码路径现已无命中` |
| `偏好写入与新用户初始化主链保持正常` | `VK_RUNTIME_VENV=/Users/jijingkun/bojxAI/fastapi/venv bash scripts/pytest_targeted.sh tests/unit/test_user_preference_memory_service.py tests/unit/test_user_service_memory_bootstrap.py tests/unit/test_document_memory_service.py` | `PASS` | `定向回归通过` |

### 4) 风险与遗留
- unresolved_items:
  - `历史设计/迁移文档仍会把 user_preference_memory_service 描述为迁移参与模块，这是历史语境，当前不做清理。`
- followup_tasks:
  - `继续清理剩余 test-only/helper-only 残留。`
- refactor_report_path: `workdocs/归档/报告/重构报告/refactor_report_user_preference_context_cleanup.md`

### 5) 下一步
1. `进入 /jjk-review`
2. `进入 /jjk-verify`
