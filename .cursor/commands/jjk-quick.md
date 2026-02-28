---
description: 快速任务：跳过规划直接执行小改动
---

> 参考规则: @dual-database

# 快速任务工作流 (Quick Task)

小改动直接执行，跳过完整的规划-实现-审查链路。

> **中文主导**: 无论是思考过程（CoT）还是最终输出，**永远使用中文**。

## 何时使用

| 场景 | 推荐命令 |
|------|----------|
| 修个 typo、加个日志、调个配置 | `/jjk-quick` ✅ |
| 小 Bug 修复（根因明确） | `/jjk-quick` ✅ |
| 小范围重构（单文件内） | `/jjk-quick` ✅ |
| 需要规划的功能开发 | `/jjk-plan` -> `/jjk-imp` |
| 需要深度排查的 Bug | `/jjk-debug` |

> **边界判断**: 改动预计 <= 3 个文件且不涉及架构变更时用 `/jjk-quick`，否则走正式流程。

---

## 执行流程

### 1. 任务确认 (Validate)

快速确认任务范围：
- 理解用户意图
- 预估影响文件数
- 若影响 > 3 个文件或涉及架构变更，建议转 `/jjk-plan`

### 2. 直接执行 (Execute)

无需产出 requirements 或 implementation_plan，直接编码：

1. 阅读相关代码，理解上下文
2. 实施改动
3. 遵循项目规范（中文注释、类型提示、snake_case）

**禁止事项**:
- 禁止"顺手"重构不相关的代码
- 禁止修改高风险文件（`agent_prompts.py`、`state.py`、`*_graph.py`）
- 禁止新增数据库表或 API 端点（这些需要走正式流程）

### 3. 最小验证 (Minimal Verify)

根据改动类型选择最小验证：

| 改动类型 | 验证方式 |
|---------|---------|
| Python 代码 | `python -m pytest tests/unit/<相关测试> -v --tb=short` |
| TypeScript 代码 | `cd web && npx tsc --noEmit` |
| 配置文件 | 确认服务能启动 |
| 文档/注释 | 无需验证 |

若无现成测试覆盖，不强制补测试（区别于正式流程）。

### 4. 文档同步 (Doc Sync，按需)

仅在以下情况同步文档：
- API 行为变更 -> `docs/API文档/接口文档.md`
- 配置项变更 -> `docs/开发文档/快速入门/配置说明.md`

纯代码修复、日志调整、typo 修正无需同步文档。

### 5. 交付 (Deliver)

用 1-3 句话总结改动：

```markdown
修改了 `app/services/chat_service.py` 中的日志级别，
将 DEBUG 改为 INFO 避免生产环境日志过多。已通过相关单元测试。
```

若用户需要提交，建议使用 `/jjk-git-commit`。

---

## 与 GSD quick 的差异

| 维度 | GSD quick | jjk-quick |
|------|----------|-----------|
| 状态追踪 | 更新 STATE.md | 无额外状态文件 |
| 子 agent | 生成 planner + executor | 不委托，直接执行 |
| Git 集成 | 自动原子 commit | 建议手动 commit |
| 验证 | 可选 `--full` 启用验证 | 默认最小验证 |

设计理念：保持极简，不为小任务引入额外开销。

---
*使用 `/jjk-quick` 触发。适合 3 个文件以内的小改动。*
