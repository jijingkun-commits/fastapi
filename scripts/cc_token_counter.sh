#!/bin/bash
# Claude Code Token 计数器（简化版）
# 通过估算当前会话的字符数来推算 token 使用情况

# 配置
MAX_TOKENS=1000000
SYSTEM_TOKENS=25000
WARNING_THRESHOLD=600000
DANGER_THRESHOLD=800000

# 颜色
RED='\033[0;31m'
YELLOW='\033[1;33m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 估算 token（粗略：1 token ≈ 4 字符）
estimate_tokens() {
    local char_count=$1
    echo $(( char_count / 4 + SYSTEM_TOKENS ))
}

# 显示进度条
show_progress() {
    local current=$1
    local max=$2
    local width=50
    local percent=$(( current * 100 / max ))
    local filled=$(( width * current / max ))

    printf "["
    for ((i=0; i<filled; i++)); do printf "█"; done
    for ((i=filled; i<width; i++)); do printf "░"; done
    printf "] %d%%\n" "$percent"
}

# 获取状态
get_status() {
    local tokens=$1
    if [ $tokens -ge $DANGER_THRESHOLD ]; then
        echo -e "${RED}🔴 危险：即将触发压缩${NC}"
    elif [ $tokens -ge $WARNING_THRESHOLD ]; then
        echo -e "${YELLOW}🟡 警告：上下文较长${NC}"
    else
        echo -e "${GREEN}🟢 安全${NC}"
    fi
}

# 主函数
main() {
    echo -e "${BLUE}📊 Claude Code 上下文估算${NC}"
    echo "======================================"

    # 方法1：从剪贴板估算（如果你复制了整个对话）
    if command -v pbpaste &> /dev/null; then
        echo "提示：复制整个对话窗口内容后运行此脚本"
        echo "或者手动输入对话轮次..."
        echo ""
    fi

    # 方法2：手动输入轮次
    read -p "请输入当前对话轮次（问+答算1轮）: " rounds

    if [[ ! "$rounds" =~ ^[0-9]+$ ]]; then
        echo "❌ 请输入有效数字"
        exit 1
    fi

    # 估算（每轮平均 5000 tokens）
    avg_tokens_per_round=5000
    estimated_tokens=$(( rounds * avg_tokens_per_round + SYSTEM_TOKENS ))

    remaining=$(( MAX_TOKENS - estimated_tokens ))
    percent=$(( estimated_tokens * 100 / MAX_TOKENS ))

    echo ""
    echo "状态: $(get_status $estimated_tokens)"
    echo "对话轮次: $rounds 轮"
    echo "估算 Token: $(printf "%'d" $estimated_tokens) / $(printf "%'d" $MAX_TOKENS)"
    echo "使用率: ${percent}%"
    echo "剩余空间: $(printf "%'d" $remaining) tokens"
    echo ""

    show_progress $estimated_tokens $MAX_TOKENS

    echo ""
    echo "💡 建议:"
    if [ $estimated_tokens -ge $DANGER_THRESHOLD ]; then
        echo "  - ⚠️  立即开启新会话"
        echo "  - 保存关键决策到 memory-bank.md"
    elif [ $estimated_tokens -ge $WARNING_THRESHOLD ]; then
        echo "  - 考虑在完成当前任务后开启新会话"
        echo "  - 避免粘贴大量代码"
    else
        echo "  - 上下文使用正常，可以继续"
    fi
    echo "======================================"
}

main
