"""技能管理 API（中文注释）。

提供：
- 技能列表查询
- 技能元数据治理
- 向量重新生成
- 混合检索调试
"""

import json
import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.ai.utils.embedding_util import get_embedding
from app.db.session import get_db
from app.models.agent_skill import AgentSkill, AgentSkillVersion, UserSkillBinding
from app.repositories import config_repo
from app.services.skill_bootstrap_service import load_bootstrap_template_from_config, normalize_bootstrap_template
from app.services.skill_service import SkillService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/skill-admin", tags=["技能管理"])


class SkillResponse(BaseModel):
    """技能列表响应。"""

    id: int
    skill_id: str
    name: str
    description: Optional[str]
    content_preview: str
    file_hash: Optional[str]
    has_embedding: bool
    embedding_dim: Optional[int]
    is_enabled: bool
    auto_enabled: bool
    priority: int
    scope: str
    trigger_phrases: List[str]
    conflicts_with: List[str]
    published_version: Optional[str] = None
    bound_version: Optional[str] = None
    binding_status: Optional[str] = None
    effective_version: Optional[str] = None
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
    is_enabled: bool
    auto_enabled: bool
    priority: int
    scope: str
    trigger_phrases: List[str]
    conflicts_with: List[str]


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

    skill_ids: Optional[List[str]] = None


class SkillMetadataUpdateRequest(BaseModel):
    """技能元数据更新请求。"""

    is_enabled: Optional[bool] = None
    auto_enabled: Optional[bool] = None
    priority: Optional[int] = Field(default=None, ge=0, le=10000)
    scope: Optional[str] = Field(default=None, min_length=1, max_length=32)
    trigger_phrases: Optional[List[str]] = None
    conflicts_with: Optional[List[str]] = None


class SkillVersionItem(BaseModel):
    """技能版本信息。"""

    skill_id: str
    version: str
    status: str
    name: str
    description: Optional[str]
    is_enabled: bool
    auto_enabled: bool
    priority: int
    scope: str
    published_at: Optional[str]
    updated_at: Optional[str]


class PublishVersionRequest(BaseModel):
    """发布技能版本请求。"""

    version: str = Field(..., min_length=1, max_length=64)


class RollbackVersionRequest(BaseModel):
    """回滚技能版本请求。"""

    target_version: Optional[str] = Field(default=None, min_length=1, max_length=64)


class BindSkillRequest(BaseModel):
    """用户技能绑定请求。"""

    user_id: int = Field(..., ge=1)
    skill_id: str = Field(..., min_length=1, max_length=100)
    version: str = Field(..., min_length=1, max_length=64)
    is_enabled: bool = True
    priority_override: Optional[int] = Field(default=None, ge=0, le=10000)
    config_override: Optional[Dict[str, Any]] = None


class RollbackBindingRequest(BaseModel):
    """用户绑定回滚请求。"""

    user_id: int = Field(..., ge=1)
    skill_id: str = Field(..., min_length=1, max_length=100)


class SkillBindingItem(BaseModel):
    """用户技能绑定信息。"""

    user_id: int
    skill_id: str
    version: Optional[str]
    binding_status: str
    is_enabled: bool
    priority_override: Optional[int]
    config_override: Dict[str, Any]
    updated_at: Optional[str]


class SearchResultItem(BaseModel):
    """技能搜索结果。"""

    skill_id: str
    name: str
    description: Optional[str]
    similarity: float
    vector_score: float
    lexical_score: float
    trigger_hit: float
    effective_version: Optional[str] = None
    binding_status: Optional[str] = None


class BootstrapTemplateUpdateRequest(BaseModel):
    """统一模板更新请求。"""

    default_version: Optional[str] = Field(default=None, min_length=1, max_length=64)
    skills: List[Dict[str, Any]] = Field(default_factory=list)


class BootstrapTemplateResponse(BaseModel):
    """统一模板响应。"""

    default_version: str
    skills: List[Dict[str, Any]]


class SyncTemplateRequest(BaseModel):
    """模板同步请求。"""

    overwrite_existing: bool = False


@router.get("/skills", response_model=List[SkillResponse])
def list_skills(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, le=200),
    search: Optional[str] = None,
    has_embedding: Optional[bool] = None,
    user_id: Optional[int] = Query(None, ge=1),
    db: Session = Depends(get_db),
):
    """获取技能列表。"""

    query = db.query(AgentSkill)

    if search:
        query = query.filter(
            (AgentSkill.name.ilike(f"%{search}%"))
            | (AgentSkill.description.ilike(f"%{search}%"))
            | (AgentSkill.skill_id.ilike(f"%{search}%"))
        )

    if has_embedding is not None:
        if has_embedding:
            query = query.filter(AgentSkill.embedding.isnot(None))
        else:
            query = query.filter(AgentSkill.embedding.is_(None))

    skills = query.order_by(AgentSkill.name).offset(skip).limit(limit).all()

    skill_ids = [skill.skill_id for skill in skills]
    published_version_map: Dict[str, str] = {}
    binding_map: Dict[str, UserSkillBinding] = {}

    if skill_ids and SkillService._is_skill_versioning_enabled():
        try:
            version_rows = (
                db.query(AgentSkillVersion)
                .filter(
                    AgentSkillVersion.skill_id.in_(skill_ids),
                    AgentSkillVersion.status == SkillService.VERSION_STATUS_PUBLISHED,
                )
                .all()
            )
            for row in version_rows:
                current = published_version_map.get(row.skill_id)
                if current is None:
                    published_version_map[row.skill_id] = row.version
                    continue

                current_row = next((item for item in version_rows if item.skill_id == row.skill_id and item.version == current), None)
                current_ts = (
                    current_row.published_at or current_row.updated_at or current_row.created_at
                    if current_row is not None
                    else None
                )
                row_ts = row.published_at or row.updated_at or row.created_at
                if current_ts is None or (row_ts is not None and row_ts > current_ts):
                    published_version_map[row.skill_id] = row.version
        except Exception as exc:  # pragma: no cover - 兼容迁移期
            logger.warning("查询发布版本失败，回退兼容响应: %s", exc)

    if skill_ids and user_id is not None and SkillService._is_user_skill_binding_enabled():
        try:
            binding_rows = (
                db.query(UserSkillBinding)
                .filter(
                    UserSkillBinding.user_id == user_id,
                    UserSkillBinding.skill_id.in_(skill_ids),
                )
                .all()
            )
            binding_map = {row.skill_id: row for row in binding_rows}
        except Exception as exc:  # pragma: no cover - 兼容迁移期
            logger.warning("查询用户技能绑定失败，忽略绑定信息: %s", exc)

    response: List[SkillResponse] = []
    for skill in skills:
        published_version = published_version_map.get(skill.skill_id)
        binding = binding_map.get(skill.skill_id)
        bound_version = binding.version if binding is not None else None
        binding_status = binding.binding_status if binding is not None else None

        effective_version = published_version
        if (
            binding is not None
            and binding.binding_status == SkillService.BINDING_STATUS_ENABLED
            and bool(binding.is_enabled)
            and bound_version
        ):
            effective_version = bound_version

        response.append(
            SkillResponse(
                id=skill.id,
                skill_id=skill.skill_id,
                name=skill.name,
                description=skill.description,
                content_preview=skill.content[:200] + "..." if len(skill.content) > 200 else skill.content,
                file_hash=skill.file_hash,
                has_embedding=skill.embedding is not None,
                embedding_dim=len(skill.embedding) if skill.embedding is not None else None,
                is_enabled=bool(skill.is_enabled),
                auto_enabled=bool(skill.auto_enabled),
                priority=int(skill.priority or 100),
                scope=skill.scope or SkillService.DEFAULT_SCOPE,
                trigger_phrases=[str(item) for item in (skill.trigger_phrases or [])],
                conflicts_with=[str(item) for item in (skill.conflicts_with or [])],
                published_version=published_version,
                bound_version=bound_version,
                binding_status=binding_status,
                effective_version=effective_version,
                created_at=skill.created_at.isoformat() if skill.created_at else None,
                updated_at=skill.updated_at.isoformat() if skill.updated_at else None,
            )
        )

    return response


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
        embedding_dim=len(skill.embedding) if skill.embedding is not None else None,
        is_enabled=bool(skill.is_enabled),
        auto_enabled=bool(skill.auto_enabled),
        priority=int(skill.priority or 100),
        scope=skill.scope or SkillService.DEFAULT_SCOPE,
        trigger_phrases=[str(item) for item in (skill.trigger_phrases or [])],
        conflicts_with=[str(item) for item in (skill.conflicts_with or [])],
    )


@router.get("/skills/{skill_id}/versions", response_model=List[SkillVersionItem])
def list_skill_versions(skill_id: str, db: Session = Depends(get_db)):
    """获取技能版本列表。"""

    try:
        versions = SkillService.list_skill_versions(db, skill_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except RuntimeError as exc:
        raise HTTPException(status_code=409, detail=str(exc))

    return [SkillVersionItem(**item) for item in versions]


@router.post("/skills/{skill_id}/versions/publish")
def publish_skill_version(skill_id: str, request: PublishVersionRequest, db: Session = Depends(get_db)):
    """发布指定技能版本。"""

    try:
        payload = SkillService.publish_skill_version(
            db=db,
            skill_id=skill_id,
            version=request.version,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except RuntimeError as exc:
        raise HTTPException(status_code=409, detail=str(exc))

    logger.info("技能版本发布: skill_id=%s version=%s", skill_id, request.version)
    return payload


@router.post("/skills/{skill_id}/versions/rollback")
def rollback_skill_version(skill_id: str, request: RollbackVersionRequest, db: Session = Depends(get_db)):
    """回滚技能到指定版本或最近可用版本。"""

    try:
        payload = SkillService.rollback_skill_version(
            db=db,
            skill_id=skill_id,
            target_version=request.target_version,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except RuntimeError as exc:
        raise HTTPException(status_code=409, detail=str(exc))

    logger.info(
        "技能版本回滚: skill_id=%s target=%s active=%s",
        skill_id,
        request.target_version,
        payload.get("active_version"),
    )
    return payload


@router.get("/bindings", response_model=List[SkillBindingItem])
def list_skill_bindings(
    user_id: Optional[int] = Query(None, ge=1),
    skill_id: Optional[str] = None,
    binding_status: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """查询用户技能绑定。"""

    try:
        bindings = SkillService.list_user_skill_bindings(
            db=db,
            user_id=user_id,
            skill_id=skill_id,
            binding_status=binding_status,
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=409, detail=str(exc))

    return [SkillBindingItem(**item) for item in bindings]


@router.get("/bootstrap-template", response_model=BootstrapTemplateResponse)
def get_bootstrap_template():
    """读取统一用户 Skill 初始化模板。"""

    payload = normalize_bootstrap_template(load_bootstrap_template_from_config())
    return BootstrapTemplateResponse(
        default_version=str(payload.get("default_version") or SkillService.DEFAULT_VERSION),
        skills=list(payload.get("skills") or []),
    )


@router.put("/bootstrap-template", response_model=BootstrapTemplateResponse)
def update_bootstrap_template(request: BootstrapTemplateUpdateRequest, db: Session = Depends(get_db)):
    """更新统一用户 Skill 初始化模板。"""

    normalized = normalize_bootstrap_template(request.model_dump())
    config_repo.upsert_config(
        db=db,
        key=SkillService.USER_BOOTSTRAP_TEMPLATE_KEY,
        value=json.dumps(normalized, ensure_ascii=False),
        value_type="json",
        category="skill",
        description="用户 Skill 初始化模板（默认版本 + 技能列表）",
    )
    db.commit()

    logger.info(
        "技能模板更新: default_version=%s count=%d",
        normalized.get("default_version"),
        len(normalized.get("skills") or []),
    )
    return BootstrapTemplateResponse(
        default_version=str(normalized.get("default_version") or SkillService.DEFAULT_VERSION),
        skills=list(normalized.get("skills") or []),
    )


@router.post("/users/{user_id}/sync-template")
def sync_user_template(
    user_id: int,
    request: SyncTemplateRequest | None = None,
    db: Session = Depends(get_db),
):
    """对指定用户执行模板对齐（默认仅补齐缺失绑定）。"""

    normalized_request = request or SyncTemplateRequest()
    template = normalize_bootstrap_template(load_bootstrap_template_from_config())
    skills = list(template.get("skills") or [])
    if not skills:
        return {
            "user_id": user_id,
            "total": 0,
            "synced_count": 0,
            "skipped_count": 0,
            "failed_count": 0,
            "overwrite_existing": normalized_request.overwrite_existing,
        }

    try:
        existing_bindings = SkillService.list_user_skill_bindings(db=db, user_id=user_id)
    except RuntimeError as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    existing_skill_ids = {
        str(item.get("skill_id") or "").strip()
        for item in existing_bindings
        if str(item.get("skill_id") or "").strip()
    }

    synced_count = 0
    skipped_count = 0
    failed_count = 0

    for item in skills:
        skill_id = str(item.get("skill_id") or "").strip()
        if not skill_id:
            skipped_count += 1
            continue

        if not normalized_request.overwrite_existing and skill_id in existing_skill_ids:
            skipped_count += 1
            continue

        try:
            SkillService.bind_user_skill(
                db=db,
                user_id=user_id,
                skill_id=skill_id,
                version=str(item.get("version") or template.get("default_version") or SkillService.DEFAULT_VERSION),
                is_enabled=bool(item.get("enabled", True)),
                priority_override=item.get("priority_override"),
                config_override=dict(item.get("config_override") or {}),
            )
            synced_count += 1
        except (ValueError, RuntimeError) as exc:
            failed_count += 1
            logger.warning("模板同步失败 user_id=%s skill_id=%s error=%s", user_id, skill_id, exc)

    return {
        "user_id": user_id,
        "total": len(skills),
        "synced_count": synced_count,
        "skipped_count": skipped_count,
        "failed_count": failed_count,
        "overwrite_existing": normalized_request.overwrite_existing,
    }


@router.post("/bindings")
def bind_skill(request: BindSkillRequest, db: Session = Depends(get_db)):
    """绑定用户技能版本。"""

    try:
        payload = SkillService.bind_user_skill(
            db=db,
            user_id=request.user_id,
            skill_id=request.skill_id,
            version=request.version,
            is_enabled=request.is_enabled,
            priority_override=request.priority_override,
            config_override=request.config_override,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except RuntimeError as exc:
        raise HTTPException(status_code=409, detail=str(exc))

    logger.info(
        "用户技能绑定: user_id=%s skill_id=%s version=%s",
        request.user_id,
        request.skill_id,
        request.version,
    )
    return payload


@router.post("/bindings/rollback")
def rollback_skill_binding(request: RollbackBindingRequest, db: Session = Depends(get_db)):
    """回滚用户技能绑定。"""

    try:
        payload = SkillService.rollback_user_skill_binding(
            db=db,
            user_id=request.user_id,
            skill_id=request.skill_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except RuntimeError as exc:
        raise HTTPException(status_code=409, detail=str(exc))

    logger.info(
        "用户技能绑定回滚: user_id=%s skill_id=%s",
        request.user_id,
        request.skill_id,
    )
    return payload


@router.patch("/skills/{skill_id}/meta")
def update_skill_metadata(
    skill_id: str,
    request: SkillMetadataUpdateRequest,
    db: Session = Depends(get_db),
):
    """更新技能元数据。"""

    skill = db.query(AgentSkill).filter(AgentSkill.skill_id == skill_id).first()
    if not skill:
        raise HTTPException(status_code=404, detail="技能不存在")

    updates = request.model_dump(exclude_none=True)
    if not updates:
        return {"skill_id": skill_id, "updated": False, "updated_fields": []}

    if "scope" in updates:
        updates["scope"] = updates["scope"].strip().lower()

    if "trigger_phrases" in updates:
        updates["trigger_phrases"] = [
            phrase.strip() for phrase in updates["trigger_phrases"] if phrase and phrase.strip()
        ]

    if "conflicts_with" in updates:
        normalized_conflicts = [
            value.strip() for value in updates["conflicts_with"] if value and value.strip()
        ]
        if skill_id in normalized_conflicts:
            raise HTTPException(status_code=400, detail="conflicts_with 不能包含自身")
        updates["conflicts_with"] = list(dict.fromkeys(normalized_conflicts))

    for field, value in updates.items():
        setattr(skill, field, value)

    db.commit()

    logger.info("技能元数据更新: %s, fields=%s", skill_id, list(updates.keys()))
    return {"skill_id": skill_id, "updated": True, "updated_fields": list(updates.keys())}


@router.get("/vector-status", response_model=VectorStatusResponse)
def get_vector_status(db: Session = Depends(get_db)):
    """获取向量状态概览。"""

    total = db.query(AgentSkill).count()
    with_embedding = db.query(AgentSkill).filter(AgentSkill.embedding.isnot(None)).count()
    without_embedding = total - with_embedding

    sample = db.query(AgentSkill).filter(AgentSkill.embedding.isnot(None)).first()
    embedding_dim = len(sample.embedding) if sample is not None and sample.embedding is not None else None

    try:
        test_embedding = get_embedding("test")
        current_model_dim = len(test_embedding) if test_embedding else None
    except Exception:
        current_model_dim = None

    dimension_mismatch = (
        embedding_dim is not None
        and current_model_dim is not None
        and embedding_dim != current_model_dim
    )

    return VectorStatusResponse(
        total_skills=total,
        with_embedding=with_embedding,
        without_embedding=without_embedding,
        embedding_dim=embedding_dim,
        dimension_mismatch=dimension_mismatch,
        current_model_dim=current_model_dim,
    )


@router.post("/regenerate-embeddings")
def regenerate_embeddings(
    request: RegenerateRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """重新生成技能向量（后台任务）。"""

    if request.skill_ids:
        skills = db.query(AgentSkill).filter(AgentSkill.skill_id.in_(request.skill_ids)).all()
    else:
        skills = db.query(AgentSkill).all()

    if not skills:
        raise HTTPException(status_code=400, detail="没有找到技能")

    if len(skills) <= 10:
        success_count = 0
        errors: List[str] = []

        for skill in skills:
            try:
                embedding = get_embedding(skill.description or skill.name)
                if embedding:
                    skill.embedding = embedding
                    success_count += 1
            except Exception as exc:  # pragma: no cover - 外部依赖异常
                errors.append(f"{skill.skill_id}: {str(exc)}")

        db.commit()

        return {
            "message": "重新生成完成",
            "success_count": success_count,
            "total": len(skills),
            "errors": errors if errors else None,
        }

    skill_ids = [skill.skill_id for skill in skills]
    background_tasks.add_task(_regenerate_embeddings_task, skill_ids)
    return {
        "message": f"后台任务已启动，正在重新生成 {len(skills)} 个技能的向量",
        "total": len(skills),
        "status": "processing",
    }


def _regenerate_embeddings_task(skill_ids: List[str]) -> None:
    """后台任务：重新生成向量。"""

    from app.db.session import SessionLocal

    logger.info("开始重新生成 %d 个技能的向量...", len(skill_ids))

    with SessionLocal() as db:
        success = 0
        errors = 0

        for skill_id in skill_ids:
            try:
                skill = db.query(AgentSkill).filter(AgentSkill.skill_id == skill_id).first()
                if not skill:
                    continue

                embedding = get_embedding(skill.description or skill.name)
                if embedding:
                    skill.embedding = embedding
                    success += 1
                    db.commit()
            except Exception as exc:  # pragma: no cover - 外部依赖异常
                errors += 1
                logger.error("重新生成向量失败 %s: %s", skill_id, exc)

        logger.info("向量重新生成完成: 成功 %d, 失败 %d", success, errors)


@router.delete("/skills/{skill_id}")
def delete_skill(skill_id: str, db: Session = Depends(get_db)):
    """删除技能。"""

    skill = db.query(AgentSkill).filter(AgentSkill.skill_id == skill_id).first()
    if not skill:
        raise HTTPException(status_code=404, detail="技能不存在")

    db.delete(skill)
    db.commit()

    logger.info("删除技能: %s", skill_id)
    return {"message": "技能已删除", "skill_id": skill_id}


@router.post("/skills/{skill_id}/regenerate")
def regenerate_single_skill(skill_id: str, db: Session = Depends(get_db)):
    """重新生成单个技能的向量。"""

    skill = db.query(AgentSkill).filter(AgentSkill.skill_id == skill_id).first()
    if not skill:
        raise HTTPException(status_code=404, detail="技能不存在")

    try:
        embedding = get_embedding(skill.description or skill.name)
        if not embedding:
            raise HTTPException(status_code=500, detail="向量生成失败")

        skill.embedding = embedding
        db.commit()

        return {
            "message": "向量已重新生成",
            "skill_id": skill_id,
            "embedding_dim": len(embedding),
        }
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("重新生成向量失败: %s", skill_id)
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/search")
def search_skills(
    query: str = Query(..., min_length=1),
    top_k: int = Query(5, ge=1, le=20),
    threshold: Optional[float] = Query(None, ge=0, le=1),
    scope: str = Query("global"),
    user_id: Optional[int] = Query(None, ge=1),
):
    """搜索技能（优先使用 hybrid 检索，返回简化结果）。"""

    debug = SkillService.search_skills_debug(
        query=query,
        top_k=top_k,
        threshold=threshold,
        scope=scope,
        auto_only=False,
        user_id=user_id,
    )

    results = [
        SearchResultItem(
            skill_id=item["skill_id"],
            name=item["name"],
            description=item.get("description"),
            similarity=float(item.get("score", 0.0)),
            vector_score=float(item.get("vector_score", 0.0)),
            lexical_score=float(item.get("lexical_score", 0.0)),
            trigger_hit=float(item.get("trigger_hit", 0.0)),
            effective_version=item.get("effective_version"),
            binding_status=item.get("binding_status"),
        ).model_dump()
        for item in debug.get("results", [])
    ]

    return {
        "query": query,
        "scope": scope,
        "results": results,
        "count": len(results),
    }


@router.get("/search/hybrid")
def search_skills_hybrid(
    query: str = Query(..., min_length=1),
    top_k: int = Query(5, ge=1, le=20),
    threshold: Optional[float] = Query(None, ge=0, le=1),
    scope: str = Query("global"),
    auto_only: bool = Query(False),
    user_id: Optional[int] = Query(None, ge=1),
):
    """Hybrid 检索调试接口，返回召回与裁决明细。"""

    return SkillService.search_skills_debug(
        query=query,
        top_k=top_k,
        threshold=threshold,
        scope=scope,
        auto_only=auto_only,
        user_id=user_id,
    )
