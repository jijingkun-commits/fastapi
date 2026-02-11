# 工作包说明

> WS 编号: WS-G2  
> 名称: 文档终稿门禁  
> 类型: Gate（串行）

---

## 1. 目标与完成定义

### 1.1 目标

1. 在 WS-G1 后完成文档终稿同步与索引闭环。
2. 保证需求、实施方案、模块文档与实现一致。

### 1.2 DoD

1. 文档治理 strict 无 error。
2. 所有关键变更均可追溯到实现或回归证据。

---

## 2. 文件边界

### 2.1 可修改（白名单）

- `docs/内部参考/迭代需求/requirements.md`
- `docs/内部参考/迭代需求/implementation_plan.md`
- `docs/产品文档/*.md`
- `docs/API文档/*.md`
- `docs/开发文档/架构设计/*.md`
- `docs/SUMMARY.md`

### 2.2 禁止修改（黑名单）

- 业务代码文件

---

## 3. 状态与契约

- 可写字段：文档术语、接口描述、测试追溯、索引结构。
- 只读字段：G0 冻结契约定义（仅同步，不重定义）。

---

## 4. 实施步骤

1. 同步需求/实施/模块文档与最终实现差异。
2. 校对 API 与关键链路文档（chat stream/resume、管理接口等）。
3. 修复 `docs/SUMMARY.md` 索引缺失或失效链接。
4. 执行 `venv/bin/python scripts/docs_guard.py --strict` 并记录结果。

---

## 5. 局部验收与最小验证命令

- `venv/bin/python scripts/docs_guard.py --strict`

验收标准：

1. strict 无 error；
2. 文档索引与内容可被实现证据追溯。

---

## 6. 风险与回滚

- 风险：文档术语更新不一致导致认知偏差。
- 回滚：按文档版本回滚，保留门禁记录。

---

## 7. 本次执行记录（2026-02-10）

### 7.1 已执行动作

1. 修复 `docs/SUMMARY.md` 中失效链接：
   - 将 `implementation_plan_多智能体上下文管理重构.md` 失效索引调整为已存在的 `implementation_plan.md`。
2. 执行文档门禁命令：
   - `venv/bin/python scripts/docs_guard.py --strict`
3. 执行 Gate 自动回填：
   - `venv/bin/python scripts/backfill_gate_status.py --plan docs/内部参考/任务拆解/2026-02-09_待办隐式指代并行拆解/parallel_plan.md`

### 7.2 命令结果

- 退出码：`0`
- 结果：`errors: 0 | warnings: 0`
- 说明：本轮 strict 全绿，无阻断项。

### 7.3 结论

- `EX-G1-002`（文档门禁豁免）已关闭。
- 自动回填已同步 `parallel_plan.md` Gate 区块（`pytest 428 passed` / `docs_guard 0 error, 0 warning`）。
- WS-G2 达成 DoD，可作为本轮 Gate 层终点。

### 7.4 TC-TBD 补齐清单（闭环）

> 来源：WS-G1 中 `TC-GATE-DOC-01`（历史临时编号 `TC-TBD-DOC-001`）。

| 临时ID | 补齐后ID | 对应检查项 | 处理动作 | 当前状态 | 证据 |
|------|----------|------------|----------|----------|------|
| TC-TBD-DOC-001 | TC-GATE-DOC-01 | `venv/bin/python scripts/docs_guard.py --strict` | 修复 `docs/SUMMARY.md` 失效索引并复测 | CLOSED | `WS-G2` 第 7.2 节结果（`errors: 0`） |

补齐说明：

1. `TC-GATE-DOC-01` 作为 Gate 文档治理固定用例编号，后续轮次沿用。
2. 若后续新增 Gate 临时编号，必须在 `WS-G2` 落地为正式编号并回填 `WS-G1` 映射表。

---

## 8. 协作者自检卡（提交必填）

- 实际修改文件列表：
  - `docs/SUMMARY.md`
  - `docs/内部参考/任务拆解/2026-02-09_待办隐式指代并行拆解/workstreams/WS-G2_文档终稿门禁.md`
  - `docs/内部参考/任务拆解/2026-02-09_待办隐式指代并行拆解/merge_checklist.md`
  - `docs/内部参考/任务拆解/2026-02-09_待办隐式指代并行拆解/parallel_plan.md`
- 是否修改白名单外文件（是/否）：否
- 测试命令与结果：`venv/bin/python scripts/docs_guard.py --strict` -> 通过（0 error, 0 warning）；`venv/bin/python scripts/backfill_gate_status.py --plan docs/内部参考/任务拆解/2026-02-09_待办隐式指代并行拆解/parallel_plan.md` -> 通过
- 已知风险点：无阻断风险；当前门禁结果见 `parallel_plan.md` 自动回填区块
- 回滚建议：如需回滚仅回滚文档索引改动，保留 Gate 执行记录
