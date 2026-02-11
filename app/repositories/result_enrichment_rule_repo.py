"""结果增强规则仓储（中文注释）。"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from app.models.result_enrichment_rule import (
    ResultEnrichmentRule,
    ResultEnrichmentRuleAudit,
)


class ResultEnrichmentRuleRepo:
    """结果增强规则仓储。"""

    def list_rules(self, db: Session, include_disabled: bool = True) -> List[ResultEnrichmentRule]:
        """按优先级获取规则列表。"""
        query = db.query(ResultEnrichmentRule)
        if not include_disabled:
            query = query.filter(ResultEnrichmentRule.enabled.is_(True))

        return query.order_by(ResultEnrichmentRule.priority.asc(), ResultEnrichmentRule.id.asc()).all()

    def list_active_rules(self, db: Session) -> List[ResultEnrichmentRule]:
        """获取启用中的规则列表。"""
        return self.list_rules(db, include_disabled=False)

    def get_rule_by_id(self, db: Session, rule_id: int) -> Optional[ResultEnrichmentRule]:
        """按 ID 获取规则。"""
        return db.query(ResultEnrichmentRule).filter(ResultEnrichmentRule.id == rule_id).first()

    def get_rule_by_code(self, db: Session, rule_code: str) -> Optional[ResultEnrichmentRule]:
        """按编码获取规则。"""
        return db.query(ResultEnrichmentRule).filter(ResultEnrichmentRule.rule_code == rule_code).first()

    def create_rule(
        self,
        db: Session,
        payload: Dict[str, Any],
        operator_id: Optional[str] = None,
    ) -> ResultEnrichmentRule:
        """创建规则并写审计。"""
        rule = ResultEnrichmentRule(**payload)
        db.add(rule)
        db.flush()

        self.add_audit(
            db,
            rule_id=rule.id,
            op_type="create",
            before_json=None,
            after_json=self.serialize_rule(rule),
            operator_id=operator_id,
        )
        return rule

    def update_rule(
        self,
        db: Session,
        rule: ResultEnrichmentRule,
        payload: Dict[str, Any],
        operator_id: Optional[str] = None,
    ) -> ResultEnrichmentRule:
        """更新规则并写审计。"""
        before = self.serialize_rule(rule)
        for key, value in payload.items():
            setattr(rule, key, value)

        db.flush()
        self.add_audit(
            db,
            rule_id=rule.id,
            op_type="update",
            before_json=before,
            after_json=self.serialize_rule(rule),
            operator_id=operator_id,
        )
        return rule

    def set_rule_enabled(
        self,
        db: Session,
        rule: ResultEnrichmentRule,
        enabled: bool,
        operator_id: Optional[str] = None,
    ) -> ResultEnrichmentRule:
        """启停规则并写审计。"""
        before = self.serialize_rule(rule)
        rule.enabled = enabled
        db.flush()
        self.add_audit(
            db,
            rule_id=rule.id,
            op_type="enable" if enabled else "disable",
            before_json=before,
            after_json=self.serialize_rule(rule),
            operator_id=operator_id,
        )
        return rule

    def update_rule_priority(
        self,
        db: Session,
        rule: ResultEnrichmentRule,
        priority: int,
        operator_id: Optional[str] = None,
    ) -> ResultEnrichmentRule:
        """更新优先级并写审计。"""
        before = self.serialize_rule(rule)
        rule.priority = priority
        db.flush()
        self.add_audit(
            db,
            rule_id=rule.id,
            op_type="reorder",
            before_json=before,
            after_json=self.serialize_rule(rule),
            operator_id=operator_id,
        )
        return rule

    def add_audit(
        self,
        db: Session,
        *,
        rule_id: int,
        op_type: str,
        before_json: Optional[Dict[str, Any]],
        after_json: Optional[Dict[str, Any]],
        operator_id: Optional[str],
    ) -> ResultEnrichmentRuleAudit:
        """写入审计记录。"""
        audit = ResultEnrichmentRuleAudit(
            rule_id=rule_id,
            op_type=op_type,
            before_json=before_json,
            after_json=after_json,
            operator_id=operator_id,
        )
        db.add(audit)
        return audit

    @staticmethod
    def serialize_rule(rule: ResultEnrichmentRule) -> Dict[str, Any]:
        """序列化规则用于审计。"""
        return {
            "id": rule.id,
            "rule_code": rule.rule_code,
            "rule_name": rule.rule_name,
            "enabled": rule.enabled,
            "priority": rule.priority,
            "key_column_candidates": list(rule.key_column_candidates or []),
            "target_column": rule.target_column,
            "source_table": rule.source_table,
            "source_key_column": rule.source_key_column,
            "source_value_column": rule.source_value_column,
            "source_date_column": rule.source_date_column,
            "result_date_column_candidates": list(rule.result_date_column_candidates or []),
            "description": rule.description,
            "created_by": rule.created_by,
            "updated_by": rule.updated_by,
            "created_at": rule.created_at.isoformat() if rule.created_at else None,
            "updated_at": rule.updated_at.isoformat() if rule.updated_at else None,
        }

