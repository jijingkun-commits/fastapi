"""
Vanna 客户端封装：使用项目现有的 embedding 工具和 PGVector 存储。

依赖数据库配置：t_llm_models 中需要配置 type='embedding' 的模型。
"""
import logging
from typing import List, Dict, Any, Optional
import pandas as pd
from vanna.base import VannaBase
from sqlalchemy import create_engine, text

from app.core.config import DATABASE_URL
from app.db.session import analytics_engine
from app.ai.utils.embedding_util import get_embedding

logger = logging.getLogger(__name__)


class VannaPGVector(VannaBase):
    """
    基于 PGVector 的 Vanna 实现。
    使用项目统一的 embedding 工具（从数据库读取模型配置）。
    """
    def __init__(self, config=None):
        if config is None:
            config = {}
            
        VannaBase.__init__(self, config=config)
        self.metadata_db_url = DATABASE_URL
        
    def generate_embedding(self, data: str) -> Optional[List[float]]:
        """使用项目统一的 embedding 工具生成向量"""
        return get_embedding(data)

    def add_ddl(self, ddl: str, **kwargs) -> str:
        """
        Store DDL in t_meta_tables (simulated).
        In our architecture, we use schema_sync.py to populate metadata.
        This method is kept for compatibility but logs a warning.
        """
        raise NotImplementedError("Use schema_sync.py to manage DDL/schema metadata.")

    def add_documentation(self, documentation: str, **kwargs) -> str:
        """Add documentation for RAG."""
        # TODO: Implement adding to t_metrics or documentation table
        pass

    def add_question_sql(self, question: str, sql: str, **kwargs) -> str:
        """Add training data (question-SQL pair) to t_data_query_log."""
        # This will be handled by the training API
        pass

    def get_related_ddl(self, question: str, **kwargs) -> List[str]:
        """
        检索相关 DDL（基于问题相似度）。
        查询 t_meta_tables 和 t_meta_columns，使用 pgvector。
        注意：智谱 embedding-3 输出 1024 维向量
        """
        embedding = self.generate_embedding(question)
        embedding_str = str(embedding)
        
        sql = text("""
            SELECT table_name, description 
            FROM t_meta_tables 
            ORDER BY embedding <=> :embedding 
            LIMIT 5
        """)
        
        with create_engine(self.metadata_db_url).connect() as conn:
            result = conn.execute(sql, {"embedding": embedding_str}).fetchall()
            
        ddl_list = []
        for row in result:
             # Basic DDL reconstruction - in production, we might store full CREATE TABLE
             ddl_list.append(f"CREATE TABLE {row.table_name} ...; -- {row.description}")
             
        return ddl_list

    def get_related_documentation(self, question: str, **kwargs) -> List[str]:
        """
        Retrieve relevant metrics/documentation.
        Query t_metrics.
        """
        embedding = self.generate_embedding(question)
        embedding_str = str(embedding)
        
        sql = text("""
            SELECT name, description, formula 
            FROM t_metrics 
            ORDER BY embedding <=> :embedding 
            LIMIT 5
        """)
        
        with create_engine(self.metadata_db_url).connect() as conn:
            result = conn.execute(sql, {"embedding": embedding_str}).fetchall()
            
        docs = []
        for row in result:
            docs.append(f"Metric: {row.name}\nDescription: {row.description}\nFormula: {row.formula}")
            
        return docs

    def get_related_question_sql(self, question: str, **kwargs) -> List[Dict]:
        """
        Retrieve similar past questions.
        Query t_data_query_log where trained=true.
        """
        embedding = self.generate_embedding(question)
        embedding_str = str(embedding)
        
        sql = text("""
            SELECT question, generated_sql 
            FROM t_data_query_log 
            WHERE trained = true 
            ORDER BY question_embedding <=> :embedding 
            LIMIT 3
        """)
        
        with create_engine(self.metadata_db_url).connect() as conn:
            result = conn.execute(sql, {"embedding": embedding_str}).fetchall()
            
        return [{"question": row.question, "sql": row.generated_sql} for row in result]

    def run_sql(self, sql: str, **kwargs) -> pd.DataFrame:
        """Execute SQL on the Analytics DB."""
        return pd.read_sql(sql, analytics_engine)

    def submit_prompt(self, prompt, **kwargs) -> str:
        """
        Submit prompt to LLM (OpenAI Chat).
        Override if using a different LLM provider via Vanna.
        """
        # OpenAI_Chat implementation usually sufficient if configured correctly
        # Or use our own LLM client
        return super().submit_prompt(prompt, **kwargs)


# 直接导出 VannaPGVector 作为 VannaClient（暂不需要 OpenAI Chat 继承）
VannaClient = VannaPGVector

# 全局单例（延迟初始化）
_vanna_instance = None

def get_vanna() -> VannaClient:
    """获取 Vanna 客户端单例"""
    global _vanna_instance
    if _vanna_instance is None:
        _vanna_instance = VannaClient()
    return _vanna_instance

# 兼容旧代码的全局变量
vanna = None  # 使用 get_vanna() 替代直接访问
