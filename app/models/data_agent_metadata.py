from sqlalchemy import Column, Integer, String, Text, Boolean, TIMESTAMP, ForeignKey, UniqueConstraint, ARRAY
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from pgvector.sqlalchemy import Vector
from app.db.base import Base

class MetaTable(Base):
    """表元数据"""
    __tablename__ = "t_meta_tables"

    id = Column(Integer, primary_key=True, index=True)
    schema_name = Column(String(100), default="public", nullable=False, comment="Schema 名称")
    table_name = Column(String(100), nullable=False, comment="表名")
    display_name = Column(String(100), comment="显示名称")
    description = Column(Text, comment="描述")
    category = Column(String(50), comment="分类")
    embedding = Column(Vector(2048), comment="表描述向量（智谱 embedding-3）")
    
    created_at = Column(TIMESTAMP, server_default=func.now())
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())

    columns = relationship("MetaColumn", back_populates="table", cascade="all, delete-orphan")
    
    __table_args__ = (
        UniqueConstraint('schema_name', 'table_name', name='uq_schema_table'),
    )

class MetaColumn(Base):
    """字段元数据"""
    __tablename__ = "t_meta_columns"

    id = Column(Integer, primary_key=True, index=True)
    table_id = Column(Integer, ForeignKey("t_meta_tables.id", ondelete="CASCADE"), nullable=False)
    column_name = Column(String(100), nullable=False, comment="字段名")
    display_name = Column(String(100), comment="显示名称")
    data_type = Column(String(50), comment="数据类型")
    description = Column(Text, comment="描述")
    is_primary_key = Column(Boolean, default=False, comment="是否主键")
    is_foreign_key = Column(Boolean, default=False, comment="是否外键")
    foreign_table = Column(String(100), comment="外键关联表")
    foreign_column = Column(String(100), comment="外键关联字段")
    sample_values = Column(Text, comment="示例值")
    embedding = Column(Vector(2048), comment="字段描述向量（智谱 embedding-3）")

    table = relationship("MetaTable", back_populates="columns")

    __table_args__ = (
        UniqueConstraint('table_id', 'column_name', name='uq_table_column'),
    )

class MetaRelation(Base):
    """表关系元数据"""
    __tablename__ = "t_meta_relations"

    id = Column(Integer, primary_key=True, index=True)
    from_table = Column(String(100), nullable=False, comment="源表")
    from_column = Column(String(100), nullable=False, comment="源字段")
    to_table = Column(String(100), nullable=False, comment="目标表")
    to_column = Column(String(100), nullable=False, comment="目标字段")
    relation_type = Column(String(20), default="foreign_key", comment="关系类型")
    join_hint = Column(Text, comment="关联提示")

class DataQueryLog(Base):
    """问数查询日志"""
    __tablename__ = "t_data_query_log"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, comment="用户ID")
    thread_id = Column(String(100), comment="会话ID")
    question = Column(Text, nullable=False, comment="用户原始问题")
    generated_sql = Column(Text, comment="生成的 SQL")
    sql_source = Column(String(20), comment="'metric' | 'vanna' | 'template'")
    execution_result = Column(JSONB, comment="执行结果摘要")
    is_correct = Column(Boolean, comment="是否正确（用户反馈）")
    corrected_sql = Column(Text, comment="人工修正后的 SQL")
    trained = Column(Boolean, default=False, comment="是否已训练进向量库")
    question_embedding = Column(Vector(2048), comment="问题向量（智谱 embedding-3）")
    created_at = Column(TIMESTAMP, server_default=func.now())


class Metric(Base):
    """指标定义，对齐数据库表 t_metric_definition 真实 schema。"""
    __tablename__ = "t_metric_definition"

    metric_id = Column(String(50), primary_key=True, comment="指标唯一编码")
    metric_name = Column(String(200), nullable=False, comment="指标名称")
    aliases = Column(Text, comment="别名/同义词（逗号分隔）")
    description = Column(Text, nullable=False, comment="自然语言口径描述（向量化核心字段）")
    category = Column(String(100), comment="指标分类")
    sub_category = Column(String(100), comment="指标子分类")
    unit = Column(String(50), comment="单位")
    frequency = Column(String(20), comment="统计频率")
    sql_template = Column(Text, comment="原始 SQL 模板（可能是 ETL 脚本）")
    query_template = Column(Text, comment="可直接执行的 SELECT 查询模板")
    template_source = Column(String(20), default="none", comment="模板来源: manual|ai_extract|result_lookup|none")
    embedding = Column(Vector(2048), comment="语义向量（智谱 embedding-3，2048 维）")
    is_active = Column(Boolean, default=True, comment="是否启用")
    created_at = Column(TIMESTAMP, server_default=func.now())
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())

# === 废弃表说明 ===
# t_metrics 表已废弃，统一使用 t_metric_definition
# t_dmp_ind_info 表已废弃，不再使用 DIDP 原始格式
# 
# 指标定义表现在只有一个：t_metric_definition
# 详见 docs/开发文档/架构设计/数据库设计.md
