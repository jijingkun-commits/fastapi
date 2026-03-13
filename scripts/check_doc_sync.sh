#!/usr/bin/env bash
# 文档同步检查脚本
# 用法：
#   scripts/check_doc_sync.sh --cached [--strict|--non-blocking]
#   scripts/check_doc_sync.sh --diff-range origin/master...HEAD [--strict|--non-blocking]

set -eo pipefail

MODE="cached"
DIFF_RANGE=""
STRICT_MODE="false"

usage() {
    cat <<'EOF'
用法:
  scripts/check_doc_sync.sh --cached [--strict|--non-blocking]
  scripts/check_doc_sync.sh --diff-range <base...head> [--strict|--non-blocking]
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
        --strict)
            STRICT_MODE="true"
            shift
            ;;
        --non-blocking)
            STRICT_MODE="false"
            shift
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

PYTHON_BIN="$(bash scripts/repo_python.sh)"

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
        if [[ "$STRICT_MODE" == "true" ]]; then
            echo "  文档同步检查失败（阻断）"
        else
            echo "  文档同步检查告警（允许继续）"
        fi
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
        echo "  - 新过程文档只应写入 workdocs/ 与 .artifacts/；docs/plans/、docs/内部参考/迭代需求/ 仅保留历史追溯"
        echo "  - 建议先执行 /jjk-doc-check 再提交"
        if [[ "$STRICT_MODE" != "true" ]]; then
            echo "  - 当前为非阻断模式：本次仅告警，不阻断提交"
        fi
        echo ""
        echo "========================================"
        echo ""
        if [[ "$STRICT_MODE" == "true" ]]; then
            exit 1
        fi
    fi

    if [[ ${#MISSING_DOCS[@]} -gt 0 && "$STRICT_MODE" != "true" ]]; then
        echo "文档映射检查完成（已提示告警）"
    else
        echo "文档映射检查通过"
        if [[ -n "${CHANGED_PROCESS_DOCS//$'
'/}" ]]; then
            echo "补充说明：检测到过程文档变更，但过程文档不会替代稳定真理源同步。"
            printf '%s
' "$CHANGED_PROCESS_DOCS" | sed 's/^/  - /'
        fi
    fi
fi

# 特殊处理（防屎山）强制同步检查：命中已登记文件时必须更新手册
CURRENT_STATE_DOCS="$(printf '%s\n' "$CHANGED_DOCS" | grep -E '^(docs/产品文档/|docs/开发文档/架构设计/|docs/API文档/)' | grep -v '^docs/开发文档/架构设计/防屎山记录手册\.md$' || true)"
if [[ -n "${CURRENT_STATE_DOCS//$'\n'/}" ]]; then
    CURRENT_STATE_DOC_ARRAY=()
    while IFS= read -r doc_path; do
        [[ -z "$doc_path" ]] && continue
        CURRENT_STATE_DOC_ARRAY+=("$doc_path")
    done <<EOF
$CURRENT_STATE_DOCS
EOF
    "$PYTHON_BIN" scripts/docs_guard.py --non-blocking --paths "${CURRENT_STATE_DOC_ARRAY[@]}"
fi

if [[ "$MODE" == "cached" ]]; then
    "$PYTHON_BIN" scripts/check_special_doc_sync.py --cached --strict
else
    "$PYTHON_BIN" scripts/check_special_doc_sync.py --diff-range "$DIFF_RANGE" --strict
fi

exit 0
