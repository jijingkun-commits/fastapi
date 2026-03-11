"""AI 出题任务与历史记录模型（中文注释）。"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Index, Integer, JSON, String, Text, text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class ExamGenerationJob(Base):
    __tablename__ = "t_exam_generation_job"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True, comment="创建任务的管理员 ID")
    title: Mapped[str] = mapped_column(String(120), nullable=False, comment="试卷标题")
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="queued", comment="任务状态")
    dataset_ids: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list, comment="数据集 ID 列表")
    request_snapshot: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict, comment="提交快照")
    result_payload: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict, comment="结果 canonical")
    asset_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True, index=True, comment="导出资产 ID")
    minio_object_key: Mapped[str | None] = mapped_column(String(255), nullable=True, comment="导出 PDF 对象路径")
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True, comment="失败原因")
    started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, comment="开始执行时间")
    finished_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, comment="完成时间")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, nullable=False, comment="创建时间")
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, onupdate=datetime.now, nullable=False, comment="更新时间")

    __table_args__ = (
        Index("idx_exam_generation_job_user_created", "user_id", text("created_at DESC")),
        Index("idx_exam_generation_job_user_status_updated", "user_id", "status", text("updated_at DESC")),
    )
