"""
Tests for configuration management.
"""

import os
import sys
from pathlib import Path

import pytest
import psutil

# Patch psutil._common.pmmap if missing (some psutil versions lack it)
if not hasattr(psutil._common, 'pmmap'):
    psutil._common.pmmap = type('pmmap', (), {})

# Ensure src is importable
sys.path.insert(0, str(Path(__file__).parent.parent))


class TestConfig:
    """Tests for configuration management."""

    def test_config_creation_defaults(self):
        from src.config import Config
        config = Config()
        assert config.scan_settings.default_type == "INT_32"
        assert config.scan_settings.parallel_workers == 4
        assert config.auto_backup is True

    def test_config_manager_singleton(self):
        from src.config import ConfigManager
        cm1 = ConfigManager()
        cm2 = ConfigManager()
        assert cm1 is cm2

    def test_config_serialization_roundtrip(self):
        from src.config.settings import Config, HotkeyConfig
        config = Config()
        config.hotkeys['test_cheat'] = HotkeyConfig(key='f1', modifiers=['ctrl'])
        data = config.to_dict()
        config2 = Config.from_dict(data)
        assert config2.hotkeys['test_cheat'].key == 'f1'
        assert config2.hotkeys['test_cheat'].modifiers == ['ctrl']

    def test_config_scan_settings(self):
        from src.config.settings import ScanSettings
        s = ScanSettings()
        assert s.max_results == 10000
        assert s.enable_signature_scan is True

    def test_config_to_dict_has_all_keys(self):
        from src.config import Config
        config = Config()
        d = config.to_dict()
        assert 'hotkeys' in d
        assert 'scan_settings' in d
        assert 'ui_theme' in d
        assert 'auto_backup' in d
