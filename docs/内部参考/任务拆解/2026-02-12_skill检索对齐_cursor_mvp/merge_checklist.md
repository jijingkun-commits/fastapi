# 合并检查清单

## 1. 边界检查

- [ ] 各 WS 仅修改白名单文件
- [ ] 无共享文件越权修改
- [ ] 关键字段单写入权未被破坏

## 2. 契约检查

- [ ] `skill_candidates`/`selected_skill_ids`/`skill_context` 契约一致
- [ ] G0 冻结字段 required/optional 未被破坏
- [ ] 混合检索分数字段可解释

## 3. 行为检查

- [ ] 自动触发开关 `auto_enabled` 生效
- [ ] 冲突技能裁决与优先级策略生效
- [ ] 注入内容遵守 token budget

## 4. 测试检查

- [ ] `app/tests/test_skill_retrieval_smoke.py` 通过
- [ ] `tests -k "skill"` 通过
- [ ] `docs_guard --strict` 通过

## 5. 文档检查

- [ ] `docs/开发文档/架构设计/数据库设计.md` 已同步
- [ ] `docs/开发文档/架构设计/AI模块设计.md` 已同步
- [ ] `docs/开发文档/快速入门/配置说明.md` 与 `.env.example` 已同步（如涉及新变量）
- [ ] `docs/SUMMARY.md` 收录新文档

