#!/bin/bash
# Claude Code 状态栏（显示累计消耗 + 当前窗口使用率）

set -euo pipefail

# 颜色
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
CYAN='\033[0;36m'
GRAY='\033[0;90m'
NC='\033[0m'

# 读取 stdin 的 JSON 数据
json_data=$(cat)

# 如果没有数据，显示默认信息
if [[ -z "$json_data" ]]; then
    echo "[Claude Code]"
    exit 0
fi

# 解析 JSON 数据
model_name=$(echo "$json_data" | jq -r '.model.display_name // "Claude"' 2>/dev/null || echo "Claude")

# 当前上下文窗口使用量
current_input=$(echo "$json_data" | jq -r '.context_window.current_usage.input_tokens // 0' 2>/dev/null || echo "0")
current_output=$(echo "$json_data" | jq -r '.context_window.current_usage.output_tokens // 0' 2>/dev/null || echo "0")
current_tokens=$((current_input + current_output))

# 累计消耗（整个会话）
total_input=$(echo "$json_data" | jq -r '.context_window.total_input_tokens // 0' 2>/dev/null || echo "0")
total_output=$(echo "$json_data" | jq -r '.context_window.total_output_tokens // 0' 2>/dev/null || echo "0")
total_tokens=$((total_input + total_output))

# 上下文窗口大小（使用 CC 的实际限制 200k）
CC_ACTUAL_LIMIT=200000
context_size=$CC_ACTUAL_LIMIT

# 重新计算真实使用率（基于 200k 限制）
if [[ $context_size -gt 0 ]]; then
    used_percent=$((current_tokens * 100 / context_size))
else
    used_percent=0
fi

# 工作区信息
current_dir=$(echo "$json_data" | jq -r '.workspace.current_dir // ""' 2>/dev/null)
project_dir=$(echo "$json_data" | jq -r '.workspace.project_dir // ""' 2>/dev/null)

# 检测是否在 worktree 中，并获取主项目名称
get_project_and_worktree() {
    if [[ -z "$current_dir" ]]; then
        echo "unknown||"
        return
    fi

    # 尝试从 git 获取信息
    if [[ -e "$current_dir/.git" ]]; then
        local git_dir=$(cd "$current_dir" 2>/dev/null && git rev-parse --git-dir 2>/dev/null)

        # 检查是否是 worktree（git-dir 包含 .git/worktrees/）
        if [[ "$git_dir" == *"/.git/worktrees/"* ]]; then
            # 提取主仓库路径
            local main_repo=$(echo "$git_dir" | sed 's|/.git/worktrees/.*||')
            local project=$(basename "$main_repo")
            local worktree=$(basename "$current_dir")
            echo "${project}|${worktree}"
            return
        fi
    fi

    # 普通仓库
    local project=$(basename "$current_dir")
    echo "${project}|"
}

# 获取当前 Git 分支
get_git_branch() {
    if [[ -n "$current_dir" && -e "$current_dir/.git" ]]; then
        (cd "$current_dir" && git branch --show-current 2>/dev/null) || echo ""
    else
        echo ""
    fi
}

project_and_worktree=$(get_project_and_worktree)
project_name=$(echo "$project_and_worktree" | cut -d'|' -f1)
worktree_dir=$(echo "$project_and_worktree" | cut -d'|' -f2)
git_branch=$(get_git_branch)

# 生成进度条（基于当前窗口使用率）
width=10
filled=$((width * used_percent / 100))
[[ $filled -gt $width ]] && filled=$width

bar=""
for ((i=0; i<filled; i++)); do bar+="█"; done
for ((i=filled; i<width; i++)); do bar+="░"; done

# 选择颜色
color="$GREEN"
[[ $used_percent -ge 60 ]] && color="$YELLOW"
[[ $used_percent -ge 80 ]] && color="$RED"

# 格式化数字
format_number() {
    printf "%'d" "$1" 2>/dev/null || echo "$1"
}

current_fmt=$(format_number "$current_tokens")
context_fmt=$(format_number "$context_size")
total_fmt=$(format_number "$total_tokens")

# 构建显示文本
build_location_text() {
    local text="$project_name"

    # 如果在 worktree 中，显示 worktree 目录
    if [[ -n "$worktree_dir" ]]; then
        text="${text}/${GRAY}${worktree_dir}${NC}"
    fi

    # 显示分支
    if [[ -n "$git_branch" ]]; then
        text="${text} ${GRAY}(${git_branch})${NC}"
    fi

    echo -e "$text"
}

location_text=$(build_location_text)

# 输出状态栏（两行）
# 第一行：当前窗口使用率 + 项目/分支/worktree
echo -e "[${CYAN}${model_name}${NC}] ${color}${bar}${NC} ${used_percent}% | ${location_text}"
# 第二行：详细统计
echo -e "${GRAY}Window: ${current_fmt}/${context_fmt} | Total: ${total_fmt}${NC}"
