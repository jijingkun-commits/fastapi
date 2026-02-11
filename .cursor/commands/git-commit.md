---
description: 📝 规范化 Git 提交：生成简洁、符合规范的 commit message
---

# 📝 Git 规范化提交 (Git Commit)

创建简洁、规范的 commit message 并提交暂存的更改。

> **中文主导**: 无论是思考过程还是最终输出，**永远使用中文**。

## 步骤

### 1. 审查变更
```bash
# 查看已暂存的变更
git diff --cached

# 查看未暂存的变更
git diff
```
- 理解变更内容和原因

### 2. 检查关联 Issue（可选）
- 检查分支名是否包含 issue key（如 `feature/PROJ-123`）
- 如无 issue key，询问用户是否需要关联

### 3. 暂存变更（如未暂存）
```bash
git add -A
```

### 4. 创建 Commit Message

**格式模板**:
```
<type>(<scope>): <简短描述>

[可选的详细说明]

[可选: Refs #issue-number]
```

**带 Issue Key**:
```
PROJ-123: <type>(<scope>): <简短描述>
```

## 规则

| 规则 | 说明 | 示例 |
|------|------|------|
| **长度** | ≤ 72 字符 | ✅ |
| **语气** | 使用祈使句 | fix, add, update（不是 fixed, added） |
| **首字母** | 小写 | `fix: 修复登录问题` |
| **结尾** | 不加句号 | `feat: 添加用户认证` |
| **描述** | 说明为什么，而非仅仅是什么 | ❌ `fix stuff` → ✅ `fix: 修复 token 过期未刷新` |

## Type 类型

| Type | 说明 |
|------|------|
| `feat` | 新功能 |
| `fix` | Bug 修复 |
| `docs` | 文档更新 |
| `style` | 代码格式（不影响逻辑） |
| `refactor` | 重构（非新功能、非修复） |
| `perf` | 性能优化 |
| `test` | 测试相关 |
| `chore` | 构建/工具链变更 |

## 示例

```bash
# 功能
git commit -m "feat(auth): 添加 JWT 刷新机制"

# 修复
git commit -m "fix(chat): 修复消息重复保存问题"

# 文档
git commit -m "docs: 更新 API 接口文档"

# 带 Issue
git commit -m "PROJ-123: fix(api): 修复空指针异常"
```

---
*提示：使用 `/git-commit` 触发此工作流。*
