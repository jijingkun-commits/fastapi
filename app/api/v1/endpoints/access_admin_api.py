"""数据访问控制管理 API（中文注释）。

提供：
- 表白名单管理
- 表黑名单管理
- 分析 Schema 白名单管理
- 系统 Schema 黑名单管理
- data_role 策略管理
- SQL 权限试跑
"""

from __future__ import annotations

import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.ai.semantic.data_access_control import (
    DEFAULT_SCHEMA_BLACKLIST,
    DEFAULT_TABLE_BLACKLIST,
    DEFAULT_TABLE_WHITELIST,
    DataAccessControl,
    invalidate_config_cache,
)
from app.core.config import ANALYTICS_SCHEMAS
from app.db.session import get_db
from app.models.system_config import SystemConfig
from app.schemas.access_admin import (
    DataRole,
    DataRolePolicyDeleteResponse,
    DataRolePolicyListResponse,
    DataRolePolicyResponse,
    DataRolePolicyUpsertRequest,
    SQLDryRunRequest,
    SQLDryRunResponse,
)
from app.services.permission_service import get_permission_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/access-admin", tags=["数据访问控制"])


# ==================== 兼容 Schemas ====================

class TableWhitelistResponse(BaseModel):
    """表白名单响应。"""

    tables: List[str]
    source: str  # "database" 或 "default"


class TableBlacklistResponse(BaseModel):
    """表黑名单响应。"""

    tables: List[str]


class SchemaWhitelistResponse(BaseModel):
    """Schema 白名单响应。"""

    schemas: List[str]


class SystemSchemaBlacklistResponse(BaseModel):
    """系统 Schema 黑名单响应。"""

    schemas: List[str]


class UpdateWhitelistRequest(BaseModel):
    """更新白名单请求。"""

    tables: List[str]


class UpdateBlacklistRequest(BaseModel):
    """更新黑名单请求。"""

    tables: List[str]


class UpdateSchemaWhitelistRequest(BaseModel):
    """更新 Schema 白名单请求。"""

    schemas: List[str]


class SQLTestRequest(BaseModel):
    """SQL 测试请求。"""

    sql: str


class SQLTestResponse(BaseModel):
    """SQL 测试响应。"""

    is_valid: bool
    error: Optional[str] = None
    tables_found: List[str]
    tables_allowed: List[str]
    tables_denied: List[str]


class AccessConfigResponse(BaseModel):
    """访问控制配置完整响应。"""

    whitelist: List[str]
    whitelist_source: str
    blacklist: List[str]
    schema_whitelist: List[str]
    system_schema_blacklist: List[str]


# ==================== 配置键常量 ====================

CONFIG_KEY_WHITELIST = "askdata.table_whitelist"
CONFIG_KEY_BLACKLIST = "askdata.table_blacklist"
CONFIG_KEY_SCHEMA_ALLOWLIST = "askdata.analytics_schema_allowlist"
CONFIG_KEY_SYSTEM_SCHEMA_BLACKLIST = "askdata.system_schema_blacklist"

# 向后兼容常量名
CONFIG_KEY_SCHEMA_WHITELIST = CONFIG_KEY_SCHEMA_ALLOWLIST

CONFIG_KEY_ALIASES = {
    CONFIG_KEY_WHITELIST: ("data_access.table_whitelist",),
    CONFIG_KEY_BLACKLIST: ("data_access.table_blacklist",),
    CONFIG_KEY_SCHEMA_ALLOWLIST: (
        "askdata.schema_whitelist",
        "data_access.schema_whitelist",
    ),
    CONFIG_KEY_SYSTEM_SCHEMA_BLACKLIST: ("askdata.schema_blacklist",),
}


# ==================== 辅助函数 ====================


def _get_config_value(db: Session, key: str) -> Optional[str]:
    """从数据库获取配置值（主键优先，兼容旧键）。"""

    lookup_keys = (key, *CONFIG_KEY_ALIASES.get(key, ()))
    for lookup_key in lookup_keys:
        config = db.query(SystemConfig).filter(SystemConfig.config_key == lookup_key).first()
        if config is not None:
            return config.config_value
    return None


def _set_config_value(db: Session, key: str, value: str, description: str = ""):
    """设置数据库配置值（仅写入主键）。"""

    config = db.query(SystemConfig).filter(SystemConfig.config_key == key).first()
    if config:
        config.config_value = value
    else:
        config = SystemConfig(
            config_key=key,
            config_value=value,
            description=description,
            category="askdata",
        )
        db.add(config)
    db.commit()
    invalidate_config_cache()


def _parse_list_config(value: Optional[str]) -> List[str]:
    """解析逗号分隔的配置值为列表。"""

    if not value:
        return []
    return [t.strip() for t in value.split(",") if t.strip()]


def _serialize_list_config(items: List[str]) -> str:
    """将列表序列化为逗号分隔的字符串。"""

    return ",".join(sorted(set(items)))


# ==================== API 端点 ====================


@router.get("/config", response_model=AccessConfigResponse)
def get_access_config(db: Session = Depends(get_db)):
    """获取完整的访问控制配置。"""

    # 表白名单
    whitelist_str = _get_config_value(db, CONFIG_KEY_WHITELIST)
    if whitelist_str:
        whitelist = _parse_list_config(whitelist_str)
        whitelist_source = "database"
    else:
        whitelist = list(DEFAULT_TABLE_WHITELIST)
        whitelist_source = "default"

    # 表黑名单
    blacklist_str = _get_config_value(db, CONFIG_KEY_BLACKLIST)
    if blacklist_str:
        blacklist = _parse_list_config(blacklist_str)
    else:
        blacklist = list(DEFAULT_TABLE_BLACKLIST)

    # 分析 Schema 白名单
    schema_allowlist_str = _get_config_value(db, CONFIG_KEY_SCHEMA_ALLOWLIST)
    if schema_allowlist_str:
        schema_whitelist = _parse_list_config(schema_allowlist_str)
    else:
        schema_whitelist = list(ANALYTICS_SCHEMAS)

    # 系统 Schema 黑名单
    system_schema_blacklist_str = _get_config_value(db, CONFIG_KEY_SYSTEM_SCHEMA_BLACKLIST)
    if system_schema_blacklist_str:
        system_schema_blacklist = _parse_list_config(system_schema_blacklist_str)
    else:
        system_schema_blacklist = list(DEFAULT_SCHEMA_BLACKLIST)

    return AccessConfigResponse(
        whitelist=sorted(whitelist),
        whitelist_source=whitelist_source,
        blacklist=sorted(blacklist),
        schema_whitelist=sorted(schema_whitelist),
        system_schema_blacklist=sorted(system_schema_blacklist),
    )


@router.get("/whitelist", response_model=TableWhitelistResponse)
def get_table_whitelist(db: Session = Depends(get_db)):
    """获取表白名单。"""

    whitelist_str = _get_config_value(db, CONFIG_KEY_WHITELIST)

    if whitelist_str:
        tables = _parse_list_config(whitelist_str)
        source = "database"
    else:
        tables = list(DEFAULT_TABLE_WHITELIST)
        source = "default"

    return TableWhitelistResponse(tables=sorted(tables), source=source)


@router.put("/whitelist")
def update_table_whitelist(request: UpdateWhitelistRequest, db: Session = Depends(get_db)):
    """更新表白名单。"""

    value = _serialize_list_config(request.tables)
    _set_config_value(db, CONFIG_KEY_WHITELIST, value, "数据访问控制-表白名单")

    logger.info("表白名单已更新: %s", request.tables)

    return {
        "message": "白名单已更新",
        "tables": sorted(request.tables),
        "count": len(request.tables),
    }


@router.post("/whitelist/add")
def add_to_whitelist(table_name: str, db: Session = Depends(get_db)):
    """添加表到白名单。"""

    whitelist_str = _get_config_value(db, CONFIG_KEY_WHITELIST)

    if whitelist_str:
        tables = set(_parse_list_config(whitelist_str))
    else:
        tables = set(DEFAULT_TABLE_WHITELIST)

    tables.add(table_name.lower())

    _set_config_value(db, CONFIG_KEY_WHITELIST, _serialize_list_config(list(tables)), "数据访问控制-表白名单")

    return {"message": f"表 {table_name} 已添加到白名单", "tables": sorted(tables)}


@router.delete("/whitelist/{table_name}")
def remove_from_whitelist(table_name: str, db: Session = Depends(get_db)):
    """从白名单移除表。"""

    whitelist_str = _get_config_value(db, CONFIG_KEY_WHITELIST)

    if whitelist_str:
        tables = set(_parse_list_config(whitelist_str))
    else:
        tables = set(DEFAULT_TABLE_WHITELIST)

    tables.discard(table_name.lower())

    _set_config_value(db, CONFIG_KEY_WHITELIST, _serialize_list_config(list(tables)), "数据访问控制-表白名单")

    return {"message": f"表 {table_name} 已从白名单移除", "tables": sorted(tables)}


@router.get("/blacklist", response_model=TableBlacklistResponse)
def get_table_blacklist(db: Session = Depends(get_db)):
    """获取表黑名单。"""

    blacklist_str = _get_config_value(db, CONFIG_KEY_BLACKLIST)

    if blacklist_str:
        tables = _parse_list_config(blacklist_str)
    else:
        tables = list(DEFAULT_TABLE_BLACKLIST)

    return TableBlacklistResponse(tables=sorted(tables))


@router.put("/blacklist")
def update_table_blacklist(request: UpdateBlacklistRequest, db: Session = Depends(get_db)):
    """更新表黑名单。"""

    value = _serialize_list_config(request.tables)
    _set_config_value(db, CONFIG_KEY_BLACKLIST, value, "数据访问控制-表黑名单")

    logger.info("表黑名单已更新: %s", request.tables)

    return {
        "message": "黑名单已更新",
        "tables": sorted(request.tables),
        "count": len(request.tables),
    }


@router.get("/schema-whitelist", response_model=SchemaWhitelistResponse)
def get_schema_whitelist(db: Session = Depends(get_db)):
    """获取 Schema 白名单。"""

    schema_str = _get_config_value(db, CONFIG_KEY_SCHEMA_ALLOWLIST)

    if schema_str:
        schemas = _parse_list_config(schema_str)
    else:
        schemas = list(ANALYTICS_SCHEMAS)

    return SchemaWhitelistResponse(schemas=sorted(schemas))


@router.put("/schema-whitelist")
def update_schema_whitelist(request: UpdateSchemaWhitelistRequest, db: Session = Depends(get_db)):
    """更新 Schema 白名单。"""

    value = _serialize_list_config(request.schemas)
    _set_config_value(db, CONFIG_KEY_SCHEMA_ALLOWLIST, value, "数据访问控制-分析Schema白名单")

    logger.info("Schema 白名单已更新: %s", request.schemas)

    return {
        "message": "Schema 白名单已更新",
        "schemas": sorted(request.schemas),
        "count": len(request.schemas),
    }


@router.get("/system-schema-blacklist", response_model=SystemSchemaBlacklistResponse)
def get_system_schema_blacklist(db: Session = Depends(get_db)):
    """获取系统 Schema 黑名单。"""

    schema_str = _get_config_value(db, CONFIG_KEY_SYSTEM_SCHEMA_BLACKLIST)

    if schema_str:
        schemas = _parse_list_config(schema_str)
    else:
        schemas = list(DEFAULT_SCHEMA_BLACKLIST)

    return SystemSchemaBlacklistResponse(schemas=sorted(schemas))


@router.put("/system-schema-blacklist")
def update_system_schema_blacklist(
    request: UpdateSchemaWhitelistRequest,
    db: Session = Depends(get_db),
):
    """更新系统 Schema 黑名单。"""

    value = _serialize_list_config(request.schemas)
    _set_config_value(
        db,
        CONFIG_KEY_SYSTEM_SCHEMA_BLACKLIST,
        value,
        "数据访问控制-系统Schema黑名单",
    )

    logger.info("系统 Schema 黑名单已更新: %s", request.schemas)

    return {
        "message": "系统 Schema 黑名单已更新",
        "schemas": sorted(request.schemas),
        "count": len(request.schemas),
    }


@router.get("/data-roles", response_model=DataRolePolicyListResponse)
def list_data_role_policies(db: Session = Depends(get_db)):
    """列出全部 data_role 策略模板。"""

    service = get_permission_service()
    items: list[DataRolePolicyResponse] = []

    for data_role in DataRole:
        policy = service.get_data_role_policy(data_role.value, db)
        items.append(DataRolePolicyResponse(data_role=data_role, **policy))

    return DataRolePolicyListResponse(items=items)


@router.get("/data-roles/{data_role}", response_model=DataRolePolicyResponse)
def get_data_role_policy(data_role: DataRole, db: Session = Depends(get_db)):
    """查询单个 data_role 的策略模板。"""

    service = get_permission_service()
    policy = service.get_data_role_policy(data_role.value, db)
    return DataRolePolicyResponse(data_role=data_role, **policy)


@router.put("/data-roles/{data_role}", response_model=DataRolePolicyResponse)
def update_data_role_policy(
    data_role: DataRole,
    request: DataRolePolicyUpsertRequest,
    db: Session = Depends(get_db),
):
    """全量更新 data_role 策略模板。"""

    service = get_permission_service()

    try:
        policy = service.replace_data_role_policy(
            data_role.value,
            table_rules=[item.model_dump() for item in request.table_rules],
            row_rules=[item.model_dump() for item in request.row_rules],
            column_rules=[item.model_dump() for item in request.column_rules],
            db=db,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("更新 data_role 策略失败: data_role=%s", data_role.value)
        raise HTTPException(status_code=500, detail="更新数据角色策略失败") from exc

    return DataRolePolicyResponse(data_role=data_role, **policy)


@router.delete("/data-roles/{data_role}", response_model=DataRolePolicyDeleteResponse)
def delete_data_role_policy(data_role: DataRole, db: Session = Depends(get_db)):
    """删除单个 data_role 的全部策略。"""

    service = get_permission_service()

    try:
        deleted = service.delete_data_role_policy(data_role.value, db)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("删除 data_role 策略失败: data_role=%s", data_role.value)
        raise HTTPException(status_code=500, detail="删除数据角色策略失败") from exc

    return DataRolePolicyDeleteResponse(data_role=data_role, **deleted)


@router.post("/sql-dry-run", response_model=SQLDryRunResponse)
def sql_dry_run(request: SQLDryRunRequest, db: Session = Depends(get_db)):
    """执行 SQL 试跑并返回命中轨迹。"""

    service = get_permission_service()

    try:
        result = service.evaluate_sql_dry_run(
            user_id=request.user_id,
            sql=request.sql,
            auto_limit=request.auto_limit,
            limit=request.limit,
            db=db,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("SQL 试跑失败: user_id=%s", request.user_id)
        raise HTTPException(status_code=500, detail="SQL 试跑失败") from exc

    return SQLDryRunResponse(**result)


@router.post("/test-sql", response_model=SQLTestResponse)
def test_sql_access(request: SQLTestRequest, db: Session = Depends(get_db)):
    """测试 SQL 语句的访问权限。

    不执行 SQL，仅检查权限。
    """

    dac = DataAccessControl()

    # 提取表名
    tables = dac.extract_tables_from_sql(request.sql)

    # 检查每个表的权限
    tables_allowed = []
    tables_denied = []

    for table in tables:
        if dac.check_table_access(table):
            tables_allowed.append(table)
        else:
            tables_denied.append(table)

    is_valid = len(tables_denied) == 0
    error = f"无权访问表: {', '.join(tables_denied)}" if tables_denied else None

    return SQLTestResponse(
        is_valid=is_valid,
        error=error,
        tables_found=tables,
        tables_allowed=tables_allowed,
        tables_denied=tables_denied,
    )


@router.get("/available-tables")
def get_available_tables(db: Session = Depends(get_db)):
    """获取业务数据库中所有可用的表（用于 UI 选择）。"""

    from sqlalchemy import text

    from app.db.session import analytics_engine

    try:
        with analytics_engine.connect() as conn:
            result = conn.execute(
                text(
                    """
                SELECT table_schema, table_name
                FROM information_schema.tables
                WHERE table_type = 'BASE TABLE'
                  AND table_schema NOT IN ('pg_catalog', 'information_schema')
                ORDER BY table_schema, table_name
                """
                )
            )

            tables = [
                {
                    "schema": row.table_schema,
                    "table": row.table_name,
                    "full_name": f"{row.table_schema}.{row.table_name}",
                }
                for row in result.fetchall()
            ]

        return {"tables": tables, "count": len(tables)}

    except Exception as e:
        logger.exception("获取可用表列表失败")
        raise HTTPException(status_code=500, detail=str(e))
