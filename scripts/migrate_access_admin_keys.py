"""迁移问数访问控制历史配置键到 askdata 主键（中文注释）。

用途：将 t_system_config 中历史 `data_access.*` 键的值迁移到 `askdata.*` 主键，
保持“新键主写、旧键兼容读”的配置治理策略。

运行方式：
    python scripts/migrate_access_admin_keys.py --dry-run
    python scripts/migrate_access_admin_keys.py
"""
from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

# 添加项目根目录到导入路径
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from app.db.session import SessionLocal
from app.models.system_config import SystemConfig


@dataclass(frozen=True)
class KeyMapping:
    """历史键与主键的映射关系。"""

    legacy_key: str
    primary_key: str
    description: str


MAPPINGS: tuple[KeyMapping, ...] = (
    KeyMapping(
        legacy_key="data_access.table_whitelist",
        primary_key="askdata.table_whitelist",
        description="数据访问控制-表白名单",
    ),
    KeyMapping(
        legacy_key="data_access.table_blacklist",
        primary_key="askdata.table_blacklist",
        description="数据访问控制-表黑名单",
    ),
    KeyMapping(
        legacy_key="askdata.schema_whitelist",
        primary_key="askdata.schema_blacklist",
        description="数据访问控制-Schema白名单（历史字段名）",
    ),
    KeyMapping(
        legacy_key="data_access.schema_whitelist",
        primary_key="askdata.schema_blacklist",
        description="数据访问控制-Schema白名单（历史字段名）",
    ),
)


def _normalize_list_value(value: str | None) -> str:
    """规范化逗号分隔值，用于等价比较（忽略顺序与空格）。"""

    if not value:
        return ""
    normalized_items = []
    seen = set()
    for item in value.split(","):
        normalized_item = item.strip().lower()
        if not normalized_item or normalized_item in seen:
            continue
        seen.add(normalized_item)
        normalized_items.append(normalized_item)
    normalized_items.sort()
    return ",".join(normalized_items)


def _is_empty(value: str | None) -> bool:
    """判断配置值是否为空。"""

    return value is None or value.strip() == ""


def _load_config_map(db: Session) -> dict[str, SystemConfig]:
    """一次性加载所有迁移相关配置记录。"""

    all_keys = [mapping.legacy_key for mapping in MAPPINGS] + [
        mapping.primary_key for mapping in MAPPINGS
    ]
    stmt = select(SystemConfig).where(SystemConfig.config_key.in_(all_keys))
    rows = db.execute(stmt).scalars().all()
    return {row.config_key: row for row in rows}


def migrate_keys(db: Session, dry_run: bool = False) -> dict[str, int]:
    """执行历史键迁移。"""

    config_map = _load_config_map(db)
    summary = {
        "migrated": 0,
        "conflict": 0,
        "already_synced": 0,
        "legacy_empty": 0,
    }

    for mapping in MAPPINGS:
        legacy_config = config_map.get(mapping.legacy_key)
        primary_config = config_map.get(mapping.primary_key)

        legacy_value = legacy_config.config_value if legacy_config else ""
        primary_value = primary_config.config_value if primary_config else ""

        if _is_empty(legacy_value):
            print(f"- [{mapping.primary_key}] 跳过：历史键为空")
            summary["legacy_empty"] += 1
            continue

        if _is_empty(primary_value):
            print(
                f"- [{mapping.primary_key}] 迁移："
                f"{mapping.legacy_key} -> {mapping.primary_key}"
            )
            summary["migrated"] += 1

            if dry_run:
                continue

            if primary_config is None:
                db.add(
                    SystemConfig(
                        config_key=mapping.primary_key,
                        config_value=legacy_value,
                        value_type=legacy_config.value_type if legacy_config else "string",
                        category="askdata",
                        description=mapping.description,
                        is_secret=legacy_config.is_secret if legacy_config else False,
                    )
                )
            else:
                primary_config.config_value = legacy_value
                if not primary_config.value_type:
                    primary_config.value_type = (
                        legacy_config.value_type if legacy_config else "string"
                    )
                if not primary_config.category:
                    primary_config.category = "askdata"
                if not primary_config.description:
                    primary_config.description = mapping.description
            continue

        if _normalize_list_value(primary_value) == _normalize_list_value(legacy_value):
            print(f"- [{mapping.primary_key}] 跳过：主键值已与历史键一致")
            summary["already_synced"] += 1
            continue

        print(
            f"- [{mapping.primary_key}] 冲突："
            f"主键({primary_value}) 与历史键({legacy_value}) 不一致，保留主键"
        )
        summary["conflict"] += 1

    return summary


def parse_args() -> argparse.Namespace:
    """解析命令行参数。"""

    parser = argparse.ArgumentParser(description="迁移 askdata/data_access 历史配置键")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="仅打印迁移计划，不写入数据库",
    )
    return parser.parse_args()


def main() -> int:
    """脚本入口。"""

    args = parse_args()

    print("=" * 60)
    print("问数配置键迁移（仅 chat_db / DATABASE_URL）")
    print("=" * 60)
    print(f"模式: {'DRY-RUN' if args.dry_run else 'APPLY'}")

    with SessionLocal() as db:
        try:
            summary = migrate_keys(db, dry_run=args.dry_run)
            if args.dry_run:
                db.rollback()
            else:
                db.commit()
        except Exception as exc:
            db.rollback()
            print(f"迁移失败：{exc}")
            return 1

    print("-" * 60)
    print("迁移结果：")
    print(f"  migrated      : {summary['migrated']}")
    print(f"  already_synced: {summary['already_synced']}")
    print(f"  conflict      : {summary['conflict']}")
    print(f"  legacy_empty  : {summary['legacy_empty']}")
    print("=" * 60)
    print("完成")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
