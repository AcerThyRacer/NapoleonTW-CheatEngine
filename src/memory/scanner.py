"""
Memory scanner implementation with backend abstraction.
Provides Cheat Engine-like functionality for scanning and editing memory.
"""

from enum import Enum
from typing import TYPE_CHECKING, Dict, List, Optional, TypedDict, Union, cast, Any
from dataclasses import dataclass
import json
import struct
import time
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading
from pathlib import Path

from .process import ProcessManager
from .backend import MemoryBackend, MemoryRegion, create_backend

logger = logging.getLogger('napoleon.memory.scanner')

if TYPE_CHECKING:
    from .advanced import MemoryFreezer

ScanValue = Union[int, float, str]


class ScanHistoryEntry(TypedDict, total=False):
    """Recorded metadata for previous scans."""
    scan_type: str
    value: ScanValue
    value_type: str
    result_count: int


class FreezeStats(TypedDict, total=False):
    """Statistics returned by the memory freezer."""
    total_frozen: int
    active_frozen: int
    total_writes: int
    total_errors: int
    is_running: bool


class ValueType(Enum):
    """Supported value types for scanning."""
    INT_8 = '1 Byte'
    INT_16 = '2 Bytes'
    INT_32 = '4 Bytes'
    INT_64 = '8 Bytes'
    FLOAT = 'Float'
    DOUBLE = 'Double'
    STRING = 'String'


class ScanType(Enum):
    """Types of memory scans."""
    EXACT_VALUE = 'exact'
    INCREASED_VALUE = 'increased'
    DECREASED_VALUE = 'decreased'
    CHANGED_VALUE = 'changed'
    UNCHANGED_VALUE = 'unchanged'
    UNKNOWN_INITIAL = 'unknown'
    BETWEEN_RANGE = 'range'


@dataclass
class ScanResult:
    """Represents a memory scan result."""
    address: int
    value: ScanValue
    value_type: ValueType
    previous_value: Optional[ScanValue] = None
    
    def __str__(self) -> str:
        return f"0x{self.address:08X}: {self.value} ({self.value_type.value})"


class MemoryScanner:
    """
    Cross-platform memory scanner for Napoleon Total War.
    Uses the backend abstraction layer for memory access.
    """
    
    def __init__(self, process_manager: ProcessManager) -> None:
        """
        Initialize the memory scanner.
        
        Args:
            process_manager: ProcessManager instance
        """
        self.process_manager = process_manager
        self.backend: Optional[MemoryBackend] = None
        # Legacy alias for code that references self.editor
        self.editor: Optional[MemoryBackend] = None
        self.results: List[ScanResult] = []
        self.previous_values: Dict[int, ScanValue] = {}
        self.scan_history: List[ScanHistoryEntry] = []
        self._freezer: Optional["MemoryFreezer"] = None
        
        # Incremental scan caching
        self.scan_cache: Dict[str, Dict[str, Any]] = {}
        self._cache_dir = Path.cwd() / '.cache' / 'scans'
        self._cache_dir.mkdir(parents=True, exist_ok=True)
        
    def attach(self) -> bool:
        """
        Attach to the process and initialize memory backend.
        
        Returns:
            bool: True if successful
        """
        if not self.process_manager.attach():
            return False
        
        self.backend = create_backend(self.process_manager.pid)
        if self.backend:
            # Legacy alias so existing code referencing self.editor still works
            self.editor = self.backend
            logger.info("Attached to PID %d with backend %s",
                        self.process_manager.pid, type(self.backend).__name__)
            return True
        
        logger.error("No memory backend available for PID %d", self.process_manager.pid)
        return False
    
    def detach(self) -> None:
        """
        Detach from the process.
        """
        # Stop freezer if running
        if self._freezer:
            self._freezer.unfreeze_all()
            self._freezer = None
        
        if self.backend:
            try:
                self.backend.close()
            except Exception:
                pass
            self.backend = None
            self.editor = None
        
        self.process_manager.detach()
        self.results = []
        self.previous_values = {}
    
    def is_attached(self) -> bool:
        """Check if attached to process."""
        return self.process_manager.is_attached() and self.backend is not None and self.backend.is_open
    
    def _get_type_size(self, value_type: ValueType) -> int:
        """Get size in bytes for a value type."""
        sizes = {
            ValueType.INT_8: 1,
            ValueType.INT_16: 2,
            ValueType.INT_32: 4,
            ValueType.INT_64: 8,
            ValueType.FLOAT: 4,
            ValueType.DOUBLE: 8,
        }
        return sizes.get(value_type, 4)
    
    def get_prioritized_regions(
        self,
        regions: List[MemoryRegion]
    ) -> List[MemoryRegion]:
        """
        Sort and filter memory regions by priority for faster scanning.
        
        Priority order:
        1. napoleon.exe module (primary game executable)
        2. Anonymous heap/private memory (likely game data)
        3. Other executable modules (DLLs)
        4. Mapped files/data segments
        
        Skipped entirely:
        - Video driver memory (large, rarely contains game state)
        - Kernel/system memory
        - Hardware-mapped regions
        
        Args:
            regions: List of all readable memory regions
            
        Returns:
            List[MemoryRegion]: Prioritized and filtered regions
        """
        if not regions:
            return []
        
        prioritized: List[MemoryRegion] = []
        heap_regions: List[MemoryRegion] = []
        dll_regions: List[MemoryRegion] = []
        other_regions: List[MemoryRegion] = []
        
        for region in regions:
            addr = region['address']
            size = region['size']
            
            # Skip video driver memory (typically 0xA0000000+ or very large)
            if addr >= 0xA0000000:
                continue
            
            # Skip kernel/system memory (low addresses on Windows)
            if addr < 0x00400000 and addr > 0x10000:
                continue
            
            # Skip hardware-mapped regions
            if size > 0x40000000:  # > 1GB
                continue
            
            # Check if this is napoleon.exe (typically first module at 0x00400000)
            if addr == 0x00400000 or (0x00400000 <= addr < 0x01000000 and size > 0x100000):
                prioritized.append(region)
                continue
            
            # Check if this is anonymous private memory (heap)
            # Private memory typically has no image name and is in range 0x10000000-0x80000000
            if 0x10000000 <= addr < 0x80000000 and size > 0x10000:
                heap_regions.append(region)
                continue
            
            # DLLs and other modules
            if size > 0x10000:
                dll_regions.append(region)
            else:
                other_regions.append(region)
        
        # Sort each category by size (larger first - more likely to contain data)
        heap_regions.sort(key=lambda r: r['size'], reverse=True)
        dll_regions.sort(key=lambda r: r['size'], reverse=True)
        
        # Combine in priority order
        result = prioritized + heap_regions + dll_regions + other_regions
        
        logger.debug(
            "Region prioritization: %d total → %d prioritized "
            "(%d exe, %d heap, %d dll, %d other, %d skipped)",
            len(regions), len(result),
            len(prioritized), len(heap_regions), len(dll_regions),
            len(other_regions), len(regions) - len(result)
        )
        
        return result
    
    def suggest_value_type(
        self,
        address: int,
        results: Optional[List[ScanResult]] = None
    ) -> str:
        """
        Suggest the likely type of value at an address based on heuristics.
        
        Uses pattern recognition to classify values as:
        - Health: Typically 0-1000 range, often floats or integers
        - Gold/Currency: Typically large integers (1000+), increases/decreases
        - Ammunition: Small integers (0-999), discrete values
        - Mana/Energy: 0-100 or 0-1000 range, often regenerates
        - Unknown: Doesn't match known patterns
        
        Args:
            address: Address to analyze
            results: Optional list of scan results for context
            
        Returns:
            str: Suggested value type description
        """
        if not self.is_attached():
            return "Unknown (not attached)"
        
        # Read the current value
        current_value = None
        value_type = ValueType.INT_32  # Default assumption
        
        # Try reading as different types
        try:
            int_val = self.read_value(address, ValueType.INT_32)
            float_val = self.read_value(address, ValueType.FLOAT)
            
            if int_val is not None:
                current_value = int_val
                value_type = ValueType.INT_32
            elif float_val is not None:
                current_value = float_val
                value_type = ValueType.FLOAT
        except Exception:
            return "Unknown (read failed)"
        
        if current_value is None:
            return "Unknown (invalid address)"
        
        # Analyze the value
        suggestions = []
        
        # Health detection (0-1000 range common for health)
        if isinstance(current_value, (int, float)):
            if 0 <= current_value <= 100:
                suggestions.append(("Health (0-100 range)", 0.7))
            elif 0 <= current_value <= 1000:
                suggestions.append(("Health/Gold (0-1000 range)", 0.6))
            
            # Very large values often gold or points
            if current_value >= 10000:
                suggestions.append(("Gold/Points (large value)", 0.8))
            
            # Small discrete values often ammunition or counts
            if isinstance(current_value, int) and 0 <= current_value <= 999:
                suggestions.append(("Ammunition/Count (small integer)", 0.6))
            
            # Check if value is a "round" number (common for currency)
            if isinstance(current_value, int) and current_value % 100 == 0:
                suggestions.append(("Currency (round number)", 0.5))
        
        # Float-specific heuristics
        if isinstance(current_value, float):
            # Values close to 1.0 often multipliers or normalized stats
            if 0.9 <= current_value <= 1.1:
                suggestions.append(("Multiplier/Scale (near 1.0)", 0.7))
            
            # Time-related values (seconds/frames)
            if current_value > 0 and current_value < 10:
                suggestions.append(("Timer/Cooldown (small float)", 0.5))
        
        # If we have scan history, use behavior patterns
        if results and len(results) > 0:
            # Count how many results are in similar ranges
            similar_range = sum(
                1 for r in results
                if isinstance(r.value, (int, float))
                and abs(float(r.value) - float(current_value)) < float(current_value) * 0.1
            )
            
            if similar_range > len(results) * 0.5:
                suggestions.append(("Common game stat (many similar values)", 0.6))
        
        # Return best suggestion
        if suggestions:
            suggestions.sort(key=lambda x: x[1], reverse=True)
            return f"{suggestions[0][0]} (value={current_value})"
        
        return f"Unknown type (value={current_value})"
    
    def _get_cache_path(self, label: str) -> Path:
        """Get the cache file path for a scan label."""
        safe_label = "".join(c for c in label if c.isalnum() or c in ('-', '_'))
        return self._cache_dir / f"cache_{safe_label}.json"
    
    def _load_scan_cache(self, label: str) -> Optional[Dict[str, Any]]:
        """
        Load cached scan data for a label.
        
        Args:
            label: Semantic scan label (e.g., 'gold', 'health')
            
        Returns:
            Cached data dict or None if not found/expired
        """
        if not label:
            return None
        
        cache_path = self._get_cache_path(label)
        
        if not cache_path.exists():
            return None
        
        try:
            with open(cache_path, 'r') as f:
                cache_data = json.load(f)
            
            # Check if cache is still valid (within 24 hours)
            from datetime import datetime, timedelta
            timestamp = datetime.fromisoformat(cache_data.get('timestamp', ''))
            if datetime.now() - timestamp > timedelta(hours=24):
                logger.debug("Scan cache expired for label '%s'", label)
                return None
            
            logger.info(
                "Loaded scan cache for '%s': %d regions from %s",
                label,
                len(cache_data.get('regions', [])),
                cache_data.get('game_version', 'unknown')
            )
            
            return cache_data
            
        except Exception as e:
            logger.debug("Failed to load scan cache: %s", e)
            return None
    
    def _save_scan_cache(
        self,
        label: str,
        regions: List[MemoryRegion],
        results: List[ScanResult]
    ) -> None:
        """
        Save scan results to cache.
        
        Args:
            label: Semantic scan label
            regions: Memory regions that were scanned
            results: Scan results to cache
        """
        if not label:
            return
        
        try:
            from datetime import datetime
            
            cache_data = {
                'label': label,
                'timestamp': datetime.now().isoformat(),
                'game_version': 'unknown',  # Could be determined from process
                'pid': self.process_manager.pid,
                'regions': [
                    {'address': r['address'], 'size': r['size']}
                    for r in regions
                ],
                'result_count': len(results),
                'result_addresses': [r.address for r in results[:100]]  # Cache first 100
            }
            
            cache_path = self._get_cache_path(label)
            with open(cache_path, 'w') as f:
                json.dump(cache_data, f, indent=2)
            
            logger.debug(
                "Saved scan cache for '%s': %d regions, %d results",
                label, len(regions), len(results)
            )
            
        except Exception as e:
            logger.debug("Failed to save scan cache: %s", e)
    
    def _pack_value(self, value: ScanValue, value_type: ValueType) -> bytes:
        """Pack a value into bytes."""
        try:
            if value_type == ValueType.INT_8:
                return struct.pack('<b', int(value))
            elif value_type == ValueType.INT_16:
                return struct.pack('<h', int(value))
            elif value_type == ValueType.INT_32:
                return struct.pack('<i', int(value))
            elif value_type == ValueType.INT_64:
                return struct.pack('<q', int(value))
            elif value_type == ValueType.FLOAT:
                return struct.pack('<f', float(value))
            elif value_type == ValueType.DOUBLE:
                return struct.pack('<d', float(value))
            elif value_type == ValueType.STRING:
                return str(value).encode('utf-8')
        except struct.error as e:
            raise ValueError(f"Failed to pack value: {e}")
        
        raise ValueError(f"Unknown value type: {value_type}")
    
    def _unpack_value(self, data: bytes, value_type: ValueType) -> ScanValue:
        """Unpack bytes into a value."""
        try:
            if value_type == ValueType.INT_8:
                return struct.unpack('<b', data)[0]
            elif value_type == ValueType.INT_16:
                return struct.unpack('<h', data)[0]
            elif value_type == ValueType.INT_32:
                return struct.unpack('<i', data)[0]
            elif value_type == ValueType.INT_64:
                return struct.unpack('<q', data)[0]
            elif value_type == ValueType.FLOAT:
                return struct.unpack('<f', data)[0]
            elif value_type == ValueType.DOUBLE:
                return struct.unpack('<d', data)[0]
            elif value_type == ValueType.STRING:
                return data.decode('utf-8', errors='ignore')
        except struct.error as e:
            raise ValueError(f"Failed to unpack value: {e}")
        
        raise ValueError(f"Unknown value type: {value_type}")
    
    def scan_exact_value_parallel(
        self,
        value: ScanValue,
        value_type: ValueType = ValueType.INT_32,
        from_scratch: bool = True,
        max_workers: int = 4,
        timeout: float = 30.0
    ) -> int:
        """
        Scan for an exact value using parallel multi-threading.
        
        This is significantly faster than sequential scanning for large memory spaces.
        
        Args:
            value: Value to search for
            value_type: Type of the value
            from_scratch: If True, start new scan
            max_workers: Number of parallel threads (default: 4)
            timeout: Maximum time in seconds for the scan (default: 30.0)
            
        Returns:
            int: Number of results found
        """
        if not self.is_attached():
            raise RuntimeError("Not attached to process")
        
        if from_scratch:
            self.results = []
            self.previous_values = {}
        
        backend = self.backend
        if not backend:
            return self._manual_scan_exact(value, value_type, from_scratch)
        
        start_time = time.monotonic()
        
        try:
            # Get memory regions and apply prioritization
            all_regions = backend.get_readable_regions()
            
            if not all_regions:
                return 0
            
            # Apply region prioritization for faster scanning
            regions = self.get_prioritized_regions(all_regions)
            
            # Prepare scan parameters
            value_bytes = self._pack_value(value, value_type)
            type_size = self._get_type_size(value_type)
            
            # Thread-safe results collection
            results_lock = threading.Lock()
            thread_results: List[ScanResult] = []
            timed_out = False
            
            def scan_region_task(region: MemoryRegion) -> List[ScanResult]:
                """Worker function to scan a single region."""
                local_results: List[ScanResult] = []
                
                try:
                    if time.monotonic() - start_time > timeout:
                        return local_results
                    
                    # Read entire region via backend
                    data = backend.read_bytes(
                        region['address'],
                        region['size']
                    )
                    
                    if not data or len(data) < type_size:
                        return local_results
                    
                    # Search for value in data
                    value_pattern = value_bytes
                    pos = 0
                    
                    while pos <= len(data) - type_size:
                        if time.monotonic() - start_time > timeout:
                            break
                        
                        # Find next occurrence
                        found_pos = data.find(value_pattern, pos)
                        
                        if found_pos == -1:
                            break
                        
                        # Calculate actual address
                        address = region['address'] + found_pos
                        
                        # Read and verify value
                        current_data = data[found_pos:found_pos + type_size]
                        if current_data:
                            current_value = self._unpack_value(current_data, value_type)
                            local_results.append(ScanResult(
                                address=address,
                                value=current_value,
                                value_type=value_type
                            ))
                        
                        pos = found_pos + 1
                    
                except Exception:
                    # Skip regions that can't be read
                    pass
                
                return local_results
            
            # Execute parallel scan
            remaining = max(0.1, timeout - (time.monotonic() - start_time))
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                # Submit all region scans
                future_to_region = {
                    executor.submit(scan_region_task, region): region
                    for region in regions
                }
                
                # Collect results as they complete
                for future in as_completed(future_to_region, timeout=remaining):
                    try:
                        region_results = future.result()
                        with results_lock:
                            thread_results.extend(region_results)
                    except Exception:
                        # Ignore failed regions
                        pass
            
            if time.monotonic() - start_time > timeout:
                print(f"Parallel scan timed out after {timeout:.1f} seconds")
            
            self.results = thread_results
            return len(self.results)
            
        except Exception as e:
            print(f"Parallel scan error: {e}")
            return 0
    
    def scan_exact_value(
        self,
        value: ScanValue,
        value_type: ValueType = ValueType.INT_32,
        from_scratch: bool = True,
        timeout: float = 30.0
    ) -> int:
        """
        Scan for an exact value.
        
        Args:
            value: Value to search for
            value_type: Type of the value
            from_scratch: If True, start new scan; if False, filter previous results
            timeout: Maximum time in seconds for the scan (default: 30.0)
            
        Returns:
            int: Number of results found
        """
        if not self.is_attached():
            raise RuntimeError("Not attached to process")
        
        if from_scratch:
            self.results = []
            self.previous_values = {}
        
        start_time = time.monotonic()
        
        # Use backend if available
        if self.backend:
            try:
                # Convert value to bytes
                value_bytes = self._pack_value(value, value_type)
                
                # Search memory via backend
                addresses = self.backend.search_bytes(value_bytes)
                
                type_size = self._get_type_size(value_type)
                for addr in addresses:
                    if time.monotonic() - start_time > timeout:
                        logger.warning("Scan timed out after %.1f seconds", timeout)
                        break
                    
                    # Read current value
                    current_data = self.backend.read_bytes(addr, type_size)
                    if current_data:
                        current_value = self._unpack_value(current_data, value_type)
                        self.results.append(ScanResult(
                            address=addr,
                            value=current_value,
                            value_type=value_type
                        ))
                
                return len(self.results)
                
            except Exception as e:
                logger.error("Scan error: %s", e)
                return 0
        
        # Fallback: Manual scanning (simplified, less efficient)
        return self._manual_scan_exact(value, value_type, from_scratch)
    
    def _manual_scan_exact(
        self,
        value: ScanValue,
        value_type: ValueType,
        from_scratch: bool
    ) -> int:
        """Manual memory scanning fallback."""
        # This is a simplified implementation
        # In practice, you'd need to read process memory maps and scan each region
        # For now, return 0 to indicate this needs PyMemoryEditor
        print("Manual scanning requires PyMemoryEditor for full functionality")
        return 0
    
    def scan_increased_value(self, value_type: ValueType = ValueType.INT_32, timeout: float = 30.0) -> int:
        """
        Scan for values that increased since last scan.
        
        Args:
            value_type: Type of values to scan
            timeout: Maximum time in seconds for the scan (default: 30.0)
            
        Returns:
            int: Number of results found
        """
        if not self.results:
            raise RuntimeError("No previous scan results. Do an exact value scan first.")
        
        start_time = time.monotonic()
        new_results: List[ScanResult] = []
        
        for result in self.results:
            if time.monotonic() - start_time > timeout:
                print(f"Increased-value scan timed out after {timeout:.1f} seconds")
                break
            
            # Read current value
            current_value = self.read_value(result.address, value_type)
            
            if (
                isinstance(current_value, (int, float))
                and isinstance(result.value, (int, float))
                and current_value > result.value
            ):
                new_results.append(ScanResult(
                    address=result.address,
                    value=current_value,
                    value_type=value_type,
                    previous_value=result.value
                ))
        
        self.results = new_results
        return len(self.results)
    
    def scan_decreased_value(self, value_type: ValueType = ValueType.INT_32, timeout: float = 30.0) -> int:
        """
        Scan for values that decreased since last scan.
        
        Args:
            value_type: Type of values to scan
            timeout: Maximum time in seconds for the scan (default: 30.0)
            
        Returns:
            int: Number of results found
        """
        if not self.results:
            raise RuntimeError("No previous scan results. Do an exact value scan first.")
        
        start_time = time.monotonic()
        new_results: List[ScanResult] = []
        
        for result in self.results:
            if time.monotonic() - start_time > timeout:
                print(f"Decreased-value scan timed out after {timeout:.1f} seconds")
                break
            
            current_value = self.read_value(result.address, value_type)
            
            if (
                isinstance(current_value, (int, float))
                and isinstance(result.value, (int, float))
                and current_value < result.value
            ):
                new_results.append(ScanResult(
                    address=result.address,
                    value=current_value,
                    value_type=value_type,
                    previous_value=result.value
                ))
        
        self.results = new_results
        return len(self.results)
    
    def read_value(self, address: int, value_type: ValueType = ValueType.INT_32) -> Optional[ScanValue]:
        """
        Read a value from memory.
        
        Args:
            address: Memory address
            value_type: Type of value to read
            
        Returns:
            Optional[ScanValue]: Read value or None if failed
        """
        if not self.is_attached():
            return None
        
        if self.backend:
            try:
                size = self._get_type_size(value_type)
                data = self.backend.read_bytes(address, size)
                if data:
                    return self._unpack_value(data, value_type)
            except Exception as e:
                logger.error("Read error at 0x%08X: %s", address, e)
        
        return None
    
    def write_value(self, address: int, value: ScanValue, value_type: ValueType = ValueType.INT_32) -> bool:
        """
        Write a value to memory.
        
        Args:
            address: Memory address
            value: Value to write
            value_type: Type of value
            
        Returns:
            bool: True if successful
        """
        if not self.is_attached():
            return False
        
        if self.backend:
            try:
                value_bytes = self._pack_value(value, value_type)
                return self.backend.write_bytes(address, value_bytes)
            except Exception as e:
                logger.error("Write error at 0x%08X: %s", address, e)
        
        return False
    
    def freeze_value(self, address: int, value: ScanValue, value_type: ValueType = ValueType.INT_32,
                     interval_ms: int = 50) -> bool:
        """
        Freeze a value at a specific address (continuously writes in background).
        
        Args:
            address: Memory address
            value: Value to freeze
            value_type: Type of value
            interval_ms: Write interval in milliseconds
            
        Returns:
            bool: True if started freezing
        """
        if not self.is_attached():
            return False
        
        from .advanced import MemoryFreezer
        
        # Lazily create the freezer, wired to our backend
        freezer = self._freezer
        if freezer is None:
            freezer = MemoryFreezer(editor=self.backend)
            self._freezer = freezer
        
        # Map ValueType enum to freezer type strings
        type_map = {
            ValueType.INT_8: 'int8',
            ValueType.INT_16: 'int16',
            ValueType.INT_32: 'int32',
            ValueType.INT_64: 'int64',
            ValueType.FLOAT: 'float',
            ValueType.DOUBLE: 'double',
        }
        freeze_type = type_map.get(value_type, 'int32')
        
        return freezer.freeze(
            address=address,
            value=value,
            value_type=freeze_type,
            interval_ms=interval_ms,
            description=f"Frozen {value_type.value} @ 0x{address:08X}"
        )
    
    def unfreeze_value(self, address: int) -> bool:
        """Unfreeze a previously frozen address."""
        if self._freezer:
            return self._freezer.unfreeze(address)
        return False
    
    def unfreeze_all(self) -> int:
        """Unfreeze all frozen addresses."""
        if self._freezer:
            return self._freezer.unfreeze_all()
        return 0
    
    def get_freeze_stats(self) -> FreezeStats:
        """Get statistics about frozen addresses."""
        if self._freezer:
            return cast(FreezeStats, self._freezer.get_stats())
        return {
            'total_frozen': 0,
            'active_frozen': 0,
            'total_writes': 0,
            'total_errors': 0,
            'is_running': False,
        }
    
    def get_results(self) -> List[ScanResult]:
        """
        Get current scan results.
        
        Returns:
            List[ScanResult]: List of scan results
        """
        return self.results
    
    def clear_results(self) -> None:
        """Clear scan results."""
        self.results = []
        self.previous_values = {}
    
    def get_result_count(self) -> int:
        """Get number of scan results."""
        return len(self.results)
    
    def suggest_value_type(
        self,
        address: int,
        results: Optional[List[ScanResult]] = None,
    ) -> Optional[str]:
        """
        Suggest the type of value at an address based on heuristic analysis.
        
        Uses behavioral patterns and context to classify values as:
        - Health: Values that decrease when damaged, typically 100-1000 range
        - Gold/Currency: Large integer values that decrease on spending
        - Ammunition: Integer values that decrease in discrete amounts
        - Timer: Values that count down regularly
        - Flag: Binary or small integer values
        
        Args:
            address: Address to analyze
            results: Optional list of scan results for context
            
        Returns:
            Optional[str]: Suggested type or None if cannot determine
        """
        if not self.backend or not self.is_attached():
            return None
        
        # Read current value
        current_value = None
        try:
            # Try reading as int32 first
            data = self.backend.read_bytes(address, 4)
            if data:
                current_value = struct.unpack('<i', data)[0]
        except Exception:
            return None
        
        if current_value is None:
            return None
        
        # Heuristic classification
        suggestions = []
        
        # Health heuristic: 100-1000 range, common in games
        if 50 <= current_value <= 10000:
            suggestions.append(('Health', 0.6))
        
        # Gold heuristic: Large values, typically > 100
        if current_value >= 100:
            suggestions.append(('Gold/Currency', 0.5))
        
        # Ammunition heuristic: Discrete values, typically 1-999
        if 1 <= current_value <= 999:
            suggestions.append(('Ammunition', 0.4))
        
        # Timer heuristic: Small positive integers
        if 0 <= current_value <= 100:
            suggestions.append(('Timer', 0.3))
        
        # Flag/boolean heuristic: 0 or 1
        if current_value in (0, 1):
            suggestions.append(('Flag/Boolean', 0.7))
        
        # Check scan history for behavioral patterns
        if results:
            for result in results:
                if result.address == address and result.previous_value is not None:
                    prev = result.previous_value
                    curr = result.value
                    
                    # Decreasing value (likely health, ammo, or resource)
                    if isinstance(curr, (int, float)) and isinstance(prev, (int, float)):
                        if curr < prev:
                            suggestions.append(('Resource (decreasing)', 0.5))
                        
                        # Large decrease (likely damage or spending)
                        if prev - curr > 10:
                            suggestions.append(('Health/Damage', 0.6))
        
        # Return best suggestion
        if suggestions:
            suggestions.sort(key=lambda x: x[1], reverse=True)
            return suggestions[0][0]
        
        return None
    
    def scan_signature(
        self,
        pattern: bytes,
        mask: Optional[str] = None,
        from_scratch: bool = True,
        timeout: float = 30.0
    ) -> int:
        """
        Scan for a byte pattern in memory (signature scanning).
        
        This is much faster than value scanning for finding known code patterns,
        pointers, or static addresses.
        
        Args:
            pattern: Byte pattern to search for
            mask: Optional mask string where 'x' means match, '?' means wildcard
                  Example: 'xx??x??' matches pattern with wildcards at positions 2,3,5,7
                  If None, exact match required
            from_scratch: If True, start new scan; if False, not applicable for signatures
            timeout: Maximum time in seconds for the scan (default: 30.0)
            
        Returns:
            int: Number of matches found
        """
        if not self.is_attached():
            raise RuntimeError("Not attached to process")
        
        if from_scratch:
            self.results = []
        
        if not self.backend:
            logger.warning("Signature scanning requires a memory backend")
            return 0
        
        start_time = time.monotonic()
        
        try:
            # Get memory regions to scan
            regions = self.backend.get_readable_regions()
            
            for region in regions:
                if time.monotonic() - start_time > timeout:
                    logger.warning("Signature scan timed out after %.1f seconds", timeout)
                    break
                
                try:
                    # Read entire region via backend
                    data = self.backend.read_bytes(
                        region['address'],
                        region['size']
                    )
                    
                    if not data:
                        continue
                    
                    # Search for pattern in data
                    matches = self._find_pattern(data, pattern, mask)
                    
                    for offset in matches:
                        address = region['address'] + offset
                        self.results.append(ScanResult(
                            address=address,
                            value=f"Pattern match at +{offset:X}",
                            value_type=ValueType.STRING
                        ))
                    
                except Exception as region_error:
                    # Skip unreadable regions
                    continue
            
            return len(self.results)
            
        except Exception as e:
            print(f"Signature scan error: {e}")
            return 0
    
    def _get_readable_memory_regions(self) -> List[MemoryRegion]:
        """
        Get list of readable memory regions from the process.
        Delegates to the backend.
        
        Returns:
            List[MemoryRegion]: List of region dictionaries with 'address' and 'size'
        """
        if self.backend:
            return self.backend.get_readable_regions()
        return []
    
    def _find_pattern(
        self,
        data: bytes,
        pattern: bytes,
        mask: Optional[str] = None
    ) -> List[int]:
        """
        Find all occurrences of a pattern in data buffer.
        
        Args:
            data: Data buffer to search
            pattern: Pattern bytes
            mask: Optional mask ('x' = match, '?' = wildcard)
            
        Returns:
            List[int]: List of offsets where pattern found
        """
        matches: List[int] = []
        
        if not pattern:
            return matches
        
        # If no mask, use simple bytes search
        if mask is None:
            start = 0
            while True:
                pos = data.find(pattern, start)
                if pos == -1:
                    break
                matches.append(pos)
                start = pos + 1
            return matches
        
        # With mask, need manual comparison
        pattern_len = len(pattern)
        data_len = len(data)
        
        for i in range(data_len - pattern_len + 1):
            match = True
            
            for j in range(pattern_len):
                if mask[j] == 'x' and data[i + j] != pattern[j]:
                    match = False
                    break
            
            if match:
                matches.append(i)
        
        return matches
    
    def scan_region(
        self,
        start: int,
        end: int,
        pattern: bytes,
        mask: Optional[str] = None
    ) -> List[int]:
        """
        Scan a specific memory region for a pattern.
        
        Args:
            start: Start address
            end: End address
            pattern: Byte pattern
            mask: Optional mask
            
        Returns:
            List[int]: List of matching addresses
        """
        if not self.is_attached() or not self.backend:
            return []
        
        try:
            size = end - start
            data = self.backend.read_bytes(start, size)
            
            if not data:
                return []
            
            offsets = self._find_pattern(data, pattern, mask)
            return [start + offset for offset in offsets]
            
        except Exception:
            return []

    # ------------------------------------------------------------------
    # Pointer chain scanning
    # ------------------------------------------------------------------

    def scan_pointers(self, base_address: int, offsets: List[int]) -> Optional[int]:
        """
        Follow a pointer chain starting from *base_address*.

        At each level the method reads an 8-byte (64-bit) or 4-byte
        (32-bit) pointer, adds the next offset, and dereferences again
        until the chain is exhausted.

        Args:
            base_address: Starting memory address.
            offsets:      List of offsets to apply at each dereference level.

        Returns:
            The final resolved address, or ``None`` if any read fails.
        """
        if not self.is_attached() or not self.backend:
            return None

        address = base_address
        for offset in offsets:
            try:
                data = self.backend.read_bytes(address, 8)
                if not data or len(data) < 4:
                    logger.warning("Pointer read failed at 0x%08X", address)
                    return None

                # Try 64-bit first, fall back to 32-bit
                if len(data) >= 8:
                    ptr = struct.unpack('<Q', data[:8])[0]
                    if ptr > 0x7FFFFFFFFFFF:
                        ptr = struct.unpack('<I', data[:4])[0]
                else:
                    ptr = struct.unpack('<I', data[:4])[0]

                if ptr == 0:
                    logger.warning("Null pointer at 0x%08X", address)
                    return None

                address = ptr + offset
            except Exception as exc:
                logger.error("scan_pointers failed at 0x%08X: %s", address, exc)
                return None

        return address

    # ------------------------------------------------------------------
    # AOB (Array of Bytes) convenience scanner
    # ------------------------------------------------------------------

    def scan_aob(self, signature: str, max_results: int = 100,
                 timeout: float = 30.0) -> List[int]:
        """
        Scan memory for an AOB (Array of Bytes) pattern string.

        The pattern uses hex bytes separated by spaces.  Use ``??``
        as a wildcard for any single byte.

        Example::

            addresses = scanner.scan_aob("89 5D ?? ?? 8B 45")

        Args:
            signature:   Pattern string, e.g. ``"89 5D ?? ?? 8B 45"``.
            max_results: Maximum number of matches to return.
            timeout:     Scan timeout in seconds.

        Returns:
            List of matching memory addresses.
        """
        if not self.is_attached() or not self.backend:
            return []

        from .advanced import AOBPattern, AOBScanner

        pattern = AOBPattern(
            name='scan_aob_query',
            pattern=signature,
            description='User AOB scan',
        )
        aob = AOBScanner(editor=self.backend)
        return aob.scan(
            pattern,
            max_results=max_results,
            timeout=timeout,
        )
