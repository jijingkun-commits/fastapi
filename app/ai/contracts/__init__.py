"""交付合同定义与校验器。"""

from app.ai.contracts.delivery_contract_validators import (
    build_contract_validation_meta,
    validate_active_goals_contract,
    validate_coverage_report_contract,
    validate_intent_plan_contract,
)
from app.ai.contracts.delivery_contracts import (
    ActiveGoalsContract,
    CoverageMissingGoalContract,
    CoverageReportContract,
    DeliverableContract,
    FinalAnswerContract,
    GoalContract,
    IntentPlanContract,
    RouteDecisionContract,
)

__all__ = [
    "GoalContract",
    "ActiveGoalsContract",
    "IntentPlanContract",
    "RouteDecisionContract",
    "DeliverableContract",
    "CoverageMissingGoalContract",
    "CoverageReportContract",
    "FinalAnswerContract",
    "validate_active_goals_contract",
    "validate_intent_plan_contract",
    "validate_coverage_report_contract",
    "build_contract_validation_meta",
]
