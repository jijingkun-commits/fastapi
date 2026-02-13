# Skill 管理后台前端对齐需求

> 迭代目标：将管理后台前端页面对齐后端 Skill 治理能力（commit 52ed26d 基线）
>
> 关联模块需求：[管理后台需求](../../产品文档/管理后台需求.md) §3.4
>
> 关联后端 API：`app/api/v1/endpoints/skill_admin_api.py`

---

## 1. 背景与动机

后端已完成 Skill 元数据治理 + Hybrid 检索升级，但前端管理页面仍停留在"向量管理"阶段：

| 能力 | 后端状态 | 前端状态 | Gap |
|------|---------|---------|-----|
| 治理元数据展示 | ✅ 列表/详情已返回 6 字段 | ❌ 类型定义缺失，UI 未展示 | 需补齐 |
| 元数据编辑 | ✅ `PATCH /meta` | ❌ 无 API 函数，无编辑 UI | 需新建 |
| Hybrid 搜索调试 | ✅ `GET /search/hybrid` | ❌ 无 API 函数，无可视化 | 需新建 |
| 搜索结果多维分数 | ✅ 返回 vector/lexical/trigger | ❌ 只展示 similarity | 需升级 |
| 批量治理 | ✅ 后端支持逐条 PATCH | ❌ 无批量操作 UI | 需新建 |

---

## 2. 用户故事

### US-SKILL-FE-01：元数据可视化

**作为**平台管理员，**我需要**在技能列表中直观看到每个技能的启用状态、自动触发、优先级、作用域，**以便**快速判断技能治理现状。

**验收标准**：
- 列表表格新增列：启用状态（开关图标）、自动触发（开关图标）、优先级、作用域
- 详情对话框展示完整元数据（含 trigger_phrases、conflicts_with）
- 列表支持按启用状态、作用域筛选

### US-SKILL-FE-02：元数据编辑

**作为**平台管理员，**我需要**在管理后台直接编辑技能的治理元数据，**以便**无需操作数据库即可调整技能策略。

**验收标准**：
- 详情页或独立编辑面板支持修改：is_enabled、auto_enabled、priority、scope、trigger_phrases、conflicts_with
- trigger_phrases 支持标签式输入（添加/删除短语）
- conflicts_with 支持从已有技能列表中选择
- 提交后即时刷新列表
- 非法输入（自冲突、priority 超范围）前端校验 + 后端 400 错误展示

### US-SKILL-FE-03：Hybrid 检索调试

**作为**平台管理员/研发人员，**我需要**通过调试界面查看 Hybrid 检索的完整过程，**以便**理解技能命中逻辑并调优配置。

**验收标准**：
- 新增"Hybrid 调试"Tab 或升级现有"搜索测试"Tab
- 展示每个候选的三维分数：vector_score、lexical_score、trigger_hit
- 展示融合后总分（similarity）
- 展示被淘汰的候选及淘汰原因（disabled/scope_mismatch/conflict_eliminated 等）
- 展示最终注入的 context_preview（章节级）
- 支持 scope 和 auto_only 参数调节

### US-SKILL-FE-04：批量治理

**作为**平台管理员，**我需要**批量启用/禁用技能，**以便**高效管理大量技能的上线状态。

**验收标准**：
- 列表支持多选（checkbox）
- 提供批量操作栏：批量启用、批量禁用
- 操作完成后刷新列表并提示结果

---

## 3. 非功能需求

1. **一致性**：前端类型定义与后端 Pydantic Schema 字段一一对应
2. **响应性**：元数据编辑提交后 ≤ 1s 反馈结果
3. **可访问性**：开关、标签输入等交互组件需键盘可操作
4. **银行场景**：技能列表中应能识别 scope=data 的问数类技能与 scope=todo 的待办类技能

---

## 4. 测试追溯

| 编号 | 用例目标 | 类型 |
|------|---------|------|
| SKILL-FE-TC-01 | 列表展示新元数据字段 | E2E |
| SKILL-FE-TC-02 | 元数据编辑提交与校验 | E2E |
| SKILL-FE-TC-03 | Hybrid 调试视图展示 | E2E |
| SKILL-FE-TC-04 | 批量启用/禁用 | E2E |
| SKILL-FE-TC-05 | 筛选（启用状态/作用域） | E2E |
| SKILL-FE-TC-06 | 非法输入前端校验 | Unit |
