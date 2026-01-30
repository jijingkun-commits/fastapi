"""问数权限服务（中文注释）。

提供权限配置加载、缓存和权限判断功能。
"""
import logging
import fnmatch
import threading
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from app.db.session import get_db_context
from app.models.user import User
from app.models.data_permission import (
    DataPermissionTable,
    DataPermissionRow,
    DataPermissionColumn,
)
from app.ai.utils.permission_context import UserPermissionContext

logger = logging.getLogger(__name__)

# 缓存过期时间（秒）
CACHE_TTL = 300  # 5 分钟


class PermissionService:
    """问数权限服务。
    
    负责：
    1. 加载用户权限配置
    2. 构建权限上下文
    3. 判断表/行/列访问权限
    
    线程安全：使用锁保护缓存操作。
    """
    
    _instance = None
    _cache: Dict[int, Tuple[UserPermissionContext, datetime]] = {}
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def get_user_permission_context(
        self, 
        user_id: int, 
        db: Optional[Session] = None
    ) -> UserPermissionContext:
        """获取用户权限上下文（带缓存，线程安全）。
        
        Args:
            user_id: 用户 ID
            db: 数据库会话（可选，不传则自动获取）
            
        Returns:
            UserPermissionContext 权限上下文对象
        """
        # 检查缓存（加锁读取）
        with self._lock:
            if user_id in self._cache:
                ctx, cached_at = self._cache[user_id]
                if datetime.now() - cached_at < timedelta(seconds=CACHE_TTL):
                    logger.debug(f"权限上下文命中缓存: user_id={user_id}")
                    return ctx
        
        # 从数据库加载（在锁外执行 I/O 操作）
        if db is None:
            with get_db_context() as session:
                ctx = self._load_permission_context(user_id, session)
        else:
            ctx = self._load_permission_context(user_id, db)
        
        # 更新缓存（加锁写入）
        with self._lock:
            self._cache[user_id] = (ctx, datetime.now())
        
        logger.info(f"权限上下文已加载: user_id={user_id}, role={ctx.role}")
        return ctx
    
    def invalidate_cache(self, user_id: Optional[int] = None):
        """清除缓存（线程安全）。
        
        Args:
            user_id: 指定用户 ID，不传则清除全部
        """
        with self._lock:
            if user_id is not None:
                self._cache.pop(user_id, None)
            else:
                self._cache.clear()
        logger.info(f"权限缓存已清除: user_id={user_id}")
    
    def _load_permission_context(
        self, 
        user_id: int, 
        db: Session
    ) -> UserPermissionContext:
        """从数据库加载用户权限配置。
        
        Args:
            user_id: 用户 ID
            db: 数据库会话
            
        Returns:
            UserPermissionContext 权限上下文
        """
        # 1. 加载用户基本信息
        user = db.query(User).filter(User.id == user_id).first()
        
        if user is None:
            logger.warning(f"用户不存在: user_id={user_id}，返回默认权限")
            return UserPermissionContext(user_id=user_id)
        
        role = user.role or "user"
        
        ctx = UserPermissionContext(
            user_id=user_id,
            role=role,
            org_code=user.org_code,
            org_name=user.org_name,
            dept_code=user.dept_code,
            dept_name=user.dept_name,
        )
        
        # admin 角色无限制
        if ctx.is_admin():
            logger.debug(f"管理员用户，跳过权限加载: user_id={user_id}")
            return ctx
        
        # 2. 加载表级权限
        table_perms = db.query(DataPermissionTable).filter(
            DataPermissionTable.role == role
        ).all()
        
        for perm in table_perms:
            table_key = f"{perm.schema_name}.{perm.table_name}"
            if perm.allow_access:
                ctx.allowed_tables.append(table_key)
                if perm.schema_name not in ctx.allowed_schemas:
                    ctx.allowed_schemas.append(perm.schema_name)
            else:
                ctx.denied_tables.add(table_key)
        
        # 3. 加载行级权限（RLS）
        row_perms = db.query(DataPermissionRow).filter(
            (DataPermissionRow.role == role) | (DataPermissionRow.role.is_(None))
        ).all()
        
        for perm in row_perms:
            table_key = f"{perm.schema_name}.{perm.table_name}"
            
            # 获取实际过滤值
            if perm.filter_source == "fixed":
                filter_value = perm.filter_value
            else:
                filter_value = ctx.get_row_filter_value(perm.filter_source)
            
            if filter_value:
                filter_tuple = (perm.filter_column, perm.filter_operator or "=", filter_value)
                
                if table_key not in ctx.row_filters:
                    ctx.row_filters[table_key] = []
                ctx.row_filters[table_key].append(filter_tuple)
        
        # 4. 加载列级权限（脱敏）
        col_perms = db.query(DataPermissionColumn).filter(
            DataPermissionColumn.role == role
        ).all()
        
        for perm in col_perms:
            col_key = f"{perm.schema_name}.{perm.table_name}.{perm.column_name}"
            ctx.masked_columns[col_key] = perm.mask_type
        
        logger.debug(f"权限加载完成: allowed_tables={len(ctx.allowed_tables)}, "
                    f"row_filters={len(ctx.row_filters)}, masked_columns={len(ctx.masked_columns)}")
        
        return ctx
    
    def check_table_access(
        self, 
        ctx: UserPermissionContext, 
        schema: str, 
        table: str
    ) -> Tuple[bool, Optional[str]]:
        """检查表访问权限。
        
        Args:
            ctx: 权限上下文
            schema: Schema 名称
            table: 表名
            
        Returns:
            (allowed, reason) 元组
        """
        # admin 无限制
        if ctx.is_admin():
            return (True, None)
        
        full_name = f"{schema}.{table}"
        
        # 检查黑名单
        if full_name in ctx.denied_tables:
            return (False, f"表 {full_name} 禁止访问")
        
        # 检查白名单（支持通配符匹配）
        for pattern in ctx.allowed_tables:
            if self._match_table_pattern(pattern, schema, table):
                return (True, None)
        
        # 默认拒绝
        return (False, f"角色 {ctx.role} 无权访问表 {full_name}")
    
    def _match_table_pattern(self, pattern: str, schema: str, table: str) -> bool:
        """匹配表名模式（支持通配符）。
        
        Args:
            pattern: 模式，如 "fdmdata.*" 或 "fdmdata.f_mid_deposit_%"
            schema: 实际 Schema
            table: 实际表名
            
        Returns:
            是否匹配
        """
        parts = pattern.split(".", 1)
        if len(parts) != 2:
            return False
        
        pattern_schema, pattern_table = parts
        
        # Schema 必须完全匹配
        if pattern_schema != schema:
            return False
        
        # 表名支持通配符
        if pattern_table == "*":
            return True
        
        # 支持 SQL LIKE 风格的 % 通配符，转换为 fnmatch 格式
        fnmatch_pattern = pattern_table.replace("%", "*")
        return fnmatch.fnmatch(table, fnmatch_pattern)
    
    def get_row_filters_for_table(
        self, 
        ctx: UserPermissionContext, 
        schema: str, 
        table: str
    ) -> List[Tuple[str, str, str]]:
        """获取表的行级过滤条件。
        
        Args:
            ctx: 权限上下文
            schema: Schema 名称
            table: 表名
            
        Returns:
            过滤条件列表 [(column, operator, value), ...]
        """
        if ctx.is_admin():
            return []
        
        filters = []
        
        # 精确匹配
        full_name = f"{schema}.{table}"
        if full_name in ctx.row_filters:
            filters.extend(ctx.row_filters[full_name])
        
        # 通配符匹配 (schema.*)
        wildcard_key = f"{schema}.*"
        if wildcard_key in ctx.row_filters:
            filters.extend(ctx.row_filters[wildcard_key])
        
        return filters
    
    def get_masked_columns_for_table(
        self, 
        ctx: UserPermissionContext, 
        schema: str, 
        table: str
    ) -> Dict[str, str]:
        """获取表的列脱敏规则。
        
        Args:
            ctx: 权限上下文
            schema: Schema 名称
            table: 表名
            
        Returns:
            脱敏规则 {column_name: mask_type}
        """
        if ctx.is_admin():
            return {}
        
        result = {}
        
        # 精确匹配
        prefix = f"{schema}.{table}."
        for col_key, mask_type in ctx.masked_columns.items():
            if col_key.startswith(prefix):
                col_name = col_key[len(prefix):]
                result[col_name] = mask_type
        
        # 通配符匹配 (schema.*.column)
        wildcard_prefix = f"{schema}.*."
        for col_key, mask_type in ctx.masked_columns.items():
            if col_key.startswith(wildcard_prefix):
                col_name = col_key[len(wildcard_prefix):]
                if col_name not in result:  # 精确匹配优先
                    result[col_name] = mask_type
        
        return result


# 全局单例
_permission_service: Optional[PermissionService] = None


def get_permission_service() -> PermissionService:
    """获取权限服务单例。"""
    global _permission_service
    if _permission_service is None:
        _permission_service = PermissionService()
    return _permission_service


def get_user_permission_context(user_id: int, db: Optional[Session] = None) -> UserPermissionContext:
    """便捷方法：获取用户权限上下文。"""
    return get_permission_service().get_user_permission_context(user_id, db)
