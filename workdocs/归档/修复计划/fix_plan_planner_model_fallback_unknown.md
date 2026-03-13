# fix_plan_planner_model_fallback_unknown

## 1. 问题摘要
- 现象：前端 Planner 状态提示出现“模型主判定失败，已切换规则兜底：unknown”，无法直接看到具体失败原因。
- 影响范围：`multi_agent_graph` 的 `model_primary` 规划路径；用户侧提示、排障效率与可观测性受影响。
- 严重级别：中（功能可继续执行，但根因被遮蔽，影响故障定位与运维判断）。

## 2. 根因结论

### 根因假设矩阵
| 假设ID | 假设描述 | 证据 | 验证动作 | 结果 |
|---|---|---|---|---|
| H1 | 当前轮没有真正调用模型（是 `heuristic_only` 或 planner 未初始化） | 日志显示创建图后加载了轻量模型 `qwen3.5-flash` | 检查运行日志中的模型初始化记录 | FAIL |
| H2 | 模型已调用，但返回结构不符合 `_IntentPlanModel`（`goals` 返回字符串数组） | 日志出现 `2 validation errors for _IntentPlanModel`，`goals.0/goals.1` 均为 `input_type=str` | 对照 `_infer_model_intent_plan` 的 Pydantic 解析路径 | PASS |
| H3 | 错误原因被合同校验层丢弃，导致前端显示 `unknown` | `IntentPlanContract` 不包含 `fallback_meta`；`validate_intent_plan_contract` 后字段消失 | 本地脚本构造含 `fallback_meta` 的样例并校验，输出中该字段为 `None` | PASS |

### 最终根因
- 根因 1（主因）：Planner 主判定模型在该请求上返回了不符合结构化协议的 `goals` 形态（字符串数组），触发 `_infer_model_intent_plan` 的结构校验失败并进入 `heuristic_fallback`。
- 根因 2（观测因）：`fallback_meta` 在合同校验后被裁剪，`_planner_node` 从已裁剪的 `intent_plan` 取 `fallback_reason`，因此用户提示退化为 `unknown`。

### 证据链
- 日志证据（模型调用与失败）：
  - `logs/assistant.log` 记录 Planner 使用轻量模型：`model=qwen3.5-flash`。
  - `logs/assistant.log` 记录失败原因：`planner_model_fallback_to_heuristic: 2 validation errors for _IntentPlanModel`，并指向 `goals.0/goals.1` 为字符串输入。
- 代码证据（失败触发点）：
  - `app/ai/workflow/multi_agent_graph.py`：`_infer_model_intent_plan` 对 `raw_output` 进行 `_IntentPlanModel` 校验，失败时抛出 `_PlannerModelOutputError`。
  - `app/ai/workflow/multi_agent_graph.py`：`_build_planner_intent_plan` 捕获异常后写入 `fallback_meta.reason`。
- 代码证据（原因丢失点）：
  - `app/ai/contracts/delivery_contracts.py`：`IntentPlanContract` 未定义 `fallback_meta`。
  - `app/ai/contracts/delivery_contract_validators.py`：`model_dump()` 后仅保留合同字段，`fallback_meta` 被忽略。
  - `app/ai/workflow/multi_agent_graph.py`：`_planner_node` 读取校验后的 `intent_plan`，最终 `fallback_reason` 为空并展示为 `unknown`。

### 已排除假设
- 非 `heuristic_only` 模式误触发：排除（当前链路在 `model_primary` 下运行）。
- Planner LLM 初始化失败并回退到 supervisor 模型：本次样本排除（日志无 `planner_llm_init_failed_fallback_to_supervisor_llm`，且看到轻量模型加载成功）。
- 数据库路由配置缺失：排除（`model_routing.lightweight` 已绑定有效模型）。

## 3. 修复方案对比（2-3 方案）
| 方案 | 优点 | 缺点 | 成本 | 推荐度 |
|---|---|---|---|---|
| A. 在 `IntentPlanContract` 中纳入 `fallback_meta` | 前后端可直接拿到失败原因，改动直观 | 语义合同混入控制面故障元信息，边界变脏 | 低 | ⭐⭐⭐ |
| B. 保持语义合同纯净，在 `_planner_node` 使用校验前 `raw_intent_plan` 提取 fallback 原因，并写入 `delivery_meta`/状态文案 | 符合控制面与语义面分层，兼容现有合同，不破坏下游依赖 | 需补一层“原始元信息 -> 展示/观测元信息”映射 | 低-中 | ⭐⭐⭐⭐⭐ |
| C. 强化模型主判定鲁棒性（更严格结构化调用 + 对 `goals: list[str]` 做兼容归一） | 直接降低 fallback 频率，提升主判定命中率 | 改动面较大，需更充分回归；可能影响模型成本/延迟 | 中 | ⭐⭐⭐⭐ |

### 推荐方案
- 推荐：**B（主） + C（增量）**。
- 理由：先修“原因可见性”保证排障闭环，再做模型输出鲁棒性治理，避免把观测问题和模型稳定性问题耦合在一次大改中。

## 4. 推荐方案实施清单
- 代码变更：
  - `app/ai/workflow/multi_agent_graph.py`
    - 在 `_planner_node` 中保留 `raw_intent_plan` 的 fallback 元信息用于状态提示与 `delivery_meta`。
    - 对用户可见错误原因做白名单化（仅 `reason`/`fallback_rule_id`/`trigger`），避免直接暴露敏感 `detail`。
  - `app/ai/contracts/delivery_contract_validators.py`（可选）
    - 不改合同结构，仅在元信息汇总函数中接收 planner fallback 观测字段。
  - `tests/unit/` 新增或扩展用例
    - 覆盖“模型输出非法 -> fallback 原因在状态消息可见”。
    - 覆盖“合同校验后语义字段不被污染，观测字段在 `delivery_meta` 可追踪”。
- 数据库变更：无必需变更。
- 配置变更（可选灰度）：
  - 若 `qwen3.5-flash` 在结构化输出不稳定，可在灰度环境将 `model_routing.lightweight` 临时切到结构化约束更稳定模型后观察。

## 5. 风险与回滚
- 风险：
  - 将内部错误原文直接透传到用户文案，可能泄露供应商或网关细节。
  - 观测字段写入位置变化后，现有监控脚本若硬编码路径可能失效。
- 回滚策略：
  - 通过开关控制“前端展示详细 fallback reason”是否开启，异常时回退到现有文案。
  - 保留旧 `delivery_meta` 字段兼容一个版本窗口，监控稳定后再清理。

## 6. 验证计划
- 单元测试：
  - 模拟 `_infer_model_intent_plan` 抛出 `_PlannerModelOutputError`，断言 `_planner_node` 状态文案不再出现 `unknown`。
  - 断言 `IntentPlanContract` 仍保持语义字段集合（无 `fallback_meta` 污染）。
- 集成测试：
  - 用真实会话输入“先查待办 + 再看天气”回放一次，校验 SSE `status` 与 `plan_ready` 的观测字段。
- 手动验证：
  - 前端确认文案可见规则化 reason（如 `planner_model_error:_PlannerModelOutputError`）。
  - 日志可检索到 `fallback_rule_id/trigger`，且与前端提示一致。

## 7. 实施顺序与工作量
- 顺序：
  1. 先补 `planner_node` 观测透传（方案 B）。
  2. 补单测与 SSE 回归。
  3. 再评估并灰度推进模型输出鲁棒性优化（方案 C）。
- 工时估算：
  - 方案 B：0.5 人日。
  - 方案 C（兼容归一 + 回归）：1~1.5 人日。
