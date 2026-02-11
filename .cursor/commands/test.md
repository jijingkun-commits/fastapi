---
description: 完整测试流程：环境准备 -> 用例生成 -> 执行验证 -> 报告产出
---

> 参考规则: @dual-database

# 测试执行脚本 (Test Execution Protocol)

执行完整的测试流程，包括用例生成、多层验证、报告产出。

> **中文主导**: 无论是思考过程（CoT）还是最终输出，**永远使用中文**。

## 何时使用

| 场景 | 推荐命令 |
|------|----------|
| 功能开发完成，需要完整测试 | `/test` ✅ |
| 代码写完，快速冒烟测试 | `/review` (包含快速自测) |
| 修复 Bug 后验证 | `/debug` (包含回归测试) |

---

## Step 0: 环境准备 (Environment Setup)

| 服务 | 端口 | 检查命令 |
|------|------|----------|
| 前端 (Next.js) | `3000` | `lsof -i :3000` |
| 后端 (FastAPI) | `8000` | `lsof -i :8000` |

```bash
# 仅检查服务状态，不自动启动
if ! lsof -i :8000 >/dev/null 2>&1; then
  echo "❌ 后端未启动：请先在新终端执行 uvicorn app.main:app --reload --port 8000"
  exit 1
fi

# 仅当本轮需要 E2E/UI 时再检查前端（RUN_E2E=1）
if [ "${RUN_E2E:-0}" = "1" ] && ! lsof -i :3000 >/dev/null 2>&1; then
  echo "❌ 前端未启动：请先在新终端执行 cd web && pnpm dev"
  exit 1
fi
```

**测试账号**: `jjk` / (空密码)


### Step 0.1: 在线测试硬门禁（禁止以 skip 代替）

执行在线 API/E2E 前，必须先确认后端服务可用；若不可用，`/test` 立即中断并提示用户手动启动服务，不允许用 `skip` 作为通过依据。

```bash
# 后端端口硬检查（未监听则立即失败）
if ! lsof -i :8000 >/dev/null 2>&1; then
  echo "❌ 后端未启动：请先执行 uvicorn app.main:app --reload --port 8000"
  exit 1
fi

# 健康检查（未就绪则立即失败）
curl -fsS http://127.0.0.1:8000/health >/dev/null
```

> 说明：若项目当前没有 `/health` 路由，可临时改为 `curl -fsS http://127.0.0.1:8000/docs >/dev/null`。


## Step 1: 锁定测试依据 (Acquire Context)

1. 明确测试模块：待办 / 聊天 / 管理后台 / 问数引擎
2. 阅读需求文档：
   - `docs/产品文档/<模块>需求.md`
   - `docs/内部参考/迭代需求/requirements.md`（迭代级概览）
3. 阅读测试案例文档：
   - `docs/开发文档/测试管理/<模块>测试案例.md`
4. 查看追溯矩阵：
   - `docs/开发文档/测试管理/测试用例库.md`
5. 若缺失，先补全需求/用例，再执行测试
6. 用例设计需结合银行工作场景（如分行、存贷、合规约束）

## Step 2: 生成测试矩阵 (Generate Test Cases)

遵循 **Arrange-Act-Assert** 模式：

```python
def test_example():
    # Arrange - 准备测试数据
    user = create_test_user()
    
    # Act - 执行被测操作
    result = service.do_something(user)
    
    # Assert - 验证结果
    assert result.success is True
```

**必须覆盖**:
1. **Happy Path**: 正常业务流
2. **Edge Cases**: 边界条件（空值、极限长度）
3. **Error Handling**: 异常场景（无效输入、权限不足）
4. **性能与稳定性**: 关键路径耗时、重试/超时场景

## Step 3: 执行与深度验证 (Execute & Verify)

**三重验证**:

| 层级 | 验证内容 | 工具 |
|------|----------|------|
| UI/API | 响应状态码、JSON 结构 | Playwright / curl |
| 数据层 | 数据是否正确持久化 | `postgres_query` |
| 系统层 | 日志无 ERROR | `grep -i "error" logs/assistant.log` |

**在线验证门禁规则**:
- 在线 API 与 E2E 测试前必须通过 Step 0.1 端口与健康检查。
- 检查未通过时必须立即中断并提示用户先启动服务（前端门禁仅在 RUN_E2E=1 时启用）。
- 因后端未启动导致的连接错误应记为 **FAIL**，不得记为 **SKIP**。

### Playwright E2E 测试（可视化优先）

```bash
cd web
npm test                         # 无界面运行（CI）
npm run test:visual              # 可视化慢速执行（推荐）
npm run test:ui                  # 交互式调试
npm run test:debug               # 断点/逐步调试
npx playwright test chat.spec.cjs # 单个测试
```


### Step 3.1: Gate 结果自动回填（并行拆解场景）

如果当前测试属于某一轮并行拆解 Gate（存在 `parallel_plan.md`），执行完门禁后必须自动回填：

```bash
# PARALLEL_PLAN_PATH 由执行者传入，例如：
# docs/内部参考/任务拆解/2026-02-09_待办隐式指代并行拆解/parallel_plan.md
venv/bin/python scripts/backfill_gate_status.py --plan "$PARALLEL_PLAN_PATH"
```

规则：
1. 不允许手工修改 Gate 数字结果。
2. 回填失败视为 Gate 未完成。
3. 非并行拆解场景可跳过本步骤。


## Step 4: 产出报告 (Final Report)

在 `docs/开发文档/测试管理/测试报告/` 产出报告：

1. 命名必须符合以下之一：
   - 主报告：`{模块名}测试报告.md`
   - 归档：`{模块名}测试报告_YYYYMMDD_{主题}.md`
   - 归档：`{模块名}测试报告_YYYY-MM-DD_{主题}.md`
2. 禁止新增兼容旧命名（如 `测试报告_{场景}_{日期}.md` 或仅日期无主题后缀）。
3. 报告正文至少包含：
   - **Executive Summary**: PASS / FAIL / WARN
   - **Defect List**: 问题列表（含日志片段）
   - **Trace Matrix**: 用例ID | UI结果 | DB结果 | 最终状态

示例：

- `待办助手测试报告.md`
- `问数引擎测试报告_20260210_全量执行.md`
- `用户管理测试报告_2026-02-10_自动化回归.md`

原有最低内容要求：
1. **Executive Summary**: PASS / FAIL / WARN
2. **Defect List**: 问题列表（含日志片段）
3. **Trace Matrix**: 用例ID | UI结果 | DB结果 | 最终状态

## Step 5: 沉淀资产 (Sediment Assets)

- 新用例补充到 `docs/开发文档/测试管理/<模块>测试案例.md`
- 更新 `docs/开发文档/测试管理/测试用例库.md` 的追溯矩阵
- 标记自动化覆盖状态（用例表中 ✅/⬜）

### 报告命名与索引同步清单（新增/重命名测试报告时必做）

- [ ] `docs/SUMMARY.md` 入口链接已同步
- [ ] `docs/开发文档/测试管理/测试用例库.md` “详细报告”链接已同步
- [ ] `docs/开发文档/测试管理/测试报告/README.md` 主报告/归档表已同步

### 脚本同步检查清单

**新增/修改 E2E 脚本时必须检查**:

- [ ] 脚本开头有 `@test-case TC-XXX-xx` 注释
- [ ] 脚本开头有 `@see docs/开发文档/测试管理/<模块>测试案例.md`
- [ ] 测试案例文档第 0 节"自动化覆盖"列已更新
- [ ] 脚本文件名与测试案例文档中的映射表一致

**示例**:

```javascript
/**
 * 待办多轮对话测试
 * 
 * @test-case TC-MULTI-01 信息补充对话
 * @test-case TC-MULTI-02 渐进式策略
 * @see docs/开发文档/测试管理/待办助手测试案例.md
 */
```

## Step 6: 文档同步 (Doc Sync)

如果测试中发现并修复了 Bug：
- [ ] API 变更 -> `docs/API文档/接口文档.md`
- [ ] 数据库变更 -> `docs/开发文档/架构设计/数据库设计.md`

---
*使用 `/test` 触发。适合在 `/review` 之后执行。*
