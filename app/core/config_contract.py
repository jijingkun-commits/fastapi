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
