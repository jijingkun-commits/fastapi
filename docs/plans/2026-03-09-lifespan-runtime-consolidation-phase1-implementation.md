# Lifespan Runtime Consolidation Phase 1 Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build the first `AppRuntime` skeleton and move the outermost application-level startup resources under `lifespan` ownership.

**Architecture:** Keep FastAPI `lifespan` as the only startup/shutdown orchestrator, introduce a small `app.state.runtime` contract, and move only low-risk shared resources in Phase 1. Do not rewrite all service access patterns yet. Focus on owner convergence, startup/shutdown tests, and deletion of import-time side effects.

**Tech Stack:** FastAPI, Starlette lifespan, Python dataclasses, SQLAlchemy, pytest

---

### Task 1: Create the runtime contract and its first unit tests

**Files:**
- Create: `app/core/runtime.py`
- Create: `tests/unit/test_app_runtime.py`
- Modify: `app/core/__init__.py`（如果需要导出 runtime helper）

**Step 1: Write the failing tests**

新增 `tests/unit/test_app_runtime.py`，至少覆盖：

```python
import asyncio

from app.core.runtime import AppRuntime, GraphRuntime


async def _close_marker(bucket: list[str]) -> None:
    bucket.append("closed")


def test_app_runtime_aclose_executes_registered_cleanup():
    events: list[str] = []
    runtime = AppRuntime(
        db=None,
        checkpointer=None,
        tracer=None,
        asset_service=None,
        graphs=GraphRuntime(default_multi_agent_graph=None),
        cache_registry={},
        cleanup_callbacks=[lambda: _close_marker(events)],
    )

    asyncio.run(runtime.aclose())

    assert events == ["closed"]
```

**Step 2: Run test to verify it fails**

Run:
```bash
bash scripts/repo_python.sh
bash scripts/pytest_targeted.sh tests/unit/test_app_runtime.py -q
```
Expected: FAIL，因为 `app/core/runtime.py` 尚不存在。

**Step 3: Write minimal implementation**

在 `app/core/runtime.py` 新增最小骨架：

```python
from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable, Optional

CleanupCallback = Callable[[], Awaitable[None] | None]

@dataclass(slots=True)
class GraphRuntime:
    default_multi_agent_graph: Optional[Any] = None

@dataclass(slots=True)
class AppRuntime:
    db: Any
    checkpointer: Any
    tracer: Any
    asset_service: Any
    graphs: GraphRuntime
    cache_registry: dict[str, Any]
    cleanup_callbacks: list[CleanupCallback] = field(default_factory=list)

    async def aclose(self) -> None:
        for callback in reversed(self.cleanup_callbacks):
            result = callback()
            if result is not None:
                await result
```

**Step 4: Run test to verify it passes**

Run:
```bash
bash scripts/repo_python.sh
bash scripts/pytest_targeted.sh tests/unit/test_app_runtime.py -q
```
Expected: PASS。

**Step 5: Checkpoint**

- 记录 runtime 基础 owner 已建立；
- 暂不引入额外抽象或 DI 容器。

### Task 2: Add bootstrap helpers for startup directories, tracer, rules, and optional asset service

**Files:**
- Modify: `app/core/runtime.py`
- Modify: `app/ai/utils/observability.py`
- Modify: `app/services/asset_service.py`
- Create: `tests/unit/test_app_runtime_bootstrap.py`

**Step 1: Write the failing tests**

新增 `tests/unit/test_app_runtime_bootstrap.py`，覆盖：

1. `build_runtime()` 会准备 `PUBLIC_DIR/images`；
2. `build_runtime()` 会调用 `get_tracer()`；
3. `build_runtime()` 会刷新结果增强规则；
4. `AssetService` 初始化失败时只降级，不阻断 runtime 构建。

示例断言：

```python
def test_build_runtime_prepares_images_dir_and_rule_warmup(monkeypatch, tmp_path):
    ...
    runtime = asyncio.run(build_runtime())
    assert (tmp_path / "images").exists()
    assert warmup_calls == ["rules"]
```

**Step 2: Run tests to verify they fail**

Run:
```bash
bash scripts/repo_python.sh
bash scripts/pytest_targeted.sh tests/unit/test_app_runtime.py tests/unit/test_app_runtime_bootstrap.py -q
```
Expected: FAIL，因为 `build_runtime()` 和相关 helper 尚不存在。

**Step 3: Write minimal implementation**

在 `app/core/runtime.py` 新增：

1. `build_runtime()`：
   - 调 `setup_logging()`；
   - 创建 `PUBLIC_DIR/images`；
   - 调 `get_tracer()`；
   - 调 `get_result_enrichment_rule_service().refresh_rules()`；
   - 尝试创建 `get_asset_service()`，失败则记日志并返回 `None`；
2. 在 `app/ai/utils/observability.py` 增加最小 `flush_tracer()` helper：

```python
def flush_tracer() -> None:
    tracer = get_tracer()
    flush = getattr(tracer, "flush", None)
    if callable(flush):
        flush()
```

3. 在 `app/services/asset_service.py` 保持现有对外接口不变，只补最小的健康检查/初始化包装，不新增第二套 owner。

**Step 4: Run tests to verify they pass**

Run:
```bash
bash scripts/repo_python.sh
bash scripts/pytest_targeted.sh tests/unit/test_app_runtime.py tests/unit/test_app_runtime_bootstrap.py -q
```
Expected: PASS。

**Step 5: Checkpoint**

- 可选资源已和核心资源分层；
- 目录准备已脱离导入期副作用。

### Task 3: Move checkpointer and default graph warmup under runtime ownership

**Files:**
- Modify: `app/core/runtime.py`
- Modify: `app/main.py`
- Modify: `app/ai/workflow/multi_agent_graph.py`（如需补最小 cache clear helper）
- Create: `tests/unit/test_app_runtime_lifespan.py`
- Reuse: `tests/unit/test_postgres_checkpointer_pooling.py`

**Step 1: Write the failing tests**

新增 `tests/unit/test_app_runtime_lifespan.py`，覆盖：

1. `lifespan` 启动时会把 runtime 挂到 `app.state.runtime`；
2. `lifespan` 退出时会执行 `runtime.aclose()`；
3. `build_runtime()` 会初始化 checkpointer；
4. 默认图预热失败只降级，不阻断启动。

示例断言：

```python
async def test_lifespan_sets_runtime_on_app_state(monkeypatch):
    ...
    async with lifespan(app):
        assert app.state.runtime is runtime
```

**Step 2: Run tests to verify they fail**

Run:
```bash
bash scripts/repo_python.sh
bash scripts/pytest_targeted.sh tests/unit/test_app_runtime_lifespan.py tests/unit/test_postgres_checkpointer_pooling.py -q
```
Expected: FAIL，因为 `app/main.py` 还未切到 runtime owner。

**Step 3: Write minimal implementation**

1. 在 `build_runtime()` 中：
   - `await get_checkpointer()`；
   - 可选预热 `get_multi_agent_graph(enable_thinking=False, model_id=None)`；
   - 把 `close_checkpointer` 和 `flush_tracer` 注册到 `cleanup_callbacks`；
2. 改造 `app/main.py`：

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    runtime = await build_runtime()
    app.state.runtime = runtime
    try:
        yield
    finally:
        await runtime.aclose()
```

3. 删除 `app/main.py` 里已迁移的细碎初始化段，保留必要的配置 fail-fast 与路由装配。

**Step 4: Run tests to verify they pass**

Run:
```bash
bash scripts/repo_python.sh
bash scripts/pytest_targeted.sh tests/unit/test_app_runtime.py tests/unit/test_app_runtime_bootstrap.py tests/unit/test_app_runtime_lifespan.py tests/unit/test_postgres_checkpointer_pooling.py -q
```
Expected: PASS。

**Step 5: Checkpoint**

- `app.main` 已从“细节堆场”收敛为“启动编排入口”；
- checkpointer teardown 已通过 runtime 统一管理。

### Task 4: Delete duplicated outer-layer resource owners and keep service API stable

**Files:**
- Modify: `app/main.py`
- Modify: `app/services/metric_service.py`
- Modify: `app/db/session.py`（仅在 Phase 1 需要补最小 dispose helper 时修改）
- Test: `tests/unit/test_app_runtime_lifespan.py`
- Test: `app/tests/test_chat_assets.py`
- Test: `tests/unit/test_observability.py`

**Step 1: Write the failing cleanup assertions**

补断言或检查项，确保：

1. `app/main.py` 不再有导入期 `os.makedirs()`；
2. `MetricService` 不再新增新的 engine owner；
3. `AssetService` 既有接口仍可工作；
4. tracer 行为不回归。

**Step 2: Run focused tests to confirm failure or risk surface**

Run:
```bash
bash scripts/repo_python.sh
bash scripts/pytest_targeted.sh tests/unit/test_app_runtime_lifespan.py app/tests/test_chat_assets.py tests/unit/test_observability.py -q
```
Expected: 如果当前仍存在旧 owner 或导入期副作用，测试或断言失败。

**Step 3: Write minimal cleanup implementation**

1. 删除 `app/main.py` 中已迁移到 runtime 的启动细节；
2. 若 `MetricService` 仍需保留现有接口，仅允许改为依赖统一 engine，不得继续私有 `create_engine()`；
3. 不新增兼容层，不保留“临时双 owner”。

**Step 4: Re-run focused tests**

Run:
```bash
bash scripts/repo_python.sh
bash scripts/pytest_targeted.sh tests/unit/test_app_runtime.py tests/unit/test_app_runtime_bootstrap.py tests/unit/test_app_runtime_lifespan.py app/tests/test_chat_assets.py tests/unit/test_observability.py tests/unit/test_postgres_checkpointer_pooling.py -q
```
Expected: PASS。

**Step 5: Checkpoint**

- Phase 1 外层 owner 已收口；
- 旧调用面尽量不变，但 owner 已统一到 runtime。

### Task 5: Sync docs and record the long-term decision

**Files:**
- Modify: `docs/plans/2026-03-09-lifespan-runtime-consolidation-design.md`
- Modify: `memory-bank.md`

**Step 1: Update design with actual landed paths**

把实现后真实落地的文件路径、fail-fast / degrade 边界、未纳入本期的项原位更新回设计文档。

**Step 2: Update memory-bank entry**

确保 `memory-bank.md` 记录：

1. `lifespan` 只负责编排；
2. `app.state.runtime` 是应用级资源唯一 owner；
3. 请求态与用户态状态不进入 runtime。

**Step 3: Run targeted doc sanity check**

Run:
```bash
rg -n "app\.state\.runtime|lifespan 只负责编排|唯一 owner" docs/plans/2026-03-09-lifespan-runtime-consolidation-design.md memory-bank.md
```
Expected: 命中设计文档与记忆文件中的最终结论。

**Step 4: Final checkpoint**

- 记录 Phase 1 已完成的收口范围；
- 明确 Phase 2 再处理 DB owner 与缓存 registry，不在本期偷跑。
