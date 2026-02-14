"""数据访问控制模块（中文注释）。

提供 Data Agent 的数据权限控制功能：
- 表级别黑名单（从数据库配置读取）
- Schema 级别黑名单（禁止访问系统 schema）
- 行级别安全 (RLS) 支持
- SQL 审计日志
"""
import logging
import time
from typing import List, Optional, Dict, Set, Tuple

from app.db.session import get_db_context
from app.core.config import ANALYTICS_SCHEMAS

logger = logging.getLogger(__name__)


# 默认可访问的表白名单（只允许查询这些表）
# 生产环境应从数据库配置读取
DEFAULT_TABLE_WHITELIST: Set[str] = {
    # fdmdata schema - 业务中间表
    "f_mid_ckcp_a038_h",
    "f_mid_ctcxcp_a036_h",
    "f_mid_dep_k_tb",
    "f_mid_dep_tb",
    "f_mid_dkcp_a008_h",
    "f_mid_fns_subject",
    "f_mid_index_result",
    "f_mid_index_result_derive",
    "f_mid_index_result_dim",
    "f_mid_index_result_dim_derive",
    "f_mid_khfl_a017_h",
    "f_mid_loan_k_tb",
    "f_mid_loan_tb",
    "f_mid_mms_sxyxh",
    "f_mid_org_tree",
    "f_mid_org_tree_k",
    "f_mid_payr_summary",
    "f_mid_sxqj_a010_h",
    # public schema - 维度表
    "t_ods_g_c_dim_date",
    # 测试/演示业务表
    "t_orders",
    "t_products",
    "t_customers",
}

# 敏感表黑名单（默认值，生产环境从数据库读取）
DEFAULT_TABLE_BLACKLIST: Set[str] = {
    "t_user",
    "t_chat_message",
    "t_chat_feedback",
    "t_chat_asset",
    "t_todo",
    "t_llm_model",
    "t_agent_skills",
    "t_system_config",
    "t_metric_definitions",
}

# 系统 schema 黑名单（默认值，禁止访问系统元数据表）
DEFAULT_SCHEMA_BLACKLIST: Set[str] = {
    "pg_catalog",
    "information_schema",
}

# 允许访问的 information_schema 只读视图（用于元数据查询）
# 这些视图只包含表结构信息，不含敏感数据
ALLOWED_METADATA_VIEWS: Set[str] = {
    "information_schema.tables",
    "information_schema.columns",
    "information_schema.schemata",
    "information_schema.table_constraints",
    "information_schema.key_column_usage",
    "information_schema.views",
}

# 配置缓存（避免每次查询都访问数据库）
_config_cache: Dict[str, Tuple[Set[str], float]] = {}  # key -> (value_set, timestamp)
_CACHE_TTL = 300  # 缓存 5 分钟

# 主键与兼容键定义（配置治理收敛）
ASKDATA_TABLE_WHITELIST_KEY = "askdata.table_whitelist"
ASKDATA_TABLE_WHITELIST_LEGACY_KEY = "data_access.table_whitelist"
ASKDATA_TABLE_BLACKLIST_KEY = "askdata.table_blacklist"
ASKDATA_TABLE_BLACKLIST_LEGACY_KEY = "data_access.table_blacklist"
ASKDATA_SYSTEM_SCHEMA_BLACKLIST_KEY = "askdata.system_schema_blacklist"
ASKDATA_SYSTEM_SCHEMA_BLACKLIST_LEGACY_KEYS = ("askdata.schema_blacklist",)
ASKDATA_ANALYTICS_SCHEMA_ALLOWLIST_KEY = "askdata.analytics_schema_allowlist"
ASKDATA_ANALYTICS_SCHEMA_ALLOWLIST_LEGACY_KEYS = (
    "askdata.schema_whitelist",
    "data_access.schema_whitelist",
)

# 向后兼容常量别名（仅保留名称，不再混用白名单语义）
ASKDATA_SCHEMA_BLACKLIST_KEY = ASKDATA_SYSTEM_SCHEMA_BLACKLIST_KEY
ASKDATA_SCHEMA_BLACKLIST_LEGACY_KEYS = ASKDATA_SYSTEM_SCHEMA_BLACKLIST_LEGACY_KEYS


def _load_config_from_db(config_key: str, default: Set[str], aliases: Tuple[str, ...] = ()) -> Set[str]:
    """从数据库加载配置，带缓存并兼容旧键。"""
    global _config_cache

    cache_key = "|".join((config_key, *aliases))
    if cache_key in _config_cache:
        cached_value, cached_time = _config_cache[cache_key]
        if time.time() - cached_time < _CACHE_TTL:
            return cached_value

    try:
        from app.repositories import config_repo

        with get_db_context() as db:
            for lookup_key in (config_key, *aliases):
                value = config_repo.get_config_value(db, lookup_key)
                if value:
                    result = {s.strip().lower() for s in value.split(",") if s.strip()}
                    _config_cache[cache_key] = (result, time.time())
                    logger.debug("从数据库加载配置 %s (lookup=%s): %s", config_key, lookup_key, result)
                    return result
    except Exception as e:
        logger.warning(f"加载配置 {config_key} 失败，使用默认值: {e}")

    default_lower = {s.lower() for s in default}
    _config_cache[cache_key] = (default_lower, time.time())
    return default_lower


def get_system_schema_blacklist() -> Set[str]:
    """获取系统 Schema 黑名单（主键 askdata.system_schema_blacklist）。"""

    return _load_config_from_db(
        ASKDATA_SYSTEM_SCHEMA_BLACKLIST_KEY,
        DEFAULT_SCHEMA_BLACKLIST,
        aliases=ASKDATA_SYSTEM_SCHEMA_BLACKLIST_LEGACY_KEYS,
    )


def get_analytics_schema_allowlist() -> Set[str]:
    """获取分析 Schema 白名单（主键 askdata.analytics_schema_allowlist）。"""

    default_allowlist = {
        str(schema).strip().lower()
        for schema in ANALYTICS_SCHEMAS
        if str(schema).strip()
    }
    if not default_allowlist:
        default_allowlist = {"fdmdata", "sdmdata", "public"}

    return _load_config_from_db(
        ASKDATA_ANALYTICS_SCHEMA_ALLOWLIST_KEY,
        default_allowlist,
        aliases=ASKDATA_ANALYTICS_SCHEMA_ALLOWLIST_LEGACY_KEYS,
    )


def get_schema_blacklist() -> Set[str]:
    """兼容函数：返回系统 Schema 黑名单。"""

    return get_system_schema_blacklist()


def get_table_blacklist() -> Set[str]:
    """获取表黑名单（主键 askdata.*，兼容 data_access.*）。"""

    return _load_config_from_db(
        ASKDATA_TABLE_BLACKLIST_KEY,
        DEFAULT_TABLE_BLACKLIST,
        aliases=(ASKDATA_TABLE_BLACKLIST_LEGACY_KEY,),
    )


class DataAccessControl:
    """数据访问控制类。
    
    提供以下功能：
    1. 表级别白名单检查
    2. 行级别安全策略（基于 user_id 等）
    3. SQL 审计日志记录
    """
    
    def __init__(self, user_id: Optional[int] = None):
        """初始化访问控制实例。
        
        Args:
            user_id: 当前用户 ID（用于 RLS）
        """
        self.user_id = user_id
        self._whitelist = self._load_whitelist()
    
    def _load_whitelist(self) -> Set[str]:
        """从数据库加载表白名单（主键 askdata.*，兼容 data_access.*）。"""

        return _load_config_from_db(
            ASKDATA_TABLE_WHITELIST_KEY,
            DEFAULT_TABLE_WHITELIST,
            aliases=(ASKDATA_TABLE_WHITELIST_LEGACY_KEY,),
        )
    
    def check_table_access(self, table_name: str) -> bool:
        """检查表访问权限。
        
        Args:
            table_name: 表名（可包含 schema 前缀，如 information_schema.tables）
            
        Returns:
            是否允许访问
        """
        table_lower = table_name.lower()
        
        # 优先检查是否为允许的元数据视图
        if table_lower in {v.lower() for v in ALLOWED_METADATA_VIEWS}:
            logger.debug(f"允许访问元数据视图: {table_name}")
            return True
        
        # 获取最新的 Schema 策略配置
        system_schema_blacklist = get_system_schema_blacklist()
        analytics_schema_allowlist = get_analytics_schema_allowlist()
        table_blacklist = get_table_blacklist()

        # 检查是否为系统 schema 的表（如 information_schema.tables）
        if '.' in table_lower:
            schema = table_lower.split('.')[0]
            # 检查 schema 黑名单（禁止访问系统 schema）
            if schema in system_schema_blacklist:
                logger.warning(f"表访问被拒绝（系统 Schema 黑名单）: {table_name}")
                return False
            # 检查分析 schema 白名单
            if analytics_schema_allowlist and schema not in analytics_schema_allowlist:
                logger.warning(f"表访问被拒绝（Schema 不在分析白名单）: {table_name}")
                return False
            # 提取纯表名用于后续检查
            pure_table = table_lower.split('.')[-1]
        else:
            pure_table = table_lower
        
        # 检查表黑名单
        if pure_table in table_blacklist:
            logger.warning(f"表访问被拒绝（表黑名单）: {table_name}")
            return False
        
        # 检查白名单（如果启用）
        if self._whitelist:
            if pure_table not in {t.lower() for t in self._whitelist}:
                logger.warning(f"表访问被拒绝（不在白名单）: {table_name}")
                return False
        
        return True
    
    def extract_tables_from_sql(self, sql: str) -> List[str]:
        """从 SQL 语句中提取表名。
        
        使用 sqlglot 进行 AST 解析，比正则更准确可靠。
        保留完整表名（包含 schema 前缀），以便 check_table_access 进行系统表检查。
        
        Args:
            sql: SQL 语句
            
        Returns:
            表名列表（可能包含 schema 前缀，如 information_schema.tables）
        """
        from app.ai.utils.sql_parser import extract_tables_from_sql as parse_tables
        
        # 使用统一的 SQL 解析工具，保留完整表名（包含 schema）
        tables = parse_tables(sql)
        return list(set(tables))
    
    def validate_sql(self, sql: str) -> tuple[bool, Optional[str]]:
        """验证 SQL 语句的访问权限。
        
        Args:
            sql: SQL 语句
            
        Returns:
            (is_valid, error_message) 元组
        """
        # 提取表名
        tables = self.extract_tables_from_sql(sql)
        
        # 检查每个表的访问权限
        for table in tables:
            if not self.check_table_access(table):
                return (False, f"无权访问表: {table}")
        
        return (True, None)
    
    def apply_rls(self, sql: str, table_name: str) -> str:
        """应用行级别安全策略（简化版）。
        
        根据 user_id 添加 WHERE 条件。
        
        Args:
            sql: 原始 SQL
            table_name: 主表名
            
        Returns:
            添加 RLS 条件后的 SQL
        """
        if not self.user_id:
            return sql
        
        # 简化实现：只對特定表添加用户过滤
        # 生产环境应基于配置或元数据
        user_filtered_tables = {"t_orders", "t_customers"}
        
        if table_name.lower() in user_filtered_tables:
            # 检查是否已有 WHERE
            sql_upper = sql.upper()
            if "WHERE" in sql_upper:
                # 在 WHERE 后添加 AND 条件
                insert_pos = sql_upper.find("WHERE") + 6
                sql = sql[:insert_pos] + f" user_id = {self.user_id} AND " + sql[insert_pos:]
            else:
                # 在末尾添加 WHERE（注意需要在 ORDER BY/LIMIT 之前）
                for keyword in ["ORDER BY", "GROUP BY", "LIMIT"]:
                    if keyword in sql_upper:
                        insert_pos = sql_upper.find(keyword)
                        sql = sql[:insert_pos] + f" WHERE user_id = {self.user_id} " + sql[insert_pos:]
                        break
                else:
                    sql = sql.rstrip(";") + f" WHERE user_id = {self.user_id}"
        
        return sql
    
    def log_query(
        self, 
        question: str, 
        sql: str, 
        success: bool, 
        thread_id: Optional[str] = None,
        sql_source: str = "vanna"
    ):
        """记录查询日志到 t_data_query_log。
        
        Args:
            question: 用户原始问题
            sql: 生成的 SQL
            success: 是否执行成功
            thread_id: 会话 ID
            sql_source: SQL 来源（metric/training/vanna_rag）
        """
        if not question or not question.strip():
            logger.debug("log_query 跳过: question 为空")
            return
        
        # embedding 生成独立于日志写入，失败不阻塞
        embedding = None
        try:
            from app.ai.utils.embedding_util import get_embedding
            embedding = get_embedding(question)
        except Exception as emb_err:
            logger.debug(f"查询日志 embedding 生成失败（不影响日志写入）: {emb_err}")
        
        try:
            from app.models.data_agent_metadata import DataQueryLog
            
            with get_db_context() as db:
                log = DataQueryLog(
                    user_id=self.user_id,
                    thread_id=thread_id,
                    question=question,
                    generated_sql=sql,
                    sql_source=sql_source,
                    is_correct=success,
                    question_embedding=embedding
                )
                db.add(log)
                db.commit()
                logger.info(f"查询日志已记录: question={question[:50]}..., source={sql_source}")
        except Exception as e:
            logger.error(f"查询日志记录失败: {e}", exc_info=True)


def invalidate_config_cache() -> None:
    """清理访问控制配置缓存。"""

    _config_cache.clear()


# 全局访问控制实例工厂
def get_access_control(user_id: Optional[int] = None) -> DataAccessControl:
    """获取数据访问控制实例。
    
    Args:
        user_id: 用户 ID
        
    Returns:
        DataAccessControl 实例
    """
    return DataAccessControl(user_id=user_id)


# 导出
# 向后兼容别名
TABLE_BLACKLIST = DEFAULT_TABLE_BLACKLIST
SYSTEM_SCHEMA_WHITELIST = DEFAULT_SCHEMA_BLACKLIST

__all__ = [
    "DataAccessControl", 
    "get_access_control", 
    "get_schema_blacklist",
    "get_system_schema_blacklist",
    "get_analytics_schema_allowlist",
    "get_table_blacklist",
    "DEFAULT_TABLE_WHITELIST", 
    "DEFAULT_TABLE_BLACKLIST", 
    "DEFAULT_SCHEMA_BLACKLIST",
    "ALLOWED_METADATA_VIEWS",
    "TABLE_BLACKLIST",
    "SYSTEM_SCHEMA_WHITELIST",
    "invalidate_config_cache",
]
