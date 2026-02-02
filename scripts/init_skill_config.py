import logging
import sys
from pathlib import Path
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Add project root
sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.core.config import DATABASE_URL

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def init_skill_config():
    """初始化技能检索阈值配置到数据库。"""
    engine = create_engine(DATABASE_URL)
    with engine.connect() as conn:
        # Check if config exists
        result = conn.execute(text(
            "SELECT 1 FROM t_system_config WHERE config_key = 'skill_similarity_threshold'"
        )).scalar()
        
        if result:
            logger.info("配置 'skill_similarity_threshold' 已存在，跳过。")
            return

        # Insert default config
        logger.info("正在插入 'skill_similarity_threshold' 配置 (默认 0.55)...")
        conn.execute(text("""
            INSERT INTO t_system_config 
            (config_key, config_value, value_type, category, description, is_secret, create_time, update_time)
            VALUES 
            ('skill_similarity_threshold', '0.55', 'number', 'ai', '技能检索的向量相似度阈值', false, now(), now())
        """))
        conn.commit()
        logger.info("配置初始化完成。")

if __name__ == "__main__":
    init_skill_config()
