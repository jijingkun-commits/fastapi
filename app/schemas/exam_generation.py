"""AI 出题任务相关 schema（中文注释）。"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


ExamQuestionType = Literal["single_choice", "multiple_choice", "judge", "short_answer"]
ExamJobStatus = Literal["queued", "running", "succeeded", "failed"]


class DatasetOption(BaseModel):
    dataset_id: str
    label: str


class DifficultyDistribution(BaseModel):
    easy: float = 0.4
    medium: float = 0.4
    hard: float = 0.2

    @model_validator(mode="after")
    def validate_total(self):
        total = float(self.easy) + float(self.medium) + float(self.hard)
        if abs(total - 1.0) > 0.01:
            raise ValueError("难度分布之和必须约等于 1")
        return self


class ScoreStrategy(BaseModel):
    single_choice: int = 2
    multiple_choice: int = 3
    judge: int = 1
    short_answer: int = 10


class PaperRenderOptions(BaseModel):
    answer_section_enabled: bool = True
    answer_page_break: bool = True
    answer_explanation_mode: Literal["short"] = "short"


class PaperTemplateRequest(BaseModel):
    paper_title: str = Field(min_length=1, max_length=120)
    single_choice_count: int = Field(default=5, ge=0, le=50)
    multiple_choice_count: int = Field(default=3, ge=0, le=50)
    judge_count: int = Field(default=3, ge=0, le=50)
    short_answer_count: int = Field(default=2, ge=0, le=50)
    difficulty_distribution: DifficultyDistribution = Field(default_factory=DifficultyDistribution)
    score_strategy: ScoreStrategy = Field(default_factory=ScoreStrategy)
    answer_section_enabled: bool = True
    answer_page_break: bool = True
    answer_explanation_mode: Literal["short"] = "short"

    @property
    def total_question_count(self) -> int:
        return int(self.single_choice_count + self.multiple_choice_count + self.judge_count + self.short_answer_count)

    def build_render_options(self) -> PaperRenderOptions:
        return PaperRenderOptions(
            answer_section_enabled=self.answer_section_enabled,
            answer_page_break=self.answer_page_break,
            answer_explanation_mode=self.answer_explanation_mode,
        )

    @model_validator(mode="after")
    def validate_total(self):
        if self.total_question_count <= 0:
            raise ValueError("总题数必须大于 0")
        return self


class QuestionEvidence(BaseModel):
    dataset_id: str
    document_id: Optional[str] = None
    source_name: str
    excerpt: str
    score: float = 0.0


class QuestionOption(BaseModel):
    key: str
    text: str


class ExamQuestion(BaseModel):
    question_id: str
    question_type: ExamQuestionType
    stem: str
    options: list[QuestionOption] = Field(default_factory=list)
    answers: list[str] = Field(default_factory=list)
    explanation: str
    reference_answer: Optional[str] = None
    answer_points: list[str] = Field(default_factory=list)
    evidence: list[QuestionEvidence] = Field(default_factory=list)


class PaperContract(BaseModel):
    paper_title: str
    dataset_ids: list[str]
    generated_at: datetime
    questions: list[ExamQuestion]
    render_options: PaperRenderOptions = Field(default_factory=PaperRenderOptions)


class ExamQualityIssue(BaseModel):
    code: str
    message: str
    question_id: Optional[str] = None


class ExamQualityReport(BaseModel):
    passed: bool
    duplicate_count: int = 0
    evidence_missing_count: int = 0
    coverage_score: float = 0.0
    issues: list[ExamQualityIssue] = Field(default_factory=list)


class ExamGenerationJobCreateRequest(BaseModel):
    dataset_ids: list[str] = Field(min_length=1)
    template: PaperTemplateRequest

    @field_validator("dataset_ids")
    @classmethod
    def validate_datasets(cls, value: list[str]) -> list[str]:
        normalized = [str(item).strip() for item in value if str(item).strip()]
        if not normalized:
            raise ValueError("至少选择一个知识库")
        deduped: list[str] = []
        for item in normalized:
            if item not in deduped:
                deduped.append(item)
        return deduped


class ExamGenerationJobSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    title: str
    status: ExamJobStatus
    dataset_ids: list[str]
    asset_id: Optional[int] = None
    minio_object_key: Optional[str] = None
    download_url: Optional[str] = None
    error_message: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None


class ExamGenerationJobDetail(ExamGenerationJobSummary):
    request_snapshot: dict[str, Any]
    result_payload: dict[str, Any]


class ExamTemplateResponse(BaseModel):
    template: PaperTemplateRequest
    available_datasets: list[DatasetOption]
    limits: dict[str, int]
