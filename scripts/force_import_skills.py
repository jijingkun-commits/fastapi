import sys
from pathlib import Path
from sqlalchemy import text

project_root = Path(__file__).parent.absolute()
sys.path.insert(0, str(project_root))

from app.services.skill_service import SkillService
from app.db.session import get_db_context

def import_skills():
    print("Importing skills...")
    skills_dir = project_root / "app/ai/skills"
    
    with get_db_context() as db:
        # Initialize LLM config to enable embedding generation
        from app.services.llm_config_service import LLMConfigService
        LLMConfigService.load_from_db(db)
        
        # Force import to ensure embeddings are generated
        count = SkillService.import_all_skills(skills_dir, force=True)
    print(f"Imported {count} skills.")

if __name__ == "__main__":
    import_skills()
