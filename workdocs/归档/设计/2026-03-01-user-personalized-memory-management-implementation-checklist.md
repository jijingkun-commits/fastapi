# 用户个性化永久记忆与管理能力实施清单（Checklist）

- 文档版本：v1.0
- 创建日期：2026-03-01
- 适用范围：`/Users/jijingkun/bojxAI/fastapi` 用户个性化永久记忆与管理能力
- 关联设计：`/Users/jijingkun/bojxAI/fastapi/workdocs/归档/设计/2026-03-01-user-personalized-memory-management-design.md`
- 关联实施方案：`/Users/jijingkun/bojxAI/fastapi/workdocs/归档/实施计划/用户个性化永久记忆与管理能力_implementation_plan.md`
- 使用方式：按卡片执行时逐项勾选；未满足项不可推进到下一阶段。

---

## 0. 前置门禁（进入开发前）

- [ ] `design_approved=true` 审批记录已存在且与当前方案一致。
- [ ] 当前任务上下文已确认（`_active_task.json` 与本清单同主题）。
- [ ] 执行模式确认为 `serial`，不跨卡片并发改动。
- [ ] 目标范围已锁定（本轮仅覆盖记忆管理能力，不扩展无关需求）。
- [ ] 回滚策略已预设（开关回退 + 路由兼容回退）。

---

## 1. API 层清单（memory-admin）

- [ ] 新增语义化接口：`GET /memory-admin/memories`。
- [ ] 新增语义化接口：`GET /memory-admin/memories/{memory_id}`。
- [ ] 新增语义化接口：`GET /memory-admin/memories/{memory_id}/chunks`。
- [ ] 新增治理接口：`POST /memory-admin/memories/{memory_id}/archive`。
- [ ] 新增治理接口：`DELETE /memory-admin/memories/{memory_id}`。
- [ ] 新增调试接口：`POST /memory-admin/memories/search-debug`。
- [ ] 兼容接口仍可用：`/document/rebuild-embeddings`、`/document/embedding-status`、`/document/retry-failed`。
- [ ] 参数校验完整（分页、过滤、可选字段、错误码语义）。

---

## 2. Service 层清单（编排与审计）

- [ ] 归档流程在 Service 层统一编排，不把业务策略下沉到 API/Repo。
- [ ] 删除流程在 Service 层统一编排，执行前有明确校验与确认机制。
- [ ] 调试查询流程与主对话链路解耦（仅管理域可调用）。
- [ ] 管理动作结果统一状态：`accepted | processing | completed | failed`。
- [ ] 每次管理动作都写审计（成功与失败都记录）。
- [ ] 审计失败时降级为日志，不阻断主业务返回。

---

## 3. Repo 与数据层清单

- [ ] 列表查询支持分页、筛选、排序，且默认只看 `active`。
- [ ] 详情查询按需加载，不在列表接口回传大字段正文。
- [ ] 分块查询可返回向量状态（`pending | ready | failed`）。
- [ ] 归档实现为逻辑状态变更（`active -> archived`）。
- [ ] 删除流程保证文档与分块的一致性清理。
- [ ] 数据库迁移脚本包含审计表 `t_user_memory_admin_audit`。

---

## 4. 配置与开关清单

- [ ] `feature.enable_document_memory_admin_api` 行为与预期一致。
- [ ] `feature.enable_document_memory_admin_web` 已接入并可动态控制入口可见性。
- [ ] `feature.enable_document_memory_admin_audit` 已接入并可单独控制审计。
- [ ] `memory.document.admin.max_page_size` 已生效并有边界校验。
- [ ] 关闭开关后系统可平滑降级（返回明确提示，不抛内部错误）。

---

## 5. 管理后台（Web）清单

- [ ] 管理页面可加载记忆列表（含分页/筛选）。
- [ ] 详情抽屉可展示正文与分块状态。
- [ ] 归档、删除操作具备确认交互和结果反馈。
- [ ] 搜索调试页面可展示召回结果分数与引用来源。
- [ ] 异常态可见（空数据、接口失败、超时、部分失败）。
- [ ] 前端只消费 API，不在页面层拼业务规则。

---

## 6. 测试与验收清单

- [ ] API 合约测试覆盖：列表、详情、chunks、archive、delete、search-debug。
- [ ] Service 单测覆盖：流程编排、状态流转、审计写入。
- [ ] Repo 单测覆盖：分页过滤、状态统计、删除一致性。
- [ ] 权限测试覆盖：管理员、非管理员、禁用场景。
- [ ] 前端冒烟通过：列表、详情、治理动作、调试查询。
- [ ] 回归验证通过：既有文档记忆召回主链路无回退。

---

## 7. 发布与文档收口清单

- [ ] 相关设计文档与实施文档状态已同步（进行中/完成/阻塞）。
- [ ] 路由与配置变更已同步到文档索引（`docs/SUMMARY.md`）。
- [ ] 运维手册补充了开关说明、故障排查、回滚步骤。
- [ ] 验收结论已记录（通过/附条件通过/不通过）。
- [ ] 下一轮遗留项已列清单并指定责任人和截止时间。

---

## 8. 最终放行（Go/No-Go）

- [ ] 功能闭环已打通（查询、治理、调试、审计）。
- [ ] 测试证据充分且可复现。
- [ ] 配置开关和回滚路径可用。
- [ ] 文档、状态、责任人同步完成。

> 放行规则：以上任一项未满足，结论应为 **No-Go**。
