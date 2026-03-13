### 1) 重构摘要
- task_id: `none`
- card_id: `none`
- pr_id: `none`
- scope: `app/services/document_memory_service.py, tests/unit/test_document_memory_service.py, tests/unit/test_document_memory_service_hybrid.py`
- execution_mode: `single`
- final_decision: `PASS`
- markers: `TEAM_UNAVAILABLE_FALLBACK`

### 2) 重构切片清单
| slice_id | target | refactor_goal | key_change | status |
|---|---|---|---|---|
| `RF-01` | `app/services/document_memory_service.py#memory_get` | `删除旧 seam` | `删除 recall 已不再使用的局部全文读取函数` | `done` |
| `RF-02` | `tests/unit/test_document_memory_service.py` | `删除重复旧测试` | `删除依赖 memory_get 旧 seam 的重复测试` | `done` |
| `RF-03` | `tests/unit/test_document_memory_service_hybrid.py` | `保留行为护栏` | `将“不回源”断言上提到 repo.get_document_excerpt` | `done` |

### 3) 行为等价证据
| contract | verification | result | evidence |
|---|---|---|---|
| `memory_get 仅为遗留接缝，无生产调用` | `rg -n "\\bmemory_get\\b" app tests app/tests scripts` | `PASS` | `代码与测试路径已无命中` |
| `recall 继续基于 chunk_text + citation 组装上下文` | `VK_RUNTIME_VENV=/Users/jijingkun/bojxAI/fastapi/venv bash scripts/pytest_targeted.sh tests/unit/test_document_memory_service.py tests/unit/test_document_memory_service_hybrid.py` | `PASS` | `定向回归通过` |

### 4) 风险与遗留
- unresolved_items:
  - `events` 兼容导出仍由专门测试锁定，后续需要拆分为保留 `stopped_event` / 清理 `emit_*` 两部分。
  - `check_workflow_contract` 相关脚本测试仍有仓内旧基线问题，和本次 refactor 无关，后续单独治理。
- followup_tasks:
  - `拆分 test_events_contract，仅保留仍有效导出契约。`
  - `继续清理 test-only/兼容壳残留。`
- refactor_report_path: `workdocs/归档/报告/重构报告/refactor_report_memory_get_retirement.md`

### 5) 下一步
1. `进入 /jjk-review`
2. `进入 /jjk-verify`
