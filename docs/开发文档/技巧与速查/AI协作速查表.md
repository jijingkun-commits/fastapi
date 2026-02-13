# AI 协作速查表

> 一句话原则：先把需求与边界讲清，再按命令工作流推进；并行场景优先保证“可机读、可追溯、可落卡”。

本文定位：开发人员一页速查卡。若需命令/技能/规则细节，请配合阅读 `vibe-coding开发技巧.md` 与 `.cursor/commands/*.md`。

---

## 1. 核心工作流

### 1.1 常规开发（单任务）

```text
想法 -> /clarify -> /plan -> /imp -> /review -> /test -> 验收
```

### 1.2 并行开发（多 AI / 多 worktree）

```text
想法 -> /clarify -> /plan -> /vkplan（= /rwfj） -> /vkkb（或 /vktodo）
     -> /imp-ws(并行层) -> /imp-ws(WS-G1) -> /imp-ws(WS-G2)
     -> /review -> /test -> 验收
```

并行执行顺序固定：

1. `WS-00_G0_协议冻结`（Foundation，由 `/rwfj` 生成并冻结，默认不单独执行 `/imp-ws`）
2. `WS-01 ... WS-N`（并行层）
3. `WS-G1_集成回归门禁`
4. `WS-G2_文档终稿门禁`

---

## 2. 并行流程逐步清单（推荐）

| 步骤 | 命令 | 关键产物 | 通过条件 |
|---|---|---|---|
| 1. 需求与方案 | `/plan` | `requirements.md` + `implementation_plan.md`（含 `task_key/card_seed`） | `task_key` 全局唯一，`card_seed` 字段完整 |
| 2. 并行拆解 | `/vkplan`（等价 `/rwfj`） | `parallel_plan.md` + `workstreams/WS-*.md` + `vk_cards.json` | 有 `WS-00`，每个 WS 含 `card_export`；VK 落卡默认不含 `WS-00` |
| 3. 看板一体落地 | `/vkkb <任务拆解目录>`（或 `/vktodo <任务拆解目录>`） | VK 实际卡片（`WS-01...WS-G2`） | 建卡成功且依赖关系正确 |
| 4. 子任务执行 | `/imp-ws @WS-*.md` | 代码 + 自检卡 | 仅改白名单，完成最小验证 |
| 5. Gate 回填 | `/imp-ws @WS-G1` + `/imp-ws @WS-G2` | Gate 结果回填到 `parallel_plan.md` | 门禁命令通过，回填脚本成功 |

---

## 3. 命令选型速查

| 场景 | 推荐命令 | 说明 |
|---|---|---|
| 快速澄清需求 | `/clarify` | 只问答，不落文档 |
| 规划（不拆卡） | `/plan` 或 `/plan core` | 只产出需求与技术方案 |
| 规划 + 并行拆解（推荐） | `/plan -> /vkplan` | `/vkplan` 等价 `/rwfj`，含 G0 冻结与落卡前产物 |
| 并行拆包（兼容） | `/rwfj` | 与 `/vkplan` 语义等价 |
| 基线同步（调试） | `/vksync <任务拆解目录>` | 校验 G0 是否在所有目标 worktree 生效 |
| 看板一体落地（推荐） | `/vkkb <任务拆解目录>` | 自动补导出并落卡 |
| 看板落卡（兼容） | `/vktodo <任务拆解目录>` | 自动读取 `vk_cards.json` 批量建卡（不含 `WS-00`） |
| 看板导出（可选） | `/vk` | 仅在需要审阅 payload 或排障时使用 |
| 看板推进（简化） | `/vktodo <任务拆解目录> move <状态>` | 按 `task_key` 前缀筛选并推进 |
| 执行单个 WS | `/imp-ws` | 按白名单改动并回填自检卡 |
| 单任务实现 | `/imp` | 不走并行流程时使用 |
| 代码审查 | `/review` | 质量与风险检查 |
| 测试验证 | `/test` | 回归验证与报告沉淀 |

---

## 4. 并行前 3 秒判断法

满足以下 4 条才建议 `/rwfj`：

1. 子任务可独立开始并独立交付（无需等待他人产出）
2. 文件白名单互斥（无共享文件并发写）
3. 关键状态字段无语义冲突（单写入权清晰）
4. 子任务可做局部验证（不依赖全量集成）

若任一不满足：

- 回退单任务 `/imp`
- 或先解耦后再拆分

---

## 5. 上下文注入（@）最小原则

只 @ 当前任务最相关文档，避免上下文污染。

| 场景 | 必须引用 | 可选引用 |
|------|---------|---------|
| 并行规划 | `@docs/内部参考/迭代需求/requirements.md` | `@implementation_plan.md` |
| 并行拆解 | `@implementation_plan.md` | `@requirements.md` |
| 执行 WS | `@workstreams/WS-*.md` | `@parallel_plan.md` |
| 修 Bug | `@错误日志` + `@疑似代码` | `@需求文档` |

---

## 6. 常见误区

- “并行 = 随便拆几个 WS”：错误；缺 `task_key/card_export` 会导致看板不可执行。
- “/plan 一定要出 seed”：错误；只有并行场景才建议 `/vkplan` 或 `/plan parallel`。
- “子任务阶段跑全量回归”：错误；并行层做最小验证，全量回归放 Gate 层。
- “Gate 结果手工改”：错误；必须走回填脚本，保证可追溯。

---

## 6.1 `/vktodo` 最简用法（新增）

1. 先执行 `/plan -> /vkplan`，产出 `vk_cards.json`。
2. 建卡可直接用路径直传：

```text
/vktodo 2026-02-12_skill检索对齐_cursor_mvp
```

3. 推进状态可直接用：

```text
/vktodo 2026-02-12_skill检索对齐_cursor_mvp move Doing
```

4. 若需要指定项目：

```text
/vktodo 2026-02-12_skill检索对齐_cursor_mvp create Backlog project=fastapi
```

---

## 7. 最终验收要点

1. `parallel_plan.md` 有 `task_key` 与看板导出索引。
2. 每个 `WS-*.md` 文末都有 `card_export`。
3. 卡片 ID 使用 `<task_key>::<WS-ID>`，标题采用 `WS-ID` 前置并保留 `task_key`。
4. `WS-00` 在 master 基线前置完成，不进入 VK 落卡列表。
5. `review/test` 在门禁收口后统一执行。
