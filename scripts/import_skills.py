#!/usr/bin/env python3
"""导入技能脚本：将 Skills 目录中的技能向量化并存入数据库（中文注释）。

用法:
    python scripts/import_skills.py --source app/data/skills
    python scripts/import_skills.py --source app/data/skills --force
"""
import argparse
import logging
import sys
from pathlib import Path

# 添加项目根目录到 path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.db.session import get_db_context
from app.services.llm_config_service import LLMConfigService
from app.services.skill_service import SkillService

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(description="导入 Agent Skills 到数据库")
    parser.add_argument(
        "--source", 
        type=str, 
        default="app/data/skills",
        help="技能目录路径"
    )
    parser.add_argument(
        "--force", 
        action="store_true",
        help="强制更新所有技能（忽略 hash 检查）"
    )
    parser.add_argument(
        "--filter", 
        type=str, 
        help="仅导入指定的 skill_id，以逗号分隔（如: react-best-practices,api-patterns）"
    )
    parser.add_argument(
        "--file", 
        type=str, 
        help="从文件读取白名单（每行一个 skill_id）"
    )
    args = parser.parse_args()
    
    skills_dir = Path(args.source)
    if not skills_dir.exists():
        logger.error(f"技能目录不存在: {skills_dir}")
        sys.exit(1)
    
    # 提取白名单
    whitelist = None
    if args.filter:
        whitelist = [s.strip() for s in args.filter.split(",") if s.strip()]
    elif args.file:
        file_path = Path(args.file)
        if file_path.exists():
            content = file_path.read_text(encoding="utf-8")
            whitelist = [
                line.strip() 
                for line in content.split("\n") 
                if line.strip() and not line.strip().startswith("#")
            ]
            logger.info(f"从文件加载白名单 ({len(whitelist)} 个): {file_path}")
        else:
            logger.error(f"白名单文件不存在: {file_path}")
            sys.exit(1)
    
    # 初始化 LLM 配置缓存（用于获取 embedding 模型）
    logger.info("初始化 LLM 配置...")
    with get_db_context() as db:
        LLMConfigService.load_from_db(db)
    
    if not LLMConfigService.is_type_configured("embedding"):
        logger.error("未配置 embedding 模型，请在 t_llm_models 中添加类型为 'embedding' 的模型")
        sys.exit(1)
    
    # 导入技能
    logger.info(f"开始导入技能，源目录: {skills_dir}, 强制更新: {args.force}, 过滤: {whitelist}")
    count = SkillService.import_all_skills(skills_dir, force=args.force, whitelist=whitelist)
    
    logger.info(f"导入完成，共处理 {count} 个技能")


if __name__ == "__main__":
    main()
