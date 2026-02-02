#!/bin/bash
# 文档同步检查脚本
# 检查代码变更是否有对应文档更新
# 仅警告模式，不阻断提交（避免过度约束）

set -e

# 获取暂存区中的代码文件变更
CHANGED_CODE=$(git diff --cached --name-only 2>/dev/null | grep -E '^(app/|web/src/)' || true)

# 获取暂存区中的文档变更
CHANGED_DOCS=$(git diff --cached --name-only 2>/dev/null | grep -E '^docs/' || true)

# 如果没有代码变更，直接退出
if [ -z "$CHANGED_CODE" ]; then
    exit 0
fi

# 如果有代码变更但没有文档变更，输出警告
if [ -n "$CHANGED_CODE" ] && [ -z "$CHANGED_DOCS" ]; then
    echo ""
    echo "========================================"
    echo "  文档同步检查"
    echo "========================================"
    echo ""
    echo "检测到代码变更但无文档更新，请确认是否需要同步文档"
    echo ""
    echo "变更的代码文件："
    echo "$CHANGED_CODE" | while read -r file; do
        echo "  - $file"
    done
    echo ""
    echo "提示："
    echo "  - 使用 /doc-check 命令查看详细映射"
    echo "  - 查阅 .cursor/rules/doc_sync.mdc 了解文档映射规则"
    echo ""
    echo "跳过条件（如满足可忽略此警告）："
    echo "  - 纯格式化/重构（不改功能）"
    echo "  - 简单 Bug 修复（不涉及设计）"
    echo ""
    echo "========================================"
    echo ""
fi

# 不阻断提交
exit 0
