"""
Tests for DXVK installer integration.
"""

import io
import sys
import tarfile
import types
from pathlib import Path
from unittest.mock import Mock, patch

# Ensure src is importable
sys.path.insert(0, str(Path(__file__).parent.parent))


def _build_dxvk_archive(archive_path: Path, version: str = "2.3") -> None:
    root = f"dxvk-{version}/x32"
    with tarfile.open(archive_path, 'w:gz') as archive:
        for name, data in (('d3d9.dll', b'd3d9-data'), ('dxgi.dll', b'dxgi-data')):
            content = io.BytesIO(data)
            info = tarfile.TarInfo(name=f"{root}/{name}")
            info.size = len(data)
            archive.addfile(info, content)


class TestDXVKInstaller:
    """Tests for DXVK download and install flow."""

    def setup_method(self):
        from src.utils.events import EventEmitter
        EventEmitter.reset_instance()

    def teardown_method(self):
        from src.utils.events import EventEmitter
        EventEmitter.reset_instance()

    def test_install_dxvk_returns_false_when_game_path_missing(self):
        from src.files.dxvk_installer import install_dxvk
        from src.utils.events import EventEmitter, EventType

        with patch('src.files.dxvk_installer.get_napoleon_install_path', return_value=None):
            assert install_dxvk() is False

        errors = EventEmitter().get_history(EventType.ERROR_OCCURRED)
        assert errors[-1].data['error'] == (
            "Could not find Napoleon Total War installation directory for DXVK."
        )

    def test_install_dxvk_skips_download_when_already_installed(self, tmp_path):
        from src.files.dxvk_installer import install_dxvk
        from src.utils.events import EventEmitter, EventType

        (tmp_path / 'd3d9.dll').write_bytes(b'installed')
        (tmp_path / 'dxgi.dll').write_bytes(b'installed')

        with patch('src.files.dxvk_installer.get_napoleon_install_path', return_value=tmp_path), \
             patch('src.files.dxvk_installer.urllib.request.urlretrieve') as mock_retrieve:
            assert install_dxvk() is True

        mock_retrieve.assert_not_called()
        statuses = EventEmitter().get_history(EventType.STATUS_CHANGED)
        assert statuses[-1].data['status'] == "DXVK is already installed."

    def test_install_dxvk_downloads_and_extracts_x32_dlls(self, tmp_path):
        from src.files.dxvk_installer import install_dxvk
        from src.utils.events import EventEmitter, EventType

        source_archive = tmp_path / 'source_dxvk.tar.gz'
        _build_dxvk_archive(source_archive)

        def fake_urlretrieve(url, destination):
            Path(destination).write_bytes(source_archive.read_bytes())
            return destination, None

        with patch('src.files.dxvk_installer.get_napoleon_install_path', return_value=tmp_path), \
             patch('src.files.dxvk_installer.urllib.request.urlretrieve', side_effect=fake_urlretrieve):
            assert install_dxvk() is True

        assert (tmp_path / 'd3d9.dll').read_bytes() == b'd3d9-data'
        assert (tmp_path / 'dxgi.dll').read_bytes() == b'dxgi-data'

        statuses = [event.data['status'] for event in EventEmitter().get_history(EventType.STATUS_CHANGED)]
        assert statuses == [
            "Downloading DXVK...",
            "Installing DXVK...",
            "DXVK successfully installed!",
        ]

    def test_dxvk_plugin_is_discoverable(self):
        from src.plugins.manager import PluginManager

        plugin_manager = PluginManager()
        discovered = plugin_manager.discover_plugins()

        assert any(path.name == 'dxvk_plugin.py' for path in discovered)


class TestStartupPluginLoading:
    """Tests for the GUI startup plugin hook."""

    def test_launch_gui_uses_engine_service_before_gui(self):
        import src.main as main_module

        gui_main = Mock()
        service = Mock()
        real_import = __import__

        def fake_import(name, globals=None, locals=None, fromlist=(), level=0):
            if name == 'src.gui.napoleon_panel':
                raise ImportError("enhanced GUI unavailable")
            if name == 'src.gui.main_window':
                return types.SimpleNamespace(main=gui_main)
            return real_import(name, globals, locals, fromlist, level)

        def fake_run(runner, *, load_plugins=False):
            assert load_plugins is True
            return runner(service)

        service.run.side_effect = fake_run

        with patch('builtins.__import__', side_effect=fake_import):
            main_module.launch_gui(service)

        service.run.assert_called_once()
        gui_main.assert_called_once_with(service=service)
