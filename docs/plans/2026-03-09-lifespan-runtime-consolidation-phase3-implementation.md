# Lifespan Runtime Consolidation Phase 3 Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Consolidate selected process-wide caches under a shared cache registry and make runtime hold the single cache owner reference.

**Architecture:** Add one lightweight cache registry module as the shared owner for process-wide dict caches. Migrate `data_graph` intent policy cache and `data_access_control` config cache onto it, keep existing public invalidation contracts, and let `AppRuntime` carry the registry reference instead of ad-hoc status dicts.

**Tech Stack:** FastAPI, Starlette lifespan, Python dataclasses, pytest

---

### Task 1: Add cache registry primitive with tests

**Files:**
- Create: `app/core/cache_registry.py`
- Create: `tests/unit/test_cache_registry.py`

**Step 1: Write the failing tests**

覆盖：
1. 同名缓存槽会复用同一 dict 实例
2. `clear(name)` 会清空该槽数据
3. `reset_all()` 会清空全部槽与状态

**Step 2: Run test to verify it fails**

Run:
```bash
VK_RUNTIME_VENV=/tmp/codex-py311 bash scripts/pytest_targeted.sh tests/unit/test_cache_registry.py -q
```
Expected: FAIL，因为 registry 尚不存在。

**Step 3: Write minimal implementation**

新增 `CacheRegistry`，仅提供：
- `get_dict_cache(name, initial)`
- `clear(name)`
- `reset_all()`
- `set_status(name, status)` / `get_status(name)`

**Step 4: Re-run focused tests**

Run:
```bash
VK_RUNTIME_VENV=/tmp/codex-py311 bash scripts/pytest_targeted.sh tests/unit/test_cache_registry.py -q
```
Expected: PASS。

### Task 2: Migrate `data_graph` intent policy cache to registry

**Files:**
- Modify: `app/ai/workflow/data_graph.py`
- Create: `tests/unit/test_data_graph_intent_policy_cache_registry.py`

**Step 1: Write the failing tests**

覆盖：
1. `_load_data_graph_intent_policy()` 第二次命中缓存，不重复读配置
2. `invalidate_data_graph_intent_policy_cache()` 后会重新加载
3. `_get_data_graph_intent_policy_cache_meta()` 仍输出 `source/cache_hit/cache_age_sec`

**Step 2: Run test to verify it fails**

Run:
```bash
VK_RUNTIME_VENV=/tmp/codex-py311 bash scripts/pytest_targeted.sh tests/unit/test_data_graph_intent_policy_cache_registry.py -q
```
Expected: FAIL，因为 registry 接入和 invalidator 尚不存在。

**Step 3: Write minimal implementation**

- 去掉模块内独占 `_DATA_GRAPH_INTENT_POLICY_CACHE`
- 改为从 registry 获取命名缓存槽
- 新增 `invalidate_data_graph_intent_policy_cache()`

**Step 4: Re-run focused tests**

Run:
```bash
VK_RUNTIME_VENV=/tmp/codex-py311 bash scripts/pytest_targeted.sh tests/unit/test_data_graph_intent_policy_cache_registry.py -q
```
Expected: PASS。

### Task 3: Migrate `data_access_control` config cache to registry

**Files:**
- Modify: `app/ai/semantic/data_access_control.py`
- Reuse: `tests/unit/test_access_admin_key_compat.py`

**Step 1: Extend failing tests if needed**

补最小断言：`invalidate_config_cache()` 之后，配置查询会重新走加载路径。

**Step 2: Run targeted tests**

Run:
```bash
VK_RUNTIME_VENV=/tmp/codex-py311 bash scripts/pytest_targeted.sh tests/unit/test_access_admin_key_compat.py -q
```
Expected: 至少一条失败，或暴露当前缓存仍是模块私有 owner。

**Step 3: Write minimal implementation**

- 去掉模块内私有 `_config_cache`
- 改为使用 registry 命名缓存槽
- 保持 `invalidate_config_cache()` 对外契约不变

**Step 4: Re-run focused tests**

Run:
```bash
VK_RUNTIME_VENV=/tmp/codex-py311 bash scripts/pytest_targeted.sh tests/unit/test_access_admin_key_compat.py -q
```
Expected: PASS。

### Task 4: Let runtime hold the shared cache registry reference

**Files:**
- Modify: `app/core/runtime.py`
- Reuse: `tests/unit/test_app_runtime_bootstrap.py`

**Step 1: Extend failing tests**

补断言：
1. `runtime.cache_registry` 是 registry owner，而不是临时状态 dict
2. startup optional warmup status 仍可记录
3. runtime close 可以清空 registry

**Step 2: Run focused tests**

Run:
```bash
VK_RUNTIME_VENV=/tmp/codex-py311 bash scripts/pytest_targeted.sh tests/unit/test_cache_registry.py tests/unit/test_app_runtime_bootstrap.py -q
```
Expected: FAIL，因为 runtime 还没切到 registry owner。

**Step 3: Write minimal implementation**

- `build_runtime()` 使用 shared registry
- 用 registry 记录 warm/degraded 状态
- 把 registry reset 注册到 cleanup callbacks

**Step 4: Re-run focused tests**

Run:
```bash
VK_RUNTIME_VENV=/tmp/codex-py311 bash scripts/pytest_targeted.sh tests/unit/test_cache_registry.py tests/unit/test_data_graph_intent_policy_cache_registry.py tests/unit/test_access_admin_key_compat.py tests/unit/test_app_runtime_bootstrap.py -q
```
Expected: PASS。

### Task 5: Run focused Phase 1-3 regression suite

**Files:**
- Reuse all runtime / db / cache related tests

**Step 1: Run targeted regression suite**

Run:
```bash
VK_RUNTIME_VENV=/tmp/codex-py311 bash scripts/pytest_targeted.sh \
  tests/unit/test_cache_registry.py \
  tests/unit/test_data_graph_intent_policy_cache_registry.py \
  tests/unit/test_access_admin_key_compat.py \
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
