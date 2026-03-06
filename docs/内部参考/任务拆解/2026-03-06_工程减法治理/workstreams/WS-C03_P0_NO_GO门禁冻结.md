# WS-C03 P0 NO-GO 门禁冻结

- 对应 card_id: `C03`
- 对应 feature_id: `P0-03`
- 目标: 冻结高风险直删命令，建立阻断机制。

## card_export

```yaml
card_export:
  id: WS-C03
  feature_id: P0-03
  card_key: PP-20260306-ENGINEERING-LEAN-GOV::WS-C03
  title: NO-GO 门禁冻结
  type: parallel
  task_mode: implementation-card
  merge_required: true
  execution_mode: serial
  hard_depends_on: [C02]
  depends_on: [C02]
  mechanism_summary:
    - 明确 NO-GO 阻断条件与替代路径
  code_anchor_refs:
    - docs/内部参考/工程减法体检报告_2026-03-06.md::3.1
  acceptance_checks:
    - rg -n "NO-GO|冻结执行" docs/内部参考/工程减法体检报告_2026-03-06.md
  rollback_anchors:
    - git checkout -- docs/内部参考/工程减法体检报告_2026-03-06.md
  evidence_entry: docs/内部参考/工程减法体检报告_2026-03-06.md#31-冻结执行no-go
```
