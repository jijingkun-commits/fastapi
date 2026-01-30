
import asyncio
import logging
import sys
import os
from pathlib import Path

# Add project root to python path
project_root = str(Path(__file__).resolve().parents[1])
sys.path.append(project_root)

# Set logging
logging.basicConfig(level=logging.ERROR) # Only show errors to keep output clean
logger = logging.getLogger(__name__)

from app.services.skill_service import SkillService
# from app.core.config import settings

from app.services.llm_config_service import LLMConfigService
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.core.config import DATABASE_URL

async def verify_skill_loading():
    print("=== 开始验证技能加载逻辑 (Skill Loading Verification) ===")
    
    # Init LLM Config for Embeddings
    try:
        engine = create_engine(DATABASE_URL)
        SessionLocal = sessionmaker(bind=engine)
        session = SessionLocal()
        LLMConfigService.load_from_db(session)
        session.close()
        print("✅ LLM Config Loaded")
    except Exception as e:
        print(f"⚠️ Failed to load LLM Config: {e}")
        return
    
    # Test Case 1: General Query (Should NOT trigger code-review)
    query_1 = "查询知识库，用户已注销无法使用该功能的问题要怎么解决？"
    print(f"\n[TC-SKILL-01] 测试通用查询: '{query_1}'")
    try:
        skills_1 = SkillService.search_skills(query_1, top_k=3, threshold=0.4)
        found_ids_1 = [s.skill_id for s in skills_1]
        print(f"   -> 召回技能: {found_ids_1}")
        
        if 'code-review' in found_ids_1:
            print("   ❌ FAILED: 'code-review' 被错误加载！")
        else:
            print("   ✅ PASSED: 'code-review' 未被加载。")
    except Exception as e:
        print(f"   ⚠️ ERROR: 查询执行失败 - {e}")

    # Test Case 2: Code Query (Should trigger code-review)
    query_2 = "帮我 Review 这段 Python 代码"
    print(f"\n[TC-SKILL-02] 测试编程查询: '{query_2}'")
    try:
        skills_2 = SkillService.search_skills(query_2, top_k=3, threshold=0.4)
        found_ids_2 = [s.skill_id for s in skills_2]
        print(f"   -> 召回技能: {found_ids_2}")
        
        if 'code-review' in found_ids_2:
             print("   ✅ PASSED: 'code-review' 正常加载。")
        else:
            print("   ❌ FAILED: 'code-review' 未被加载！")
    except Exception as e:
        print(f"   ⚠️ ERROR: 查询执行失败 - {e}")
        
    print("\n=== 验证结束 ===")

if __name__ == "__main__":
    asyncio.run(verify_skill_loading())
