# WS-C04 P0 退役验收矩阵

- 对应 card_id: `C04`
- 对应 feature_id: `P0-04`
- 目标: 建立可重复执行的治理验收矩阵。

## card_export

```yaml
card_export:
  id: WS-C04
  feature_id: P0-04
  card_key: PP-20260306-ENGINEERING-LEAN-GOV::WS-C04
  title: 退役验收矩阵
  type: parallel
  task_mode: implementation-card
  merge_required: true
  execution_mode: serial
  hard_depends_on: [C03]
  depends_on: [C03]
  mechanism_summary:
    - 统一验收命令与通过标准
  code_anchor_refs:
    - docs/内部参考/工程减法体检报告_2026-03-06_v3.md::8. 验收矩阵
  acceptance_checks:
    - rg -n "验收矩阵" docs/内部参考/工程减法体检报告_2026-03-06_v3.md
  rollback_anchors:
    - git checkout -- docs/内部参考/工程减法体检报告_2026-03-06_v3.md
  evidence_entry: docs/内部参考/工程减法体检报告_2026-03-06_v3.md#8-验收矩阵执行完成前必跑
```
