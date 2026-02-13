"""初始化 Skill 检索配置（中文注释）。"""

import logging
import sys
from pathlib import Path

from sqlalchemy import create_engine, text

# Add project root
sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.core.config import DATABASE_URL

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

SKILL_CONFIGS = [
    ("skill_similarity_threshold", "0.55", "number", "ai", "技能检索向量相似度阈值"),
    ("skill.retrieval_mode", "hybrid", "string", "ai", "技能检索模式：vector/hybrid"),
    ("skill.top_k", "3", "number", "ai", "技能检索返回数量"),
    ("skill.context_max_length", "2400", "number", "ai", "技能上下文最大字符长度"),
    ("skill.section_max_count", "2", "number", "ai", "单技能最多注入章节数"),
    ("skill.hybrid.vector_weight", "0.65", "number", "ai", "Hybrid 检索向量分权重"),
    ("skill.hybrid.lexical_weight", "0.25", "number", "ai", "Hybrid 检索关键词分权重"),
    ("skill.hybrid.trigger_weight", "0.10", "number", "ai", "Hybrid 检索触发短语加权"),
    ("skill.hybrid.candidate_multiplier", "3", "number", "ai", "Hybrid 检索候选扩容倍率"),
]


def init_skill_config() -> None:
    """初始化 Skill 相关系统配置到数据库。"""

    engine = create_engine(DATABASE_URL)
    with engine.connect() as conn:
        inserted = 0

        for key, value, value_type, category, description in SKILL_CONFIGS:
            exists = conn.execute(
                text("SELECT 1 FROM t_system_config WHERE config_key = :key"),
                {"key": key},
            ).scalar()
            if exists:
                logger.info("配置 '%s' 已存在，跳过。", key)
                continue

            conn.execute(
                text(
                    """
                    INSERT INTO t_system_config
                    (config_key, config_value, value_type, category, description, is_secret, create_time, update_time)
                    VALUES
                    (:key, :value, :value_type, :category, :description, false, now(), now())
                    """
                ),
                {
                    "key": key,
                    "value": value,
                    "value_type": value_type,
                    "category": category,
                    "description": description,
                },
            )
            inserted += 1
            logger.info("已插入配置 '%s'。", key)

        conn.commit()
        logger.info("Skill 配置初始化完成，新增 %d 项。", inserted)


if __name__ == "__main__":
    init_skill_config()
