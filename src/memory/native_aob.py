"""
Python wrapper for the native AOB (Array of Bytes) scanner C extension.

The module compiles ``native_scanner.c`` on first use and loads the resulting
shared library via :mod:`ctypes`.  If compilation is unavailable (e.g. no C
compiler), the wrapper falls back to the pure-Python implementation in
:class:`~src.memory.advanced.AOBScanner`.

Usage::

    from src.memory.native_aob import NativeAOBScanner

    scanner = NativeAOBScanner()
    results = scanner.scan_buffer(
        data=some_bytes,
        pattern="8B 0D ?? ?? ?? ?? 8B 01 8B 40 18",
        base_address=0x00400000,
    )
"""

from __future__ import annotations

import ctypes
import logging
import os
import platform
import subprocess
import sys
from pathlib import Path
from typing import List, Optional, Sequence

logger = logging.getLogger("napoleon.memory.native_aob")

# Wildcard sentinel — must match the value in native_scanner.c
_WILDCARD: int = 0xFFFF

# Maximum results per scan call — must match MAX_RESULTS in native_scanner.c
_MAX_RESULTS: int = 4096

# ──────────────────────────────────────────────────────────────────────
# Compilation helpers
# ──────────────────────────────────────────────────────────────────────

_SRC_DIR = Path(__file__).resolve().parent
_C_SOURCE = _SRC_DIR / "native_scanner.c"
_SO_NAME = "native_scanner.so"


def _so_path() -> Path:
    """Return the expected path of the compiled shared library."""
    return _SRC_DIR / _SO_NAME


def _compile(force: bool = False) -> Optional[Path]:
    """
    Compile ``native_scanner.c`` into a shared library.

    Returns the path to the ``.so`` on success, *None* on failure.
    """
    so = _so_path()
    if so.exists() and not force:
        return so

    if not _C_SOURCE.exists():
        logger.warning("C source not found: %s", _C_SOURCE)
        return None

    cc = os.environ.get("CC", "gcc")
    cmd = [
        cc, "-O2", "-shared", "-fPIC",
        "-o", str(so),
        str(_C_SOURCE),
    ]

    logger.info("Compiling native scanner: %s", " ".join(cmd))
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode != 0:
            logger.error("Compilation failed:\n%s\n%s", result.stdout, result.stderr)
            return None
        logger.info("Native scanner compiled → %s", so)
        return so
    except FileNotFoundError:
        logger.warning("C compiler '%s' not found — native scanner unavailable", cc)
        return None
    except Exception as exc:  # noqa: BLE001
        logger.warning("Compilation error: %s", exc)
        return None


# ──────────────────────────────────────────────────────────────────────
# Library loading
# ──────────────────────────────────────────────────────────────────────

_lib: Optional[ctypes.CDLL] = None


def _load_library() -> Optional[ctypes.CDLL]:
    """Load (and compile if necessary) the native scanner shared library."""
    global _lib
    if _lib is not None:
        return _lib

    so = _so_path()
    if not so.exists():
        so = _compile()
    if so is None or not so.exists():
        return None

    try:
        lib = ctypes.CDLL(str(so))
    except OSError as exc:
        logger.warning("Failed to load native scanner: %s", exc)
        return None

    # int aob_scan_buffer(
    #     const uint8_t  *data,
    #     size_t          data_len,
    #     const uint16_t *pattern,
    #     size_t          pattern_len,
    #     uint64_t        base_address,
    #     uint64_t       *out_addresses,
    #     size_t          max_results)
    lib.aob_scan_buffer.argtypes = [
        ctypes.c_char_p,                # data
        ctypes.c_size_t,                # data_len
        ctypes.POINTER(ctypes.c_uint16),  # pattern
        ctypes.c_size_t,                # pattern_len
        ctypes.c_uint64,                # base_address
        ctypes.POINTER(ctypes.c_uint64),  # out_addresses
        ctypes.c_size_t,                # max_results
    ]
    lib.aob_scan_buffer.restype = ctypes.c_int

    # Linux-only: aob_scan_process
    if sys.platform == "linux" and hasattr(lib, "aob_scan_process"):
        lib.aob_scan_process.argtypes = [
            ctypes.c_int,                   # pid
            ctypes.POINTER(ctypes.c_uint16),  # pattern
            ctypes.c_size_t,                # pattern_len
            ctypes.c_uint64,                # start_address
            ctypes.c_uint64,                # end_address
            ctypes.POINTER(ctypes.c_uint64),  # out_addresses
            ctypes.c_size_t,                # max_results
        ]
        lib.aob_scan_process.restype = ctypes.c_int

    _lib = lib
    return _lib


def is_available() -> bool:
    """Return *True* if the native scanner can be loaded."""
    return _load_library() is not None


# ──────────────────────────────────────────────────────────────────────
# Pattern parsing
# ──────────────────────────────────────────────────────────────────────

def parse_pattern(pattern_str: str) -> List[int]:
    """
    Parse an AOB pattern string into a list of ``uint16`` values.

    Each whitespace-separated token is interpreted as:
    * A two-character hex literal (``"8B"`` → ``0x8B``).
    * A wildcard placeholder (``"??"``/ ``"**"``/ ``"XX"``/ ``"xx"``) →
      ``_WILDCARD`` (0xFFFF).

    Returns:
        List of int values suitable for passing to the C extension.
    """
    result: List[int] = []
    for token in pattern_str.strip().split():
        token = token.strip()
        if token in ("??", "**", "XX", "xx"):
            result.append(_WILDCARD)
        else:
            try:
                result.append(int(token, 16))
            except ValueError:
                result.append(_WILDCARD)
    return result


def _make_c_pattern(pattern: Sequence[int]) -> ctypes.Array:
    """Convert a Python list of pattern values to a ctypes uint16 array."""
    ArrayType = ctypes.c_uint16 * len(pattern)
    return ArrayType(*pattern)


# ──────────────────────────────────────────────────────────────────────
# Public API
# ──────────────────────────────────────────────────────────────────────

class NativeAOBScanner:
    """
    High-performance AOB scanner backed by a C extension.

    Falls back to the pure-Python :class:`~src.memory.advanced.AOBScanner`
    when the native library is not available.
    """

    def __init__(self) -> None:
        self._lib = _load_library()

    @property
    def native_available(self) -> bool:
        """Whether the native C library is loaded."""
        return self._lib is not None

    # ── buffer-based scan ────────────────────────────────────────────

    def scan_buffer(
        self,
        data: bytes,
        pattern: str,
        base_address: int = 0,
        max_results: int = _MAX_RESULTS,
    ) -> List[int]:
        """
        Scan a byte buffer for an AOB pattern.

        Args:
            data:         The raw bytes to search.
            pattern:      AOB pattern string, e.g. ``"8B 0D ?? ?? ?? ?? 8B 01"``.
            base_address: Virtual address corresponding to *data[0]*.
            max_results:  Maximum number of matches to return.

        Returns:
            List of virtual addresses where the pattern was found.
        """
        parsed = parse_pattern(pattern)
        if not parsed or not data:
            return []

        if self._lib is not None:
            return self._scan_buffer_native(data, parsed, base_address, max_results)
        return self._scan_buffer_python(data, parsed, base_address, max_results)

    def _scan_buffer_native(
        self,
        data: bytes,
        pattern: List[int],
        base_address: int,
        max_results: int,
    ) -> List[int]:
        """Call the C ``aob_scan_buffer`` function."""
        assert self._lib is not None
        c_pattern = _make_c_pattern(pattern)
        out = (ctypes.c_uint64 * max_results)()

        count = self._lib.aob_scan_buffer(
            data,
            len(data),
            c_pattern,
            len(pattern),
            ctypes.c_uint64(base_address),
            out,
            max_results,
        )
        return [out[i] for i in range(max(count, 0))]

    @staticmethod
    def _scan_buffer_python(
        data: bytes,
        pattern: List[int],
        base_address: int,
        max_results: int,
    ) -> List[int]:
        """Pure-Python fallback for buffer scanning."""
        results: List[int] = []
        plen = len(pattern)
        limit = len(data) - plen + 1

        for i in range(limit):
            matched = True
            for j, expected in enumerate(pattern):
                if expected >= 256:  # wildcard
                    continue
                if data[i + j] != expected:
                    matched = False
                    break
            if matched:
                results.append(base_address + i)
                if len(results) >= max_results:
                    break
        return results

    # ── process-level scan (Linux only) ──────────────────────────────

    def scan_process(
        self,
        pid: int,
        pattern: str,
        start_address: int = 0x00400000,
        end_address: int = 0x7FFFFFFF,
        max_results: int = _MAX_RESULTS,
    ) -> List[int]:
        """
        Scan a remote process's memory for an AOB pattern (Linux only).

        Uses ``process_vm_readv(2)`` via the C extension for zero-copy reads.

        Args:
            pid:           Target process PID.
            pattern:       AOB pattern string.
            start_address: First virtual address to scan.
            end_address:   One-past-the-last address.
            max_results:   Maximum matches to return.

        Returns:
            List of matched virtual addresses.

        Raises:
            RuntimeError: If the native library is not available or not on
                          Linux.
        """
        parsed = parse_pattern(pattern)
        if not parsed:
            return []

        if self._lib is None:
            raise RuntimeError(
                "Native scanner library not available — cannot scan process memory"
            )

        if sys.platform != "linux" or not hasattr(self._lib, "aob_scan_process"):
            raise RuntimeError(
                "process_vm_readv scanning is only supported on Linux"
            )

        c_pattern = _make_c_pattern(parsed)
        out = (ctypes.c_uint64 * max_results)()

        count = self._lib.aob_scan_process(
            pid,
            c_pattern,
            len(parsed),
            ctypes.c_uint64(start_address),
            ctypes.c_uint64(end_address),
            out,
            max_results,
        )

        if count < 0:
            logger.error("aob_scan_process returned error code %d", count)
            return []

        return [out[i] for i in range(count)]
