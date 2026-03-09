"""
Tests for cheat metadata, address-table export, and code-cave helpers.
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))


class FakeBackend:
    """Simple byte-addressable backend for patching tests."""

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

    def get_readable_regions(self):
        return [{'address': self.base_address, 'size': self.size}]


class TestCheatManagerDefinitions:
    def test_requested_cheats_are_present(self):
        from src.memory import ProcessManager, MemoryScanner
        from src.memory.cheats import CheatManager, CheatType

        manager = CheatManager(MemoryScanner(ProcessManager()))
        cheat_types = {definition.cheat_type for definition in manager.cheat_definitions}

        assert len(manager.cheat_definitions) >= 20
        for cheat_type in (
            CheatType.INFINITE_ACTION_POINTS,
            CheatType.MAX_RESEARCH_POINTS,
            CheatType.INSTANT_AGENT_TRAINING,
            CheatType.FREE_DIPLOMATIC_ACTIONS,
            CheatType.INVISIBLE_ARMIES,
            CheatType.INFINITE_MORALE,
            CheatType.INSTANT_RELOAD,
            CheatType.RANGE_BOOST,
            CheatType.SPEED_BOOST,
            CheatType.INFINITE_UNIT_HEALTH,
            CheatType.INSTANT_VICTORY,
            CheatType.MAX_PUBLIC_ORDER,
            CheatType.ZERO_ATTRITION,
            CheatType.FREE_UPGRADES,
        ):
            assert cheat_type in cheat_types

    def test_new_cheat_instructions_use_real_scan_guide(self):
        from src.memory import ProcessManager, MemoryScanner
        from src.memory.cheats import CheatManager, CheatType

        manager = CheatManager(MemoryScanner(ProcessManager()))
        instructions = manager.get_cheat_instructions(CheatType.MAX_PUBLIC_ORDER)

        assert 'public order' in instructions.lower()
        assert 'scan' in instructions.lower()


class TestAddressTableExport:
    def test_build_address_table_payload_contains_new_cheats(self):
        from src.memory import ProcessManager, MemoryScanner
        from src.memory.cheats import CheatManager

        manager = CheatManager(MemoryScanner(ProcessManager()))
        payload = manager.build_address_table_payload()

        assert 'cheats' in payload
        assert 'pointer_chains' in payload
        assert 'aob_patterns' in payload
        assert payload['cheats']['max_public_order']['pointer_chains'] == ['public_order']
        assert payload['cheats']['speed_boost']['patch_mode'] == 'code_cave'

    def test_export_address_table_writes_json_file(self, tmp_path):
        from src.memory import ProcessManager, MemoryScanner
        from src.memory.cheats import CheatManager

        manager = CheatManager(MemoryScanner(ProcessManager()))
        output = tmp_path / 'napoleon_addresses.json'
        exported = manager.export_address_table(str(output))

        assert exported == output
        data = json.loads(output.read_text())
        assert data['cheats']['instant_victory']['pointer_chains'] == ['autoresolve_victory_flag']
        assert 'charge_speed_write' in data['aob_patterns']


class TestCodeCaveInjector:
    def test_injector_writes_jump_and_payload(self):
        from src.memory.cheats import CodeCaveInjector

        backend = FakeBackend()
        site_address = 0x1000
        cave_address = 0x1100

        backend.write_bytes(site_address, b'\x8B\x45\xFC\x90\x90')
        injector = CodeCaveInjector(backend)
        patches = injector.inject(
            site_address=site_address,
            payload=b'\x90\x90',
            overwrite_size=5,
            cave_address=cave_address,
        )

        assert patches is not None
        site_bytes = backend.read_bytes(site_address, 5)
        cave_bytes = backend.read_bytes(cave_address, 7)

        assert site_bytes[0] == 0xE9
        assert cave_bytes[:2] == b'\x90\x90'
        assert cave_bytes[2] == 0xE9
