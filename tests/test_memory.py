"""
Tests for memory scanner and advanced memory operations.
"""

import io
import os
import sys
import struct
from pathlib import Path
from unittest.mock import Mock, MagicMock, patch, PropertyMock

import pytest
import psutil

# Patch psutil._common.pmmap if missing (some psutil versions lack it)
if not hasattr(psutil._common, 'pmmap'):
    psutil._common.pmmap = type('pmmap', (), {})

# Ensure src is importable
sys.path.insert(0, str(Path(__file__).parent.parent))


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


class TestMemoryBackend:
    """Tests for memory backend helpers."""

    def test_procmem_regions_skip_malformed_lines(self):
        from src.memory.backend import ProcMemBackend

        backend = ProcMemBackend()
        backend._pid = 1234
        maps_data = io.StringIO(
            "00400000-00452000 r-xp 00000000 08:02 123 /bin/cat\n"
            "malformed-line-without-range r--p 00000000 00:00 0\n"
            "zzzz-00453000 r--p 00000000 00:00 0\n"
            "00453000-00452000 r--p 00000000 00:00 0\n"
            "00652000-00653000 ---p 00052000 08:02 123 /bin/cat\n"
            "00653000-00654000 r--p 00053000 08:02 123 /bin/cat\n"
        )

        with patch('builtins.open', return_value=maps_data):
            regions = backend.get_readable_regions()

        assert regions == [
            {'address': 0x00400000, 'size': 0x52000},
            {'address': 0x00653000, 'size': 0x1000},
        ]
