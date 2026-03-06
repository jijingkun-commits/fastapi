# WS-C01 P0 治理基线快照

- 对应 card_id: `C01`
- 对应 feature_id: `P0-01`
- 目标: 固化工程减法治理基线。

## card_export

```yaml
card_export:
  id: WS-C01
  feature_id: P0-01
  card_key: PP-20260306-ENGINEERING-LEAN-GOV::WS-C01
  title: 治理基线快照
  type: parallel
  task_mode: implementation-card
  merge_required: true
  execution_mode: serial
  hard_depends_on: []
  depends_on: []
  mechanism_summary:
    - 统计并固定当前文件与依赖基线
  code_anchor_refs:
    - docs/内部参考/工程减法体检报告_2026-03-06_v3.md::核验基线
  acceptance_checks:
    - rg -n "核验基线" docs/内部参考/工程减法体检报告_2026-03-06_v3.md
  rollback_anchors:
    - git checkout -- docs/内部参考/工程减法体检报告_2026-03-06_v3.md
  evidence_entry: docs/内部参考/工程减法体检报告_2026-03-06_v3.md#2-核验基线2026-03-06-实测
```
