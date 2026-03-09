"""
Tests for the visual overhaul: new overlay animations, animated components,
napoleon panel modernization, SVG icon assets, and sound integration.
"""

import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))


# ── Overlay animation tests ──────────────────────────────────────────


class TestNewOverlayAnimations:
    """Tests for the 4 new overlay animation styles."""

    def test_lightning_strike_enum_exists(self):
        from src.trainer.overlay import OverlayAnimationStyle
        assert hasattr(OverlayAnimationStyle, 'LIGHTNING_STRIKE')
        assert OverlayAnimationStyle.LIGHTNING_STRIKE.value == "lightning_strike"

    def test_flag_wave_enum_exists(self):
        from src.trainer.overlay import OverlayAnimationStyle
        assert hasattr(OverlayAnimationStyle, 'FLAG_WAVE')
        assert OverlayAnimationStyle.FLAG_WAVE.value == "flag_wave"

    def test_cannonball_trail_enum_exists(self):
        from src.trainer.overlay import OverlayAnimationStyle
        assert hasattr(OverlayAnimationStyle, 'CANNONBALL_TRAIL')
        assert OverlayAnimationStyle.CANNONBALL_TRAIL.value == "cannonball_trail"

    def test_morale_boost_enum_exists(self):
        from src.trainer.overlay import OverlayAnimationStyle
        assert hasattr(OverlayAnimationStyle, 'MORALE_BOOST')
        assert OverlayAnimationStyle.MORALE_BOOST.value == "morale_boost"

    def test_new_styles_have_display_names(self):
        from src.trainer.overlay import OverlayAnimationStyle
        names = OverlayAnimationStyle.display_names()
        for value in ("lightning_strike", "flag_wave", "cannonball_trail", "morale_boost"):
            assert value in names, f"Missing display name for {value}"

    def test_from_value_new_styles(self):
        from src.trainer.overlay import OverlayAnimationStyle
        for value in ("lightning_strike", "flag_wave", "cannonball_trail", "morale_boost"):
            style = OverlayAnimationStyle.from_value(value)
            assert style.value == value

    def test_new_styles_have_handlers(self):
        from src.trainer.overlay import OverlayAnimationManager, OverlayAnimationStyle
        for style in (
            OverlayAnimationStyle.LIGHTNING_STRIKE,
            OverlayAnimationStyle.FLAG_WAVE,
            OverlayAnimationStyle.CANNONBALL_TRAIL,
            OverlayAnimationStyle.MORALE_BOOST,
        ):
            mgr = OverlayAnimationManager(style)
            assert callable(mgr._get_handler(opening=True))
            assert callable(mgr._get_handler(opening=False))

    def test_animate_open_none_for_new_styles(self):
        """Ensure NONE style still works with manager set to new style then reset."""
        from src.trainer.overlay import OverlayAnimationManager, OverlayAnimationStyle
        mgr = OverlayAnimationManager(OverlayAnimationStyle.LIGHTNING_STRIKE)
        mgr.animation_style = OverlayAnimationStyle.NONE
        widget = MagicMock()
        rect = MagicMock()
        mgr.animate_open(widget, rect)
        widget.setGeometry.assert_called_with(rect)
        widget.show.assert_called_once()

    def test_cheat_overlay_accepts_new_styles(self):
        from src.trainer.overlay import CheatOverlay
        for style_val in ("lightning_strike", "flag_wave", "cannonball_trail", "morale_boost"):
            overlay = CheatOverlay(animation_style=style_val)
            assert overlay.animation_style == style_val

    def test_total_animation_count_is_17(self):
        from src.trainer.overlay import OverlayAnimationStyle
        assert len(OverlayAnimationStyle) == 17


# ── SVG icon assets ──────────────────────────────────────────────────


class TestSVGIcons:
    """Tests for Napoleon-era SVG icon assets."""

    ICONS_DIR = Path(__file__).parent.parent / "assets" / "icons"

    EXPECTED_ICONS = [
        "eagle.svg", "cannon.svg", "crown.svg", "shield.svg",
        "treasury.svg", "sword.svg", "campaign.svg", "diplomacy.svg",
        "quality.svg", "flag.svg", "lightning.svg", "morale.svg",
        "search.svg", "settings.svg",
    ]

    def test_icons_directory_exists(self):
        assert self.ICONS_DIR.is_dir()

    @pytest.mark.parametrize("icon_name", EXPECTED_ICONS)
    def test_icon_exists(self, icon_name):
        path = self.ICONS_DIR / icon_name
        assert path.exists(), f"Missing icon: {icon_name}"

    @pytest.mark.parametrize("icon_name", EXPECTED_ICONS)
    def test_icon_is_valid_svg(self, icon_name):
        path = self.ICONS_DIR / icon_name
        content = path.read_text()
        assert "<svg" in content.lower()
        assert "</svg>" in content.lower()


# ── Sound assets ─────────────────────────────────────────────────────


class TestSoundAssets:
    """Tests for the sounds asset directory."""

    SOUNDS_DIR = Path(__file__).parent.parent / "assets" / "sounds"

    def test_sounds_directory_exists(self):
        assert self.SOUNDS_DIR.is_dir()

    def test_readme_exists(self):
        readme = self.SOUNDS_DIR / "README.md"
        assert readme.exists()


# ── Napoleon panel helpers ───────────────────────────────────────────


class TestNapoleonPanelImports:
    """Tests for importable symbols from napoleon_panel module.

    The module defines GUI classes that inherit from PyQt6 widgets, so it
    can only be fully imported when PyQt6 is available.  We use AST
    inspection as a portable fallback.
    """

    def _module_source(self) -> str:
        path = Path(__file__).parent.parent / "src" / "gui" / "napoleon_panel.py"
        return path.read_text()

    def test_category_icon_map_defined(self):
        source = self._module_source()
        assert "CATEGORY_ICON_MAP" in source

    def test_category_icon_map_has_all_categories(self):
        source = self._module_source()
        for cat in ("treasury", "military", "campaign", "battle", "diplomacy", "quality"):
            assert cat in source

    def test_assets_dir_constant_defined(self):
        source = self._module_source()
        assert "ASSETS_DIR" in source
        assert "ICONS_DIR" in source

    def test_cheat_category_quality_of_life(self):
        import ast
        source = self._module_source()
        tree = ast.parse(source)
        class_names = [n.name for n in ast.walk(tree) if isinstance(n, ast.ClassDef)]
        assert "CheatCategory" in class_names

    def test_search_input_present(self):
        """The module should contain a search bar widget."""
        source = self._module_source()
        assert "search_input" in source or "_search_input" in source

    def test_live_stats_dashboard_referenced(self):
        source = self._module_source()
        assert "LiveStatsDashboard" in source

    def test_parallax_battle_scene_referenced(self):
        source = self._module_source()
        assert "ParallaxBattleScene" in source

    def test_cannon_smoke_referenced(self):
        source = self._module_source()
        assert "CannonSmokeSystem" in source

    def test_sound_effect_player_referenced(self):
        source = self._module_source()
        assert "SoundEffectPlayer" in source

    def test_icon_only_buttons(self):
        """Category navigation should use QToolButton for icon-only style."""
        source = self._module_source()
        assert "QToolButton" in source

    def test_search_filter_method(self):
        """A search-changed handler should be present."""
        source = self._module_source()
        assert "_on_search_changed" in source


# ── Animated components (headless-safe) ──────────────────────────────


class TestAnimatedComponentsConstants:
    """Tests for animated_components module-level constructs."""

    def test_module_parses(self):
        """Ensure the module can be loaded (AST) even without PyQt6."""
        import ast
        path = Path(__file__).parent.parent / "src" / "gui" / "animated_components.py"
        source = path.read_text()
        tree = ast.parse(source)
        class_names = [n.name for n in ast.walk(tree) if isinstance(n, ast.ClassDef)]
        assert "ParticleSystem" in class_names
        assert "CannonSmokeSystem" in class_names
        assert "MotionBlurParticleSystem" in class_names
        assert "ParallaxBattleScene" in class_names
        assert "FPSCounter" in class_names
        assert "LiveStatsDashboard" in class_names
        assert "SoundEffectPlayer" in class_names

    def test_cannon_smoke_particle_class(self):
        import ast
        path = Path(__file__).parent.parent / "src" / "gui" / "animated_components.py"
        source = path.read_text()
        tree = ast.parse(source)
        classes = {n.name for n in ast.walk(tree) if isinstance(n, ast.ClassDef)}
        assert "CannonSmokeParticle" in classes

    def test_motion_blur_particle_class(self):
        import ast
        path = Path(__file__).parent.parent / "src" / "gui" / "animated_components.py"
        source = path.read_text()
        tree = ast.parse(source)
        classes = {n.name for n in ast.walk(tree) if isinstance(n, ast.ClassDef)}
        assert "MotionBlurParticle" in classes

    def test_parallax_layer_class(self):
        import ast
        path = Path(__file__).parent.parent / "src" / "gui" / "animated_components.py"
        source = path.read_text()
        tree = ast.parse(source)
        classes = {n.name for n in ast.walk(tree) if isinstance(n, ast.ClassDef)}
        assert "ParallaxLayer" in classes
