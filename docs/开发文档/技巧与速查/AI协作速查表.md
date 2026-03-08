# AI 协作速查表

> 一句话原则：先把需求与边界讲清，再按命令工作流推进；并行场景优先保证“可机读、可追溯、可落卡”。

本文定位：开发人员一页速查卡。若需命令/技能/规则细节，请配合阅读 `vibe-coding开发技巧.md` 与 `.cursor/commands/*.md`。

> 命令权威源：`.cursor/commands/*.md`。同步镜像：`.claude/commands/*.md`（Claude Code）与 `~/.codex/prompts/*.md`（Codex）。当速查表、工作流文档与命令文档冲突时，一律以命令文档为准。

> 命令触发差异：Claude Code / Cursor 可直接用 `/jjk-xxx`；Codex 需使用 `/prompts:jjk-xxx`。

> 产品运行时 Skill 门禁：命中 `skill_service.py`、`skill_admin_api.py`、`user_skill_api.py`、`agent_skill.py`、Skill runtime 测试、部署/退役脚本等 DB-only 主链路径时，必须按 `.cursor/rules/doc_sync.mdc` 的“产品运行时 Skill 专项映射（强制）”同步 `技能系统需求.md`、`AI技能库.md`、`接口文档.md`、相关配置/部署/测试文档，并保持“本地 `SKILL.md` / 导入脚本已退役”口径。

---

## 1. 核心工作流

### 1.1 常规开发（单任务）

```text
想法 -> /jjk-clarify -> /jjk-plan -> /jjk-imp -> /jjk-verify -> 验收
                                                  （或 /jjk-review -> /jjk-test -> 验收）
```

补充分流：
1. 默认只用 `/jjk-clarify` 完成“探索 + 冻结”闭环。
2. 若需要额外探索轮，也在当前 `/jjk-clarify` 会话内完成。

### 1.2 并行开发（多 AI / 多 worktree）

```text
想法 -> /jjk-clarify -> /jjk-plan parallel（或 /jjk-plan core） -> /jjk-vkplan
     -> /jjk-vktodo <任务拆解目录> create（create-only）
     -> /jjk-cardrun <任务拆解目录> loop
        （主控自动：选卡 -> 真实调用 /jjk-wtimp(cardrun_dispatch) -> verify -> merge -> 下一卡）
     -> python3 scripts/check_workflow_contract.py --mode gate_contract --task-split-dir <任务拆解目录>
     -> python3 scripts/check_workflow_contract.py --mode integration_gate --task-split-dir <任务拆解目录> --baseline master
     -> /jjk-verify -> 验收
                       （或 /jjk-review -> /jjk-test -> 验收）
```

并行执行顺序固定：

1. `/jjk-vktodo` create-only 一次性落卡（不负责推进状态）
2. `/jjk-cardrun loop` 按 `card_order` 串行执行实现卡，并强制每卡 `verify -> merge -> done`
3. `G01`：Gate 契约一致性校验
4. `IG01`：实现卡已合并且主干可见校验

### 1.3 开发前文档门禁（Clarify v3.2）

进入 `/jjk-plan` 之前必须满足：

1. `design.md` 已审批（`design_approved=true`）。
2. `design.md` 包含 `product_contract`（PRD-Lite）：
   - `target_users/core_scenarios/business_goals/non_goals/acceptance_gates`
3. `design_freeze_summary.product_contract_ready=true`。
4. `clarify_consistency_check.clarify_phase=approval` 且 `open_questions_count=0`。
5. `clarify_handoff_contract.required.product_contract_summary` 完整。
6. 修改 `jjk-clarify` 命令/模板后执行：`python3 scripts/check_clarify_contract_consistency.py`。

推荐在 `requirements + implementation_plan` 产出后执行：

```bash
python3 scripts/check_workflow_contract.py --mode clarify_plan \
  --requirements-path docs/内部参考/迭代需求/<topic>_requirements.md \
  --implementation-path docs/内部参考/迭代需求/<topic>_implementation_plan.md
```

---

## 2. 并行流程逐步清单（推荐）

| 步骤 | 命令 | 关键产物 | 通过条件 |
|---|---|---|---|
| 1. 需求与方案 | `/jjk-plan parallel`（或 `/jjk-plan core`） | 默认 `<topic>_requirements.md` + `<topic>_implementation_plan.md` | `task_key` 全局唯一；若 `card_seed` 缺失，需由 `/jjk-vkplan` 推导并在 `parallel_plan.md` 标注来源 |
| 2. 并行拆解 | `/jjk-vkplan` | `parallel_plan.md` + `workstreams/WS-*.md` + `vk_cards.json` | 有 `WS-00`，每个 WS 含 `card_export`；VK 落卡默认不含 `WS-00` |
| 3. 看板建卡 | `/jjk-vktodo <任务拆解目录> create` | VK 卡片（按 `vk_cards.json`） | create-only 幂等建卡成功 |
| 4. 串行执行收口 | `/jjk-cardrun <任务拆解目录> loop` | 每卡执行证据 + merge 证据 | 当前卡 `verify -> merge -> done` 后才激活下一卡 |
| 5. Gate 一致性 | `python3 scripts/check_workflow_contract.py --mode gate_contract --task-split-dir <任务拆解目录>` | G01 校验结果 | `vk_cards/parallel_plan/implementation_plan` 契约一致 |
| 6. 集成门禁 | `python3 scripts/check_workflow_contract.py --mode integration_gate --task-split-dir <任务拆解目录> --baseline master` | IG01 校验结果 | 实现卡 merge 证据齐全且 `master` 可见 |

---

## 3. 命令选型速查

| 场景 | 推荐命令 | 说明 |
|---|---|---|
| 快速澄清需求 | `/jjk-clarify` | 设计冻结入口（默认收敛），产出 `design_freeze_summary + clarify_handoff_contract` |
| 改动前先过架构门禁 | `/jjk-arch-gate` | 先输出四段式架构结论，确认该走 `plan / imp / refactor` 哪条线 |
| 规划（不拆卡） | `/jjk-plan` 或 `/jjk-plan core` | 只产出需求与技术方案 |
| API / Schema 文档同步 | `/jjk-api-doc-sync` | 命中路由 / schema / DTO / 接口语义变更时，先列必须同步的文档清单 |
| 规划 + 并行拆解（推荐） | `/jjk-plan parallel -> /jjk-vkplan`（或 `/jjk-plan core -> /jjk-vkplan`） | 含 G0 冻结与落卡前产物 |
| 看板落卡（推荐） | `/jjk-vktodo <任务拆解目录> create` | create-only 幂等建卡（不负责状态推进） |
| 串行卡片执行（推荐） | `/jjk-cardrun <任务拆解目录> loop` | 主控按 `card_order` 串行执行并执行每卡 merge 收口 |
| G01 契约一致性 | `python3 scripts/check_workflow_contract.py --mode gate_contract --task-split-dir <任务拆解目录>` | 校验三文档 Gate 契约一致 |
| IG01 集成门禁 | `python3 scripts/check_workflow_contract.py --mode integration_gate --task-split-dir <任务拆解目录> --baseline master` | 校验实现卡合并证据与主干可见性 |
| 执行单个 WS | `/jjk-imp-ws @workstreams/WS-*.md` | 按白名单改动并回填自检卡 |
| 单任务实现 | `/jjk-imp` | 不走并行流程时使用 |
| Worktree 隔离实现 | `/jjk-wtimp` | 大任务隔离分支执行，降低并发污染 |
| 一站式验证 | `/jjk-verify` | 审查 + 测试 + 交互式 UAT，一次完成 |
| 代码审查 | `/jjk-review` | 质量与风险检查 |
| 测试验证 | `/jjk-test` | 回归验证与报告沉淀 |

---

## 4. 并行前 3 秒判断法

满足以下 4 条才建议 `/jjk-vkplan`：

1. 子任务可独立开始并独立交付（无需等待他人产出）
2. 文件白名单互斥（无共享文件并发写）
3. 关键状态字段无语义冲突（单写入权清晰）
4. 子任务可做局部验证（不依赖全量集成）

若任一不满足：

- 回退单任务 `/jjk-imp`
- 或先解耦后再拆分

---

## 5. 上下文注入（@）最小原则

只 @ 当前任务最相关文档，避免上下文污染。

| 场景 | 必须引用 | 可选引用 |
|------|---------|---------|
| 并行规划 | `@docs/内部参考/迭代需求/<topic>_requirements.md` | `@<topic>_implementation_plan.md` |
| 并行拆解 | `@<topic>_implementation_plan.md` | `@<topic>_requirements.md` |
| 执行 WS | `@workstreams/WS-*.md` | `@parallel_plan.md` |
| 修 Bug | `@错误日志` + `@疑似代码` | `@需求文档` |

---

## 6. 常见误区

- “并行 = 随便拆几个 WS”：错误；缺 `task_key/card_export` 会导致看板不可执行。
- “/jjk-plan 一定要出 seed”：错误；只有并行场景才建议 `/jjk-vkplan` 或 `/jjk-plan parallel`。
- “子任务阶段跑全量回归”：错误；并行层做最小验证，全量回归放 Gate 层。
- “Gate 结果手工改”：错误；必须走回填脚本，保证可追溯。

---

## 6.1 `/jjk-vktodo` 最简用法（新增）

1. 推荐执行 `/jjk-plan parallel -> /jjk-vkplan`（或 `/jjk-plan core -> /jjk-vkplan`），产出 `vk_cards.json`。
2. 建卡可直接用路径直传（等价于 `create-only`）：

```text
/jjk-vktodo 2026-02-12_skill检索对齐_cursor_mvp
```

3. 显式写法（推荐）：

```text
/jjk-vktodo 2026-02-12_skill检索对齐_cursor_mvp create
```

4. 若需要指定项目：

```text
/jjk-vktodo task_split_dir=2026-02-12_skill检索对齐_cursor_mvp action=create project=fastapi
```

5. `vktodo` 不再支持 `move/review/done`，状态推进统一交由 `/jjk-cardrun`。

---

## 7. 最终验收要点

1. `parallel_plan.md` 有 `task_key` 与看板导出索引。
2. 每个 `WS-*.md` 文末都有 `card_export`。
3. 卡片 ID 使用 `<task_key>::<WS-ID>`，标题采用 `WS-ID` 前置并保留 `task_key`。
4. `WS-00` 在 master 基线前置完成，不进入 VK 落卡列表。
5. 所有实现卡必须完成 `verify -> merge -> done`，并产出 `merge_result.json`。
6. `G01` 与 `IG01` 必须分别通过，`IG01` 未过不得宣称最终完成。
7. `review/test` 在门禁收口后统一执行。
