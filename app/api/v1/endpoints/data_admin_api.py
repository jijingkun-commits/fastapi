"""问数 Agent 管理 API（中文注释）。

提供：
- 查询日志管理
- SQL 修正与反馈
- 训练数据管理
- 指标管理
"""
import logging
from typing import Any, Dict, List, Optional, Tuple
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import text
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field

from app.db.session import get_db
from app.models.data_agent_metadata import DataQueryLog, Metric, MetaTable
from app.models.result_enrichment_rule import ResultEnrichmentRule
from app.models.user import User
from app.repositories.result_enrichment_rule_repo import ResultEnrichmentRuleRepo
from app.services.result_enrichment_rule_service import (
    ResultLookupEnrichmentRuleConfig,
    apply_lookup_enrichment_rule,
    get_result_enrichment_rule_service,
)
from app.api.deps import get_admin_user

logger = logging.getLogger(__name__)

_rule_repo = ResultEnrichmentRuleRepo()
_rule_service = get_result_enrichment_rule_service()

router = APIRouter(prefix="/data-admin", tags=["问数管理"])


# ==================== Schemas ====================

class QueryLogResponse(BaseModel):
    """查询日志响应。"""
    id: int
    user_id: Optional[int]
    thread_id: Optional[str]
    question: str
    generated_sql: Optional[str]
    sql_source: Optional[str]
    is_correct: Optional[bool]
    corrected_sql: Optional[str]
    trained: bool
    is_ignored: bool
    created_at: str
    
    class Config:
        from_attributes = True


class SQLCorrectionRequest(BaseModel):
    """SQL 修正请求。"""
    log_id: int
    corrected_sql: str
    is_correct: bool = True


class TrainRequest(BaseModel):
    """训练请求。"""
    log_ids: List[int]


class IgnoreLogsRequest(BaseModel):
    """忽略日志请求。"""
    log_ids: List[int]


class MetricCreate(BaseModel):
    """创建/更新指标请求（对齐 t_metric_definition 真实 schema）。"""
    metric_id: str
    metric_name: str
    aliases: Optional[str] = None
    description: str
    sql_template: str
    category: Optional[str] = None
    sub_category: Optional[str] = None
    unit: Optional[str] = None
    frequency: Optional[str] = None


class MetricResponse(BaseModel):
    """指标响应。"""
    metric_id: str
    metric_name: str
    aliases: Optional[str] = None
    description: Optional[str] = None
    sql_template: Optional[str] = None
    query_template: Optional[str] = None
    template_source: Optional[str] = None
    category: Optional[str] = None
    sub_category: Optional[str] = None
    unit: Optional[str] = None
    frequency: Optional[str] = None
    is_active: Optional[bool] = True
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    class Config:
        from_attributes = True


class MetricStatsResponse(BaseModel):
    """指标统计响应。"""
    total: int
    by_template_type: list
    by_template_source: list
    by_category: list
    query_ready: int
    query_ready_percent: float
    embedding_ready: int
    embedding_ready_percent: float


class BatchConvertRequest(BaseModel):
    """批量转换请求。"""
    mode: str = "result_lookup"
    limit: int = 100
    dry_run: bool = False


class ETLConvertRequest(BaseModel):
    """ETL 脚本转 SELECT 模板请求。"""
    etl_script: str


class ETLConvertResponse(BaseModel):
    """ETL 转换结果（供前端预览/编辑）。"""
    metric_id: Optional[str] = None
    metric_name: Optional[str] = None
    aliases: Optional[str] = None
    description: Optional[str] = None
    sql_template: Optional[str] = None
    category: Optional[str] = None
    unit: Optional[str] = None


# ==================== 查询日志管理 ====================

@router.get("/query-logs", response_model=List[QueryLogResponse])
def list_query_logs(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, le=100),
    is_correct: Optional[bool] = None,
    trained: Optional[bool] = None,
    include_ignored: bool = False,
    db: Session = Depends(get_db)
):
    """获取查询日志列表。
    
    支持筛选：
    - is_correct: 是否正确
    - trained: 是否已训练
    - include_ignored: 是否包含已忽略日志
    """
    query = db.query(DataQueryLog)

    if not include_ignored:
        query = query.filter(DataQueryLog.is_ignored == False)
    
    if is_correct is not None:
        query = query.filter(DataQueryLog.is_correct == is_correct)
    if trained is not None:
        query = query.filter(DataQueryLog.trained == trained)
    
    logs = query.order_by(DataQueryLog.created_at.desc()).offset(skip).limit(limit).all()
    
    return [
        QueryLogResponse(
            id=log.id,
            user_id=log.user_id,
            thread_id=log.thread_id,
            question=log.question,
            generated_sql=log.generated_sql,
            sql_source=log.sql_source,
            is_correct=log.is_correct,
            corrected_sql=log.corrected_sql,
            trained=log.trained or False,
            is_ignored=log.is_ignored or False,
            created_at=log.created_at.isoformat() if log.created_at else ""
        )
        for log in logs
    ]


@router.get("/query-logs/{log_id}", response_model=QueryLogResponse)
def get_query_log(log_id: int, db: Session = Depends(get_db)):
    """获取单条查询日志详情。"""
    log = db.query(DataQueryLog).filter(DataQueryLog.id == log_id).first()
    if not log:
        raise HTTPException(status_code=404, detail="日志不存在")
    
    return QueryLogResponse(
        id=log.id,
        user_id=log.user_id,
        thread_id=log.thread_id,
        question=log.question,
        generated_sql=log.generated_sql,
        sql_source=log.sql_source,
        is_correct=log.is_correct,
        corrected_sql=log.corrected_sql,
        trained=log.trained or False,
        is_ignored=log.is_ignored or False,
        created_at=log.created_at.isoformat() if log.created_at else ""
    )


@router.post("/query-logs/ignore")
def ignore_query_logs(request: IgnoreLogsRequest, db: Session = Depends(get_db)):
    """批量忽略查询日志（软隐藏）。"""
    if not request.log_ids:
        raise HTTPException(status_code=400, detail="log_ids 不能为空")

    ignored_count = 0
    skipped_count = 0
    errors: List[str] = []

    for log_id in request.log_ids:
        log = db.query(DataQueryLog).filter(DataQueryLog.id == log_id).first()
        if not log:
            errors.append(f"日志 {log_id} 不存在")
            continue

        if log.trained:
            errors.append(f"日志 {log_id} 已训练，不能忽略")
            continue

        if log.is_ignored:
            skipped_count += 1
            continue

        log.is_ignored = True
        ignored_count += 1

    db.commit()

    return {
        "message": f"忽略完成，成功 {ignored_count} 条",
        "ignored_count": ignored_count,
        "skipped_count": skipped_count,
        "errors": errors if errors else None,
    }


# ==================== SQL 修正 ====================

@router.post("/query-logs/correct")
def correct_sql(request: SQLCorrectionRequest, db: Session = Depends(get_db)):
    """修正 SQL 并标记反馈。
    
    用于管理员修正错误的 SQL 生成结果。
    """
    log = db.query(DataQueryLog).filter(DataQueryLog.id == request.log_id).first()
    if not log:
        raise HTTPException(status_code=404, detail="日志不存在")
    
    log.corrected_sql = request.corrected_sql
    log.is_correct = request.is_correct
    
    db.commit()
    
    logger.info(f"SQL 修正完成: log_id={request.log_id}")
    
    return {"message": "修正成功", "log_id": request.log_id}


@router.post("/query-logs/feedback/{log_id}")
def feedback_sql(
    log_id: int,
    is_correct: bool,
    db: Session = Depends(get_db)
):
    """用户反馈 SQL 是否正确。"""
    log = db.query(DataQueryLog).filter(DataQueryLog.id == log_id).first()
    if not log:
        raise HTTPException(status_code=404, detail="日志不存在")
    
    log.is_correct = is_correct
    db.commit()
    
    return {"message": "反馈已记录", "log_id": log_id, "is_correct": is_correct}


# ==================== 训练管理 ====================

@router.post("/train")
def train_from_logs(request: TrainRequest, db: Session = Depends(get_db)):
    """将修正后的日志训练到 Vanna 向量库。
    
    只训练 is_correct=True 且有 corrected_sql 的记录。
    """
    from app.ai.semantic import get_vanna
    
    trained_count = 0
    errors = []
    
    for log_id in request.log_ids:
        log = db.query(DataQueryLog).filter(DataQueryLog.id == log_id).first()
        if not log:
            errors.append(f"日志 {log_id} 不存在")
            continue
        
        if log.trained:
            errors.append(f"日志 {log_id} 已训练")
            continue
        
        # 使用修正后的 SQL 或原始 SQL
        sql = log.corrected_sql or log.generated_sql
        if not sql:
            errors.append(f"日志 {log_id} 没有可训练的 SQL")
            continue
        
        try:
            vanna = get_vanna()
            # 训练问答对
            vanna.train(question=log.question, sql=sql)
            
            # 标记已训练
            log.trained = True
            trained_count += 1
            
            logger.info(f"训练成功: log_id={log_id}, question={log.question[:50]}...")
            
        except Exception as e:
            logger.exception(f"训练失败: log_id={log_id}")
            errors.append(f"日志 {log_id} 训练失败: {str(e)}")
    
    db.commit()
    
    return {
        "message": f"训练完成，成功 {trained_count} 条",
        "trained_count": trained_count,
        "errors": errors if errors else None
    }


@router.post("/train/all-pending")
def train_all_pending(db: Session = Depends(get_db)):
    """训练所有待训练的日志（is_correct=True 且 trained=False）。"""
    from app.ai.semantic import get_vanna
    
    # 查询待训练的日志
    pending_logs = db.query(DataQueryLog).filter(
        DataQueryLog.is_correct == True,
        DataQueryLog.trained == False,
        DataQueryLog.is_ignored == False
    ).all()
    
    if not pending_logs:
        return {"message": "没有待训练的日志", "trained_count": 0}
    
    trained_count = 0
    errors = []
    
    for log in pending_logs:
        sql = log.corrected_sql or log.generated_sql
        if not sql:
            continue
        
        try:
            vanna = get_vanna()
            vanna.train(question=log.question, sql=sql)
            log.trained = True
            trained_count += 1
        except Exception as e:
            errors.append(f"日志 {log.id}: {str(e)}")
    
    db.commit()
    
    return {
        "message": f"训练完成，成功 {trained_count} 条",
        "trained_count": trained_count,
        "total_pending": len(pending_logs),
        "errors": errors if errors else None
    }


# ==================== 指标管理 ====================

def _metric_to_response(m: Metric) -> MetricResponse:
    """将 ORM 对象转为响应模型。"""
    return MetricResponse(
        metric_id=m.metric_id,
        metric_name=m.metric_name,
        aliases=m.aliases,
        description=m.description,
        sql_template=m.sql_template,
        query_template=m.query_template,
        template_source=m.template_source,
        category=m.category,
        sub_category=m.sub_category,
        unit=m.unit,
        frequency=m.frequency,
        is_active=m.is_active,
        created_at=m.created_at.isoformat() if m.created_at else None,
        updated_at=m.updated_at.isoformat() if m.updated_at else None,
    )


@router.get("/metrics/stats", response_model=MetricStatsResponse)
def get_metric_stats(db: Session = Depends(get_db)):
    """获取指标模板统计数据（支持仪表盘展示）。"""
    from sqlalchemy import func as sqla_func

    total = db.query(sqla_func.count(Metric.metric_id)).scalar() or 0

    # 按模板类型分组（基于 sql_template 内容判断）
    type_query = db.execute(text("""
        SELECT 
          CASE 
            WHEN sql_template IS NULL THEN '无模板'
            WHEN sql_template ~* '^\\s*SELECT' THEN 'SELECT'
            WHEN UPPER(sql_template) LIKE '%DELETE%' THEN 'ETL(DELETE+INSERT)'
            WHEN UPPER(sql_template) LIKE '%INSERT INTO%' THEN 'ETL(INSERT)'
            ELSE '其他'
          END AS template_type,
          COUNT(*) AS cnt
        FROM t_metric_definition
        GROUP BY template_type
        ORDER BY cnt DESC
    """))
    by_template_type = [
        {"type": row.template_type, "count": row.cnt,
         "percent": round(row.cnt * 100.0 / max(total, 1), 1)}
        for row in type_query
    ]

    # 按 template_source 分组
    source_query = db.execute(text("""
        SELECT COALESCE(template_source, 'none') AS source, COUNT(*) AS cnt
        FROM t_metric_definition
        GROUP BY source
        ORDER BY cnt DESC
    """))
    by_template_source = [
        {"source": row.source, "count": row.cnt} for row in source_query
    ]

    # 按分类分组
    cat_query = db.execute(text("""
        SELECT COALESCE(category, '未分类') AS category, COUNT(*) AS cnt
        FROM t_metric_definition
        GROUP BY category
        ORDER BY cnt DESC
        LIMIT 10
    """))
    by_category = [{"category": row.category, "count": row.cnt} for row in cat_query]

    # 覆盖率统计
    query_ready = db.execute(text(
        "SELECT COUNT(*) FROM t_metric_definition WHERE query_template IS NOT NULL"
    )).scalar() or 0
    embedding_ready = db.execute(text(
        "SELECT COUNT(*) FROM t_metric_definition WHERE embedding IS NOT NULL"
    )).scalar() or 0

    return MetricStatsResponse(
        total=total,
        by_template_type=by_template_type,
        by_template_source=by_template_source,
        by_category=by_category,
        query_ready=query_ready,
        query_ready_percent=round(query_ready * 100.0 / max(total, 1), 1),
        embedding_ready=embedding_ready,
        embedding_ready_percent=round(embedding_ready * 100.0 / max(total, 1), 1),
    )


@router.get("/metrics", response_model=List[MetricResponse])
def list_metrics(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, le=200),
    category: Optional[str] = None,
    keyword: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """获取指标列表，支持分类和关键词筛选。"""
    query = db.query(Metric)
    
    if category:
        query = query.filter(Metric.category == category)
    if keyword:
        like_pattern = f"%{keyword}%"
        query = query.filter(
            (Metric.metric_name.ilike(like_pattern))
            | (Metric.aliases.ilike(like_pattern))
            | (Metric.description.ilike(like_pattern))
        )
    
    metrics = query.order_by(Metric.metric_id).offset(skip).limit(limit).all()
    return [_metric_to_response(m) for m in metrics]


@router.post("/metrics", response_model=MetricResponse)
def create_metric(request: MetricCreate, db: Session = Depends(get_db)):
    """创建新指标。"""
    existing = db.query(Metric).filter(Metric.metric_id == request.metric_id).first()
    if existing:
        raise HTTPException(status_code=400, detail=f"指标 {request.metric_id} 已存在")

    # 生成 embedding
    embedding = None
    try:
        from app.ai.utils.embedding_util import get_embedding
        embed_text = request.description or request.metric_name
        embedding = get_embedding(embed_text)
    except Exception as e:
        logger.warning(f"生成指标 embedding 失败: {e}")

    metric = Metric(
        metric_id=request.metric_id,
        metric_name=request.metric_name,
        aliases=request.aliases,
        description=request.description,
        sql_template=request.sql_template,
        category=request.category,
        sub_category=request.sub_category,
        unit=request.unit,
        frequency=request.frequency,
        embedding=embedding,
        is_active=True,
    )

    db.add(metric)
    db.commit()
    db.refresh(metric)

    logger.info(f"创建指标: {request.metric_id} - {request.metric_name}")
    return _metric_to_response(metric)


@router.put("/metrics/{metric_id}", response_model=MetricResponse)
def update_metric(metric_id: str, request: MetricCreate, db: Session = Depends(get_db)):
    """更新指标。"""
    metric = db.query(Metric).filter(Metric.metric_id == metric_id).first()
    if not metric:
        raise HTTPException(status_code=404, detail="指标不存在")

    metric.metric_name = request.metric_name
    metric.aliases = request.aliases
    metric.description = request.description
    metric.sql_template = request.sql_template
    metric.category = request.category
    metric.sub_category = request.sub_category
    metric.unit = request.unit
    metric.frequency = request.frequency

    # 重新生成 embedding
    try:
        from app.ai.utils.embedding_util import get_embedding
        embed_text = request.description or request.metric_name
        metric.embedding = get_embedding(embed_text)
    except Exception as e:
        logger.warning(f"更新 embedding 失败: {e}")

    db.commit()
    db.refresh(metric)

    logger.info(f"更新指标: {metric_id}")
    return _metric_to_response(metric)


@router.delete("/metrics/{metric_id}")
def delete_metric(metric_id: str, db: Session = Depends(get_db)):
    """删除指标。"""
    metric = db.query(Metric).filter(Metric.metric_id == metric_id).first()
    if not metric:
        raise HTTPException(status_code=404, detail="指标不存在")

    db.delete(metric)
    db.commit()

    return {"message": "删除成功", "metric_id": metric_id}


# ==================== AI ETL 转换 ====================

ETL_CONVERT_PROMPT = """你是一个银行数据仓库专家。用户会粘贴一段 ETL 批处理脚本（通常包含 DELETE + INSERT INTO ... SELECT 结构），
你需要从中提取核心 SELECT 查询逻辑，将其转化为一个问数助手可以直接使用的 SELECT 查询模板。

## 规则
1. 只保留 SELECT 部分，去掉 DELETE 和 INSERT INTO ... 包装
2. 去掉写入目标表相关的常量列（如 INDEX_CODE、INDEX_NAME、MONTH_TO_DATE 等固定值列）
3. 保留有意义的业务列（如机构、金额、户数等），用中文别名
4. 日期参数统一使用 ${data_dt} 占位符
5. 如果原 SQL 中有 ETL 调度宏（如 [DATE,0D,YYYY-MM-DD]），替换为 '${data_dt}'
6. 加上 ORDER BY（如果合理的话）
7. GROUP BY 去掉常量列，只保留有效分组列

## 输出格式（严格 JSON）
```json
{
    "metric_id": "从脚本注释或 INDEX_CODE 推断，如 AK000119",
    "metric_name": "从 INDEX_NAME 或脚本注释推断，如 各项贷款户数",
    "aliases": "逗号分隔的别名，如 贷款户数,贷款客户数",
    "description": "用自然语言描述这个指标的口径，包含筛选条件、排除条件等",
    "sql_template": "提取并优化后的 SELECT 查询模板",
    "category": "贷款/存款/综合/其他",
    "unit": "元/户/笔/%/其他"
}
```

## 用户输入的 ETL 脚本
"""


@router.post("/metrics/convert-etl", response_model=ETLConvertResponse)
def convert_etl_to_select(request: ETLConvertRequest):
    """AI 转换：将 ETL 脚本转为 SELECT 查询模板。

    不直接保存，返回结构化结果供前端预览和编辑。
    """
    if not request.etl_script or not request.etl_script.strip():
        raise HTTPException(status_code=400, detail="ETL 脚本不能为空")

    try:
        from app.ai.llm_util import get_scene_llm, _normalize_text_content
        from app.ai.scene_registry import SCENE_KEY_DATA_ADMIN_ETL_CONVERT
        from langchain_core.messages import SystemMessage, HumanMessage
        import json

        llm = get_scene_llm(
            scene_key=SCENE_KEY_DATA_ADMIN_ETL_CONVERT,
            internal=True,
        )
        messages = [
            SystemMessage(content=ETL_CONVERT_PROMPT),
            HumanMessage(content=request.etl_script),
        ]
        response = llm.invoke(messages)
        content = _normalize_text_content(
            response.content if hasattr(response, "content") else response
        )

        # 从响应中提取 JSON
        json_str = content
        if "```json" in json_str:
            json_str = json_str.split("```json")[1].split("```")[0]
        elif "```" in json_str:
            json_str = json_str.split("```")[1].split("```")[0]

        result = json.loads(json_str.strip())

        return ETLConvertResponse(
            metric_id=result.get("metric_id"),
            metric_name=result.get("metric_name"),
            aliases=result.get("aliases"),
            description=result.get("description"),
            sql_template=result.get("sql_template"),
            category=result.get("category"),
            unit=result.get("unit"),
        )
    except json.JSONDecodeError as e:
        logger.error(f"AI 响应 JSON 解析失败: {e}")
        raise HTTPException(status_code=422, detail=f"AI 返回结果解析失败，请重试: {str(e)}")
    except Exception as e:
        logger.exception("ETL 转换失败")
        raise HTTPException(status_code=500, detail=f"转换失败: {str(e)}")


# ==================== 表元数据管理 ====================

@router.get("/tables")
def list_meta_tables(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, le=200),
    db: Session = Depends(get_db)
):
    """获取表元数据列表。"""
    tables = db.query(MetaTable).offset(skip).limit(limit).all()
    return [
        {
            "id": t.id,
            "table_name": t.table_name,
            "display_name": t.display_name,
            "description": t.description,
            "category": t.category,
            "column_count": len(t.columns) if t.columns else 0
        }
        for t in tables
    ]


@router.post("/sync-schema")
def sync_schema(db: Session = Depends(get_db)):
    """手动触发表结构同步。"""
    from scripts.schema_sync import get_analytics_tables, sync_tables_to_metadata, sync_relations
    from app.core.config import ANALYTICS_DATABASE_URL
    
    try:
        tables = get_analytics_tables(ANALYTICS_DATABASE_URL)
        synced = sync_tables_to_metadata(tables, force=True)
        relations = sync_relations(tables)
        
        return {
            "message": "同步完成",
            "tables_synced": synced,
            "relations_synced": relations
        }
    except Exception as e:
        logger.exception("表结构同步失败")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== 批量模板转换 ====================

@router.post("/metrics/batch-convert")
def batch_convert_templates(request: BatchConvertRequest, db: Session = Depends(get_db)):
    """批量将 ETL 模板转换为可执行查询模板。

    支持两种模式：
    - result_lookup: 自动生成结果表查询（无需 LLM，秒级完成）
    - ai_extract: 使用 AI 从 ETL 脚本提取 SELECT（需 LLM，较慢）
    """
    if request.mode == "result_lookup":
        return _batch_convert_result_lookup(db, request.limit, request.dry_run)
    elif request.mode == "ai_extract":
        return _batch_convert_ai_extract(db, request.limit, request.dry_run)
    else:
        raise HTTPException(status_code=400, detail=f"不支持的模式: {request.mode}")


def _batch_convert_result_lookup(db: Session, limit: int, dry_run: bool):
    """批量生成结果表查询模板（无需 LLM）。"""
    # 查找尚未转换的 ETL 指标
    pending = db.execute(text("""
        SELECT metric_id, metric_name,
          CASE
            WHEN UPPER(sql_template) LIKE '%F_MID_INDEX_RESULT_DIM%' THEN 'dim'
            WHEN UPPER(sql_template) LIKE '%F_MID_INDEX_RESULT_DERIVE%' THEN 'derive'
            ELSE 'main'
          END AS target_type
        FROM t_metric_definition
        WHERE sql_template IS NOT NULL
          AND UPPER(sql_template) LIKE '%INSERT INTO%F_MID_INDEX_RESULT%'
          AND (query_template IS NULL OR template_source = 'none')
        LIMIT :limit
    """), {"limit": limit}).fetchall()

    if not pending:
        return {"message": "没有待转换的 ETL 指标", "processed": 0, "success": 0}

    if dry_run:
        return {
            "message": f"预览模式：发现 {len(pending)} 条待转换指标",
            "processed": len(pending),
            "success": 0,
            "dry_run": True,
            "preview": [{"metric_id": r.metric_id, "metric_name": r.metric_name,
                         "target_type": r.target_type} for r in pending]
        }

    # 执行转换
    success = 0
    errors = []
    for row in pending:
        try:
            table_map = {
                "main": "fdmdata.f_mid_index_result",
                "dim": "fdmdata.f_mid_index_result_dim",
                "derive": "fdmdata.f_mid_index_result_derive",
            }
            target = table_map.get(row.target_type, table_map["main"])

            extra_cols = ", dim_name AS 维度名称, dim_value AS 维度值" if row.target_type == "dim" else ""

            qt = (
                f"SELECT data_dt, org_no, org_no_map AS 机构名称, ccy AS 币种, "
                f"index_name AS 指标名称, index_value AS 指标值, "
                f"year_to_date AS 年累计{extra_cols} "
                f"FROM {target} "
                f"WHERE index_code = '{row.metric_id}' AND data_dt = '${{data_dt}}' "
                f"ORDER BY org_no"
            )

            db.execute(text("""
                UPDATE t_metric_definition
                SET query_template = :qt, template_source = 'result_lookup'
                WHERE metric_id = :mid
            """), {"qt": qt, "mid": row.metric_id})
            success += 1
        except Exception as e:
            errors.append({"metric_id": row.metric_id, "error": str(e)})

    db.commit()
    logger.info(f"批量转换完成: 成功={success}, 失败={len(errors)}")

    return {
        "message": f"转换完成，成功 {success} 条",
        "processed": len(pending),
        "success": success,
        "errors": errors if errors else None,
    }


def _batch_convert_ai_extract(db: Session, limit: int, dry_run: bool):
    """批量使用 AI 从 ETL 脚本提取 SELECT（较慢）。"""
    pending = db.execute(text("""
        SELECT metric_id, metric_name, sql_template
        FROM t_metric_definition
        WHERE sql_template IS NOT NULL
          AND UPPER(sql_template) LIKE '%INSERT INTO%'
          AND (query_template IS NULL OR template_source = 'none')
        LIMIT :limit
    """), {"limit": limit}).fetchall()

    if not pending:
        return {"message": "没有待转换的 ETL 指标", "processed": 0, "success": 0}

    if dry_run:
        return {
            "message": f"预览模式：发现 {len(pending)} 条待 AI 提取的指标",
            "processed": len(pending),
            "success": 0,
            "dry_run": True,
            "preview": [{"metric_id": r.metric_id, "metric_name": r.metric_name}
                         for r in pending[:20]]
        }

    from app.ai.llm_util import get_scene_llm, _normalize_text_content
    from app.ai.scene_registry import SCENE_KEY_DATA_ADMIN_BATCH_ETL_CONVERT
    from langchain_core.messages import SystemMessage, HumanMessage
    import json

    llm = get_scene_llm(
        scene_key=SCENE_KEY_DATA_ADMIN_BATCH_ETL_CONVERT,
        internal=True,
    )
    success = 0
    errors = []

    for row in pending:
        try:
            messages = [
                SystemMessage(content=ETL_CONVERT_PROMPT),
                HumanMessage(content=row.sql_template),
            ]
            response = llm.invoke(messages)
            content = _normalize_text_content(
                response.content if hasattr(response, "content") else response
            )

            # 提取 JSON
            json_str = content
            if "```json" in json_str:
                json_str = json_str.split("```json")[1].split("```")[0]
            elif "```" in json_str:
                json_str = json_str.split("```")[1].split("```")[0]

            result = json.loads(json_str.strip())
            extracted_sql = result.get("sql_template", "")

            if extracted_sql:
                db.execute(text("""
                    UPDATE t_metric_definition
                    SET query_template = :qt, template_source = 'ai_extract'
                    WHERE metric_id = :mid
                """), {"qt": extracted_sql, "mid": row.metric_id})
                success += 1
        except Exception as e:
            errors.append({"metric_id": row.metric_id, "error": str(e)[:100]})

    db.commit()
    logger.info(f"AI 批量提取完成: 成功={success}, 失败={len(errors)}")

    return {
        "message": f"AI 提取完成，成功 {success} 条",
        "processed": len(pending),
        "success": success,
        "errors": errors if errors else None,
    }

# ==================== 结果增强规则管理 ====================


class EnrichmentRuleResponse(BaseModel):
    """结果增强规则响应。"""

    id: int
    rule_code: str
    rule_name: str
    enabled: bool
    priority: int
    key_column_candidates: List[str]
    target_column: str
    source_table: str
    source_key_column: str
    source_value_column: str
    source_date_column: Optional[str]
    result_date_column_candidates: List[str]
    description: Optional[str]
    created_by: Optional[str]
    updated_by: Optional[str]
    created_at: Optional[str]
    updated_at: Optional[str]


class EnrichmentRuleCreateRequest(BaseModel):
    """创建结果增强规则请求。"""

    rule_code: str
    rule_name: str
    enabled: bool = True
    priority: int = Field(default=100, ge=0)
    key_column_candidates: List[str]
    target_column: str
    source_table: str
    source_key_column: str
    source_value_column: str
    source_date_column: Optional[str] = None
    result_date_column_candidates: List[str] = Field(default_factory=lambda: ["data_dt"])
    description: Optional[str] = None


class EnrichmentRuleUpdateRequest(BaseModel):
    """更新结果增强规则请求。"""

    rule_code: str
    rule_name: str
    enabled: bool
    priority: int = Field(ge=0)
    key_column_candidates: List[str]
    target_column: str
    source_table: str
    source_key_column: str
    source_value_column: str
    source_date_column: Optional[str] = None
    result_date_column_candidates: List[str]
    description: Optional[str] = None


class EnrichmentRuleEnableRequest(BaseModel):
    """规则启停请求。"""

    enabled: bool


class EnrichmentRulePriorityRequest(BaseModel):
    """规则优先级请求。"""

    priority: int = Field(ge=0)


class EnrichmentRuleTestRequest(BaseModel):
    """规则测试请求。"""

    rows: List[Dict[str, Any]]
    columns: List[str]
    rule_id: Optional[int] = None


class EnrichmentRuleTestResponse(BaseModel):
    """规则测试响应。"""

    rows: List[Dict[str, Any]]
    columns: List[str]
    applied_rule_codes: List[str]


class EnrichmentRuleRefreshResponse(BaseModel):
    """规则缓存刷新响应。"""

    message: str
    rule_count: int
    ttl_seconds: int


def _rule_to_response(rule: ResultEnrichmentRule) -> EnrichmentRuleResponse:
    """规则 ORM 转响应模型。"""
    return EnrichmentRuleResponse(
        id=rule.id,
        rule_code=rule.rule_code,
        rule_name=rule.rule_name,
        enabled=rule.enabled,
        priority=rule.priority,
        key_column_candidates=list(rule.key_column_candidates or []),
        target_column=rule.target_column,
        source_table=rule.source_table,
        source_key_column=rule.source_key_column,
        source_value_column=rule.source_value_column,
        source_date_column=rule.source_date_column,
        result_date_column_candidates=list(rule.result_date_column_candidates or []),
        description=rule.description,
        created_by=rule.created_by,
        updated_by=rule.updated_by,
        created_at=rule.created_at.isoformat() if rule.created_at else None,
        updated_at=rule.updated_at.isoformat() if rule.updated_at else None,
    )


def _rule_payload_from_request(data: Dict[str, Any]) -> Dict[str, Any]:
    """从请求生成规则 payload。"""
    return {
        "rule_code": data.get("rule_code"),
        "rule_name": data.get("rule_name"),
        "enabled": data.get("enabled", True),
        "priority": data.get("priority", 100),
        "key_column_candidates": data.get("key_column_candidates"),
        "target_column": data.get("target_column"),
        "source_table": data.get("source_table"),
        "source_key_column": data.get("source_key_column"),
        "source_value_column": data.get("source_value_column"),
        "source_date_column": data.get("source_date_column"),
        "result_date_column_candidates": data.get("result_date_column_candidates"),
        "description": data.get("description"),
    }


def _get_operator(admin_user: User) -> str:
    """生成操作人标识。"""
    if admin_user.username:
        return str(admin_user.username)
    return str(admin_user.id)


@router.get("/enrichment-rules", response_model=List[EnrichmentRuleResponse])
def list_enrichment_rules(db: Session = Depends(get_db)):
    """获取结果增强规则列表。"""
    rules = _rule_repo.list_rules(db, include_disabled=True)
    return [_rule_to_response(rule) for rule in rules]


@router.post("/enrichment-rules", response_model=EnrichmentRuleResponse)
def create_enrichment_rule(
    request: EnrichmentRuleCreateRequest,
    db: Session = Depends(get_db),
    admin_user: User = Depends(get_admin_user),
):
    """创建结果增强规则。"""
    payload = _rule_payload_from_request(request.model_dump())
    try:
        normalized = _rule_service.validate_rule_payload(payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    existing = _rule_repo.get_rule_by_code(db, normalized["rule_code"])
    if existing:
        raise HTTPException(status_code=400, detail=f"规则编码已存在: {normalized['rule_code']}")

    operator = _get_operator(admin_user)
    normalized["created_by"] = operator
    normalized["updated_by"] = operator

    rule = _rule_repo.create_rule(db, normalized, operator_id=operator)
    db.commit()
    db.refresh(rule)

    _rule_service.invalidate_cache()
    return _rule_to_response(rule)


@router.put("/enrichment-rules/{rule_id}", response_model=EnrichmentRuleResponse)
def update_enrichment_rule(
    rule_id: int,
    request: EnrichmentRuleUpdateRequest,
    db: Session = Depends(get_db),
    admin_user: User = Depends(get_admin_user),
):
    """更新结果增强规则。"""
    rule = _rule_repo.get_rule_by_id(db, rule_id)
    if not rule:
        raise HTTPException(status_code=404, detail="规则不存在")

    payload = _rule_payload_from_request(request.model_dump())
    try:
        normalized = _rule_service.validate_rule_payload(payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    if normalized["rule_code"] != rule.rule_code:
        duplicate = _rule_repo.get_rule_by_code(db, normalized["rule_code"])
        if duplicate and duplicate.id != rule.id:
            raise HTTPException(status_code=400, detail=f"规则编码已存在: {normalized['rule_code']}")

    operator = _get_operator(admin_user)
    normalized["updated_by"] = operator

    _rule_repo.update_rule(db, rule, normalized, operator_id=operator)
    db.commit()
    db.refresh(rule)

    _rule_service.invalidate_cache()
    return _rule_to_response(rule)


@router.patch("/enrichment-rules/{rule_id}/enable", response_model=EnrichmentRuleResponse)
def set_enrichment_rule_enabled(
    rule_id: int,
    request: EnrichmentRuleEnableRequest,
    db: Session = Depends(get_db),
    admin_user: User = Depends(get_admin_user),
):
    """启停结果增强规则。"""
    rule = _rule_repo.get_rule_by_id(db, rule_id)
    if not rule:
        raise HTTPException(status_code=404, detail="规则不存在")

    operator = _get_operator(admin_user)
    rule.updated_by = operator
    _rule_repo.set_rule_enabled(db, rule, request.enabled, operator_id=operator)
    db.commit()
    db.refresh(rule)

    _rule_service.invalidate_cache()
    return _rule_to_response(rule)


@router.patch("/enrichment-rules/{rule_id}/priority", response_model=EnrichmentRuleResponse)
def update_enrichment_rule_priority(
    rule_id: int,
    request: EnrichmentRulePriorityRequest,
    db: Session = Depends(get_db),
    admin_user: User = Depends(get_admin_user),
):
    """更新结果增强规则优先级。"""
    rule = _rule_repo.get_rule_by_id(db, rule_id)
    if not rule:
        raise HTTPException(status_code=404, detail="规则不存在")

    operator = _get_operator(admin_user)
    rule.updated_by = operator
    _rule_repo.update_rule_priority(db, rule, request.priority, operator_id=operator)
    db.commit()
    db.refresh(rule)

    _rule_service.invalidate_cache()
    return _rule_to_response(rule)


@router.post("/enrichment-rules/test", response_model=EnrichmentRuleTestResponse)
def test_enrichment_rules(
    request: EnrichmentRuleTestRequest,
    db: Session = Depends(get_db),
    admin_user: User = Depends(get_admin_user),
):
    """测试规则增强效果（仅预览，不写主链路结果）。"""
    rows = list(request.rows or [])
    columns = list(request.columns or [])
    if not columns:
        raise HTTPException(status_code=400, detail="columns 不能为空")

    rules: Tuple[ResultLookupEnrichmentRuleConfig, ...]
    selected_rule: Optional[ResultEnrichmentRule] = None

    if request.rule_id is not None:
        selected_rule = _rule_repo.get_rule_by_id(db, request.rule_id)
        if not selected_rule:
            raise HTTPException(status_code=404, detail="规则不存在")

        runtime_rule = _rule_service._validate_and_convert_rule(selected_rule)
        if not runtime_rule:
            raise HTTPException(status_code=400, detail="规则配置非法，无法测试")
        rules = (runtime_rule,)
    else:
        rules = _rule_service.get_active_rules(force_refresh=False, fallback_rules=())

    applied_rule_codes: List[str] = []
    enriched_rows = rows
    enriched_columns = columns
    for runtime_rule in rules:
        before_columns = list(enriched_columns)
        before_rows = list(enriched_rows)
        enriched_rows, enriched_columns = apply_lookup_enrichment_rule(
            enriched_rows,
            enriched_columns,
            runtime_rule,
        )
        if enriched_columns != before_columns or enriched_rows != before_rows:
            applied_rule_codes.append(runtime_rule.name)

    if selected_rule is not None:
        _rule_repo.add_audit(
            db,
            rule_id=selected_rule.id,
            op_type="test",
            before_json={"rows": rows, "columns": columns},
            after_json={"rows": enriched_rows, "columns": enriched_columns, "applied_rule_codes": applied_rule_codes},
            operator_id=_get_operator(admin_user),
        )
        db.commit()

    return EnrichmentRuleTestResponse(
        rows=enriched_rows,
        columns=enriched_columns,
        applied_rule_codes=applied_rule_codes,
    )


@router.post("/enrichment-rules/refresh-cache", response_model=EnrichmentRuleRefreshResponse)
def refresh_enrichment_rule_cache(
    db: Session = Depends(get_db),
    admin_user: User = Depends(get_admin_user),
):
    """手动刷新结果增强规则缓存。"""
    _ = db
    _ = admin_user
    rules = _rule_service.get_active_rules(force_refresh=True, fallback_rules=())

    return EnrichmentRuleRefreshResponse(
        message="规则缓存刷新成功",
        rule_count=len(rules),
        ttl_seconds=_rule_service.ttl_seconds,
    )
