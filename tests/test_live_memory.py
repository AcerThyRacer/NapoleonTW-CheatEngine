"""
Tests for live memory monitoring, speedhack, teleport, and new scanner methods.
"""

import struct
import sys
import time
from pathlib import Path
from unittest.mock import Mock, MagicMock, patch, PropertyMock

import pytest

# Ensure src is importable
sys.path.insert(0, str(Path(__file__).parent.parent))


# =========================================================================
# MemoryMonitor tests
# =========================================================================

class TestMemoryMonitor:
    """Tests for the MemoryMonitor background thread."""

    def test_import(self):
        from src.gui.memory_monitor import MemoryMonitor
        assert MemoryMonitor is not None

    def test_init_without_scanner(self):
        from src.gui.memory_monitor import MemoryMonitor
        mon = MemoryMonitor()
        assert mon._scanner is None
        assert mon._interval == 0.1

    def test_set_scanner(self):
        from src.gui.memory_monitor import MemoryMonitor
        mon = MemoryMonitor()
        scanner = Mock()
        mon.set_scanner(scanner)
        assert mon._scanner is scanner

    def test_set_interval_clamps(self):
        from src.gui.memory_monitor import MemoryMonitor
        mon = MemoryMonitor()
        mon.set_interval(0.005)
        assert mon._interval == 0.01  # minimum
        mon.set_interval(0.5)
        assert mon._interval == 0.5

    def test_monitor_and_unmonitor(self):
        from src.gui.memory_monitor import MemoryMonitor
        mon = MemoryMonitor()
        mon.monitor("infinite_gold", 0x1000)
        assert "infinite_gold" in mon._monitored
        mon.unmonitor("infinite_gold")
        assert "infinite_gold" not in mon._monitored

    def test_set_expected_value(self):
        from src.gui.memory_monitor import MemoryMonitor
        mon = MemoryMonitor()
        mon.set_expected_value("gold", 999999)
        assert mon._expected_values["gold"] == 999999
        mon.clear_expected_value("gold")
        assert "gold" not in mon._expected_values

    def test_get_last_value_empty(self):
        from src.gui.memory_monitor import MemoryMonitor
        mon = MemoryMonitor()
        assert mon.get_last_value("foo") is None

    def test_get_all_values(self):
        from src.gui.memory_monitor import MemoryMonitor
        mon = MemoryMonitor()
        mon._last_values = {"gold": 100, "health": 50}
        vals = mon.get_all_values()
        assert vals == {"gold": 100, "health": 50}
        # Returned dict should be a copy
        vals["gold"] = 0
        assert mon._last_values["gold"] == 100

    def test_stop_flag(self):
        from src.gui.memory_monitor import MemoryMonitor
        mon = MemoryMonitor()
        mon._running = True
        mon.stop()
        assert mon._running is False

    def test_poll_address_records_value(self):
        from src.gui.memory_monitor import MemoryMonitor
        from src.memory.scanner import ValueType
        mon = MemoryMonitor()
        scanner = Mock()
        scanner.read_value.return_value = 42
        scanner.is_attached.return_value = True
        mon.set_scanner(scanner)

        info = {'address': 0x1000, 'value_type': ValueType.INT_32}
        mon._poll_address("test", info)

        assert mon._last_values["test"] == 42

    def test_poll_address_read_failure(self):
        from src.gui.memory_monitor import MemoryMonitor
        from src.memory.scanner import ValueType
        mon = MemoryMonitor()
        scanner = Mock()
        scanner.read_value.side_effect = RuntimeError("fail")
        scanner.is_attached.return_value = True
        mon.set_scanner(scanner)

        info = {'address': 0xDEAD, 'value_type': ValueType.INT_32}
        mon._poll_address("test", info)
        # Should not crash, value should remain unset
        assert mon.get_last_value("test") is None


# =========================================================================
# SpeedhackManager tests
# =========================================================================

class TestSpeedhackManager:
    """Tests for SpeedhackManager."""

    def test_import(self):
        from src.memory.speedhack import SpeedhackManager
        assert SpeedhackManager is not None

    def test_init_defaults(self):
        from src.memory.speedhack import SpeedhackManager
        shm = SpeedhackManager()
        assert shm.multiplier == 1.0
        assert not shm.is_active
        assert shm.speed_addresses == []

    def test_set_scanner(self):
        from src.memory.speedhack import SpeedhackManager
        shm = SpeedhackManager()
        scanner = Mock()
        shm.set_scanner(scanner)
        assert shm._scanner is scanner

    def test_add_speed_address(self):
        from src.memory.speedhack import SpeedhackManager
        shm = SpeedhackManager()
        shm.add_speed_address(0x1000)
        shm.add_speed_address(0x2000)
        shm.add_speed_address(0x1000)  # duplicate — ignored
        assert shm.speed_addresses == [0x1000, 0x2000]

    def test_set_game_speed_clamps(self):
        from src.memory.speedhack import SpeedhackManager
        scanner = Mock()
        scanner.backend = Mock()
        scanner.backend.write_bytes = Mock()
        scanner.backend.read_bytes = Mock(return_value=struct.pack('<f', 1.0))
        shm = SpeedhackManager(scanner)
        shm.add_speed_address(0x1000)

        shm.set_game_speed(100.0)  # should clamp to 10.0
        assert shm.multiplier == 10.0

        shm.set_game_speed(0.01)  # should clamp to 0.5
        assert shm.multiplier == 0.5

    def test_set_game_speed_writes(self):
        from src.memory.speedhack import SpeedhackManager
        scanner = Mock()
        scanner.backend = Mock()
        scanner.backend.write_bytes = Mock()
        scanner.backend.read_bytes = Mock(return_value=struct.pack('<f', 1.0))
        shm = SpeedhackManager(scanner)
        shm.add_speed_address(0xABC0)

        result = shm.set_game_speed(2.0)
        assert result is True
        assert shm.is_active is True
        scanner.backend.write_bytes.assert_called_with(
            0xABC0, struct.pack('<f', 2.0)
        )

    def test_set_game_speed_no_addresses(self):
        from src.memory.speedhack import SpeedhackManager
        shm = SpeedhackManager(Mock())
        result = shm.set_game_speed(2.0)
        assert result is False

    def test_restore(self):
        from src.memory.speedhack import SpeedhackManager
        scanner = Mock()
        scanner.backend = Mock()
        scanner.backend.write_bytes = Mock()
        scanner.backend.read_bytes = Mock(return_value=struct.pack('<f', 1.0))
        shm = SpeedhackManager(scanner)
        shm.add_speed_address(0x1000)
        shm.set_game_speed(3.0)

        result = shm.restore()
        assert result is True
        assert shm.multiplier == 1.0
        assert shm.is_active is False

    def test_get_status(self):
        from src.memory.speedhack import SpeedhackManager
        shm = SpeedhackManager()
        shm.add_speed_address(0x1000)
        status = shm.get_status()
        assert status['active'] is False
        assert status['multiplier'] == 1.0
        assert status['address_count'] == 1
        assert '0x00001000' in status['addresses']

    def test_find_speed_addresses_no_scanner(self):
        from src.memory.speedhack import SpeedhackManager
        shm = SpeedhackManager()
        result = shm.find_speed_addresses()
        assert result == []

    def test_speed_limits_constants(self):
        from src.memory.speedhack import SpeedhackManager
        assert SpeedhackManager.MIN_MULTIPLIER == 0.5
        assert SpeedhackManager.MAX_MULTIPLIER == 10.0
        assert SpeedhackManager.DEFAULT_MULTIPLIER == 1.0


# =========================================================================
# TeleportManager tests
# =========================================================================

class TestTeleportManager:
    """Tests for TeleportManager and Coordinates."""

    def test_import(self):
        from src.memory.teleport import TeleportManager, Coordinates, TeleportTarget
        assert TeleportManager is not None
        assert Coordinates is not None
        assert TeleportTarget is not None

    def test_coordinates_dataclass(self):
        from src.memory.teleport import Coordinates
        c = Coordinates(1.5, 2.5, 3.5)
        assert c.x == 1.5
        assert c.y == 2.5
        assert c.z == 3.5
        assert c.as_tuple() == (1.5, 2.5, 3.5)

    def test_coordinates_str(self):
        from src.memory.teleport import Coordinates
        c = Coordinates(10.0, 20.0, 30.0)
        assert "10.00" in str(c)
        assert "20.00" in str(c)
        assert "30.00" in str(c)

    def test_register_entity(self):
        from src.memory.teleport import TeleportManager
        tm = TeleportManager()
        tm.register_entity("army1", 0x100, 0x104, 0x108)
        assert "army1" in tm.list_entities()

    def test_register_entity_from_base(self):
        from src.memory.teleport import TeleportManager
        tm = TeleportManager()
        tm.register_entity_from_base("army1", 0x1000)
        addrs = tm._entities["army1"]
        assert addrs['x'] == 0x1000 + TeleportManager.POSITION_OFFSETS['x']
        assert addrs['y'] == 0x1000 + TeleportManager.POSITION_OFFSETS['y']
        assert addrs['z'] == 0x1000 + TeleportManager.POSITION_OFFSETS['z']

    def test_unregister_entity(self):
        from src.memory.teleport import TeleportManager
        tm = TeleportManager()
        tm.register_entity("army1", 0x100, 0x104, 0x108)
        tm.unregister_entity("army1")
        assert "army1" not in tm.list_entities()

    def test_read_position(self):
        from src.memory.teleport import TeleportManager, Coordinates
        scanner = Mock()
        scanner.backend = Mock()

        def fake_read(addr, size):
            values = {0x100: 1.0, 0x104: 2.0, 0x108: 3.0}
            return struct.pack('<f', values.get(addr, 0.0))

        scanner.backend.read_bytes = fake_read
        tm = TeleportManager(scanner)
        tm.register_entity("army1", 0x100, 0x104, 0x108)
        pos = tm.read_position("army1")
        assert pos is not None
        assert abs(pos.x - 1.0) < 0.001
        assert abs(pos.y - 2.0) < 0.001
        assert abs(pos.z - 3.0) < 0.001

    def test_read_position_unknown_entity(self):
        from src.memory.teleport import TeleportManager
        tm = TeleportManager()
        assert tm.read_position("unknown") is None

    def test_teleport(self):
        from src.memory.teleport import TeleportManager, Coordinates
        scanner = Mock()
        scanner.backend = Mock()
        scanner.backend.write_bytes = Mock()
        tm = TeleportManager(scanner)
        tm.register_entity("army1", 0x100, 0x104, 0x108)

        result = tm.teleport("army1", Coordinates(10.0, 20.0, 30.0))
        assert result is True
        assert scanner.backend.write_bytes.call_count == 3

    def test_teleport_unknown_entity(self):
        from src.memory.teleport import TeleportManager, Coordinates
        tm = TeleportManager()
        assert tm.teleport("unknown", Coordinates()) is False

    def test_teleport_relative(self):
        from src.memory.teleport import TeleportManager, Coordinates
        scanner = Mock()
        scanner.backend = Mock()
        scanner.backend.read_bytes = Mock(return_value=struct.pack('<f', 5.0))
        scanner.backend.write_bytes = Mock()
        tm = TeleportManager(scanner)
        tm.register_entity("army1", 0x100, 0x104, 0x108)

        result = tm.teleport_relative("army1", dx=10.0)
        assert result is True

    def test_bookmarks(self):
        from src.memory.teleport import TeleportManager, Coordinates
        tm = TeleportManager()
        tm.save_bookmark("Paris", Coordinates(150.0, 0.0, 300.0), "Capital")
        bm = tm.get_bookmark("Paris")
        assert bm is not None
        assert bm.name == "Paris"
        assert bm.coords.x == 150.0
        assert len(tm.list_bookmarks()) == 1

        assert tm.delete_bookmark("Paris") is True
        assert tm.delete_bookmark("Paris") is False  # already gone
        assert len(tm.list_bookmarks()) == 0

    def test_teleport_to_bookmark(self):
        from src.memory.teleport import TeleportManager, Coordinates
        scanner = Mock()
        scanner.backend = Mock()
        scanner.backend.write_bytes = Mock()
        tm = TeleportManager(scanner)
        tm.register_entity("army1", 0x100, 0x104, 0x108)
        tm.save_bookmark("Paris", Coordinates(150.0, 0.0, 300.0))

        result = tm.teleport_to_bookmark("army1", "Paris")
        assert result is True

    def test_teleport_to_unknown_bookmark(self):
        from src.memory.teleport import TeleportManager
        tm = TeleportManager()
        assert tm.teleport_to_bookmark("army1", "Atlantis") is False

    def test_get_status(self):
        from src.memory.teleport import TeleportManager, Coordinates
        tm = TeleportManager()
        tm.register_entity("army1", 0x100, 0x104, 0x108)
        tm.save_bookmark("London", Coordinates(0, 0, 0))
        status = tm.get_status()
        assert status['entity_count'] == 1
        assert status['bookmark_count'] == 1
        assert 'army1' in status['entities']
        assert 'London' in status['bookmarks']

    def test_read_all_positions(self):
        from src.memory.teleport import TeleportManager
        scanner = Mock()
        scanner.backend = Mock()
        scanner.backend.read_bytes = Mock(return_value=struct.pack('<f', 1.0))
        tm = TeleportManager(scanner)
        tm.register_entity("a1", 0x100, 0x104, 0x108)
        tm.register_entity("a2", 0x200, 0x204, 0x208)
        positions = tm.read_all_positions()
        assert len(positions) == 2
        assert "a1" in positions
        assert "a2" in positions

    def test_position_offsets(self):
        from src.memory.teleport import TeleportManager
        assert 'x' in TeleportManager.POSITION_OFFSETS
        assert 'y' in TeleportManager.POSITION_OFFSETS
        assert 'z' in TeleportManager.POSITION_OFFSETS


# =========================================================================
# Scanner: scan_pointers / scan_aob methods
# =========================================================================

class TestScannerNewMethods:
    """Tests for scan_pointers() and scan_aob() on MemoryScanner."""

    def test_has_scan_pointers_method(self):
        from src.memory import ProcessManager, MemoryScanner
        pm = ProcessManager()
        scanner = MemoryScanner(pm)
        assert hasattr(scanner, 'scan_pointers')

    def test_has_scan_aob_method(self):
        from src.memory import ProcessManager, MemoryScanner
        pm = ProcessManager()
        scanner = MemoryScanner(pm)
        assert hasattr(scanner, 'scan_aob')

    def test_scan_pointers_not_attached(self):
        from src.memory import ProcessManager, MemoryScanner
        pm = ProcessManager()
        scanner = MemoryScanner(pm)
        result = scanner.scan_pointers(0x1000, [0x10, 0x20])
        assert result is None

    def test_scan_pointers_follows_chain(self):
        from src.memory import ProcessManager, MemoryScanner

        pm = ProcessManager()
        scanner = MemoryScanner(pm)

        # Mock attachment and backend
        scanner.process_manager.process = Mock()
        scanner.process_manager.process.is_running.return_value = True
        mock_backend = Mock()
        mock_backend.is_open = True
        scanner.backend = mock_backend

        # Simulate: base_address reads ptr=0x5000, then 0x5000+0x10 reads ptr=0x8000
        # Final address = 0x8000 + 0x20 = 0x8020
        def fake_read(addr, size):
            if addr == 0x1000:
                return struct.pack('<Q', 0x5000)
            elif addr == 0x5000 + 0x10:
                return struct.pack('<Q', 0x8000)
            return b'\x00' * size

        mock_backend.read_bytes = fake_read
        result = scanner.scan_pointers(0x1000, [0x10, 0x20])
        assert result == 0x8020

    def test_scan_pointers_null_pointer(self):
        from src.memory import ProcessManager, MemoryScanner
        pm = ProcessManager()
        scanner = MemoryScanner(pm)
        scanner.process_manager.process = Mock()
        scanner.process_manager.process.is_running.return_value = True
        mock_backend = Mock()
        mock_backend.is_open = True
        mock_backend.read_bytes = Mock(return_value=struct.pack('<Q', 0))
        scanner.backend = mock_backend

        result = scanner.scan_pointers(0x1000, [0x10])
        assert result is None

    def test_scan_aob_not_attached(self):
        from src.memory import ProcessManager, MemoryScanner
        pm = ProcessManager()
        scanner = MemoryScanner(pm)
        result = scanner.scan_aob("89 5D ?? ?? 8B 45")
        assert result == []


# =========================================================================
# __init__ exports
# =========================================================================

class TestModuleExports:
    """Verify new symbols are exported from src.memory."""

    def test_speedhack_manager_exported(self):
        from src.memory import SpeedhackManager
        assert SpeedhackManager is not None

    def test_teleport_manager_exported(self):
        from src.memory import TeleportManager
        assert TeleportManager is not None

    def test_coordinates_exported(self):
        from src.memory import Coordinates
        assert Coordinates is not None

    def test_teleport_target_exported(self):
        from src.memory import TeleportTarget
        assert TeleportTarget is not None

    def test_lua_injector_exported(self):
        from src.memory import LuaInjector
        assert LuaInjector is not None


# =========================================================================
# LuaInjector tests
# =========================================================================

class TestLuaInjector:
    """Tests for the LuaInjector Lua 5.1 script injection manager."""

    def test_import(self):
        from src.memory.advanced import LuaInjector
        assert LuaInjector is not None

    def test_init_defaults(self):
        from src.memory.advanced import LuaInjector
        inj = LuaInjector()
        assert not inj.is_ready
        assert inj.loadbuffer_address is None
        assert inj.pcall_address is None
        assert inj.lua_state_address is None
        assert inj.history == []

    def test_set_editor(self):
        from src.memory.advanced import LuaInjector
        inj = LuaInjector()
        editor = Mock()
        inj.set_editor(editor)
        assert inj.editor is editor
        # set_editor resets resolved addresses
        assert not inj.is_ready

    def test_set_addresses(self):
        from src.memory.advanced import LuaInjector
        inj = LuaInjector()
        inj.set_addresses(
            loadbuffer=0x00401000,
            pcall=0x00402000,
            lua_state=0x00600000,
        )
        assert inj.is_ready
        assert inj.loadbuffer_address == 0x00401000
        assert inj.pcall_address == 0x00402000
        assert inj.lua_state_address == 0x00600000

    def test_is_ready_requires_all_three(self):
        from src.memory.advanced import LuaInjector
        inj = LuaInjector()
        inj._loadbuffer_addr = 0x1000
        assert not inj.is_ready  # missing pcall and lua_state

        inj._pcall_addr = 0x2000
        assert not inj.is_ready  # still missing lua_state

        inj._lua_state_addr = 0x3000
        assert inj.is_ready

    def test_get_status_not_ready(self):
        from src.memory.advanced import LuaInjector
        inj = LuaInjector()
        status = inj.get_status()
        assert status['ready'] is False
        assert status['loadbuffer_addr'] is None
        assert status['pcall_addr'] is None
        assert status['lua_state_addr'] is None
        assert status['injections'] == 0

    def test_get_status_ready(self):
        from src.memory.advanced import LuaInjector
        inj = LuaInjector()
        inj.set_addresses(0x1000, 0x2000, 0x3000)
        status = inj.get_status()
        assert status['ready'] is True
        assert status['loadbuffer_addr'] == '0x00001000'
        assert status['pcall_addr'] == '0x00002000'
        assert status['lua_state_addr'] == '0x00003000'

    def test_execute_not_ready_returns_false(self):
        from src.memory.advanced import LuaInjector
        inj = LuaInjector()
        result = inj.execute("print('hello')")
        assert result is False

    def test_execute_no_editor_returns_false(self):
        from src.memory.advanced import LuaInjector
        inj = LuaInjector()
        inj.set_addresses(0x1000, 0x2000, 0x3000)
        result = inj.execute("print('hello')")
        assert result is False

    def test_execute_source_too_long(self):
        from src.memory.advanced import LuaInjector
        editor = Mock()
        inj = LuaInjector(editor)
        inj.set_addresses(0x1000, 0x2000, 0x3000)
        long_source = "x" * (LuaInjector.MAX_LUA_SOURCE_LEN + 1)
        result = inj.execute(long_source)
        assert result is False

    def test_execute_writes_source_and_shellcode(self):
        """Full execute path with a fake backend that provides a code cave."""
        from src.memory.advanced import LuaInjector

        # Build a fake backend with a large zero-filled "code cave"
        cave_data = bytearray(b'\x00' * 0x4000)
        writes = []

        def fake_read(addr, size):
            # Return zeros for any read (simulates code cave)
            return bytes(size)

        def fake_write(addr, data):
            writes.append((addr, data))
            return True

        editor = Mock()
        editor.read_bytes = fake_read
        editor.write_bytes = fake_write
        editor.get_readable_regions = Mock(return_value=[
            {'address': 0x00700000, 'size': 0x4000},
        ])

        inj = LuaInjector(editor)
        inj.set_addresses(
            loadbuffer=0x00401000,
            pcall=0x00402000,
            lua_state=0x00600000,
        )

        result = inj.execute("print('hello')")
        assert result is True
        assert len(inj.history) == 1

        entry = inj.history[0]
        assert entry['source'] == "print('hello')"
        assert entry['source_addr'] == 0x00700000  # first cave found
        assert entry['source_size'] == len(b"print('hello')\x00")

        # Verify writes: at least source + shellcode
        assert len(writes) >= 2
        # First write is the Lua source string
        assert writes[0][0] == 0x00700000
        assert b"print('hello')" in writes[0][1]

    def test_execute_thread_safety(self):
        """Concurrent execute calls are serialised."""
        from src.memory.advanced import LuaInjector
        import threading

        call_order = []
        entered = threading.Event()

        def slow_do_execute(self_inj, source_bytes, lua_source):
            call_order.append(('start', lua_source))
            entered.set()  # signal that we're inside _do_execute
            import time
            time.sleep(0.05)
            call_order.append(('end', lua_source))
            return True

        editor = Mock()
        editor.get_readable_regions = Mock(return_value=[
            {'address': 0x700000, 'size': 0x4000},
        ])
        editor.read_bytes = Mock(return_value=b'\x00' * 256)
        editor.write_bytes = Mock(return_value=True)

        inj = LuaInjector(editor)
        inj.set_addresses(0x1000, 0x2000, 0x3000)

        with patch.object(LuaInjector, '_do_execute', slow_do_execute):
            t1 = threading.Thread(target=inj.execute, args=("script_a",))
            t2 = threading.Thread(target=inj.execute, args=("script_b",))
            t1.start()
            entered.wait(timeout=5)  # wait until t1 holds the lock
            entered.clear()
            t2.start()
            t1.join(timeout=5)
            t2.join(timeout=5)

        # Verify the calls didn't interleave
        assert len(call_order) == 4
        # First script should start and end before the second starts
        assert call_order[0][0] == 'start'
        assert call_order[1][0] == 'end'
        assert call_order[1][1] == call_order[0][1]  # same script
        assert call_order[2][0] == 'start'
        assert call_order[3][0] == 'end'
        assert call_order[3][1] == call_order[2][1]

    def test_scan_lua_functions_no_editor(self):
        from src.memory.advanced import LuaInjector
        inj = LuaInjector()
        result = inj.scan_lua_functions()
        assert result is False

    def test_scan_lua_functions_nothing_found(self):
        """Scan with an editor that returns no matching patterns."""
        from src.memory.advanced import LuaInjector
        editor = Mock()
        editor.read_bytes = Mock(return_value=b'\x90' * 256)
        editor.get_readable_regions = Mock(return_value=[])

        inj = LuaInjector(editor)
        result = inj.scan_lua_functions()
        assert result is False
        assert not inj.is_ready

    def test_build_shellcode_structure(self):
        """Verify the shellcode builder returns valid structure."""
        from src.memory.advanced import LuaInjector
        raw_code, fixup_offset, chunk_name_rel = LuaInjector._build_lua_exec_shellcode(
            lua_state_ptr_addr=0x00600000,
            loadbuffer_addr=0x00401000,
            pcall_addr=0x00402000,
            source_addr=0x00700000,
            source_len=16,
        )

        # Should return bytes
        assert isinstance(raw_code, bytes)
        assert len(raw_code) > 20  # non-trivial shellcode

        # Fixup offset should be within the code
        assert 0 < fixup_offset < len(raw_code)

        # Chunk name starts after code, contains "inject"
        assert raw_code[chunk_name_rel:chunk_name_rel + 6] == b'inject'

        # Starts with pushad (0x60)
        assert raw_code[0] == 0x60

        # Ends with chunk-name string
        assert raw_code[-1] == 0x00  # NUL-terminated
        assert b'inject\x00' in raw_code

        # Contains popad (0x61) and ret (0xC3) before the chunk name
        code_part = raw_code[:chunk_name_rel]
        assert 0x61 in code_part  # popad
        assert 0xC3 in code_part  # ret

    def test_build_shellcode_contains_addresses(self):
        """Verify addresses are embedded in the shellcode as expected."""
        from src.memory.advanced import LuaInjector
        raw_code, _, _ = LuaInjector._build_lua_exec_shellcode(
            lua_state_ptr_addr=0xAABBCCDD,
            loadbuffer_addr=0x11223344,
            pcall_addr=0x55667788,
            source_addr=0xDEADBEEF,
            source_len=42,
        )
        # Addresses should appear as little-endian 32-bit values
        assert struct.pack('<I', 0xAABBCCDD) in raw_code  # lua_state_ptr
        assert struct.pack('<I', 0x11223344) in raw_code  # loadbuffer
        assert struct.pack('<I', 0x55667788) in raw_code  # pcall
        assert struct.pack('<I', 0xDEADBEEF) in raw_code  # source_addr
        assert struct.pack('<I', 42) in raw_code           # source_len

    def test_cleanup(self):
        """cleanup() zeroes out written caves."""
        from src.memory.advanced import LuaInjector

        writes = []

        def fake_write(addr, data):
            writes.append((addr, data))
            return True

        editor = Mock()
        editor.read_bytes = Mock(return_value=b'\x00' * 256)
        editor.write_bytes = fake_write
        editor.get_readable_regions = Mock(return_value=[
            {'address': 0x700000, 'size': 0x4000},
        ])

        inj = LuaInjector(editor)
        inj.set_addresses(0x1000, 0x2000, 0x3000)
        inj.execute("print('hi')")

        writes.clear()
        inj.cleanup()

        # cleanup should have written zero-fill for both code and source
        assert len(writes) >= 2
        for addr, data in writes:
            assert all(b == 0 for b in data)
        assert inj.history == []

    def test_cleanup_no_editor(self):
        """cleanup() with no editor does not crash."""
        from src.memory.advanced import LuaInjector
        inj = LuaInjector()
        inj.cleanup()  # should not raise

    def test_lua_signatures_defined(self):
        """All three expected Lua AOB signatures are defined."""
        from src.memory.advanced import LuaInjector
        sigs = LuaInjector.LUA_SIGNATURES
        assert 'luaL_loadbuffer' in sigs
        assert 'lua_pcall' in sigs
        assert 'lua_state_global' in sigs
        for key, pattern in sigs.items():
            assert pattern.name
            assert pattern.pattern
            assert pattern.description

    def test_history_returns_copy(self):
        """history property returns a copy, not the internal list."""
        from src.memory.advanced import LuaInjector
        inj = LuaInjector()
        h1 = inj.history
        h1.append({'fake': True})
        assert len(inj.history) == 0  # internal list unaffected

    def test_max_lua_source_len(self):
        from src.memory.advanced import LuaInjector
        assert LuaInjector.MAX_LUA_SOURCE_LEN == 8192

    def test_alloc_cave_no_editor(self):
        from src.memory.advanced import LuaInjector
        inj = LuaInjector()
        assert inj._alloc_cave(100) is None

    def test_alloc_cave_no_regions(self):
        from src.memory.advanced import LuaInjector
        editor = Mock()
        editor.get_readable_regions = Mock(return_value=[])
        inj = LuaInjector(editor)
        assert inj._alloc_cave(100) is None

    def test_alloc_cave_finds_zeros(self):
        """_alloc_cave should find a run of zero bytes."""
        from src.memory.advanced import LuaInjector
        # Region with some non-zero bytes then a block of zeros
        data = b'\xFF' * 50 + b'\x00' * 200 + b'\xFF' * 50
        editor = Mock()
        editor.get_readable_regions = Mock(return_value=[
            {'address': 0x500000, 'size': len(data)},
        ])
        editor.read_bytes = Mock(return_value=data)
        inj = LuaInjector(editor)
        cave = inj._alloc_cave(100)
        assert cave is not None
        assert cave == 0x500000 + 50  # start of the zero run

    def test_alloc_cave_finds_int3_padding(self):
        """_alloc_cave should also match 0xCC (INT3) padding."""
        from src.memory.advanced import LuaInjector
        data = b'\xFF' * 10 + b'\xCC' * 100
        editor = Mock()
        editor.get_readable_regions = Mock(return_value=[
            {'address': 0x400000, 'size': len(data)},
        ])
        editor.read_bytes = Mock(return_value=data)
        inj = LuaInjector(editor)
        cave = inj._alloc_cave(50)
        assert cave == 0x400000 + 10
