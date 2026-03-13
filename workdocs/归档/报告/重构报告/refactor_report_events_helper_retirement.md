### 1) 重构摘要
- task_id: `none`
- card_id: `none`
- pr_id: `none`
- scope: `app/ai/events.py, tests/unit/test_events_contract.py, docs/开发文档/**`
- execution_mode: `single`
- final_decision: `PASS`
- markers: `TEAM_UNAVAILABLE_FALLBACK`

### 2) 重构切片清单
| slice_id | target | refactor_goal | key_change | status |
|---|---|---|---|---|
| `RF-01` | `app/ai/events.py` | `删除兼容壳` | `删除无调用的 emit_confirmation/emit_stopped/emit_done helper` | `done` |
| `RF-02` | `tests/unit/test_events_contract.py` | `收口活契约` | `测试仅保留 chat_service 仍依赖的 stopped_event 导出` | `done` |
| `RF-03` | `docs/开发文档/**` | `文档收口` | `将 confirmation/done 发送口径改为 AgentEvent/统一 stream contract` | `done` |

### 3) 行为等价证据
| contract | verification | result | evidence |
|---|---|---|---|
| `chat_service stopped 载荷保持不变` | `VK_RUNTIME_VENV=/Users/jijingkun/bojxAI/fastapi/venv bash scripts/pytest_targeted.sh tests/unit/test_events_contract.py` | `PASS` | `stopped_event 契约回归通过` |
| `emit_* helper 已无代码调用` | `rg -n "\\bemit_confirmation\\b|\\bemit_stopped\\b|\\bemit_done\\b" app tests app/tests scripts` | `PASS` | `仅文档/历史报告命中` |

### 4) 风险与遗留
- unresolved_items:
  - `历史 debug/report 文档仍会提到已退役 helper，这是历史证据，保留不改。`
  - `confirmation 事件当前仍采用统一 stream contract 直写；若未来调用点增多，可再评估是否新增 AgentEvent.confirmation()`。
- followup_tasks:
  - `继续清理 test-only/兼容壳残留。`
  - `按需补充 AgentEvent.confirmation()，前提是出现稳定调用面。`
- refactor_report_path: `workdocs/归档/报告/重构报告/refactor_report_events_helper_retirement.md`

### 5) 下一步
1. `进入 /jjk-review`
2. `进入 /jjk-verify`
