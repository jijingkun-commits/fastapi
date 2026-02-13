# Skill 管理后台前端对齐 - 实施计划

> 从属需求：[skill_admin_frontend_requirements.md](skill_admin_frontend_requirements.md)
>
> 基线 commit：52ed26d（skill功能完善）
>
> 目标：前端管理页面完全对齐后端 Skill 治理 API

---

## 1. 架构影响与约束

### 1.1 模块边界

- 变更范围严格限于前端 `web/src/` 目录
- 后端 API 已就绪，本轮零后端改动
- 涉及文件：
  - `web/src/lib/skill-admin-api.ts`（API 客户端 + 类型定义）
  - `web/src/components/admin/SkillAdminPanel.tsx`（主面板，需拆分子组件）

### 1.2 状态契约

后端 `SkillResponse` 已返回但前端未消费的字段：

| 字段 | 类型 | 前端当前状态 |
|------|------|-------------|
| `is_enabled` | `boolean` | ❌ 未定义 |
| `auto_enabled` | `boolean` | ❌ 未定义 |
| `priority` | `number` | ❌ 未定义 |
| `scope` | `string` | ❌ 未定义 |
| `trigger_phrases` | `string[]` | ❌ 未定义 |
| `conflicts_with` | `string[]` | ❌ 未定义 |

后端 `SearchResultItem` 已返回但前端未消费的字段：

| 字段 | 类型 | 前端当前状态 |
|------|------|-------------|
| `vector_score` | `number` | ❌ 未定义 |
| `lexical_score` | `number` | ❌ 未定义 |
| `trigger_hit` | `number` | ❌ 未定义 |

后端已有但前端无对应 API 函数：

| 接口 | 方法 | 用途 |
|------|------|------|
| `/skills/{skill_id}/meta` | `PATCH` | 元数据更新 |
| `/search/hybrid` | `GET` | Hybrid 调试视图 |

### 1.3 可测试性

- 类型对齐可通过 TypeScript 编译验证
- UI 交互通过 Playwright E2E 覆盖
- 前端校验逻辑可抽取为纯函数做 Unit Test

---

## 2. 实施阶段

### Phase 1：类型定义与 API 客户端对齐（CAP-01）

**目标**：`skill-admin-api.ts` 类型和函数与后端 Schema 一一对应

**变更文件**：`web/src/lib/skill-admin-api.ts`

**具体任务**：

1. `Skill` 接口补齐 6 个治理字段
2. `SkillDetail` 接口补齐 6 个治理字段
3. `SearchResult` 接口补齐 `vector_score`、`lexical_score`、`trigger_hit`
4. 新增 `SkillMetadataUpdate` 接口（对应 `SkillMetadataUpdateRequest`）
5. 新增 `HybridSearchResult` 接口（对应 `/search/hybrid` 响应结构）
6. 新增 `updateSkillMetadata(skillId, data)` API 函数
7. 新增 `searchSkillsHybrid(query, params)` API 函数

**验证**：`pnpm tsc --noEmit` 无新增类型错误

---

### Phase 2：技能列表升级（CAP-02）

**目标**：列表展示治理元数据 + 筛选 + 批量操作

**变更文件**：`web/src/components/admin/SkillAdminPanel.tsx`

**具体任务**：

1. 表格新增列：
   - 启用状态：绿色/灰色圆点或 Switch 组件
   - 自动触发：同上
   - 优先级：数字 Badge
   - 作用域：彩色 Badge（global=蓝、data=绿、todo=橙、admin=紫）
2. 筛选栏新增：
   - 启用状态下拉：全部 / 已启用 / 已禁用
   - 作用域下拉：全部 / global / data / todo / admin
3. 批量操作：
   - 每行添加 Checkbox
   - 选中后顶部出现批量操作栏（批量启用 / 批量禁用）
   - 批量操作调用逐条 `PATCH /meta`，Promise.allSettled 后汇总结果

**验证**：启动开发服务器，列表正确展示新字段，筛选和批量操作可用

---

### Phase 3：元数据编辑面板（CAP-03）

**目标**：在详情对话框中支持元数据编辑

**变更文件**：`web/src/components/admin/SkillAdminPanel.tsx`（或拆出 `SkillMetadataEditor.tsx`）

**具体任务**：

1. 详情对话框改为双区域布局：
   - 左侧/上方：只读信息（skill_id、name、content 预览、向量状态）
   - 右侧/下方：可编辑元数据表单
2. 表单字段：
   - `is_enabled`：Switch
   - `auto_enabled`：Switch
   - `priority`：Number Input（0-10000）
   - `scope`：Select（global/data/todo/admin）
   - `trigger_phrases`：Tag Input（输入后回车添加，点击 x 删除）
   - `conflicts_with`：Multi-Select（从已有技能列表中选择，排除自身）
3. 前端校验：
   - priority 范围 0-10000
   - conflicts_with 不能包含自身 skill_id
   - trigger_phrases 去重去空
4. 提交调用 `updateSkillMetadata`，成功后关闭对话框并刷新列表

**验证**：编辑各字段并提交，数据库值正确更新

---

### Phase 4：Hybrid 检索调试视图（CAP-04）

**目标**：升级搜索测试 Tab 为 Hybrid 调试视图

**变更文件**：`web/src/components/admin/SkillAdminPanel.tsx`

**具体任务**：

1. 将现有"搜索测试"Tab 升级为三子 Tab：
   - "快速搜索"：保留现有简化搜索
   - "Hybrid 调试"：调用 `/search/hybrid`，展示完整调试信息
2. Hybrid 调试视图：
   - 参数栏：query 输入、scope 选择、auto_only 开关、top_k 滑块、threshold 滑块
   - 结果区域：
     - 候选列表表格：skill_id、name、vector_score、lexical_score、trigger_hit、总分
     - 分数可视化：每行用三段式进度条展示三维分数占比
     - 淘汰候选折叠区：展示被过滤的候选及原因
     - context_preview 折叠区：展示最终注入的章节级上下文

**验证**：输入查询，三维分数正确展示，淘汰原因可见

---

### Phase 5：文档同步与测试（CAP-05）

**目标**：文档与测试用例同步

**变更文件**：
- `docs/开发文档/测试管理/管理后台测试案例.md`
- `docs/开发文档/架构设计/前端架构.md`

**具体任务**：

1. 管理后台测试案例新增 Skill 前端用例（SKILL-FE-TC-01 ~ 06）
2. 前端架构文档更新 SkillAdminPanel 组件说明

---

## 3. CAP 清单

| CAP-ID | 能力描述 | 影响模块 | 可并行 | 依赖 |
|--------|---------|---------|--------|------|
| CAP-01 | 类型定义与 API 客户端对齐 | `skill-admin-api.ts` | 是 | 无 |
| CAP-02 | 技能列表升级（元数据展示+筛选+批量） | `SkillAdminPanel.tsx` | 否 | CAP-01 |
| CAP-03 | 元数据编辑面板 | `SkillAdminPanel.tsx` 或新组件 | 否 | CAP-01 |
| CAP-04 | Hybrid 检索调试视图 | `SkillAdminPanel.tsx` | 否 | CAP-01 |
| CAP-05 | 文档同步与测试 | `docs/` | 是 | CAP-02~04 |

## 4. 边界矩阵

| CAP-ID | 可改文件白名单 | 禁止触碰区 |
|--------|---------------|-----------|
| CAP-01 | `web/src/lib/skill-admin-api.ts` | 后端 `app/` 目录 |
| CAP-02 | `web/src/components/admin/SkillAdminPanel.tsx` | 后端 API |
| CAP-03 | `web/src/components/admin/Skill*.tsx` | 后端 API |
| CAP-04 | `web/src/components/admin/Skill*.tsx` | 后端 API |
| CAP-05 | `docs/` | 代码文件 |

## 5. 最小验证矩阵

| CAP-ID | 最小验证命令 | 通过标准 |
|--------|-------------|---------|
| CAP-01 | `cd web && pnpm tsc --noEmit` | 零类型错误 |
| CAP-02 | 启动 dev server，访问 /admin/skills | 列表展示 6 个新字段 |
| CAP-03 | 点击技能详情，编辑元数据并提交 | PATCH 请求 200，列表刷新 |
| CAP-04 | 切换到 Hybrid 调试 Tab，执行搜索 | 三维分数和淘汰原因可见 |
| CAP-05 | `grep -c "SKILL-FE-TC" docs/开发文档/测试管理/管理后台测试案例.md` | ≥ 6 |

## 6. Gate 预设

- **G1 集成回归门禁**：CAP-01~04 全部完成后，`pnpm tsc --noEmit` + `pnpm lint` 通过
- **G2 文档终稿门禁**：CAP-05 完成，文档审阅通过

## 7. 执行顺序

```
CAP-01 (类型对齐)
  ├── CAP-02 (列表升级)
  ├── CAP-03 (编辑面板)
  └── CAP-04 (调试视图)
        └── CAP-05 (文档同步)
              └── G1 + G2
```

建议在另一个 worktree 按 CAP-01 → CAP-02 → CAP-03 → CAP-04 → CAP-05 顺序执行。CAP-02/03/04 之间理论上可并行，但共享 `SkillAdminPanel.tsx` 文件，串行更安全。
