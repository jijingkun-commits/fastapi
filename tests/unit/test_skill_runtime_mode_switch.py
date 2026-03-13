"""Skill runtime mode switch 专项测试。"""

from app.core.config_contract import CONFIG_SPECS
from app.services.config_resolver import ConfigResolver
from app.services.skill_service import SkillService


def test_config_contract_contains_progressive_runtime_keys() -> None:
    """配置契约应暴露 progressive loader 所需的主开关与 trace 开关。"""

    assert CONFIG_SPECS["feature.enable_progressive_skill_loading"].default is True
    assert CONFIG_SPECS["skill.runtime_mode"].default == "catalog_tool"
    assert CONFIG_SPECS["feature.enable_skill_runtime_trace"].default is True
    assert CONFIG_SPECS["feature.enable_skill_catalog_metadata_normalization"].default is True


def test_resolve_runtime_mode_returns_hybrid_when_progressive_flag_disabled(monkeypatch) -> None:
    """关闭 progressive flag 时必须统一回到 hybrid_rag。"""

    monkeypatch.setattr(
        SkillService,
        "_is_progressive_skill_loading_enabled",
        classmethod(lambda cls: False),
    )

    assert SkillService.resolve_runtime_mode() == SkillService.SKILL_RUNTIME_MODE_HYBRID


def test_resolve_runtime_mode_maps_catalog_tool_to_progressive(monkeypatch) -> None:
    """catalog_tool 配置值应归一到 canonical progressive_loader。"""

    monkeypatch.setattr(
        SkillService,
        "_is_progressive_skill_loading_enabled",
        classmethod(lambda cls: True),
    )
    monkeypatch.setattr(
        ConfigResolver,
        "get_string",
        classmethod(lambda cls, key, default="": "catalog_tool"),
    )

    assert SkillService.resolve_runtime_mode() == SkillService.SKILL_RUNTIME_MODE_PROGRESSIVE


def test_resolve_runtime_mode_accepts_explicit_hybrid(monkeypatch) -> None:
    """显式配置 hybrid_rag 时应保持 hybrid 路径，不混淆为 progressive。"""

    monkeypatch.setattr(
        SkillService,
        "_is_progressive_skill_loading_enabled",
        classmethod(lambda cls: True),
    )
    monkeypatch.setattr(
        ConfigResolver,
        "get_string",
        classmethod(lambda cls, key, default="": "hybrid_rag"),
    )

    assert SkillService.resolve_runtime_mode() == SkillService.SKILL_RUNTIME_MODE_HYBRID
