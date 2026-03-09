"""
Tests for trainer cheats and hotkey manager.
"""

import os
import sys
from pathlib import Path
from unittest.mock import Mock, MagicMock, patch, PropertyMock

import pytest
import psutil

# Patch psutil._common.pmmap if missing (some psutil versions lack it)
if not hasattr(psutil._common, 'pmmap'):
    psutil._common.pmmap = type('pmmap', (), {})

# Ensure src is importable
sys.path.insert(0, str(Path(__file__).parent.parent))


class TestTrainerCheats:
    """Tests for trainer cheat system."""

    def test_init(self):
        from src.memory import ProcessManager, MemoryScanner, CheatManager
        from src.trainer import TrainerCheats
        pm = ProcessManager()
        scanner = MemoryScanner(pm)
        cheat_manager = CheatManager(scanner)
        trainer = TrainerCheats(cheat_manager)
        assert trainer is not None
        assert len(trainer.cheat_status) > 0

    def test_get_summary(self):
        from src.memory import ProcessManager, MemoryScanner, CheatManager
        from src.trainer import TrainerCheats
        pm = ProcessManager()
        scanner = MemoryScanner(pm)
        cheat_manager = CheatManager(scanner)
        trainer = TrainerCheats(cheat_manager)
        summary = trainer.get_summary()
        assert isinstance(summary, str)
        assert len(summary) > 0

    def test_get_all_cheat_statuses(self):
        from src.memory import ProcessManager, MemoryScanner, CheatManager
        from src.trainer import TrainerCheats
        pm = ProcessManager()
        scanner = MemoryScanner(pm)
        cheat_manager = CheatManager(scanner)
        trainer = TrainerCheats(cheat_manager)
        statuses = trainer.get_all_cheat_statuses()
        assert isinstance(statuses, dict)
        assert all(isinstance(v, bool) for v in statuses.values())


class TestHotkeyManager:
    """Tests for the hotkey manager."""

    def test_init(self):
        from src.trainer.hotkeys import HotkeyManager
        hm = HotkeyManager()
        assert hm is not None
        assert hm.bindings == {}

    @patch('src.trainer.hotkeys.PYNPUT_AVAILABLE', True)
    def test_register_hotkey_with_pynput(self):
        from src.trainer.hotkeys import HotkeyManager
        hm = HotkeyManager()
        callback = Mock()
        result = hm.register_hotkey('f1', callback, 'Test hotkey')
        assert result is True
        assert len(hm.bindings) == 1

    @patch('src.trainer.hotkeys.PYNPUT_AVAILABLE', True)
    def test_unregister_hotkey(self):
        from src.trainer.hotkeys import HotkeyManager
        hm = HotkeyManager()
        callback = Mock()
        hm.register_hotkey('f1', callback, 'Test hotkey')
        binding_id = list(hm.bindings.keys())[0]
        result = hm.unregister_hotkey(binding_id)
        assert result is True
        assert len(hm.bindings) == 0

    @patch('src.trainer.hotkeys.PYNPUT_AVAILABLE', True)
    def test_get_registered_hotkeys(self):
        from src.trainer.hotkeys import HotkeyManager
        hm = HotkeyManager()
        callback = Mock()
        hm.register_hotkey('f2', callback, 'Another hotkey')
        hotkeys = hm.get_registered_hotkeys()
        assert len(hotkeys) == 1
        assert hotkeys[0]['key'] == 'f2'

    def test_register_without_pynput_returns_false(self):
        """Verify graceful failure when pynput is missing."""
        from src.trainer.hotkeys import HotkeyManager, PYNPUT_AVAILABLE
        if PYNPUT_AVAILABLE:
            pytest.skip("pynput is installed")
        hm = HotkeyManager()
        result = hm.register_hotkey('f1', Mock(), 'Test')
        assert result is False


# ══════════════════════════════════════════════════════════════
# Overlay Animation Tests
# ══════════════════════════════════════════════════════════════

class TestOverlayAnimationStyle:
    """Tests for OverlayAnimationStyle enum."""

    def test_all_styles_have_display_names(self):
        from src.trainer.overlay import OverlayAnimationStyle
        names = OverlayAnimationStyle.display_names()
        for member in OverlayAnimationStyle:
            assert member.value in names, f"Missing display name for {member}"

    def test_display_names_returns_dict(self):
        from src.trainer.overlay import OverlayAnimationStyle
        names = OverlayAnimationStyle.display_names()
        assert isinstance(names, dict)
        assert len(names) == len(OverlayAnimationStyle)

    def test_from_value_valid(self):
        from src.trainer.overlay import OverlayAnimationStyle
        style = OverlayAnimationStyle.from_value("imperial_march")
        assert style == OverlayAnimationStyle.IMPERIAL_MARCH

    def test_from_value_invalid_returns_none(self):
        from src.trainer.overlay import OverlayAnimationStyle
        style = OverlayAnimationStyle.from_value("nonexistent_animation")
        assert style == OverlayAnimationStyle.NONE

    def test_from_value_each_member(self):
        from src.trainer.overlay import OverlayAnimationStyle
        for member in OverlayAnimationStyle:
            assert OverlayAnimationStyle.from_value(member.value) == member

    def test_style_count_at_least_twelve(self):
        """Ensure many animation styles are available."""
        from src.trainer.overlay import OverlayAnimationStyle
        assert len(OverlayAnimationStyle) == 17

    def test_expected_styles_present(self):
        from src.trainer.overlay import OverlayAnimationStyle
        expected = [
            "none", "imperial_march", "cannon_fire", "eagle_standard",
            "smoke_screen", "battle_formation", "cavalry_charge",
            "naval_broadside", "vive_empereur", "artillery_barrage",
            "grapeshot", "old_guard", "russian_winter",
            "lightning_strike", "flag_wave", "cannonball_trail", "morale_boost",
        ]
        values = [m.value for m in OverlayAnimationStyle]
        for name in expected:
            assert name in values, f"Expected style '{name}' not found"

    def test_overlay_presets_resolve_to_valid_animations(self):
        from src.trainer.overlay import OverlayAnimationStyle
        presets = OverlayAnimationStyle.preset_definitions()
        names = OverlayAnimationStyle.display_names()
        assert "balanced_command" in presets
        for preset in presets.values():
            assert preset["animation"] in names


class TestOverlayAnimationManager:
    """Tests for OverlayAnimationManager."""

    def test_init_default_style(self):
        from src.trainer.overlay import OverlayAnimationManager, OverlayAnimationStyle
        mgr = OverlayAnimationManager()
        assert mgr.animation_style == OverlayAnimationStyle.SMOKE_SCREEN

    def test_init_custom_style(self):
        from src.trainer.overlay import OverlayAnimationManager, OverlayAnimationStyle
        mgr = OverlayAnimationManager(OverlayAnimationStyle.CANNON_FIRE)
        assert mgr.animation_style == OverlayAnimationStyle.CANNON_FIRE

    def test_set_animation_style(self):
        from src.trainer.overlay import OverlayAnimationManager, OverlayAnimationStyle
        mgr = OverlayAnimationManager()
        mgr.animation_style = OverlayAnimationStyle.EAGLE_STANDARD
        assert mgr.animation_style == OverlayAnimationStyle.EAGLE_STANDARD

    def test_get_handler_returns_callable(self):
        from src.trainer.overlay import OverlayAnimationManager, OverlayAnimationStyle
        for style in OverlayAnimationStyle:
            if style == OverlayAnimationStyle.NONE:
                continue
            mgr = OverlayAnimationManager(style)
            handler_open = mgr._get_handler(opening=True)
            handler_close = mgr._get_handler(opening=False)
            assert callable(handler_open), f"Open handler not callable for {style}"
            assert callable(handler_close), f"Close handler not callable for {style}"

    def test_animate_open_none_style_shows_widget(self):
        from src.trainer.overlay import OverlayAnimationManager, OverlayAnimationStyle
        mgr = OverlayAnimationManager(OverlayAnimationStyle.NONE)
        widget = MagicMock()
        from unittest.mock import ANY
        target = MagicMock()
        mgr.animate_open(widget, target)
        widget.setGeometry.assert_called_once_with(target)
        widget.show.assert_called_once()

    def test_animate_close_none_style_hides_widget(self):
        from src.trainer.overlay import OverlayAnimationManager, OverlayAnimationStyle
        mgr = OverlayAnimationManager(OverlayAnimationStyle.NONE)
        widget = MagicMock()
        callback = Mock()
        mgr.animate_close(widget, callback)
        widget.hide.assert_called_once()
        callback.assert_called_once()

    def test_animate_close_none_style_no_callback(self):
        from src.trainer.overlay import OverlayAnimationManager, OverlayAnimationStyle
        mgr = OverlayAnimationManager(OverlayAnimationStyle.NONE)
        widget = MagicMock()
        mgr.animate_close(widget)
        widget.hide.assert_called_once()

    def test_stop_active_when_no_group(self):
        from src.trainer.overlay import OverlayAnimationManager
        mgr = OverlayAnimationManager()
        mgr._stop_active()  # should not raise

    def test_stop_active_stops_group(self):
        from src.trainer.overlay import OverlayAnimationManager
        mgr = OverlayAnimationManager()
        mock_group = MagicMock()
        mgr._active_group = mock_group
        mgr._stop_active()
        mock_group.stop.assert_called_once()
        assert mgr._active_group is None


class TestCheatOverlayAnimationIntegration:
    """Tests for CheatOverlay animation integration (no PyQt6 window)."""

    def test_init_default_animation(self):
        from src.trainer.overlay import CheatOverlay
        overlay = CheatOverlay()
        assert overlay.animation_style == "smoke_screen"

    def test_init_custom_animation(self):
        from src.trainer.overlay import CheatOverlay
        overlay = CheatOverlay(animation_style="imperial_march")
        assert overlay.animation_style == "imperial_march"

    def test_set_animation_style(self):
        from src.trainer.overlay import CheatOverlay
        overlay = CheatOverlay()
        overlay.animation_style = "cannon_fire"
        assert overlay.animation_style == "cannon_fire"

    def test_get_available_animations(self):
        from src.trainer.overlay import CheatOverlay
        overlay = CheatOverlay()
        anims = overlay.get_available_animations()
        assert isinstance(anims, dict)
        assert len(anims) >= 12
        assert "none" in anims
        assert "imperial_march" in anims

    def test_get_available_presets(self):
        from src.trainer.overlay import CheatOverlay
        overlay = CheatOverlay()
        presets = overlay.get_available_presets()
        assert isinstance(presets, dict)
        assert "balanced_command" in presets
        assert "winter_campaign" in presets

    @patch('src.trainer.overlay.PYQT_AVAILABLE', False)
    def test_create_overlay_no_pyqt(self):
        from src.trainer.overlay import CheatOverlay
        overlay = CheatOverlay()
        assert overlay.create_overlay() is False

    def test_toggle_without_window(self):
        from src.trainer.overlay import CheatOverlay
        overlay = CheatOverlay()
        overlay.toggle()  # should not raise; no window so still not visible
        assert overlay.visible is False

    def test_close_without_window(self):
        from src.trainer.overlay import CheatOverlay
        overlay = CheatOverlay()
        overlay.close()  # should not raise

    def test_is_visible_default(self):
        from src.trainer.overlay import CheatOverlay
        overlay = CheatOverlay()
        assert overlay.is_visible() is False

    def test_update_cheats_without_window(self):
        from src.trainer.overlay import CheatOverlay
        overlay = CheatOverlay()
        overlay.update_cheats(["Gold", "God Mode"])  # should not raise


class TestOverlayAnimationConfig:
    """Tests for overlay animation in the config system."""

    def test_config_default_overlay_animation(self):
        from src.config.settings import Config
        config = Config()
        assert config.overlay_animation == "smoke_screen"

    def test_config_to_dict_includes_overlay_animation(self):
        from src.config.settings import Config
        config = Config()
        d = config.to_dict()
        assert "overlay_animation" in d
        assert d["overlay_animation"] == "smoke_screen"

    def test_config_from_dict_with_overlay_animation(self):
        from src.config.settings import Config
        data = {
            "overlay_animation": "cavalry_charge",
            "overlay_preset": "shock_assault",
            "setup_completed": True,
        }
        config = Config.from_dict(data)
        assert config.overlay_animation == "cavalry_charge"
        assert config.overlay_preset == "shock_assault"
        assert config.setup_completed is True

    def test_config_from_dict_without_overlay_animation(self):
        from src.config.settings import Config
        config = Config.from_dict({})
        assert config.overlay_animation == "smoke_screen"

    def test_config_validation_overlay_animation(self):
        from src.config.settings import ConfigManager
        ConfigManager.reset_instance()
        mgr = ConfigManager()
        errors = mgr._validate_config({"overlay_animation": "imperial_march"})
        assert errors == []

    def test_config_validation_overlay_animation_wrong_type(self):
        from src.config.settings import ConfigManager
        ConfigManager.reset_instance()
        mgr = ConfigManager()
        errors = mgr._validate_config({"overlay_animation": 123})
        assert len(errors) > 0
