#!/usr/bin/env bash
# 文档同步强校验脚本
# 用法：
#   scripts/check_doc_sync.sh --cached
#   scripts/check_doc_sync.sh --diff-range origin/master...HEAD

set -eo pipefail

MODE="cached"
DIFF_RANGE=""

usage() {
    cat <<'EOF'
用法:
  scripts/check_doc_sync.sh --cached
  scripts/check_doc_sync.sh --diff-range <base...head>
EOF
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --cached)
            MODE="cached"
            shift
            ;;
        --diff-range)
            MODE="diff-range"
            DIFF_RANGE="${2:-}"
            if [[ -z "$DIFF_RANGE" ]]; then
                echo "错误: --diff-range 缺少参数" >&2
                usage
                exit 2
            fi
            shift 2
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        *)
            echo "错误: 未知参数 $1" >&2
            usage
            exit 2
            ;;
    esac
done

if [[ "$MODE" == "cached" && -n "$DIFF_RANGE" ]]; then
    echo "错误: --cached 与 --diff-range 不能同时使用" >&2
    exit 2
fi

if [[ "$MODE" == "cached" ]]; then
    CHANGED_FILES="$(git -c core.quotepath=false diff --cached --name-only --diff-filter=ACMRTUXB || true)"
else
    CHANGED_FILES="$(git -c core.quotepath=false diff --name-only --diff-filter=ACMRTUXB "$DIFF_RANGE" || true)"
fi

if [[ -z "${CHANGED_FILES//$'\n'/}" ]]; then
    echo "无变更文件，跳过文档同步检查"
    exit 0
fi

CHANGED_CODE="$(printf '%s\n' "$CHANGED_FILES" | grep -E '^(app/|web/src/|\.cursor/commands/|\.env|install/|scripts/)' || true)"
CHANGED_DOCS="$(printf '%s\n' "$CHANGED_FILES" | grep -E '^docs/' || true)"

if [[ -z "${CHANGED_CODE//$'\n'/}" ]]; then
    echo "未检测到受文档映射约束的代码变更，跳过映射校验"
else
    declare -a REQUIRED_DOCS=()

    add_required_doc() {
        local doc="$1"
        local existing
        for existing in "${REQUIRED_DOCS[@]}"; do
            if [[ "$existing" == "$doc" ]]; then
                return
            fi
        done
        REQUIRED_DOCS+=("$doc")
    }

    has_code_match() {
        local regex="$1"
        printf '%s\n' "$CHANGED_CODE" | grep -qE "$regex"
    }

    # 设计文档映射
    has_code_match '^app/ai/(workflow|tools)/' && add_required_doc 'docs/开发文档/架构设计/AI模块设计.md'
    has_code_match '^app/api/' && add_required_doc 'docs/API文档/接口文档.md'
    has_code_match '^app/models/' && add_required_doc 'docs/开发文档/架构设计/数据库设计.md'
    has_code_match '^web/src/components/' && add_required_doc 'docs/开发文档/架构设计/前端架构.md'

    if has_code_match '^\.env'; then
        add_required_doc 'docs/开发文档/快速入门/配置说明.md'
        add_required_doc '.env.example'
    fi

    if has_code_match '^(app/core/config\.py|app/core/config_contract\.py|app/services/config_resolver\.py|install/scripts/init_system_config\.py|scripts/config_doctor\.py)$'; then
        add_required_doc 'docs/开发文档/快速入门/配置说明.md'
    fi

    if has_code_match '^\.cursor/commands/'; then
        add_required_doc 'docs/开发文档/工作流/开发工作流.md'
        add_required_doc 'docs/开发文档/技巧与速查/vibe-coding开发技巧.md'
        add_required_doc 'docs/开发文档/技巧与速查/AI协作速查表.md'
    fi

    # 需求文档映射（关键链路）
    if has_code_match '^(app/ai/|app/services/chat_service\.py|web/src/lib/backend\.ts|web/src/types/message\.ts|web/src/components/chat/)'; then
        add_required_doc 'docs/产品文档/聊天系统需求.md'
    fi

    if has_code_match '^(app/api/v1/endpoints/admin_overview_api\.py|app/api/v1/endpoints/data_admin_api\.py|app/api/v1/endpoints/memory_admin_api\.py|app/services/memory_admin_service\.py|app/services/overview_runtime_collector\.py|app/services/result_enrichment_rule_service\.py|web/src/components/admin/)'; then
        add_required_doc 'docs/产品文档/管理后台需求.md'
    fi

    declare -a MISSING_DOCS=()
    if [[ ${#REQUIRED_DOCS[@]} -gt 0 ]]; then
        local_doc=""
        for local_doc in "${REQUIRED_DOCS[@]}"; do
            if [[ "$local_doc" == ".env.example" ]]; then
                if ! printf '%s\n' "$CHANGED_CODE" | grep -qxF '.env.example'; then
                    MISSING_DOCS+=("$local_doc")
                fi
                continue
            fi

            if ! printf '%s\n' "$CHANGED_DOCS" | grep -qxF "$local_doc"; then
                MISSING_DOCS+=("$local_doc")
            fi
        done
    fi

    if [[ ${#MISSING_DOCS[@]} -gt 0 ]]; then
        echo ""
        echo "========================================"
        echo "  文档同步检查失败（阻断）"
        echo "========================================"
        echo ""
        echo "检测到以下代码变更："
        printf '%s\n' "$CHANGED_CODE" | sed 's/^/  - /'
        echo ""
        echo "本次必须同步但未改动的文档："
        printf '%s\n' "${MISSING_DOCS[@]}" | sed 's/^/  - /'
        echo ""
        echo "提示："
        echo "  - 文档映射规则见 .cursor/rules/doc_sync.mdc"
        echo "  - 建议先执行 /jjk-doc-check 再提交"
        echo ""
        echo "========================================"
        echo ""
        exit 1
    fi

    echo "文档映射检查通过"
fi

# 特殊处理（防屎山）强制同步检查：命中已登记文件时必须更新手册
if [[ "$MODE" == "cached" ]]; then
    python3 scripts/check_special_doc_sync.py --cached --strict
else
    python3 scripts/check_special_doc_sync.py --diff-range "$DIFF_RANGE" --strict
fi

exit 0
