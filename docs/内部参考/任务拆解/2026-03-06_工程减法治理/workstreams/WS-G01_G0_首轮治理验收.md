# WS-G01 G0 首轮治理验收

- 对应 card_id: `G01`
- 对应 feature_id: `G0-01`
- 目标: 验证治理卡片包可被 create-only 消费。

## card_export

```yaml
card_export:
  id: WS-G01
  feature_id: G0-01
  card_key: PP-20260306-ENGINEERING-LEAN-GOV::WS-G01
  title: 首轮治理验收
  type: gate
  task_mode: inspection/question-card
  merge_required: false
  execution_mode: serial
  hard_depends_on: [C04]
  depends_on: [C04]
  mechanism_summary:
    - 校验建卡契约完整性
  code_anchor_refs:
    - scripts/coder4/coder4_vk_sync.py::sync_all_cards
  acceptance_checks:
    - python3 scripts/coder4/coder4_vk_sync.py --active-task docs/内部参考/任务拆解/2026-03-06_工程减法治理/_active_task.json --sync-all --dry-run
  rollback_anchors:
    - 仅保留本地契约，不写远端看板
  evidence_entry: docs/内部参考/任务拆解/2026-03-06_工程减法治理/.state/PP-20260306-ENGINEERING-LEAN-GOV/vktodo_dryrun_result.json
```
