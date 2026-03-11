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
        from src.memory.backend import SafeMemory
        scanner.safe_memory = SafeMemory(scanner.backend)

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
