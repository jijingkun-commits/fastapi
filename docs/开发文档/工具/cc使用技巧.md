# Claude Code 使用技巧

## 1. 状态栏：实时显示上下文用量

Claude Code 支持自定义状态栏，可以在终端底部实时显示模型、上下文占用、token 用量和费用。

### 配置步骤

**第一步：安装 jq（脚本依赖）**

```bash
brew install jq
```

**第二步：创建状态栏脚本 `~/.claude/statusline.sh`**

```bash
#!/bin/bash
read -r input

model=$(echo "$input" | jq -r '.model.display_name // .model.id // .model // "unknown"')
input_tokens=$(echo "$input" | jq -r '.context_window.current_usage.input_tokens // 0')
output_tokens=$(echo "$input" | jq -r '.context_window.current_usage.output_tokens // 0')
cache_creation=$(echo "$input" | jq -r '.context_window.current_usage.cache_creation_input_tokens // 0')
context_window=$(echo "$input" | jq -r '.context_window.context_window_size // 200000')
used_pct=$(echo "$input" | jq -r '.context_window.used_percentage // 0')
total_cost=$(echo "$input" | jq -r '.cost.total_cost_usd // 0')
total_input=$(echo "$input" | jq -r '.context_window.total_input_tokens // 0')
total_output=$(echo "$input" | jq -r '.context_window.total_output_tokens // 0')

cur_k=$(echo "scale=1; ($input_tokens + $output_tokens) / 1000" | bc)
window_k=$(echo "scale=0; $context_window / 1000" | bc)
total_in_k=$(echo "scale=1; $total_input / 1000" | bc)
total_out_k=$(echo "scale=1; $total_output / 1000" | bc)

bar_len=20
filled=$((used_pct * bar_len / 100))
empty=$((bar_len - filled))
bar=$(printf '%0.s█' $(seq 1 $filled 2>/dev/null))$(printf '%0.s░' $(seq 1 $empty 2>/dev/null))

printf "%s | [%s] %d%% (%sK/%sK) | total in: %sK out: %sK | \$%.4f" \
  "$model" "$bar" "$used_pct" "$cur_k" "$window_k" "$total_in_k" "$total_out_k" "$total_cost"
```

```bash
chmod +x ~/.claude/statusline.sh
```

**第三步：在 `~/.claude/settings.json` 中启用**

```json
{
  "statusLine": {
    "type": "command",
    "command": "cat | ~/.claude/statusline.sh"
  }
}
```

重新打开 Claude Code 会话即可在底部看到状态栏。

### 状态栏字段说明

| 字段 | 含义 |
|------|------|
| 模型名 | 当前使用的模型 |
| 进度条 + 百分比 | 当前轮上下文占用比例 |
| `(xK/200K)` | 当前轮 token / 上下文窗口大小 |
| `total in/out` | 本次会话累计输入/输出 token |
| `$x.xxxx` | 本次会话累计费用（USD） |

### 关于上下文窗口大小

Opus 4.6 模型支持最大 1M 上下文，但 Claude Code CLI 目前硬编码为 200K，暂无配置项可以修改。这是社区高频需求（GitHub issues #5644, #23714 等），等待官方支持。

当前建议：
- 上下文接近 80% 时主动执行 `/compact` 压缩
- Claude Code 在接近上限时也会自动压缩

---

## 2. 免确认执行：跳过权限提示

每次操作都要确认很烦，两种方式解决。

### 方式一：alias 快捷启动（简单粗暴）

在 `~/.zshrc` 中添加：

```bash
alias cc="claude --dangerously-skip-permissions"
```

然后 `source ~/.zshrc`，以后直接用 `cc` 启动。

### 方式二：permissions allowlist（更精细）

在 `~/.claude/settings.json` 中配置：

```json
{
  "permissions": {
    "allow": [
      "Bash(.*)",
      "Read",
      "Write",
      "Edit",
      "Glob",
      "Grep",
      "WebFetch",
      "WebSearch",
      "Task",
      "Skill",
      "NotebookEdit"
    ]
  }
}
```

可以按需缩小范围，比如 `Bash(git .*)` 只允许 git 命令。

---

## 3. 常用斜杠命令

| 命令 | 作用 |
|------|------|
| `/compact` | 压缩上下文，可加指令如 `/compact 聚焦 auth 模块` |
| `/clear` | 清空当前会话，从头开始 |
| `/resume` | 恢复上一次会话 |
| `/cost` | 查看当前会话 token 用量和费用 |
| `/model` | 切换模型 |
| `/memory` | 编辑 CLAUDE.md |
| `/init` | 为当前项目生成 CLAUDE.md |
| `/config` | 打开 settings.json |
| `/permissions` | 查看和修改工具权限 |
| `/doctor` | 诊断常见配置问题 |
| `/vim` | 切换 vim 键绑定 |

---

## 4. 快捷键

| 快捷键 | 作用 |
|--------|------|
| `Shift+Tab` | 切换 Plan 模式（先思考）和 Act 模式（直接执行） |
| `Ctrl+C` | 取消当前生成/工具执行 |
| `Ctrl+C` 连按两次 | 强制退出 |
| `Escape` | 中断当前响应，保留已有输出 |
| `↑` 方向键 | 翻阅历史输入 |
| `Ctrl+R` | 搜索历史输入 |
| `Ctrl+J` / `Enter` | 多行输入换行 |

---

## 5. CLI 启动参数

```bash
# 恢复上次会话
claude --resume

# 恢复指定会话
claude --resume SESSION_ID

# 继续上次会话并追加消息
claude --continue "加上测试"

# 单次模式，输出到 stdout
claude --print "解释这个错误" < error.log

# 管道组合
cat src/app.py | claude --print "review this code"
git diff | claude --print "写一个 commit message"

# 指定模型启动
claude --model claude-sonnet-4-20250514

# JSON 输出（适合脚本）
claude --print --output-format json "列出所有 TODO"

# 附加文件作为上下文
claude --file src/main.py --file README.md "解释架构"
```

---

## 6. CLAUDE.md：项目上下文

CLAUDE.md 会被自动加载为上下文，按层级生效：

| 文件位置 | 作用域 |
|----------|--------|
| `~/CLAUDE.md` | 全局，所有项目 |
| `./CLAUDE.md` | 项目根目录 |
| `.claude/CLAUDE.md` | 项目（替代位置） |
| `./src/CLAUDE.md` | 子目录级别，引用该目录文件时加载 |

建议写入内容：
- 构建/测试/lint 命令
- 架构概览和关键约定
- 文件命名规范
- 禁止事项（如"不要直接修改 migration 文件"）

---

## 7. 会话管理

- 每次新开终端是全新会话，不会继承之前的上下文
- `claude --resume` 恢复最近一次会话
- 历史对话存储在 `~/.claude/projects/` 下，不影响性能
- 清理磁盘空间：`du -sh ~/.claude/projects/` 查看占用，按需删除
- 长会话中用 `/compact` 主动压缩，切换无关任务时用 `/clear`

---

## 8. Hook 系统

在 `.claude/settings.json` 中配置自动化钩子：

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Edit|Write",
        "command": "python lint_check.py $CLAUDE_FILE_PATH"
      }
    ],
    "PostToolUse": [
      {
        "matcher": "Bash",
        "command": "/path/to/log_commands.sh"
      }
    ],
    "Notification": [
      {
        "matcher": "",
        "command": "terminal-notifier -message 'Claude 需要你的注意'"
      }
    ]
  }
}
```

| Hook 类型 | 触发时机 |
|-----------|----------|
| `PreToolUse` | 工具执行前，返回非零退出码可阻止执行 |
| `PostToolUse` | 工具执行后 |
| `Notification` | Claude 需要你关注时 |
| `Stop` | Claude 完成一轮回复时 |

---

## 9. 进阶技巧

- `Shift+Tab` 进入 Plan 模式让 Claude 先规划再动手，适合复杂任务
- Claude 陷入循环时按 `Escape` 中断，然后用更具体的提示重新引导
- 项目级 `.claude/settings.json`（提交到 git）用于团队共享配置，`~/.claude/settings.json` 用于个人偏好
- CI/CD 中组合 `--dangerously-skip-permissions` + `--print` 实现全自动化
