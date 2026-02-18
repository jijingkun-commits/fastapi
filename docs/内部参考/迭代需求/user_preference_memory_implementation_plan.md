# 跨会话用户偏好记忆实施方案（2026-02）

> 文档状态：实施基线（`/plan core`）
> 更新时间：2026-02-16
> 对应需求：`docs/内部参考/迭代需求/user_preference_memory_requirements.md`

---

## 1. 方案概览

本方案采用“MVP 先行”策略：先落地规则化显式偏好记忆，确保稳定可控，再逐步扩展到语义记忆。

实施目标：

1. 建立 `t_user_memory` 数据模型，承载用户级跨会话偏好。
2. 在 `ChatService.stream` 中打通“读取注入 + 显式写入”闭环。
3. 通过环境变量开关控制发布与回退。

---

## 2. 架构影响与约束

### 2.1 模块边界

1. **存储层**：`app/models/user_memory.py` + `app/repositories/user_memory_repo.py`。
2. **业务规则层**：`app/services/user_preference_memory_service.py`（规则提取与上下文格式化）。
3. **接入层**：`app/services/chat_service.py`（读取注入与写入触发）。

约束：不得把记忆规则散落到 `workflow` 节点与 prompt 文本中，避免重复策略源。

### 2.2 状态契约

1. 记忆记录 canonical 结构：`user_id + scope + memory_key + memory_value`。
2. 活跃状态字段：`status=active`；删除策略后续使用软删除扩展。
3. 读取结果只以 `SystemMessage` 注入，不写回用户输入内容。

### 2.3 路由闭环

固定闭环：

`用户输入 -> 保存 human 消息 -> 显式偏好提取并持久化 -> 读取偏好 -> 注入系统上下文 -> Graph 执行`

禁止在其他链路旁路写记忆（如工具节点直接写库）。

### 2.4 端到端链路

1. 前端保持现有请求结构，不新增字段。
2. 后端在 `ChatService` 内部完成记忆处理，不改变 SSE 协议。
3. 历史消息展示保持原样，不暴露内部记忆注入文本。

### 2.5 可测试性

1. 规则提取函数做纯单测覆盖（中英文、长短偏好、结论优先）。
2. 上下文格式化函数覆盖条数限制与排序稳定性。
3. 回归验证聊天主链路：功能关闭、读取异常、未登录用户场景。

---

## 3. 数据设计

### 3.1 新增表 `t_user_memory`

关键字段：

1. `user_id`：用户 ID。
2. `scope`：作用域（首期仅 `global`）。
3. `memory_key`：偏好键（如 `response.language`）。
4. `memory_value`：偏好值（如 `zh-CN`）。
5. `confidence`：置信度（首期规则写死区间）。
6. `source_thread_id/source_message_id`：追溯来源。
7. `status`：记录状态（active/deleted 预留）。

索引策略：

1. `idx_user_memory_user_scope`：`(user_id, scope)` 用于读取。
2. `idx_user_memory_active_unique`：`(user_id, scope, memory_key)` + `status='active'` 唯一，保障 upsert。

### 3.2 迁移策略

1. 新增 Alembic 迁移脚本创建表与索引。
2. 不回填历史数据，发布后按自然流量逐步积累。

---

## 4. 代码改造点

### 4.1 服务与仓储

1. `user_memory_repo`：读取活跃偏好、按 key 查询、创建/更新。
2. `user_preference_memory_service`：
   - 显式偏好规则提取（触发词 + 键值规则）
   - 记忆上下文拼装（系统提示格式 + 摘要压缩）
   - 读取结果冲突去重（按 `update_time` 倒序取最新值）
   - 偏好持久化（按 key 覆盖）

### 4.2 ChatService 接入

1. `stream` 开始前读取用户偏好并构造 `SystemMessage` 注入 `input_messages`。
2. human 消息落库后，使用原始用户输入触发显式偏好提取并写入。
3. 异常策略：记忆模块异常仅告警，不中断对话。

### 4.3 检索与压缩策略

1. 仓储层保持 `update_time DESC` 排序，确保新偏好优先。
2. 服务层对检索结果进行“同 key 去重”，防御历史脏数据或人工写入冲突。
3. 当上下文超出阈值时，自动降级为压缩摘要（保留关键偏好 + 省略计数）。

### 4.4 配置项

新增环境变量：

1. `ENABLE_USER_PREFERENCE_MEMORY`
2. `USER_PREFERENCE_MEMORY_MAX_ITEMS`

---

## 5. 风险评估

| 风险 | 级别 | 触发条件 | 缓解策略 |
|---|---|---|---|
| 规则误判 | 中 | 触发词命中但非偏好语义 | 首期仅支持白名单 key + 显式触发词 |
| 注入冗余 | 中 | 偏好数量过多 | 通过 `MAX_ITEMS` 限制注入条数 |
| 性能抖动 | 低 | 每轮新增一次读库 | 读取索引优化 + 异常降级 |
| 跨用户污染 | 高 | 查询条件遗漏 user_id | 仓储层强制 user_id 过滤 + 单测覆盖 |

---

## 6. 实施步骤（建议顺序）

1. 文档更新：需求/方案/数据库/配置说明/聊天需求。
2. 新增模型与迁移：`t_user_memory`。
3. 新增仓储与服务：完成提取、读写、格式化能力。
4. ChatService 接入：注入与写入闭环。
5. 补充单测并执行 targeted pytest。

---

## 7. 发布与回滚

1. 发布前执行迁移脚本。
2. 默认可在灰度环境开启 `ENABLE_USER_PREFERENCE_MEMORY=true`。
3. 若出现异常，可通过开关快速回滚到“无记忆”模式，无需回滚表结构。

---

## 8. 与总控迁移方案映射

对应总控文档：`docs/内部参考/迭代需求/openclaw全量迁移_implementation_plan.md`

1. 批次映射：本专题对应 **Batch-4（跨会话偏好记忆接线）**。
2. 进入条件：Batch-0 文档治理拆分完成，批次映射已回挂。
3. 本批产出：
   - `t_user_memory` 记忆读写闭环；
   - `ChatService` 读取注入与显式写入接线；
   - 开关化发布与快速回滚能力。
4. 退出条件：
   - 本文 2~7 节能力落地并通过测试；
   - 记忆异常不阻断主对话；
   - 配置与文档同步完成。
5. 回滚锚点：
   - `ENABLE_USER_PREFERENCE_MEMORY`
   - `USER_PREFERENCE_MEMORY_MAX_ITEMS`
