# 全面代码审查整改 — 实施方案

> 日期: 2026-02-26  
> 需求基线: `docs/内部参考/迭代需求/全面代码审查整改_requirements.md`  
> 输入报告: `output/全面代码审查报告_合并版_20260225.md`（问题 #1-#68）  
> 代码复测参考: `HEAD a51cb83`（静态复测）

---

## 0. 输入来源清单

1. `output/全面代码审查报告_合并版_20260225.md`（单一入口，含基线+增补）。
2. 当前代码静态复测证据（`app/**`, `web/**` 关键链路）。
3. 既有开发流程约束：单卡滚动、串行执行、Gate 门禁。

> 说明：本计划以“风险优先 + 架构收敛 + 工程补齐”三阶段执行，不新增第四类主文档。

---

## 1. 架构影响与约束

### 1.1 模块边界

1. 安全策略统一在后端入口层 + AI 执行链路收敛，不允许同类校验散落在 endpoint/tool/graph 多层重复实现。
2. 权限控制必须在“资源查询入口”强制执行，不接受仅依赖上层路由登录态。
3. Repo 层只负责数据访问，不再反向依赖 Service。

### 1.2 状态契约

1. 聊天链路关键字段（`thread_id/run_id/user_id/current_todo_id`）作为 canonical 字段，不允许别名漂移。
2. `resume/cancel/done/stopped` 的状态转移必须由 `run_control_service` 单点裁决。
3. 分页、反馈、资产等接口统一参数契约（`limit` 上下限、归属校验、错误码语义）。

### 1.3 路由闭环

1. `analyze -> safety -> execute` 链路必须保留，禁止绕过 `sql_safety_check` 直达执行。
2. `interrupt -> resume` 必须绑定 run/thread 归属校验，防止“已登录但越权”。

### 1.4 端到端链路

1. 前端确认操作类型必须与后端 `decision` 协议一致。
2. SSE 异常收尾必须触发线程刷新，避免“消息到了但列表未更新”。

### 1.5 可测试性

1. 每个功能机制包必须有最小回归命令。
2. P0/P1 机制必须具备“攻击样例回归用例”。
3. 集成测试必须覆盖银行场景（分行/机构权限）与合规边界（越权拒绝）。

---

## 2. 功能机制包总表（Feature Packet）

| feature_id | 目标 | 覆盖问题编号 |
|---|---|---|
| FP-SEC-01 | Python 执行沙箱化 | #1 |
| FP-SEC-02 | SQL 安全链统一（含 LIMIT） | #2 #11 #36 #68 |
| FP-SEC-03 | RLS/权限重写安全化 | #3 |
| FP-SEC-04 | 认证与密钥基线收敛 | #4 #6 #12 #13 #37 #67 |
| FP-SEC-05 | 访问控制与归属校验闭环 | #7 #15 #60 #61 #62 #63 |
| FP-SEC-06 | 资产代理稳定性与错误语义 | #47 #64 #65 |
| FP-SEC-07 | 健康检查与配置暴露收敛 | #34 #39 #66 |
| FP-SEC-08 | API Key 传输与开发工具约束 | #5 #14 |
| FP-OPS-01 | CORS 与护栏 fail-close 策略 | #10 #49 |
| FP-ARC-01 | Graph 体量与状态收敛 | #16 #23 #59 |
| FP-ARC-02 | Service/Controller/Repo 职责解耦 | #17 #18 #19 #20 #40 #41 #42 #45 #46 #56 #57 |
| FP-ARC-03 | 运行态一致性与异步可靠性 | #21 #22 #38 #43 #58 |
| FP-BE-01 | 后端模型/Schema/异常治理 | #8 #24 #29 #30 #31 #32 #33 #44 #48 #50 #51 |
| FP-FE-01 | 前端类型与交互一致性 | #9 #26 #27 #28 #35 #52 #53 #54 #55 |
| FP-QA-01 | 集成测试与追溯矩阵补齐 | #25 |

覆盖校验：`issue_ids 1..68` 全量映射，`mapped=68, unmapped=0`。

---

## 3. 功能机制包明细

### FP-SEC-01: Python 执行沙箱化

- 目标与边界: 替换裸 `eval/exec`，保留必要数据分析能力；不在本轮做完整远程执行平台。
- 触发条件与状态流转: tool 调用进入 `python_inter/fig_inter` 时先走 AST/沙箱策略再执行。
- 代码锚点: `app/ai/tools/chatTools.py`（`python_inter`, `fig_inter`）。
- 关键契约字段: `thread_id`, `user_id`, `py_code`, `execution_result`。
- 回滚锚点: `FEATURE_SANDBOX_PYTOOLS` 开关（默认开，失败可降级到只读解释器）。
- 验证命令: `pytest tests/unit -k "python_inter or fig_inter" -q`。
- 来源证据: 报告 #1。

```python
# 最小实现示意
from asteval import Interpreter
aeval = Interpreter()
if contains_dangerous_nodes(py_code):
    raise ValueError("dangerous code")
result = aeval(py_code)
```

### FP-SEC-02: SQL 安全链统一（含 LIMIT）

- 目标与边界: 所有 SQL 执行入口统一 `check_sql_safety + permission_rewrite + limit`；不改业务语义。
- 触发条件与状态流转: `generated_sql -> safety -> execute`，任何拒绝均走澄清分支。
- 代码锚点: `app/ai/workflow/data_graph.py`, `app/ai/utils/sql_safety.py`, `app/ai/semantic/vanna_client.py`, `app/ai/tools/chatTools.py`。
- 关键契约字段: `generated_sql`, `pending_sql`, `query_context.permission_rewritten`。
- 回滚锚点: `SQL_POLICY_STRICT_MODE`（紧急时允许只读降级但保留审计）。
- 验证命令: `pytest tests/unit -k "sql_safety or sql_parser or sql_rewriter" -q`。
- 来源证据: 报告 #2 #11 #36 #68。

```python
safe_sql, ok, err = sanitize_sql(raw_sql, auto_limit=True, limit=1000)
if not ok:
    return deny(err)
rewritten_sql, allowed, reason = check_and_rewrite_sql(safe_sql, user_id)
```

### FP-SEC-03: RLS/权限重写安全化

- 目标与边界: 移除字符串拼接注入点，RLS 统一参数化/AST 重写。
- 触发条件与状态流转: `evaluate_sql_policy` 中权限重写阶段触发。
- 代码锚点: `app/ai/semantic/data_access_control.py`, `app/ai/utils/sql_rewriter.py`。
- 关键契约字段: `user_context`, `row_filters`, `permission_scope_summary`。
- 回滚锚点: `RLS_REWRITE_ENGINE=v2`（支持回退 v1）。
- 验证命令: `pytest tests/unit -k "permission or rls or rewrite" -q`。
- 来源证据: 报告 #3。

```python
stmt = text("... WHERE user_id = :uid")
conn.execute(stmt, {"uid": user_id})
```

### FP-SEC-04: 认证与密钥基线收敛

- 目标与边界: JWT 强密钥、启动 fail-fast、登录风控、开发态认证策略显式化。
- 触发条件与状态流转: 应用启动阶段 + 登录链路 + 初始化脚本。
- 代码锚点: `app/core/config.py`, `app/core/settings.py`, `app/api/v1/endpoints/auth.py`, `app/services/user_service.py`, `app/db/init_db.py`, `app/services/token_service.py`。
- 关键契约字段: `JWT_SECRET`, `ENV`, `login_attempt_counter`, `expires_at(UTC)`。
- 回滚锚点: `AUTH_STRICT_MODE`、`RATE_LIMIT_MODE`。
- 验证命令: `pytest tests/unit -k "auth or token" -q`。
- 来源证据: 报告 #4 #6 #12 #13 #37 #67。

```python
if ENV == "prod" and len(JWT_SECRET) < 32:
    raise RuntimeError("weak jwt secret")
```

### FP-SEC-05: 访问控制与归属校验闭环

- 目标与边界: `users/messages/feedback/resume/assets/ragflow` 全链路资源归属校验。
- 触发条件与状态流转: endpoint 入参后先校验归属，再进入业务处理。
- 代码锚点: `app/api/v1/endpoints/user.py`, `app/api/v1/endpoints/chat_api.py`, `app/repositories/chat_repo.py`, `app/services/chat_service.py`, `app/services/run_control_service.py`, `app/api/v1/endpoints/assets_api.py`。
- 关键契约字段: `current_user.id`, `thread.user_id`, `message.user_id`, `run_snapshot.user_id`。
- 回滚锚点: `STRICT_RESOURCE_OWNERSHIP=true`（只允许向更严格方向切换）。
- 验证命令: `pytest tests/integration -k "idor or ownership or resume" -q`。
- 来源证据: 报告 #7 #15 #60 #61 #62 #63。

```python
msg = get_message(message_id)
if msg.user_id != current_user.id:
    raise HTTPException(status_code=403, detail="forbidden")
```

### FP-SEC-06: 资产代理稳定性与错误语义

- 目标与边界: 修复流式生命周期、异常吞码、废弃 API 使用。
- 触发条件与状态流转: 代理请求时保留上游连接到响应结束。
- 代码锚点: `app/api/v1/endpoints/assets_api.py`。
- 关键契约字段: `upstream_status`, `stream_closed`, `http_error_passthrough`。
- 回滚锚点: `ASSET_PROXY_STREAM_V2`。
- 验证命令: `pytest tests/integration -k "assets or ragflow" -q`。
- 来源证据: 报告 #47 #64 #65。

```python
try:
    ...
except HTTPException:
    raise
except Exception:
    raise HTTPException(status_code=500, detail="internal error")
```

### FP-SEC-07: 健康检查与配置暴露收敛

- 目标与边界: 健康检查最小暴露、错误文本脱敏、状态码语义正确。
- 触发条件与状态流转: 健康探针失败返回 503 + 通用信息。
- 代码锚点: `app/api/v1/endpoints/health.py`, `app/core/config.py`。
- 关键契约字段: `status`, `http_status`, `public_error_code`。
- 回滚锚点: `HEALTH_PUBLIC_MODE`。
- 验证命令: `pytest tests/integration -k "health" -q`。
- 来源证据: 报告 #34 #39 #66。

```python
if not result.healthy:
    raise HTTPException(status_code=503, detail="dependency unavailable")
```

### FP-SEC-08: API Key 传输与开发工具约束

- 目标与边界: 禁止 query 传敏感值，限制开发工具高危沙箱。
- 触发条件与状态流转: API Key 更新改为 body/header；dev_codex 接口禁止 `danger-full-access`。
- 代码锚点: `app/api/v1/endpoints/llm_admin_api.py`, `app/api/v1/endpoints/dev_codex_api.py`。
- 关键契约字段: `api_key`, `sandbox_mode`。
- 回滚锚点: `DEV_CODEX_ALLOW_DANGER=false`。
- 验证命令: `pytest tests/unit -k "llm_admin or dev_codex" -q`。
- 来源证据: 报告 #5 #14。

```python
class ApiKeyPayload(BaseModel):
    api_key: str
```

### FP-OPS-01: CORS 与护栏 fail-close 策略

- 目标与边界: 禁止生产回退 `*`，护栏异常默认拒绝并告警。
- 触发条件与状态流转: middleware 初始化与 guardrail 执行异常路径。
- 代码锚点: `app/core/middleware.py`, `app/ai/guardrails.py`。
- 关键契约字段: `allow_origins`, `guardrail_decision`。
- 回滚锚点: `GUARDRAIL_FAIL_MODE=close`。
- 验证命令: `pytest tests/unit -k "guardrail or cors" -q`。
- 来源证据: 报告 #10 #49。

```python
if ENV == "prod" and not origins:
    raise RuntimeError("CORS origins required in prod")
```

### FP-ARC-01: Graph 体量与状态收敛

- 目标与边界: 按职责拆分 graph 大文件，清理膨胀状态字段与失效引用。
- 触发条件与状态流转: 先拆公用节点，再替换主 graph 引用，最后删除僵尸路径。
- 代码锚点: `app/ai/workflow/data_graph.py`, `app/ai/workflow/multi_agent_graph.py`, `app/ai/workflow/todo_graph.py`, `app/ai/state.py`。
- 关键契约字段: `BaseAgentState`, `TodoAgentState`, `MultiAgentState`。
- 回滚锚点: `GRAPH_SPLIT_PHASE`（phase1/phase2）。
- 验证命令: `pytest tests/unit -k "graph or state" -q`。
- 来源证据: 报告 #16 #23 #59。

```python
class BaseAgentState(TypedDict):
    messages: list
    user_id: int
```

### FP-ARC-02: Service/Controller/Repo 职责解耦

- 目标与边界: 拆分 God Object/Fat Controller，修复依赖反转与重复认证逻辑。
- 触发条件与状态流转: 优先抽公共服务，再切 endpoint，最后收敛 repo 依赖。
- 代码锚点: `app/services/chat_service.py`, `app/services/skill_service.py`, `app/api/v1/endpoints/data_admin_api.py`, `app/repositories/chat_repo.py`, `app/api/deps.py`, `app/core/handlers.py`。
- 关键契约字段: `service_interface`, `repository_contract`。
- 回滚锚点: `SERVICE_SPLIT_ENABLE`。
- 验证命令: `pytest tests/unit -k "service or repository or deps" -q`。
- 来源证据: 报告 #17 #18 #19 #20 #40 #41 #42 #45 #46 #56 #57。

```python
class ChatMessageRepository(Protocol):
    def get_messages_by_thread(...): ...
```

### FP-ARC-03: 运行态一致性与异步可靠性

- 目标与边界: run-control 内存态与 DB 态一致、阻塞路径异步化、时间语义统一 UTC。
- 触发条件与状态流转: `start/cancel/resume/complete/fail` 全状态落库并可恢复。
- 代码锚点: `app/services/run_control_service.py`, `app/db/postgres_checkpoint.py`, `app/services/token_service.py`, `app/api/v1/endpoints/chat_api.py`。
- 关键契约字段: `run_id`, `status`, `updated_at`, `expires_at_utc`。
- 回滚锚点: `RUN_CONTROL_PERSISTENCE_MODE`。
- 验证命令: `pytest tests/unit -k "run_control or checkpoint" -q`。
- 来源证据: 报告 #21 #22 #38 #43 #58。

```python
expires_at = datetime.fromtimestamp(exp, tz=timezone.utc)
```

### FP-BE-01: 后端模型/Schema/异常治理

- 目标与边界: 模型定义统一、schema 下沉、异常处理与日志规范收敛、修复空指针与缓存泄漏。
- 触发条件与状态流转: API 层 schema -> service -> repo 全链路契约统一。
- 代码锚点: `app/models/**`, `app/schemas/**`, `app/api/v1/endpoints/*.py`, `app/ai/tools/chatTools.py`。
- 关键契约字段: `created_at`, `feedback_model`, `validation_return_type`。
- 回滚锚点: `MODEL_SCHEMA_REFACTOR_PHASE`。
- 验证命令: `pytest tests/unit -k "models or schema or todo_api" -q`。
- 来源证据: 报告 #8 #24 #29 #30 #31 #32 #33 #44 #48 #50 #51。

```python
limit: int = Query(default=50, ge=1, le=100)
```

### FP-FE-01: 前端类型与交互一致性

- 目标与边界: 清理 `as any/catch any`、修复 confirm/refresh/路由重复与缓存失效问题。
- 触发条件与状态流转: 仅调整类型与调用契约，不改业务文案。
- 代码锚点: `web/src/components/**`, `web/src/hooks/useSSEStream.ts`, `web/src/lib/backend.ts`, `web/src/app/layout.tsx`。
- 关键契约字段: `DecisionType`, `refreshThreads`, `lang="zh-CN"`。
- 回滚锚点: `FRONTEND_STRICT_TYPES`。
- 验证命令: `cd web && pnpm test && pnpm lint`。
- 来源证据: 报告 #9 #26 #27 #28 #35 #52 #53 #54 #55。

```ts
try {
  ...
} catch (err: unknown) {
  const message = err instanceof Error ? err.message : "unknown";
}
```

### FP-QA-01: 集成测试与追溯矩阵补齐

- 目标与边界: 建立 `tests/integration/`，形成“问题 -> feature -> case -> 证据”闭环。
- 触发条件与状态流转: 每张整改卡完成前必须补齐对应最小集成测试。
- 代码锚点: `tests/integration/**`, `docs/开发文档/测试管理/测试用例库.md`。
- 关键契约字段: `tc_id`, `feature_id`, `evidence_ref`。
- 回滚锚点: 不允许回滚（仅可扩展）。
- 验证命令: `pytest tests/integration -q`。
- 来源证据: 报告 #25。

```yaml
tc_id: TC-SEC-03
feature_id: FP-SEC-05
evidence: tests/integration/test_messages_idor.py
```

---

## 4. 分阶段实施路线图

### Phase 0（D0-D1）基线冻结

- 冻结整改范围（#1-#68）。
- 产出卡片与门禁契约。
- 建立复测台账模板（用于后续自动打勾）。

### Phase 1（D1-D5）安全高风险收口

- 执行 FP-SEC-01 ~ FP-SEC-08、FP-OPS-01。
- 目标：P0 全清、P1 安全主链清。

### Phase 2（D5-D10）架构高风险收口

- 执行 FP-ARC-01 ~ FP-ARC-03。
- 目标：主干架构不再继续膨胀，状态/依赖方向可验证。

### Phase 3（D10-D14）工程质量与测试收口

- 执行 FP-BE-01、FP-FE-01、FP-QA-01。
- 目标：P2 核心项闭环，形成稳定回归基线。

---

## 5. 依赖与风险矩阵

| 风险 | 影响 | 前置缓解 |
|---|---|---|
| 沙箱替换影响数据分析能力 | 业务功能退化 | 先引入兼容白名单、保留灰度开关 |
| 归属校验加严导致历史调用失败 | 前端回归风险 | 同步补齐错误码语义与前端处理 |
| 大文件拆分引发隐式导入问题 | 编译/运行失败 | 分阶段拆分 + 每阶段最小回归 |
| 集成测试新增导致 CI 时长增加 | 交付周期压力 | 冒烟套件与全量套件分层执行 |

---

## 6. 验证与发布策略

1. 单卡验证：每卡至少 1 条单测 + 1 条接口/集成验证命令。
2. 波次验证：每阶段结束执行一次 P0/P1 回归。
3. 发布门禁：Gate 卡全部通过后才允许合并到主分支。
4. 回滚策略：按 feature 开关/迁移脚本/接口兼容三层回滚。

---

## 7. 机读执行契约

```yaml
planning_contract:
  task_key: PP-20260226-全面代码审查整改
  execution_mode: serial
  card_order: [C00, C01, C02, C03, C04, C05, C06, C07, C08, C09, C10, C11, C12, C13, C14, G01, G02, G03, G04]
  strict_single_active_card: true
  auto_done_policy:
    implementation-card: hard_gate
    inspection-card: policy_gate
  gate_contract:
    mode: as_cards
    gate_ids: [G01, G02, G03, G04]
    depends_on:
      G01: [C08]
      G02: [C11]
      G03: [C14]
      G04: [G03]
  cards:
    - card_id: C00
      wave: P0
      feature_ids: [FP-SEC-01, FP-SEC-02, FP-SEC-03, FP-SEC-04, FP-SEC-05, FP-SEC-06, FP-SEC-07, FP-SEC-08, FP-OPS-01]
      depends_on: []
      acceptance_checks:
        - "python3 scripts/docs_guard.py --strict"
        - "python3 -m pytest tests/unit -k 'sql_safety or run_control' -q"
      done_gate:
        - "范围冻结为 #1-#68"
        - "卡片与 feature 映射一致"

    - card_id: C01
      wave: P0
      feature_ids: [FP-SEC-04]
      depends_on: [C00]
      acceptance_checks:
        - "python3 -m pytest tests/unit -k 'auth or token' -q"
      done_gate:
        - "JWT/密码/限流基线已收口"

    - card_id: C02
      wave: P0
      feature_ids: [FP-SEC-01]
      depends_on: [C01]
      acceptance_checks:
        - "python3 -m pytest tests/unit -k 'python_inter or fig_inter' -q"
      done_gate:
        - "chatTools 不再含裸 eval/exec 执行路径"

    - card_id: C03
      wave: P0
      feature_ids: [FP-SEC-02, FP-SEC-03]
      depends_on: [C02]
      acceptance_checks:
        - "python3 -m pytest tests/unit -k 'sql_safety or sql_rewriter' -q"
      done_gate:
        - "SQL 安全链统一生效"
        - "RLS 不再字符串拼接"

    - card_id: C04
      wave: P0
      feature_ids: [FP-SEC-05]
      depends_on: [C03]
      acceptance_checks:
        - "python3 -m pytest tests/integration -k 'idor or ownership or resume' -q"
      done_gate:
        - "messages/feedback/resume/assets 归属校验通过"

    - card_id: C05
      wave: P1
      feature_ids: [FP-SEC-06]
      depends_on: [C04]
      acceptance_checks:
        - "python3 -m pytest tests/integration -k 'assets or ragflow' -q"
      done_gate:
        - "流式代理生命周期与错误码语义正确"

    - card_id: C06
      wave: P1
      feature_ids: [FP-SEC-07, FP-SEC-08]
      depends_on: [C05]
      acceptance_checks:
        - "python3 -m pytest tests/integration -k 'health or dev_codex' -q"
      done_gate:
        - "健康检查脱敏 + APIKey/开发工具约束完成"

    - card_id: C07
      wave: P1
      feature_ids: [FP-OPS-01]
      depends_on: [C06]
      acceptance_checks:
        - "python3 -m pytest tests/unit -k 'guardrail or cors' -q"
      done_gate:
        - "prod CORS 不可退化"
        - "guardrail fail-close"

    - card_id: C08
      wave: P1
      feature_ids: [FP-SEC-05]
      depends_on: [C07]
      acceptance_checks:
        - "python3 -m pytest tests/integration -k 'authorization' -q"
      done_gate:
        - "P1 安全链复测通过"

    - card_id: C09
      wave: P1
      feature_ids: [FP-ARC-01]
      depends_on: [C08]
      acceptance_checks:
        - "python3 -m pytest tests/unit -k 'graph or state' -q"
      done_gate:
        - "Graph/State 拆分第一阶段完成"

    - card_id: C10
      wave: P1
      feature_ids: [FP-ARC-02]
      depends_on: [C09]
      acceptance_checks:
        - "python3 -m pytest tests/unit -k 'service or repository or deps' -q"
      done_gate:
        - "Service/Repo/Controller 边界收敛"

    - card_id: C11
      wave: P1
      feature_ids: [FP-ARC-03]
      depends_on: [C10]
      acceptance_checks:
        - "python3 -m pytest tests/unit -k 'run_control or checkpoint' -q"
      done_gate:
        - "运行态一致性闭环"

    - card_id: C12
      wave: P2
      feature_ids: [FP-BE-01]
      depends_on: [C11]
      acceptance_checks:
        - "python3 -m pytest tests/unit -k 'models or schema or todo_api' -q"
      done_gate:
        - "后端模型/schema/异常治理完成"

    - card_id: C13
      wave: P2
      feature_ids: [FP-FE-01]
      depends_on: [C12]
      acceptance_checks:
        - "cd web && pnpm lint"
        - "cd web && pnpm test"
      done_gate:
        - "前端类型与交互一致性达标"

    - card_id: C14
      wave: P2
      feature_ids: [FP-QA-01]
      depends_on: [C13]
      acceptance_checks:
        - "python3 -m pytest tests/integration -q"
      done_gate:
        - "integration 测试基线建立"

    - card_id: G01
      task_mode: inspection-card
      merge_required: false
      feature_ids: [FP-SEC-01, FP-SEC-02, FP-SEC-03, FP-SEC-04, FP-SEC-05, FP-SEC-06, FP-SEC-07, FP-SEC-08, FP-OPS-01]
      depends_on: [C08]
      acceptance_checks:
        - "python3 -m pytest tests/integration -k 'security or authorization' -q"
      done_gate:
        - "P0/P1 安全项闭环"

    - card_id: G02
      task_mode: inspection-card
      merge_required: false
      feature_ids: [FP-ARC-01, FP-ARC-02, FP-ARC-03]
      depends_on: [C11]
      acceptance_checks:
        - "python3 -m pytest tests/unit -k 'graph or run_control or repository' -q"
      done_gate:
        - "架构边界与状态契约通过"

    - card_id: G03
      task_mode: inspection-card
      merge_required: false
      feature_ids: [FP-BE-01, FP-FE-01, FP-QA-01]
      depends_on: [C14]
      acceptance_checks:
        - "python3 -m pytest tests/integration -q"
      done_gate:
        - "端到端回归通过"

    - card_id: G04
      task_mode: inspection-card
      merge_required: false
      feature_ids: [FP-SEC-01, FP-SEC-02, FP-SEC-03, FP-SEC-04, FP-SEC-05, FP-SEC-06, FP-SEC-07, FP-SEC-08, FP-OPS-01, FP-ARC-01, FP-ARC-02, FP-ARC-03, FP-BE-01, FP-FE-01, FP-QA-01]
      depends_on: [G03]
      acceptance_checks:
        - "python3 scripts/docs_guard.py --strict"
      done_gate:
        - "文档、证据、台账同步完成"
```

