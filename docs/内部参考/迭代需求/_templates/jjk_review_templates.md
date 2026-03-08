# `/jjk-review` 项目覆盖模板（轻量）

> 仅用于覆盖全局模板差异：
> `/Users/jijingkun/.codex/engineering/templates/jjk_review_templates.md`

## 项目覆盖段（按需填写）

```markdown
### 覆盖: test-quality-scorecard
- 覆盖原因: 本项目需要把“有测试”与“测试质量达标”显式区分。
- 输出模板差异:
  - 审查报告必须新增 `测试质量评分卡`。
  - 评分维度固定为：风险覆盖、失败模式覆盖、断言质量、脆弱性、可维护性。
  - 任一维度 `0` 分时，不得给 `PASS`。
```
