"""系统配置数据访问层（中文注释）。"""
from typing import Optional, List
from sqlalchemy.orm import Session

from app.models.system_config import SystemConfig


def get_all_configs(db: Session) -> List[SystemConfig]:
    """获取所有配置项。"""
    return db.query(SystemConfig).all()


def get_configs_by_category(db: Session, category: str) -> List[SystemConfig]:
    """按分类获取配置项。"""
    return db.query(SystemConfig).filter(SystemConfig.category == category).all()


def get_config_by_key(db: Session, key: str) -> Optional[SystemConfig]:
    """根据 key 获取单个配置。"""
    return db.query(SystemConfig).filter(SystemConfig.config_key == key).first()


def upsert_config(db: Session, key: str, value: str, value_type: str = "string",
                  category: str = None, description: str = None) -> SystemConfig:
    """插入或更新配置项。"""
    config = get_config_by_key(db, key)
    if config:
        config.config_value = value
        if value_type:
            config.value_type = value_type
        if category:
            config.category = category
        if description:
            config.description = description
    else:
        config = SystemConfig(
            config_key=key,
            config_value=value,
            value_type=value_type,
            category=category,
            description=description
        )
        db.add(config)
    db.flush()
    return config
