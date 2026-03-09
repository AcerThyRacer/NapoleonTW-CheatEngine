"""
Tests for memory scanner and advanced memory operations.
"""

import io
import os
import sys
import struct
from pathlib import Path
from typing import Optional
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

    def test_parallel_scan_finds_integer_matches_with_backend(self):
        from src.memory.scanner import MemoryScanner, ValueType

        class FakeBackend:
            is_open = True

            def __init__(self) -> None:
                self._region = {'address': 0x1000, 'size': 12}
                self._data = struct.pack('<iii', 42, 7, 42)

            def get_readable_regions(self):
                return [self._region]

            def read_bytes(self, address: int, size: int) -> Optional[bytes]:
                if address == self._region['address'] and size == self._region['size']:
                    return self._data
                return None

        process_manager = Mock()
        process_manager.is_attached.return_value = True

        scanner = MemoryScanner(process_manager)
        scanner.backend = FakeBackend()

        count = scanner.scan_exact_value_parallel(42, ValueType.INT_32)

        assert count == 2
        assert [result.address for result in scanner.get_results()] == [0x1000, 0x1008]


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

    def test_search_bytes_uses_supplied_regions(self):
        from src.memory.backend import MemoryBackend

        class FakeBackend(MemoryBackend):
            def __init__(self) -> None:
                self._data = {0x1000: b'ABABX'}

            def open(self, pid: int) -> bool:
                return True

            def close(self) -> None:
                pass

            def read_bytes(self, address: int, size: int) -> Optional[bytes]:
                return self._data.get(address)

            def write_bytes(self, address: int, data: bytes) -> bool:
                return False

            def get_readable_regions(self):
                raise AssertionError("search_bytes should use supplied regions")

            @property
            def is_open(self) -> bool:
                return True

        backend = FakeBackend()

        results = backend.search_bytes(b'AB', regions=[{'address': 0x1000, 'size': 5}])

        assert results == [0x1000, 0x1002]

    def test_get_best_backend_prefers_procmem_on_native_linux(self):
        from src.memory.backend import ProcMemBackend, get_best_backend

        with patch('src.memory.backend.get_platform', return_value='linux'), \
             patch('src.memory.backend.is_proton', return_value=False):
            assert get_best_backend() is ProcMemBackend

    def test_get_best_backend_prefers_pymem_on_proton(self):
        from src.memory.backend import PymemBackend, get_best_backend

        with patch('src.memory.backend.get_platform', return_value='linux'), \
             patch('src.memory.backend.is_proton', return_value=True):
            assert get_best_backend() is PymemBackend

    def test_create_backend_uses_linux_priority_order(self):
        from src.memory.backend import create_backend, ProcMemBackend

        calls = []

        def procmem_open(self, pid):
            calls.append(('ProcMemBackend', pid))
            return True

        with patch('src.memory.backend.get_platform', return_value='linux'), \
             patch('src.memory.backend.is_proton', return_value=False), \
             patch('src.memory.backend.ProcMemBackend.open', new=procmem_open), \
             patch('src.memory.backend.PymemBackend.open', side_effect=AssertionError("Pymem should not be tried first")), \
             patch('src.memory.backend.PyMemoryEditorBackend.open', side_effect=AssertionError("PyMemoryEditor should not be tried first")):
            backend = create_backend(4242)

        assert isinstance(backend, ProcMemBackend)
        assert calls == [('ProcMemBackend', 4242)]

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
