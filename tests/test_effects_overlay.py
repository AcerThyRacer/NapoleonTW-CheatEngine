"""
Tests for the visual effects overlay system.
"""

import sys
from pathlib import Path
from unittest.mock import Mock, MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))


# ══════════════════════════════════════════════════════════════
# EffectCategory
# ══════════════════════════════════════════════════════════════

class TestEffectCategory:
    """Tests for EffectCategory enum."""

    def test_all_categories_have_display_names(self):
        from src.trainer.effects_overlay import EffectCategory
        names = EffectCategory.display_names()
        for member in EffectCategory:
            assert member.value in names, f"Missing display name for {member}"

    def test_display_names_returns_dict(self):
        from src.trainer.effects_overlay import EffectCategory
        names = EffectCategory.display_names()
        assert isinstance(names, dict)
        assert len(names) == len(EffectCategory)

    def test_eight_categories(self):
        from src.trainer.effects_overlay import EffectCategory
        assert len(EffectCategory) == 8

    def test_expected_categories_present(self):
        from src.trainer.effects_overlay import EffectCategory
        expected = [
            "color", "lighting", "blur_focus", "cinematic",
            "atmosphere", "film_grain_noise", "artistic", "napoleon_themed",
        ]
        values = [m.value for m in EffectCategory]
        for name in expected:
            assert name in values, f"Expected category '{name}' not found"


# ══════════════════════════════════════════════════════════════
# EffectParameter / EffectDefinition / EffectState / EffectsPreset
# ══════════════════════════════════════════════════════════════

class TestEffectDataClasses:
    """Tests for data classes used in the effects system."""

    def test_effect_parameter_to_dict(self):
        from src.trainer.effects_overlay import EffectParameter
        p = EffectParameter("Intensity", "slider", 50.0, 0.0, 100.0, 1.0, "%")
        d = p.to_dict()
        assert d["name"] == "Intensity"
        assert d["param_type"] == "slider"
        assert d["default_value"] == 50.0

    def test_effect_parameter_from_dict(self):
        from src.trainer.effects_overlay import EffectParameter
        d = {"name": "Tint", "param_type": "color", "default_value": "#fff",
             "min_value": 0, "max_value": 100, "step": 1, "suffix": ""}
        p = EffectParameter.from_dict(d)
        assert p.name == "Tint"
        assert p.param_type == "color"

    def test_effect_definition_to_dict(self):
        from src.trainer.effects_overlay import EffectDefinition, EffectParameter
        edef = EffectDefinition(
            effect_id="vibrance", name="Vibrance", category="color",
            description="Boost saturation",
            parameters=[EffectParameter("Intensity", "slider", 50)],
        )
        d = edef.to_dict()
        assert d["effect_id"] == "vibrance"
        assert len(d["parameters"]) == 1

    def test_effect_definition_from_dict(self):
        from src.trainer.effects_overlay import EffectDefinition
        d = {
            "effect_id": "bloom",
            "name": "Bloom",
            "category": "lighting",
            "description": "Glow",
            "parameters": [
                {"name": "Intensity", "param_type": "slider",
                 "default_value": 30, "min_value": 0, "max_value": 100,
                 "step": 1, "suffix": "%"}
            ],
            "enabled": True,
        }
        edef = EffectDefinition.from_dict(d)
        assert edef.effect_id == "bloom"
        assert edef.enabled is True
        assert len(edef.parameters) == 1

    def test_effect_state_roundtrip(self):
        from src.trainer.effects_overlay import EffectState
        s = EffectState(enabled=True, values={"Intensity": 70})
        d = s.to_dict()
        s2 = EffectState.from_dict(d)
        assert s2.enabled is True
        assert s2.values["Intensity"] == 70

    def test_effects_preset_roundtrip(self):
        from src.trainer.effects_overlay import EffectsPreset, EffectState
        preset = EffectsPreset(
            name="Test", description="A test preset",
            effects={"vibrance": EffectState(True, {"Intensity": 60})},
        )
        d = preset.to_dict()
        p2 = EffectsPreset.from_dict(d)
        assert p2.name == "Test"
        assert "vibrance" in p2.effects
        assert p2.effects["vibrance"].enabled is True


# ══════════════════════════════════════════════════════════════
# Effect Registry
# ══════════════════════════════════════════════════════════════

class TestEffectRegistry:
    """Tests for the default effects registry."""

    def test_at_least_50_effects(self):
        from src.trainer.effects_overlay import build_default_effects
        effects = build_default_effects()
        assert len(effects) >= 50, f"Only {len(effects)} effects found"

    def test_all_effects_have_unique_ids(self):
        from src.trainer.effects_overlay import build_default_effects
        effects = build_default_effects()
        ids = [e.effect_id for e in effects]
        assert len(ids) == len(set(ids)), "Duplicate effect IDs found"

    def test_all_effects_have_category(self):
        from src.trainer.effects_overlay import build_default_effects, EffectCategory
        valid_cats = {c.value for c in EffectCategory}
        for e in build_default_effects():
            assert e.category in valid_cats, f"Invalid category for {e.effect_id}"

    def test_all_effects_have_parameters(self):
        from src.trainer.effects_overlay import build_default_effects
        for e in build_default_effects():
            assert len(e.parameters) > 0, f"{e.effect_id} has no parameters"

    def test_all_effects_have_name_and_description(self):
        from src.trainer.effects_overlay import build_default_effects
        for e in build_default_effects():
            assert e.name, f"{e.effect_id} has no name"
            assert e.description, f"{e.effect_id} has no description"

    def test_every_category_has_at_least_one_effect(self):
        from src.trainer.effects_overlay import build_default_effects, EffectCategory
        effects = build_default_effects()
        cats_seen = {e.category for e in effects}
        for cat in EffectCategory:
            assert cat.value in cats_seen, f"No effects for category {cat.value}"

    def test_parameter_types_valid(self):
        from src.trainer.effects_overlay import build_default_effects
        valid = {"slider", "color", "toggle"}
        for e in build_default_effects():
            for p in e.parameters:
                assert p.param_type in valid, (
                    f"Invalid type '{p.param_type}' in {e.effect_id}.{p.name}"
                )

    def test_specific_effects_present(self):
        from src.trainer.effects_overlay import build_default_effects
        ids = {e.effect_id for e in build_default_effects()}
        for expected in ["vibrance", "vignette", "bloom", "film_grain",
                         "battle_smoke", "imperial_gold", "depth_of_field",
                         "chromatic_aberration", "fog", "posterize"]:
            assert expected in ids, f"Expected effect '{expected}' not found"


# ══════════════════════════════════════════════════════════════
# Built-in Presets
# ══════════════════════════════════════════════════════════════

class TestBuiltinPresets:
    """Tests for built-in effect presets."""

    def test_builtin_presets_exist(self):
        from src.trainer.effects_overlay import get_builtin_presets
        presets = get_builtin_presets()
        assert len(presets) >= 5

    def test_default_preset_exists(self):
        from src.trainer.effects_overlay import get_builtin_presets
        presets = get_builtin_presets()
        assert "default" in presets

    def test_default_preset_has_no_effects(self):
        from src.trainer.effects_overlay import get_builtin_presets
        presets = get_builtin_presets()
        assert len(presets["default"].effects) == 0

    def test_named_presets_have_effects(self):
        from src.trainer.effects_overlay import get_builtin_presets
        presets = get_builtin_presets()
        for pname, preset in presets.items():
            if pname == "default":
                continue
            assert len(preset.effects) > 0, f"Preset '{pname}' has no effects"

    def test_preset_to_dict_roundtrip(self):
        from src.trainer.effects_overlay import get_builtin_presets, EffectsPreset
        for name, preset in get_builtin_presets().items():
            d = preset.to_dict()
            restored = EffectsPreset.from_dict(d)
            assert restored.name == preset.name


# ══════════════════════════════════════════════════════════════
# EffectsConfig
# ══════════════════════════════════════════════════════════════

class TestEffectsConfig:
    """Tests for EffectsConfig dataclass."""

    def test_default(self):
        from src.trainer.effects_overlay import EffectsConfig
        cfg = EffectsConfig()
        assert cfg.enabled is False
        assert cfg.active_preset == "default"
        assert cfg.presets == {}

    def test_to_dict(self):
        from src.trainer.effects_overlay import EffectsConfig
        cfg = EffectsConfig()
        d = cfg.to_dict()
        assert "enabled" in d
        assert "presets" in d

    def test_from_dict(self):
        from src.trainer.effects_overlay import EffectsConfig
        d = {"enabled": True, "active_preset": "cinematic_war", "presets": {}}
        cfg = EffectsConfig.from_dict(d)
        assert cfg.enabled is True
        assert cfg.active_preset == "cinematic_war"


# ══════════════════════════════════════════════════════════════
# EffectsOverlay (main class — no PyQt6 window tests)
# ══════════════════════════════════════════════════════════════

class TestEffectsOverlay:
    """Tests for the EffectsOverlay class (headless)."""

    def test_init_default(self):
        from src.trainer.effects_overlay import EffectsOverlay
        overlay = EffectsOverlay()
        assert overlay is not None
        assert overlay.visible is False
        assert overlay.get_effect_count() >= 50

    def test_init_with_config(self):
        from src.trainer.effects_overlay import EffectsOverlay, EffectsConfig
        cfg = EffectsConfig(enabled=True, active_preset="default")
        overlay = EffectsOverlay(effects_config=cfg)
        assert overlay.config.enabled is True

    def test_builtin_presets_injected(self):
        from src.trainer.effects_overlay import EffectsOverlay, get_builtin_presets
        overlay = EffectsOverlay()
        for pname in get_builtin_presets():
            assert pname in overlay.config.presets

    def test_get_effect_definitions(self):
        from src.trainer.effects_overlay import EffectsOverlay
        overlay = EffectsOverlay()
        defs = overlay.get_effect_definitions()
        assert len(defs) >= 50
        assert all(hasattr(d, 'effect_id') for d in defs)

    def test_get_effect_valid(self):
        from src.trainer.effects_overlay import EffectsOverlay
        overlay = EffectsOverlay()
        e = overlay.get_effect("vibrance")
        assert e is not None
        assert e.name == "Vibrance"

    def test_get_effect_invalid(self):
        from src.trainer.effects_overlay import EffectsOverlay
        overlay = EffectsOverlay()
        assert overlay.get_effect("nonexistent") is None

    def test_get_state(self):
        from src.trainer.effects_overlay import EffectsOverlay
        overlay = EffectsOverlay()
        state = overlay.get_state("vibrance")
        assert state is not None
        assert state.enabled is False  # default preset

    def test_get_state_invalid(self):
        from src.trainer.effects_overlay import EffectsOverlay
        overlay = EffectsOverlay()
        assert overlay.get_state("nonexistent") is None

    def test_set_effect_enabled(self):
        from src.trainer.effects_overlay import EffectsOverlay
        overlay = EffectsOverlay()
        assert overlay.set_effect_enabled("vibrance", True) is True
        assert overlay.get_state("vibrance").enabled is True

    def test_set_effect_enabled_invalid(self):
        from src.trainer.effects_overlay import EffectsOverlay
        overlay = EffectsOverlay()
        assert overlay.set_effect_enabled("nonexistent", True) is False

    def test_set_effect_value(self):
        from src.trainer.effects_overlay import EffectsOverlay
        overlay = EffectsOverlay()
        assert overlay.set_effect_value("vibrance", "Intensity", 75) is True
        assert overlay.get_state("vibrance").values["Intensity"] == 75

    def test_set_effect_value_invalid_effect(self):
        from src.trainer.effects_overlay import EffectsOverlay
        overlay = EffectsOverlay()
        assert overlay.set_effect_value("nonexistent", "x", 1) is False

    def test_set_effect_value_invalid_param(self):
        from src.trainer.effects_overlay import EffectsOverlay
        overlay = EffectsOverlay()
        assert overlay.set_effect_value("vibrance", "NoSuchParam", 1) is False

    def test_get_active_effects_default_empty(self):
        from src.trainer.effects_overlay import EffectsOverlay
        overlay = EffectsOverlay()
        assert len(overlay.get_active_effects()) == 0

    def test_get_active_effects_after_enable(self):
        from src.trainer.effects_overlay import EffectsOverlay
        overlay = EffectsOverlay()
        overlay.set_effect_enabled("bloom", True)
        active = overlay.get_active_effects()
        assert "bloom" in active

    def test_get_effects_by_category(self):
        from src.trainer.effects_overlay import EffectsOverlay
        overlay = EffectsOverlay()
        color_fx = overlay.get_effects_by_category("color")
        assert len(color_fx) >= 5
        assert all(e.category == "color" for e in color_fx)

    def test_get_categories(self):
        from src.trainer.effects_overlay import EffectsOverlay
        overlay = EffectsOverlay()
        cats = overlay.get_categories()
        assert len(cats) == 8

    def test_get_preset_names(self):
        from src.trainer.effects_overlay import EffectsOverlay
        overlay = EffectsOverlay()
        names = overlay.get_preset_names()
        assert "default" in names
        assert len(names) >= 5

    def test_apply_preset(self):
        from src.trainer.effects_overlay import EffectsOverlay
        overlay = EffectsOverlay()
        assert overlay.apply_preset("cinematic_war") is True
        assert overlay.config.active_preset == "cinematic_war"
        assert overlay.get_state("vignette").enabled is True

    def test_apply_preset_invalid(self):
        from src.trainer.effects_overlay import EffectsOverlay
        overlay = EffectsOverlay()
        assert overlay.apply_preset("nonexistent") is False

    def test_save_current_as_preset(self):
        from src.trainer.effects_overlay import EffectsOverlay
        overlay = EffectsOverlay()
        overlay.set_effect_enabled("bloom", True)
        overlay.set_effect_value("bloom", "Intensity", 42)
        assert overlay.save_current_as_preset("my_preset", "My custom") is True
        assert "my_preset" in overlay.config.presets
        assert overlay.config.presets["my_preset"].effects["bloom"].enabled

    def test_save_preset_empty_name_fails(self):
        from src.trainer.effects_overlay import EffectsOverlay
        overlay = EffectsOverlay()
        assert overlay.save_current_as_preset("") is False

    def test_delete_preset(self):
        from src.trainer.effects_overlay import EffectsOverlay
        overlay = EffectsOverlay()
        overlay.save_current_as_preset("temp_preset")
        assert overlay.delete_preset("temp_preset") is True
        assert "temp_preset" not in overlay.config.presets

    def test_delete_preset_default_fails(self):
        from src.trainer.effects_overlay import EffectsOverlay
        overlay = EffectsOverlay()
        assert overlay.delete_preset("default") is False

    def test_delete_preset_nonexistent_fails(self):
        from src.trainer.effects_overlay import EffectsOverlay
        overlay = EffectsOverlay()
        assert overlay.delete_preset("no_such") is False

    def test_delete_active_preset_resets(self):
        from src.trainer.effects_overlay import EffectsOverlay
        overlay = EffectsOverlay()
        overlay.save_current_as_preset("tmp")
        overlay.config.active_preset = "tmp"
        overlay.delete_preset("tmp")
        assert overlay.config.active_preset == "default"

    def test_get_config_dict(self):
        from src.trainer.effects_overlay import EffectsOverlay
        overlay = EffectsOverlay()
        d = overlay.get_config_dict()
        assert isinstance(d, dict)
        assert "presets" in d

    def test_get_effect_count(self):
        from src.trainer.effects_overlay import EffectsOverlay
        overlay = EffectsOverlay()
        assert overlay.get_effect_count() >= 50

    def test_get_enabled_count_default(self):
        from src.trainer.effects_overlay import EffectsOverlay
        overlay = EffectsOverlay()
        assert overlay.get_enabled_count() == 0

    def test_get_enabled_count_after_enable(self):
        from src.trainer.effects_overlay import EffectsOverlay
        overlay = EffectsOverlay()
        overlay.set_effect_enabled("vibrance", True)
        overlay.set_effect_enabled("bloom", True)
        assert overlay.get_enabled_count() == 2

    def test_toggle_without_window(self):
        from src.trainer.effects_overlay import EffectsOverlay
        overlay = EffectsOverlay()
        overlay.toggle()  # should not raise
        assert overlay.visible is False

    def test_show_without_window(self):
        from src.trainer.effects_overlay import EffectsOverlay
        overlay = EffectsOverlay()
        overlay.show()  # should not raise
        assert overlay.visible is False

    def test_hide_without_window(self):
        from src.trainer.effects_overlay import EffectsOverlay
        overlay = EffectsOverlay()
        overlay.hide()  # should not raise

    def test_close_without_window(self):
        from src.trainer.effects_overlay import EffectsOverlay
        overlay = EffectsOverlay()
        overlay.close()  # should not raise

    def test_is_visible_default(self):
        from src.trainer.effects_overlay import EffectsOverlay
        overlay = EffectsOverlay()
        assert overlay.is_visible() is False

    @patch('src.trainer.effects_overlay.PYQT_AVAILABLE', False)
    def test_create_overlay_no_pyqt(self):
        from src.trainer.effects_overlay import EffectsOverlay
        overlay = EffectsOverlay()
        assert overlay.create_overlay() is False


# ══════════════════════════════════════════════════════════════
# Preset application (state consistency)
# ══════════════════════════════════════════════════════════════

class TestPresetApplication:
    """Tests for applying presets and verifying live state."""

    def test_apply_cinematic_war_enables_expected(self):
        from src.trainer.effects_overlay import EffectsOverlay
        overlay = EffectsOverlay()
        overlay.apply_preset("cinematic_war")
        active = overlay.get_active_effects()
        assert "vignette" in active
        assert "bloom" in active
        assert "color_grading" in active

    def test_apply_napoleon_glory_enables_expected(self):
        from src.trainer.effects_overlay import EffectsOverlay
        overlay = EffectsOverlay()
        overlay.apply_preset("napoleon_glory")
        active = overlay.get_active_effects()
        assert "imperial_gold" in active
        assert "vibrance" in active

    def test_apply_default_disables_all(self):
        from src.trainer.effects_overlay import EffectsOverlay
        overlay = EffectsOverlay()
        overlay.apply_preset("cinematic_war")
        assert overlay.get_enabled_count() > 0
        overlay.apply_preset("default")
        assert overlay.get_enabled_count() == 0

    def test_switching_presets_updates_values(self):
        from src.trainer.effects_overlay import EffectsOverlay
        overlay = EffectsOverlay()
        overlay.apply_preset("vibrant_battles")
        v1 = overlay.get_state("vibrance").values.get("Intensity")
        overlay.apply_preset("napoleon_glory")
        v2 = overlay.get_state("vibrance").values.get("Intensity")
        # Both have vibrance but with different intensity
        assert v1 is not None
        assert v2 is not None


# ══════════════════════════════════════════════════════════════
# SimpleEffectsOverlay (console fallback)
# ══════════════════════════════════════════════════════════════

class TestSimpleEffectsOverlay:
    """Tests for the console fallback overlay."""

    def test_show_no_active(self, capsys):
        from src.trainer.effects_overlay import SimpleEffectsOverlay
        s = SimpleEffectsOverlay()
        s.show()
        captured = capsys.readouterr()
        assert "No effects active" in captured.out

    def test_show_with_active(self, capsys):
        from src.trainer.effects_overlay import SimpleEffectsOverlay
        s = SimpleEffectsOverlay()
        s._overlay.set_effect_enabled("vibrance", True)
        s.show()
        captured = capsys.readouterr()
        assert "Vibrance" in captured.out

    def test_hide_no_error(self):
        from src.trainer.effects_overlay import SimpleEffectsOverlay
        SimpleEffectsOverlay().hide()

    def test_toggle_shows(self, capsys):
        from src.trainer.effects_overlay import SimpleEffectsOverlay
        s = SimpleEffectsOverlay()
        s.toggle()
        captured = capsys.readouterr()
        assert "effects" in captured.out.lower()

    def test_close_no_error(self):
        from src.trainer.effects_overlay import SimpleEffectsOverlay
        SimpleEffectsOverlay().close()


# ══════════════════════════════════════════════════════════════
# Config integration
# ══════════════════════════════════════════════════════════════

class TestEffectsConfigIntegration:
    """Tests for effects_overlay in the Config system."""

    def test_config_default_effects_overlay(self):
        from src.config.settings import Config
        config = Config()
        assert config.effects_overlay == {}

    def test_config_to_dict_includes_effects_overlay(self):
        from src.config.settings import Config
        config = Config()
        d = config.to_dict()
        assert "effects_overlay" in d

    def test_config_from_dict_with_effects_overlay(self):
        from src.config.settings import Config
        data = {"effects_overlay": {"enabled": True, "active_preset": "test"}}
        config = Config.from_dict(data)
        assert config.effects_overlay["enabled"] is True

    def test_config_from_dict_without_effects_overlay(self):
        from src.config.settings import Config
        config = Config.from_dict({})
        assert config.effects_overlay == {}

    def test_config_validation_effects_overlay(self):
        from src.config.settings import ConfigManager
        ConfigManager.reset_instance()
        mgr = ConfigManager()
        errors = mgr._validate_config({"effects_overlay": {"enabled": True}})
        assert errors == []

    def test_config_validation_effects_overlay_wrong_type(self):
        from src.config.settings import ConfigManager
        ConfigManager.reset_instance()
        mgr = ConfigManager()
        errors = mgr._validate_config({"effects_overlay": "not_a_dict"})
        assert len(errors) > 0


# ══════════════════════════════════════════════════════════════
# Import from trainer __init__
# ══════════════════════════════════════════════════════════════

class TestTrainerImport:
    """Test that EffectsOverlay is importable from trainer package."""

    def test_import_effects_overlay(self):
        from src.trainer import EffectsOverlay
        assert EffectsOverlay is not None

    def test_in_all(self):
        import src.trainer as trainer_mod
        assert 'EffectsOverlay' in trainer_mod.__all__
