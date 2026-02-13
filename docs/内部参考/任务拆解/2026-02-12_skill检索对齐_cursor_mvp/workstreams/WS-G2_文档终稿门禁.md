# 工作包说明

> WS 编号: WS-G2  
> 名称: 文档终稿门禁  
> 类型: Gate（串行）

---

## 1. 目标与完成定义

### 1.1 目标

1. 对代码改动执行文档映射闭环。
2. 更新文档索引并通过 docs_guard。
3. 关闭 Gate 文档类遗留项。

### 1.2 DoD

1. 文档映射规则覆盖完整。
2. `docs_guard --strict` 通过。
3. 总结报告可追溯到实现与测试证据。

---

## 2. 文件边界

### 2.1 可修改（白名单）

- `docs/开发文档/架构设计/AI模块设计.md`
- `docs/开发文档/架构设计/数据库设计.md`
- `docs/开发文档/快速入门/配置说明.md`
- `.env.example`
- `docs/SUMMARY.md`
- `docs/内部参考/任务拆解/2026-02-12_skill检索对齐_cursor_mvp/workstreams/WS-G2_文档终稿门禁.md`

### 2.2 禁止修改（黑名单）

- 业务代码文件

---

## 3. 实施步骤

1. 按 doc_sync 规则补齐文档更新。
2. 执行 docs_guard 并记录结果。
3. 形成终稿收口说明。

---

## 4. 最小验证命令

- `venv/bin/python scripts/docs_guard.py --strict`

---

## 5. 浏览器测试触发评估

- 是否触发浏览器测试：否
- 原因：文档 Gate，无前端交互改动。

---

## 6. 协作者自检卡（提交必填）

- 实际修改文件列表：
  - `docs/SUMMARY.md`
  - `docs/内部参考/任务拆解/2026-02-12_skill检索对齐_cursor_mvp/workstreams/WS-G2_文档终稿门禁.md`
- 是否修改白名单外文件（是/否）：否
- 测试命令与结果：
  - `python3 scripts/docs_guard.py --strict` -> 通过（`errors: 0 | warnings: 0`）
- 已知风险点：
  - 当前工作树 `venv` 为 Windows 目录结构（`venv/Scripts`），`venv/bin/python` 不存在；如在类 Unix 环境复跑，需确认虚拟环境路径一致。
- 回滚建议：
  - 如需回滚，仅回滚 `docs/SUMMARY.md` 的索引修正；保留本文件的门禁执行记录。

---

## 7. 本次执行记录（2026-02-13）

### 7.1 动作

1. 修复 `docs/SUMMARY.md` 中“内部参考/迭代需求”下的断链：
   - 移除不存在的 `内部参考/迭代需求/requirements.md`
   - 移除不存在的 `内部参考/迭代需求/implementation_plan.md`
   - 将入口收敛到已存在文档：`skill_admin_frontend_requirements.md`、`skill_admin_frontend_plan.md`、`evaluation_report.md`
2. 执行 strict 门禁检查：
   - `python3 scripts/docs_guard.py --strict`

### 7.2 结果

- `broken_links: 0`
- `summary_broken_targets: 0`
- `summary_coverage: 83/83 (100.00%)`
- `errors: 0 | warnings: 0`

### 7.3 Gate 结论

- `WS-G2` 文档终稿门禁通过。
- `TC-GATE-DOC-01`（文档治理 strict）阻塞项已关闭。

---

## card_export

```yaml
card_export:
  id: WS-G2
  card_key: PP-20260213-SKILL-RETRIEVAL-MVP::WS-G2
  title: 文档终稿门禁
  type: gate
  lane: lane-gate
  hard_depends_on:
    - WS-G1
  soft_depends_on: []
  depends_on:
    - WS-G1
  file_whitelist:
    - docs/
    - .env.example
  readonly_scope:
    - app/
    - web/
  owner_fields:
    - gate.g2.status
    - docs.summary
  check_cmd:
    - venv/bin/python scripts/docs_guard.py --strict
  handoff_artifacts:
    - docs/SUMMARY.md
  dod:
    - 文档同步与索引门禁通过
```
