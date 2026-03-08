# Async 单元测试支持补齐设计

> **文档类型**: 设计说明
> **创建日期**: 2026-03-07
> **更新日期**: 2026-03-07
> **问题范围**: `tests/unit`, `pyproject.toml`, `requirements.txt`
> **目标**: 消除仓内 async 单元测试因测试运行时缺失而产生的 `skipped`

---

## 1. 结论先行

当前 `tests/unit` 中剩余的 `6 skipped`，根因不是业务代码错误，而是 **pytest 缺少 async 执行插件**，导致：

1. `@pytest.mark.asyncio` 未被识别；
2. `async def test_*` 被 pytest 当作“无法原生执行的协程测试”直接跳过；
3. 仓库看似全绿，实际 async 子域没有进入真实验证。

本轮采用的唯一修复方向是：

- **把 `pytest-asyncio` 提升为仓库级测试依赖契约**；
- 保持业务代码零侵入；
- 让 async 测试在标准 `pytest` 流程中被真实收集、真实执行、真实计入结果。

---

## 2. 根因矩阵

| 层 | 现象 | 根因 | 是否应改业务代码 |
| - | - | - | - |
| 测试发现层 | `Unknown pytest.mark.asyncio` warning | pytest 未加载 async 插件 | 否 |
| 测试执行层 | `PytestUnhandledCoroutineWarning` + skipped | 原生 pytest 不执行 `async def` 测试 | 否 |
| 仓库契约层 | `requirements` / `dev extras` 未声明 async 测试依赖 | 测试环境不完整 | 否 |
| 业务实现层 | `chat_service`, `streaming helpers` 已有测试 | 业务代码本身不是这 6 个 skipped 的根因 | 否 |

---

## 3. 设计决策

### 3.1 采纳方案

1. 在 `pyproject.toml` 的 `project.optional-dependencies.dev` 中补充 `pytest-asyncio`；
2. 在 `requirements.txt` 中同步补充 `pytest-asyncio`；
3. 不引入自定义 `conftest` 协程执行器，不复制第三方插件行为；
4. 用最小 focused 回归 + `tests/unit` 全量回归验证。
5. 在 `pytest` 配置中显式声明 `asyncio_default_fixture_loop_scope = "function"`，避免第三方插件未来默认值变化造成测试语义漂移。

### 3.2 不采纳方案

| 方案 | 不采纳原因 |
| - | - |
| 自写 `conftest.py` 执行 async 测试 | 重复造轮子，增加维护面，且与 pytest 生态脱节 |
| 仅在本机手工安装插件，不改仓库依赖 | 只能修复当前机器，无法形成可传递契约 |
| 修改测试为同步包装器 | 扭曲测试原语，掩盖真实异步行为 |

---

## 4. Definition of Done

满足以下条件才算完成：

1. `tests/unit/test_llm_list_content_guard.py` 与 `tests/unit/test_multi_agent_streaming_helpers.py` 中 async 用例不再 skipped；
2. `tests/unit` 全量回归退出码为 `0`；
3. `requirements.txt` 与 `pyproject.toml` 对 async 测试依赖保持一致；
4. 结论可由机器复现，而不是依赖本机口头说明。
