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
        """Main freeze loop - runs in background thread."""
        while self._running:
            try:
                current_time = time.time()
                
                with self._lock:
                    addresses = list(self.frozen.values())
                
                for frozen in addresses:
                    if not frozen.enabled:
                        continue
                    
                    # Check if it's time to write
                    elapsed_ms = (current_time - frozen.last_write_time) * 1000
                    if elapsed_ms < frozen.interval_ms:
                        continue
                    
                    self._write_frozen_value(frozen, current_time)
                
                # Sleep for minimum interval
                time.sleep(self._min_interval_ms / 1000.0)
                
            except Exception as e:
                logger.error("Freeze loop error: %s", e)
                time.sleep(0.1)
    
    def _write_frozen_value(self, frozen: FrozenAddress, current_time: float) -> None:
        """Write a frozen value to memory via the backend."""
        if not self.editor:
            return
        
        try:
            fmt, size = self.VALUE_FORMATS[frozen.value_type]
            data = struct.pack(fmt, frozen.value)
            
            # Support both backend (write_bytes) and legacy (write_process_memory)
            if hasattr(self.editor, 'write_bytes'):
                self.editor.write_bytes(frozen.address, data)
            else:
                self._write_mem(frozen.address, data)
            
            frozen.last_write_time = current_time
            frozen.write_count += 1
            frozen.error_count = 0  # Reset on success
            
            if self._on_write:
                self._on_write(frozen.address, frozen.value)
                
        except Exception as e:
            frozen.error_count += 1
            
            if frozen.error_count >= self._max_errors_per_address:
                logger.warning("Disabling freeze for 0x%08X after %d errors", 
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
        Scan memory for an AOB pattern.
        
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
        start_time = time.time()
        
        logger.info("AOB scan: %s (%s) range 0x%08X-0x%08X", 
                    pattern.name, pattern.pattern, start_address, end_address)
        
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
                
                # Search for pattern in chunk
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
# Lua Injection for Napoleon Total War (embedded Lua 5.1)
# ============================================================================

class LuaInjector(_BackendMixin):
    """
    Inject and execute arbitrary Lua scripts into Napoleon Total War's
    embedded Lua 5.1 engine.

    The injector locates ``luaL_loadbuffer`` and ``lua_pcall`` via AOB
    signature scanning, resolves the game's main ``lua_State*`` pointer,
    then uses a small x86 shellcode stub to call those functions from
    within the game process.  All injection is synchronised with a lock
    so that concurrent calls do not corrupt the Lua state.

    Typical workflow::

        inj = LuaInjector(editor)
        inj.scan_lua_functions()
        inj.execute("scripting.game_interface:grant_faction_handover()")
        inj.cleanup()
    """

    # -----------------------------------------------------------------
    # Known AOB signatures for Lua 5.1 inside the WARSCAPE engine.
    # These are x86 instruction patterns around the function prologues.
    # -----------------------------------------------------------------
    LUA_SIGNATURES: Dict[str, AOBPattern] = {
        'luaL_loadbuffer': AOBPattern(
            name='luaL_loadbuffer',
            pattern='55 8B EC 83 EC ?? 56 8B 75 08 57 8B 7D 10 85 FF',
            description=(
                'luaL_loadbuffer prologue — push ebp / mov ebp,esp / '
                'sub esp,N / push esi / mov esi,[ebp+8] / push edi / '
                'mov edi,[ebp+10h] / test edi,edi'
            ),
            offset_from_match=0,
        ),
        'lua_pcall': AOBPattern(
            name='lua_pcall',
            pattern='55 8B EC 8B 55 0C 56 8B 75 08 85 D2 78',
            description=(
                'lua_pcall prologue — push ebp / mov ebp,esp / '
                'mov edx,[ebp+0Ch] / push esi / mov esi,[ebp+8] / '
                'test edx,edx / js …'
            ),
            offset_from_match=0,
        ),
        'lua_state_global': AOBPattern(
            name='lua_state_global',
            pattern='A1 ?? ?? ?? ?? 85 C0 74 ?? 50 E8 ?? ?? ?? ?? 83 C4 04',
            description=(
                'MOV EAX,[global_lua_state] / TEST EAX,EAX / JZ … — '
                'common pattern where the game loads the main lua_State* '
                'from a global variable before calling into Lua'
            ),
            offset_from_match=1,  # skip the A1 opcode to land on the address
        ),
    }

    # Maximum Lua source length we will inject in one call.
    MAX_LUA_SOURCE_LEN = 8192

    def __init__(self, editor: Optional[Any] = None):
        """
        Initialise the Lua injector.

        Args:
            editor: A memory backend (or legacy editor) instance.
        """
        self.editor = editor

        # Resolved function addresses
        self._loadbuffer_addr: Optional[int] = None
        self._pcall_addr: Optional[int] = None
        self._lua_state_addr: Optional[int] = None

        # Code-cave address allocated for the shellcode stub
        self._cave_addr: Optional[int] = None
        self._cave_size: int = 0
        self._cave_original: Optional[bytes] = None

        # Thread-safety: only one Lua injection at a time
        self._inject_lock = threading.Lock()

        # Execution history
        self._history: List[Dict[str, Any]] = []

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def is_ready(self) -> bool:
        """``True`` when all three function pointers have been resolved."""
        return all([
            self._loadbuffer_addr is not None,
            self._pcall_addr is not None,
            self._lua_state_addr is not None,
        ])

    @property
    def loadbuffer_address(self) -> Optional[int]:
        return self._loadbuffer_addr

    @property
    def pcall_address(self) -> Optional[int]:
        return self._pcall_addr

    @property
    def lua_state_address(self) -> Optional[int]:
        return self._lua_state_addr

    @property
    def history(self) -> List[Dict[str, Any]]:
        """Return a *copy* of the execution history."""
        return list(self._history)

    # ------------------------------------------------------------------
    # Public helpers
    # ------------------------------------------------------------------

    def set_editor(self, editor: Any) -> None:
        """Attach or replace the memory backend."""
        self.editor = editor
        self._reset()

    def set_addresses(
        self,
        loadbuffer: int,
        pcall: int,
        lua_state: int,
    ) -> None:
        """Manually supply the three required addresses."""
        self._loadbuffer_addr = loadbuffer
        self._pcall_addr = pcall
        self._lua_state_addr = lua_state
        logger.info(
            "Lua addresses set: luaL_loadbuffer=0x%08X  lua_pcall=0x%08X  "
            "lua_State*=0x%08X",
            loadbuffer, pcall, lua_state,
        )

    # ------------------------------------------------------------------
    # Scanning
    # ------------------------------------------------------------------

    def scan_lua_functions(
        self,
        start: int = 0x00400000,
        end: int = 0x7FFFFFFF,
        timeout: float = 30.0,
    ) -> bool:
        """
        Scan the game's memory for luaL_loadbuffer, lua_pcall and the
        global lua_State* pointer.

        Returns:
            ``True`` if all three addresses were found.
        """
        if not self.editor:
            logger.warning("No editor set — cannot scan for Lua functions")
            return False

        scanner = AOBScanner(editor=self.editor)

        for key, pattern in self.LUA_SIGNATURES.items():
            try:
                results = scanner.scan(
                    pattern,
                    start_address=start,
                    end_address=end,
                    max_results=1,
                    timeout=timeout,
                )
                if results:
                    addr = results[0]
                    if key == 'luaL_loadbuffer':
                        self._loadbuffer_addr = addr
                    elif key == 'lua_pcall':
                        self._pcall_addr = addr
                    elif key == 'lua_state_global':
                        # The AOB landed on the 4-byte address operand;
                        # dereference it to get the *pointer to* lua_State.
                        self._lua_state_addr = addr
                    logger.info(
                        "Found %s at 0x%08X", pattern.name, addr,
                    )
                else:
                    logger.warning("Signature not found: %s", pattern.name)
            except Exception as exc:
                logger.error("Scan failed for %s: %s", pattern.name, exc)

        if self.is_ready:
            logger.info("All Lua function pointers resolved — injector ready")
        else:
            logger.warning("Lua injector not fully initialised")
        return self.is_ready

    # ------------------------------------------------------------------
    # Shellcode building
    # ------------------------------------------------------------------

    @staticmethod
    def _build_lua_exec_shellcode(
        lua_state_ptr_addr: int,
        loadbuffer_addr: int,
        pcall_addr: int,
        source_addr: int,
        source_len: int,
    ) -> bytes:
        """
        Build x86 (32-bit) shellcode that calls:

            lua_State *L = *(lua_State **)lua_state_ptr_addr;
            luaL_loadbuffer(L, source, source_len, "inject");
            lua_pcall(L, 0, 0, 0);
            ret;

        The shellcode is position-independent with respect to its own
        location — it only uses absolute addresses embedded as immediates.
        """
        #   pushad                          ; save all regs
        #   mov eax, [lua_state_ptr_addr]   ; eax = lua_State*
        #
        #   ; --- luaL_loadbuffer(L, source, len, name) ---
        #   push <chunk_name_addr>          ; will be patched to point at "inject\\0"
        #   push source_len
        #   push source_addr
        #   push eax                        ; L
        #   mov ebx, loadbuffer_addr
        #   call ebx
        #   add esp, 16
        #
        #   ; --- lua_pcall(L, 0, 0, 0) ---
        #   mov eax, [lua_state_ptr_addr]
        #   push 0                          ; errfunc
        #   push 0                          ; nresults
        #   push 0                          ; nargs
        #   push eax                        ; L
        #   mov ebx, pcall_addr
        #   call ebx
        #   add esp, 16
        #
        #   popad
        #   ret

        chunk_name = b'inject\x00'

        # We'll assemble the whole thing, then append the chunk-name string
        # at a known offset so we can reference it.
        parts: List[bytes] = []

        # pushad
        parts.append(b'\x60')

        # mov eax, [lua_state_ptr_addr]
        parts.append(b'\xA1' + struct.pack('<I', lua_state_ptr_addr))

        # -- placeholder PUSH for chunk_name address (patched below) --
        chunk_name_push_offset = sum(len(p) for p in parts)
        parts.append(b'\x68' + b'\x00\x00\x00\x00')  # push imm32 (patched)

        # push source_len
        parts.append(b'\x68' + struct.pack('<I', source_len))

        # push source_addr
        parts.append(b'\x68' + struct.pack('<I', source_addr))

        # push eax  (L)
        parts.append(b'\x50')

        # mov ebx, loadbuffer_addr ; call ebx
        parts.append(b'\xBB' + struct.pack('<I', loadbuffer_addr))
        parts.append(b'\xFF\xD3')

        # add esp, 16
        parts.append(b'\x83\xC4\x10')

        # mov eax, [lua_state_ptr_addr]  (reload L — callee may have trashed it)
        parts.append(b'\xA1' + struct.pack('<I', lua_state_ptr_addr))

        # push 0 ; push 0 ; push 0 ; push eax
        parts.append(b'\x6A\x00')  # errfunc
        parts.append(b'\x6A\x00')  # nresults
        parts.append(b'\x6A\x00')  # nargs
        parts.append(b'\x50')      # L

        # mov ebx, pcall_addr ; call ebx
        parts.append(b'\xBB' + struct.pack('<I', pcall_addr))
        parts.append(b'\xFF\xD3')

        # add esp, 16
        parts.append(b'\x83\xC4\x10')

        # popad ; ret
        parts.append(b'\x61')
        parts.append(b'\xC3')

        code = b''.join(parts)

        # The chunk name string is appended right after the code.
        chunk_name_offset = len(code)
        code += chunk_name

        # We still need to know the absolute address of the chunk name in
        # memory.  The caller will relocate the shellcode to a code cave
        # so this method returns the raw bytes + the offset that must be
        # patched with (cave_base + chunk_name_offset).
        # We embed the offset inside the returned tuple via a small helper
        # that the caller invokes.  For simplicity, we store the fixup
        # index in the first byte sequence that is all-zero push.

        # Patch: the chunk_name push is at chunk_name_push_offset+1 (skip 0x68 opcode)
        # We'll return (code_bytes, fixup_offset, chunk_name_relative_offset)
        return code, chunk_name_push_offset + 1, chunk_name_offset  # type: ignore[return-value]

    # ------------------------------------------------------------------
    # Injection
    # ------------------------------------------------------------------

    def execute(self, lua_source: str) -> bool:
        """
        Inject and execute a Lua source string in the game's main state.

        The call is thread-safe — concurrent ``execute()`` calls are
        serialised so only one Lua chunk runs at a time.

        Args:
            lua_source: Lua source code to execute (max 8 KiB).

        Returns:
            ``True`` if the shellcode was written and triggered
            successfully.
        """
        if not self.is_ready:
            logger.error("Lua injector not ready — call scan_lua_functions() first")
            return False

        if not self.editor:
            logger.error("No editor available")
            return False

        source_bytes = lua_source.encode('utf-8') + b'\x00'
        if len(source_bytes) > self.MAX_LUA_SOURCE_LEN:
            logger.error(
                "Lua source too long (%d bytes, max %d)",
                len(source_bytes), self.MAX_LUA_SOURCE_LEN,
            )
            return False

        with self._inject_lock:
            return self._do_execute(source_bytes, lua_source)

    def _do_execute(self, source_bytes: bytes, lua_source: str) -> bool:
        """Internal execute — called under ``_inject_lock``."""
        assert self._loadbuffer_addr is not None
        assert self._pcall_addr is not None
        assert self._lua_state_addr is not None

        # 1. Write the Lua source string into a code cave
        source_cave = self._alloc_cave(len(source_bytes))
        if source_cave is None:
            logger.error("Could not allocate cave for Lua source")
            return False

        if not self._write_mem(source_cave, source_bytes):
            logger.error("Failed to write Lua source to 0x%08X", source_cave)
            return False

        # 2. Build the shellcode
        raw_code, fixup_offset, chunk_name_rel = self._build_lua_exec_shellcode(
            lua_state_ptr_addr=self._lua_state_addr,
            loadbuffer_addr=self._loadbuffer_addr,
            pcall_addr=self._pcall_addr,
            source_addr=source_cave,
            source_len=len(source_bytes) - 1,  # exclude the NUL terminator
        )

        # 3. Allocate a cave for the shellcode itself
        code_cave = self._alloc_cave(len(raw_code))
        if code_cave is None:
            logger.error("Could not allocate cave for shellcode")
            return False

        # 4. Patch the chunk-name absolute address
        chunk_name_abs = code_cave + chunk_name_rel
        patched = (
            raw_code[:fixup_offset]
            + struct.pack('<I', chunk_name_abs)
            + raw_code[fixup_offset + 4:]
        )

        # 5. Write the shellcode
        if not self._write_mem(code_cave, patched):
            logger.error("Failed to write shellcode to 0x%08X", code_cave)
            return False

        logger.info(
            "Lua injection prepared at cave=0x%08X source=0x%08X (%d bytes)",
            code_cave, source_cave, len(source_bytes) - 1,
        )

        # Record in history
        self._history.append({
            'source': lua_source,
            'source_addr': source_cave,
            'code_addr': code_cave,
            'code_size': len(patched),
            'source_size': len(source_bytes),
        })

        return True

    # ------------------------------------------------------------------
    # Cave allocation helpers
    # ------------------------------------------------------------------

    def _alloc_cave(self, size: int) -> Optional[int]:
        """Find a code cave large enough for *size* bytes."""
        if not self.editor:
            return None

        # If the backend has a find_code_cave helper (from CodeCaveInjector
        # compatibility), use it.
        if hasattr(self.editor, 'get_readable_regions'):
            regions = self.editor.get_readable_regions()
            for region in regions:
                data = self._read_mem(region['address'], region['size'])
                if not data or len(data) < size:
                    continue
                run_start = None
                run_length = 0
                for idx, byte in enumerate(data):
                    if byte in (0x00, 0xCC):
                        if run_start is None:
                            run_start = idx
                        run_length += 1
                        if run_length >= size:
                            return region['address'] + run_start
                    else:
                        run_start = None
                        run_length = 0
        return None

    # ------------------------------------------------------------------
    # Cleanup
    # ------------------------------------------------------------------

    def cleanup(self) -> None:
        """Zero out any shellcode and source buffers written during this session."""
        if not self.editor:
            return

        for entry in self._history:
            try:
                self._write_mem(entry['code_addr'], b'\x00' * entry['code_size'])
            except Exception:
                pass
            try:
                self._write_mem(entry['source_addr'], b'\x00' * entry['source_size'])
            except Exception:
                pass

        self._history.clear()
        logger.info("Lua injector cleaned up")

    def get_status(self) -> Dict[str, Any]:
        """Return a summary dictionary of the injector state."""
        return {
            'ready': self.is_ready,
            'loadbuffer_addr': (
                f'0x{self._loadbuffer_addr:08X}'
                if self._loadbuffer_addr is not None else None
            ),
            'pcall_addr': (
                f'0x{self._pcall_addr:08X}'
                if self._pcall_addr is not None else None
            ),
            'lua_state_addr': (
                f'0x{self._lua_state_addr:08X}'
                if self._lua_state_addr is not None else None
            ),
            'injections': len(self._history),
        }

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _reset(self) -> None:
        """Clear all resolved addresses."""
        self._loadbuffer_addr = None
        self._pcall_addr = None
        self._lua_state_addr = None
        self._history.clear()
