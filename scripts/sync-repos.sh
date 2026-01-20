#!/bin/bash
# GitHub CI 测试推送脚本
# 用法: ./scripts/sync-repos.sh [branch]
# 默认分支: main
#
# 说明：只推送到 GitHub 触发 CI 测试，Gitee 需要手动操作

set -e

BRANCH="${1:-main}"

echo "🧪 推送到 GitHub 触发 CI 测试..."
echo "分支: $BRANCH"
echo ""

# 检查 GitHub remote 是否存在
if ! git remote | grep -q "github"; then
    echo "❌ 错误: GitHub remote 未配置"
    echo ""
    echo "请先运行以下命令添加 GitHub remote:"
    echo "  git remote add github https://github.com/你的用户名/fastapi.git"
    exit 1
fi

# 推送到 GitHub
echo "📤 推送到 GitHub..."
git push github "$BRANCH"

echo ""
echo "✅ 推送完成! 请到 GitHub Actions 页面查看 CI 状态"
echo ""
echo "💡 提示: 如需同时推送到 Gitee，请手动执行:"
echo "   git push origin $BRANCH"
