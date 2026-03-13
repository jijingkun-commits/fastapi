# Admin Overview Metrics V2 Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Rebuild the admin overview metrics pipeline so `summary` / `trends` / `stream` share one minute-bucket source of truth, while splitting business request quality from user question activity and making `no_data/stale/degraded` explicit.

**Architecture:** Replace the current in-memory 5-minute collector as the source of truth with a persisted minute-bucket read model, then move scoring/state derivation into a single overview query layer. Refactor the frontend to render explicit card states rather than inferring semantics from missing values.

**Tech Stack:** FastAPI, SQLAlchemy, PostgreSQL JSONB, Next.js/React, targeted pytest, Playwright/E2E as needed.

---

## 0. Preflight Rules

- 任何实现开始前，先执行：`pwd`、`git branch --show-current`、`git worktree list`。
- 任何测试前，先执行：`bash scripts/repo_python.sh`，回显命中的解释器路径。
- 定向回归统一使用：`bash scripts/pytest_targeted.sh <tests...>`。
- 当前环境若无独立 `apply_patch`，必须记录 `APPLY_PATCH_TOOL_UNAVAILABLE_FALLBACK`，并使用安全直接写回方式。
- 本计划默认 **不执行 git commit**；只有用户明确授权后，才把“Checkpoint”替换成真实 commit。

### Task 1: Freeze truth-source docs and API contract

**Files:**
- Modify: `docs/API文档/接口文档.md`
- Modify: `docs/开发文档/架构设计/前端架构.md`
- Modify: `docs/开发文档/架构设计/数据库设计.md`
- Reference: `workdocs/归档/正文/设计/2026-03-09-admin-overview-metrics-v2-design.md`

**Step 1: Write the failing doc expectations**

把以下最终口径写成文档 TODO：
- `请求质量` = 全业务 API 请求质量
- `用户提问活跃度` = 聊天提问口径
- `summary/trends/stream` = 同一事实源
- 卡片状态 = `ok/no_data/stale/degraded`

**Step 2: Verify the current docs still describe old semantics**

Run:
```bash
rg -n "用户提问事件口径|请求质量|总览驾驶舱|分钟快照" docs/API文档/接口文档.md docs/开发文档/架构设计/前端架构.md docs/开发文档/架构设计/数据库设计.md
```
Expected: 现有文档仍保留旧“用户提问口径”描述。

**Step 3: Update docs in place**

- 原位修改 API 文档的总览章节。
- 原位修改前端架构中 `AdminOverviewCockpit` 的关键行为。
- 原位修改数据库设计，新增分钟桶读模型并标注旧快照表去向。

**Step 4: Re-run the doc grep check**

Run:
```bash
rg -n "ok/no_data/stale/degraded|用户提问活跃度|单一事实源|分钟桶" docs/API文档/接口文档.md docs/开发文档/架构设计/前端架构.md docs/开发文档/架构设计/数据库设计.md
```
Expected: 新口径关键词全部命中。

**Step 5: Checkpoint**

- 记录文档映射完成，等待后续代码实现。

### Task 2: Introduce observability registry and minute-bucket model

**Files:**
- Create: `app/observability/module_registry.py`
- Create: `app/observability/request_scope_resolver.py`
- Create: `app/models/runtime_metric_bucket.py`
- Create: `alembic/versions/<timestamp>_create_runtime_metric_bucket_minute.py`
- Modify: `app/models/__init__.py`
- Modify: `docs/开发文档/架构设计/数据库设计.md`
- Test: `tests/unit/test_request_scope_resolver.py`
- Test: `tests/unit/test_runtime_metric_bucket_model.py`

**Step 1: Write the failing tests**

覆盖以下行为：
- 路由被解析为 `all_business / user_question / admin_operation`
- 模块映射输出稳定的 `module_key`
- 分钟桶模型具备唯一约束与必要字段

**Step 2: Run focused tests to confirm failure**

Run:
```bash
bash scripts/pytest_targeted.sh tests/unit/test_request_scope_resolver.py tests/unit/test_runtime_metric_bucket_model.py -q
```
Expected: FAIL，因为 resolver 和模型尚不存在。

**Step 3: Implement minimal model and registry**

- 新增 observability registry，收敛路径到 `scope/module_key` 的映射。
- 新增分钟桶 SQLAlchemy 模型。
- 编写 Alembic 迁移。

**Step 4: Re-run focused tests**

Run:
```bash
bash scripts/pytest_targeted.sh tests/unit/test_request_scope_resolver.py tests/unit/test_runtime_metric_bucket_model.py -q
```
Expected: PASS。

**Step 5: Checkpoint**

- 记录分钟桶模型已落库、旧关键词猜测路径准备淘汰。

### Task 3: Replace in-memory fact source with minute-bucket writer

**Files:**
- Create: `app/services/runtime_metric_bucket_writer.py`
- Modify: `app/core/middlewares/correlation.py`
- Modify: `app/services/runtime_request_metrics.py`
- Modify or delete: `app/services/overview_runtime_collector.py`
- Test: `tests/unit/test_runtime_metric_bucket_writer.py`
- Test: `tests/unit/test_correlation_middleware_metrics.py`

**Step 1: Write the failing tests**

要求：
- API 请求完成后写入分钟桶，而不是只写进程内队列。
- 总览自身请求仍被排除在业务质量统计外。
- `user_question` 与 `all_business` 可以同时累积样本。

**Step 2: Run the failing tests**

Run:
```bash
bash scripts/pytest_targeted.sh tests/unit/test_runtime_metric_bucket_writer.py tests/unit/test_correlation_middleware_metrics.py -q
```
Expected: FAIL，因为当前仅有进程内写入。

**Step 3: Implement minimal writer path**

- 中间件调用分钟桶写入器。
- 如需临时保留内存缓存，仅允许作为短期缓存，不可再作为事实源读取。
- 删除或收缩 `overview_runtime_collector.py` 的职责，避免双源聚合。

**Step 4: Re-run focused tests**

Run:
```bash
bash scripts/pytest_targeted.sh tests/unit/test_runtime_metric_bucket_writer.py tests/unit/test_correlation_middleware_metrics.py -q
```
Expected: PASS。

**Step 5: Checkpoint**

- 确认请求事实已从“进程内状态”迁移到“分钟桶读模型”。

### Task 4: Build one overview query service for summary, trends, and stream

**Files:**
- Create: `app/services/admin_overview_query_service.py`
- Modify or replace: `app/services/admin_overview_service.py`
- Modify: `app/api/v1/endpoints/admin_overview_api.py`
- Modify: `app/schemas/admin_overview.py`
- Test: `tests/unit/test_admin_overview_query_service.py`
- Test: `tests/api/test_admin_overview_api.py`

**Step 1: Write the failing service/API tests**

覆盖四类状态：
- `ok`
- `no_data`
- `stale`
- `degraded`

并验证：
- `summary/trends/stream` 同源
- `请求质量` 与 `用户提问活跃度` 拆分
- 健康总分在 `no_data` 时不再误给高分

**Step 2: Run the failing tests**

Run:
```bash
bash scripts/pytest_targeted.sh tests/unit/test_admin_overview_query_service.py tests/api/test_admin_overview_api.py -q
```
Expected: FAIL，因为当前 contract 仍是旧模型。

**Step 3: Implement the canonical query layer**

- 用分钟桶查询构建当前窗口快照。
- 用同一事实源构建 `1h/24h` 趋势。
- `stream` 只发送 canonical snapshot patch，不再重算另一套语义。

**Step 4: Re-run focused tests**

Run:
```bash
bash scripts/pytest_targeted.sh tests/unit/test_admin_overview_query_service.py tests/api/test_admin_overview_api.py -q
```
Expected: PASS。

**Step 5: Checkpoint**

- 记录旧 `summary -> persist -> trends` 链路已断开。

### Task 5: Refactor frontend to explicit card states and split metrics

**Files:**
- Modify: `web/src/types/admin-overview.ts`
- Modify: `web/src/lib/admin-overview-api.ts`
- Modify: `web/src/components/admin/overview/AdminOverviewCockpit.tsx`
- Modify: `web/e2e/features/admin-overview.feature.cjs`
- Test: `web/src/components/admin/overview/__tests__/AdminOverviewCockpit.test.tsx`（如已有相邻测试目录则复用）

**Step 1: Write the failing UI tests**

覆盖：
- `no_data` 时展示“无业务样本”而不是 `-- + 健康分`
- 请求质量与用户提问活跃度分成两张卡
- 趋势图仍可显示历史点，但当前卡片状态正确
- 模块跳转按 `module_key` 而不是关键词猜测

**Step 2: Run the focused UI tests**

Run:
```bash
bash scripts/pytest_targeted.sh web/src/components/admin/overview/__tests__/AdminOverviewCockpit.test.tsx -q
```
Expected: FAIL，因为 UI 仍消费旧 contract。

**Step 3: Implement the minimal frontend refactor**

- 更新类型定义和 API normalizer。
- 改卡片结构与状态渲染。
- 移除前端对 `unknown/null/--` 的业务语义猜测。

**Step 4: Re-run focused UI tests**

Run:
```bash
bash scripts/pytest_targeted.sh web/src/components/admin/overview/__tests__/AdminOverviewCockpit.test.tsx -q
```
Expected: PASS。

**Step 5: Checkpoint**

- 记录 UI 已完全切换到显式状态 contract。

### Task 6: Delete obsolete paths and verify lean closure

**Files:**
- Delete or shrink: `app/services/overview_runtime_collector.py`
- Delete or shrink: `app/services/runtime_request_metrics.py`
- Modify: related imports and tests
- Test: `tests/unit/test_runtime_overview_collector.py`（替换/删除旧测试）
- Test: `tests/unit/test_admin_overview_service.py`

**Step 1: Write the failing cleanup assertions**

验证：
- 不再存在旧“用户提问即请求质量”的分支口径。
- 不再存在以进程内队列为事实源的读取链路。
- 旧测试全部迁移到新 contract，或在无价值时删除。

**Step 2: Run the focused cleanup tests**

Run:
```bash
bash scripts/pytest_targeted.sh tests/unit/test_admin_overview_service.py tests/unit/test_runtime_overview_collector.py -q
```
Expected: FAIL，因为仍残留旧实现/旧测试。

**Step 3: Remove obsolete code paths**

- 删除无用 collector 和旧状态分支。
- 收敛 `admin_overview_service` 到新 query service 或直接合并职责。
- 清理旧字段、旧 helper、旧测试。

**Step 4: Re-run focused tests and lean guard**

Run:
```bash
bash scripts/pytest_targeted.sh tests/unit/test_admin_overview_query_service.py tests/api/test_admin_overview_api.py tests/unit/test_correlation_middleware_metrics.py -q
python3 scripts/ci/check_lean_budget.py --cached --strict
```
Expected: PASS；lean guard 不报热点净增长阻断。

**Step 5: Checkpoint**

- 输出删除清单、重复收敛点、复杂度变化。

### Task 7: Final verification and runtime evidence

**Files:**
- Modify in place if needed: `docs/开发文档/测试管理/管理后台测试案例.md`
- Reference: `docs/API文档/接口文档.md`
- Reference: `docs/开发文档/架构设计/数据库设计.md`

**Step 1: Resolve repo python and verify context**

Run:
```bash
pwd
git branch --show-current
git worktree list
bash scripts/repo_python.sh
```
Expected: 输出当前 worktree、分支、解释器路径。

**Step 2: Run targeted regression matrix**

Run:
```bash
bash scripts/pytest_targeted.sh tests/unit/test_admin_overview_query_service.py tests/api/test_admin_overview_api.py tests/unit/test_correlation_middleware_metrics.py -q
```
Expected: PASS。

**Step 3: Run runtime checks for backend/frontend**

Run:
```bash
eval "$(bash scripts/vk_ports.sh --export)"
lsof -nP -iTCP:${VK_BACKEND_PORT} -sTCP:LISTEN
curl -sf "http://127.0.0.1:${VK_BACKEND_PORT}/health"
```
Expected: 后端监听正常，健康接口返回成功。

**Step 4: Validate the key user story**

验证三个场景：
- 无业务流量：页面显示 `no_data`
- 有业务 API 无提问：业务请求质量有值，提问活跃度为 `no_data`
- 有提问流量：两张卡都更新，趋势与当前窗口一致

**Step 5: Final handoff**

交付内容应包含：
- 设计收敛说明
- 删除清单
- 新旧 contract 对照
- 测试与运行态证据
- 残余风险与后续优化项
