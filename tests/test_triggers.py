"""
Tests for Conditional Cheat Triggers in CheatManager.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.memory.cheats import CheatManager, CheatType
from src.memory.watchpoints import ConditionType
from src.memory.scanner import MemoryScanner
from src.memory.process import ProcessManager

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


def test_add_conditional_cheat():
    manager = CheatManager(MemoryScanner(ProcessManager()))
    backend = FakeBackend()
    manager.memory_scanner.backend = backend

    # Try adding conditional cheat for infinite gold
    success = manager.add_conditional_cheat(
        cheat_type=CheatType.INFINITE_GOLD,
        condition_type=ConditionType.LESS_THAN,
        condition_value=10000,
        trigger_description="Auto-activate infinite gold if gold drops below 10,000",
        pointer_chain_name="treasury"
    )

    assert success is True
    assert "trigger_infinite_gold_less_than" in manager.watchpoint_manager.watchpoints

    wp = manager.watchpoint_manager.watchpoints["trigger_infinite_gold_less_than"]
    assert len(wp.conditions) == 1
    assert wp.conditions[0].condition_type == ConditionType.LESS_THAN
    assert wp.conditions[0].value == 10000
    assert len(wp.actions) == 1
