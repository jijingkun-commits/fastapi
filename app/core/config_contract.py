"""配置契约定义：统一维护配置来源与类型约束（中文注释）。"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Literal, Tuple

ConfigSource = Literal["db-dynamic", "env-only"]
ConfigValueType = Literal["string", "number", "boolean", "json"]


@dataclass(frozen=True)
class ConfigSpec:
    """配置项契约定义。"""

    key: str
    source: ConfigSource
    value_type: ConfigValueType = "string"
    default: Any = ""
    env_key: str | None = None
    db_key: str | None = None
    aliases: Tuple[str, ...] = ()
    editable: bool = True
    is_secret: bool = False

    def all_db_keys(self) -> Tuple[str, ...]:
        """返回数据库读取键（主键 + 兼容别名）。"""

        primary = self.db_key or self.key
        return (primary, *self.aliases)


@dataclass(frozen=True)
class ToolPolicyContract:
    """工具治理配置契约。"""

    enabled_key: str = "tool_governance.enabled"
    fail_mode_key: str = "tool_governance.fail_mode"
    task_mode_key: str = "tool_governance.task_mode"
    requires_evidence_key: str = "tool_governance.requires_evidence"
    global_policy_key: str = "tool_governance.policy.global"

    @classmethod
    def agent_policy_key(cls, agent_name: str) -> str:
        """生成 Agent 级策略键。"""

        normalized = str(agent_name or "").strip().lower() or "default"
        return f"tool_governance.policy.agent.{normalized}"


TOOL_POLICY_CONTRACT = ToolPolicyContract()


CONFIG_SPECS: Dict[str, ConfigSpec] = {
    # ==================== 模型路由 ====================
    "model_routing.default_chat": ConfigSpec(
        key="model_routing.default_chat",
        source="db-dynamic",
        value_type="string",
        default="",
    ),
    "model_routing.lightweight": ConfigSpec(
        key="model_routing.lightweight",
        source="db-dynamic",
        value_type="string",
        default="qwen-plus",
        env_key="INTENT_CLASSIFIER_MODEL",
    ),
    "model_routing.sql_generation": ConfigSpec(
        key="model_routing.sql_generation",
        source="db-dynamic",
        value_type="string",
        default="qwen-plus",
        env_key="SQL_GENERATION_MODEL",
    ),
    "vision": ConfigSpec(
        key="vision",
        source="db-dynamic",
        value_type="string",
        default="",
        aliases=("model_routing.vision",),
    ),
    # ==================== 工具治理（P2） ====================
    TOOL_POLICY_CONTRACT.enabled_key: ConfigSpec(
        key=TOOL_POLICY_CONTRACT.enabled_key,
        source="db-dynamic",
        value_type="boolean",
        default=False,
        env_key="ENABLE_TOOL_GOVERNANCE",
        aliases=("feature.enable_tool_governance",),
    ),
    TOOL_POLICY_CONTRACT.fail_mode_key: ConfigSpec(
        key=TOOL_POLICY_CONTRACT.fail_mode_key,
        source="db-dynamic",
        value_type="string",
        default="compat",
        env_key="TOOL_POLICY_FAIL_MODE",
        aliases=("tool_policy.fail_mode",),
    ),
    TOOL_POLICY_CONTRACT.task_mode_key: ConfigSpec(
        key=TOOL_POLICY_CONTRACT.task_mode_key,
        source="db-dynamic",
        value_type="string",
        default="chat",
        env_key="TASK_MODE",
    ),
    TOOL_POLICY_CONTRACT.requires_evidence_key: ConfigSpec(
        key=TOOL_POLICY_CONTRACT.requires_evidence_key,
        source="db-dynamic",
        value_type="boolean",
        default=False,
        env_key="REQUIRES_EVIDENCE",
    ),
    TOOL_POLICY_CONTRACT.global_policy_key: ConfigSpec(
        key=TOOL_POLICY_CONTRACT.global_policy_key,
        source="db-dynamic",
        value_type="json",
        default={},
        env_key="TOOL_POLICY_GLOBAL_JSON",
    ),
    TOOL_POLICY_CONTRACT.agent_policy_key("common"): ConfigSpec(
        key=TOOL_POLICY_CONTRACT.agent_policy_key("common"),
        source="db-dynamic",
        value_type="json",
        default={},
        env_key="TOOL_POLICY_AGENT_COMMON_JSON",
    ),
    TOOL_POLICY_CONTRACT.agent_policy_key("supervisor"): ConfigSpec(
        key=TOOL_POLICY_CONTRACT.agent_policy_key("supervisor"),
        source="db-dynamic",
        value_type="json",
        default={},
        env_key="TOOL_POLICY_AGENT_SUPERVISOR_JSON",
    ),
    # ==================== 实验开关 ====================
    "feature.proxy_experiment_enabled": ConfigSpec(
        key="feature.proxy_experiment_enabled",
        source="db-dynamic",
        value_type="boolean",
        default=False,
        env_key="ENABLE_PROXY_EXPERIMENT",
    ),
    "feature.proxy_experiment_providers": ConfigSpec(
        key="feature.proxy_experiment_providers",
        source="db-dynamic",
        value_type="string",
        default="openai_proxy_trial",
        env_key="PROXY_EXPERIMENT_PROVIDERS",
    ),
    "feature.enable_ruleset_v2": ConfigSpec(
        key="feature.enable_ruleset_v2",
        source="db-dynamic",
        value_type="boolean",
        default=False,
        env_key="ENABLE_RULESET_V2",
        aliases=("feature.ruleset_v2_enabled",),
    ),
    "feature.enable_prompt_registry_v2": ConfigSpec(
        key="feature.enable_prompt_registry_v2",
        source="db-dynamic",
        value_type="boolean",
        default=False,
        env_key="ENABLE_PROMPT_REGISTRY_V2",
        aliases=("feature.prompt_registry_v2_enabled",),
    ),
    "release.ruleset_v2_rollout_percentage": ConfigSpec(
        key="release.ruleset_v2_rollout_percentage",
        source="db-dynamic",
        value_type="number",
        default=0,
        env_key="RULESET_V2_ROLLOUT_PERCENTAGE",
    ),
    "release.prompt_registry_v2_rollout_percentage": ConfigSpec(
        key="release.prompt_registry_v2_rollout_percentage",
        source="db-dynamic",
        value_type="number",
        default=0,
        env_key="PROMPT_REGISTRY_V2_ROLLOUT_PERCENTAGE",
    ),
    # ==================== 技能检索 ====================
    "skill_similarity_threshold": ConfigSpec(
        key="skill_similarity_threshold",
        source="db-dynamic",
        value_type="number",
        default=0.55,
        env_key="SKILL_SIMILARITY_THRESHOLD",
    ),
    "skill.retrieval_mode": ConfigSpec(
        key="skill.retrieval_mode",
        source="db-dynamic",
        value_type="string",
        default="hybrid",
    ),
    "skill.top_k": ConfigSpec(
        key="skill.top_k",
        source="db-dynamic",
        value_type="number",
        default=3,
    ),
    "skill.context_max_length": ConfigSpec(
        key="skill.context_max_length",
        source="db-dynamic",
        value_type="number",
        default=2400,
    ),
    "skill.section_max_count": ConfigSpec(
        key="skill.section_max_count",
        source="db-dynamic",
        value_type="number",
        default=2,
    ),
    "skill.hybrid.vector_weight": ConfigSpec(
        key="skill.hybrid.vector_weight",
        source="db-dynamic",
        value_type="number",
        default=0.65,
    ),
    "skill.hybrid.lexical_weight": ConfigSpec(
        key="skill.hybrid.lexical_weight",
        source="db-dynamic",
        value_type="number",
        default=0.25,
    ),
    "skill.hybrid.trigger_weight": ConfigSpec(
        key="skill.hybrid.trigger_weight",
        source="db-dynamic",
        value_type="number",
        default=0.10,
    ),
    "skill.hybrid.candidate_multiplier": ConfigSpec(
        key="skill.hybrid.candidate_multiplier",
        source="db-dynamic",
        value_type="number",
        default=3,
    ),
    "feature.enable_skill_versioning": ConfigSpec(
        key="feature.enable_skill_versioning",
        source="db-dynamic",
        value_type="boolean",
        default=False,
        env_key="ENABLE_SKILL_VERSIONING",
        aliases=("skill.enable_versioning",),
    ),
    "feature.enable_user_skill_binding": ConfigSpec(
        key="feature.enable_user_skill_binding",
        source="db-dynamic",
        value_type="boolean",
        default=False,
        env_key="ENABLE_USER_SKILL_BINDING",
        aliases=("skill.enable_user_binding",),
    ),
    "skill.runtime_source_mode": ConfigSpec(
        key="skill.runtime_source_mode",
        source="db-dynamic",
        value_type="string",
        default="compat",
        aliases=("skill.source_mode",),
    ),
    "skill.user_bootstrap_template": ConfigSpec(
        key="skill.user_bootstrap_template",
        source="db-dynamic",
        value_type="json",
        default={"default_version": "v1", "skills": []},
        aliases=("skill.bootstrap_template",),
    ),
    "memory.user_preference_bootstrap_template": ConfigSpec(
        key="memory.user_preference_bootstrap_template",
        source="db-dynamic",
        value_type="json",
        default={"assistant.persona": "小嘉"},
        env_key="USER_PREFERENCE_MEMORY_BOOTSTRAP_TEMPLATE",
        aliases=("memory.bootstrap_template",),
    ),
    "feature.enable_document_memory": ConfigSpec(
        key="feature.enable_document_memory",
        source="db-dynamic",
        value_type="boolean",
        default=False,
        env_key="ENABLE_DOCUMENT_MEMORY",
    ),
    "memory.document.admin.default_page_size": ConfigSpec(
        key="memory.document.admin.default_page_size",
        source="db-dynamic",
        value_type="number",
        default=20,
        env_key="DOCUMENT_MEMORY_ADMIN_DEFAULT_PAGE_SIZE",
    ),
    "memory.document.admin.max_page_size": ConfigSpec(
        key="memory.document.admin.max_page_size",
        source="db-dynamic",
        value_type="number",
        default=100,
        env_key="DOCUMENT_MEMORY_ADMIN_MAX_PAGE_SIZE",
    ),
    "memory.document.max_results": ConfigSpec(
        key="memory.document.max_results",
        source="db-dynamic",
        value_type="number",
        default=6,
        env_key="DOCUMENT_MEMORY_MAX_RESULTS",
    ),
    "memory.document.max_injected_chars": ConfigSpec(
        key="memory.document.max_injected_chars",
        source="db-dynamic",
        value_type="number",
        default=1200,
        env_key="DOCUMENT_MEMORY_MAX_INJECTED_CHARS",
    ),
    "memory.document.hybrid.vector_weight": ConfigSpec(
        key="memory.document.hybrid.vector_weight",
        source="db-dynamic",
        value_type="number",
        default=0.7,
        env_key="DOCUMENT_MEMORY_VECTOR_WEIGHT",
    ),
    "memory.document.hybrid.text_weight": ConfigSpec(
        key="memory.document.hybrid.text_weight",
        source="db-dynamic",
        value_type="number",
        default=0.3,
        env_key="DOCUMENT_MEMORY_TEXT_WEIGHT",
    ),
    "memory.document.hybrid.min_score": ConfigSpec(
        key="memory.document.hybrid.min_score",
        source="db-dynamic",
        value_type="number",
        default=0.05,
        env_key="DOCUMENT_MEMORY_HYBRID_MIN_SCORE",
    ),
    "memory.document.embedding.batch_size": ConfigSpec(
        key="memory.document.embedding.batch_size",
        source="db-dynamic",
        value_type="number",
        default=32,
        env_key="DOCUMENT_MEMORY_EMBEDDING_BATCH_SIZE",
    ),
    "memory.document.embedding.max_retry": ConfigSpec(
        key="memory.document.embedding.max_retry",
        source="db-dynamic",
        value_type="number",
        default=3,
        env_key="DOCUMENT_MEMORY_EMBEDDING_MAX_RETRY",
    ),
    # ==================== 问数权限配置（主键 askdata.*, 兼容 data_access.*） ====================
    "askdata.table_whitelist": ConfigSpec(
        key="askdata.table_whitelist",
        source="db-dynamic",
        value_type="string",
        default="",
        aliases=("data_access.table_whitelist",),
    ),
    "askdata.table_blacklist": ConfigSpec(
        key="askdata.table_blacklist",
        source="db-dynamic",
        value_type="string",
        default="t_user,t_chat_message,t_chat_feedback,t_chat_asset,t_todo,t_llm_model,t_agent_skills,t_system_config,t_metric_definitions",
        aliases=("data_access.table_blacklist",),
    ),
    "askdata.analytics_schema_allowlist": ConfigSpec(
        key="askdata.analytics_schema_allowlist",
        source="db-dynamic",
        value_type="string",
        default="fdmdata,sdmdata,public",
        aliases=("askdata.schema_whitelist", "data_access.schema_whitelist"),
    ),
    "askdata.system_schema_blacklist": ConfigSpec(
        key="askdata.system_schema_blacklist",
        source="db-dynamic",
        value_type="string",
        default="pg_catalog,information_schema",
        aliases=("askdata.schema_blacklist",),
    ),
}
