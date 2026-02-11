# 合并冲突检查清单（本轮兜底）

> 说明：本轮按并行判定四问通过执行，当前设计下共享冲突可控。  
> 仍保留此清单作为兜底模板；若出现共享文件或共享字段冲突，必须逐项勾选并记录处置结果。

---

## 1. 边界检查

- [x] 各 WS 仅修改白名单文件（按 WS 文档自检卡核对）
- [x] 无共享文件越权修改（Gate 层仅更新门禁文档）
- [x] 关键状态字段单写入权未被破坏（按 parallel_plan owner 约束）
- [x] 并行层与 Gate 层改动边界清晰

---

## 2. 契约检查

- [ ] API 契约未被破坏（chat/data_admin/llm_admin/dev-tools）
- [ ] SSE 事件契约一致（done/result/interrupt）
- [ ] 前后端字段命名与时序一致
- [x] 双数据库链路未串库（本轮未发现串库证据）

> 注：API/SSE/时序三项需在并行 WS 修复并回归后由下一轮 WS-G1 复核闭环。

---

## 3. 行为检查

- [ ] 无新增重复澄清循环
- [ ] 待办隐式指代可收敛
- [ ] interrupt/resume 链路可闭环
- [ ] 模型路由更新后业务链路可用

> 注：行为项依赖 `pytest` 失败面清零后复验。

---

## 4. 测试检查

- [ ] `venv/bin/python -m pytest -q --maxfail=20`（失败 13）
- [x] `cd web && npx tsc --noEmit`（通过）
- [x] `cd web && npm run -s lint`（通过，38 warning）
- [x] `venv/bin/python scripts/docs_guard.py --strict`（WS-G2 修复后通过）

---

## 5. 文档检查

- [x] 迭代需求与实施方案已同步
- [x] 模块需求文档（5 份）已同步
- [x] API/架构文档已同步（按当前变更范围）
- [x] `docs/SUMMARY.md` 索引完整

---

## 6. 冲突记录（仅冲突时填写）

- 冲突文件：无
- 冲突字段：无
- 处理策略：沿用 owner 单写入权 + Gate 串行收口
- 验证结果：通过
- 责任人：WS 负责人集合

---

## 7. 本轮门禁执行摘要（2026-02-10）

1. `pytest -q --maxfail=20`：失败 13（已归类为 WS-01/WS-02 回流项）
2. `tsc --noEmit`：通过
3. `npm run -s lint`：通过（38 warning）
4. `docs_guard --strict`：G1 时失败（2 error），WS-G2 修复后通过（0 error）

