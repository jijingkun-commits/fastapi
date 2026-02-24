---
description: 🚀 创建 Pull Request：自动生成 PR 描述、检查清单和标签
---

# 🚀 创建 Pull Request (Create PR)

创建结构良好的 Pull Request，包含完整描述、标签和审查者。

> **中文主导**: 无论是思考过程还是最终输出，**永远使用中文**。

## 步骤

### 1. 准备分支
```bash
# 确保所有变更已提交
git status

# 先同步基线分支（main 或 master）
git fetch origin main
# 若仓库默认分支为 master，请替换为 origin/master
git rebase origin/main  # 或 merge

# 再推送分支到远程；若此前已推送且发生 rebase，使用 --force-with-lease
git push -u origin HEAD
```

### 2. 分析变更
```bash
# 查看与基线分支（main 或 master）的差异
git log origin/main..HEAD --oneline
git diff origin/main...HEAD --stat
```

### 3. 生成 PR 描述

**PR 模板**:
```markdown
## 概述
[一句话描述本次变更的目的]

## 变更内容
- [ ] 功能 A
- [ ] 修复 B
- [ ] 重构 C

## 影响范围
- 模块: [受影响的模块]
- API: [新增/修改的接口]
- 数据库: [表结构变更]

## 测试
- [ ] 单元测试通过
- [ ] 集成测试通过
- [ ] 手动测试完成

## 截图（如有 UI 变更）
[添加截图]

## 关联 Issue
Closes #xxx
```

### 4. 创建 PR
```bash
# 使用 GitHub CLI
gh pr create --title "feat: 功能描述" --body "PR 描述"

# 添加标签
gh pr edit --add-label "enhancement"

# 指定审查者
gh pr edit --add-reviewer @username
```

## PR 检查清单

- [ ] 代码已自测通过
- [ ] 没有引入新的 lint 警告
- [ ] 相关文档已更新
- [ ] Breaking changes 已标注
- [ ] 敏感信息已清理（无 API key、密码等）

## 标签建议

| 标签 | 适用场景 |
|------|----------|
| `enhancement` | 新功能 |
| `bug` | Bug 修复 |
| `documentation` | 文档更新 |
| `refactor` | 重构 |
| `breaking-change` | 破坏性变更 |

---
*提示：使用 `/jjk-create-pr` 触发此工作流。*
