# OpenClaw迁移重建基线 实施方案

> 文档状态：`/jjk-plan -p -h` 产物（实现侧）  
> 更新时间：2026-02-25  
> 主题：openclaw迁移重建基线  
> 执行模式：`serial`（单活卡片）

---

## 0. 输入来源清单（hydrate 固定）

本方案仅基于以下输入来源构建：

1. `output/openclaw源码解析/openclaw迁移_输入归一化草案.md`
2. `docs/内部参考/迭代需求/openclaw全量迁移_implementation_plan.md`
3. `docs/内部参考/迭代需求/迁移执行波次_implementation_plan.md`

约束：

1. 不引入新主文档类别。
2. 状态事实以“唯一状态入口”口径执行（波次文档 Gate 看板 + 当前卡记录区）。
3. 编号继承：保留 `C00/C01~C06`、`P1~P6`，不重命名既有编号。

---

## 1. 架构影响与边界

### 1.1 模块边界

1. 协议与编排：`app/ai/workflow/multi_agent_graph.py`、`app/ai/state.py`、`app/ai/events.py`
2. 运行时控制：`app/models/chat_run.py`、`app/services/run_control_service.py`、`app/services/chat_service.py`
3. 配置与治理：`app/services/config_resolver.py`、`app/core/config_contract.py`
4. 管理接口：`app/api/v1/endpoints/chat_api.py`、`app/api/v1/endpoints/skill_admin_api.py`

### 1.2 状态契约

1. run 控制契约：`run_id`、run 状态流转、取消幂等。
2. 协议事件契约：`done/result/interrupt/stopped` 兼容演进。
3. 治理策略契约：`task_mode`、`requires_evidence`、策略分层（settings + DB 覆盖）。
4. 多用户契约：`user_id` 隔离、skill 版本绑定与记忆隔离。

### 1.3 路由闭环

1. `C00` 先决门禁通过后进入 `C01/P1`。
2. `P1 -> P2 -> P3 -> P4 -> P5 -> P6` 为执行主链。
3. `Batch` 仅作跨专题治理视图，不替代 `Wave` 执行链。

---

## 2. hydrate 冲突裁决（source_conflicts）

| 冲突ID | 冲突点 | 裁决口径 |
|---|---|---|
| CF-01 | Batch/Wave/蓝图多路线并存 | 研发执行以 `P1~P6` 为主时序；Batch 仅作治理；蓝图作机制映射。 |
| CF-02 | 协议拓扑 A+C vs B+C | 默认采用 `B(Planner)+C(Evaluate Gate)`；保留 A+C 为最小回退。 |
| CF-03 | 插件接入节奏差异 | 插件归入 `P4.5/P5`，不得阻塞 `P1~P4` 主线。 |
| CF-04 | 进度状态时间切片差异 | 按时间线解释历史状态，禁止把旧状态当当前状态。 |
| CF-05 | 状态权威入口冲突 | 执行状态唯一入口固定为波次文档 Gate 看板与卡记录区。 |
| CF-06 | 队列能力分期口径差异 | P1 可接入 interrupt/steer-backlog，但按 feature flag 分级放开。 |
| CF-07 | 记忆载体文件 vs DB 差异 | 语义层对齐文件模型，存储层使用多用户 DB 隔离承载。 |
| CF-08 | 全版机制 vs 增量推进表面冲突 | 不做阉割版目标；允许按 P1~P6 增量交付并保留全链路闭环字段。 |

证据入口：`openclaw迁移_输入归一化草案.md` 第 C 节（Conflict Table）。

---

## 3. Feature Packet 总览（继承编号）

| feature_id | 归属卡 | 目标摘要 | 主要来源映射 |
|---|---|---|---|
| C00-01 | C00 | 迁移前置门禁与口径统一 | FP-10/FP-11 |
| P1-01 | C01 | run 状态模型与控制面接线 | FP-06 |
| P1-02 | C01 | 取消后的流式回灌阻断与队列 drain | FP-06/FP-02 |
| P1-03 | C01 | cancel API 幂等与路径权威化 | FP-06 |
| P1-04 | C01 | SSE `stopped` 事件兼容演进 | FP-06 |
| P1-05 | C01 | active_run 恢复与 orphan 清理 | FP-06/FP-11 |
| P2-01 | C02 | Tool Registry/Policy/Broker 首期治理 | FP-04 |
| P3-01 | C03 | Skill 版本与用户绑定三层治理 | FP-08 |
| P4-01 | C04 | Hybrid recall + pre-compaction flush | FP-05 |
| P5-01 | C05 | 稳态增强（恢复/隔离/观测）+插件后置接线 | FP-02/FP-03/FP-07 |
| P6-01 | C06 | 全链路收口、Gate 证据闭环与回滚演练 | FP-09/FP-10/FP-11 |

---

## 4. Feature Packet 详情（每项均含机制/锚点/验收/回滚/证据）

### 4.1 C00-01 迁移前置门禁统一

1. 目标与边界：
   - 做：固化四风险修订、取消接口口径统一、文档与 Gate 证据绑定。
   - 不做：业务功能新增与运行时深改。
2. 触发条件与状态流转：`TODO -> IN_PROGRESS -> DONE`；未通过则阻断 `C01`。
3. 代码/文档锚点：
   - `docs/内部参考/迭代需求/openclaw全量迁移_implementation_plan.md`（2.2）
   - `docs/内部参考/迭代需求/迁移执行波次_implementation_plan.md`（2.2~2.4）
4. 关键契约字段：`task_mode`、`requires_evidence`、`cancel API path`、`status_source_of_truth`。
5. 验收命令：
   - `python3 scripts/docs_guard.py --strict`
6. 回滚锚点：文档索引回退、状态镜像回退（不改运行时逻辑）。
7. 证据入口：归一化草案 `CF-01/CF-05/CF-08` + FP-10/FP-11。
8. 最小代码样例：

```python
if not preflight_c00_passed():
    raise RuntimeError("BLOCKED_C00_PRECHECK")
```

### 4.2 P1-01 run 状态模型与控制面

1. 目标与边界：
   - 做：run 状态模型、取消控制服务、`run_id` 贯通。
   - 不做：P2 工具策略治理逻辑。
2. 触发条件与状态流转：创建 run -> 进入执行 -> 可取消 -> 终态。
3. 代码锚点：
   - `app/models/chat_run.py`
   - `app/services/run_control_service.py`
   - `app/schemas/chat.py`
4. 关键契约字段：`run_id`、run status、cancel timestamp。
5. 验收命令：
   - `PYTHONPATH=. pytest tests/unit/test_run_control_service.py`
6. 回滚锚点：`ENABLE_RUN_CONTROL=false`
7. 证据入口：归一化草案 FP-06。
8. 最小代码样例：

```python
run = run_control_service.create_run(session_id, user_id)
assert run.run_id is not None
```

### 4.3 P1-02 取消后的流式阻断与队列 drain

1. 目标与边界：
   - 做：取消后停止 token 回灌、阻断历史流继续发送、队列 drain。
   - 不做：跨波次插件策略。
2. 触发条件与状态流转：收到 cancel -> 标记中断 -> 停止输出 -> drain 结束。
3. 代码锚点：
   - `app/services/chat_service.py`
   - `app/ai/workflow/multi_agent_graph.py`
   - `app/ai/state.py`
4. 关键契约字段：`cancel_after_token_count`、stream state、queue state。
5. 验收命令：
   - `PYTHONPATH=. pytest tests/unit/test_chat_service_cancel_stream.py`
6. 回滚锚点：`ENABLE_RUN_CONTROL=false`
7. 证据入口：归一化草案 FP-06、FP-02。
8. 最小代码样例：

```python
if run_control_service.is_cancelled(run_id):
    return stream_writer.emit_stopped(run_id)
```

### 4.4 P1-03 cancel API 幂等与路径权威化

1. 目标与边界：
   - 做：统一使用 `POST /api/v1/chat/runs/{run_id}/cancel` 并保证幂等。
   - 不做：新增多种取消入口。
2. 触发条件与状态流转：首次取消成功；重复取消返回幂等成功态。
3. 代码锚点：
   - `app/api/v1/endpoints/chat_api.py`
4. 关键契约字段：`run_id`、API 响应状态、幂等标识。
5. 验收命令：
   - `PYTHONPATH=. pytest tests/api/test_chat_api.py -k cancel`
6. 回滚锚点：`ENABLE_RUN_CONTROL=false`
7. 证据入口：归一化草案 FP-06、`C00` 口径统一记录。
8. 最小代码样例：

```python
@router.post("/chat/runs/{run_id}/cancel")
def cancel_run(run_id: str): ...
```

### 4.5 P1-04 SSE stopped 事件兼容演进

1. 目标与边界：
   - 做：新增 `stopped`，并与 `done/result/interrupt` 兼容。
   - 不做：破坏既有前端消费契约。
2. 触发条件与状态流转：cancel 生效后优先发 stopped，再终止后续 token。
3. 代码锚点：
   - `app/services/chat_service.py`
   - `app/ai/events.py`
4. 关键契约字段：event type、version、metadata。
5. 验收命令：
   - `PYTHONPATH=. pytest tests/unit/test_chat_service_resume_after_cancel.py`
6. 回滚锚点：`ENABLE_SSE_STOPPED_EVENT=false`
7. 证据入口：归一化草案 FP-06（事件兼容要求）。
8. 最小代码样例：

```python
stream_writer.write({"type": "stopped", "run_id": run_id, "version": 1})
```

### 4.6 P1-05 active_run 恢复与 orphan 清理

1. 目标与边界：
   - 做：重启后恢复可恢复 run，清理 orphan run/queue。
   - 不做：跨会话插件生命周期重构。
2. 触发条件与状态流转：服务重启 -> 扫描 run/queue -> 恢复或回收。
3. 代码锚点：
   - `app/services/run_control_service.py`
   - `app/services/chat_service.py`
4. 关键契约字段：recovery status、orphan marker、cleanup timestamp。
5. 验收命令：
   - `PYTHONPATH=. pytest tests/unit/test_run_control_service.py -k recover`
6. 回滚锚点：`ENABLE_RUN_CONTROL=false`
7. 证据入口：归一化草案 FP-06、FP-11。
8. 最小代码样例：

```python
for run in run_repo.list_orphan_runs():
    run_control_service.cleanup_orphan(run.run_id)
```

### 4.7 P2-01 Tool Registry/Policy/Broker 首期治理

1. 目标与边界：
   - 做：工具注册、策略解析、broker 接线、证据门禁按任务类型启用。
   - 不做：插件全面平台化（后置到 P4.5/P5）。
2. 触发条件与状态流转：请求进入 -> 策略决策 -> 工具执行/拒绝 -> 证据输出。
3. 代码锚点：
   - `app/ai/workflow/multi_agent_graph.py`
   - `app/services/config_resolver.py`
   - `app/core/config_contract.py`
4. 关键契约字段：`task_mode`、`requires_evidence`、policy decision、tool audit。
5. 验收命令：
   - `PYTHONPATH=. pytest tests/unit/test_multi_agent_streaming_helpers.py`
6. 回滚锚点：
   - `ENABLE_TOOL_GOVERNANCE=false`
   - `TOOL_POLICY_FAIL_MODE=compat`
7. 证据入口：归一化草案 FP-04 + Conflict `CF-03`。
8. 最小代码样例：

```python
decision = tool_policy_pipeline.evaluate(task_mode, tool_name)
if not decision.allowed:
    return policy_block_response(decision.reason)
```

### 4.8 P3-01 Skill 三层治理（定义/版本/用户绑定）

1. 目标与边界：
   - 做：Skill 定义层、版本层、用户绑定层解耦并支持回滚。
   - 不做：跨租户共享写入。
2. 触发条件与状态流转：发布新版本 -> 绑定用户 -> 生效 -> 回滚。
3. 代码锚点：
   - `app/models/agent_skill.py`
   - `app/services/skill_service.py`
   - `app/api/v1/endpoints/skill_admin_api.py`
4. 关键契约字段：`user_id`、`skill_id`、`version`、binding status。
5. 验收命令：
   - `PYTHONPATH=. pytest app/tests/test_handoff_detection.py`
6. 回滚锚点：
   - `ENABLE_SKILL_VERSIONING=false`
   - `ENABLE_USER_SKILL_BINDING=false`
7. 证据入口：归一化草案 FP-08。
8. 最小代码样例：

```python
skill_service.bind_user_skill(user_id, skill_id, version)
```

### 4.9 P4-01 Hybrid recall + pre-compaction flush

1. 目标与边界：
   - 做：记忆检索增强、压缩前 flush、降级可控、用户隔离。
   - 不做：将记忆系统与会话主链硬耦合。
2. 触发条件与状态流转：会话进入 -> recall -> 对话推进 -> compaction 前 flush。
3. 代码锚点：
   - `app/services/user_preference_memory_service.py`
   - `app/services/chat_service.py`
4. 关键契约字段：`user_id`、memory layer、flush trigger、recall source。
5. 验收命令：
   - `PYTHONPATH=. pytest tests/unit/test_multi_intent_queue_flow.py`
6. 回滚锚点：
   - `ENABLE_MEMORY_RECALL=false`
   - `ENABLE_PRE_COMPACTION_FLUSH=false`
7. 证据入口：归一化草案 FP-05 + Conflict `CF-07`。
8. 最小代码样例：

```python
if should_flush_before_compaction(ctx):
    memory_service.flush(session_id, user_id)
```

### 4.10 P5-01 稳态增强与插件后置接线

1. 目标与边界：
   - 做：恢复/隔离/观测增强，插件能力后置接线，fallback 与队列/子任务稳定化。
   - 不做：在主链未稳时强行并发扩容。
2. 触发条件与状态流转：异常/重启/降级场景触发 -> 选择恢复或降级路径。
3. 代码锚点：
   - `app/ai/workflow/multi_agent_graph.py`
   - `app/ai/state.py`
   - `app/services/chat_service.py`
4. 关键契约字段：recovery metrics、fallback route、plugin lifecycle status。
5. 验收命令：
   - `PYTHONPATH=. pytest tests/unit/test_multi_agent_streaming_helpers.py -k fallback`
6. 回滚锚点：灰度开关矩阵（治理/插件/恢复能力分别可关）。
7. 证据入口：归一化草案 FP-02/FP-03/FP-07 + Conflict `CF-03/CF-06`。
8. 最小代码样例：

```python
if plugin_registry_unhealthy():
    return run_core_tools_only()
```

### 4.11 P6-01 全链路收口与回滚演练

1. 目标与边界：
   - 做：G-1~G-4 收口、发布前回滚演练、证据链闭环。
   - 不做：绕过 Gate 直接宣称“已吃透”。
2. 触发条件与状态流转：前置卡完成 -> Gate 逐项验收 -> 发布清单冻结。
3. 代码/文档锚点：
   - `docs/内部参考/迭代需求/迁移执行波次_implementation_plan.md`（11.2~11.5）
   - `scripts/docs_guard.py`
4. 关键契约字段：Gate 状态、evidence 四元组、回滚演练记录。
5. 验收命令：
   - `python3 scripts/docs_guard.py --strict`
6. 回滚锚点：`WAVE_ROLLBACK_DRILL_MATRIX`（`迁移执行波次_implementation_plan.md` 第 11.6 节）。
7. 证据入口：归一化草案 FP-09/FP-10/FP-11 + Conflict `CF-05/CF-08` + `迁移执行波次_implementation_plan.md` 第 8.3/11.5/11.6 节。
8. 最小代码样例：

```python
assert gates["G-1"] and gates["G-2"] and gates["G-3"] and gates["G-4"]
```

9. 执行留痕（2026-02-25）：
   - G-1~G-4 全部通过并完成证据链复核。
   - docs/code/test 三线收口完成（`scripts/docs_guard.py` 严格门禁通过）。
   - 各 Wave 回滚锚点组合演练通过并写入 `WAVE_ROLLBACK_DRILL_MATRIX`。

---

## 5. hydrate 覆盖率（强制输出）

### 5.1 覆盖率统计（机读）

```yaml
source_atoms_total: 1270
source_atoms_mapped: 1270
source_atoms_unmapped: []
source_conflicts:
  - CF-01
  - CF-02
  - CF-03
  - CF-04
  - CF-05
  - CF-06
  - CF-07
  - CF-08
```

### 5.2 覆盖率判定

1. 当前判定：`READY_FOR_VKPLAN`（`source_atoms_unmapped` 为空）。
2. 强制规则：若 `source_atoms_unmapped` 非空，计划状态必须改为 `BLOCKED`，并停止进入 `/jjk-vkplan`。

---

## 6. 依赖关系（卡片级）

1. `C00` 为前置卡，必须 `DONE` 才允许 `C01`。
2. `C01 -> C02 -> C03 -> C04`
3. `C05` 依赖 `C02` 与 `C04`
4. `C06` 依赖 `C01~C05`
5. `G01 -> G02` 为 Gate 复核链，仅用于核验 `hard_depends_on` 与 `single_active_card` 约束，不改变 `C01~C06` 的串行主链。

---

## 7. planning_contract（供 `/jjk-vkplan` 直接消费）

```yaml
planning_contract:
  execution_mode: serial
  strict_single_active_card: true
  auto_done_policy:
    implementation-card: hard_gate
    inspection/question-card: policy_gate
  status_source_of_truth: docs/内部参考/迭代需求/迁移执行波次_implementation_plan.md
  preflight:
    - card_id: C00
      feature_ids: [C00-01]
      done_gate:
        - 四风险修订口径固化完成（evidence/task_mode、scene fallback、插件后置、引用锚点）
        - 取消接口统一为 POST /api/v1/chat/runs/{run_id}/cancel
        - python3 scripts/docs_guard.py --strict 通过
  card_order: [C01, C02, C03, C04, C05, C06]
  inspection_chain:
    - card_id: G02
      feature_ids: [G-2]
      hard_depends_on: [G01]
      excluded_from_card_order: true
      task_mode: inspection-card
      merge_required: false
      acceptance_checks:
        - python3 scripts/docs_guard.py --strict
      evidence_entry: docs/内部参考/迭代需求/openclaw迁移重建基线_implementation_plan.md#7
  cards:
    - card_id: C01
      wave: P1
      feature_ids: [P1-01, P1-02, P1-03, P1-04, P1-05]
      depends_on: []
      done_gate:
        - P1-01~P1-05 验收命令通过
        - cancel_after_token_count=0
        - ENABLE_RUN_CONTROL/ENABLE_SSE_STOPPED_EVENT 回滚验证通过
    - card_id: C02
      wave: P2
      feature_ids: [P2-01]
      depends_on: [C01]
      done_gate:
        - Tool Registry/Policy/Broker 接线通过
        - ENABLE_TOOL_GOVERNANCE 与 TOOL_POLICY_FAIL_MODE 回滚验证通过
    - card_id: C03
      wave: P3
      feature_ids: [P3-01]
      depends_on: [C02]
      done_gate:
        - Skill 版本发布/回滚/用户绑定回归通过
        - ENABLE_SKILL_VERSIONING 与 ENABLE_USER_SKILL_BINDING 回滚验证通过
    - card_id: C04
      wave: P4
      feature_ids: [P4-01]
      depends_on: [C03]
      done_gate:
        - recall/flush 链路回归通过
        - 记忆异常不阻断主对话
    - card_id: C05
      wave: P5
      feature_ids: [P5-01]
      depends_on: [C02, C04]
      done_gate:
        - 恢复任务、观测阈值、降级策略验收通过
        - 插件后置接线不阻塞主链
    - card_id: C06
      wave: P6
      feature_ids: [P6-01]
      depends_on: [C01, C02, C03, C04, C05]
      done_gate:
        - G-1~G-4 全部通过
        - docs/code/test 三线收口完成
        - 各 Wave 回滚锚点组合演练通过
```
