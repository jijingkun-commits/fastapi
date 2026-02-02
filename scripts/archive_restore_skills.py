import sys
import os
from pathlib import Path
from sqlalchemy import select

# Add project root to path
project_root = Path(__file__).parent.parent.absolute()
sys.path.insert(0, str(project_root))

from app.db.session import get_db_context
from app.models.agent_skill import AgentSkill

# Whitelist of skill IDs to restore (high value ones)
# Based on earlier analysis of DB content
SKILLS_TO_RESTORE = [
    # Office / Productivity
    "meeting-minutes",
    "email-pro",
    "copywriter",
    "translator",
    "productivity-guide", # Already imported, but good to ensure consistency
    
    # Coding / Quality
    "code-review",
    "regex-wizard",
    "tailwind-patterns",
    "sql-expert",
    "python-debug",
    "api-doc",
    "clean-code",
    "testing-patterns",
    "react-best-practices",
    "langgraph",
    "fastapi-expert", # Already imported
    "nextjs-expert",  # Already imported
    "python-expert",  # Already imported
    
    # Specialized
    "data-insight"
]

def restore_skills():
    print("Starting skill restoration from DB...")
    
    skills_dir = project_root / "app/ai/skills"
    
    with get_db_context() as db:
        for skill_id in SKILLS_TO_RESTORE:
            skill = db.execute(
                select(AgentSkill).where(AgentSkill.skill_id == skill_id)
            ).scalar_one_or_none()
            
            if not skill:
                print(f"⚠️ Skill not found in DB: {skill_id}")
                continue
                
            # Define target path
            target_dir = skills_dir / skill_id
            target_file = target_dir / "SKILL.md"
            
            # Create directory
            target_dir.mkdir(parents=True, exist_ok=True)
            
            # Ensure content has frontmatter if missing
            content = skill.content
            if not content.startswith("---"):
                # Reconstruct frontmatter
                frontmatter = f"---\nname: {skill.name}\ndescription: {skill.description}\n---\n\n"
                content = frontmatter + content
            
            # Write file
            if target_file.exists():
                print(f"ℹ️ Skill file already exists (skipping overwrite): {target_file}")
            else:
                target_file.write_text(content, encoding="utf-8")
                print(f"✅ Restored: {skill_id} -> {target_file}")

if __name__ == "__main__":
    restore_skills()
