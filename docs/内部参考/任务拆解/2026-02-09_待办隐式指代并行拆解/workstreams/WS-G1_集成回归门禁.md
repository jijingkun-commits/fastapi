# 工作包说明

> WS 编号: WS-G1  
> 名称: 集成回归门禁  
> 类型: Gate（串行）

---

## 1. 目标与完成定义

### 1.1 目标

1. 汇总并验证 WS-01/WS-02/WS-03 合并后的跨模块行为。
2. 输出可追溯的门禁结果与豁免清单。

### 1.2 DoD

1. 门禁命令全部通过，或存在批准豁免且记录完备。
2. 回归报告可直接供 WS-G2 与发布阶段使用。

---

## 2. 文件边界

### 2.1 可修改（白名单）

- `docs/内部参考/任务拆解/2026-02-09_待办隐式指代并行拆解/merge_checklist.md`
- `docs/内部参考/任务拆解/2026-02-09_待办隐式指代并行拆解/parallel_plan.md`（仅门禁结果区）

### 2.2 禁止修改（黑名单）

- 业务代码文件（除非阻断并经回流到对应 WS）。

---

## 3. 状态与契约

- 可写字段：门禁结果、豁免项、回归记录。
- 只读字段：G0 冻结契约与各 WS 业务语义定义。

---

## 4. 实施步骤

1. 运行统一门禁命令：
   - `venv/bin/python -m pytest -q --maxfail=20`
   - `cd web && npx tsc --noEmit`
   - `cd web && npm run -s lint`
   - `venv/bin/python scripts/docs_guard.py --strict`
2. 归类失败项并映射到对应 WS。
3. 对暂不修复项产出豁免清单（风险、期限、回归条件）。

---

## 5. 局部验收与最小验证命令

- 同第 4 节门禁命令。

验收标准：

1. 门禁结果清晰、可追溯；
2. 豁免项具备责任人与截止条件。

---

## 6. 风险与回滚

- 风险：跨 WS 交互缺陷在局部验证阶段未暴露。
- 回滚：回退到具体 WS 处理，不在 Gate 层直接修业务。

---

## 7. 本次执行记录（2026-02-10）

### 7.1 门禁命令结果

1. `venv/bin/python -m pytest -q --maxfail=20`
   - 退出码：`1`
   - 摘要：`13 failed`
   - 主要失败归类：
     - 数据访问白名单/SQL 校验：`app/tests/test_data_agent.py`、`tests/api/test_data_chat.py`
     - 模型初始化密钥依赖：`app/tests/test_model_switch.py`
     - 待办集成与多轮异步：`app/tests/test_todo_graph_integration.py`、`app/tests/test_todo_multiround.py`

2. `cd web && npx tsc --noEmit`
   - 退出码：`0`
   - 摘要：类型检查通过

3. `cd web && npm run -s lint`
   - 退出码：`0`
   - 摘要：`38` 条 warning（无 error）

4. `venv/bin/python scripts/docs_guard.py --strict`
   - 退出码：`1`
   - 摘要：`2 error / 4 warning`
   - 根因：`docs/SUMMARY.md` 中 `implementation_plan_多智能体上下文管理重构.md` 目标缺失

### 7.2 失败项映射

- WS-01：待办意图与多轮链路收敛相关失败（integration/multiround）
- WS-02：数据访问策略、模型配置与契约相关失败（data_access/model_switch）
- WS-G2：文档索引失效链接修复（docs_guard strict error）

### 7.3 TC-ID 映射表（Gate 追溯）

| TC-ID | 门禁命令/检查项 | 自动化脚本或 pytest nodeid | 本次结果 | 责任 WS | 豁免/缺陷单 |
|------|------------------|----------------------------|----------|---------|-------------|
| TC-MULTI-01~05 | `venv/bin/python -m pytest -q --maxfail=20` | `app/tests/test_todo_graph_integration.py`, `app/tests/test_todo_multiround.py` | FAIL | WS-01 | EX-G1-001 |
| TC-AD-02, TC-AD-ERR-03 | `venv/bin/python -m pytest -q --maxfail=20` | `app/tests/test_data_agent.py`, `tests/api/test_data_chat.py` | FAIL | WS-02 | EX-G1-001 |
| TC-CHAT-BIZ-02 | `venv/bin/python -m pytest -q --maxfail=20` | `app/tests/test_model_switch.py` | FAIL | WS-02 | EX-G1-001 |
| TC-CHAT-01~04, TC-SYNC-01~05 | `cd web && npx tsc --noEmit` | 前端类型检查（`web/src/**`） | PASS | WS-03 | - |
| TC-ADMIN-01~04 | `cd web && npm run -s lint` | 前端管理后台静态检查（`web/src/components/admin/**`） | PASS（warning 不阻断） | WS-03 | - |
| TC-GATE-DOC-01（原 `TC-TBD-DOC-001`） | `venv/bin/python scripts/docs_guard.py --strict` | `docs/SUMMARY.md` 索引校验 | FAIL | WS-G2 | EX-G1-002 |

### 7.4 浏览器测试触发评估

- 是否触发浏览器测试：否（Gate 本轮未触发）
- 评估结论：本轮 WS-G1 聚焦统一门禁与失败归因，未新增前端交互实现改动；浏览器行为验证由相关 owner WS 在局部验收或后续专项回归中执行。
- 备注：若下一轮 WS-03 或 WS-02 涉及跨端交互变化，按 `imp-ws` 触发规则补充 Playwright 证据。

---

## 8. 豁免清单（进入 WS-G2 前）

1. `EX-G1-001`（临时豁免）
   - 项目：`pytest` 13 个失败
   - 风险：中高（核心链路仍有回归风险）
   - 责任：WS-01 / WS-02
   - 处理：回流并行 WS 修复后，下一轮 `WS-G1` 复测清零

2. `EX-G1-002`（本轮内闭环）
   - 项目：`docs_guard --strict` 2 个 error
   - 风险：中（文档索引可追溯性受损）
   - 责任：WS-G2
   - 处理：在 `WS-G2` 修复 `docs/SUMMARY.md` 并复测 strict

---

## 9. 协作者自检卡（提交必填）

- 实际修改文件列表：
  - `docs/内部参考/任务拆解/2026-02-09_待办隐式指代并行拆解/workstreams/WS-G1_集成回归门禁.md`
  - `docs/内部参考/任务拆解/2026-02-09_待办隐式指代并行拆解/merge_checklist.md`
  - `docs/内部参考/任务拆解/2026-02-09_待办隐式指代并行拆解/parallel_plan.md`
- 是否修改白名单外文件（是/否）：是（`docs/SUMMARY.md` 由 WS-G2 修复）
- 测试命令与结果：见第 7 节
- 已知风险点：`pytest` 仍有 13 个失败待并行 WS 回流修复
- 回滚建议：仅回滚 Gate 文档变更，不触碰业务代码
