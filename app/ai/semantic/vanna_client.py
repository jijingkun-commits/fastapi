"""Vanna 客户端封装：使用项目现有的 embedding 工具和 PGVector 存储。

依赖数据库配置：t_llm_model 中需要配置 model_type='embedding' 的模型。

重要：t_meta_tables.embedding 列定义必须与 EMBEDDING_DIMENSION 配置一致（当前为 2048 维）。
模型升级时需同步执行：ALTER TABLE + 重新生成向量。
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
            
        注意：embedding 维度必须与 t_meta_tables.embedding 列定义一致（当前为 2048 维）。
        """
        embedding = self.generate_embedding(question)
        if not embedding:
            logger.warning("无法生成问题 embedding，跳过向量检索，降级到关键词匹配")
            return self._fallback_keyword_search(question, schema)
            
        embedding_str = str(embedding)
        
        # 构建 Schema 过滤条件
        allowed_schemas = [s.lower() for s in ANALYTICS_SCHEMAS]
        if schema:
            schema_filter = [schema.lower()]
        else:
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
                    logger.info(f"向量检索未命中，降级到关键词匹配（Schema: {schema_filter}）")
                    return self._fallback_keyword_search(question, schema)
                
                # 第二步：获取每个表的完整列信息
                ddl_list = self._fetch_ddl_for_tables(conn, tables, similarity_threshold=0.3)
                
        except Exception as e:
            logger.warning(f"向量检索失败: {e}，降级到关键词匹配")
            return self._fallback_keyword_search(question, schema)
        
        if not ddl_list:
            logger.info("向量检索无高相似度结果，降级到关键词匹配")
            return self._fallback_keyword_search(question, schema)
        
        logger.info(f"检索到 {len(ddl_list)} 个相关表的 DDL")
        return ddl_list
    
    def _fetch_ddl_for_tables(self, conn, tables, similarity_threshold: float = 0.3) -> List[str]:
        """根据检索到的表记录获取完整 DDL。"""
        ddl_list = []
        for table_row in tables:
            table_id = table_row.id
            schema_name = table_row.schema_name or "public"
            table_name = table_row.table_name
            table_desc = table_row.description or ""
            similarity = getattr(table_row, 'similarity', 1.0)
            
            if similarity < similarity_threshold:
                continue
            
            col_sql = text("""
                SELECT column_name, display_name, data_type, description,
                       is_primary_key, is_foreign_key, foreign_table, foreign_column,
                       sample_values
                FROM t_meta_columns 
                WHERE table_id = :table_id
                ORDER BY is_primary_key DESC, column_name
            """)
            
            columns = conn.execute(col_sql, {"table_id": table_id}).fetchall()
            
            full_table_name = f"{schema_name}.{table_name}"
            ddl = self._build_complete_ddl(full_table_name, table_desc, columns)
            ddl_list.append(ddl)
            
            logger.debug(f"检索到表 {full_table_name}，相似度: {similarity:.3f}")
        
        return ddl_list

    def _fallback_keyword_search(self, question: str, schema: Optional[str] = None) -> List[str]:
        """降级方案：基于关键词匹配检索相关表。
        
        当向量检索不可用（embedding 生成失败、维度不匹配等）时，
        使用 ILIKE 在表名、显示名、描述字段中搜索问题关键词。
        """
        import re
        
        # 提取关键词：去除常见停用词，保留有意义的业务词汇
        stop_words = {"查询", "统计", "计算", "多少", "什么", "哪些", "按", "的", "总",
                      "汇总", "明细", "列表", "本月", "上月", "今年", "去年", "当前"}
        words = re.findall(r'[\u4e00-\u9fa5a-zA-Z_]+', question)
        keywords = [w for w in words if w not in stop_words and len(w) >= 2]
        
        if not keywords:
            logger.warning("无法提取有效关键词，跳过降级检索")
            return []
        
        # 构建 Schema 过滤
        allowed_schemas = [s.lower() for s in ANALYTICS_SCHEMAS]
        schema_filter = [schema.lower()] if schema else allowed_schemas
        
        # 构建 OR 条件匹配关键词
        conditions = []
        params = {"schemas": schema_filter}
        for i, kw in enumerate(keywords[:5]):
            param_name = f"kw_{i}"
            conditions.append(
                f"(LOWER(table_name) LIKE :{param_name} "
                f"OR LOWER(COALESCE(display_name, '')) LIKE :{param_name} "
                f"OR LOWER(COALESCE(description, '')) LIKE :{param_name})"
            )
            params[param_name] = f"%{kw.lower()}%"
        
        where_clause = " OR ".join(conditions)
        
        fallback_sql = text(f"""
            SELECT id, schema_name, table_name, display_name, description
            FROM t_meta_tables 
            WHERE LOWER(COALESCE(schema_name, 'public')) = ANY(:schemas)
              AND ({where_clause})
            LIMIT 5
        """)
        
        ddl_list = []
        try:
            with create_engine(self.metadata_db_url).connect() as conn:
                tables = conn.execute(fallback_sql, params).fetchall()
                
                if not tables:
                    logger.info(f"关键词降级检索未命中（关键词: {keywords}）")
                    return []
                
                ddl_list = self._fetch_ddl_for_tables(conn, tables, similarity_threshold=0.0)
                logger.info(f"关键词降级检索命中 {len(ddl_list)} 个表（关键词: {keywords}）")
                
        except Exception as e:
            logger.exception(f"关键词降级检索失败: {e}")
        
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
        """检索相关指标定义（基于语义相似度，带阈值过滤和去重）。
        
        查询 t_metric_definition 表，优化策略：
        - 相似度阈值 0.4，过滤不相关指标
        - 按 metric_name 去重（避免 A/AK 前缀重复占位）
        - 优先使用 query_template（可执行 SELECT），回退 sql_template
        - ETL 格式的 sql_template 不再直接截断展示（无用信息）
        - 最多返回 3 条
        """
        embedding = self.generate_embedding(question)
        if not embedding:
            return []
            
        embedding_str = str(embedding)
        
        # 检索相关指标（带相似度阈值 + 去重，同时取 query_template）
        sql = text("""
            SELECT DISTINCT ON (metric_name) 
                metric_id, metric_name, description, 
                query_template, sql_template, template_source,
                1 - (embedding <=> :embedding) AS similarity
            FROM t_metric_definition 
            WHERE is_active = TRUE 
              AND embedding IS NOT NULL
              AND 1 - (embedding <=> :embedding) > 0.4
            ORDER BY metric_name, embedding <=> :embedding
            LIMIT 10
        """)
        
        with create_engine(self.metadata_db_url).connect() as conn:
            rows = conn.execute(sql, {"embedding": embedding_str}).fetchall()
        
        # 按相似度排序，取 top 3
        rows = sorted(rows, key=lambda r: r.similarity, reverse=True)[:3]
            
        docs = []
        for row in rows:
            # 优先使用 query_template（可执行 SELECT），回退 sql_template
            sql_preview = ""
            if row.query_template:
                # query_template 是干净的 SELECT，可给更多字符
                sql_preview = row.query_template[:400]
                if len(row.query_template) > 400:
                    sql_preview += "..."
            elif row.sql_template:
                # 检查是否为 ETL 格式（DELETE/INSERT），跳过无用的 ETL 头部
                upper = row.sql_template.strip().upper()
                if upper.startswith("SELECT") or upper.startswith("WITH"):
                    sql_preview = row.sql_template[:300]
                    if len(row.sql_template) > 300:
                        sql_preview += "..."
                else:
                    sql_preview = "(ETL 脚本，暂无可执行查询模板)"
            
            doc = (
                f"指标代码: {row.metric_id}\n"
                f"指标名称: {row.metric_name}\n"
                f"定义说明: {row.description or ''}\n"
                f"SQL模板: {sql_preview}"
            )
            docs.append(doc)
            
        logger.info("指标文档检索: 阈值>0.4, 去重后返回 %d 条", len(docs))
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
        """通过项目统一的 get_llm() 调用 LLM 生成 SQL。
        
        Args:
            prompt: Vanna 传入的 prompt（消息列表或字符串）
            **kwargs:
                model_id: 用户选择的模型标识（可选，默认使用系统默认模型）
                enable_thinking: 是否启用深度思考（可选，默认 False）
        """
        from app.ai.llm_util import get_llm, _normalize_text_content
        from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
        
        model_id = kwargs.get("model_id")
        enable_thinking = kwargs.get("enable_thinking", False)
        
        try:
            llm = get_llm(
                enable_streaming=False,
                force_thinking=enable_thinking,
                model_id=model_id,
            )
            
            # dict messages -> LangChain messages
            raw = prompt if isinstance(prompt, list) else [{"role": "user", "content": prompt}]
            messages = []
            for m in raw:
                role = m.get("role", "user")
                content = m.get("content", "")
                if role == "system":
                    messages.append(SystemMessage(content=content))
                elif role == "assistant":
                    messages.append(AIMessage(content=content))
                else:
                    messages.append(HumanMessage(content=content))
            
            logger.info("Vanna submit_prompt: model_id=%s, enable_thinking=%s, messages=%d条",
                        model_id or "default", enable_thinking, len(messages))
            
            response = llm.invoke(messages)
            raw_content = response.content if hasattr(response, 'content') else response
            content = _normalize_text_content(raw_content)
            
            logger.info("LLM 响应: content_len=%d", len(content) if content else 0)
            
            if not content:
                logger.warning("LLM 返回空内容")
            
            return content
        except Exception as e:
            logger.error(f"LLM generation failed: {e}", exc_info=True)
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
