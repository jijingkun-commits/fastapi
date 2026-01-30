
import asyncio
import logging
import sys
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Add project root to python path
project_root = str(Path(__file__).resolve().parents[1])
sys.path.append(project_root)

# Set logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

from app.services.skill_service import SkillService
from app.services.llm_config_service import LLMConfigService
from app.core.config import DATABASE_URL

async def update_skills():
    print("=== 强制更新技能库 (Force Update Skills) ===")
    
    # Init DB & LLM Config
    engine = create_engine(DATABASE_URL)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    try:
        LLMConfigService.load_from_db(session)
        print("✅ LLM Config Loaded")
    except Exception as e:
        print(f"❌ Failed to load LLM Config: {e}")
        return
    finally:
        session.close()

    # Define Skills Dir
    skills_dir = Path(project_root) / "app" / "ai" / "skills"
    
    # Import
    count = SkillService.import_all_skills(skills_dir, force=True)
    print(f"✅ 更新了 {count} 个技能。")

if __name__ == "__main__":
    asyncio.run(update_skills())
