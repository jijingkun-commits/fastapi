# 工作包说明

> WS 编号: WS-03  
> 名称: 前端 SSE 与交互收敛  
> 类型: Frontend（可并行，协议 consumer）

---

## 0. 关联文档

1. 主计划：`docs/内部参考/迭代需求/implementation_plan.md`
2. 并行总计划：`docs/内部参考/任务拆解/2026-02-09_待办隐式指代并行拆解/parallel_plan.md`
3. G0 约束：只读消费 `## 0. G0 协议冻结`，不得自行扩展协议语义。

---

## 1. 目标与完成定义

### 1.1 目标

1. 收敛 SSE 消费逻辑与前端消息类型模型。
2. 解决 `todo` 相关类型阻断与交互一致性问题。
3. 保障 `done/result/interrupt` 事件消费稳定。

### 1.2 DoD

1. 前端消息模型与后端冻结契约一一映射。
2. SSE 事件顺序与持久化回填逻辑一致。
3. 类型层不再依赖弱断言兜底。

---

## 2. 文件边界

### 2.1 可修改（白名单）

- `web/src/components/*`
- `web/src/hooks/*`
- `web/src/lib/*`
- `web/src/types/*`
- `web/src/utils/*`
- `web/tests/*`（如存在）

### 2.2 禁止修改（黑名单）

- `app/*`
- `alembic/*`
- 后端测试目录

---

## 3. 状态与契约

- WS-03 可写：
  - 前端消息映射模型
  - SSE 事件消费与 UI 交互逻辑
- WS-03 只读：
  - `done/result/interrupt` 字段定义（WS-02 owner）
  - 工作流状态语义（WS-01 owner）

---

## 4. 实施步骤

1. 对齐 G0 冻结字段，建立前端事件到消息模型映射。
2. 收敛 `useSSEStream`、`backend.ts`、`message types` 的重复分支。
3. 修复 `todo` 交互的类型断言风险点（含确认卡片链路）。
4. 校验 `message_id` 回填后反馈能力可用。

---

## 5. 局部验收与最小验证命令

- `cd web && npx tsc --noEmit`
- `cd web && npm run -s lint`

验收标准：

1. tsc 无阻断错误；
2. 关键 SSE 消费链路可正常渲染；
3. 协议消费符合 G0 冻结定义。

---

## 6. 风险与回滚

- 风险：前端类型收敛时引发历史消息解析兼容问题。
- 回滚：按组件/Hook 粒度回滚，保留协议兼容分支。

---

## 7. 协作者自检卡（提交必填）

- 实际修改文件列表：
  - `web/src/types/message.ts`
  - `web/src/lib/backend.ts`
  - `web/src/hooks/useSSEStream.ts`
  - `web/src/components/todo/ConfirmationCard.tsx`
  - `docs/开发文档/架构设计/前端架构.md`
  - `docs/内部参考/任务拆解/2026-02-09_待办隐式指代并行拆解/workstreams/WS-03_前端SSE与交互收敛.md`
- 是否修改白名单外文件（是/否）：是（仅文档回填）
- 测试命令与结果：
  - `cd web && npx tsc --noEmit` ✅ 通过
  - `cd web && npm run -s lint` ✅ 通过（存在历史 warning，未新增阻断）
- 已知风险点：
  - `useSSEStream.ts` 仍依赖 LangGraph `Message` 的宽类型（`additional_kwargs` 需局部窄化），后续若 SDK 类型变化需复核。
  - `done.final_content` 当前仅在传输层解析保留，UI 仍按 `token/result` 聚合展示。
- 回滚建议：
  - 若出现消息渲染异常，优先回滚 `web/src/hooks/useSSEStream.ts` 与 `web/src/lib/backend.ts` 到上一个稳定版本。
  - 若出现待办确认卡片入参兼容问题，可单独回滚 `web/src/components/todo/ConfirmationCard.tsx`。
