# 并行计划书：Skill 检索能力对齐 Cursor（MVP）

> 计划 ID: PP-20260212-SKILL-ALIGN-MVP  
> 主题: Skill 自动触发与检索链路平台化升级  
> 输入来源: `docs/内部参考/迭代需求/requirements.md` / `docs/内部参考/迭代需求/implementation_plan.md`

---

## 0. G0 协议冻结

### 0.1 目标

在并行开发前冻结 Skill 检索链路的跨层数据契约，确保服务层、工作流层、观测层语义一致。

### 0.2 冻结字段清单

#### `skill_candidates`

- required:
  - `skill_id`
  - `vector_score`
  - `keyword_score`
  - `final_score`
- optional:
  - `priority_boost`
  - `drop_reason`
- 兼容说明:
  - 新字段仅可追加 optional，不得删改 required。

#### `selected_skill_ids`

- required:
  - `selected_skill_ids`
- optional:
  - `selection_reason`
- 兼容说明:
  - 必须保持有序数组语义，按最终得分降序。

#### `skill_context`

- required:
  - `content`
- optional:
  - `source_skills`
  - `truncated`
  - `budget_used`
- 兼容说明:
  - 内容格式允许扩展，但必须保持文本可读。

### 0.3 owner / consumer

- 契约 owner：`WS-03_混合检索与注入策略`
- 元数据 owner：`WS-01_技能元数据与迁移`
- 导入语义 owner：`WS-02_SKILL导入与frontmatter治理`
- 观测消费方：`WS-04_可观测与离线评测`

---

## 1. 并行判定（四问）

1. 是否可独立开始并独立交付：**是**
2. 是否可做到文件白名单互斥：**是**
3. 是否存在不可消解状态冲突：**否（已定义 owner）**
4. 是否可各自执行局部验收：**是**

结论：**并行通过**。

---

## 2. 自动拆分依据

### 2.1 冲突图核心维度

1. 文件冲突：`agent_skill.py` / `skill_service.py` / `multi_agent_graph.py` 分离。
2. 状态冲突：`skill_candidates` 与 `skill_context` owner 分离。
3. 依赖阻断：Gate 层依赖并行层完成后执行。

### 2.2 分组结果

- 并行层：`WS-01`、`WS-02`、`WS-03`、`WS-04`
- 串行门禁层：`WS-G1` -> `WS-G2`

---

## 3. 工作包总览

| WS | 名称 | 类型 | 可并行 | 依赖 |
|---|---|---|---|---|
| WS-01 | 技能元数据与迁移 | Backend | 是 | G0 |
| WS-02 | SKILL导入与frontmatter治理 | Backend | 是 | WS-01 |
| WS-03 | 混合检索与注入策略 | Backend/Workflow | 是 | WS-01, WS-02 |
| WS-04 | 可观测与离线评测 | Observability/Test | 是 | WS-03 |
| WS-G1 | 集成回归门禁 | Gate | 否 | WS-01, WS-02, WS-03, WS-04 |
| WS-G2 | 文档终稿门禁 | Gate | 否 | WS-G1 |

---

## 4. 冲突矩阵（互不干涉）

| 资源 | Owner WS | 其他 WS 是否可改 | 规则 |
|---|---|---|---|
| `app/models/agent_skill.py` | WS-01 | 否 | 模型结构单所有者 |
| `alembic/*agent_skill*` | WS-01 | 否 | 迁移单所有者 |
| `app/services/skill_service.py` | WS-02/WS-03（阶段所有权） | 否（同阶段） | 以依赖顺序串接 |
| `app/ai/workflow/multi_agent_graph.py` | WS-03 | 否 | 注入策略单所有者 |
| `tests/**skill*` | WS-04 | 可追加不可改语义 | 回归资产单所有者 |
| `docs/**` | WS-G2 | 否（Gate 前） | 文档终稿单所有者 |

---

## 5. 依赖图与里程碑

1. M1：`WS-01` 完成元数据迁移。
2. M2：`WS-02` 完成导入治理。
3. M3：`WS-03` 完成混合检索与注入策略。
4. M4：`WS-04` 完成可观测与离线评测。
5. M5：`WS-G1` 门禁通过。
6. M6：`WS-G2` 文档门禁通过并收口。

---

## 6. 合并策略

1. 并行层按依赖顺序准入：`WS-01 -> WS-02 -> WS-03 -> WS-04`（实现可并行，合并按依赖）。
2. Gate 层固定串行：`WS-G1 -> WS-G2`。
3. 任一 WS 失败不允许跨 WS 修补，必须回到 owner WS 处理。

---

## 7. 串行回退说明

当前结论：未触发串行回退。若出现以下情况，立即回退：

1. `skill_service.py` 多 WS 并发冲突无法解消。
2. `skill_context` 语义出现双 owner。
3. Gate 复测无法归因责任 WS。

---

## 8. Gate 预设

### 8.1 WS-G1 门禁命令

1. `venv/bin/python -m pytest -q app/tests/test_skill_retrieval_smoke.py`
2. `venv/bin/python -m pytest -q tests -k "skill"`
3. `venv/bin/python scripts/docs_guard.py --strict`

### 8.2 WS-G2 门禁命令

1. 文档映射核对（架构/数据库/配置/测试）
2. `venv/bin/python scripts/docs_guard.py --strict`

---

## 9. 看板导出索引

- 任务拆解目录 ID：`2026-02-12_skill检索对齐_cursor_mvp`
- WS 总数：`6`
- Gate 总数：`2`
- 默认列流转：`Backlog -> Doing -> Review -> Gate -> Done`

