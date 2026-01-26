"""数据访问控制模块（中文注释）。

提供 Data Agent 的数据权限控制功能：
- 表级别白名单
- 行级别安全 (RLS) 支持
- SQL 审计日志
"""
import logging
from typing import List, Optional, Dict, Set
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.db.session import get_db_context

logger = logging.getLogger(__name__)


# 默认可访问的表白名单（只允许查询这些表）
# 生产环境应从数据库配置读取
DEFAULT_TABLE_WHITELIST: Set[str] = {
    "t_orders",
    "t_products", 
    "t_customers",
    "t_sales",
}

# 敏感表黑名单（绝对禁止访问）
TABLE_BLACKLIST: Set[str] = {
    "t_user",
    "t_llm_models",
    "t_agent_skills",
    "t_conversations",
    "t_messages",
}


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
        """从数据库加载表白名单。"""
        # 生产环境应从 t_meta_tables 加载
        # 这里使用默认值
        return DEFAULT_TABLE_WHITELIST.copy()
    
    def check_table_access(self, table_name: str) -> bool:
        """检查表访问权限。
        
        Args:
            table_name: 表名
            
        Returns:
            是否允许访问
        """
        table_lower = table_name.lower()
        
        # 黑名单优先
        if table_lower in {t.lower() for t in TABLE_BLACKLIST}:
            logger.warning(f"表访问被拒绝（黑名单）: {table_name}")
            return False
        
        # 检查白名单（如果启用）
        if self._whitelist:
            if table_lower not in {t.lower() for t in self._whitelist}:
                logger.warning(f"表访问被拒绝（不在白名单）: {table_name}")
                return False
        
        return True
    
    def extract_tables_from_sql(self, sql: str) -> List[str]:
        """从 SQL 语句中提取表名。
        
        简单实现，使用正则匹配。
        生产环境应使用 SQL 解析器（如 sqlglot）。
        
        Args:
            sql: SQL 语句
            
        Returns:
            表名列表
        """
        import re
        
        sql_upper = sql.upper()
        tables = []
        
        # 匹配 FROM / JOIN 后的表名
        patterns = [
            r'FROM\s+([a-zA-Z_][a-zA-Z0-9_]*)',
            r'JOIN\s+([a-zA-Z_][a-zA-Z0-9_]*)',
            r'INTO\s+([a-zA-Z_][a-zA-Z0-9_]*)',
            r'UPDATE\s+([a-zA-Z_][a-zA-Z0-9_]*)',
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, sql, re.IGNORECASE)
            tables.extend(matches)
        
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
        thread_id: Optional[str] = None
    ):
        """记录查询日志到 t_data_query_log。
        
        Args:
            question: 用户原始问题
            sql: 生成的 SQL
            success: 是否执行成功
            thread_id: 会话 ID
        """
        try:
            from app.models.data_agent_metadata import DataQueryLog
            from app.ai.utils.embedding_util import get_embedding
            
            with get_db_context() as db:
                log = DataQueryLog(
                    user_id=self.user_id,
                    thread_id=thread_id,
                    question=question,
                    generated_sql=sql,
                    sql_source="vanna",
                    is_correct=success,
                    question_embedding=get_embedding(question)
                )
                db.add(log)
                db.commit()
                logger.debug(f"查询日志已记录: question={question[:50]}...")
        except Exception as e:
            logger.warning(f"查询日志记录失败: {e}")


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
__all__ = ["DataAccessControl", "get_access_control", "DEFAULT_TABLE_WHITELIST", "TABLE_BLACKLIST"]
