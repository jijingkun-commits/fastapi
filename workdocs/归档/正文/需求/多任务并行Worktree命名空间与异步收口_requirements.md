# 多任务并行 Worktree 命名空间与异步收口需求基线

> 文档日期：2026-03-03
> 文档定位：定义“多任务并行开发”与“用户响应链路异步收口”的统一需求边界
> 上游设计输入：`workdocs/归档/正文/设计/2026-03-03-parallel-task-worktree-namespace-design.md`

---

## 1. 背景与问题定义

当前系统存在两类耦合问题，已经开始互相放大：

1. **并行任务资源冲突**：多个 `task_key` 并行开发时，`feature/C01`、`.worktrees/C01`、`.artifacts/states/task_splits/<task_split_dir>/<task_key>/task-runner-state.json`、`.artifacts/states/task_splits/<task_split_dir>/<task_key>/task-runner-state.json::gate_results/merge_results/C01/*` 等资源存在复用覆盖风险。
2. **用户响应链路被收口逻辑拖慢**：在聊天主链路中存在同步写入/召回操作，容易把“后台治理动作”叠加到用户可感知时延。
3. **读写口径不一致**：即使写入端隔离，读侧脚本仍可能读取全局默认路径，导致 active 索引与运行状态漂移。

本需求目标是：**在不破坏 `jjk-*` 既有串行闭环的前提下，实现任务级并行隔离与用户无感异步收口**。

---

## 2. 目标、范围与边界

### 2.1 目标（Goal）

1. 不同 `task_key` 的同名卡片（如 `C01`）可并行推进，且分支/worktree/状态/证据互不覆盖。
2. 聊天主链路中的“非回答必要动作”异步化，避免延长用户等待。
3. 建立统一状态契约，确保 active 索引、任务状态、Gate 证据一致可追溯。
4. 保持 `jjk-cardrun` 的 `verify -> merge -> done` 串行闭环语义不变。

### 2.2 范围（In Scope）

1. `scripts/coder4/wt-flow.sh` 的命名空间隔离改造（分支、worktree、state、attempts）。
2. `scripts/coder4/coder4_bootstrap_kernel.py`、`scripts/coder4/coder4_vk_sync.py`、`scripts/coder4/check_integration_gate.py` 的读侧路径统一。
3. `scripts/coder4/coder4_scope_guard.py` 的 active 判定一致性修正。
4. `app/services/chat_service.py` 的主链路异步收口改造（把后台动作从用户响应关键路径拆出）。
5. 配套文档与流程命令更新：`jjk-cardrun`、`jjk-vkplan`、工作流文档。

### 2.3 非范围（Out of Scope）

1. 不重构 LangGraph 主业务语义与节点职责。
2. 不改 Vibe Kanban API 协议，不新增外部任务调度中间件（如 Celery/Kafka）作为首期硬依赖。
3. 不引入多卡并发执行（卡片级仍保持串行）。
4. 不做跨仓库分布式锁改造。

---

## 3. 用户故事（User Stories）

### US-01（终端用户）
作为最终用户，我希望系统优先返回回答内容，后台同步/归档不应让我等待更久。

### US-02（开发者）
作为开发者，我希望两个任务都可以有 `C01`，并在不同 worktree 同时推进，而不会互相覆盖状态。

### US-03（自动执行维护者）
作为自动执行维护者，我希望 active 索引与任务状态始终一致，切换任务后不会读到旧任务状态。

### US-04（交付负责人）
作为交付负责人，我希望 Gate 与集成检查读取的证据路径稳定，避免“看起来通过、实际上读错任务”的误判。

---

## 4. 方案对比与选型

| 方案 | 优点 | 缺点 | 成本 | 推荐度 |
|---|---|---|---|---|
| A. 仅流程规范（人工切 active） | 无代码改动，交付快 | 不能根治命名空间与读写漂移，易复发 | 低 | ⭐⭐ |
| B. 仅改 `wt-flow.sh` 写路径 | 能解决部分冲突，改动集中 | 读侧仍可能读全局文件，出现隐性错位 | 中 | ⭐⭐⭐ |
| C. 全链路隔离 + 响应异步化 | 根因闭环，既解决并行冲突又保证用户时延 | 改动面较大，需要回归测试 | 中高 | ⭐⭐⭐⭐⭐ |

结论：采用 **方案 C**。

---

## 5. 功能需求（Functional Requirements）

### 5.1 并行隔离需求

1. `FR-01` 分支命名空间：支持 `feature/<task_key>/<card_id>`，兼容 legacy `feature/<card_id>`。
2. `FR-02` Worktree 命名空间：支持 `.worktrees/<task_key>/<card_id>`，兼容 legacy `.worktrees/<card_id>`。
3. `FR-03` 会话状态隔离：`wt-flow` 会话状态按 `task_key` 隔离，不允许不同任务覆盖。
4. `FR-04` 卡片状态隔离：`task-runner-state.json` 按 `task_key` 隔离，读写口径统一。
5. `FR-05` 证据目录隔离：`gate_result.json/merge_result.json` 按 `task_key` + `card_id` 双维度隔离。

### 5.2 异步收口需求

1. `FR-06` 主回答优先：聊天主链路先返回用户可见内容，再执行非关键收口动作。
2. `FR-07` 后台任务异步化：记忆 flush/状态同步/Gate 归档等由异步队列或后台任务执行。
3. `FR-08` 异步任务幂等：每个异步任务必须具备 idempotency key，支持重复投递去重。
4. `FR-09` 异步失败可恢复：失败任务记录结构化错误并支持重试，不影响本次用户回答。

### 5.3 状态一致性需求

1. `FR-10` active 与 state 一致性检查：`task_key` 与 `card_order` 必须可机读对齐。
2. `FR-11` scope_guard 判定增强：already_active 判定必须包含 `task_key` 维度。
3. `FR-12` 集成检查统一路径：Integration Gate 仅从当前 task_key 作用域读取状态与证据。

### 5.4 文档与流程需求

1. `FR-13` 更新 `jjk-*` 文档命名口径，避免旧示例误导执行。
2. `FR-14` 新增回归测试与验收命令，覆盖“任务切换 + 并行同名卡 + 异步失败恢复”。
3. `FR-15` 保留 plan-only 原则：本轮仅输出规划，不自动进入实施链。

---

## 6. 验收标准（Acceptance Criteria）

### 6.1 Happy Path

1. `AC-01` 任务 A/B 均存在 `C01` 时，可各自创建分支与 worktree，互不冲突。
2. `AC-02` 切换 active 任务后，`next/verify/merge/list` 命中当前任务状态，不读错旧任务。
3. `AC-03` 用户聊天请求首包/完成时延无明显回归（后台收口已异步化）。
4. `AC-04` 异步任务失败时，用户仍能收到完整回答，失败记录进入可追踪日志。
5. `AC-05` Gate 与 Integration 检查能读取到当前任务对应证据文件并判定正确。

### 6.2 异常与边界

1. `AC-06` legacy 分支/legacy worktree 仍可继续收口，不强制一次性迁移。
2. `AC-07` active 索引缺失或损坏时，执行链路给出明确阻断码并拒绝继续推进。
3. `AC-08` 异步任务重复投递不会产生重复写入或状态污染。
4. `AC-09` 单任务模式下行为与现状兼容，不引入额外复杂操作。

### 6.3 性能与稳定性

1. `AC-10` 主链路同步阶段不再执行重型后台动作，关键路径可观测时延下降或持平。
2. `AC-11` 异步任务处理具备重试和退避策略，失败不阻断主流程。
3. `AC-12` 并行任务切换 50 次后，状态文件与证据路径一致性无漂移。

---

## 7. 非功能需求（NFR）

1. **性能**：用户响应关键路径与后台收口解耦，避免尾延迟放大。
2. **可靠性**：异步任务可重试、可去重、可追踪。
3. **一致性**：active 索引、state、attempts 三层必须同 task_key 对齐。
4. **可维护性**：命名规则和路径规则统一，避免脚本与文档双轨口径。
5. **可回滚性**：保持 legacy 兼容路径，支持分阶段迁移。

---

## 8. 场景约束（平台/架构任务）

1. 保持 `jjk-cardrun` 串行卡语义，不引入多卡抢占。
2. 主链路“回答输出”优先级高于后台收口动作。
3. 后台任务失败只影响可观测告警，不可反向阻断用户回答。
4. 所有新增异步行为必须有审计或日志证据。

---

## 9. 关联测试矩阵（Traceability）

| 用例 ID | 对应需求 | 场景 |
|---|---|---|
| TC-WT-01 | FR-01/FR-02 | A/B 任务同名 `C01` 并行创建 |
| TC-WT-02 | FR-03/FR-04 | 任务切换后状态隔离与恢复 |
| TC-WT-03 | FR-05/FR-12 | Gate/merge 证据按 task_key 读取 |
| TC-WT-04 | FR-10/FR-11 | active/state/scope_guard 一致性 |
| TC-ASYNC-01 | FR-06 | 用户响应主链路不被后台动作拖慢 |
| TC-ASYNC-02 | FR-07/FR-08 | 异步任务投递与幂等去重 |
| TC-ASYNC-03 | FR-09 | 异步失败重试与降级 |
| TC-DOC-01 | FR-13/FR-14 | 文档口径与验收命令一致性 |

---

## 10. 发布完成定义（DoD）

1. `FR-01` ~ `FR-12` 全部实现并通过对应测试。
2. 主链路时延对比报告可见（改造前/后）。
3. 文档索引更新完成且 `docs_guard --strict` 通过。
4. 迁移策略验证通过（legacy + namespace 混合场景）。
5. 形成可执行实施计划并具备 `planning_contract` 与 `execution_contract`。
