"""
Tests for MemoryWatchpoint and WatchpointManager.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.memory.watchpoints import (
    WatchpointCondition,
    ConditionType,
    MemoryWatchpoint,
    WatchpointManager
)

class FakeBackend:
    """Simple byte-addressable backend for testing."""

    def __init__(self, base_address=0x1000, size=0x400):
        self.base_address = base_address
        self.memory = bytearray(b'\x00' * size)
        self.size = size

    def _slice(self, address: int, size: int):
        start = address - self.base_address
        end = start + size
        if start < 0 or end > len(self.memory):
            return None
        return start, end

    def read_bytes(self, address: int, size: int):
        bounds = self._slice(address, size)
        if bounds is None:
            return None
        start, end = bounds
        return bytes(self.memory[start:end])

    def write_bytes(self, address: int, data: bytes):
        bounds = self._slice(address, len(data))
        if bounds is None:
            return False
        start, end = bounds
        self.memory[start:end] = data
        return True


def test_watchpoint_conditions():
    cond_eq = WatchpointCondition(ConditionType.EQUALS, 100)
    assert cond_eq.evaluate(100, 50) is True
    assert cond_eq.evaluate(50, 50) is False

    cond_gt = WatchpointCondition(ConditionType.GREATER_THAN, 100)
    assert cond_gt.evaluate(150, 50) is True
    assert cond_gt.evaluate(50, 50) is False

    cond_lt = WatchpointCondition(ConditionType.LESS_THAN, 100)
    assert cond_lt.evaluate(50, 150) is True
    assert cond_lt.evaluate(150, 150) is False

    cond_changed = WatchpointCondition(ConditionType.CHANGED, None)
    assert cond_changed.evaluate(100, 50) is True
    assert cond_changed.evaluate(100, 100) is False


def test_watchpoint_manager():
    import struct
    import time

    backend = FakeBackend()
    manager = WatchpointManager(editor=backend)
    manager._interval_ms = 10 # fast for testing

    triggered_values = []
    def on_trigger(curr, prev):
        triggered_values.append((curr, prev))

    wp = MemoryWatchpoint(
        id="test_wp",
        description="Test watchpoint",
        address=0x1000,
        value_type="int32",
        conditions=[WatchpointCondition(ConditionType.LESS_THAN, 10000)],
        actions=[on_trigger]
    )

    # Write 15000 initially
    backend.write_bytes(0x1000, struct.pack('<i', 15000))

    manager.add_watchpoint(wp)
    time.sleep(0.05)

    # Should not be triggered yet
    assert len(triggered_values) == 0

    # Write 5000, which is < 10000
    backend.write_bytes(0x1000, struct.pack('<i', 5000))
    time.sleep(0.05)

    # Should be triggered
    assert len(triggered_values) > 0
    assert triggered_values[0][0] == 5000

    manager.stop()
