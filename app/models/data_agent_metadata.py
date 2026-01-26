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
    table_name = Column(String(100), unique=True, nullable=False, comment="表名")
    display_name = Column(String(100), comment="显示名称")
    description = Column(Text, comment="描述")
    category = Column(String(50), comment="分类")
    embedding = Column(Vector(1024), comment="表描述向量（智谱 embedding-3）")
    
    created_at = Column(TIMESTAMP, server_default=func.now())
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())

    columns = relationship("MetaColumn", back_populates="table", cascade="all, delete-orphan")

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
    embedding = Column(Vector(1024), comment="字段描述向量（智谱 embedding-3）")

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
    question_embedding = Column(Vector(1024), comment="问题向量（智谱 embedding-3）")
    created_at = Column(TIMESTAMP, server_default=func.now())

class Metric(Base):
    """指标定义表"""
    __tablename__ = "t_metrics"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False, comment="指标名称")
    description = Column(Text, comment="描述")
    metric_type = Column(String(20), comment="count, sum, avg, derived")
    model_name = Column(String(100), comment="关联的数据模型")
    field_name = Column(String(100), comment="计算字段")
    formula = Column(Text, comment="计算公式（派生指标）")
    filter_condition = Column(Text, comment="WHERE 条件")
    synonyms = Column(ARRAY(String), comment="同义词数组")
    embedding = Column(Vector(1024), comment="指标描述向量（智谱 embedding-3）")
    
    created_by = Column(Integer, comment="创建人ID")
    created_at = Column(TIMESTAMP, server_default=func.now())
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())
