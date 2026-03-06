# WS-C02 P0 脚本依赖台账

- 对应 card_id: `C02`
- 对应 feature_id: `P0-02`
- 目标: 形成脚本 owner/trigger/replacement 台账。

## card_export

```yaml
card_export:
  id: WS-C02
  feature_id: P0-02
  card_key: PP-20260306-ENGINEERING-LEAN-GOV::WS-C02
  title: 脚本依赖台账
  type: parallel
  task_mode: implementation-card
  merge_required: true
  execution_mode: serial
  hard_depends_on: [C01]
  depends_on: [C01]
  mechanism_summary:
    - 补齐 owner/trigger/replacement 字段
  code_anchor_refs:
    - docs/内部参考/工程减法治理看板模板_2026-03-06.md::卡片模板
  acceptance_checks:
    - rg -n "owner / trigger / replacement" docs/内部参考/工程减法治理看板模板_2026-03-06.md
  rollback_anchors:
    - git checkout -- docs/内部参考/工程减法治理看板模板_2026-03-06.md
  evidence_entry: docs/内部参考/工程减法治理看板模板_2026-03-06.md#2-卡片模板复制即用
```
