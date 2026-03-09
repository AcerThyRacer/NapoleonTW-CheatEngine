"""
Tests for the plugin system.
"""

import os
import sys
import tempfile
from pathlib import Path

import pytest
import psutil

# Patch psutil._common.pmmap if missing (some psutil versions lack it)
if not hasattr(psutil._common, 'pmmap'):
    psutil._common.pmmap = type('pmmap', (), {})

# Ensure src is importable
sys.path.insert(0, str(Path(__file__).parent.parent))


@pytest.fixture
def temp_dir():
    """Provide a temporary directory that is cleaned up after test."""
    with tempfile.TemporaryDirectory() as d:
        yield Path(d)


class TestPluginSystem:
    """Tests for the plugin manager."""

    def test_plugin_manager_init(self):
        from src.plugins.manager import PluginManager
        pm = PluginManager()
        assert pm.plugin_count == 0

    def test_load_plugin_class(self):
        from src.plugins.manager import PluginManager, PluginBase, PluginMetadata

        class TestPlugin(PluginBase):
            metadata = PluginMetadata(name="TestPlugin", version="0.1")
            def on_load(self, engine): pass
            def on_unload(self): pass

        pm = PluginManager()
        name = pm.load_plugin_class(TestPlugin)
        assert name == "TestPlugin"
        assert pm.plugin_count == 1

    def test_unload_plugin(self):
        from src.plugins.manager import PluginManager, PluginBase, PluginMetadata

        class TestPlugin(PluginBase):
            metadata = PluginMetadata(name="UnloadTest")
            def on_load(self, engine): pass
            def on_unload(self): pass

        pm = PluginManager()
        pm.load_plugin_class(TestPlugin)
        assert pm.plugin_count == 1
        pm.unload_plugin("UnloadTest")
        assert pm.plugin_count == 0

    def test_list_plugins(self):
        from src.plugins.manager import PluginManager, PluginBase, PluginMetadata

        class TestPlugin(PluginBase):
            metadata = PluginMetadata(name="ListTest", version="1.0", author="Tester")
            def on_load(self, engine): pass
            def on_unload(self): pass

        pm = PluginManager()
        pm.load_plugin_class(TestPlugin)
        plugins = pm.list_plugins()
        assert len(plugins) == 1
        assert plugins[0]['name'] == 'ListTest'
        assert plugins[0]['version'] == '1.0'

    def test_enable_disable_plugin(self):
        from src.plugins.manager import PluginManager, PluginBase, PluginMetadata

        class TestPlugin(PluginBase):
            metadata = PluginMetadata(name="ToggleTest")
            def on_load(self, engine): pass
            def on_unload(self): pass

        pm = PluginManager()
        pm.load_plugin_class(TestPlugin)

        pm.disable_plugin("ToggleTest")
        assert pm.get_plugin("ToggleTest").enabled is False

        pm.enable_plugin("ToggleTest")
        assert pm.get_plugin("ToggleTest").enabled is True

    def test_get_nonexistent_plugin(self):
        from src.plugins.manager import PluginManager
        pm = PluginManager()
        assert pm.get_plugin("nonexistent") is None

    def test_unload_nonexistent(self):
        from src.plugins.manager import PluginManager
        pm = PluginManager()
        result = pm.unload_plugin("nonexistent")
        assert result is False

    def test_discover_plugins(self, temp_dir):
        from src.plugins.manager import PluginManager
        pm = PluginManager(plugin_dirs=[temp_dir])

        plugin_code = '''
from src.plugins.manager import PluginBase, PluginMetadata
class DiscoverPlugin(PluginBase):
    metadata = PluginMetadata(name="Discovered")
    def on_load(self, engine): pass
    def on_unload(self): pass
'''
        (temp_dir / "test_plugin.py").write_text(plugin_code)
        found = pm.discover_plugins()
        assert len(found) >= 1

    def test_load_allowlist_ignores_invalid_hashes(self, temp_dir):
        from src.plugins.manager import PluginManager

        valid_hash = 'a' * 64
        invalid_hash = 'g' * 64
        allowlist = temp_dir / "plugin_allowlist.sha256"
        allowlist.write_text(
            f"{valid_hash}  # valid\n"
            f"{invalid_hash}  # invalid non-hex\n"
            "short-hash\n"
        )

        pm = PluginManager(plugin_dirs=[temp_dir])
        count = pm.load_allowlist(allowlist)

        assert count == 1
        assert pm._hash_allowlist == {valid_hash}
