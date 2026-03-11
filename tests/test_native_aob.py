"""
Tests for the native AOB (Array of Bytes) scanner C extension and Python wrapper.
"""

import struct
import sys
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.memory.native_aob import (
    NativeAOBScanner,
    parse_pattern,
    is_available,
    _WILDCARD,
)


# ──────────────────────────────────────────────────────────────────────
# Pattern parsing
# ──────────────────────────────────────────────────────────────────────

class TestParsePattern:
    """Tests for the AOB pattern string parser."""

    def test_simple_hex_pattern(self):
        result = parse_pattern("8B 0D 01 02")
        assert result == [0x8B, 0x0D, 0x01, 0x02]

    def test_wildcards_question_marks(self):
        result = parse_pattern("8B ?? 01")
        assert result == [0x8B, _WILDCARD, 0x01]

    def test_wildcards_asterisks(self):
        result = parse_pattern("8B ** 01")
        assert result == [0x8B, _WILDCARD, 0x01]

    def test_wildcards_xx(self):
        result = parse_pattern("8B XX 01")
        assert result == [0x8B, _WILDCARD, 0x01]

    def test_wildcards_xx_lower(self):
        result = parse_pattern("8B xx 01")
        assert result == [0x8B, _WILDCARD, 0x01]

    def test_mixed_pattern(self):
        result = parse_pattern("8B 0D ?? ?? ?? ?? 8B 01 8B 40 18")
        assert result == [0x8B, 0x0D, _WILDCARD, _WILDCARD, _WILDCARD, _WILDCARD,
                          0x8B, 0x01, 0x8B, 0x40, 0x18]

    def test_empty_pattern(self):
        result = parse_pattern("")
        assert result == []

    def test_single_byte(self):
        result = parse_pattern("FF")
        assert result == [0xFF]

    def test_invalid_token_becomes_wildcard(self):
        result = parse_pattern("8B ZZ 01")
        assert result == [0x8B, _WILDCARD, 0x01]

    def test_lowercase_hex(self):
        result = parse_pattern("8b 0d ff")
        assert result == [0x8B, 0x0D, 0xFF]


# ──────────────────────────────────────────────────────────────────────
# NativeAOBScanner
# ──────────────────────────────────────────────────────────────────────

class TestNativeAOBScanner:
    """Tests for the NativeAOBScanner class."""

    def test_initialization(self):
        scanner = NativeAOBScanner()
        assert scanner is not None

    def test_native_available(self):
        """The native extension should compile and load in a Linux CI env."""
        scanner = NativeAOBScanner()
        assert scanner.native_available is True

    def test_scan_buffer_exact_match(self):
        scanner = NativeAOBScanner()
        data = bytes([0x8B, 0x0D, 0x10, 0x20, 0x30, 0x40, 0x8B, 0x01])
        results = scanner.scan_buffer(data, "8B 0D 10 20 30 40 8B 01")
        assert results == [0]

    def test_scan_buffer_with_base_address(self):
        scanner = NativeAOBScanner()
        data = bytes([0x8B, 0x0D, 0x10, 0x20, 0x30, 0x40, 0x8B, 0x01])
        results = scanner.scan_buffer(data, "8B 0D 10 20 30 40 8B 01",
                                      base_address=0x00400000)
        assert results == [0x00400000]

    def test_scan_buffer_with_wildcards(self):
        scanner = NativeAOBScanner()
        data = bytes([0x8B, 0x0D, 0xAA, 0xBB, 0xCC, 0xDD, 0x8B, 0x01])
        results = scanner.scan_buffer(data, "8B 0D ?? ?? ?? ?? 8B 01",
                                      base_address=0x1000)
        assert results == [0x1000]

    def test_scan_buffer_no_match(self):
        scanner = NativeAOBScanner()
        data = bytes([0x00, 0x01, 0x02, 0x03, 0x04, 0x05])
        results = scanner.scan_buffer(data, "FF FE FD")
        assert results == []

    def test_scan_buffer_multiple_matches(self):
        scanner = NativeAOBScanner()
        # Pattern AB CD appears at offset 0, 4, and 8
        data = bytes([0xAB, 0xCD, 0x00, 0x00,
                      0xAB, 0xCD, 0x00, 0x00,
                      0xAB, 0xCD])
        results = scanner.scan_buffer(data, "AB CD")
        assert results == [0, 4, 8]

    def test_scan_buffer_wildcard_only_pattern(self):
        scanner = NativeAOBScanner()
        data = bytes([0x01, 0x02, 0x03, 0x04])
        results = scanner.scan_buffer(data, "?? ??")
        assert len(results) == 3  # offsets 0, 1, 2

    def test_scan_buffer_empty_data(self):
        scanner = NativeAOBScanner()
        results = scanner.scan_buffer(b"", "8B 0D")
        assert results == []

    def test_scan_buffer_empty_pattern(self):
        scanner = NativeAOBScanner()
        results = scanner.scan_buffer(b"\x8B\x0D", "")
        assert results == []

    def test_scan_buffer_pattern_longer_than_data(self):
        scanner = NativeAOBScanner()
        results = scanner.scan_buffer(b"\x8B", "8B 0D 01 02")
        assert results == []

    def test_scan_buffer_single_byte_pattern(self):
        scanner = NativeAOBScanner()
        data = bytes([0x00, 0xFF, 0x00, 0xFF, 0x00])
        results = scanner.scan_buffer(data, "FF")
        assert results == [1, 3]

    def test_scan_buffer_max_results(self):
        scanner = NativeAOBScanner()
        data = bytes([0xAB] * 100)
        results = scanner.scan_buffer(data, "AB", max_results=5)
        assert len(results) == 5
        assert results == [0, 1, 2, 3, 4]

    def test_scan_buffer_napoleon_tw_pattern(self):
        """Test with a realistic Napoleon TW instruction pattern."""
        scanner = NativeAOBScanner()
        # Simulate: MOV [ESI+offset], EAX — treasury write
        # 89 86 XX XX XX XX 8B 45 FC
        preamble = bytes([0x90, 0x90])  # NOP padding
        instruction = bytes([0x89, 0x86, 0x44, 0x01, 0x00, 0x00, 0x8B, 0x45, 0xFC])
        postamble = bytes([0xC3])  # RET
        data = preamble + instruction + postamble

        results = scanner.scan_buffer(
            data, "89 86 ?? ?? ?? ?? 8B 45 FC", base_address=0x00401000
        )
        assert results == [0x00401002]

    def test_scan_buffer_overlapping_matches(self):
        """Pattern can overlap itself."""
        scanner = NativeAOBScanner()
        data = bytes([0xAA, 0xAA, 0xAA, 0xAA])
        results = scanner.scan_buffer(data, "AA AA")
        assert results == [0, 1, 2]


# ──────────────────────────────────────────────────────────────────────
# Python fallback
# ──────────────────────────────────────────────────────────────────────

class TestPythonFallback:
    """Tests for the pure-Python fallback path."""

    def test_fallback_scan_buffer(self):
        results = NativeAOBScanner._scan_buffer_python(
            data=bytes([0x8B, 0x0D, 0xAA, 0xBB, 0x8B, 0x01]),
            pattern=[0x8B, _WILDCARD, 0xAA, 0xBB],
            base_address=0x2000,
            max_results=100,
        )
        assert results == [0x2000]

    def test_fallback_multiple_matches(self):
        results = NativeAOBScanner._scan_buffer_python(
            data=bytes([0xAB, 0xCD, 0x00, 0xAB, 0xCD]),
            pattern=[0xAB, 0xCD],
            base_address=0,
            max_results=100,
        )
        assert results == [0, 3]

    def test_fallback_no_match(self):
        results = NativeAOBScanner._scan_buffer_python(
            data=bytes([0x00, 0x01, 0x02]),
            pattern=[0xFF],
            base_address=0,
            max_results=100,
        )
        assert results == []

    def test_fallback_max_results(self):
        results = NativeAOBScanner._scan_buffer_python(
            data=bytes([0xAB] * 50),
            pattern=[0xAB],
            base_address=0,
            max_results=3,
        )
        assert len(results) == 3

    def test_fallback_used_when_native_unavailable(self):
        """When the C library cannot be loaded, the Python fallback is used."""
        scanner = NativeAOBScanner()
        scanner._lib = None  # Force fallback

        data = bytes([0x8B, 0x0D, 0xAA, 0xBB, 0xCC, 0xDD, 0x8B, 0x01])
        results = scanner.scan_buffer(data, "8B 0D ?? ?? ?? ?? 8B 01")
        assert results == [0]


# ──────────────────────────────────────────────────────────────────────
# Integration with AOBScanner
# ──────────────────────────────────────────────────────────────────────

class TestAOBScannerIntegration:
    """Tests for AOBScanner native acceleration integration."""

    def test_aob_scanner_has_native_attribute(self):
        from src.memory.advanced import AOBScanner
        scanner = AOBScanner()
        assert hasattr(scanner, '_native')

    def test_aob_scanner_native_loaded(self):
        """AOBScanner should auto-load the native extension if available."""
        from src.memory.advanced import AOBScanner
        scanner = AOBScanner()
        # In CI with gcc available, native should be loaded
        assert scanner._native is not None

    def test_aob_scanner_scan_uses_native(self):
        """AOBScanner.scan() should use native extension for chunk scanning."""
        from src.memory.advanced import AOBScanner, AOBPattern

        mock_editor = Mock()
        # Return a chunk containing the pattern
        preamble = bytes([0x90] * 4)
        pattern_bytes = bytes([0x89, 0x86, 0x44, 0x01, 0x00, 0x00, 0x8B, 0x45, 0xFC])
        mock_editor.read_bytes.return_value = preamble + pattern_bytes + bytes(100)

        scanner = AOBScanner(mock_editor)
        pat = AOBPattern(
            name="Test",
            pattern="89 86 ?? ?? ?? ?? 8B 45 FC",
        )

        results = scanner.scan(
            pat,
            start_address=0x00400000,
            end_address=0x00400200,
            chunk_size=256,
        )
        # The pattern is at offset 4 in the data, so address = 0x00400000 + 4
        assert 0x00400004 in results


# ──────────────────────────────────────────────────────────────────────
# Export
# ──────────────────────────────────────────────────────────────────────

class TestExport:
    """Tests that NativeAOBScanner is properly exported."""

    def test_importable_from_memory_module(self):
        from src.memory import NativeAOBScanner
        assert NativeAOBScanner is not None

    def test_is_available_function(self):
        assert is_available() is True


# ──────────────────────────────────────────────────────────────────────
# scan_process (Linux-only, won't work without target process)
# ──────────────────────────────────────────────────────────────────────

class TestScanProcess:
    """Tests for the process_vm_readv-based scan path."""

    def test_scan_process_raises_without_native(self):
        scanner = NativeAOBScanner()
        scanner._lib = None
        with pytest.raises(RuntimeError, match="not available"):
            scanner.scan_process(pid=1, pattern="8B 0D")

    def test_scan_process_empty_pattern(self):
        scanner = NativeAOBScanner()
        results = scanner.scan_process(pid=1, pattern="")
        assert results == []
