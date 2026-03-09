"""
Tests for platform utilities, exceptions, logging, game state, and process manager.
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


class TestPlatform:
    """Tests for platform detection utilities."""

    def test_get_platform_returns_valid(self):
        from src.utils.platform import get_platform
        result = get_platform()
        assert result in ('windows', 'linux', 'macos', 'unknown')

    def test_get_process_name_returns_string(self):
        from src.utils.platform import get_process_name
        name = get_process_name()
        assert isinstance(name, str)
        assert len(name) > 0

    def test_get_all_possible_names_not_empty(self):
        from src.utils.platform import get_all_possible_process_names
        names = get_all_possible_process_names()
        assert len(names) > 0
        assert all(isinstance(n, str) for n in names)

    def test_normalize_path_returns_path(self):
        from src.utils.platform import normalize_path
        result = normalize_path("/some/path")
        assert isinstance(result, Path)

    def test_detect_display_server_wayland(self):
        from src.utils.platform import detect_display_server

        with patch('src.utils.platform.get_platform', return_value='linux'), \
             patch.dict(os.environ, {'XDG_SESSION_TYPE': 'wayland'}, clear=False):
            assert detect_display_server() == 'wayland'

    def test_detect_display_server_x11(self):
        from src.utils.platform import detect_display_server

        with patch('src.utils.platform.get_platform', return_value='linux'), \
             patch.dict(os.environ, {'XDG_SESSION_TYPE': 'x11'}, clear=False):
            assert detect_display_server() == 'x11'

    def test_get_hotkey_compatibility_warning_on_wayland(self):
        from src.utils.platform import get_hotkey_compatibility_warning

        with patch('src.utils.platform.detect_display_server', return_value='wayland'):
            assert "Wayland detected" in get_hotkey_compatibility_warning()

    def test_get_steam_path_supports_flatpak_layout(self, tmp_path):
        from src.utils.platform import get_steam_path

        steam_path = tmp_path / '.var' / 'app' / 'com.valvesoftware.Steam' / '.local' / 'share' / 'Steam'
        steam_path.mkdir(parents=True)

        with patch('src.utils.platform.get_platform', return_value='linux'), \
             patch('src.utils.platform.Path.home', return_value=tmp_path):
            assert get_steam_path() == steam_path

    def test_get_napoleon_install_path_supports_linux_steam_name(self, tmp_path):
        from src.utils.platform import get_napoleon_install_path

        install_path = tmp_path / '.local' / 'share' / 'Steam' / 'steamapps' / 'common' / 'Napoleon Total War'
        install_path.mkdir(parents=True)

        with patch('src.utils.platform.get_platform', return_value='linux'), \
             patch('src.utils.platform.Path.home', return_value=tmp_path):
            assert get_napoleon_install_path() == install_path

    def test_check_memory_access_permissions_linux(self):
        from src.utils.platform import check_memory_access_permissions

        def fake_open(path, mode='r', *args, **kwargs):
            if path == '/proc/sys/kernel/yama/ptrace_scope':
                return MagicMock(__enter__=lambda self: self, __exit__=lambda *exc: None, read=lambda: '1')
            if path.endswith('/mem') and mode == 'rb':
                return MagicMock(__enter__=lambda self: self, __exit__=lambda *exc: None)
            raise FileNotFoundError(path)

        with patch('src.utils.platform.get_platform', return_value='linux'), \
             patch('src.utils.platform.os.geteuid', return_value=0), \
             patch('builtins.open', side_effect=fake_open):
            result = check_memory_access_permissions()

        assert result['can_read'] is True
        assert result['can_write'] is True
        assert result['ptrace_scope'] == 1
        assert result['recommendations']

    def test_check_memory_access_permissions_permission_denied(self):
        from src.utils.platform import check_memory_access_permissions

        def fake_open(path, mode='r', *args, **kwargs):
            if path == '/proc/sys/kernel/yama/ptrace_scope':
                raise FileNotFoundError(path)
            if path.endswith('/mem'):
                raise PermissionError(path)
            raise FileNotFoundError(path)

        with patch('src.utils.platform.get_platform', return_value='linux'), \
             patch('src.utils.platform.os.geteuid', return_value=1000), \
             patch('builtins.open', side_effect=fake_open):
            result = check_memory_access_permissions()

        assert result['can_read'] is False
        assert result['can_write'] is False
        assert any('sudo' in note or 'CAP_SYS_PTRACE' in note for note in result['recommendations'])


class TestExceptions:
    """Tests for the exception hierarchy."""

    def test_base_exception(self):
        from src.utils.exceptions import CheatEngineError
        exc = CheatEngineError("test error")
        assert str(exc) == "test error"
        assert isinstance(exc, Exception)

    def test_process_error_hierarchy(self):
        from src.utils.exceptions import CheatEngineError, ProcessError
        exc = ProcessError("proc fail")
        assert isinstance(exc, CheatEngineError)

    def test_memory_error_hierarchy(self):
        from src.utils.exceptions import CheatEngineError
        from src.utils.exceptions import MemoryError as NapMemoryError
        exc = NapMemoryError("mem fail")
        assert isinstance(exc, CheatEngineError)

    def test_file_error_hierarchy(self):
        from src.utils.exceptions import CheatEngineError, FileError
        exc = FileError("file fail")
        assert isinstance(exc, CheatEngineError)

    def test_all_error_types_exist(self):
        from src.utils import exceptions
        for attr in ['CheatEngineError', 'ProcessError', 'MemoryError',
                     'FileError', 'ConfigError', 'TrainerError']:
            assert hasattr(exceptions, attr), f"Missing: {attr}"

    def test_specific_subclasses_exist(self):
        from src.utils import exceptions
        for attr in ['ProcessNotFoundError', 'ProcessAccessDeniedError',
                     'MemoryReadError', 'MemoryWriteError',
                     'ESFParseError', 'PackParseError',
                     'HotkeyError', 'PluginError']:
            assert hasattr(exceptions, attr), f"Missing: {attr}"


class TestLogging:
    """Tests for the logging configuration."""

    def test_setup_logging_returns_logger(self):
        from src.utils.logging_config import setup_logging
        logger = setup_logging(console=False)
        assert logger is not None

    def test_get_logger(self):
        from src.utils.logging_config import get_logger
        logger = get_logger('test_module')
        assert logger is not None
        assert 'test_module' in logger.name


class TestGameState:
    """Tests for game state monitoring."""

    def test_initial_state_not_running(self):
        from src.utils.game_state import GameStateMonitor, GameMode
        monitor = GameStateMonitor()
        assert monitor.mode == GameMode.NOT_RUNNING
        assert monitor.pid is None
        assert not monitor.is_running

    def test_get_state_snapshot(self):
        from src.utils.game_state import GameStateMonitor
        monitor = GameStateMonitor()
        state = monitor.get_state()
        assert 'mode' in state
        assert 'pid' in state
        assert 'is_running' in state
        assert state['is_running'] is False

    def test_callbacks_stored(self):
        from src.utils.game_state import GameStateMonitor
        monitor = GameStateMonitor()

        started_cb = Mock()
        stopped_cb = Mock()
        mode_cb = Mock()

        monitor.set_callbacks(
            on_game_started=started_cb,
            on_game_stopped=stopped_cb,
            on_mode_changed=mode_cb,
        )

        assert monitor._on_game_started is started_cb
        assert monitor._on_game_stopped is stopped_cb
        assert monitor._on_mode_changed is mode_cb

    def test_game_mode_enum_values(self):
        from src.utils.game_state import GameMode
        assert GameMode.NOT_RUNNING is not None
        assert GameMode.CAMPAIGN is not None
        assert GameMode.BATTLE is not None


class TestProcessManager:
    """Tests for process management."""

    @patch('src.memory.process.psutil')
    def test_list_game_processes(self, mock_psutil):
        from src.memory.process import ProcessManager

        mock_proc = Mock()
        mock_proc.info = {'pid': 123, 'name': 'napoleon.exe'}
        mock_psutil.process_iter.return_value = [mock_proc]

        procs = ProcessManager.list_game_processes()
        assert isinstance(procs, list)

    def test_process_manager_init(self):
        from src.memory.process import ProcessManager
        pm = ProcessManager()
        assert pm.pid is None
        assert pm.process is None

    def test_is_attached_false_initially(self):
        from src.memory.process import ProcessManager
        pm = ProcessManager()
        assert pm.is_attached() is False

    def test_detach_when_not_attached(self):
        from src.memory.process import ProcessManager
        pm = ProcessManager()
        pm.detach()
        assert pm.is_attached() is False
