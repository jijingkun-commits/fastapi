"""迁移前数据验证脚本（中文注释）。

在执行约束迁移前，验证存量数据是否满足约束条件。
避免迁移中断或数据丢失。

用法：
    python scripts/validate_migration_data.py --check-all
    python scripts/validate_migration_data.py --check todo_status
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import argparse
import logging
from sqlalchemy import create_engine, text
from app.core.config import DATABASE_URL

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)


def get_engine():
    return create_engine(DATABASE_URL)


def check_todo_status(engine) -> bool:
    """检查 t_todo.status 是否有非法值。"""
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT status, COUNT(*) as cnt 
            FROM t_todo 
            WHERE status NOT IN ('pending', 'completed', 'cancelled', 'todo', 'in_progress', 'done')
            GROUP BY status
        """))
        invalid = result.fetchall()
        
        if invalid:
            logger.error("❌ 发现非法 status 值：")
            for row in invalid:
                logger.error(f"   - status='{row[0]}': {row[1]} 条")
            return False
        
        logger.info("✅ t_todo.status 检查通过")
        return True


def check_chat_message_integrity(engine) -> bool:
    """检查 t_chat_message 数据完整性。"""
    with engine.connect() as conn:
        # 检查是否有 NULL thread_id
        result = conn.execute(text("""
            SELECT COUNT(*) FROM t_chat_message WHERE thread_id IS NULL
        """))
        null_count = result.scalar()
        
        if null_count > 0:
            logger.error(f"❌ 发现 {null_count} 条 thread_id 为 NULL 的消息")
            return False
        
        logger.info("✅ t_chat_message 完整性检查通过")
        return True


def check_duplicate_idempotency_keys(engine) -> bool:
    """检查幂等键是否有重复。"""
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT idempotency_key, user_id, COUNT(*) as cnt
            FROM t_idempotency_key
            GROUP BY idempotency_key, user_id
            HAVING COUNT(*) > 1
        """))
        duplicates = result.fetchall()
        
        if duplicates:
            logger.error("❌ 发现重复幂等键：")
            for row in duplicates:
                logger.error(f"   - key='{row[0]}', user_id={row[1]}: {row[2]} 条")
            return False
        
        logger.info("✅ 幂等键唯一性检查通过")
        return True


def check_all(engine) -> bool:
    """执行所有检查。"""
    results = [
        check_todo_status(engine),
        check_chat_message_integrity(engine),
        check_duplicate_idempotency_keys(engine),
    ]
    return all(results)


def main():
    parser = argparse.ArgumentParser(description="迁移前数据验证")
    parser.add_argument("--check-all", action="store_true", help="执行所有检查")
    parser.add_argument("--check", type=str, help="执行指定检查")
    args = parser.parse_args()
    
    engine = get_engine()
    
    if args.check_all:
        success = check_all(engine)
    elif args.check:
        check_map = {
            "todo_status": check_todo_status,
            "chat_integrity": check_chat_message_integrity,
            "idempotency": check_duplicate_idempotency_keys,
        }
        if args.check in check_map:
            success = check_map[args.check](engine)
        else:
            logger.error(f"未知检查项: {args.check}")
            logger.info(f"可用检查项: {', '.join(check_map.keys())}")
            sys.exit(1)
    else:
        parser.print_help()
        sys.exit(0)
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
