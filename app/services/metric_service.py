"""指标服务模块：提供指标匹配和表可用性检查功能。"""
import logging
import re
from typing import Optional, Set, List, Tuple, Dict, Any

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from app.core.config import DATABASE_URL, ANALYTICS_DATABASE_URL

logger = logging.getLogger(__name__)

# 有效的 schema 前缀（用于表名提取）
VALID_SCHEMAS = {'fdmdata', 'sdmdata', 'admdata', 'odsfile'}


class MetricDefinition:
    """指标定义数据类。"""
    
    def __init__(self, row: tuple):
        self.metric_id = row[0]
        self.metric_name = row[1]
        self.aliases = row[2] or ""
        self.description = row[3] or ""
        self.sql_template = row[4]
        self.category = row[5]
        self.unit = row[6]
    
    def __repr__(self):
        return f"MetricDefinition({self.metric_id}: {self.metric_name})"


class MetricService:
    """指标服务：提供指标匹配和表可用性检查。"""
    
    def __init__(self):
        self._chat_engine = None
        self._data_engine = None
        self._existing_tables: Optional[Set[str]] = None
    
    @property
    def chat_engine(self):
        if self._chat_engine is None:
            self._chat_engine = create_engine(str(DATABASE_URL))
        return self._chat_engine
    
    @property
    def data_engine(self):
        if self._data_engine is None:
            self._data_engine = create_engine(str(ANALYTICS_DATABASE_URL))
        return self._data_engine
    
    def match_metric(self, question: str) -> Optional[MetricDefinition]:
        """从问题中匹配预定义指标。
        
        匹配策略（按优先级）：
        1. 向量相似度搜索（使用 embedding）
        2. 指标名称精确匹配（降级方案）
        3. 别名关键词匹配（降级方案）
        
        Args:
            question: 用户问题
            
        Returns:
            匹配到的指标定义，或 None
        """
        question_lower = question.lower()
        
        try:
            # 优先尝试向量搜索
            vector_result = self._match_metric_by_vector(question)
            if vector_result:
                return vector_result
            
            # 降级到关键词匹配
            return self._match_metric_by_keyword(question_lower)
                
        except Exception as e:
            logger.exception(f"指标匹配失败: {e}")
            return None
    
    def _match_metric_by_vector(self, question: str, similarity_threshold: float = 0.6) -> Optional[MetricDefinition]:
        """使用向量相似度搜索匹配指标。
        
        查询 t_metric_definition 表的 embedding 列进行语义匹配。
        
        Args:
            question: 用户问题
            similarity_threshold: 相似度阈值（0-1），低于此值不返回
            
        Returns:
            匹配到的指标定义，或 None
        """
        try:
            from app.ai.utils.embedding_util import get_embedding
            
            # 生成问题的 embedding
            question_embedding = get_embedding(question)
            if not question_embedding:
                logger.warning("无法生成问题 embedding，跳过向量搜索")
                return None
            
            embedding_str = str(question_embedding)
            
            with self.chat_engine.connect() as conn:
                # 向量相似度搜索（统一使用 t_metric_definition）
                # 使用余弦距离，结果越小越相似
                # 1 - distance = similarity
                result = conn.execute(text("""
                    SELECT 
                        metric_id,
                        metric_name,
                        aliases,
                        description,
                        sql_template,
                        category,
                        unit,
                        1 - (embedding <=> :embedding) as similarity
                    FROM t_metric_definition
                    WHERE is_active = TRUE
                      AND embedding IS NOT NULL
                      AND sql_template IS NOT NULL
                    ORDER BY embedding <=> :embedding
                    LIMIT 3
                """), {"embedding": embedding_str})
                
                rows = result.fetchall()
                
                if not rows:
                    logger.debug("向量搜索无结果")
                    return None
                
                # 检查最佳匹配的相似度
                best_row = rows[0]
                similarity = best_row.similarity if hasattr(best_row, 'similarity') else 0
                
                logger.info(f"向量搜索最佳匹配: {best_row.metric_name}, 相似度: {similarity:.3f}")
                
                if similarity >= similarity_threshold:
                    metric = MetricDefinition((
                        best_row.metric_id,
                        best_row.metric_name,
                        best_row.aliases or "",
                        best_row.description or "",
                        best_row.sql_template,
                        best_row.category or "",
                        best_row.unit or ""
                    ))
                    logger.info(f"匹配到指标(向量搜索): {metric.metric_name} (相似度: {similarity:.3f})")
                    return metric
                else:
                    logger.debug(f"向量搜索相似度 {similarity:.3f} 低于阈值 {similarity_threshold}")
                    return None
                    
        except Exception as e:
            # 向量搜索失败不应阻止降级到关键词匹配
            logger.warning(f"向量搜索失败，将降级到关键词匹配: {e}")
            return None
    
    def _match_metric_by_keyword(self, question_lower: str) -> Optional[MetricDefinition]:
        """使用关键词匹配指标（降级方案）。
        
        查询 t_metric_definition 表进行名称和别名匹配。
        
        Args:
            question_lower: 小写的用户问题
            
        Returns:
            匹配到的指标定义，或 None
        """
        try:
            with self.chat_engine.connect() as conn:
                result = conn.execute(text("""
                    SELECT metric_id, metric_name, aliases, description, 
                           sql_template, category, unit
                    FROM t_metric_definition
                    WHERE is_active = TRUE AND sql_template IS NOT NULL
                """))
                metrics = result.fetchall()
                
                # 关键词匹配
                for row in metrics:
                    metric = MetricDefinition(row)
                    
                    # 检查指标名称
                    if metric.metric_name and metric.metric_name.lower() in question_lower:
                        logger.info(f"匹配到指标(名称): {metric.metric_name}")
                        return metric
                    
                    # 检查别名
                    if metric.aliases:
                        for alias in metric.aliases.split(','):
                            alias = alias.strip()
                            if alias and alias.lower() in question_lower:
                                logger.info(f"匹配到指标(别名): {metric.metric_name} <- {alias}")
                                return metric
                
                logger.info(f"关键词匹配无结果: {question_lower[:50]}...")
                return None
                
        except Exception as e:
            logger.exception(f"关键词匹配失败: {e}")
            return None
    
    def get_metric_by_id(self, metric_id: str) -> Optional[MetricDefinition]:
        """根据 ID 获取指标定义。"""
        try:
            with self.chat_engine.connect() as conn:
                result = conn.execute(text("""
                    SELECT metric_id, metric_name, aliases, description, 
                           sql_template, category, unit
                    FROM t_metric_definition
                    WHERE metric_id = :metric_id
                """), {"metric_id": metric_id})
                
                row = result.fetchone()
                return MetricDefinition(row) if row else None
                
        except Exception as e:
            logger.exception(f"获取指标失败: {e}")
            return None
    
    def extract_tables_from_sql(self, sql: str) -> Set[str]:
        """从 SQL 中提取依赖的表名。
        
        使用 sqlglot 进行 AST 解析，比正则更准确可靠。
        
        Args:
            sql: SQL 语句
            
        Returns:
            表名集合（格式：schema.table 或 table）
        """
        if not sql:
            return set()
        
        # 使用统一的 SQL 解析工具
        from app.ai.utils.sql_parser import extract_tables_from_sql as parse_tables
        
        all_tables = parse_tables(sql)
        
        # 过滤：只保留有效 schema 的表（如果有 schema 前缀）
        # 或者没有 schema 前缀的表名
        filtered_tables = set()
        for table in all_tables:
            if '.' in table:
                schema = table.split('.')[0]
                if schema in VALID_SCHEMAS:
                    filtered_tables.add(table)
            else:
                # 没有 schema 前缀的表也保留
                filtered_tables.add(table)
        
        return filtered_tables
    
    def get_existing_tables(self, force_refresh: bool = False) -> Set[str]:
        """获取数据库中已存在的表。
        
        Args:
            force_refresh: 是否强制刷新缓存
            
        Returns:
            表名集合
        """
        if self._existing_tables is not None and not force_refresh:
            return self._existing_tables
        
        try:
            with self.data_engine.connect() as conn:
                result = conn.execute(text("""
                    SELECT table_schema, table_name 
                    FROM information_schema.tables 
                    WHERE table_schema NOT IN ('information_schema', 'pg_catalog')
                """))
                self._existing_tables = {
                    f"{row[0]}.{row[1]}".lower() 
                    for row in result
                }
                logger.debug(f"已缓存 {len(self._existing_tables)} 张表")
                return self._existing_tables
                
        except Exception as e:
            logger.exception(f"获取表列表失败: {e}")
            return set()
    
    def check_tables_availability(self, sql: str) -> Tuple[bool, List[str]]:
        """检查 SQL 依赖的表是否都存在。
        
        Args:
            sql: SQL 语句
            
        Returns:
            (all_available, missing_tables) 元组
            - all_available: 是否所有表都可用
            - missing_tables: 缺失的表列表
        """
        required_tables = self.extract_tables_from_sql(sql)
        if not required_tables:
            return (True, [])
        
        existing = self.get_existing_tables()
        missing = [t for t in required_tables if t not in existing]
        
        return (len(missing) == 0, missing)
    
    def prepare_sql(self, sql_template: str, params: Optional[Dict[str, Any]] = None) -> str:
        """准备 SQL 语句，替换参数占位符。
        
        支持的占位符格式：
        - ${param_name} -> 替换为参数值
        - :param_name -> 保留给 SQLAlchemy 绑定
        
        Args:
            sql_template: SQL 模板
            params: 参数字典
            
        Returns:
            替换后的 SQL
        """
        if not params:
            params = {}
        
        sql = sql_template
        
        # 替换 ${...} 格式的占位符
        for key, value in params.items():
            sql = sql.replace(f"${{{key}}}", str(value))
        
        return sql


# 模块级单例
_metric_service: Optional[MetricService] = None


def get_metric_service() -> MetricService:
    """获取指标服务单例。"""
    global _metric_service
    if _metric_service is None:
        _metric_service = MetricService()
    return _metric_service
