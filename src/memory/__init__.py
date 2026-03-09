"""
Memory scanning and editing module for Napoleon Total War.
Uses PyMemoryEditor for cross-platform memory access.
"""

from .process import ProcessManager
from .scanner import MemoryScanner, ScanType, ValueType
from .cheats import CheatManager, CheatType
from .backend import MemoryBackend, create_backend
from .advanced import (
    MemoryFreezer, FrozenAddress,
    PointerResolver, PointerChain,
    AOBScanner, AOBPattern,
    ChunkedScanner,
)

__all__ = [
    'ProcessManager',
    'MemoryScanner',
    'ScanType',
    'ValueType',
    'CheatManager',
    'CheatType',
    'MemoryBackend',
    'create_backend',
    'MemoryFreezer',
    'FrozenAddress',
    'PointerResolver',
    'PointerChain',
    'AOBScanner',
    'AOBPattern',
    'ChunkedScanner',
]
