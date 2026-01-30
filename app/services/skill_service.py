"""技能服务：管理 Agent Skills 的导入、同步和检索（中文注释）。"""
import hashlib
import logging
from pathlib import Path
from typing import List, Optional

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.db.session import get_db_context
from app.models.agent_skill import AgentSkill
from app.ai.utils.embedding_util import get_embedding
from app.core.config import SKILL_SIMILARITY_THRESHOLD
from app.services.system_config_service import SystemConfigService

logger = logging.getLogger(__name__)


class SkillService:
    """技能管理服务。
    
    提供技能的导入、同步和向量检索功能。
    """
    
    @staticmethod
    def _compute_file_hash(content: str) -> str:
        """计算内容的 MD5 哈希值。"""
        return hashlib.md5(content.encode("utf-8")).hexdigest()
    
    @staticmethod
    def _parse_skill_file(skill_path: Path) -> Optional[dict]:
        """解析 SKILL.md 文件，提取元数据和内容。
        
        Args:
            skill_path: SKILL.md 文件路径
            
        Returns:
            包含 skill_id, name, description, content 的字典
        """
        if not skill_path.exists():
            return None
            
        content = skill_path.read_text(encoding="utf-8")
        skill_id = skill_path.parent.name
        
        # 解析 YAML frontmatter (如果存在)
        name = skill_id.replace("-", " ").title()
        description = ""
        
        lines = content.split("\n")
        if lines and lines[0].strip() == "---":
            # 有 frontmatter
            end_idx = -1
            for i, line in enumerate(lines[1:], start=1):
                if line.strip() == "---":
                    end_idx = i
                    break
            if end_idx > 0:
                frontmatter = "\n".join(lines[1:end_idx])
                # 简单解析 name 和 description
                for line in frontmatter.split("\n"):
                    if line.startswith("name:"):
                        name = line.split(":", 1)[1].strip().strip("\"'")
                    elif line.startswith("description:"):
                        description = line.split(":", 1)[1].strip().strip("\"'")
        
        # 如果没有 description，使用内容前 200 个字符
        if not description:
            clean_content = content.replace("#", "").strip()
            description = clean_content[:200] if len(clean_content) > 200 else clean_content
        
        return {
            "skill_id": skill_id,
            "name": name,
            "description": description,
            "content": content
        }
    
    @classmethod
    def import_skill(cls, skill_path: Path, db: Session, force: bool = False) -> bool:
        """导入单个技能到数据库。
        
        Args:
            skill_path: SKILL.md 文件路径
            db: 数据库会话
            force: 是否强制更新
            
        Returns:
            是否成功导入
        """
        parsed = cls._parse_skill_file(skill_path)
        if not parsed:
            return False
        
        content = parsed["content"]
        file_hash = cls._compute_file_hash(content)
        
        # 检查是否已存在
        existing = db.execute(
            select(AgentSkill).where(AgentSkill.skill_id == parsed["skill_id"])
        ).scalar_one_or_none()
        
        if existing:
            if not force and existing.file_hash == file_hash:
                logger.debug(f"技能 {parsed['skill_id']} 未变化，跳过")
                return False
            # 更新
            existing.name = parsed["name"]
            existing.description = parsed["description"]
            existing.content = content
            existing.file_hash = file_hash
            existing.embedding = get_embedding(parsed["description"])
            logger.info(f"更新技能: {parsed['skill_id']}")
        else:
            # 新增
            embedding = get_embedding(parsed["description"])
            skill = AgentSkill(
                skill_id=parsed["skill_id"],
                name=parsed["name"],
                description=parsed["description"],
                content=content,
                file_hash=file_hash,
                embedding=embedding
            )
            db.add(skill)
            logger.info(f"导入技能: {parsed['skill_id']}")
        
        db.commit()
        return True
    
    @classmethod
    def import_all_skills(cls, skills_dir: Path, force: bool = False, whitelist: List[str] = None) -> int:
        """从目录导入所有技能。
        
        Args:
            skills_dir: 技能目录路径
            force: 是否强制更新所有
            whitelist: 白名单列表（仅导入列表中的 skill_id），为空则导入所有
            
        Returns:
            导入的技能数量
        """
        if not skills_dir.exists():
            logger.warning(f"技能目录不存在: {skills_dir}")
            return 0
        
        count = 0
        skill_files = list(skills_dir.glob("*/SKILL.md"))
        
        # 过滤白名单
        if whitelist:
            skill_files = [
                f for f in skill_files 
                if f.parent.name in whitelist
            ]
            logger.info(f"应用白名单过滤: {whitelist}")
        
        logger.info(f"发现 {len(skill_files)} 个技能文件")
        
        with get_db_context() as db:
            for skill_path in skill_files:
                try:
                    if cls.import_skill(skill_path, db, force):
                        count += 1
                except Exception as e:
                    logger.error(f"导入技能失败 {skill_path}: {e}")
        
        logger.info(f"共导入 {count} 个技能")
        return count
    
    @classmethod
    def sync_changed_skills(cls, skills_dir: Path) -> int:
        """同步变化的技能（增量更新）。
        
        比对文件 hash，仅更新变化的技能。
        """
        return cls.import_all_skills(skills_dir, force=False)
    
    @classmethod
    def search_skills(
        cls, 
        query: str, 
        top_k: int = 2,
        threshold: float = None
    ) -> List[AgentSkill]:
        # 优先使用传入参数 -> 其次 DB 动态配置 -> 最后 env/默认值
        if threshold is None:
            threshold = SystemConfigService.get_float("skill_similarity_threshold", SKILL_SIMILARITY_THRESHOLD)
        """向量检索相关技能。
        
        Args:
            query: 查询文本
            top_k: 返回数量
            threshold: 相似度阈值
            
        Returns:
            匹配的技能列表
        """
        query_embedding = get_embedding(query)
        if not query_embedding:
            return []
        
        with get_db_context() as db:
            # 使用 pgvector 的余弦相似度检索
            # 1 - (embedding <=> query_embedding) 为相似度 (0-1)
            sql = text("""
                SELECT 
                    id, skill_id, name, description, content,
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
                    skill = AgentSkill(
                        id=row.id,
                        skill_id=row.skill_id,
                        name=row.name,
                        description=row.description,
                        content=row.content
                    )
                    skills.append(skill)
                    logger.debug(f"匹配技能: {row.skill_id} (相似度: {row.similarity:.3f})")
            
            return skills
    
    @classmethod
    def get_by_id(cls, skill_id: str) -> Optional[AgentSkill]:
        """根据 skill_id 获取技能。"""
        with get_db_context() as db:
            return db.execute(
                select(AgentSkill).where(AgentSkill.skill_id == skill_id)
            ).scalar_one_or_none()
    
    @classmethod
    def format_skills_as_context(cls, skills: List[AgentSkill], max_length: int = 2000) -> str:
        """将技能列表格式化为上下文字符串。
        
        Args:
            skills: 技能列表
            max_length: 最大长度限制
            
        Returns:
            格式化的上下文字符串
        """
        if not skills:
            return ""
        
        context_parts = []
        total_length = 0
        
        for skill in skills:
            # 截取内容的关键部分
            content_preview = skill.content[:500] if len(skill.content) > 500 else skill.content
            part = f"### {skill.name}\n{content_preview}\n"
            
            if total_length + len(part) > max_length:
                break
            
            context_parts.append(part)
            total_length += len(part)
        
        return "\n".join(context_parts)
