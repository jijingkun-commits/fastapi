"""多智能体交付合同模型。"""

from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


DeliverableStatus = Literal["success", "partial", "failed", "missing"]


class GoalContract(BaseModel):
    """问题合同目标。"""

    goal_id: str = Field(min_length=1)
    order: int = Field(ge=1)
    kind: str = Field(min_length=1)
    title: str = Field(min_length=1)
    must_answer: bool = True
    allowed_agents: List[str] = Field(default_factory=list)
    source: str = ""
    confidence: Optional[float] = Field(default=None, ge=0.0, le=1.0)


class IntentPlanContract(BaseModel):
    """意图计划合同。"""

    version: int = Field(default=1, ge=1)
    source: str = Field(min_length=1)
    user_query: str = ""
    goals: List[GoalContract] = Field(min_length=1)


class RouteDecisionContract(BaseModel):
    """路由决策合同。"""

    goal_id: str = Field(min_length=1)
    target_agent: str = Field(min_length=1)
    dispatch_reason: str = ""
    priority: int = 0
    blocked_by: List[str] = Field(default_factory=list)


class DeliverableContract(BaseModel):
    """交付物合同。"""

    goal_id: str = Field(min_length=1)
    kind: str = Field(min_length=1)
    status: DeliverableStatus
    summary: str = ""
    payload: Dict[str, Any] = Field(default_factory=dict)
    error_code: str = ""
    evidence_ref: Dict[str, Any] = Field(default_factory=dict)


class CoverageMissingGoalContract(BaseModel):
    """覆盖缺口条目。"""

    goal_id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    reason: str = Field(min_length=1)


class CoverageReportContract(BaseModel):
    """覆盖率报告合同。"""

    model_config = ConfigDict(populate_by_name=True)

    pass_: bool = Field(alias="pass")
    total_goals: int = Field(ge=0)
    answered_goals: int = Field(ge=0)
    missing_goals: List[CoverageMissingGoalContract] = Field(default_factory=list)
    matched_goal_ids: List[str] = Field(default_factory=list)
    goal_results: Dict[str, DeliverableContract] = Field(default_factory=dict)


class FinalAnswerContract(BaseModel):
    """最终答复合同。"""

    content: str = Field(min_length=1)
    coverage_pass: bool
    missing_goal_count: int = Field(ge=0)
    render_version: str = "v1"
