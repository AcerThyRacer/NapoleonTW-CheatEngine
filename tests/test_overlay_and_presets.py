"""
Tests for Battle Map Overlay and Cheat Preset Manager.
"""

import json
import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import Mock, MagicMock, patch

import pytest

# Patch psutil._common.pmmap if missing
import psutil

if not hasattr(psutil._common, 'pmmap'):
    psutil._common.pmmap = type('pmmap', (), {})

sys.path.insert(0, str(Path(__file__).parent.parent))


# ---------------------------------------------------------------------------
# Preset Manager (non-GUI) tests
# ---------------------------------------------------------------------------


class TestCheatPreset:
    """Tests for the CheatPreset data model."""

    def test_create_default(self):
        from src.gui.preset_manager import CheatPreset
        p = CheatPreset()
        assert p.name == "Untitled"
        assert p.version == "2.0"
        assert p.cheats == {}
        assert isinstance(p.tags, list)

    def test_create_with_args(self):
        from src.gui.preset_manager import CheatPreset
        p = CheatPreset(name="Test", description="desc", author="me", tags=["a", "b"])
        assert p.name == "Test"
        assert p.description == "desc"
        assert p.author == "me"
        assert p.tags == ["a", "b"]

    def test_to_dict_roundtrip(self):
        from src.gui.preset_manager import CheatPreset
        p = CheatPreset(name="RT", description="roundtrip", author="bot", tags=["x"])
        p.cheats = {"infinite_gold": {"name": "Infinite Gold", "active": True, "mode": "campaign"}}
        d = p.to_dict()
        assert d["name"] == "RT"
        assert d["preset_format_version"] == "2.0"

        p2 = CheatPreset.from_dict(d)
        assert p2.name == "RT"
        assert p2.cheats["infinite_gold"]["active"] is True

    def test_save_and_load_file(self, tmp_path):
        from src.gui.preset_manager import CheatPreset
        p = CheatPreset(name="FileTest", description="file round-trip")
        p.cheats = {"god_mode": {"name": "God Mode", "active": True, "mode": "battle"}}
        file_path = tmp_path / "test_preset.json"
        p.save_to_file(file_path)

        assert file_path.exists()
        loaded = CheatPreset.load_from_file(file_path)
        assert loaded.name == "FileTest"
        assert loaded.cheats["god_mode"]["active"] is True


class TestPresetRepository:
    """Tests for the preset repository."""

    def test_list_empty(self, tmp_path):
        from src.gui.preset_manager import PresetRepository
        repo = PresetRepository(directory=tmp_path / "presets")
        assert repo.list_presets() == []

    def test_save_and_list(self, tmp_path):
        from src.gui.preset_manager import PresetRepository, CheatPreset
        repo = PresetRepository(directory=tmp_path / "presets")
        p = CheatPreset(name="SaveTest")
        p.cheats = {"fast_research": {"active": True}}
        path = repo.save_preset(p)
        assert path.exists()
        presets = repo.list_presets()
        assert len(presets) == 1
        assert presets[0].name == "SaveTest"

    def test_delete(self, tmp_path):
        from src.gui.preset_manager import PresetRepository, CheatPreset
        repo = PresetRepository(directory=tmp_path / "presets")
        p = CheatPreset(name="ToDelete")
        repo.save_preset(p)
        assert len(repo.list_presets()) == 1
        assert repo.delete_preset("ToDelete") is True
        assert len(repo.list_presets()) == 0

    def test_import_export(self, tmp_path):
        from src.gui.preset_manager import PresetRepository, CheatPreset
        repo = PresetRepository(directory=tmp_path / "presets")
        # Create an external file
        ext_path = tmp_path / "external.json"
        p = CheatPreset(name="Imported")
        p.save_to_file(ext_path)

        imported = repo.import_preset(ext_path)
        assert imported.name == "Imported"
        assert len(repo.list_presets()) == 1

        # Export
        export_path = tmp_path / "exported.json"
        repo.export_preset(imported, export_path)
        assert export_path.exists()
        data = json.loads(export_path.read_text())
        assert data["name"] == "Imported"


class TestVersionCompatibility:
    """Tests for preset version compatibility checks."""

    def test_compatible_current_version(self):
        from src.gui.preset_manager import CheatPreset, check_version_compatibility
        p = CheatPreset(name="V2")
        result = check_version_compatibility(p)
        assert result["compatible"] is True
        assert result["warnings"] == []

    def test_incompatible_version(self):
        from src.gui.preset_manager import CheatPreset, check_version_compatibility
        p = CheatPreset(name="Old")
        p.version = "99.0"
        result = check_version_compatibility(p)
        assert result["compatible"] is False
        assert len(result["warnings"]) > 0

    def test_unknown_cheat_types_warn(self):
        from src.gui.preset_manager import CheatPreset, check_version_compatibility
        p = CheatPreset(name="Warn")
        p.cheats = {"nonexistent_cheat": {"active": True}}
        result = check_version_compatibility(p)
        assert result["compatible"] is True
        assert any("unknown cheat types" in w.lower() for w in result["warnings"])


class TestCaptureApply:
    """Tests for capturing and applying presets to a CheatManager."""

    def _make_cheat_manager(self):
        from src.memory import ProcessManager, MemoryScanner, CheatManager
        pm = ProcessManager()
        scanner = MemoryScanner(pm)
        return CheatManager(scanner)

    def test_capture(self):
        from src.gui.preset_manager import capture_preset_from_manager
        cm = self._make_cheat_manager()
        preset = capture_preset_from_manager(cm, name="Cap", author="tester")
        assert preset.name == "Cap"
        assert preset.author == "tester"
        # Should have entries for all defined cheats
        assert len(preset.cheats) > 0
        assert "infinite_gold" in preset.cheats

    def test_apply_empty(self):
        from src.gui.preset_manager import capture_preset_from_manager, apply_preset_to_manager
        cm = self._make_cheat_manager()
        preset = capture_preset_from_manager(cm, name="Empty")
        # None active → nothing to activate
        result = apply_preset_to_manager(cm, preset)
        assert result["activated"] == []
        assert result["errors"] == []

    def test_apply_incompatible(self):
        from src.gui.preset_manager import CheatPreset, apply_preset_to_manager
        cm = self._make_cheat_manager()
        p = CheatPreset(name="Bad")
        p.version = "99.0"
        result = apply_preset_to_manager(cm, p)
        assert len(result["errors"]) > 0


# ---------------------------------------------------------------------------
# Battle Map Overlay (non-GUI / logic-only) tests
# ---------------------------------------------------------------------------


class TestBattleOverlayHelpers:
    """Tests that the overlay module can be imported and metadata is correct."""

    def test_import_module(self):
        from src.gui import battle_overlay
        assert hasattr(battle_overlay, 'BattleMapOverlay')
        assert hasattr(battle_overlay, '_CAMPAIGN_CHEATS')
        assert hasattr(battle_overlay, '_BATTLE_CHEATS')
        assert hasattr(battle_overlay, '_STRATEGIC_CHEATS')

    def test_cheat_lists_have_entries(self):
        from src.gui.battle_overlay import _CAMPAIGN_CHEATS, _BATTLE_CHEATS, _STRATEGIC_CHEATS
        assert len(_CAMPAIGN_CHEATS) > 0
        assert len(_BATTLE_CHEATS) > 0
        assert len(_STRATEGIC_CHEATS) > 0

    def test_cheat_list_structure(self):
        from src.gui.battle_overlay import _CAMPAIGN_CHEATS
        for entry in _CAMPAIGN_CHEATS:
            assert 'type' in entry
            assert 'label' in entry
            assert 'icon' in entry

    def test_unit_stats_widget_importable(self):
        from src.gui.battle_overlay import _UnitStatsWidget
        assert _UnitStatsWidget is not None

    def test_active_cheats_summary_importable(self):
        from src.gui.battle_overlay import _ActiveCheatsSummary
        assert _ActiveCheatsSummary is not None


class TestPresetManagerImport:
    """Tests that preset_manager module exports are correct."""

    def test_module_exports(self):
        from src.gui.preset_manager import (
            CheatPreset,
            PresetRepository,
            check_version_compatibility,
            capture_preset_from_manager,
            apply_preset_to_manager,
            PRESET_FORMAT_VERSION,
            COMPATIBLE_VERSIONS,
        )
        assert PRESET_FORMAT_VERSION == "2.0"
        assert "2.0" in COMPATIBLE_VERSIONS

    def test_preset_format_json_schema(self):
        """Ensure the JSON output has all required fields."""
        from src.gui.preset_manager import CheatPreset
        p = CheatPreset(name="Schema")
        d = p.to_dict()
        required_keys = {
            "preset_format_version", "app_version", "name", "description",
            "author", "tags", "created", "modified", "cheats",
        }
        assert required_keys.issubset(d.keys())
