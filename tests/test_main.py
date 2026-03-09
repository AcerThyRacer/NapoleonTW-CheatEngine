"""
Comprehensive test suite for Napoleon Total War Cheat Engine.
Uses pytest with mocking for external dependencies.
"""

import os
import sys
import json
import struct
import tempfile
import threading
from pathlib import Path
from unittest.mock import Mock, MagicMock, patch, PropertyMock

import pytest
import psutil

# Patch psutil._common.pmmap if missing (some psutil versions lack it)
if not hasattr(psutil._common, 'pmmap'):
    psutil._common.pmmap = type('pmmap', (), {})

# Ensure src is importable
sys.path.insert(0, str(Path(__file__).parent.parent))


# ══════════════════════════════════════════════════════════════
# Fixtures
# ══════════════════════════════════════════════════════════════

@pytest.fixture
def temp_dir():
    """Provide a temporary directory that is cleaned up after test."""
    with tempfile.TemporaryDirectory() as d:
        yield Path(d)


@pytest.fixture
def mock_process():
    """Mock psutil.Process for game process."""
    proc = Mock()
    proc.pid = 12345
    proc.name.return_value = "napoleon.exe"
    proc.is_running.return_value = True
    proc.status.return_value = "running"
    proc.cpu_percent.return_value = 25.0
    proc.num_threads.return_value = 10
    proc.memory_info.return_value = Mock(rss=500 * 1024 * 1024, vms=1024 * 1024 * 1024)
    proc.oneshot.return_value.__enter__ = Mock(return_value=None)
    proc.oneshot.return_value.__exit__ = Mock(return_value=False)
    proc.info = {'pid': 12345, 'name': 'napoleon.exe'}
    return proc


@pytest.fixture
def sample_esf_data():
    """Create minimal valid ESF binary data."""
    buf = bytearray()
    buf.extend(b'ESF\x00')  # Magic
    buf.extend(struct.pack('<I', 1))  # Version 1

    # Root block node
    buf.append(0x01)  # BLOCK type
    name = b'root'
    buf.extend(struct.pack('<I', len(name)))
    buf.extend(name)

    # Child integer node
    buf.append(0x02)  # INTEGER type
    name2 = b'gold'
    buf.extend(struct.pack('<I', len(name2)))
    buf.extend(name2)
    buf.extend(struct.pack('<i', 50000))  # Value: 50000

    # Child float node
    buf.append(0x03)  # FLOAT type
    name3 = b'morale'
    buf.extend(struct.pack('<I', len(name3)))
    buf.extend(name3)
    buf.extend(struct.pack('<f', 100.0))

    # Child string node
    buf.append(0x04)  # STRING type
    name4 = b'faction'
    buf.extend(struct.pack('<I', len(name4)))
    buf.extend(name4)
    val = b'france'
    buf.extend(struct.pack('<I', len(val)))
    buf.extend(val)

    # Child boolean node
    buf.append(0x05)  # BOOLEAN type
    name5 = b'is_player'
    buf.extend(struct.pack('<I', len(name5)))
    buf.extend(name5)
    buf.append(0x01)  # True

    buf.append(0xFF)  # End block

    return bytes(buf)


@pytest.fixture
def sample_esf_file(temp_dir, sample_esf_data):
    """Write ESF data to a temp file."""
    path = temp_dir / "test_save.esf"
    path.write_bytes(sample_esf_data)
    return path


# ══════════════════════════════════════════════════════════════
# Platform / Utils Tests
# ══════════════════════════════════════════════════════════════

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


# ══════════════════════════════════════════════════════════════
# Memory Module Tests
# ══════════════════════════════════════════════════════════════

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


class TestMemoryScanner:
    """Tests for memory scanner."""

    def test_scanner_initialization(self):
        from src.memory import ProcessManager, MemoryScanner
        pm = ProcessManager()
        scanner = MemoryScanner(pm)
        assert scanner is not None
        assert not scanner.is_attached()

    def test_value_type_enum(self):
        from src.memory.scanner import ValueType
        assert ValueType.INT_32.value == '4 Bytes'
        assert ValueType.FLOAT.value == 'Float'
        assert ValueType.DOUBLE.value == 'Double'

    def test_scan_type_enum(self):
        from src.memory.scanner import ScanType
        assert ScanType.EXACT_VALUE is not None
        assert ScanType.INCREASED_VALUE is not None
        assert ScanType.DECREASED_VALUE is not None

    def test_clear_results(self):
        from src.memory import ProcessManager, MemoryScanner
        pm = ProcessManager()
        scanner = MemoryScanner(pm)
        scanner.clear_results()
        assert scanner.get_results() == []

    def test_has_parallel_scan_method(self):
        from src.memory import ProcessManager, MemoryScanner
        pm = ProcessManager()
        scanner = MemoryScanner(pm)
        assert hasattr(scanner, 'scan_exact_value_parallel')


class TestMemoryAdvanced:
    """Tests for advanced memory operations."""

    def test_memory_freezer_init(self):
        from src.memory.advanced import MemoryFreezer
        mock_editor = Mock()
        freezer = MemoryFreezer(mock_editor)
        assert len(freezer.frozen) == 0

    def test_freezer_freeze_and_unfreeze(self):
        from src.memory.advanced import MemoryFreezer
        mock_editor = Mock()
        freezer = MemoryFreezer(mock_editor)

        freezer.freeze(0x12345678, 999, 'int32')
        stats = freezer.get_stats()
        assert stats['total_frozen'] >= 1

        freezer.unfreeze(0x12345678)
        stats = freezer.get_stats()
        assert stats['total_frozen'] == 0

    def test_freezer_unfreeze_all(self):
        from src.memory.advanced import MemoryFreezer
        mock_editor = Mock()
        freezer = MemoryFreezer(mock_editor)

        freezer.freeze(0x1000, 1, 'int32')
        freezer.freeze(0x2000, 2, 'int32')
        count = freezer.unfreeze_all()
        assert count == 2
        assert len(freezer.frozen) == 0

    def test_freezer_set_frozen_value(self):
        from src.memory.advanced import MemoryFreezer
        mock_editor = Mock()
        freezer = MemoryFreezer(mock_editor)

        freezer.freeze(0x1000, 100, 'int32')
        result = freezer.set_frozen_value(0x1000, 200)
        assert result is True
        assert freezer.frozen[0x1000].value == 200

    def test_freezer_get_stats_structure(self):
        from src.memory.advanced import MemoryFreezer
        freezer = MemoryFreezer(None)
        stats = freezer.get_stats()
        assert 'total_frozen' in stats
        assert 'active_frozen' in stats

    def test_pointer_resolver_init(self):
        from src.memory.advanced import PointerResolver
        mock_editor = Mock()
        resolver = PointerResolver(mock_editor)
        assert resolver is not None

    def test_aob_scanner_init(self):
        from src.memory.advanced import AOBScanner
        mock_editor = Mock()
        scanner = AOBScanner(mock_editor)
        assert scanner is not None

    def test_chunked_scanner_init(self):
        from src.memory.advanced import ChunkedScanner
        mock_editor = Mock()
        scanner = ChunkedScanner(mock_editor)
        assert scanner is not None

    def test_pointer_chain_dataclass(self):
        from src.memory.advanced import PointerChain
        chain = PointerChain(
            module_name="napoleon.exe",
            base_offset=0x1000,
            offsets=[0x10, 0x20],
            description="test chain",
            value_type='int32'
        )
        assert chain.module_name == "napoleon.exe"
        assert chain.offsets == [0x10, 0x20]

    def test_frozen_address_dataclass(self):
        from src.memory.advanced import FrozenAddress
        fa = FrozenAddress(
            address=0xDEAD,
            value=42,
            value_type='int32'
        )
        assert fa.address == 0xDEAD
        assert fa.value == 42
        assert fa.enabled is True


# ══════════════════════════════════════════════════════════════
# ESF Editor Tests
# ══════════════════════════════════════════════════════════════

class TestESFEditor:
    """Tests for ESF file parsing and serialization."""

    def test_editor_init(self):
        from src.files import ESFEditor
        editor = ESFEditor()
        assert editor is not None
        assert editor.root is None

    def test_load_valid_esf(self, sample_esf_file):
        from src.files.esf_editor import ESFEditor
        editor = ESFEditor()
        result = editor.load_file(str(sample_esf_file))
        assert result is True
        assert editor.root is not None

    def test_parse_root_has_children(self, sample_esf_file):
        from src.files.esf_editor import ESFEditor
        editor = ESFEditor()
        editor.load_file(str(sample_esf_file))
        assert editor.root is not None
        assert len(editor.root.children) >= 1

    def test_load_empty_file(self, temp_dir):
        from src.files.esf_editor import ESFEditor
        empty_file = temp_dir / "empty.esf"
        empty_file.write_bytes(b'')
        editor = ESFEditor()
        result = editor.load_file(str(empty_file))
        assert result is False

    def test_load_nonexistent_file(self):
        from src.files.esf_editor import ESFEditor
        editor = ESFEditor()
        result = editor.load_file("/nonexistent/path/file.esf")
        assert result is False

    def test_save_and_reload(self, sample_esf_file, temp_dir):
        from src.files.esf_editor import ESFEditor
        editor = ESFEditor()
        editor.load_file(str(sample_esf_file))

        out_path = temp_dir / "resaved.esf"
        result = editor.save_file(str(out_path))
        assert result is True
        assert out_path.exists()

        editor2 = ESFEditor()
        result2 = editor2.load_file(str(out_path))
        assert result2 is True
        assert editor2.root is not None

    def test_node_to_dict(self, sample_esf_file):
        from src.files.esf_editor import ESFEditor
        editor = ESFEditor()
        editor.load_file(str(sample_esf_file))
        d = editor.root.to_dict()
        assert isinstance(d, dict)
        assert 'name' in d

    def test_esf_node_creation(self):
        from src.files.esf_editor import ESFNode, ESFNodeType
        node = ESFNode(
            name='test_node',
            node_type=ESFNodeType.INTEGER,
            value=42
        )
        assert node.name == 'test_node'
        assert node.value == 42
        assert node.node_type == ESFNodeType.INTEGER

    def test_esf_node_search(self):
        from src.files.esf_editor import ESFNode, ESFNodeType
        root = ESFNode(name='root', node_type=ESFNodeType.BLOCK_START)
        child1 = ESFNode(name='gold', node_type=ESFNodeType.INTEGER, value=1000)
        child2 = ESFNode(name='gold', node_type=ESFNodeType.INTEGER, value=2000)
        root.children = [child1, child2]
        results = root.find_all_by_name('gold')
        assert len(results) == 2
        assert results[0].value == 1000
        assert results[1].value == 2000

    def test_esf_node_find_child(self):
        from src.files.esf_editor import ESFNode, ESFNodeType
        root = ESFNode(name='root', node_type=ESFNodeType.BLOCK_START)
        child = ESFNode(name='gold', node_type=ESFNodeType.INTEGER, value=1000)
        root.children = [child]
        found = root.find_child('gold')
        assert found is not None
        assert found.value == 1000

    def test_esf_node_find_child_missing(self):
        from src.files.esf_editor import ESFNode, ESFNodeType
        root = ESFNode(name='root', node_type=ESFNodeType.BLOCK_START)
        found = root.find_child('nonexistent')
        assert found is None

    def test_esf_node_set_value(self):
        from src.files.esf_editor import ESFNode, ESFNodeType
        node = ESFNode(name='gold', node_type=ESFNodeType.INTEGER, value=100)
        result = node.set_value(999)
        assert result is True
        assert node.value == 999

    def test_security_error(self):
        from src.files.esf_editor import SecurityError
        with pytest.raises(SecurityError):
            raise SecurityError("Test security violation")


# ══════════════════════════════════════════════════════════════
# Script Editor Tests
# ══════════════════════════════════════════════════════════════

class TestScriptEditor:
    """Tests for Lua script editing."""

    def test_init(self):
        from src.files import ScriptEditor
        editor = ScriptEditor()
        assert editor is not None
        assert editor.content == ""

    def test_has_unsaved_changes_initially_false(self):
        from src.files import ScriptEditor
        editor = ScriptEditor()
        assert editor.has_unsaved_changes() is False

    def test_validate_syntax_returns_tuple(self):
        from src.files import ScriptEditor
        editor = ScriptEditor()
        editor.content = "local x = 5\nreturn x"
        result = editor.validate_syntax()
        assert isinstance(result, tuple)
        assert len(result) == 2
        assert isinstance(result[0], bool)


# ══════════════════════════════════════════════════════════════
# Config Editor Tests
# ══════════════════════════════════════════════════════════════

class TestConfigEditor:
    """Tests for game configuration editing."""

    def test_init(self):
        from src.files import ConfigEditor
        editor = ConfigEditor()
        assert editor is not None

    def test_value_parsing_bool(self):
        from src.files import ConfigEditor
        editor = ConfigEditor()
        assert editor._parse_value('true') is True
        assert editor._parse_value('false') is False

    def test_value_parsing_int(self):
        from src.files import ConfigEditor
        editor = ConfigEditor()
        assert editor._parse_value('42') == 42

    def test_value_parsing_float(self):
        from src.files import ConfigEditor
        editor = ConfigEditor()
        assert editor._parse_value('3.14') == 3.14

    def test_value_parsing_string(self):
        from src.files import ConfigEditor
        editor = ConfigEditor()
        assert editor._parse_value('"hello"') == 'hello'


# ══════════════════════════════════════════════════════════════
# Pack Parser Tests
# ══════════════════════════════════════════════════════════════

class TestPackParser:
    """Tests for pack file parsing."""

    def test_parser_init(self):
        from src.pack.pack_parser import PackParser
        parser = PackParser()
        assert parser is not None
        assert parser.files == {}

    def test_load_nonexistent_file(self):
        from src.pack.pack_parser import PackParser
        parser = PackParser()
        result = parser.load_file("/nonexistent/file.pack")
        assert result is False

    def test_cache_starts_empty(self):
        from src.pack.pack_parser import PackParser
        parser = PackParser()
        assert len(parser._extraction_cache) == 0

    def test_cache_stats(self):
        from src.pack import PackParser
        parser = PackParser()
        stats = parser.get_cache_stats()
        assert 'cached_files' in stats
        assert 'max_cache_size' in stats
        assert stats['cached_files'] == 0

    def test_list_files_empty(self):
        from src.pack import PackParser
        parser = PackParser()
        assert parser.list_files() == []


# ══════════════════════════════════════════════════════════════
# Database Editor Tests
# ══════════════════════════════════════════════════════════════

class TestDatabaseEditor:
    """Tests for database table editor."""

    def test_init(self):
        from src.pack import DatabaseEditor
        editor = DatabaseEditor()
        assert editor is not None
        assert editor.tables == {}

    def test_value_conversion_int(self):
        from src.pack.database_editor import DatabaseEditor
        editor = DatabaseEditor()
        assert editor._convert_value('42') == 42

    def test_value_conversion_float(self):
        from src.pack.database_editor import DatabaseEditor
        editor = DatabaseEditor()
        assert editor._convert_value('3.14') == 3.14

    def test_value_conversion_bool(self):
        from src.pack.database_editor import DatabaseEditor
        editor = DatabaseEditor()
        assert editor._convert_value('true') is True
        assert editor._convert_value('false') is False

    def test_value_conversion_string(self):
        from src.pack.database_editor import DatabaseEditor
        editor = DatabaseEditor()
        assert editor._convert_value('hello') == 'hello'

    def test_get_all_tables_empty(self):
        from src.pack.database_editor import DatabaseEditor
        editor = DatabaseEditor()
        assert editor.get_all_tables() == []


# ══════════════════════════════════════════════════════════════
# Mod Creator Tests
# ══════════════════════════════════════════════════════════════

class TestModCreator:
    """Tests for mod pack creator."""

    def test_init(self):
        from src.pack import ModCreator
        creator = ModCreator()
        assert creator is not None
        assert creator.files == {}

    def test_add_file(self):
        from src.pack import ModCreator
        creator = ModCreator()
        creator.add_file('test.txt', b'Hello World')
        assert 'test.txt' in creator.files
        assert creator.files['test.txt'] == b'Hello World'

    def test_remove_file(self):
        from src.pack import ModCreator
        creator = ModCreator()
        creator.add_file('test.txt', b'data')
        result = creator.remove_file('test.txt')
        assert result is True
        assert 'test.txt' not in creator.files

    def test_clear(self):
        from src.pack import ModCreator
        creator = ModCreator()
        creator.add_file('a.txt', b'aaa')
        creator.add_file('b.txt', b'bbb')
        creator.clear()
        assert creator.files == {}

    def test_get_stats_structure(self):
        from src.pack import ModCreator
        creator = ModCreator()
        creator.add_file('f.txt', b'12345')
        stats = creator.get_stats()
        assert stats['file_count'] == 1
        assert 'total_size' in stats
        assert 'f.txt' in stats['files']

    def test_set_mod_info(self):
        from src.pack import ModCreator
        creator = ModCreator()
        creator.set_mod_info("Test Mod", "A test mod", "2.0")
        assert creator.mod_name == "Test Mod"
        assert creator.mod_version == "2.0"


# ══════════════════════════════════════════════════════════════
# Config / Settings Tests
# ══════════════════════════════════════════════════════════════

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


# ══════════════════════════════════════════════════════════════
# Trainer / Hotkeys Tests
# ══════════════════════════════════════════════════════════════

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


# ══════════════════════════════════════════════════════════════
# CLI Tests
# ══════════════════════════════════════════════════════════════

class TestCLI:
    """Tests for the interactive CLI."""

    def test_cli_import(self):
        from src.cli import InteractiveCLI
        assert InteractiveCLI is not None

    def test_cli_init(self):
        from src.cli.interactive import InteractiveCLI
        cli = InteractiveCLI()
        assert cli._attached is False
        assert cli._process_manager is None

    def test_cli_quit_returns_true(self):
        from src.cli.interactive import InteractiveCLI
        cli = InteractiveCLI()
        result = cli.do_quit('')
        assert result is True

    def test_cli_status_unattached(self, capsys):
        from src.cli.interactive import InteractiveCLI
        cli = InteractiveCLI()
        cli.do_status('')
        captured = capsys.readouterr()
        assert 'Attached: No' in captured.out

    def test_cli_emptyline_does_nothing(self):
        from src.cli.interactive import InteractiveCLI
        cli = InteractiveCLI()
        result = cli.emptyline()
        assert result is None

    def test_cli_default_unknown_command(self, capsys):
        from src.cli.interactive import InteractiveCLI
        cli = InteractiveCLI()
        cli.default('invalid_command')
        captured = capsys.readouterr()
        assert 'Unknown command' in captured.out

    def test_cli_results_rejects_invalid_count(self, capsys):
        from src.cli.interactive import InteractiveCLI

        cli = InteractiveCLI()
        cli._scanner = Mock()
        cli._scanner.results = [
            Mock(address=0x1234, value=99, value_type=Mock(value='4 Bytes'))
        ]

        cli.do_results('not-a-number')
        captured = capsys.readouterr()

        assert 'Usage: results [positive count]' in captured.out


# ══════════════════════════════════════════════════════════════
# Plugin System Tests
# ══════════════════════════════════════════════════════════════

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


# ══════════════════════════════════════════════════════════════
# Events Tests
# ══════════════════════════════════════════════════════════════

class TestEvents:
    """Tests for the event system."""

    def test_event_emitter_singleton(self):
        from src.utils.events import EventEmitter
        ee1 = EventEmitter()
        ee2 = EventEmitter()
        assert ee1 is ee2

    def test_event_subscription_and_emit(self):
        from src.utils.events import EventEmitter, EventType
        ee = EventEmitter()
        received = []

        def handler(event):
            received.append(event)

        ee.on(EventType.CHEAT_ACTIVATED, handler)
        ee.emit(EventType.CHEAT_ACTIVATED, data={'test': 'value'})

        assert len(received) >= 1
        assert received[-1].data['test'] == 'value'

    def test_event_once(self):
        from src.utils.events import EventEmitter, EventType
        ee = EventEmitter()
        count = [0]

        def handler(event):
            count[0] += 1

        ee.once(EventType.STATUS_CHANGED, handler)
        ee.emit(EventType.STATUS_CHANGED)
        ee.emit(EventType.STATUS_CHANGED)
        assert count[0] == 1

    def test_event_priority_ordering(self):
        from src.utils.events import EventEmitter, EventType
        ee = EventEmitter()
        order = []

        def low(event): order.append('low')
        def high(event): order.append('high')

        ee.on(EventType.ERROR_OCCURRED, low, priority=1)
        ee.on(EventType.ERROR_OCCURRED, high, priority=10)
        ee.emit(EventType.ERROR_OCCURRED)

        assert order == ['high', 'low']

    def test_event_off(self):
        from src.utils.events import EventEmitter, EventType
        ee = EventEmitter()
        handler = Mock()
        ee.on(EventType.FILE_LOADED, handler)
        removed = ee.off(EventType.FILE_LOADED, handler)
        assert removed >= 1


# ══════════════════════════════════════════════════════════════
# Integration Tests
# ══════════════════════════════════════════════════════════════

class TestIntegration:
    """Integration tests that combine multiple modules."""

    def test_import_all_modules(self):
        from src import memory, files, pack, trainer, utils
        assert all(m is not None for m in [memory, files, pack, trainer, utils])
        try:
            from src import gui
            assert gui is not None
        except (ImportError, NameError):
            pytest.skip("GUI requires PyQt6")

    def test_memory_module_exports(self):
        from src.memory import (
            ProcessManager, MemoryScanner, ScanType, ValueType,
            CheatManager, CheatType
        )
        assert all(cls is not None for cls in [
            ProcessManager, MemoryScanner, ScanType, ValueType,
            CheatManager, CheatType
        ])

    def test_files_module_exports(self):
        from src.files import ESFEditor, ESFNode, ScriptEditor, ConfigEditor
        assert all(cls is not None for cls in [ESFEditor, ESFNode, ScriptEditor, ConfigEditor])

    def test_esf_roundtrip(self, sample_esf_file, temp_dir):
        """Test: load ESF -> modify -> save -> reload -> verify."""
        from src.files.esf_editor import ESFEditor

        editor = ESFEditor()
        assert editor.load_file(str(sample_esf_file))

        # Save
        out = temp_dir / "modified.esf"
        assert editor.save_file(str(out))

        # Reload and verify file is loadable
        editor2 = ESFEditor()
        assert editor2.load_file(str(out))
        assert editor2.root is not None

    def test_cheat_table_valid_json(self):
        """Test: cheat tables in tables/ dir are valid JSON."""
        tables_dir = Path(__file__).parent.parent / 'tables'
        for json_file in tables_dir.glob('*.json'):
            with open(json_file) as f:
                data = json.load(f)
            assert 'game' in data
            assert 'version' in data

    def test_tools_exist(self):
        """Test: standalone tools directory has Python files."""
        tools_dir = Path(__file__).parent.parent / 'tools'
        assert tools_dir.exists()
        assert any(tools_dir.glob('*.py'))

    def test_main_module_import(self):
        """Test: src.main can be imported and has main function."""
        import src.main
        assert hasattr(src.main, 'main')

    def test_cheat_manager_init(self):
        """Test CheatManager initializes with definitions."""
        from src.memory import ProcessManager, MemoryScanner, CheatManager
        pm = ProcessManager()
        scanner = MemoryScanner(pm)
        cm = CheatManager(scanner)
        assert len(cm.cheat_definitions) > 0

    def test_cheat_type_enum(self):
        from src.memory import CheatType
        assert CheatType.INFINITE_GOLD is not None
        assert CheatType.GOD_MODE is not None
        assert CheatType.UNLIMITED_AMMO is not None


# ══════════════════════════════════════════════════════════════
# Cheat Table File Tests
# ══════════════════════════════════════════════════════════════

class TestCheatTable:
    """Tests for cheat table JSON files."""

    def test_napoleon_table_structure(self):
        table_path = Path(__file__).parent.parent / 'tables' / 'napoleon_v1_6.json'
        if not table_path.exists():
            pytest.skip("Cheat table not found")

        with open(table_path) as f:
            data = json.load(f)

        assert 'pointer_chains' in data
        assert 'aob_patterns' in data
        assert 'scan_guides' in data

        for name, chain in data['pointer_chains'].items():
            assert 'module' in chain
            assert 'base_offset' in chain
            assert 'offsets' in chain
            assert isinstance(chain['offsets'], list)

        for name, pattern in data['aob_patterns'].items():
            assert 'pattern' in pattern
            assert 'description' in pattern


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
