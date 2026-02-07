#!/bin/bash
# 双仓库同步脚本
# 用法: ./scripts/sync-repos.sh [branch]
# 默认分支: main

set -e

BRANCH="${1:-main}"

# 颜色输出
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[OK]${NC} $1"; }

log_info "开始同步代码到双仓库..."
log_info "分支: $BRANCH"
echo ""

# 1. Gitee (Origin)
log_info "推送到 Gitee (origin)..."
git push origin "$BRANCH"
log_success "Gitee 推送完成"
echo ""

# 2. GitHub
if git remote | grep -q "github"; then
    log_info "推送到 GitHub (触发 CI)..."
    git push github "$BRANCH"
    log_success "GitHub 推送完成"
else
    echo "⚠️  未检测到 github remote，跳过 GitHub 推送"
fi

echo ""
log_success "全部同步完成!"
