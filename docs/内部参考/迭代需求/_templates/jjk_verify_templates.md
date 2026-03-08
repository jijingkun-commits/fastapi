# `/jjk-verify` 项目覆盖模板（轻量）

> 仅用于覆盖全局模板差异：
> `/Users/jijingkun/.codex/engineering/templates/jjk_verify_templates.md`

## 项目覆盖段（按需填写）

```markdown
### 覆盖: test-quality-acceptance
- 覆盖原因: 本项目验收阶段不能只看命令通过，还要确认测试质量达标。
- 极简报告差异:
  - 增加 `测试质量结论` 一节，至少回填：风险模型、失败模式覆盖、评分卡结论。
- 标准报告差异:
  - 若 review 未显式给出评分卡或失败模式覆盖结论，验收默认 `FAIL(VERIFY_TEST_QUALITY_UNPROVEN)`。
```
