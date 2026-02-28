"""Add embedding/vision scene bindings for route-based routing.

Revision ID: 20260228_0013
Revises: 20260228_0012
Create Date: 2026-02-28
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20260228_0013"
down_revision = "20260228_0012"
branch_labels = None
depends_on = None


EMBEDDING_SCENE_KEY = "app.ai.utils.embedding_util.get_embedding"
VISION_SCENE_KEY = "app.ai.tools.vision_tool.analyze_image"


def _resolve_model_by_code(conn, model_code: str | None):
    if not model_code:
        return None

    return conn.execute(
        sa.text(
            """
            SELECT id, model_type
            FROM t_llm_model
            WHERE model_code = :model_code
              AND is_active = TRUE
            LIMIT 1
            """
        ),
        {"model_code": model_code},
    ).mappings().first()


def _resolve_default_model_id_by_type(conn, model_type: str) -> int | None:
    model_id = conn.execute(
        sa.text(
            """
            SELECT id
            FROM t_llm_model
            WHERE model_type = :model_type
              AND is_default = TRUE
              AND is_active = TRUE
            ORDER BY id ASC
            LIMIT 1
            """
        ),
        {"model_type": model_type},
    ).scalar()
    if model_id:
        return model_id

    return conn.execute(
        sa.text(
            """
            SELECT id
            FROM t_llm_model
            WHERE model_type = :model_type
              AND is_active = TRUE
            ORDER BY sort_order ASC, id ASC
            LIMIT 1
            """
        ),
        {"model_type": model_type},
    ).scalar()


def _resolve_embedding_scene_model_id(conn) -> int:
    model_id = _resolve_default_model_id_by_type(conn, "embedding")
    if model_id:
        return model_id
    raise RuntimeError("未找到启用的 embedding 模型，无法初始化 Embedding 场景绑定")


def _resolve_vision_scene_model_id(conn) -> int:
    routed_model_code = conn.execute(
        sa.text(
            """
            SELECT config_value
            FROM t_system_config
            WHERE config_key = 'vision'
            LIMIT 1
            """
        )
    ).scalar()
    routed = _resolve_model_by_code(conn, routed_model_code)
    if routed and (routed["model_type"] or "chat") in {"vision", "chat", "reasoning"}:
        return int(routed["id"])

    for model_type in ("vision", "chat", "reasoning"):
        model_id = _resolve_default_model_id_by_type(conn, model_type)
        if model_id:
            return model_id

    raise RuntimeError("未找到可用于 Vision 路由的启用模型（vision/chat/reasoning）")


def _upsert_scene(
    conn,
    *,
    scene_key: str,
    scene_name: str,
    scene_type: str,
    default_model_id: int,
    description: str,
) -> None:
    conn.execute(
        sa.text(
            """
            INSERT INTO t_llm_scene (
                scene_key,
                scene_name,
                scene_type,
                default_model_id,
                description,
                is_active
            ) VALUES (
                :scene_key,
                :scene_name,
                :scene_type,
                :default_model_id,
                :description,
                TRUE
            )
            ON CONFLICT (scene_key)
            DO UPDATE SET
                scene_name = EXCLUDED.scene_name,
                scene_type = EXCLUDED.scene_type,
                default_model_id = EXCLUDED.default_model_id,
                description = EXCLUDED.description,
                is_active = TRUE,
                update_time = NOW()
            """
        ),
        {
            "scene_key": scene_key,
            "scene_name": scene_name,
            "scene_type": scene_type,
            "default_model_id": default_model_id,
            "description": description,
        },
    )


def upgrade() -> None:
    """Insert embedding/vision call-point scene bindings."""

    conn = op.get_bind()

    embedding_model_id = _resolve_embedding_scene_model_id(conn)
    vision_model_id = _resolve_vision_scene_model_id(conn)

    _upsert_scene(
        conn,
        scene_key=EMBEDDING_SCENE_KEY,
        scene_name="文本向量化",
        scene_type="embedding",
        default_model_id=embedding_model_id,
        description="Embedding 向量生成",
    )
    _upsert_scene(
        conn,
        scene_key=VISION_SCENE_KEY,
        scene_name="图片理解",
        scene_type="vision",
        default_model_id=vision_model_id,
        description="Vision 图片分析工具",
    )


def downgrade() -> None:
    """Remove embedding/vision call-point scene bindings."""

    conn = op.get_bind()
    conn.execute(
        sa.text(
            """
            DELETE FROM t_llm_scene
            WHERE scene_key IN (:embedding_key, :vision_key)
            """
        ),
        {
            "embedding_key": EMBEDDING_SCENE_KEY,
            "vision_key": VISION_SCENE_KEY,
        },
    )

