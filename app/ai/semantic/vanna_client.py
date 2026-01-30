"""
Vanna 客户端封装：使用项目现有的 embedding 工具和 PGVector 存储。

依赖数据库配置：t_llm_models 中需要配置 type='embedding' 的模型。
"""
import logging
from typing import List, Dict, Any, Optional
import pandas as pd
from vanna.base import VannaBase
from sqlalchemy import create_engine, text

from app.core.config import DATABASE_URL, ANALYTICS_SCHEMAS, ANALYTICS_DEFAULT_SCHEMA
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

    def get_related_ddl(self, question: str, schema: Optional[str] = None, **kwargs) -> List[str]:
        """
        检索相关 DDL（基于问题相似度）。
        
        改进：
        1. 基于问题语义检索相关表
        2. 获取完整的列信息（从 t_meta_columns）
        3. 构建完整的 CREATE TABLE DDL
        4. 支持按 Schema 过滤
        
        Args:
            question: 用户问题
            schema: 指定的 Schema（可选，None 表示搜索所有允许的 Schema）
            
        注意：智谱 embedding-3 输出 1024 维向量
        """
        embedding = self.generate_embedding(question)
        if not embedding:
            logger.warning("无法生成问题 embedding，跳过 DDL 检索")
            return []
            
        embedding_str = str(embedding)
        
        # 构建 Schema 过滤条件
        allowed_schemas = [s.lower() for s in ANALYTICS_SCHEMAS]
        if schema:
            # 如果指定了 schema，只搜索该 schema
            schema_filter = [schema.lower()]
        else:
            # 否则搜索所有允许的 schema
            schema_filter = allowed_schemas
        
        # 第一步：检索相关表（基于语义相似度 + Schema 过滤）
        table_sql = text("""
            SELECT id, schema_name, table_name, display_name, description,
                   1 - (embedding <=> :embedding) AS similarity
            FROM t_meta_tables 
            WHERE embedding IS NOT NULL
              AND LOWER(COALESCE(schema_name, 'public')) = ANY(:schemas)
            ORDER BY embedding <=> :embedding 
            LIMIT 5
        """)
        
        ddl_list = []
        
        try:
            with create_engine(self.metadata_db_url).connect() as conn:
                tables = conn.execute(table_sql, {
                    "embedding": embedding_str,
                    "schemas": schema_filter
                }).fetchall()
                
                if not tables:
                    logger.info(f"未检索到相关表（Schema 过滤: {schema_filter}）")
                    return []
                
                # 第二步：获取每个表的完整列信息
                for table_row in tables:
                    table_id = table_row.id
                    schema_name = table_row.schema_name or "public"
                    table_name = table_row.table_name
                    table_desc = table_row.description or ""
                    similarity = table_row.similarity
                    
                    # 只返回相似度较高的表（阈值 0.3）
                    if similarity < 0.3:
                        continue
                    
                    # 查询列信息
                    col_sql = text("""
                        SELECT column_name, display_name, data_type, description,
                               is_primary_key, is_foreign_key, foreign_table, foreign_column,
                               sample_values
                        FROM t_meta_columns 
                        WHERE table_id = :table_id
                        ORDER BY is_primary_key DESC, column_name
                    """)
                    
                    columns = conn.execute(col_sql, {"table_id": table_id}).fetchall()
                    
                    # 构建完整 DDL（包含 schema 前缀）
                    full_table_name = f"{schema_name}.{table_name}"
                    ddl = self._build_complete_ddl(full_table_name, table_desc, columns)
                    ddl_list.append(ddl)
                    
                    logger.debug(f"检索到表 {full_table_name}，相似度: {similarity:.3f}")
                
        except Exception as e:
            logger.exception(f"DDL 检索失败: {e}")
            return []
        
        logger.info(f"检索到 {len(ddl_list)} 个相关表的 DDL")
        return ddl_list
    
    def _build_complete_ddl(self, table_name: str, table_desc: str, columns) -> str:
        """构建完整的 DDL 语句（包含列注释）。
        
        Args:
            table_name: 表名
            table_desc: 表描述
            columns: 列信息列表
            
        Returns:
            完整的 CREATE TABLE DDL 字符串
        """
        col_definitions = []
        pk_columns = []
        fk_constraints = []
        
        for col in columns:
            col_name = col.column_name
            data_type = col.data_type or "TEXT"
            col_desc = col.description or col.display_name or ""
            
            # 构建列定义
            col_def = f"    {col_name} {data_type}"
            
            # 主键
            if col.is_primary_key:
                pk_columns.append(col_name)
            
            # 外键
            if col.is_foreign_key and col.foreign_table:
                fk_constraints.append(
                    f"    FOREIGN KEY ({col_name}) REFERENCES {col.foreign_table}({col.foreign_column or 'id'})"
                )
            
            # 添加列注释
            if col_desc:
                col_def += f"  -- {col_desc}"
            
            # 示例值（帮助 LLM 理解数据格式）
            if col.sample_values:
                col_def += f" (示例: {col.sample_values})"
            
            col_definitions.append(col_def)
        
        # 构建完整 DDL
        ddl_parts = [f"-- {table_desc}" if table_desc else f"-- 表 {table_name}"]
        ddl_parts.append(f"CREATE TABLE {table_name} (")
        ddl_parts.append(",\n".join(col_definitions))
        
        # 添加主键约束
        if pk_columns:
            ddl_parts[-1] += ","
            ddl_parts.append(f"    PRIMARY KEY ({', '.join(pk_columns)})")
        
        # 添加外键约束
        if fk_constraints:
            ddl_parts[-1] += ","
            ddl_parts.append(",\n".join(fk_constraints))
        
        ddl_parts.append(");")
        
        return "\n".join(ddl_parts)

    def get_related_documentation(self, question: str, **kwargs) -> List[str]:
        """
        检索相关指标定义 (基于语义相似度)。
        查询 t_dmp_ind_info。
        """
        embedding = self.generate_embedding(question)
        if not embedding:
            return []
            
        embedding_str = str(embedding)
        
        # 检索最相关的 5 个指标
        sql = text("""
            SELECT metric_code, metric_name, description, formula 
            FROM t_dmp_ind_info 
            ORDER BY embedding <=> :embedding 
            LIMIT 5
        """)
        
        with create_engine(self.metadata_db_url).connect() as conn:
            result = conn.execute(sql, {"embedding": embedding_str}).fetchall()
            
        docs = []
        for row in result:
            # 格式化文档块供 LLM 参考
            doc = (
                f"指标代码: {row.metric_code}\n"
                f"指标名称: {row.metric_name}\n"
                f"定义说明: {row.description}\n"
                f"计算逻辑: {row.formula}"
            )
            docs.append(doc)
            
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

    def system_message(self, message: str) -> Any:
        return {"role": "system", "content": message}

    def user_message(self, message: str) -> Any:
        return {"role": "user", "content": message}

    def assistant_message(self, message: str) -> Any:
        return {"role": "assistant", "content": message}
        
    def get_training_data(self, **kwargs) -> pd.DataFrame:
        """Get training data (dummy implementation)."""
        return pd.DataFrame()

    def remove_training_data(self, id: str, **kwargs) -> bool:
        """Remove training data (dummy implementation)."""
        return False
        
    def get_similar_question_sql(self, question: str, **kwargs) -> list:
        """Get similar questions (dummy implementation or reuse get_related_question_sql)."""
        return self.get_related_question_sql(question, **kwargs)

    def submit_prompt(self, prompt, **kwargs) -> str:
        """
        Submit prompt to LLM using system configuration.
        """
        from app.services.llm_config_service import LLMConfigService
        from openai import OpenAI
        
        # Get default chat model
        config = LLMConfigService.get_model_by_type("chat")
        if not config:
            logger.error("No chat model configured for Vanna.")
            return None
            
        try:
            client = OpenAI(api_key=config.api_key, base_url=config.base_url)
            
            # Construct messages
            # Vanna passes a list of dicts if using Chat interface, or string if completion
            # Usually prompt is a list of messages for chat models in Vanna
            
            messages = prompt if isinstance(prompt, list) else [{"role": "user", "content": prompt}]
            
            logger.info(f"Submitting prompt to {config.model_name}...")
            
            response = client.chat.completions.create(
                model=config.model_code,
                messages=messages,
                temperature=0, # SQL generation needs deterministic output
                max_tokens=2000 # Increased for SQL
            )
            
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"LLM generation failed: {e}")
            return None


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
