"""
Tests for the first-run setup wizard helpers.
"""

import sys
from pathlib import Path

import psutil

# Patch psutil._common.pmmap if missing (some psutil versions lack it)
if not hasattr(psutil._common, 'pmmap'):
    psutil._common.pmmap = type('pmmap', (), {})

# Ensure src is importable
sys.path.insert(0, str(Path(__file__).parent.parent))


class TestSetupWizardHelpers:
    """Tests for pure setup-wizard helper functions."""

    def test_apply_setup_choices_updates_config(self):
        from src.config import Config
        from src.gui.setup_wizard import apply_setup_choices

        config = Config()
        apply_setup_choices(
            config,
            theme_name="Imperial Blue",
            overlay_preset="winter_campaign",
            auto_backup=False,
            game_path="/games/Napoleon Total War",
            backup_path="/backups/napoleon",
        )

        assert config.ui_theme == "imperial_blue"
        assert config.overlay_preset == "winter_campaign"
        assert config.overlay_animation == "russian_winter"
        assert config.auto_backup is False
        assert config.setup_completed is True
        assert config.paths.napoleon_install == "/games/Napoleon Total War"
        assert config.paths.backup_directory == "/backups/napoleon"

    def test_theme_name_roundtrip(self):
        from src.gui.setup_wizard import (
            panel_theme_name_for_value,
            panel_theme_value_for_name,
        )

        assert panel_theme_name_for_value("midnight_command") == "Midnight Command"
        assert panel_theme_value_for_name("Royal Purple") == "royal_purple"
        assert panel_theme_value_for_name("Unknown Theme") == "napoleon_gold"
