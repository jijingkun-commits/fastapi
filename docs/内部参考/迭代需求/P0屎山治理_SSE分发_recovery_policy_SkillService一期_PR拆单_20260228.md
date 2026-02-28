# P0屎山治理：统一SSE事件分发、抽离recovery_policy、拆SkillService第一阶段（PR拆单执行稿）

> 文档日期：2026-02-28  
> 目标：把大任务拆成可独立评审/回滚/合并的 PR 单元，避免“一个大分支改到底”的隐性耦合。  
> 适用分支策略：`codex/*`（与仓库约定一致）。  
> 当前现场：`app/services/chat_service.py` 与 `app/ai/workflow/multi_agent_graph.py` 已存在未提交修改，以下拆单默认继承该现状，不覆盖他人改动。

---

## 1. Team 判定快照（用于执行模式选择）

| 指标 | 取值 | 说明 |
|---|---:|---|
| module_count | 4 | `app/services`、`app/ai/workflow`、`app/ai/runtime`、`web/src/lib` |
| boundary_count | 3 | 后端服务层 / AI 工作流层 / 前端 SSE 消费层 |
| uncertainty_count | 2 | SSE 契约归并边界、SkillService 一期拆分边界 |
| estimated_file_count | 10+ | 至少覆盖 8 个核心代码文件 + 测试文件 |

结论：命中条件 >= 2，按 Team 模式推进（Leader 单线程口径，Worker 并行收集证据）。

---

## 2. 拆单原则（强制）

1. 一张 PR 只解决一个“可验收问题”，禁止混入无关重构。  
2. 每张 PR 必须附带可执行回归命令与回滚点。  
3. 合并顺序必须遵守依赖：`PR-01 -> PR-02 -> PR-03`。  
4. SkillService 拆分一期仅做“结构抽离 + 行为保持”，不叠加新业务能力。

---

## 3. Task -> PR 映射总表

| PR | 分支名 | task_id | 目标 | 主要文件 | 验收标准 | 依赖 |
|---|---|---|---|---|---|---|
| PR-01 | `codex/p0-recovery-policy-extract` | T01 | `recovery_policy` 成为唯一策略入口，去除重复开关/错误判定 | `app/ai/runtime/recovery_policy.py`<br>`app/services/chat_service.py`<br>`app/ai/workflow/multi_agent_graph.py`<br>`tests/unit/test_recovery_policy.py` | `chat_service` 与 `multi_agent_graph` 不再维护重复策略常量；插件降级路径行为不变 | 无 |
| PR-02 | `codex/p0-sse-dispatch-unify` | T02 | 统一 SSE 事件分发与解析链路，消除 stream/resume 及多入口重复分发逻辑 | `app/services/chat_service.py`<br>`app/ai/events.py`<br>`web/src/lib/backend.ts`<br>`web/src/lib/admin-overview-api.ts`<br>`web/e2e/todo-sse-protocol.spec.cjs` | 同一事件契约在 stream/resume/admin-overview 三条链路一致；`done` 事件不重复触发 | PR-01 |
| PR-03 | `codex/p0-skillservice-split-phase1` | T03 | 拆 `SkillService` 一期：抽离纯函数与检索辅助模块，保留现有对外接口 | `app/services/skill_service.py`<br>`app/services/skill_manifest_parser.py`（新增）<br>`app/services/skill_query_utils.py`（新增）<br>`app/tests/test_skill_retrieval_smoke.py` | `SkillService.search_skills*` 行为与排序口径保持一致；类体体积下降且职责边界清晰 | PR-02 |

---

## 4. 每个 PR 的回归命令与回滚点

### PR-01（recovery_policy 抽离）

- 回归命令：
  - `python -m pytest tests/unit/test_recovery_policy.py -q`
  - `python -m pytest app/tests/test_model_switch.py -k "stream or resume" -q`
- 回滚点：
  - 若插件降级路径异常，先回滚 `app/services/chat_service.py` 的策略接线，再回滚 `multi_agent_graph` 接线。

### PR-02（SSE 分发统一）

- 回归命令：
  - `python -m pytest app/tests/test_model_switch.py -q`
  - `pnpm --dir web lint`
  - `pnpm --dir web playwright test web/e2e/todo-sse-protocol.spec.cjs`
- 回滚点：
  - 若前端实时流出现事件丢失/重复 done，先回滚前端分发器改动，再回滚后端事件适配层。

### PR-03（SkillService 一期拆分）

- 回归命令：
  - `python -m pytest app/tests/test_skill_retrieval_smoke.py -q`
  - `python -m pytest tests/verify_skill_fix.py -q`
- 回滚点：
  - 若检索排序漂移，保留新增辅助模块文件，先将 `skill_service.py` 调用回切到原路径（不删新文件，便于二次修复）。

---

## 5. OMX 执行口令（tmux 内）

```bash
tmux new -s fastapi-refactor
cd /Users/jijingkun/bojxAI/fastapi
omx team 3:executor "执行P0屎山治理：按 docs/内部参考/迭代需求/P0屎山治理_SSE分发_recovery_policy_SkillService一期_PR拆单_20260228.md 的 PR-01~PR-03 顺序推进；每个PR按 task_id 粒度回填 文件列表、验收命令与回滚点。"
```

---

## 6. 交付检查清单（Leader 视角）

- [ ] 每张 PR 只覆盖一个 task_id（T01/T02/T03）。  
- [ ] PR 描述包含：改动文件、验收命令、回滚点、依赖 PR。  
- [ ] PR-02 必须在 PR-01 合并后再开。  
- [ ] PR-03 只做一期拆分，不引入业务语义改动。  
- [ ] 全部 PR 合并后补一份汇总回归记录（SSE + Skill 检索）。

