import pytest

from bot.plugins.ark_se.plugin import ARK_SE_PLUGIN
from bot.plugins.registry import PluginRegistry


def test_ark_plugin_contains_required_specializations_and_safety_rules() -> None:
    labels = ARK_SE_PLUGIN.specialization_labels()

    assert ARK_SE_PLUGIN.key == "ark_se"
    assert "pvp" in labels
    assert "base_building" in labels
    assert any("координаты" in rule.lower() for rule in ARK_SE_PLUGIN.safety_rules)


def test_plugin_validation_normalizes_and_rejects_unknown_values() -> None:
    assert ARK_SE_PLUGIN.validate_specializations(["PVP", " taming "]) == ["pvp", "taming"]

    with pytest.raises(ValueError):
        ARK_SE_PLUGIN.validate_specializations(["unknown"])


def test_registry_returns_registered_plugin() -> None:
    registry = PluginRegistry()
    registry.register(ARK_SE_PLUGIN)

    assert registry.get("ark_se") is ARK_SE_PLUGIN
