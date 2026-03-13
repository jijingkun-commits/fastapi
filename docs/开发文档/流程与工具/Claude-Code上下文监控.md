# Claude Code 上下文监控工具

## 问题背景

Claude Code CLI 不显示实时 token 使用情况，容易导致：
- 上下文过长，LLM 注意力分散
- 触发自动压缩（context pruning）
- 超出 1M token 限制

## 解决方案

提供两个工具帮助你监控上下文使用情况：

### 方案 1：快速估算脚本（推荐）

**使用方法**：
```bash
./scripts/cc_token_counter.sh
```

**功能**：
- 输入当前对话轮次
- 自动估算 token 使用量
- 显示可视化进度条
- 给出操作建议

**示例输出**：
```
📊 Claude Code 上下文估算
======================================
状态: 🟢 安全
对话轮次: 15 轮
估算 Token: 100,000 / 1,000,000
使用率: 10%
剩余空间: 900,000 tokens

[█████░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░] 10%

💡 建议:
  - 上下文使用正常，可以继续
======================================
```

### 方案 2：Python 监控脚本（高级）

**安装依赖**：
```bash
pip install tiktoken
```

**使用方法**：
```bash
# 单次检查
python scripts/cc_context_monitor.py --once

# 持续监控（每 5 秒刷新）
python scripts/cc_context_monitor.py --interval 5
```

**功能**：
- 自动查找 Claude Code 会话文件
- 精确计算 token 使用量
- 实时监控模式
- 详细的使用建议

## Token 使用阈值

| 使用量 | 状态 | 建议 |
|--------|------|------|
| < 600K | 🟢 安全 | 正常使用 |
| 600K - 800K | 🟡 警告 | 考虑完成当前任务后开新会话 |
| > 800K | 🔴 危险 | 立即开新会话，保存关键决策 |

## 估算规则

**快速估算**（bash 脚本）：
- 系统提示词：~25K tokens
- 每轮对话（问+答）：~5K tokens
- 总计 = 25K + (轮次 × 5K)

**精确计算**（Python 脚本）：
- 使用 tiktoken 库（GPT-4 tokenizer）
- 实际分析会话文件内容
- 误差 < 10%

## 最佳实践

1. **按任务分会话**：
   - 一个功能模块 = 一个会话
   - 完成后仅把仓库级长期活跃决策摘要写入 `memory-bank.md`
   - 需要完整解释背景/决策/后果时，把 ADR 正文写入 `docs/内部参考/决策记录.md`

2. **定期检查**：
   - 每 10-15 轮对话检查一次
   - 粘贴大量代码后立即检查

3. **主动管理**：
   - 超过 50 轮对话考虑开新会话
   - 话题切换时开新会话

4. **利用项目记忆**：
   - 架构决策 → `docs/开发文档/架构设计/`
   - 决策正文 → `docs/内部参考/决策记录.md`
   - 跨任务活跃决策索引 → `memory-bank.md`
   - 需求变更 → `workdocs/需求/`
   - 不要让 LLM 重复回答已文档化的内容

5. **搜索先收窄**：
   - 默认使用 `rg`，并遵守仓库根 `.rgignore`：自动排除 `workdocs/归档/`、`docs/内部参考/决策归档/`、`.worktrees/`、`web/playwright-report/`、`web/output/`、图片和锁文件等噪音路径
   - 先命中，再小窗口读取：优先 `sed -n '80,180p' <file>` 这类 80~200 行窗口，不要为了“先了解一下”直接整篇打开
   - 只有在明确追历史方案、报告、截图或生成产物时，才显式指定这些路径

6. **规则入口按消费端收敛**：
   - Codex 运行时命中项目工作流/技能，默认先读 `.agents/skills/*/SKILL.md`
   - `.cursor/commands/*.md` 保留给“维护命令定义、查 skill 镜像漂移、同步链治理”场景，不要在普通执行任务里双读
   - 根 `AGENTS.md` 负责路由，`.cursor/rules/*.mdc` 负责技术细则，`PLANS.md` 只在长流程阶段再展开

## 推荐搜索姿势

```bash
# 先在当前真理源和代码 owner 中命中
rg -n "display_blocks|ordered content blocks" docs app web

# 命中某个工作流时，Codex 先读 skill 入口
rg -n "jjk-verify|jjk-design" .agents/skills

# 再按窗口读取，不整篇吞
sed -n '60,180p' docs/API文档/接口文档_聊天与流式协议.md

# 只有维护命令定义或查镜像漂移时，才去看命令真理源
rg -n "jjk-verify" .cursor/commands

# 只有明确追历史时，才显式点名归档路径
rg -n "cardrun-wtflow" workdocs/归档/正文/设计
```

## 识别压缩信号

如果出现以下情况，说明已触发自动压缩：
- LLM 开始"忘记"之前讨论的内容
- 回复变得不连贯或重复
- 引用之前的代码时出现错误

**解决方法**：立即开启新会话，并在开头引用相关文档。

## 快速命令

```bash
# 添加到 ~/.zshrc 或 ~/.bashrc
alias cctoken='cd /Users/jijingkun/bojxAI/fastapi && ./scripts/cc_token_counter.sh'
```

然后在任何目录下直接运行：
```bash
cctoken
```
