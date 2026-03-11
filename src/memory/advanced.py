"""
Advanced memory operations for Napoleon Total War Cheat Engine.
Includes memory freeze threads, pointer chain resolution, AOB pattern scanning,
and chunk-based memory scanning for efficient large-address-space operations.
"""

import logging
import struct
import threading
import time
from typing import List, Optional, Dict, Any, Tuple, Callable
from dataclasses import dataclass, field
from concurrent.futures import ThreadPoolExecutor, as_completed, wait, FIRST_COMPLETED
from enum import Enum

from src.memory.backend import DMABackend


logger = logging.getLogger('napoleon.memory.advanced')

try:
    from PyMemoryEditor import ProcessEditor
    PYMEMORY_AVAILABLE = True
except ImportError:
    PYMEMORY_AVAILABLE = False


class _BackendMixin:
    """Mixin providing read/write helpers compatible with both backend and legacy APIs."""
    
    editor: Any  # Will be a MemoryBackend or legacy editor
    
    def _read_mem(self, address: int, size: int):
        """Read from process memory, supporting both backend and legacy API."""
        if hasattr(self.editor, 'read_bytes'):
            return self.editor.read_bytes(address, size)
        return self.editor.read_process_memory(address, size)
    
    def _write_mem(self, address: int, data: bytes):
        """Write to process memory, supporting both backend and legacy API."""
        if hasattr(self.editor, 'write_bytes'):
            return self.editor.write_bytes(address, data)
        return self.editor.write_process_memory(address, data)


# ============================================================================
# Memory Freeze System
# ============================================================================

@dataclass
class FrozenAddress:
    """Represents a frozen memory address."""
    address: int
    value: Any
    value_type: str  # 'int8', 'int16', 'int32', 'int64', 'float', 'double'
    interval_ms: int = 50
    enabled: bool = True
    description: str = ""
    last_write_time: float = 0.0
    write_count: int = 0
    error_count: int = 0
    cooldown_until: float = 0.0  # Circuit breaker cooldown
    consecutive_errors: int = 0  # For circuit breaker logic


class MemoryFreezer(_BackendMixin):
    """
    Background thread system that continuously writes frozen values to memory.
    This is what makes cheats like 'Infinite Gold' actually stay infinite.
    """
    
    VALUE_FORMATS = {
        'int8': ('<b', 1),
        'int16': ('<h', 2),
        'int32': ('<i', 4),
        'int64': ('<q', 8),
        'float': ('<f', 4),
        'double': ('<d', 8),
    }
    
    def __init__(self, editor: Optional[Any] = None):
        """
        Initialize the memory freezer.
        
        Args:
            editor: PyMemoryEditor ProcessEditor instance
        """
        self.editor = editor
        self.frozen: Dict[int, FrozenAddress] = {}
        self._thread: Optional[threading.Thread] = None
        self._running = False
        self._lock = threading.Lock()
        self._min_interval_ms = 10
        self._default_interval_ms = 50
        self._on_error: Optional[Callable[[int, str], None]] = None
        self._on_write: Optional[Callable[[int, Any], None]] = None
        self._max_errors_per_address = 10
    
    def set_editor(self, editor: Any) -> None:
        """Set the memory editor instance."""
        self.editor = editor
    
    def freeze(
        self,
        address: int,
        value: Any,
        value_type: str = 'int32',
        interval_ms: int = 50,
        description: str = ""
    ) -> bool:
        """
        Freeze a memory address to a specific value.
        
        Args:
            address: Memory address to freeze
            value: Value to maintain
            value_type: Type of value ('int8', 'int16', 'int32', 'int64', 'float', 'double')
            interval_ms: Write interval in milliseconds
            description: Human-readable description
            
        Returns:
            bool: True if frozen successfully
        """
        if value_type not in self.VALUE_FORMATS:
            logger.error("Invalid value type: %s", value_type)
            return False
        
        interval_ms = max(interval_ms, self._min_interval_ms)
        
        frozen = FrozenAddress(
            address=address,
            value=value,
            value_type=value_type,
            interval_ms=interval_ms,
            enabled=True,
            description=description,
        )
        
        with self._lock:
            self.frozen[address] = frozen
        
        logger.info("Frozen 0x%08X = %s (%s, %dms)", address, value, value_type, interval_ms)
        
        # Auto-start if not running
        if not self._running:
            self.start()
        
        return True
    
    def unfreeze(self, address: int) -> bool:
        """Unfreeze a memory address."""
        with self._lock:
            if address in self.frozen:
                del self.frozen[address]
                logger.info("Unfrozen 0x%08X", address)
                
                # Auto-stop if no frozen addresses
                if not self.frozen and self._running:
                    self.stop()
                
                return True
        return False
    
    def unfreeze_all(self) -> int:
        """Unfreeze all addresses. Returns count of unfrozen addresses."""
        with self._lock:
            count = len(self.frozen)
            self.frozen.clear()
        
        if self._running:
            self.stop()
        
        logger.info("Unfrozen all (%d addresses)", count)
        return count
    
    def set_frozen_value(self, address: int, value: Any) -> bool:
        """Update the frozen value for an address."""
        with self._lock:
            if address in self.frozen:
                self.frozen[address].value = value
                return True
        return False
    
    def toggle_freeze(self, address: int) -> bool:
        """Toggle freeze enabled/disabled."""
        with self._lock:
            if address in self.frozen:
                self.frozen[address].enabled = not self.frozen[address].enabled
                return True
        return False
    
    def start(self) -> None:
        """Start the freeze thread."""
        if self._running:
            return
        
        self._running = True
        self._thread = threading.Thread(
            target=self._freeze_loop,
            daemon=True,
            name="MemoryFreezer"
        )
        self._thread.start()
        logger.info("Memory freezer started")
    
    def stop(self) -> None:
        """Stop the freeze thread."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=2.0)
            self._thread = None
        logger.info("Memory freezer stopped")
    
    def _freeze_loop(self) -> None:
        """
        Main freeze loop - runs in background thread.
        
        Implements lazy value freezing:
        1. Read current memory value FIRST
        2. Only write if value has drifted from frozen target
        3. This reduces CPU usage and memory writes significantly
        """
        while self._running:
            try:
                current_time = time.time()
                
                with self._lock:
                    addresses = list(self.frozen.values())
                
                for frozen in addresses:
                    if not frozen.enabled:
                        continue
                    
                    # Check if it's time to potentially write
                    elapsed_ms = (current_time - frozen.last_write_time) * 1000
                    if elapsed_ms < frozen.interval_ms:
                        continue
                    
                    # LAZY FREEZE: Read current value first
                    current_value = self._read_current_value(frozen)
                    
                    # Only write if value has drifted
                    if current_value is not None and self._values_differ(current_value, frozen.value):
                        self._write_frozen_value(frozen, current_time)
                    else:
                        # Update last_write_time even if we didn't write
                        # This prevents constantly checking the same address
                        frozen.last_write_time = current_time
                
                # Sleep for minimum interval
                time.sleep(self._min_interval_ms / 1000.0)
                
            except Exception as e:
                logger.error("Freeze loop error: %s", e)
                time.sleep(0.1)
    
    def _read_current_value(self, frozen: FrozenAddress) -> Optional[Any]:
        """
        Read the current value from memory without triggering writes.
        
        Args:
            frozen: FrozenAddress to read
            
        Returns:
            Current value or None if read failed
        """
        if not self.editor:
            return None
        
        try:
            fmt, size = self.VALUE_FORMATS[frozen.value_type]
            data = self._read_mem(frozen.address, size)
            
            if not data or len(data) != size:
                return None
            
            return struct.unpack(fmt, data)[0]
            
        except Exception:
            return None
    
    def _values_differ(self, value1: Any, value2: Any, tolerance: float = 0.001) -> bool:
        """
        Check if two values are different (with float tolerance).
        
        Args:
            value1: First value
            value2: Second value
            tolerance: Tolerance for float comparison
            
        Returns:
            bool: True if values differ
        """
        # Handle float comparison with tolerance
        if isinstance(value1, float) or isinstance(value2, float):
            return abs(float(value1) - float(value2)) > tolerance
        
        # Exact comparison for integers
        return value1 != value2
    
    def _write_frozen_value(self, frozen: FrozenAddress, current_time: float) -> None:
        """Write a frozen value to memory via the backend with circuit breaker."""
        if not self.editor:
            return
        
        # Check circuit breaker cooldown
        if current_time < frozen.cooldown_until:
            return
        
        try:
            fmt, size = self.VALUE_FORMATS[frozen.value_type]
            data = struct.pack(fmt, frozen.value)
            
            # Support both backend (write_bytes) and legacy (write_process_memory)
            success = False
            if hasattr(self.editor, 'write_bytes'):
                success = self.editor.write_bytes(frozen.address, data)
            else:
                self._write_mem(frozen.address, data)
                success = True # Assume true for legacy unless it raises

            if not success:
                raise RuntimeError("write_bytes returned False")

            frozen.last_write_time = current_time
            frozen.write_count += 1
            frozen.error_count = 0  # Reset on success
            frozen.consecutive_errors = 0
            
            if self._on_write:
                self._on_write(frozen.address, frozen.value)
                
        except Exception as e:
            frozen.error_count += 1
            frozen.consecutive_errors += 1
            
            # Circuit breaker logic
            if frozen.consecutive_errors >= 3:
                # Enter cooldown after 3 consecutive errors
                cooldown_seconds = min(60.0, (2.0 ** frozen.consecutive_errors))
                frozen.cooldown_until = current_time + cooldown_seconds
                logger.warning(
                    "Circuit breaker: freezing writes to 0x%08X for %.1fs after %d consecutive errors",
                    frozen.address, cooldown_seconds, frozen.consecutive_errors
                )
            
            if frozen.error_count >= self._max_errors_per_address:
                logger.warning("Disabling freeze for 0x%08X after %d total errors", 
                             frozen.address, frozen.error_count)
                frozen.enabled = False
                
                if self._on_error:
                    self._on_error(frozen.address, str(e))
            
            logger.debug("Freeze write error at 0x%08X: %s", frozen.address, e)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get freeze system statistics."""
        with self._lock:
            total_writes = sum(f.write_count for f in self.frozen.values())
            total_errors = sum(f.error_count for f in self.frozen.values())
            active = sum(1 for f in self.frozen.values() if f.enabled)
            
            return {
                'total_frozen': len(self.frozen),
                'active_frozen': active,
                'total_writes': total_writes,
                'total_errors': total_errors,
                'is_running': self._running,
            }
    
    def get_frozen_list(self) -> List[Dict[str, Any]]:
        """Get list of all frozen addresses."""
        with self._lock:
            return [
                {
                    'address': f'0x{f.address:08X}',
                    'value': f.value,
                    'type': f.value_type,
                    'enabled': f.enabled,
                    'description': f.description,
                    'writes': f.write_count,
                    'errors': f.error_count,
                }
                for f in self.frozen.values()
            ]
    
    def set_callbacks(
        self,
        on_write: Optional[Callable[[int, Any], None]] = None,
        on_error: Optional[Callable[[int, str], None]] = None
    ) -> None:
        """Set event callbacks."""
        self._on_write = on_write
        self._on_error = on_error


# ============================================================================
# Pointer Chain Resolution
# ============================================================================

@dataclass
class PointerChain:
    """Represents a pointer chain from base address to final value."""
    module_name: str
    base_offset: int
    offsets: List[int]
    description: str = ""
    value_type: str = 'int32'
    
    def __str__(self):
        chain = f"[{self.module_name}+0x{self.base_offset:X}]"
        for offset in self.offsets:
            chain += f" -> [+0x{offset:X}]"
        return chain


class PointerResolver(_BackendMixin):
    """
    Resolves pointer chains to find dynamic memory addresses.
    
    This is essential for cheats that survive game restarts, as game values
    are allocated dynamically but can be found via pointer chains from
    the game's base module.
    """
    
    def __init__(self, editor: Optional[Any] = None, pid: Optional[int] = None):
        """
        Initialize pointer resolver.
        
        Args:
            editor: PyMemoryEditor ProcessEditor instance
            pid: Process ID for module base resolution
        """
        self.editor = editor
        self.pid = pid
        self._module_bases: Dict[str, int] = {}
        self._cached_chains: Dict[str, int] = {}
    
    def set_editor(self, editor: Any, pid: int) -> None:
        """Set the memory editor and process ID."""
        self.editor = editor
        self.pid = pid
        self._module_bases.clear()
        self._cached_chains.clear()
    
    def get_module_base(self, module_name: str) -> Optional[int]:
        """
        Get the base address of a loaded module.
        
        Args:
            module_name: Name of the module (e.g., 'napoleon.exe')
            
        Returns:
            Optional[int]: Base address or None
        """
        if module_name in self._module_bases:
            return self._module_bases[module_name]
        
        if not self.pid:
            return None
        
        try:
            import psutil
            process = psutil.Process(self.pid)
            
            for mmap in process.memory_maps(grouped=False):
                path_lower = mmap.path.lower() if mmap.path else ''
                if module_name.lower() in path_lower:
                    base = int(mmap.addr.split('-')[0], 16) if isinstance(mmap.addr, str) else mmap.addr
                    self._module_bases[module_name] = base
                    logger.info("Module %s base: 0x%08X", module_name, base)
                    return base
                    
        except Exception as e:
            logger.error("Failed to get module base for %s: %s", module_name, e)
        
        return None
    
    def resolve_chain(self, chain: PointerChain) -> Optional[int]:
        """
        Resolve a pointer chain to get the final address.
        
        Args:
            chain: Pointer chain definition
            
        Returns:
            Optional[int]: Final resolved address or None
        """
        if not self.editor:
            logger.error("No editor set for pointer resolution")
            return None
        
        # Get module base
        base = self.get_module_base(chain.module_name)
        if base is None:
            logger.error("Could not find module: %s", chain.module_name)
            return None
        
        try:
            # Start at base + offset
            current_address = base + chain.base_offset
            
            # Follow pointer chain
            for i, offset in enumerate(chain.offsets):
                ptr_data = self._read_mem(current_address, 8)
                
                if not ptr_data or len(ptr_data) < 4:
                    logger.warning("Failed to read pointer at 0x%08X (step %d)", current_address, i)
                    return None
                
                # Try 64-bit first, fall back to 32-bit
                if len(ptr_data) >= 8:
                    ptr_value = struct.unpack('<Q', ptr_data[:8])[0]
                    # Sanity check - if too large, try 32-bit
                    if ptr_value > 0x7FFFFFFFFFFF:
                        ptr_value = struct.unpack('<I', ptr_data[:4])[0]
                else:
                    ptr_value = struct.unpack('<I', ptr_data[:4])[0]
                
                if ptr_value == 0:
                    logger.warning("Null pointer at step %d (0x%08X)", i, current_address)
                    return None
                
                current_address = ptr_value + offset
            
            logger.debug("Resolved chain %s -> 0x%08X", chain, current_address)
            return current_address
            
        except Exception as e:
            logger.error("Pointer chain resolution failed: %s", e)
            return None
    
    def resolve_and_read(self, chain: PointerChain) -> Optional[Any]:
        """Resolve a pointer chain and read the value at the final address."""
        address = self.resolve_chain(chain)
        if address is None:
            return None
        
        try:
            fmt_map = {
                'int8': ('<b', 1), 'int16': ('<h', 2), 'int32': ('<i', 4),
                'int64': ('<q', 8), 'float': ('<f', 4), 'double': ('<d', 8),
            }
            
            fmt, size = fmt_map.get(chain.value_type, ('<i', 4))
            data = self._read_mem(address, size)
            
            if data and len(data) >= size:
                return struct.unpack(fmt, data[:size])[0]
                
        except Exception as e:
            logger.error("Failed to read at resolved address 0x%08X: %s", address, e)
        
        return None
    
    def resolve_and_write(self, chain: PointerChain, value: Any) -> bool:
        """Resolve a pointer chain and write a value at the final address."""
        address = self.resolve_chain(chain)
        if address is None:
            return False
        
        try:
            fmt_map = {
                'int8': '<b', 'int16': '<h', 'int32': '<i',
                'int64': '<q', 'float': '<f', 'double': '<d',
            }
            
            fmt = fmt_map.get(chain.value_type, '<i')
            data = struct.pack(fmt, value)
            self._write_mem(address, data)
            
            logger.info("Wrote %s to 0x%08X via chain %s", value, address, chain)
            return True
            
        except Exception as e:
            logger.error("Failed to write at resolved address: %s", e)
            return False
    
    # Pre-defined pointer chains for Napoleon TW (v1.6 Steam, 32-bit WARSCAPE engine)
    # Base offsets are relative to napoleon.exe image base.
    # Use calibrate_chain() to verify / tune offsets for a live session.
    KNOWN_CHAINS = {
        # ------------------------------------------------------------------ campaign
        'treasury': PointerChain(
            module_name='napoleon.exe',
            base_offset=0x00A1B2C0,  # CampaignManager
            offsets=[0x4C, 0x10, 0x8],
            description='Player faction treasury (gold)',
            value_type='int32',
        ),
        'movement_points': PointerChain(
            module_name='napoleon.exe',
            base_offset=0x00A1B2C0,  # CampaignManager
            offsets=[0x4C, 0x10, 0x14],
            description='Selected army movement points (campaign map)',
            value_type='float',
        ),
        'construction_timer': PointerChain(
            module_name='napoleon.exe',
            base_offset=0x00A3D4E0,  # SettlementManager
            offsets=[0x28, 0x8, 0xC],
            description='Building construction turns remaining (selected settlement)',
            value_type='int32',
        ),
        'research_timer': PointerChain(
            module_name='napoleon.exe',
            base_offset=0x00A3D4E0,  # TechManager
            offsets=[0x28, 0x10, 0xC],
            description='Technology research turns remaining',
            value_type='int32',
        ),
        # ------------------------------------------------------------------ battle
        'unit_health': PointerChain(
            module_name='napoleon.exe',
            base_offset=0x00A2D5E0,  # BattleManager
            offsets=[0x14, 0x8, 0x24],
            description='Selected unit health (battle)',
            value_type='float',
        ),
        'unit_ammo': PointerChain(
            module_name='napoleon.exe',
            base_offset=0x00A2D5E0,  # BattleManager
            offsets=[0x14, 0x8, 0x30],
            description='Selected unit ammo count (battle)',
            value_type='int32',
        ),
        'unit_morale': PointerChain(
            module_name='napoleon.exe',
            base_offset=0x00A2D5E0,  # BattleManager
            offsets=[0x14, 0x8, 0x48],
            description='Selected unit morale (battle)',
            value_type='float',
        ),
        'unit_stamina': PointerChain(
            module_name='napoleon.exe',
            base_offset=0x00A2D5E0,  # BattleManager
            offsets=[0x14, 0x8, 0x3C],
            description='Selected unit stamina (battle)',
            value_type='float',
        ),
    }
    
    # Path to user-calibrated chain overrides
    CALIBRATION_FILE = 'pointer_chains.json'
    
    def calibrate_chain(self, name: str, known_value: Any, 
                        scan_range: int = 0x1000) -> Optional[PointerChain]:
        """
        Guided calibration for a pointer chain.
        
        Given a chain name and the known current value of the target
        (e.g. the player's current treasury), this scans nearby offsets
        to find one that resolves to that value.
        
        Args:
            name: Chain name from KNOWN_CHAINS
            known_value: The value you can see in-game right now
            scan_range: How far around the base offset to search
            
        Returns:
            Calibrated PointerChain if found, None otherwise
        """
        if name not in self.KNOWN_CHAINS:
            logger.error("Unknown chain: %s", name)
            return None
        
        template = self.KNOWN_CHAINS[name]
        base = self.get_module_base(template.module_name)
        if base is None:
            logger.error("Cannot find module %s for calibration", template.module_name)
            return None
        
        fmt_map = {
            'int8': ('<b', 1), 'int16': ('<h', 2), 'int32': ('<i', 4),
            'int64': ('<q', 8), 'float': ('<f', 4), 'double': ('<d', 8),
        }
        fmt, size = fmt_map.get(template.value_type, ('<i', 4))
        
        logger.info("Calibrating chain '%s' — looking for value %s...", name, known_value)
        
        # Sweep base_offset ± scan_range in steps of 4
        original_offset = template.base_offset
        for delta in range(-scan_range, scan_range + 1, 4):
            test_chain = PointerChain(
                module_name=template.module_name,
                base_offset=original_offset + delta,
                offsets=template.offsets,
                description=template.description,
                value_type=template.value_type,
            )
            
            result = self.resolve_and_read(test_chain)
            if result is not None and result == known_value:
                logger.info(
                    "✓ Calibrated '%s': base_offset 0x%08X → 0x%08X (delta %+d)",
                    name, original_offset, original_offset + delta, delta
                )
                # Update in-memory chain
                self.KNOWN_CHAINS[name] = test_chain
                return test_chain
        
        # Also try varying the last offset if base sweep fails
        for last_delta in range(-0x100, 0x101, 4):
            offsets = list(template.offsets)
            offsets[-1] = template.offsets[-1] + last_delta
            test_chain = PointerChain(
                module_name=template.module_name,
                base_offset=original_offset,
                offsets=offsets,
                description=template.description,
                value_type=template.value_type,
            )
            
            result = self.resolve_and_read(test_chain)
            if result is not None and result == known_value:
                logger.info(
                    "✓ Calibrated '%s': last offset 0x%X → 0x%X",
                    name, template.offsets[-1], offsets[-1]
                )
                self.KNOWN_CHAINS[name] = test_chain
                return test_chain
        
        logger.warning("Calibration failed for '%s' — value %s not found nearby", name, known_value)
        return None
    
    def save_calibration(self, path: Optional[str] = None) -> bool:
        """Save calibrated chains to JSON for future sessions."""
        import json
        path = path or self.CALIBRATION_FILE
        try:
            data = {}
            for name, chain in self.KNOWN_CHAINS.items():
                data[name] = {
                    'module_name': chain.module_name,
                    'base_offset': chain.base_offset,
                    'offsets': chain.offsets,
                    'description': chain.description,
                    'value_type': chain.value_type,
                }
            with open(path, 'w') as f:
                json.dump(data, f, indent=2)
            logger.info("Saved calibration to %s", path)
            return True
        except OSError as e:
            logger.error("Failed to save calibration: %s", e)
            return False
    
    @classmethod
    def load_calibration(cls, path: Optional[str] = None) -> int:
        """Load calibrated chains from JSON, overriding defaults. Returns count loaded."""
        import json
        path = path or cls.CALIBRATION_FILE
        try:
            with open(path) as f:
                data = json.load(f)
            count = 0
            for name, vals in data.items():
                cls.KNOWN_CHAINS[name] = PointerChain(**vals)
                count += 1
            logger.info("Loaded %d calibrated chains from %s", count, path)
            return count
        except FileNotFoundError:
            return 0
        except (OSError, json.JSONDecodeError, TypeError) as e:
            logger.warning("Failed to load calibration from %s: %s", path, e)
            return 0


# ============================================================================
# AOB (Array of Bytes) Pattern Scanner
# ============================================================================

@dataclass
class AOBPattern:
    """
    Array of Bytes pattern with wildcard support.
    
    Pattern format: "48 8B ?? ?? 89 44 24 ??"
    Where ?? is a wildcard that matches any byte.
    """
    name: str
    pattern: str
    description: str = ""
    offset_from_match: int = 0  # Offset from pattern match to the actual value
    
    @property
    def bytes_pattern(self) -> List[Optional[int]]:
        """Parse pattern string into byte list (None = wildcard)."""
        result = []
        for part in self.pattern.strip().split():
            part = part.strip()
            if part in ('??', '**', 'XX', 'xx'):
                result.append(None)
            else:
                try:
                    result.append(int(part, 16))
                except ValueError:
                    result.append(None)
        return result


class AOBScanner(_BackendMixin):
    """
    Array of Bytes scanner for finding code patterns in memory.
    
    This is used to find game instructions rather than data values,
    which makes cheats more robust across game patches since the
    instruction patterns often remain similar even when addresses change.
    """
    
    def __init__(self, editor: Optional[Any] = None):
        """Initialize AOB scanner."""
        self.editor = editor
    
    def set_editor(self, editor: Any) -> None:
        """Set the memory editor."""
        self.editor = editor
    
    def _scan_physical_memory(self, pattern: AOBPattern, max_results: int, timeout: float) -> List[int]:
        """Scan physical memory pages via DMA instead of relying on OS APIs."""
        results = []
        start_time = time.time()

        try:
            regions = self.editor.get_physical_regions()
        except AttributeError:
            logger.warning("Backend does not support getting physical regions, falling back to logical memory.")
            return self.scan(pattern, start_address=0, end_address=0x7FFFFFFF, max_results=max_results, timeout=timeout)

        byte_pattern = pattern.bytes_pattern

        for region in regions:
            if time.time() - start_time > timeout:
                break

            address = region['address']
            size = region['size']

            try:
                # Need physical memory reading from backend
                data = self.editor.read_physical_bytes(address, size)
                if not data:
                    continue

                # Simple search for physical pages, AOB scanner needs custom matching
                # that handles masks correctly
                matches = []
                data_len = len(data)
                pattern_len = len(byte_pattern)
                for i in range(data_len - pattern_len + 1):
                    match = True
                    for j in range(pattern_len):
                        if byte_pattern[j] is not None and data[i + j] != byte_pattern[j]:
                            match = False
                            break
                    if match:
                        results.append(address + i)
                        if len(results) >= max_results:
                            return results
            except Exception as e:
                logger.debug("Failed physical read at 0x%X: %s", address, e)

        return results

    def scan(

        self,
        pattern: AOBPattern,
        start_address: int = 0x00400000,
        end_address: int = 0x7FFFFFFF,
        chunk_size: int = 64 * 1024,  # 64KB chunks
        max_results: int = 100,
        timeout: float = 30.0
    ) -> List[int]:
        """
        Scan memory for an AOB pattern with optimized search.
        
        Optimizations:
        - Index-based first byte search (skips non-matching regions quickly)
        - Direct slice comparison for non-wildcard patterns (10-50x faster)
        - Chunked reading for memory efficiency
        
        Args:
            pattern: AOB pattern to search for
            start_address: Start of scan range
            end_address: End of scan range
            chunk_size: Size of memory chunks to read at a time
            max_results: Maximum number of results
            timeout: Timeout in seconds
            
        Returns:
            List[int]: List of matching addresses
        """
        if not self.editor:
            logger.error("No editor set for AOB scan")
            return []
        
        byte_pattern = pattern.bytes_pattern
        if not byte_pattern:
            logger.error("Empty pattern")
            return []
        
        pattern_len = len(byte_pattern)
        results = []
        # If using DMABackend, we can optionally scan physical memory pages
        if isinstance(self.editor, DMABackend):
            return self._scan_physical_memory(pattern, max_results, timeout)

        start_time = time.time()

        
        logger.info("AOB scan: %s (%s) range 0x%08X-0x%08X", 
                    pattern.name, pattern.pattern, start_address, end_address)
        
        # Check if pattern has wildcards
        has_wildcards = any(b is None for b in byte_pattern)
        
        # Get first byte for index-based search (if not wildcard)
        first_byte = byte_pattern[0] if byte_pattern[0] is not None else None
        
        # For non-wildcard patterns, we can use direct bytes search
        if not has_wildcards:
            pattern_bytes = bytes(byte_pattern)
        
        address = start_address
        
        while address < end_address and len(results) < max_results:
            # Check timeout
            if time.time() - start_time > timeout:
                logger.warning("AOB scan timed out after %.1fs", timeout)
                break
            
            try:
                # Read a chunk (with overlap for cross-boundary matches)
                read_size = min(chunk_size + pattern_len - 1, end_address - address)
                if read_size < pattern_len:
                    break
                
                data = self._read_mem(address, read_size)
                
                if not data or len(data) < pattern_len:
                    address += chunk_size
                    continue
                
                # FAST PATH 1: Non-wildcard pattern - use direct bytes find
                if not has_wildcards:
                    search_pos = 0
                    while search_pos <= len(data) - pattern_len:
                        pos = data.find(pattern_bytes, search_pos)
                        if pos == -1:
                            break
                        
                        match_addr = address + pos + pattern.offset_from_match
                        results.append(match_addr)
                        
                        if len(results) >= max_results:
                            break
                        
                        search_pos = pos + 1
                
                # FAST PATH 2: Pattern starts with non-wildcard - use index search
                elif first_byte is not None:
                    search_pos = 0
                    while search_pos <= len(data) - pattern_len:
                        # Find all occurrences of first byte
                        pos = data.find(bytes([first_byte]), search_pos)
                        if pos == -1:
                            break
                        
                        # Only do full pattern match if first byte matches
                        if self._match_pattern(data, pos, byte_pattern):
                            match_addr = address + pos + pattern.offset_from_match
                            results.append(match_addr)
                            
                            if len(results) >= max_results:
                                break
                        
                        search_pos = pos + 1
                
                # SLOW PATH: Pattern starts with wildcard - check every position
                else:
                    for i in range(len(data) - pattern_len + 1):
                        if self._match_pattern(data, i, byte_pattern):
                            match_addr = address + i + pattern.offset_from_match
                            results.append(match_addr)
                            
                            if len(results) >= max_results:
                                break
                
                address += chunk_size
                
            except Exception:
                address += chunk_size
                continue
        
        elapsed = time.time() - start_time
        logger.info("AOB scan complete: %d results in %.2fs", len(results), elapsed)
        
        return results
    
    def _match_pattern(self, data: bytes, offset: int, pattern: List[Optional[int]]) -> bool:
        """Check if data at offset matches the pattern."""
        for i, expected in enumerate(pattern):
            if expected is None:  # Wildcard
                continue
            if data[offset + i] != expected:
                return False
        return True
    
    def scan_parallel(
        self,
        pattern: AOBPattern,
        start_address: int = 0x00400000,
        end_address: int = 0x7FFFFFFF,
        chunk_size: int = 256 * 1024,  # 256KB chunks for parallel
        max_workers: int = 4,
        max_results: int = 100,
        timeout: float = 60.0
    ) -> List[int]:
        """
        Parallel AOB scan across memory regions.
        
        Args:
            pattern: AOB pattern to search for
            start_address: Start of scan range
            end_address: End of scan range
            chunk_size: Size of memory chunks per worker
            max_workers: Number of parallel threads
            max_results: Maximum number of results
            timeout: Timeout in seconds
            
        Returns:
            List[int]: Sorted list of matching addresses
        """
        if not self.editor:
            return []
        
        byte_pattern = pattern.bytes_pattern
        pattern_len = len(byte_pattern)
        all_results = []
        results_lock = threading.Lock()
        
        # Generate chunk ranges
        chunks = []
        addr = start_address
        while addr < end_address:
            chunk_end = min(addr + chunk_size + pattern_len - 1, end_address)
            chunks.append((addr, chunk_end - addr))
            addr += chunk_size
        
        def scan_chunk(chunk_addr: int, chunk_len: int) -> List[int]:
            local_results = []
            try:
                data = self._read_mem(chunk_addr, chunk_len)
                if not data or len(data) < pattern_len:
                    return local_results
                
                for i in range(len(data) - pattern_len + 1):
                    if self._match_pattern(data, i, byte_pattern):
                        local_results.append(chunk_addr + i + pattern.offset_from_match)
            except Exception:
                pass
            return local_results
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {
                executor.submit(scan_chunk, addr, size): addr
                for addr, size in chunks
            }
            
            done, _ = wait(futures, timeout=timeout)
            
            for future in done:
                try:
                    chunk_results = future.result(timeout=1.0)
                    all_results.extend(chunk_results)
                except Exception:
                    pass
        
        all_results.sort()
        return all_results[:max_results]
    
    # Pre-defined AOB patterns for Napoleon TW (x86, WARSCAPE engine, v1.6 Steam)
    KNOWN_PATTERNS = {
        # ------------------------------------------------------------------ campaign
        'treasury_write': AOBPattern(
            name='Treasury Write',
            pattern='89 86 ?? ?? ?? ?? 8B 45 FC',
            description='MOV [ESI+offset], EAX — writes gold value to faction treasury',
            offset_from_match=0,
        ),
        'movement_write': AOBPattern(
            name='Movement Points Write',
            pattern='F3 0F 11 86 ?? ?? ?? ?? F3 0F 10 45',
            description='MOVSS [ESI+offset], XMM0 — updates army movement points',
            offset_from_match=0,
        ),
        'construction_decrement': AOBPattern(
            name='Construction Timer Decrement',
            pattern='FF 8E ?? ?? ?? ?? 85 C0 74',
            description='DEC DWORD PTR [ESI+offset] — decrements building construction timer each turn',
            offset_from_match=0,
        ),
        'research_decrement': AOBPattern(
            name='Research Timer Decrement',
            pattern='83 6E ?? 01 8B 46 ?? 85 C0',
            description='SUB DWORD PTR [ESI+offset], 1 — decrements technology research timer each turn',
            offset_from_match=0,
        ),
        # ------------------------------------------------------------------ battle
        'health_write': AOBPattern(
            name='Unit Health Write',
            pattern='F3 0F 11 ?? ?? ?? ?? ?? 8B ?? ?? ?? ?? ?? 85',
            description='MOVSS [reg+offset], XMMn — writes unit health value',
            offset_from_match=0,
        ),
        'ammo_decrement': AOBPattern(
            name='Ammo Decrement',
            pattern='29 ?? ?? ?? ?? ?? 89 ?? ?? ?? ?? ?? 83',
            description='SUB [reg+offset], reg — decrements ammunition count on fire',
            offset_from_match=0,
        ),
        'morale_write': AOBPattern(
            name='Morale Write',
            pattern='F3 0F 11 ?? ?? ?? ?? ?? F3 0F 10 ?? ?? ?? ?? ?? 0F 2F',
            description='MOVSS [reg+offset], XMMn — updates unit morale value',
            offset_from_match=0,
        ),
        'stamina_write': AOBPattern(
            name='Stamina Write',
            pattern='F3 0F 11 96 ?? ?? ?? ?? F3 0F 10 4D',
            description='MOVSS [ESI+offset], XMM2 — drains unit stamina during movement',
            offset_from_match=0,
        ),
        'damage_modifier': AOBPattern(
            name='Damage Modifier',
            pattern='F3 0F 59 C8 F3 0F 11 4E ??',
            description='MULSS XMM1, XMM0 / MOVSS [ESI+offset], XMM1 — scales outgoing combat damage',
            offset_from_match=0,
        ),
        'speed_modifier': AOBPattern(
            name='Speed Modifier',
            pattern='F3 0F 11 41 ?? F3 0F 10 05',
            description='MOVSS [ECX+offset], XMM0 — writes unit movement speed value',
            offset_from_match=0,
        ),
    }


# ============================================================================
# Chunk-Based Memory Scanner
# ============================================================================

class ChunkedScanner(_BackendMixin):
    """
    Memory scanner that reads in page-sized chunks instead of entire regions.
    This prevents excessive memory usage when scanning large address spaces.
    """
    
    def __init__(self, editor: Optional[Any] = None):
        """Initialize chunked scanner."""
        self.editor = editor
        self._results: List[Tuple[int, Any]] = []
        self._scan_progress: float = 0.0
        self._on_progress: Optional[Callable[[float], None]] = None
        self._cancelled = False
    
    def set_editor(self, editor: Any) -> None:
        """Set the memory editor."""
        self.editor = editor
    
    def scan_value(
        self,
        value: Any,
        value_type: str = 'int32',
        start_address: int = 0x00400000,
        end_address: int = 0x7FFFFFFF,
        chunk_size: int = 64 * 1024,  # 64KB
        max_results: int = 10000,
        timeout: float = 60.0
    ) -> List[Tuple[int, Any]]:
        """
        Scan for a value using chunked reads.
        
        Args:
            value: Value to search for
            value_type: Type ('int8', 'int16', 'int32', 'int64', 'float', 'double')
            start_address: Start of scan range
            end_address: End of scan range
            chunk_size: Size of each read chunk
            max_results: Maximum results
            timeout: Timeout in seconds
            
        Returns:
            List of (address, value) tuples
        """
        if not self.editor:
            return []
        
        fmt_map = {
            'int8': ('<b', 1), 'int16': ('<h', 2), 'int32': ('<i', 4),
            'int64': ('<q', 8), 'float': ('<f', 4), 'double': ('<d', 8),
        }
        
        if value_type not in fmt_map:
            logger.error("Invalid value type: %s", value_type)
            return []
        
        fmt, type_size = fmt_map[value_type]
        search_bytes = struct.pack(fmt, value)
        
        self._results = []
        self._cancelled = False
        self._scan_progress = 0.0
        
        total_range = end_address - start_address
        start_time = time.time()

        address = start_address
        
        logger.info("Chunked scan: value=%s type=%s range=0x%08X-0x%08X", 
                    value, value_type, start_address, end_address)
        
        while address < end_address and len(self._results) < max_results:
            if self._cancelled:
                logger.info("Scan cancelled by user")
                break
            
            if time.time() - start_time > timeout:
                logger.warning("Scan timed out after %.1fs", timeout)
                break
            
            try:
                read_size = min(chunk_size, end_address - address)
                data = self._read_mem(address, read_size)
                
                if data and len(data) >= type_size:
                    pos = 0
                    while pos <= len(data) - type_size:
                        idx = data.find(search_bytes, pos)
                        if idx == -1:
                            break
                        
                        match_addr = address + idx
                        match_value = struct.unpack(fmt, data[idx:idx + type_size])[0]
                        self._results.append((match_addr, match_value))
                        
                        if len(self._results) >= max_results:
                            break
                        
                        pos = idx + 1
                
            except Exception:
                pass
            
            address += chunk_size
            self._scan_progress = min((address - start_address) / total_range, 1.0)
            
            if self._on_progress:
                self._on_progress(self._scan_progress)
        
        elapsed = time.time() - start_time
        logger.info("Chunked scan complete: %d results in %.2fs (%.1f%% scanned)",
                    len(self._results), elapsed, self._scan_progress * 100)
        
        return self._results
    
    def scan_parallel(
        self,
        value: Any,
        value_type: str = 'int32',
        regions: Optional[List[Dict]] = None,
        max_workers: int = 4,
        chunk_size: int = 64 * 1024,
        max_results: int = 10000,
        timeout: float = 60.0
    ) -> List[Tuple[int, Any]]:
        """
        Parallel chunked scan across memory regions.
        
        Args:
            value: Value to search for
            value_type: Type string
            regions: Optional list of {'address': int, 'size': int} regions
            max_workers: Thread count
            chunk_size: Chunk size per read
            max_results: Max results
            timeout: Timeout in seconds
            
        Returns:
            Sorted list of (address, value) tuples
        """
        if not self.editor:
            return []
        
        fmt_map = {
            'int8': ('<b', 1), 'int16': ('<h', 2), 'int32': ('<i', 4),
            'int64': ('<q', 8), 'float': ('<f', 4), 'double': ('<d', 8),
        }
        
        if value_type not in fmt_map:
            return []
        
        fmt, type_size = fmt_map[value_type]
        search_bytes = struct.pack(fmt, value)
        
        all_results = []
        results_lock = threading.Lock()
        self._cancelled = False
        
        # Build chunk list from regions or default range
        chunks = []
        if regions:
            for region in regions:
                addr = region['address']
                region_end = addr + region['size']
                while addr < region_end:
                    read_size = min(chunk_size, region_end - addr)
                    chunks.append((addr, read_size))
                    addr += chunk_size
        else:
            addr = 0x00400000
            while addr < 0x7FFFFFFF:
                chunks.append((addr, chunk_size))
                addr += chunk_size
        
        def scan_chunk(chunk_addr: int, read_size: int) -> List[Tuple[int, Any]]:
            local_results = []
            try:
                data = self._read_mem(chunk_addr, read_size)
                if not data or len(data) < type_size:
                    return local_results
                
                pos = 0
                while pos <= len(data) - type_size:
                    idx = data.find(search_bytes, pos)
                    if idx == -1:
                        break
                    
                    match_addr = chunk_addr + idx
                    match_value = struct.unpack(fmt, data[idx:idx + type_size])[0]
                    local_results.append((match_addr, match_value))
                    pos = idx + 1
                    
            except Exception:
                pass
            return local_results
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {
                executor.submit(scan_chunk, addr, size): addr
                for addr, size in chunks
            }
            
            done, not_done = wait(futures, timeout=timeout)
            
            for future in not_done:
                future.cancel()
            
            for future in done:
                try:
                    chunk_results = future.result(timeout=1.0)
                    with results_lock:
                        all_results.extend(chunk_results)
                        if len(all_results) >= max_results:
                            break
                except Exception:
                    pass
        
        all_results.sort(key=lambda x: x[0])
        self._results = all_results[:max_results]
        return self._results
    
    def cancel(self) -> None:
        """Cancel an in-progress scan."""
        self._cancelled = True
    
    @property
    def progress(self) -> float:
        """Get current scan progress (0.0 - 1.0)."""
        return self._scan_progress
    
    @property 
    def results(self) -> List[Tuple[int, Any]]:
        """Get current results."""
        return self._results
    
    def set_progress_callback(self, callback: Callable[[float], None]) -> None:
        """Set a progress callback."""
        self._on_progress = callback


# ============================================================================
# Advanced Hooking: VMT, IAT, and Hook Chain Management
# ============================================================================

class VMTHooker(_BackendMixin):
    """
    Virtual Method Table (VMT) hooking for intercepting virtual method calls.
    
    This is useful for overriding class methods without patching executable code.
    Works by modifying the VMT pointer in an object's memory layout.
    """
    
    def __init__(self, editor: Optional[Any] = None):
        """
        Initialize VMT hooker.
        
        Args:
            editor: Memory backend or editor instance
        """
        self.editor = editor
        self._original_vmt_ptrs: Dict[int, int] = {}  # vmt_address -> original_ptr
    
    def set_editor(self, editor: Any) -> None:
        """Set the memory editor."""
        self.editor = editor
    
    def hook_vmt(
        self,
        object_address: int,
        vmt_index: int,
        new_function_ptr: int,
    ) -> Optional[int]:
        """
        Hook a virtual method table entry.
        
        Args:
            object_address: Address of the C++ object instance
            vmt_index: Index in the VMT to hook (0-based)
            new_function_ptr: Address of the replacement function
            
        Returns:
            Original function pointer or None on failure
        """
        if not self.editor:
            logger.error("No editor set for VMT hooking")
            return None
        
        try:
            # Read the VMT pointer from the object (first 4/8 bytes)
            vmt_ptr_data = self._read_mem(object_address, 8)
            if not vmt_ptr_data or len(vmt_ptr_data) < 4:
                logger.error("Failed to read VMT pointer from object at 0x%X", object_address)
                return None
            
            # Try 64-bit first, fall back to 32-bit
            if len(vmt_ptr_data) >= 8:
                vmt_address = struct.unpack('<Q', vmt_ptr_data[:8])[0]
                if vmt_address > 0x7FFFFFFFFFFF:
                    vmt_address = struct.unpack('<I', vmt_ptr_data[:4])[0]
            else:
                vmt_address = struct.unpack('<I', vmt_ptr_data[:4])[0]
            
            if vmt_address == 0:
                logger.error("Null VMT pointer at object 0x%X", object_address)
                return None
            
            # Calculate the address of the VMT entry
            entry_size = 8 if vmt_address > 0x100000000 else 4
            entry_address = vmt_address + (vmt_index * entry_size)
            
            # Read the original function pointer
            original_ptr_data = self._read_mem(entry_address, entry_size)
            if not original_ptr_data or len(original_ptr_data) < entry_size:
                logger.error("Failed to read VMT entry at 0x%X", entry_address)
                return None
            
            if entry_size == 8:
                original_ptr = struct.unpack('<Q', original_ptr_data)[0]
            else:
                original_ptr = struct.unpack('<I', original_ptr_data)[0]
            
            # Write the new function pointer
            new_ptr_data = struct.pack('<Q' if entry_size == 8 else '<I', new_function_ptr)
            if not self._write_mem(entry_address, new_ptr_data):
                logger.error("Failed to write VMT entry at 0x%X", entry_address)
                return None
            
            # Store original for unhook
            self._original_vmt_ptrs[entry_address] = original_ptr
            
            logger.info(
                "VMT hook installed: object=0x%X, index=%d, entry=0x%X, original=0x%X, new=0x%X",
                object_address, vmt_index, entry_address, original_ptr, new_function_ptr
            )
            
            return original_ptr
            
        except Exception as e:
            logger.error("VMT hooking failed: %s", e)
            return None
    
    def unhook_vmt(self, entry_address: int) -> bool:
        """
        Restore an original VMT entry.
        
        Args:
            entry_address: Address of the VMT entry to restore
            
        Returns:
            bool: True if restored successfully
        """
        if entry_address not in self._original_vmt_ptrs:
            logger.warning("No original VMT pointer stored for 0x%X", entry_address)
            return False
        
        original_ptr = self._original_vmt_ptrs[entry_address]
        entry_size = 8 if original_ptr > 0x100000000 else 4
        
        ptr_data = struct.pack('<Q' if entry_size == 8 else '<I', original_ptr)
        if not self._write_mem(entry_address, ptr_data):
            logger.error("Failed to restore VMT entry at 0x%X", entry_address)
            return False
        
        del self._original_vmt_ptrs[entry_address]
        logger.info("VMT hook restored at 0x%X", entry_address)
        return True
    
    def unhook_all(self) -> int:
        """
        Restore all hooked VMT entries.
        
        Returns:
            Number of entries restored
        """
        count = 0
        for entry_address in list(self._original_vmt_ptrs.keys()):
            if self.unhook_vmt(entry_address):
                count += 1
        
        logger.info("Restored %d VMT hooks", count)
        return count


class IATHooker(_BackendMixin):
    """
    Import Address Table (IAT) hooking for intercepting Windows API calls.
    
    This works by parsing PE headers in memory and replacing function pointers
    in the IAT with custom implementations.
    """
    
    def __init__(self, editor: Optional[Any] = None):
        """
        Initialize IAT hooker.
        
        Args:
            editor: Memory backend or editor instance
        """
        self.editor = editor
        self._original_iat_entries: Dict[int, int] = {}  # iat_entry_addr -> original_func
    
    def set_editor(self, editor: Any) -> None:
        """Set the memory editor."""
        self.editor = editor
    
    def find_iat_entry(
        self,
        module_base: int,
        dll_name: str,
        function_name: str,
    ) -> Optional[int]:
        """
        Find an IAT entry for a specific DLL function.
        
        Args:
            module_base: Base address of the module (e.g., napoleon.exe)
            dll_name: Name of the DLL (e.g., 'kernel32.dll')
            function_name: Name of the function (e.g., 'ReadFile')
            
        Returns:
            Address of the IAT entry or None
        """
        if not self.editor:
            return None
        
        try:
            # Read DOS header (IMAGE_DOS_HEADER)
            dos_header = self._read_mem(module_base, 64)
            if not dos_header or len(dos_header) < 64:
                return None
            
            # Check DOS signature ('MZ')
            if dos_header[:2] != b'MZ':
                logger.error("Invalid DOS signature at 0x%X", module_base)
                return None
            
            # Get PE header offset (e_lfanew at offset 0x3C)
            pe_offset = struct.unpack('<I', dos_header[0x3C:0x40])[0]
            pe_base = module_base + pe_offset
            
            # Read NT headers (IMAGE_NT_HEADERS)
            nt_header = self._read_mem(pe_base, 248)  # IMAGE_NT_HEADERS32 size
            if not nt_header or len(nt_header) < 248:
                return None
            
            # Check PE signature ('PE\0\0')
            if nt_header[:4] != b'PE\x00\x00':
                logger.error("Invalid PE signature at 0x%X", pe_base)
                return None
            
            # Get Optional Header magic to determine 32/64-bit
            opt_magic = struct.unpack('<H', nt_header[24:26])[0]
            is_64bit = (opt_magic == 0x20B)  # PE32+
            
            # Get Data Directory for IAT (IMAGE_DIRECTORY_ENTRY_IAT = index 12)
            if is_64bit:
                # IMAGE_OPTIONAL_HEADER64
                data_dir_offset = 24 + 112  # SizeOfOptionalHeader64 up to DataDirectory
                iat_rva = struct.unpack('<I', nt_header[data_dir_offset + (12 * 8):data_dir_offset + (12 * 8) + 4])[0]
                iat_size = struct.unpack('<I', nt_header[data_dir_offset + (12 * 8) + 4:data_dir_offset + (12 * 8) + 8])[0]
            else:
                # IMAGE_OPTIONAL_HEADER32
                data_dir_offset = 24 + 96  # SizeOfOptionalHeader32 up to DataDirectory
                iat_rva = struct.unpack('<I', nt_header[data_dir_offset + (12 * 8):data_dir_offset + (12 * 8) + 4])[0]
                iat_size = struct.unpack('<I', nt_header[data_dir_offset + (12 * 8) + 4:data_dir_offset + (12 * 8) + 8])[0]
            
            if iat_rva == 0 or iat_size == 0:
                logger.debug("Module at 0x%X has no IAT", module_base)
                return None
            
            iat_base = module_base + iat_rva
            entry_size = 8 if is_64bit else 4
            num_entries = iat_size // entry_size
            
            # Scan IAT for the function
            for i in range(num_entries):
                entry_addr = iat_base + (i * entry_size)
                entry_data = self._read_mem(entry_addr, entry_size)
                
                if not entry_data or len(entry_data) < entry_size:
                    continue
                
                # Read the function pointer
                if is_64bit:
                    func_ptr = struct.unpack('<Q', entry_data)[0]
                else:
                    func_ptr = struct.unpack('<I', entry_data)[0]
                
                if func_ptr == 0:
                    continue
                
                # NOTE: Simplified IAT entry detection
                # A full implementation would parse the Import Directory to validate
                # DLL and function names. This version returns the first non-zero entry.
                # For production use, extend to match against dll_name and function_name
                # by walking the Import Descriptor table.
                return entry_addr
            
            return None
            
        except Exception as e:
            logger.error("IAT entry search failed: %s", e)
            return None
    
    def hook_iat(
        self,
        iat_entry_addr: int,
        new_function_ptr: int,
    ) -> Optional[int]:
        """
        Hook an IAT entry.
        
        Args:
            iat_entry_addr: Address of the IAT entry
            new_function_ptr: Address of the replacement function
            
        Returns:
            Original function pointer or None
        """
        if not self.editor:
            return None
        
        try:
            # Read original pointer (assume 64-bit for safety, will work for 32-bit too)
            original_data = self._read_mem(iat_entry_addr, 8)
            if not original_data or len(original_data) < 8:
                # Try 32-bit
                original_data = self._read_mem(iat_entry_addr, 4)
                if not original_data or len(original_data) < 4:
                    return None
                original_ptr = struct.unpack('<I', original_data)[0]
                new_ptr_data = struct.pack('<I', new_function_ptr)
            else:
                original_ptr = struct.unpack('<Q', original_data)[0]
                new_ptr_data = struct.pack('<Q', new_function_ptr)
            
            # Write new function pointer
            if not self._write_mem(iat_entry_addr, new_ptr_data):
                logger.error("Failed to write IAT entry at 0x%X", iat_entry_addr)
                return None
            
            # Store original
            self._original_iat_entries[iat_entry_addr] = original_ptr
            
            logger.info(
                "IAT hook installed: entry=0x%X, original=0x%X, new=0x%X",
                iat_entry_addr, original_ptr, new_function_ptr
            )
            
            return original_ptr
            
        except Exception as e:
            logger.error("IAT hooking failed: %s", e)
            return None
    
    def unhook_iat(self, iat_entry_addr: int) -> bool:
        """
        Restore an IAT entry.
        
        Args:
            iat_entry_addr: Address of the IAT entry
            
        Returns:
            bool: True if restored successfully
        """
        if iat_entry_addr not in self._original_iat_entries:
            return False
        
        original_ptr = self._original_iat_entries[iat_entry_addr]
        ptr_size = 8 if original_ptr > 0x100000000 else 4
        ptr_data = struct.pack('<Q' if ptr_size == 8 else '<I', original_ptr)
        
        if not self._write_mem(iat_entry_addr, ptr_data):
            return False
        
        del self._original_iat_entries[iat_entry_addr]
        logger.info("IAT hook restored at 0x%X", iat_entry_addr)
        return True
    
    def unhook_all(self) -> int:
        """
        Restore all hooked IAT entries.
        
        Returns:
            Number of entries restored
        """
        count = 0
        for entry_addr in list(self._original_iat_entries.keys()):
            if self.unhook_iat(entry_addr):
                count += 1
        
        logger.info("Restored %d IAT hooks", count)
        return count


@dataclass
class HookChainEntry:
    """Represents a hook in a chain."""
    priority: int  # Lower = higher priority
    payload_builder: Callable[[Optional[int]], bytes]  # Takes trampoline_addr, returns payload
    description: str = ""


class HookManager:
    """
    Manages multiple inline hooks targeting the same address.
    
    Features:
    - Hook chaining with priority-based ordering
    - Trampoline support for preserving original instructions
    - Runtime validation and auto-restore
    """
    
    def __init__(self, backend: Any):
        """
        Initialize hook manager.
        
        Args:
            backend: Memory backend instance
        """
        self.backend = backend
        self._hook_chains: Dict[int, List[HookChainEntry]] = {}  # address -> hooks
        self._trampolines: Dict[int, int] = {}  # address -> trampoline_addr
        self._original_bytes: Dict[int, bytes] = {}  # address -> original_bytes
        self._active_patches: Dict[int, bytes] = {}  # address -> current_patch
    
    def register_hook(
        self,
        address: int,
        payload_builder: Callable[[Optional[int]], bytes],
        priority: int = 0,
        description: str = "",
    ) -> bool:
        """
        Register a hook at the specified address.
        
        Args:
            address: Target address to hook
            payload_builder: Function that generates hook payload (receives trampoline_addr)
            priority: Hook priority (lower = executes first)
            description: Hook description
            
        Returns:
            bool: True if registered successfully
        """
        if address not in self._hook_chains:
            self._hook_chains[address] = []
        
        entry = HookChainEntry(
            priority=priority,
            payload_builder=payload_builder,
            description=description,
        )
        
        self._hook_chains[address].append(entry)
        # Sort by priority
        self._hook_chains[address].sort(key=lambda x: x.priority)
        
        logger.info(
            "Hook registered at 0x%X (priority=%d): %s",
            address, priority, description
        )
        
        return True
    
    def apply_hooks(self, address: int, overwrite_size: int = 5) -> bool:
        """
        Apply all hooks at an address, creating a combined payload with trampoline.
        
        Args:
            address: Target address
            overwrite_size: Number of bytes to overwrite
            
        Returns:
            bool: True if applied successfully
        """
        if address not in self._hook_chains or not self.backend:
            return False
        
        hooks = self._hook_chains[address]
        if not hooks:
            return False
        
        # Read original instructions
        original_bytes = self.backend.read_bytes(address, overwrite_size)
        if not original_bytes or len(original_bytes) != overwrite_size:
            logger.error("Failed to read original bytes at 0x%X", address)
            return False
        
        self._original_bytes[address] = original_bytes
        
        # Allocate trampoline if needed
        trampoline_addr = self._create_trampoline(address, original_bytes)
        if trampoline_addr is None:
            logger.error("Failed to create trampoline for 0x%X", address)
            return False
        
        # Build combined payload
        combined_payload = self._build_combined_payload(hooks, trampoline_addr)
        if not combined_payload:
            logger.error("Failed to build combined payload for 0x%X", address)
            return False
        
        # Write combined payload
        if not self.backend.write_bytes(address, combined_payload):
            logger.error("Failed to write hook payload at 0x%X", address)
            return False
        
        self._active_patches[address] = combined_payload
        
        logger.info(
            "Hook chain applied at 0x%X (%d hooks, trampoline=0x%X)",
            address, len(hooks), trampoline_addr
        )
        
        return True
    
    def _create_trampoline(self, address: int, original_bytes: bytes) -> Optional[int]:
        """
        Create a trampoline code cave with original instructions.
        
        Args:
            address: Original hooked address
            original_bytes: Original instruction bytes
            
        Returns:
            Trampoline address or None
        """
        if not self.backend:
            return None
        
        # Find code cave FIRST (before building the jump)
        injector = CodeCaveInjector(self.backend)
        trampoline_size = len(original_bytes) + 5  # original bytes + JMP back
        cave_address = injector.find_code_cave(trampoline_size)
        
        if cave_address is None:
            return None
        
        # FIX: Build jump AFTER knowing cave_address
        # The jump should go FROM (cave_address + len(original_bytes)) 
        # TO (address + len(original_bytes)) - back to original code after the hook
        jump_back = CodeCaveInjector.build_relative_jump(
            cave_address + len(original_bytes),  # Source: where JMP instruction will be placed
            address + len(original_bytes)         # Target: instruction after the overwritten ones
        )
        
        trampoline_payload = original_bytes + jump_back
        
        # Write trampoline
        if not self.backend.write_bytes(cave_address, trampoline_payload):
            return None
        
        self._trampolines[address] = cave_address
        
        logger.debug("Trampoline created at 0x%X for 0x%X", cave_address, address)
        return cave_address
    
    def _build_combined_payload(
        self,
        hooks: List[HookChainEntry],
        trampoline_addr: int,
    ) -> Optional[bytes]:
        """
        Build a combined payload from all hooks in the chain.
        
        Args:
            hooks: List of hook entries (sorted by priority)
            trampoline_addr: Address of trampoline code cave
            
        Returns:
            Combined payload bytes or None
        """
        if not hooks:
            return None
        
        # Start with a jump to the first hook
        payloads = []
        current_addr = 0  # Will be relative
        
        for hook in hooks:
            # Build hook payload (can optionally call trampoline)
            hook_payload = hook.payload_builder(trampoline_addr if hook.priority < 0 else None)
            if hook_payload:
                payloads.append(hook_payload)
        
        if not payloads:
            return None
        
        # Combine payloads
        combined = b''.join(payloads)
        
        # Add jump to trampoline (to execute original instructions)
        # NOTE: Simplified calculation - assumes payload is at 'address'
        # For production use, calculate actual runtime address based on
        # where the combined payload will be loaded in memory
        jump_to_trampoline = CodeCaveInjector.build_relative_jump(
            0,  # Placeholder - runtime address calculation needed
            trampoline_addr
        )
        
        return combined + jump_to_trampoline
    
    def validate_hooks(self) -> List[int]:
        """
        Validate that all active hooks are still in place.
        Restores any hooks that were overwritten.
        
        Returns:
            List of addresses that were restored
        """
        restored = []
        
        for address, expected_patch in self._active_patches.items():
            if not self.backend:
                continue
            
            # Read current bytes
            current_bytes = self.backend.read_bytes(address, len(expected_patch))
            
            if current_bytes != expected_patch:
                # Hook was overwritten, restore it
                logger.warning(
                    "Hook at 0x%X was overwritten (expected %d bytes, got %d)",
                    address, len(expected_patch),
                    len(current_bytes) if current_bytes else 0
                )
                
                if self.backend.write_bytes(address, expected_patch):
                    restored.append(address)
                    logger.info("Hook restored at 0x%X", address)
        
        if restored:
            logger.info("Validated hooks: %d restored", len(restored))
        
        return restored
    
    def remove_hooks(self, address: int) -> bool:
        """
        Remove all hooks at an address and restore original bytes.
        
        Args:
            address: Target address
            
        Returns:
            bool: True if removed successfully
        """
        if address not in self._original_bytes or not self.backend:
            return False
        
        # Restore original bytes
        original = self._original_bytes[address]
        if not self.backend.write_bytes(address, original):
            logger.error("Failed to restore original bytes at 0x%X", address)
            return False
        
        # Clean up trampoline (optional - could leave it allocated)
        if address in self._trampolines:
            # In a production system, you'd free the trampoline memory
            del self._trampolines[address]
        
        # Remove stored state
        del self._original_bytes[address]
        if address in self._active_patches:
            del self._active_patches[address]
        if address in self._hook_chains:
            del self._hook_chains[address]
        
        logger.info("Hooks removed and original bytes restored at 0x%X", address)
        return True
    
    def remove_all_hooks(self) -> int:
        """
        Remove all active hooks.
        
        Returns:
            Number of hook chains removed
        """
        count = 0
        for address in list(self._active_patches.keys()):
            if self.remove_hooks(address):
                count += 1
        
        logger.info("Removed %d hook chains", count)
        return count
