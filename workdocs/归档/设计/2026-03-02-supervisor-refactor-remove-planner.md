# Supervisor 架构重构实施方案（方案A：移除 Planner）

> **文档类型**: 长期架构重构实施方案  
> **创建日期**: 2026-03-02  
> **最后更新**: 2026-03-02  
> **版本**: v1.1（按方案A落地版）  
> **实施优先级**: P1（架构清晰 + 延迟优化）

---

## 0. 决策锁定

本次重构已明确采用 **方案A（一步到位）**：
- 移除图中的 `planner` 节点；
- 将目标拆解能力并入 `supervisor`；
- 取消 `intent_plan` 作为状态字段，改为 `decomposed_goals`；
- 最终移除 `plan_ready` 事件（保留短期兼容开关用于灰度）。

### 0.1 方案确认

| 方案 | 优点 | 缺点 | 成本 | 推荐度 |
|------|------|------|------|--------|
| 方案A（本次采用） | 彻底消除职责重叠，调用链最短，长期维护成本最低 | 改动面大，迁移风险高 | 高 | 高 |

### 0.2 不在本次范围

- 不改 `todo_expert` / `data_expert` 子图内部业务策略；
- 不改前端交互样式与页面结构；
- 不改数据库表结构。

---

## 1. 当前问题与根因

## 1.1 当前链路

```text
用户输入
  -> preprocess(注入 system_context)
  -> planner(生成 intent_plan)
  -> supervisor(再次决策 + 工具调用/委派)
  -> expert/evaluate/coverage/final
```

## 1.2 根因（按代码链路归因）

1. **串行模型调用冗余**  
   `planner` 与 `supervisor` 都在做意图判定，简单请求也固定多一次模型调用。

2. **上下文感知分裂**  
   `planner` 规划提示词仅消费 `user_text`，对 `system_context`（如 `current_todo_id`）天然不敏感，导致“选中待办 + 模糊更新表达”场景误判。

3. **合同语义分散**  
   路由门禁、多目标模式、覆盖率检查均耦合 `intent_plan`，修改一处容易引发连锁回归。

---

## 2. 目标架构（方案A）

## 2.1 新流程

```text
用户输入
  -> preprocess(注入 system_context)
  -> supervisor(统一决策)
      -> 简单请求: 直接回复或直连工具
      -> 复合请求: 调用 decompose_goals 生成 decomposed_goals
      -> 专家请求: assign_to_* 委派
  -> expert/evaluate/coverage/final
```

## 2.2 设计原则

- **单一决策层**：只有 `supervisor` 负责“识别 + 拆解 + 路由”；
- **按需拆解**：仅复合请求调用 `decompose_goals`，简单请求不额外走拆解模型；
- **上下文优先**：`current_todo_id` 对待办更新路由有最高优先级；
- **单一状态源**：状态层仅保留 `decomposed_goals`，避免 `intent_plan` / `decomposed_goals` 双写。

---

## 3. 详细技术方案

## 3.1 图结构调整

### 当前

```python
workflow.add_edge(START, "preprocess")
workflow.add_edge("preprocess", "planner")
workflow.add_edge("planner", "supervisor")
```

### 目标

```python
workflow.add_edge(START, "preprocess")
workflow.add_edge("preprocess", "supervisor")
```

### 处理动作

- 删除 `_planner_node` 与相关注册；
- 删除 `planner_llm` 初始化与引用；
- 删除 `planner -> supervisor` 相关状态透传逻辑。

---

## 3.2 State 合同调整

### 变更

- 删除：`intent_plan: Dict[str, Any]`
- 新增：`decomposed_goals: List[Dict[str, Any]]`
- 保留：`deliverables`、`coverage_report`、`route_decisions` 等交付编排字段。

### 约束

`decomposed_goals` 每个 goal 至少包含：
- `goal_id`
- `order`
- `kind`
- `title`
- `must_answer`
- `allowed_agents`

---

## 3.3 Supervisor 能力重构

### 3.3.1 新增工具 `decompose_goals`

用于将复合请求拆解为结构化 goals，仅在检测到复合意图时调用。

示例输出：

```json
{
  "goals": [
    {
      "goal_id": "GOAL-01",
      "order": 1,
      "kind": "todo.query",
      "title": "查询待办",
      "must_answer": true,
      "allowed_agents": ["todo_expert"]
    },
    {
      "goal_id": "GOAL-02",
      "order": 2,
      "kind": "external.lookup",
      "title": "查询天气",
      "must_answer": true,
      "allowed_agents": []
    }
  ]
}
```

说明：`external.lookup` 默认由 Supervisor 直连工具处理，不进入 expert 委派队列，因此 `allowed_agents=[]`。

### 3.3.2 Prompt 决策树增强（前置高优先规则）

在 `SUPERVISOR_PROMPT` 顶部加入：
1. 若 `system_context` 包含“当前选中待办ID”，且用户输入为模糊更新表达，则优先委派 `todo_expert`，并注入：
   - `todo_action="update"`
   - `todo_fields.todo_id=<current_todo_id>`
2. 若请求包含多个独立目标，先调用 `decompose_goals`。

---

## 3.4 Router 与 Coverage 改造

## 3.4.1 Router 输入源替换

- `_build_router_dispatch_goal_queue` 从 `state.decomposed_goals` 构建队列；
- 不再读取 `state.intent_plan`；
- 保持 `allowed_agents` 门禁语义不变。

## 3.4.2 Coverage 与 Final 统一入口

新增统一函数（命名可调整）：
- `_resolve_active_goals(state)`：
  - 优先取 `decomposed_goals`；
  - 空值时生成单目标 `general.reply`；
  - 负责 order 排序与默认字段补齐。

所有覆盖率相关函数改为消费 `_resolve_active_goals(state)` 返回值，而非 `intent_plan`。

---

## 3.5 SSE 事件策略（方案A最终态）

### 最终态

- 移除事件：`plan_ready`
- 保留事件：`status`、`tool_start`、`tool_end`、`result`、`coverage_check`、`final_answer`、`done` 等

### 灰度兼容（强制）

为降低前后端切换风险，提供短期兼容开关：

- `ENABLE_PLAN_READY_COMPAT=true`：继续发 `plan_ready`（由 `decomposed_goals` 映射构造）
- `ENABLE_PLAN_READY_COMPAT=false`：完全停止发 `plan_ready`

灰度结束后默认关闭并删除兼容代码。

---

## 4. 受影响文件（扩展版）

## 4.1 核心改造

| 文件 | 修改类型 | 说明 |
|------|----------|------|
| `app/ai/workflow/multi_agent_graph.py` | 重构 | 移除 planner 节点、引入 decompose_goals、路由与覆盖率改造 |
| `app/ai/state.py` | 合同调整 | 删除 intent_plan，新增 decomposed_goals |
| `app/ai/prompts/agent_prompts.py` | Prompt 增强 | 增加“选中待办优先 + 复合请求先拆解”决策规则 |

## 4.2 合同与事件层

| 文件 | 修改类型 | 说明 |
|------|----------|------|
| `app/ai/contracts/delivery_contract_validators.py` | 调整 | 意图合同校验入口改为消费 decomposed_goals |
| `app/ai/contracts/delivery_contracts.py` | 调整 | 目标合同字段命名与注释同步（不保留 planner 语义） |
| `app/ai/events.py` | 调整 | `plan_ready` 进入兼容开关控制，最终移除 |
| `app/services/chat_service.py` | 调整 | `plan_ready` payload 归一化逻辑改为兼容分支 |

## 4.3 前端与测试

| 文件/目录 | 修改类型 | 说明 |
|-----------|----------|------|
| `web/src/types/message.ts` | 调整 | 流事件类型中 `plan_ready` 迁移为兼容可选 |
| `tests/unit/**` | 更新 | planner/intent_plan 相关单测迁移到 supervisor/decomposed_goals |
| `tests/api/**` | 更新 | SSE 事件断言切换到兼容模式 + 最终态模式 |
| `tests/integration/**` | 更新 | 端到端链路改为 preprocess -> supervisor |

---

## 5. 实施计划（按方案A执行）

## 阶段0：基线与防回归准备（0.5 天）

1. 采集基线：
   - 首字延迟 P50/P95
   - 路由准确率
   - 复合请求成功率
2. 冻结回归样例：
   - “你好”
   - “查询待办”
   - “查待办，再看天气”
   - “当前选中待办ID=xxx + 现在需要两页了”

## 阶段1：图与状态改造（1-2 天）

1. 删除 `planner` 节点与边；
2. 删除 `intent_plan` 状态字段，新增 `decomposed_goals`；
3. 跑最小单测确保图可编译、可启动。

## 阶段2：Supervisor 重构（2-3 天）

1. 落地 `decompose_goals`；
2. 更新 `SUPERVISOR_PROMPT` 决策树；
3. 增强选中待办场景 frame 注入。

## 阶段3：Router/Coverage 重构（2-3 天）

1. Router 全部切换到 `decomposed_goals`；
2. Coverage/Final 统一改为 `_resolve_active_goals(state)`；
3. 删除所有 `intent_plan` 读写残留。

## 阶段4：SSE 与兼容迁移（1-2 天）

1. 加 `ENABLE_PLAN_READY_COMPAT` 开关；
2. 默认灰度阶段开启兼容；
3. 前端和测试双模式通过后关闭兼容。

## 阶段5：全量验证与灰度（1-2 周）

1. 10% -> 50% -> 100% 分阶段灰度；
2. 监控核心指标，异常即回滚；
3. 灰度稳定后清理兼容代码。

---

## 6. 测试与验收标准

## 6.1 功能验收

| 用例 | 期望 |
|------|------|
| 简单问候 | 不拆解、不委派、直接回复 |
| 单目标待办 | 直接委派 todo_expert |
| 复合请求（待办+天气） | 先 decompose_goals，再按顺序执行并统一收口 |
| 选中待办+模糊更新 | 直接按 update 走 todo_expert，命中 todo_id |

## 6.2 性能验收

| 指标 | 基线 | 目标 |
|------|------|------|
| 首字延迟 P50 | 现网基线 | 下降 >= 25% |
| 首字延迟 P95 | 现网基线 | 下降 >= 15% |

说明：目标以阶段0采集基线为准，不使用静态估算值。

## 6.3 质量验收

- 全量单测通过；
- 核心集成测试通过；
- 不允许出现 `intent_plan` 残留引用（代码与测试双清理）。

---

## 7. 风险与缓解

| 风险 | 影响 | 概率 | 缓解措施 |
|------|------|------|----------|
| decompose_goals 质量波动 | 路由不稳定 | 中 | 增加规则兜底 + 结构化校验失败降级为单目标 |
| 一步到位改动过大 | 回归风险 | 中高 | 分阶段提交 + 每阶段回归 + 灰度发布 |
| SSE 事件切换导致前端误判 | 可观测性异常 | 中 | 兼容开关 + 双模式自动化测试 |
| 漏删 intent_plan 引用 | 运行时异常 | 高 | 增加 `rg intent_plan` 清零门禁到 CI |

---

## 8. 灰度与回滚

## 8.1 灰度策略

- Week1: 10%
- Week2: 50%
- Week3: 100%

监控项：首字延迟、错误率、路由准确率、覆盖率缺口率。

## 8.2 回滚方案

### 快速回滚（5 分钟）

```bash
export ENABLE_PLAN_READY_COMPAT=true
export ENABLE_SUPERVISOR_DECOMPOSE=false
# 重启服务
systemctl restart fastapi
```

### 完全回滚（30-60 分钟）

```bash
git checkout <stable_tag_or_commit>
./scripts/deploy.sh
```

---

## 9. 实施完成定义（DoD）

1. `planner` 节点及其代码路径已删除；
2. `intent_plan` 状态字段与主流程引用已删除；
3. 复合请求拆解能力保持，且顺序执行正确；
4. 选中待办场景准确率达到目标；
5. SSE 在兼容模式与最终模式均通过测试；
6. 性能指标达到验收阈值。

---

## 10. 变更历史

| 日期 | 版本 | 变更内容 | 作者 |
|------|------|----------|------|
| 2026-03-02 | v1.0 | 初始方案 | Claude |
| 2026-03-02 | v1.1 | 按方案A补齐实施细节、兼容路径、测试与回滚 | Codex |
