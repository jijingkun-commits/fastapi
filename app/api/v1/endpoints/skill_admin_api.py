"""技能管理 API（中文注释）。

提供：
- 技能列表查询
- 技能启用/禁用
- 向量重新生成
- 向量维度检查
"""
import logging
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from sqlalchemy.orm import Session
from sqlalchemy import text
from pydantic import BaseModel

from app.db.session import get_db
from app.models.agent_skill import AgentSkill
from app.ai.utils.embedding_util import get_embedding

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/skill-admin", tags=["技能管理"])


# ==================== Schemas ====================

class SkillResponse(BaseModel):
    """技能响应。"""
    id: int
    skill_id: str
    name: str
    description: Optional[str]
    content_preview: str
    file_hash: Optional[str]
    has_embedding: bool
    embedding_dim: Optional[int]
    created_at: Optional[str]
    updated_at: Optional[str]
    
    class Config:
        from_attributes = True


class SkillDetailResponse(BaseModel):
    """技能详情响应。"""
    id: int
    skill_id: str
    name: str
    description: Optional[str]
    content: str
    file_hash: Optional[str]
    has_embedding: bool
    embedding_dim: Optional[int]


class VectorStatusResponse(BaseModel):
    """向量状态响应。"""
    total_skills: int
    with_embedding: int
    without_embedding: int
    embedding_dim: Optional[int]
    dimension_mismatch: bool
    current_model_dim: Optional[int]


class RegenerateRequest(BaseModel):
    """重新生成向量请求。"""
    skill_ids: Optional[List[str]] = None  # 为空则重新生成所有


# ==================== API 端点 ====================

@router.get("/skills", response_model=List[SkillResponse])
def list_skills(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, le=200),
    search: Optional[str] = None,
    has_embedding: Optional[bool] = None,
    db: Session = Depends(get_db)
):
    """获取技能列表。
    
    支持筛选：
    - search: 搜索技能名称或描述
    - has_embedding: 是否有向量
    """
    query = db.query(AgentSkill)
    
    if search:
        query = query.filter(
            (AgentSkill.name.ilike(f"%{search}%")) |
            (AgentSkill.description.ilike(f"%{search}%")) |
            (AgentSkill.skill_id.ilike(f"%{search}%"))
        )
    
    if has_embedding is not None:
        if has_embedding:
            query = query.filter(AgentSkill.embedding.isnot(None))
        else:
            query = query.filter(AgentSkill.embedding.is_(None))
    
    skills = query.order_by(AgentSkill.name).offset(skip).limit(limit).all()
    
    return [
        SkillResponse(
            id=s.id,
            skill_id=s.skill_id,
            name=s.name,
            description=s.description,
            content_preview=s.content[:200] + "..." if len(s.content) > 200 else s.content,
            file_hash=s.file_hash,
            has_embedding=s.embedding is not None,
            embedding_dim=len(s.embedding) if s.embedding is not None else None,
            created_at=s.created_at.isoformat() if s.created_at else None,
            updated_at=s.updated_at.isoformat() if s.updated_at else None
        )
        for s in skills
    ]


@router.get("/skills/{skill_id}", response_model=SkillDetailResponse)
def get_skill(skill_id: str, db: Session = Depends(get_db)):
    """获取单个技能详情。"""
    skill = db.query(AgentSkill).filter(AgentSkill.skill_id == skill_id).first()
    if not skill:
        raise HTTPException(status_code=404, detail="技能不存在")
    
    return SkillDetailResponse(
        id=skill.id,
        skill_id=skill.skill_id,
        name=skill.name,
        description=skill.description,
        content=skill.content,
        file_hash=skill.file_hash,
        has_embedding=skill.embedding is not None,
        embedding_dim=len(skill.embedding) if skill.embedding is not None else None
    )


@router.get("/vector-status", response_model=VectorStatusResponse)
def get_vector_status(db: Session = Depends(get_db)):
    """获取向量状态概览。"""
    total = db.query(AgentSkill).count()
    with_embedding = db.query(AgentSkill).filter(AgentSkill.embedding.isnot(None)).count()
    without_embedding = total - with_embedding
    
    # 获取现有向量维度
    sample = db.query(AgentSkill).filter(AgentSkill.embedding.isnot(None)).first()
    embedding_dim = len(sample.embedding) if sample is not None and sample.embedding is not None else None
    
    # 检查当前 embedding 模型的维度
    try:
        test_embedding = get_embedding("test")
        current_model_dim = len(test_embedding) if test_embedding else None
    except Exception:
        current_model_dim = None
    
    # 检查维度是否匹配
    dimension_mismatch = (
        embedding_dim is not None and 
        current_model_dim is not None and 
        embedding_dim != current_model_dim
    )
    
    return VectorStatusResponse(
        total_skills=total,
        with_embedding=with_embedding,
        without_embedding=without_embedding,
        embedding_dim=embedding_dim,
        dimension_mismatch=dimension_mismatch,
        current_model_dim=current_model_dim
    )


@router.post("/regenerate-embeddings")
def regenerate_embeddings(
    request: RegenerateRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """重新生成技能向量（后台任务）。
    
    如果 skill_ids 为空，则重新生成所有技能的向量。
    """
    if request.skill_ids:
        skills = db.query(AgentSkill).filter(AgentSkill.skill_id.in_(request.skill_ids)).all()
    else:
        skills = db.query(AgentSkill).all()
    
    if not skills:
        raise HTTPException(status_code=400, detail="没有找到技能")
    
    # 立即执行（小批量）
    if len(skills) <= 10:
        success_count = 0
        errors = []
        
        for skill in skills:
            try:
                embedding = get_embedding(skill.description or skill.name)
                if embedding:
                    skill.embedding = embedding
                    success_count += 1
            except Exception as e:
                errors.append(f"{skill.skill_id}: {str(e)}")
        
        db.commit()
        
        return {
            "message": f"重新生成完成",
            "success_count": success_count,
            "total": len(skills),
            "errors": errors if errors else None
        }
    else:
        # 大批量使用后台任务
        skill_ids = [s.skill_id for s in skills]
        background_tasks.add_task(_regenerate_embeddings_task, skill_ids)
        
        return {
            "message": f"后台任务已启动，正在重新生成 {len(skills)} 个技能的向量",
            "total": len(skills),
            "status": "processing"
        }


def _regenerate_embeddings_task(skill_ids: List[str]):
    """后台任务：重新生成向量。"""
    from app.db.session import SessionLocal
    
    logger.info(f"开始重新生成 {len(skill_ids)} 个技能的向量...")
    
    with SessionLocal() as db:
        success = 0
        errors = 0
        
        for skill_id in skill_ids:
            try:
                skill = db.query(AgentSkill).filter(AgentSkill.skill_id == skill_id).first()
                if skill:
                    embedding = get_embedding(skill.description or skill.name)
                    if embedding:
                        skill.embedding = embedding
                        success += 1
                        db.commit()
            except Exception as e:
                errors += 1
                logger.error(f"重新生成向量失败 {skill_id}: {e}")
        
        logger.info(f"向量重新生成完成: 成功 {success}, 失败 {errors}")


@router.delete("/skills/{skill_id}")
def delete_skill(skill_id: str, db: Session = Depends(get_db)):
    """删除技能。"""
    skill = db.query(AgentSkill).filter(AgentSkill.skill_id == skill_id).first()
    if not skill:
        raise HTTPException(status_code=404, detail="技能不存在")
    
    db.delete(skill)
    db.commit()
    
    logger.info(f"删除技能: {skill_id}")
    
    return {"message": "技能已删除", "skill_id": skill_id}


@router.post("/skills/{skill_id}/regenerate")
def regenerate_single_skill(skill_id: str, db: Session = Depends(get_db)):
    """重新生成单个技能的向量。"""
    skill = db.query(AgentSkill).filter(AgentSkill.skill_id == skill_id).first()
    if not skill:
        raise HTTPException(status_code=404, detail="技能不存在")
    
    try:
        embedding = get_embedding(skill.description or skill.name)
        if embedding:
            skill.embedding = embedding
            db.commit()
            
            return {
                "message": "向量已重新生成",
                "skill_id": skill_id,
                "embedding_dim": len(embedding)
            }
        else:
            raise HTTPException(status_code=500, detail="向量生成失败")
    except Exception as e:
        logger.exception(f"重新生成向量失败: {skill_id}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/search")
def search_skills(
    query: str = Query(..., min_length=1),
    top_k: int = Query(5, ge=1, le=20),
    threshold: float = Query(0.3, ge=0, le=1),
    db: Session = Depends(get_db)
):
    """搜索技能（向量相似度）。"""
    query_embedding = get_embedding(query)
    if not query_embedding:
        raise HTTPException(status_code=500, detail="向量生成失败")
    
    sql = text("""
        SELECT 
            skill_id, name, description,
            1 - (embedding <=> CAST(:query_vec AS vector)) as similarity
        FROM t_agent_skills
        WHERE embedding IS NOT NULL
        ORDER BY embedding <=> CAST(:query_vec AS vector)
        LIMIT :limit
    """)
    
    result = db.execute(sql, {
        "query_vec": query_embedding,
        "limit": top_k
    })
    
    skills = []
    for row in result:
        if row.similarity >= threshold:
            skills.append({
                "skill_id": row.skill_id,
                "name": row.name,
                "description": row.description,
                "similarity": round(row.similarity, 4)
            })
    
    return {
        "query": query,
        "results": skills,
        "count": len(skills)
    }
