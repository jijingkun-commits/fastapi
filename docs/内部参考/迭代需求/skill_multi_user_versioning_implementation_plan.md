# Skill 多用户版本治理实施方案（P3）

> 文档状态：实施基线（`/plan core`）
> 更新时间：2026-02-18
> 对应总控：`docs/内部参考/迭代需求/openclaw全量迁移_implementation_plan.md`

---

## 1. 方案概览

目标：把 Skill 从“全局共享配置”升级为“定义/版本/用户绑定”三层治理。

原则：

1. 按 `user_id` 做隔离与覆盖（多用户），不引入多租户模型。
2. 保持现有 `agent_skill` 兼容路径，分阶段迁移。
3. 发布、回滚、绑定全链路可追溯。

---

## 2. 数据模型

建议三层：

1. `skill_definition`：skill 基础元数据（稳定 ID、名称、分类）。
2. `skill_version`：版本化内容（prompt、schema、tool deps、状态）。
3. `user_skill_binding`：用户绑定（是否启用、锁定版本、优先级、用户覆盖配置）。

约束：

1. `UNIQUE(user_id, skill_id)`
2. 版本状态：`draft/published/rollbacked/deprecated`

---

## 3. 代码改造点

1. `app/models/agent_skill.py`：保留兼容读取，新增版本与绑定模型。
2. `app/services/skill_service.py`：
   - 发布/回滚版本
   - 按用户解析最终技能清单
   - 缓存刷新与失效
3. `app/api/v1/endpoints/skill_admin_api.py`：
   - 发布接口
   - 回滚接口
   - 用户绑定/启停/优先级接口

---

## 4. 运行时解析顺序

1. 全局默认版本（published）。
2. 用户绑定覆盖（enabled/version/priority）。
3. 若用户未绑定，回退全局默认。

---

## 5. 测试计划

1. 单元：版本发布、回滚、同名版本冲突。
2. 单元：用户绑定解析顺序与优先级。
3. 集成：用户 A/B 对同一 skill 启停互不影响。
4. 回归：无用户绑定时行为与现网一致。

---

## 6. 发布与回滚

开关建议：

1. `ENABLE_SKILL_VERSIONING`
2. `ENABLE_USER_SKILL_BINDING`

回滚策略：

1. 关闭开关回到旧 `agent_skill` 路径。
2. 新表数据保留，允许后续继续灰度。

---

## 7. 与总控迁移方案映射

对应总控文档：`docs/内部参考/迭代需求/openclaw全量迁移_implementation_plan.md`

1. 批次映射：Batch-2/Batch-4 的能力衔接专题。
2. 前置依赖：P2 工具治理一期稳定。
3. 退出条件：发布、绑定、回滚、回归测试完成。
