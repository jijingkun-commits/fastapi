#!/bin/bash
#
# 一键部署脚本
# 用法: ./deploy.sh [环境] [操作]
#
# 环境: dev | prod (默认: dev)
# 操作: init | migrate | start | stop | restart | status | logs
#
# 示例:
#   ./deploy.sh dev init      # 初始化开发环境
#   ./deploy.sh prod migrate  # 生产环境数据库迁移
#   ./deploy.sh dev start     # 启动开发环境
#

set -e

# ============================================================
# 配置
# ============================================================
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$SCRIPT_DIR"

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 日志函数
log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# ============================================================
# 参数解析
# ============================================================
ENV="${1:-dev}"
ACTION="${2:-help}"

if [[ "$ENV" != "dev" && "$ENV" != "prod" ]]; then
    log_error "无效的环境: $ENV (可选: dev | prod)"
    exit 1
fi

ENV_FILE=".env.${ENV}"
if [[ ! -f "$PROJECT_ROOT/$ENV_FILE" ]]; then
    if [[ -f "$PROJECT_ROOT/.env" ]]; then
        ENV_FILE=".env"
    else
        log_error "环境配置文件不存在: $ENV_FILE"
        exit 1
    fi
fi

log_info "使用环境: $ENV ($ENV_FILE)"

# 加载环境变量
set -a
source "$PROJECT_ROOT/$ENV_FILE"
set +a

# ============================================================
# 检查函数
# ============================================================
check_python() {
    if ! command -v python3 &> /dev/null; then
        log_error "Python3 未安装"
        exit 1
    fi
    log_info "Python: $(python3 --version)"
}

check_node() {
    if ! command -v node &> /dev/null; then
        log_warn "Node.js 未安装（前端功能不可用）"
        return 1
    fi
    log_info "Node.js: $(node --version)"
    return 0
}

check_postgres() {
    if ! python3 -c "from sqlalchemy import create_engine; e = create_engine('$DATABASE_URL'); e.connect()" 2>/dev/null; then
        log_error "无法连接 PostgreSQL: $DATABASE_URL"
        exit 1
    fi
    log_success "PostgreSQL 连接正常"
}

check_minio() {
    if [[ -z "$MINIO_ENDPOINT" ]]; then
        log_warn "MinIO 未配置"
        return 1
    fi
    # 简单检查端点是否可达
    if curl -s --connect-timeout 3 "$MINIO_ENDPOINT/minio/health/live" > /dev/null 2>&1; then
        log_success "MinIO 连接正常"
        return 0
    else
        log_warn "MinIO 不可达: $MINIO_ENDPOINT"
        return 1
    fi
}

check_ragflow() {
    if [[ -z "$RAGFLOW_BASE_URL" ]]; then
        log_warn "RAGFlow 未配置（知识库功能不可用）"
        return 1
    fi
    # 检查 RAGFlow API 是否可达
    if curl -s --connect-timeout 5 "$RAGFLOW_BASE_URL/api/v1/health" > /dev/null 2>&1; then
        log_success "RAGFlow 连接正常"
        return 0
    else
        log_warn "RAGFlow 不可达: $RAGFLOW_BASE_URL"
        return 1
    fi
}

# ============================================================
# 初始化函数
# ============================================================
init_database() {
    log_info "初始化数据库..."
    cd "$PROJECT_ROOT"
    
    # 1. 基础表结构
    log_info "  [1/6] 创建基础表结构..."
    python3 -c "
from sqlalchemy import create_engine, text
from app.core.config import DATABASE_URL

engine = create_engine(str(DATABASE_URL))
with engine.begin() as conn:
    # 启用扩展
    conn.execute(text('CREATE EXTENSION IF NOT EXISTS vector'))
    conn.execute(text('CREATE EXTENSION IF NOT EXISTS pg_trgm'))
print('扩展已启用')
"
    
    # 2. 执行 SQL 迁移
    log_info "  [2/6] 执行 SQL 迁移..."
    for sql_file in install/sql/init_postgres.sql; do
        if [[ -f "$sql_file" ]]; then
            log_info "    执行: $sql_file"
            python3 -c "
from sqlalchemy import create_engine, text
from app.core.config import DATABASE_URL
import sys

engine = create_engine(str(DATABASE_URL))
with open('$sql_file', 'r') as f:
    sql = f.read()
with engine.begin() as conn:
    for stmt in sql.split(';'):
        stmt = stmt.strip()
        if stmt and not stmt.startswith('--'):
            try:
                conn.execute(text(stmt))
            except Exception as e:
                if 'already exists' not in str(e):
                    print(f'警告: {e}', file=sys.stderr)
"
        fi
    done
    
    # 3. 增量迁移
    log_info "  [3/6] 执行增量迁移..."
    for sql_file in install/scripts/init_postgres.sql/*.sql; do
        if [[ -f "$sql_file" ]]; then
            log_info "    执行: $(basename $sql_file)"
            python3 -c "
from sqlalchemy import create_engine, text
from app.core.config import DATABASE_URL
import sys

engine = create_engine(str(DATABASE_URL))
with open('$sql_file', 'r') as f:
    sql = f.read()
with engine.begin() as conn:
    for stmt in sql.split(';'):
        stmt = stmt.strip()
        if stmt and not stmt.startswith('--'):
            try:
                conn.execute(text(stmt))
            except Exception as e:
                if 'already exists' not in str(e) and 'duplicate' not in str(e).lower():
                    print(f'警告: {e}', file=sys.stderr)
"
        fi
    done
    
    # 4. 初始化 LLM 配置
    log_info "  [4/6] 初始化 LLM 配置..."
    python3 scripts/init_llm_config.py 2>/dev/null || log_warn "LLM 配置初始化跳过"
    
    # 5. 初始化指标定义
    log_info "  [5/6] 初始化指标定义..."
    python3 scripts/init_metric_definition.py 2>/dev/null || true
    python3 scripts/expand_metrics.py 2>/dev/null || true
    
    # 6. 同步元数据
    log_info "  [6/6] 同步表元数据..."
    python3 scripts/schema_sync.py 2>/dev/null || log_warn "元数据同步跳过（可能缺少分析库）"
    
    log_success "数据库初始化完成"
}

init_minio() {
    log_info "初始化 MinIO..."
    cd "$PROJECT_ROOT"
    
    if [[ -f "install/scripts/init_minio_buckets.py" ]]; then
        python3 install/scripts/init_minio_buckets.py || log_warn "MinIO 初始化失败"
    fi
}

init_skills() {
    log_info "初始化 AI 技能..."
    cd "$PROJECT_ROOT"
    
    if [[ -f "scripts/import_skills.py" ]]; then
        python3 scripts/import_skills.py || log_warn "技能导入失败"
    fi
}

init_all() {
    log_info "========== 开始初始化 =========="
    
    # 检查环境
    check_python
    check_postgres
    check_minio || true
    check_ragflow || true
    
    # 初始化
    init_database
    init_minio || true
    init_skills || true
    
    log_success "========== 初始化完成 =========="
}

# ============================================================
# 数据库迁移
# ============================================================
migrate_database() {
    log_info "执行数据库迁移..."
    cd "$PROJECT_ROOT"
    
    check_postgres
    
    for sql_file in install/scripts/init_postgres.sql/*.sql; do
        if [[ -f "$sql_file" ]]; then
            log_info "执行: $(basename $sql_file)"
            python3 -c "
from sqlalchemy import create_engine, text
from app.core.config import DATABASE_URL
import sys

engine = create_engine(str(DATABASE_URL))
with open('$sql_file', 'r') as f:
    sql = f.read()
with engine.begin() as conn:
    for stmt in sql.split(';'):
        stmt = stmt.strip()
        if stmt and not stmt.startswith('--'):
            try:
                conn.execute(text(stmt))
            except Exception as e:
                if 'already exists' not in str(e) and 'duplicate' not in str(e).lower():
                    print(f'警告: {e}', file=sys.stderr)
"
        fi
    done
    
    log_success "数据库迁移完成"
}

# ============================================================
# 服务管理
# ============================================================
start_services() {
    log_info "启动服务..."
    cd "$PROJECT_ROOT"
    
    if [[ "$ENV" == "dev" ]]; then
        # 开发模式：前台启动
        log_info "开发模式：使用 uvicorn --reload"
        uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
    else
        # 生产模式：后台启动
        log_info "生产模式：后台启动"
        nohup uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4 > logs/uvicorn.log 2>&1 &
        echo $! > .pid
        log_success "后端已启动 (PID: $(cat .pid))"
    fi
}

stop_services() {
    log_info "停止服务..."
    
    if [[ -f "$PROJECT_ROOT/.pid" ]]; then
        PID=$(cat "$PROJECT_ROOT/.pid")
        if kill -0 $PID 2>/dev/null; then
            kill $PID
            rm "$PROJECT_ROOT/.pid"
            log_success "服务已停止 (PID: $PID)"
        else
            log_warn "服务未运行"
            rm "$PROJECT_ROOT/.pid"
        fi
    else
        log_warn "找不到 PID 文件"
    fi
}

restart_services() {
    stop_services
    sleep 2
    start_services
}

show_status() {
    log_info "服务状态:"
    
    # 后端状态
    if [[ -f "$PROJECT_ROOT/.pid" ]]; then
        PID=$(cat "$PROJECT_ROOT/.pid")
        if kill -0 $PID 2>/dev/null; then
            log_success "后端: 运行中 (PID: $PID)"
        else
            log_error "后端: 已停止 (PID 文件存在但进程不存在)"
        fi
    else
        log_warn "后端: 未启动"
    fi
    
    # 数据库状态
    check_postgres 2>/dev/null && log_success "PostgreSQL: 正常" || log_error "PostgreSQL: 不可达"
    
    # MinIO 状态
    check_minio 2>/dev/null && log_success "MinIO: 正常" || log_warn "MinIO: 不可达"
    
    # RAGFlow 状态
    check_ragflow 2>/dev/null && log_success "RAGFlow: 正常" || log_warn "RAGFlow: 不可达"
}

show_logs() {
    if [[ -f "$PROJECT_ROOT/logs/uvicorn.log" ]]; then
        tail -f "$PROJECT_ROOT/logs/uvicorn.log"
    else
        log_error "日志文件不存在"
    fi
}

# ============================================================
# 帮助信息
# ============================================================
show_help() {
    echo ""
    echo "用法: ./deploy.sh [环境] [操作]"
    echo ""
    echo "环境:"
    echo "  dev     开发环境 (默认)"
    echo "  prod    生产环境"
    echo ""
    echo "操作:"
    echo "  init      初始化环境（数据库、MinIO、技能）"
    echo "  migrate   仅执行数据库迁移"
    echo "  start     启动服务"
    echo "  stop      停止服务"
    echo "  restart   重启服务"
    echo "  status    查看服务状态"
    echo "  logs      查看日志"
    echo "  help      显示帮助"
    echo ""
    echo "示例:"
    echo "  ./deploy.sh dev init      # 初始化开发环境"
    echo "  ./deploy.sh prod migrate  # 生产环境数据库迁移"
    echo "  ./deploy.sh dev start     # 启动开发服务"
    echo ""
}

# ============================================================
# 主逻辑
# ============================================================
case "$ACTION" in
    init)
        init_all
        ;;
    migrate)
        migrate_database
        ;;
    start)
        start_services
        ;;
    stop)
        stop_services
        ;;
    restart)
        restart_services
        ;;
    status)
        show_status
        ;;
    logs)
        show_logs
        ;;
    help|--help|-h)
        show_help
        ;;
    *)
        log_error "未知操作: $ACTION"
        show_help
        exit 1
        ;;
esac
