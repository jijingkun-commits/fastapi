"""问数 Agent 管理 API（中文注释）。

提供：
- 查询日志管理
- SQL 修正与反馈
- 训练数据管理
- 指标管理
"""
import logging
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.db.session import get_db
from app.models.data_agent_metadata import DataQueryLog, Metric, MetaTable

logger = logging.getLogger(__name__)

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


class MetricCreate(BaseModel):
    """创建指标请求。"""
    name: str
    description: Optional[str] = None
    metric_type: str = "sum"
    model_name: Optional[str] = None
    field_name: Optional[str] = None
    formula: Optional[str] = None
    filter_condition: Optional[str] = None
    synonyms: Optional[List[str]] = None


class MetricResponse(BaseModel):
    """指标响应。"""
    id: int
    name: str
    description: Optional[str]
    metric_type: Optional[str]
    model_name: Optional[str]
    field_name: Optional[str]
    formula: Optional[str]
    synonyms: Optional[List[str]]
    
    class Config:
        from_attributes = True


# ==================== 查询日志管理 ====================

@router.get("/query-logs", response_model=List[QueryLogResponse])
def list_query_logs(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, le=100),
    is_correct: Optional[bool] = None,
    trained: Optional[bool] = None,
    db: Session = Depends(get_db)
):
    """获取查询日志列表。
    
    支持筛选：
    - is_correct: 是否正确
    - trained: 是否已训练
    """
    query = db.query(DataQueryLog)
    
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
        created_at=log.created_at.isoformat() if log.created_at else ""
    )


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
        DataQueryLog.trained == False
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

@router.get("/metrics", response_model=List[MetricResponse])
def list_metrics(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, le=200),
    db: Session = Depends(get_db)
):
    """获取指标列表。"""
    metrics = db.query(Metric).offset(skip).limit(limit).all()
    return metrics


@router.post("/metrics", response_model=MetricResponse)
def create_metric(request: MetricCreate, db: Session = Depends(get_db)):
    """创建新指标。"""
    # 检查重复
    existing = db.query(Metric).filter(Metric.name == request.name).first()
    if existing:
        raise HTTPException(status_code=400, detail=f"指标 {request.name} 已存在")
    
    # 生成 embedding
    try:
        from app.ai.utils.embedding_util import get_embedding
        description = request.description or request.name
        embedding = get_embedding(description)
    except Exception as e:
        logger.warning(f"生成指标 embedding 失败: {e}")
        embedding = None
    
    metric = Metric(
        name=request.name,
        description=request.description,
        metric_type=request.metric_type,
        model_name=request.model_name,
        field_name=request.field_name,
        formula=request.formula,
        filter_condition=request.filter_condition,
        synonyms=request.synonyms,
        embedding=embedding
    )
    
    db.add(metric)
    db.commit()
    db.refresh(metric)
    
    logger.info(f"创建指标: {request.name}")
    
    return metric


@router.delete("/metrics/{metric_id}")
def delete_metric(metric_id: int, db: Session = Depends(get_db)):
    """删除指标。"""
    metric = db.query(Metric).filter(Metric.id == metric_id).first()
    if not metric:
        raise HTTPException(status_code=404, detail="指标不存在")
    
    db.delete(metric)
    db.commit()
    
    return {"message": "删除成功", "metric_id": metric_id}


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
