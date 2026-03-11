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
from .advanced import (
    MemoryFreezer, FrozenAddress,
    PointerResolver, PointerChain,
    AOBScanner, AOBPattern,
    ChunkedScanner,
    VMTHooker, IATHooker, HookManager, HookChainEntry,
    LuaInjector,
)
)
from .signatures import SignatureDatabase, SignatureEntry, ChainEntry, PatternMetadata
from .speedhack import SpeedhackManager
from .teleport import TeleportManager, Coordinates, TeleportTarget
from .watchpoints import (
    WatchpointManager, ConditionalTriggerManager,
    MemoryWatchpoint, TriggerAction, ConditionType,
)
from .ml_predictor import MLPredictor
from .native_aob import NativeAOBScanner

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
    'VMTHooker',
    'IATHooker',
    'HookManager',
    'HookChainEntry',
    'LuaInjector',
    'SignatureDatabase',
    'SignatureEntry',
    'ChainEntry',
    'PatternMetadata',
    'SpeedhackManager',
    'TeleportManager',
    'Coordinates',
    'TeleportTarget',
    'VMTHooker',
    'IATHooker',
    'HookManager',
    'HookChainEntry',
    'WatchpointManager',
    'ConditionalTriggerManager',
    'MemoryWatchpoint',
    'TriggerAction',
    'ConditionType',
    'MLPredictor',
    'NativeAOBScanner',
]
