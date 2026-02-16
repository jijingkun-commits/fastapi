"""问数权限服务（中文注释）。

提供权限配置加载、缓存和权限判断功能。
"""

from __future__ import annotations

import fnmatch
import logging
import threading
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Sequence, Tuple

from sqlalchemy.orm import Session

from app.ai.utils.permission_context import UserPermissionContext
from app.db.session import get_db_context
from app.models.data_permission import (
    DataPermissionColumn,
    DataPermissionRow,
    DataPermissionTable,
)
from app.models.user import User

logger = logging.getLogger(__name__)

# 缓存过期时间（秒）
CACHE_TTL = 300  # 5 分钟

# 默认数据角色（G0 冻结兜底）
DEFAULT_DATA_ROLE = "staff"

# 冻结数据角色枚举（G0 只读）
FROZEN_DATA_ROLES = (
    "head_president",
    "department_gm",
    "department_vgm",
    "staff",
)


@dataclass(frozen=True)
class PermissionHitAudit:
    """权限命中审计条目。"""

    schema_name: str
    table_name: str
    full_name: str
    allowed: bool
    hit_rule_type: str
    matched_rule: Optional[str] = None
    reason: Optional[str] = None


class PermissionService:
    """问数权限服务。

    负责：
    1. 加载用户权限配置
    2. 构建权限上下文
    3. 判断表/行/列访问权限
    4. 管理 data_role 策略模板
    5. 输出 SQL 试跑与策略命中审计

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
        db: Optional[Session] = None,
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
                    logger.debug("权限上下文命中缓存: user_id=%s", user_id)
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

        logger.info(
            "权限上下文已加载: user_id=%s, data_role=%s, sys_role=%s",
            user_id,
            ctx.data_role,
            ctx.sys_role,
        )
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
        logger.info("权限缓存已清除: user_id=%s", user_id)

    def _resolve_user_data_role(self, user: User) -> str:
        """解析用户数据角色（优先 data_role，缺失时最小权限兜底）。"""

        data_role = str(getattr(user, "data_role", "") or "").strip().lower()
        if data_role:
            return data_role

        legacy_role = str(getattr(user, "role", "") or "").strip().lower()
        if legacy_role and legacy_role != "admin":
            return legacy_role

        logger.warning("用户缺少 data_role，降级为最小权限 staff: user_id=%s", user.id)
        return DEFAULT_DATA_ROLE

    def _load_permission_context(
        self,
        user_id: int,
        db: Session,
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
            logger.warning("用户不存在: user_id=%s，返回默认权限", user_id)
            return UserPermissionContext(user_id=user_id, data_role=DEFAULT_DATA_ROLE)

        data_role = self._resolve_user_data_role(user)

        ctx = UserPermissionContext(
            user_id=user_id,
            data_role=data_role,
            sys_role=user.role,
            org_code=user.org_code,
            org_name=user.org_name,
            dept_code=user.dept_code,
            dept_name=user.dept_name,
        )

        # 2. 加载表级权限
        table_perms = db.query(DataPermissionTable).filter(
            DataPermissionTable.role == data_role
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
            (DataPermissionRow.role == data_role) | (DataPermissionRow.role.is_(None))
        ).all()

        for perm in row_perms:
            table_key = f"{perm.schema_name}.{perm.table_name}"

            # 获取实际过滤值
            if perm.filter_source == "fixed":
                filter_value = perm.filter_value
            else:
                filter_value = ctx.get_row_filter_value(perm.filter_source)

            if filter_value:
                filter_tuple = (
                    perm.filter_column,
                    perm.filter_operator or "=",
                    filter_value,
                )

                if table_key not in ctx.row_filters:
                    ctx.row_filters[table_key] = []
                ctx.row_filters[table_key].append(filter_tuple)

        # 4. 加载列级权限（脱敏）
        col_perms = db.query(DataPermissionColumn).filter(
            DataPermissionColumn.role == data_role
        ).all()

        for perm in col_perms:
            col_key = f"{perm.schema_name}.{perm.table_name}.{perm.column_name}"
            ctx.masked_columns[col_key] = perm.mask_type

        logger.debug(
            "权限加载完成: allowed_tables=%s, row_filters=%s, masked_columns=%s",
            len(ctx.allowed_tables),
            len(ctx.row_filters),
            len(ctx.masked_columns),
        )

        return ctx

    def validate_query_context(
        self,
        ctx: UserPermissionContext,
    ) -> Tuple[bool, Optional[str]]:
        """校验 SQL 查询前的默认权限前提。"""

        if ctx.default_dept_scope and not ctx.has_dept_code():
            return (
                False,
                f"用户 {ctx.user_id} 缺少 dept_code，命中默认部门隔离策略，拒绝查询",
            )

        return (True, None)

    def _evaluate_table_access(
        self,
        ctx: UserPermissionContext,
        schema: str,
        table: str,
    ) -> PermissionHitAudit:
        """检查表访问权限并返回审计命中。"""

        full_name = f"{schema}.{table}"

        # 检查黑名单
        if full_name in ctx.denied_tables:
            reason = f"表 {full_name} 禁止访问"
            return PermissionHitAudit(
                schema_name=schema,
                table_name=table,
                full_name=full_name,
                allowed=False,
                hit_rule_type="deny",
                matched_rule=full_name,
                reason=reason,
            )

        # 检查白名单（支持通配符匹配）
        for pattern in ctx.allowed_tables:
            if self._match_table_pattern(pattern, schema, table):
                return PermissionHitAudit(
                    schema_name=schema,
                    table_name=table,
                    full_name=full_name,
                    allowed=True,
                    hit_rule_type="allow",
                    matched_rule=pattern,
                )

        # 默认拒绝
        reason = f"数据角色 {ctx.data_role} 无权访问表 {full_name}"
        return PermissionHitAudit(
            schema_name=schema,
            table_name=table,
            full_name=full_name,
            allowed=False,
            hit_rule_type="default_deny",
            reason=reason,
        )

    def check_table_access(
        self,
        ctx: UserPermissionContext,
        schema: str,
        table: str,
    ) -> Tuple[bool, Optional[str]]:
        """检查表访问权限。

        Args:
            ctx: 权限上下文
            schema: Schema 名称
            table: 表名

        Returns:
            (allowed, reason) 元组
        """

        hit = self._evaluate_table_access(ctx, schema, table)
        return (hit.allowed, hit.reason)

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
        table: str,
    ) -> List[Tuple[str, str, str]]:
        """获取表的行级过滤条件。

        Args:
            ctx: 权限上下文
            schema: Schema 名称
            table: 表名

        Returns:
            过滤条件列表 [(column, operator, value), ...]
        """

        filters = []

        # 精确匹配
        full_name = f"{schema}.{table}"
        if full_name in ctx.row_filters:
            filters.extend(ctx.row_filters[full_name])

        # 通配符匹配 (schema.*)
        wildcard_key = f"{schema}.*"
        if wildcard_key in ctx.row_filters:
            filters.extend(ctx.row_filters[wildcard_key])

        if ctx.default_dept_scope and ctx.has_dept_code():
            filters.append(("dept_code", "=", (ctx.dept_code or "").strip()))

        deduped_filters: List[Tuple[str, str, str]] = []
        seen = set()
        for item in filters:
            if item in seen:
                continue
            seen.add(item)
            deduped_filters.append(item)

        return deduped_filters

    def get_masked_columns_for_table(
        self,
        ctx: UserPermissionContext,
        schema: str,
        table: str,
    ) -> Dict[str, str]:
        """获取表的列脱敏规则。

        Args:
            ctx: 权限上下文
            schema: Schema 名称
            table: 表名

        Returns:
            脱敏规则 {column_name: mask_type}
        """

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

    def _ensure_unique_rules(
        self,
        rules: Sequence[dict],
        key_fields: Sequence[str],
        rule_name: str,
    ):
        """校验策略规则键唯一。"""

        seen: dict[tuple[str, ...], int] = {}
        for idx, rule in enumerate(rules):
            key_parts: list[str] = []
            for field in key_fields:
                value = str(rule.get(field, "") or "").strip().lower()
                if not value:
                    raise ValueError(f"{rule_name} 第 {idx + 1} 条缺少字段 {field}")
                key_parts.append(value)
            key = tuple(key_parts)
            if key in seen:
                first_idx = seen[key] + 1
                raise ValueError(
                    f"{rule_name} 存在重复规则（第 {first_idx} 条与第 {idx + 1} 条）"
                )
            seen[key] = idx

    def _build_policy_summary(self, *, table_rules: list, row_rules: list, column_rules: list) -> dict:
        """构建策略摘要。"""

        return {
            "table_rule_count": len(table_rules),
            "row_rule_count": len(row_rules),
            "column_rule_count": len(column_rules),
        }

    def get_data_role_policy(self, data_role: str, db: Session) -> dict:
        """获取指定 data_role 的权限策略。"""

        normalized_role = str(data_role or "").strip().lower()
        if not normalized_role:
            raise ValueError("data_role 不能为空")

        table_perms = (
            db.query(DataPermissionTable)
            .filter(DataPermissionTable.role == normalized_role)
            .order_by(DataPermissionTable.schema_name, DataPermissionTable.table_name, DataPermissionTable.id)
            .all()
        )
        row_perms = (
            db.query(DataPermissionRow)
            .filter(DataPermissionRow.role == normalized_role)
            .order_by(DataPermissionRow.schema_name, DataPermissionRow.table_name, DataPermissionRow.id)
            .all()
        )
        col_perms = (
            db.query(DataPermissionColumn)
            .filter(DataPermissionColumn.role == normalized_role)
            .order_by(DataPermissionColumn.schema_name, DataPermissionColumn.table_name, DataPermissionColumn.id)
            .all()
        )

        table_rules = [
            {
                "schema_name": item.schema_name,
                "table_name": item.table_name,
                "allow_access": bool(item.allow_access),
                "description": item.description,
            }
            for item in table_perms
        ]
        row_rules = [
            {
                "schema_name": item.schema_name,
                "table_name": item.table_name,
                "filter_column": item.filter_column,
                "filter_source": item.filter_source,
                "filter_value": item.filter_value,
                "filter_operator": item.filter_operator or "=",
                "description": item.description,
            }
            for item in row_perms
        ]
        column_rules = [
            {
                "schema_name": item.schema_name,
                "table_name": item.table_name,
                "column_name": item.column_name,
                "mask_type": item.mask_type,
                "description": item.description,
            }
            for item in col_perms
        ]

        return {
            "table_rules": table_rules,
            "row_rules": row_rules,
            "column_rules": column_rules,
            "summary": self._build_policy_summary(
                table_rules=table_rules,
                row_rules=row_rules,
                column_rules=column_rules,
            ),
        }

    def replace_data_role_policy(
        self,
        data_role: str,
        *,
        table_rules: Sequence[dict],
        row_rules: Sequence[dict],
        column_rules: Sequence[dict],
        db: Session,
    ) -> dict:
        """替换指定 data_role 的全量策略。"""

        normalized_role = str(data_role or "").strip().lower()
        if normalized_role not in FROZEN_DATA_ROLES:
            raise ValueError(f"不支持的数据角色: {data_role}")

        self._ensure_unique_rules(table_rules, ("schema_name", "table_name"), "table_rules")
        self._ensure_unique_rules(
            row_rules,
            ("schema_name", "table_name", "filter_column", "filter_source", "filter_operator"),
            "row_rules",
        )
        self._ensure_unique_rules(
            column_rules,
            ("schema_name", "table_name", "column_name"),
            "column_rules",
        )

        try:
            db.query(DataPermissionTable).filter(DataPermissionTable.role == normalized_role).delete()
            db.query(DataPermissionRow).filter(DataPermissionRow.role == normalized_role).delete()
            db.query(DataPermissionColumn).filter(DataPermissionColumn.role == normalized_role).delete()

            table_records = [
                DataPermissionTable(
                    role=normalized_role,
                    schema_name=str(rule["schema_name"]).strip().lower(),
                    table_name=str(rule["table_name"]).strip().lower(),
                    allow_access=bool(rule.get("allow_access", True)),
                    description=rule.get("description"),
                )
                for rule in table_rules
            ]
            if table_records:
                db.add_all(table_records)

            row_records = [
                DataPermissionRow(
                    role=normalized_role,
                    schema_name=str(rule["schema_name"]).strip().lower(),
                    table_name=str(rule["table_name"]).strip().lower(),
                    filter_column=str(rule["filter_column"]).strip().lower(),
                    filter_source=str(rule["filter_source"]).strip(),
                    filter_value=rule.get("filter_value"),
                    filter_operator=str(rule.get("filter_operator", "=")).strip().upper(),
                    description=rule.get("description"),
                )
                for rule in row_rules
            ]
            if row_records:
                db.add_all(row_records)

            column_records = [
                DataPermissionColumn(
                    role=normalized_role,
                    schema_name=str(rule["schema_name"]).strip().lower(),
                    table_name=str(rule["table_name"]).strip().lower(),
                    column_name=str(rule["column_name"]).strip().lower(),
                    mask_type=str(rule["mask_type"]).strip().lower(),
                    description=rule.get("description"),
                )
                for rule in column_rules
            ]
            if column_records:
                db.add_all(column_records)

            db.commit()
        except Exception:
            db.rollback()
            raise

        self.invalidate_cache()
        logger.info(
            "数据角色策略已替换: data_role=%s, table_rules=%s, row_rules=%s, column_rules=%s",
            normalized_role,
            len(table_rules),
            len(row_rules),
            len(column_rules),
        )

        return self.get_data_role_policy(normalized_role, db)

    def delete_data_role_policy(self, data_role: str, db: Session) -> dict:
        """删除指定 data_role 的全量策略。"""

        normalized_role = str(data_role or "").strip().lower()
        if normalized_role not in FROZEN_DATA_ROLES:
            raise ValueError(f"不支持的数据角色: {data_role}")

        try:
            deleted_tables = db.query(DataPermissionTable).filter(
                DataPermissionTable.role == normalized_role
            ).delete()
            deleted_rows = db.query(DataPermissionRow).filter(
                DataPermissionRow.role == normalized_role
            ).delete()
            deleted_columns = db.query(DataPermissionColumn).filter(
                DataPermissionColumn.role == normalized_role
            ).delete()
            db.commit()
        except Exception:
            db.rollback()
            raise

        self.invalidate_cache()

        deleted = {
            "table_rules": int(deleted_tables or 0),
            "row_rules": int(deleted_rows or 0),
            "column_rules": int(deleted_columns or 0),
        }
        total_deleted = sum(deleted.values())

        logger.info(
            "数据角色策略已删除: data_role=%s, deleted=%s",
            normalized_role,
            deleted,
        )

        return {
            "deleted": deleted,
            "total_deleted": total_deleted,
        }

    def _extract_table_pairs_from_sql(self, sql: str) -> list[tuple[str, str]]:
        """从 SQL 提取 (schema, table) 列表。"""

        from app.ai.utils.sql_parser import extract_tables_from_sql

        table_refs = extract_tables_from_sql(sql or "")
        pairs: set[tuple[str, str]] = set()
        for table_ref in table_refs:
            normalized = str(table_ref or "").strip().lower()
            if not normalized:
                continue
            if "." in normalized:
                schema, table = normalized.split(".", 1)
            else:
                schema, table = "public", normalized
            pairs.add((schema, table))
        return sorted(pairs)

    def collect_permission_hits_for_sql(
        self,
        sql: str,
        ctx: UserPermissionContext,
    ) -> List[PermissionHitAudit]:
        """收集 SQL 的表级权限命中轨迹。"""

        hits: list[PermissionHitAudit] = []
        table_pairs = self._extract_table_pairs_from_sql(sql)
        for schema, table in table_pairs:
            hits.append(self._evaluate_table_access(ctx, schema, table))
        return hits

    def evaluate_sql_dry_run(
        self,
        *,
        user_id: int,
        sql: str,
        auto_limit: bool = True,
        limit: int = 1000,
        db: Optional[Session] = None,
    ) -> dict:
        """执行 SQL 试跑并返回策略命中审计。"""

        from app.ai.utils.sql_policy_decision import evaluate_sql_policy

        ctx = self.get_user_permission_context(user_id, db=db)
        decision = evaluate_sql_policy(
            sql,
            user_id,
            auto_limit=auto_limit,
            limit=limit,
        )

        policy_hits = [
            {
                "schema_name": hit.schema_name,
                "table_name": hit.table_name,
                "full_name": hit.full_name,
                "allowed": hit.allowed,
                "hit_rule_type": hit.hit_rule_type,
                "matched_rule": hit.matched_rule,
                "reason": hit.reason,
            }
            for hit in self.collect_permission_hits_for_sql(sql, ctx)
        ]

        logger.info(
            "SQL 试跑: user_id=%s, data_role=%s, allowed=%s, reason_code=%s, denied_stage=%s, hits=%s",
            user_id,
            ctx.data_role,
            decision.is_allowed,
            decision.reason_code,
            decision.denied_stage,
            len(policy_hits),
        )

        return {
            "user_id": user_id,
            "data_role": ctx.data_role,
            "is_allowed": decision.is_allowed,
            "original_sql": sql,
            "rewritten_sql": decision.rewritten_sql,
            "reason": decision.reason,
            "reason_code": decision.reason_code,
            "denied_stage": decision.denied_stage,
            "policy_hits": policy_hits,
        }


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
