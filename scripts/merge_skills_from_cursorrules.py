import os
from pathlib import Path

# Configuration: Target Skill ID -> Source Directory in /tmp/awesome-cursorrules/rules
SKILL_MAP = {
    "fastapi-expert": "python-fastapi-best-practices-cursorrules-prompt-f",
    "nextjs-expert": "nextjs-app-router-cursorrules-prompt-file",
    "python-expert": "python-cursorrules-prompt-file-best-practices", 
    "git-expert": "git-conventional-commit-messages",
    "technical-writer": "kubernetes-mkdocs-documentation-cursorrules-prompt",
    "writing-coach": "how-to-documentation-cursorrules-prompt-file",
    "productivity-guide": "project-epic-template-cursorrules-prompt-file"
}

SOURCE_BASE = Path("/tmp/awesome-cursorrules/rules")
TARGET_BASE = Path("app/ai/skills")

def merge_skills():
    print("Starting skill merge...")
    
    for skill_id, source_dir_name in SKILL_MAP.items():
        source_dir = SOURCE_BASE / source_dir_name
        target_dir = TARGET_BASE / skill_id
        target_file = target_dir / "SKILL.md"
        
        if not source_dir.exists():
            # Try finding folder with partial match if exact match fails
            found = False
            for p in SOURCE_BASE.iterdir():
                if p.is_dir() and source_dir_name in p.name:
                    source_dir = p
                    found = True
                    break
            if not found:
                print(f"⚠️ Source directory not found for {skill_id}: {source_dir_name}")
                continue

        print(f"Processing {skill_id} from {source_dir}...")
        
        # Create target directory
        target_dir.mkdir(parents=True, exist_ok=True)
        
        # Collect content from all .md and .mdc files
        merged_content = []
        files = sorted(list(source_dir.glob("*.md")) + list(source_dir.glob("*.mdc")))
        
        for f in files:
            if f.name.lower() == "readme.md":
                continue # Skip generic readmes often found
            
            content = f.read_text(encoding="utf-8")
            merged_content.append(f"### {f.name}\n\n{content}\n")
            
        full_body = "\n".join(merged_content)
        
        # Create SKILL.md content
        skill_md = f"""---
name: {skill_id}
description: auto-imported from awesome-cursorrules.
---

{full_body}
"""
        target_file.write_text(skill_md, encoding="utf-8")
        print(f"✅ Created {target_file}")

if __name__ == "__main__":
    merge_skills()
