# Lifespan Runtime Consolidation Phase 2 Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Centralize shared DB engine lifecycle under runtime cleanup and remove `MetricService`'s duplicate private engine owners.

**Architecture:** Preserve the repository's existing `app.db.session` import contract so the change stays surgical, but add explicit DB lifecycle helpers that runtime can own. Remove `MetricService`'s local `create_engine()` branches and make it reuse the shared chat/analytics engines from `app.db.session`.

**Tech Stack:** FastAPI, SQLAlchemy, pytest

---

### Task 1: Add DB runtime lifecycle helpers with tests

**Files:**
- Modify: `app/db/session.py`
- Create: `tests/unit/test_db_session_runtime.py`

**Step 1: Write the failing tests**

覆盖：
1. `get_database_runtime()` 返回共享 `engine / analytics_engine / SessionLocal`
2. `close_database_runtime()` 会对两个 engine 调用 `dispose()`

**Step 2: Run test to verify it fails**

Run:
```bash
VK_RUNTIME_VENV=/tmp/codex-py311 bash scripts/pytest_targeted.sh tests/unit/test_db_session_runtime.py -q
```
Expected: FAIL，因为 helper 尚不存在。

**Step 3: Write minimal implementation**

在 `app/db/session.py` 增加最小 helper：
- `DatabaseRuntime`
- `get_database_runtime()`
- `close_database_runtime()`

**Step 4: Run test to verify it passes**

Run:
```bash
VK_RUNTIME_VENV=/tmp/codex-py311 bash scripts/pytest_targeted.sh tests/unit/test_db_session_runtime.py -q
```
Expected: PASS。

### Task 2: Make runtime own DB cleanup

**Files:**
- Modify: `app/core/runtime.py`
- Reuse: `tests/unit/test_app_runtime_bootstrap.py`

**Step 1: Extend failing tests**

补断言：`build_runtime()` 返回的 `runtime.db` 不再是 `None`，并且 runtime 关闭时会注册 DB cleanup。

**Step 2: Run test to verify it fails**

Run:
```bash
VK_RUNTIME_VENV=/tmp/codex-py311 bash scripts/pytest_targeted.sh tests/unit/test_app_runtime_bootstrap.py -q
```
Expected: FAIL，因为 `runtime.db` 还未接 DB helper。

**Step 3: Write minimal implementation**

让 `build_runtime()` 使用 `get_database_runtime()`，并注册 `close_database_runtime()`。

**Step 4: Run test to verify it passes**

Run:
```bash
VK_RUNTIME_VENV=/tmp/codex-py311 bash scripts/pytest_targeted.sh tests/unit/test_db_session_runtime.py tests/unit/test_app_runtime_bootstrap.py -q
```
Expected: PASS。

### Task 3: Remove MetricService private engine owners

**Files:**
- Modify: `app/services/metric_service.py`
- Create: `tests/unit/test_metric_service_engine_sharing.py`

**Step 1: Write the failing tests**

覆盖：
1. `MetricService` 默认复用 `app.db.session.engine`
2. `MetricService` 默认复用 `app.db.session.analytics_engine`
3. `get_metric_service()` 仍保持原有单例契约

**Step 2: Run test to verify it fails**

Run:
```bash
VK_RUNTIME_VENV=/tmp/codex-py311 bash scripts/pytest_targeted.sh tests/unit/test_metric_service_engine_sharing.py -q
```
Expected: FAIL，因为当前 `MetricService` 仍在私有分支内 `create_engine()`。

**Step 3: Write minimal implementation**

删除 `MetricService` 内 `_chat_engine/_data_engine` 的私有 owner 逻辑，改为直接使用共享 engine。

**Step 4: Run test to verify it passes**

Run:
```bash
VK_RUNTIME_VENV=/tmp/codex-py311 bash scripts/pytest_targeted.sh tests/unit/test_metric_service_engine_sharing.py -q
```
Expected: PASS。

### Task 4: Verify no regression on runtime and metrics tests

**Files:**
- Reuse: `tests/unit/test_app_runtime.py`
- Reuse: `tests/unit/test_app_runtime_bootstrap.py`
- Reuse: `tests/unit/test_app_runtime_lifespan.py`
- Reuse: `tests/unit/test_postgres_checkpointer_pooling.py`
- Reuse: `tests/unit/test_observability.py`
- Reuse: `app/tests/test_chat_assets.py`
- Reuse: new DB/Metric tests

**Step 1: Run focused regression suite**

Run:
```bash
VK_RUNTIME_VENV=/tmp/codex-py311 bash scripts/pytest_targeted.sh \
  tests/unit/test_db_session_runtime.py \
  tests/unit/test_metric_service_engine_sharing.py \
  tests/unit/test_app_runtime.py \
  tests/unit/test_app_runtime_bootstrap.py \
  tests/unit/test_app_runtime_lifespan.py \
  tests/unit/test_postgres_checkpointer_pooling.py \
  tests/unit/test_observability.py \
  app/tests/test_chat_assets.py -q
```
Expected: PASS。
