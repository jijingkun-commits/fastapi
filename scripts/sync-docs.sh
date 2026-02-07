#!/bin/bash
#
# 文档同步脚本：将 docs/ 目录推送到独立的 Gitee 公开仓库
#
# 用法:
#   ./scripts/sync-docs.sh              # 同步到文档仓库
#   ./scripts/sync-docs.sh --init       # 首次初始化（添加 remote）
#   ./scripts/sync-docs.sh --help       # 显示帮助
#
# 前置条件:
#   1. 在 Gitee 创建一个公开仓库（不要勾选初始化 README）
#   2. 运行 ./scripts/sync-docs.sh --init 添加 remote
#

set -e

# ============================================================
# 配置
# ============================================================
DOCS_PREFIX="docs"
DOCS_REMOTE="gitee-docs"
DOCS_BRANCH="master"
TEMP_BRANCH="docs-subtree-split"

# Gitee 文档仓库地址（修改为你的实际地址）
DOCS_REPO_URL="https://gitee.com/jijingkun/bojx-ai-docs.git"

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[OK]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# ============================================================
# 帮助信息
# ============================================================
show_help() {
    echo ""
    echo "文档同步脚本 - 将 docs/ 推送到独立的 Gitee 公开仓库"
    echo ""
    echo "用法:"
    echo "  ./scripts/sync-docs.sh              同步文档到公开仓库"
    echo "  ./scripts/sync-docs.sh --init       首次初始化（添加 remote）"
    echo "  ./scripts/sync-docs.sh --help       显示帮助"
    echo ""
    echo "首次使用步骤:"
    echo "  1. 在 Gitee 新建公开仓库: ${DOCS_REPO_URL}"
    echo "     (不要勾选 '使用 README 初始化仓库')"
    echo "  2. 运行: ./scripts/sync-docs.sh --init"
    echo "  3. 运行: ./scripts/sync-docs.sh"
    echo ""
    echo "后续每次同步只需运行:"
    echo "  ./scripts/sync-docs.sh"
    echo ""
}

# ============================================================
# 初始化
# ============================================================
init_remote() {
    log_info "初始化文档仓库 remote..."

    # 检查 remote 是否已存在
    if git remote | grep -q "^${DOCS_REMOTE}$"; then
        log_warn "Remote '${DOCS_REMOTE}' 已存在，更新 URL..."
        git remote set-url "${DOCS_REMOTE}" "${DOCS_REPO_URL}"
    else
        git remote add "${DOCS_REMOTE}" "${DOCS_REPO_URL}"
    fi

    log_success "Remote '${DOCS_REMOTE}' 已配置: ${DOCS_REPO_URL}"
    echo ""
    echo "验证:"
    git remote -v | grep "${DOCS_REMOTE}"
    echo ""
    log_info "现在可以运行 ./scripts/sync-docs.sh 同步文档"
}

# ============================================================
# 同步文档
# ============================================================
sync_docs() {
    # 检查 remote
    if ! git remote | grep -q "^${DOCS_REMOTE}$"; then
        log_error "Remote '${DOCS_REMOTE}' 不存在"
        echo ""
        echo "请先运行初始化:"
        echo "  ./scripts/sync-docs.sh --init"
        exit 1
    fi

    # 检查是否有未提交的变更
    if ! git diff --quiet -- "${DOCS_PREFIX}/"; then
        log_warn "docs/ 目录有未提交的变更，建议先提交"
        echo ""
        read -p "是否继续？(y/N) " -n 1 -r
        echo ""
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            exit 0
        fi
    fi

    log_info "正在拆分 ${DOCS_PREFIX}/ 目录的历史..."

    # 清理可能残留的临时分支
    git branch -D "${TEMP_BRANCH}" 2>/dev/null || true

    # 使用 git subtree split 将 docs/ 拆分为独立分支
    git subtree split --prefix="${DOCS_PREFIX}" -b "${TEMP_BRANCH}"

    log_info "正在推送到 ${DOCS_REMOTE}/${DOCS_BRANCH}..."

    # 推送到文档仓库
    git push "${DOCS_REMOTE}" "${TEMP_BRANCH}:${DOCS_BRANCH}" --force

    # 清理临时分支
    git branch -D "${TEMP_BRANCH}"

    log_success "文档同步完成!"
    echo ""
    log_info "公开文档仓库: ${DOCS_REPO_URL}"
}

# ============================================================
# 主逻辑
# ============================================================
case "${1:-sync}" in
    --init|-i)
        init_remote
        ;;
    --help|-h)
        show_help
        ;;
    sync|"")
        sync_docs
        ;;
    *)
        log_error "未知参数: $1"
        show_help
        exit 1
        ;;
esac
