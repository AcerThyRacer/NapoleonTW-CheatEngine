"""
Memory backend abstraction layer.

Provides a unified API over multiple memory editing libraries:
- pymem (preferred, well-documented)
- PyMemoryEditor (fallback)
- /proc/<pid>/mem direct access (Linux fallback)

This isolates the rest of the codebase from library-specific API differences.
"""

import logging
import os
import struct
import sys
import time
from typing import Any, Dict, List, Optional, Tuple, Type, TypedDict
from abc import ABC, abstractmethod

from src.utils.platform import get_platform, is_proton

logger = logging.getLogger('napoleon.memory.backend')


class MemoryRegion(TypedDict):
    """Readable process memory region."""
    address: int
    size: int


class MemoryBackend(ABC):
    """Abstract memory access backend."""
    
    def __init__(self) -> None:
        self._region_cache: List[MemoryRegion] = []
        self._region_cache_time: float = 0.0
        self._region_cache_ttl: float = 2.0  # 2 second TTL
    
    @abstractmethod
    def open(self, pid: int) -> bool:
        """Open/attach to a process."""
        ...
    
    @abstractmethod
    def close(self) -> None:
        """Close/detach from the process."""
        ...
    
    @abstractmethod
    def read_bytes(self, address: int, size: int) -> Optional[bytes]:
        """Read raw bytes from process memory."""
        ...
    
    @abstractmethod
    def write_bytes(self, address: int, data: bytes) -> bool:
        """Write raw bytes to process memory."""
        ...
    
    @abstractmethod
    def get_readable_regions(self) -> List[MemoryRegion]:
        """Get list of readable memory regions: [{'address': int, 'size': int}]."""
        ...
    
    @property
    @abstractmethod
    def is_open(self) -> bool:
        """Whether the backend is attached to a process."""
        ...
    
    def is_valid_address(self, address: int, size: int = 4) -> bool:
        """
        Validate if an address is within readable/writable memory regions.
        Uses cached regions with TTL to avoid performance penalty.
        
        Args:
            address: Address to validate
            size: Size of memory access
            
        Returns:
            bool: True if address is valid
        """
        import time
        
        current_time = time.time()
        
        # Refresh cache if expired
        if (current_time - self._region_cache_time) > self._region_cache_ttl:
            self._region_cache = self.get_readable_regions()
            self._region_cache_time = current_time
        
        # Check if address falls within any region
        for region in self._region_cache:
            region_start = region['address']
            region_end = region_start + region['size']
            
            if address >= region_start and (address + size) <= region_end:
                return True
        
        return False
    
    def search_bytes(
        self,
        pattern: bytes,
        regions: Optional[List[MemoryRegion]] = None
    ) -> List[int]:
        """
        Search for a byte pattern across all readable regions.
        Default implementation — backends can override for speed.
        """
        if regions is None:
            regions = self.get_readable_regions()
        
        results: List[int] = []
        for region in regions:
            data = self.read_bytes(region['address'], region['size'])
            if not data:
                continue
            
            start = 0
            while True:
                pos = data.find(pattern, start)
                if pos == -1:
                    break
                results.append(region['address'] + pos)
                start = pos + 1
        
        return results


class PymemBackend(MemoryBackend):
    """Backend using pymem library (preferred on Windows, works on Linux with Wine)."""
    
    def __init__(self) -> None:
        self._pm: Optional[Any] = None
        self._pid: Optional[int] = None
    
    def open(self, pid: int) -> bool:
        try:
            import pymem
            self._pm = pymem.Pymem()
            self._pm.open_process_from_id(pid)
            self._pid = pid
            logger.info("Pymem backend opened PID %d", pid)
            return True
        except ImportError:
            logger.debug("pymem not available")
            return False
        except Exception as e:
            logger.error("Pymem open failed: %s", e)
            self._pm = None
            return False
    
    def close(self) -> None:
        if self._pm:
            try:
                self._pm.close_process()
            except Exception:
                pass
            self._pm = None
            self._pid = None
    
    def read_bytes(self, address: int, size: int) -> Optional[bytes]:
        if not self._pm:
            return None
        try:
            return self._pm.read_bytes(address, size)
        except Exception:
            return None
    
    def write_bytes(self, address: int, data: bytes) -> bool:
        if not self._pm:
            return False
        try:
            self._pm.write_bytes(address, data, len(data))
            return True
        except Exception as e:
            logger.error(
                "Pymem write failed at 0x%X (size=%d): %s - %s",
                address, len(data), type(e).__name__, str(e),
                extra={'details': f'address=0x{address:X}, size={len(data)}'}
            )
            return False
    
    def get_readable_regions(self) -> List[MemoryRegion]:
        if not self._pm or not self._pid:
            return []
        try:
            import pymem.process
            regions: List[MemoryRegion] = []
            for module in pymem.process.enum_process_module(self._pm.process_handle):
                regions.append({
                    'address': module.lpBaseOfDll,
                    'size': module.SizeOfImage,
                })
            return regions
        except Exception:
            return self._fallback_regions()
    
    def _fallback_regions(self) -> List[MemoryRegion]:
        """Fallback region list if module enumeration fails."""
        return [
            {'address': 0x00400000, 'size': 0x02000000},
            {'address': 0x10000000, 'size': 0x10000000},
        ]
    
    @property
    def is_open(self) -> bool:
        return self._pm is not None
    
    def search_bytes(
        self,
        pattern: bytes,
        regions: Optional[List[MemoryRegion]] = None
    ) -> List[int]:
        """Override with pymem's native pattern scan if available."""
        if self._pm:
            try:
                import pymem.pattern
                result = pymem.pattern.pattern_scan_all(self._pm.process_handle, pattern)
                if result is not None:
                    return result if isinstance(result, list) else [result]
            except Exception:
                pass
        return super().search_bytes(pattern, regions)


class PyMemoryEditorBackend(MemoryBackend):
    """Backend using PyMemoryEditor library."""
    
    def __init__(self) -> None:
        self._editor: Optional[Any] = None
        self._pid: Optional[int] = None
    
    def open(self, pid: int) -> bool:
        try:
            from PyMemoryEditor import OpenProcess
            self._editor = OpenProcess(pid)
            self._pid = pid
            logger.info("PyMemoryEditor backend opened PID %d", pid)
            return True
        except ImportError:
            logger.debug("PyMemoryEditor not available")
            return False
        except Exception as e:
            logger.error("PyMemoryEditor open failed: %s", e)
            self._editor = None
            return False
    
    def close(self) -> None:
        if self._editor:
            try:
                self._editor.close()
            except Exception:
                pass
            self._editor = None
            self._pid = None
    
    def read_bytes(self, address: int, size: int) -> Optional[bytes]:
        if not self._editor:
            return None
        try:
            return self._editor.read_process_memory(address, bytes, size)
        except Exception:
            return None
    
    def write_bytes(self, address: int, data: bytes) -> bool:
        if not self._editor:
            return False
        try:
            self._editor.write_process_memory(address, data)
            return True
        except Exception as e:
            logger.error(
                "PyMemoryEditor write failed at 0x%X (size=%d): %s - %s",
                address, len(data), type(e).__name__, str(e),
                extra={'details': f'address=0x{address:X}, size={len(data)}'}
            )
            return False
    
    def get_readable_regions(self) -> List[MemoryRegion]:
        # PyMemoryEditor doesn't expose region enumeration directly
        return [
            {'address': 0x00400000, 'size': 0x02000000},
            {'address': 0x10000000, 'size': 0x10000000},
        ]
    
    @property
    def is_open(self) -> bool:
        return self._editor is not None


class ProcMemBackend(MemoryBackend):
    """Direct /proc/<pid>/mem access for Linux."""
    
    def __init__(self) -> None:
        self._pid: Optional[int] = None
        self._mem_fd: Optional[int] = None
    
    def open(self, pid: int) -> bool:
        if sys.platform != 'linux':
            return False
        try:
            mem_path = f"/proc/{pid}/mem"
            self._mem_fd = os.open(mem_path, os.O_RDWR)
            self._pid = pid
            logger.info("ProcMem backend opened PID %d", pid)
            return True
        except (OSError, PermissionError) as e:
            logger.debug("ProcMem open failed: %s", e)
            try:
                # Try read-only
                mem_path = f"/proc/{pid}/mem"
                self._mem_fd = os.open(mem_path, os.O_RDONLY)
                self._pid = pid
                logger.info("ProcMem backend opened PID %d (read-only)", pid)
                return True
            except Exception:
                return False
    
    def close(self) -> None:
        if self._mem_fd is not None:
            try:
                os.close(self._mem_fd)
            except Exception:
                pass
            self._mem_fd = None
            self._pid = None
    
    def read_bytes(self, address: int, size: int) -> Optional[bytes]:
        if self._mem_fd is None:
            return None
        try:
            os.lseek(self._mem_fd, address, os.SEEK_SET)
            return os.read(self._mem_fd, size)
        except Exception:
            return None
    
    def write_bytes(self, address: int, data: bytes) -> bool:
        if self._mem_fd is None:
            return False
        try:
            os.lseek(self._mem_fd, address, os.SEEK_SET)
            os.write(self._mem_fd, data)
            return True
        except Exception as e:
            logger.error(
                "ProcMem write failed at 0x%X (size=%d): %s - %s",
                address, len(data), type(e).__name__, str(e),
                extra={'details': f'address=0x{address:X}, size={len(data)}, pid={self._pid}'}
            )
            return False
    
    def get_readable_regions(self) -> List[MemoryRegion]:
        if not self._pid:
            return []
        regions: List[MemoryRegion] = []
        try:
            maps_path = f"/proc/{self._pid}/maps"
            with open(maps_path, 'r') as f:
                for line in f:
                    parts = line.split()
                    if len(parts) < 2 or 'r' not in parts[1]:
                        continue
                    addr_range = parts[0].split('-', 1)
                    if len(addr_range) != 2:
                        continue
                    try:
                        start = int(addr_range[0], 16)
                        end = int(addr_range[1], 16)
                    except ValueError:
                        continue
                    if end <= start:
                        continue
                    regions.append({'address': start, 'size': end - start})
        except Exception as e:
            logger.debug("Failed to read /proc/%d/maps: %s", self._pid, e)
        return regions
    
    @property
    def is_open(self) -> bool:
        return self._mem_fd is not None


class HypervisorBackend(MemoryBackend):
    """
    Hypervisor-based memory backend using EPT shadow hooking.
    
    This backend uses a lightweight hypervisor or kernel driver for stealthy
    memory operations. It implements Extended Page Table (EPT) shadow hooking
    to serve unmodified pages when the anti-cheat reads memory, while patched
    pages are used during normal execution.
    
    Windows only - requires a hypervisor driver with appropriate IOCTLs.
    """
    
    # Standard IOCTL codes for hypervisor communication
    IOCTL_HV_ATTACH = 0x80002000
    IOCTL_HV_DETACH = 0x80002004
    IOCTL_HV_READ = 0x80002008
    IOCTL_HV_WRITE = 0x8000200C
    IOCTL_HV_MAP_EPT_HOOK = 0x80002010
    IOCTL_HV_READ_ORIGINAL = 0x80002014
    
    def __init__(self) -> None:
        self._pid: Optional[int] = None
        self._device_handle: Optional[Any] = None
        self._hooked_pages: Dict[int, bytes] = {}  # page_addr -> original_bytes
    
    def open(self, pid: int) -> bool:
        """Attach to process via hypervisor."""
        if sys.platform != 'win32':
            logger.debug("HypervisorBackend only available on Windows")
            return False
        
        try:
            import ctypes
            from ctypes import wintypes
            
            # Load kernel32 for CreateFile
            kernel32 = ctypes.windll.kernel32
            kernel32.CreateFileW.argtypes = [
                wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD,
                ctypes.c_void_p, wintypes.DWORD, wintypes.DWORD, wintypes.HANDLE
            ]
            kernel32.CreateFileW.restype = wintypes.HANDLE
            
            kernel32.DeviceIoControl.argtypes = [
                wintypes.HANDLE, wintypes.DWORD, ctypes.c_void_p, wintypes.DWORD,
                ctypes.c_void_p, wintypes.DWORD, ctypes.POINTER(wintypes.DWORD), ctypes.c_void_p
            ]
            kernel32.DeviceIoControl.restype = wintypes.BOOL
            
            # Open hypervisor device
            device_path = r"\\.\NapoleonHypervisor"
            handle = kernel32.CreateFileW(
                device_path,
                0x80000000 | 0x40000000,  # GENERIC_READ | GENERIC_WRITE
                0,  # No sharing
                None,  # No security
                3,  # OPEN_EXISTING
                0,  # No flags
                None  # No template
            )
            
            if handle == -1 or handle is None:
                logger.debug("Failed to open hypervisor device")
                return False
            
            self._device_handle = handle
            
            # Attach to process
            attach_struct = struct.pack('<I', pid)
            bytes_returned = wintypes.DWORD()
            result = kernel32.DeviceIoControl(
                handle,
                self.IOCTL_HV_ATTACH,
                attach_struct,
                len(attach_struct),
                None,
                0,
                ctypes.byref(bytes_returned),
                None
            )
            
            if not result:
                logger.debug("Failed to attach to process %d via hypervisor", pid)
                kernel32.CloseHandle(handle)
                self._device_handle = None
                return False
            
            self._pid = pid
            logger.info("Hypervisor backend opened PID %d", pid)
            return True
            
        except Exception as e:
            logger.debug("Hypervisor backend open failed: %s", e)
            if self._device_handle:
                try:
                    kernel32.CloseHandle(self._device_handle)
                except Exception:
                    pass
                self._device_handle = None
            return False
    
    def close(self) -> None:
        """Detach from process."""
        if self._device_handle is None:
            return
        
        try:
            import ctypes
            from ctypes import wintypes
            kernel32 = ctypes.windll.kernel32
            
            # Detach
            detach_struct = struct.pack('<I', self._pid or 0)
            bytes_returned = wintypes.DWORD()
            kernel32.DeviceIoControl(
                self._device_handle,
                self.IOCTL_HV_DETACH,
                detach_struct,
                len(detach_struct),
                None,
                0,
                ctypes.byref(bytes_returned),
                None
            )
            
            kernel32.CloseHandle(self._device_handle)
        except Exception:
            pass
        finally:
            self._device_handle = None
            self._pid = None
            self._hooked_pages.clear()
    
    def read_bytes(self, address: int, size: int) -> Optional[bytes]:
        """Read memory via hypervisor."""
        if self._device_handle is None:
            return None
        
        try:
            import ctypes
            from ctypes import wintypes
            kernel32 = ctypes.windll.kernel32
            
            # Read structure: address (8) + size (4)
            read_struct = struct.pack('<QI', address, size)
            buffer = ctypes.create_string_buffer(size)
            bytes_returned = wintypes.DWORD()
            
            result = kernel32.DeviceIoControl(
                self._device_handle,
                self.IOCTL_HV_READ,
                read_struct,
                len(read_struct),
                buffer,
                size,
                ctypes.byref(bytes_returned),
                None
            )
            
            if result and bytes_returned.value == size:
                return buffer.raw
            return None
            
        except Exception as e:
            logger.error(
                "Hypervisor read failed at 0x%X (size=%d): %s",
                address, size, str(e),
                extra={'details': f'address=0x{address:X}, size={size}'}
            )
            return None
    
    def write_bytes(self, address: int, data: bytes) -> bool:
        """Write memory via hypervisor."""
        if self._device_handle is None:
            return False
        
        try:
            import ctypes
            from ctypes import wintypes
            kernel32 = ctypes.windll.kernel32
            
            # Write structure: address (8) + size (4) + data
            write_struct = struct.pack('<QI', address, len(data)) + data
            bytes_returned = wintypes.DWORD()
            
            result = kernel32.DeviceIoControl(
                self._device_handle,
                self.IOCTL_HV_WRITE,
                write_struct,
                len(write_struct),
                None,
                0,
                ctypes.byref(bytes_returned),
                None
            )
            
            return bool(result)
            
        except Exception as e:
            logger.error(
                "Hypervisor write failed at 0x%X (size=%d): %s",
                address, len(data), str(e),
                extra={'details': f'address=0x{address:X}, size={len(data)}'}
            )
            return False
    
    def get_readable_regions(self) -> List[MemoryRegion]:
        """Get readable regions via hypervisor."""
        if not self._pid:
            return []
        
        # Hypervisor can provide full memory map
        # For now, use standard Windows enumeration
        try:
            import pymem
            import pymem.process
            pm = pymem.Pymem()
            pm.open_process_from_id(self._pid)
            regions: List[MemoryRegion] = []
            for module in pymem.process.enum_process_module(pm.process_handle):
                regions.append({
                    'address': module.lpBaseOfDll,
                    'size': module.SizeOfImage,
                })
            pm.close_process()
            return regions
        except Exception:
            return [
                {'address': 0x00400000, 'size': 0x02000000},
                {'address': 0x10000000, 'size': 0x10000000},
            ]
    
    @property
    def is_open(self) -> bool:
        return self._device_handle is not None
    
    def _map_ept_hook(self, page_address: int, patched_page: bytes) -> bool:
        """
        Map an EPT hook for a 4KB page.
        
        This swaps the physical page mapping so that:
        - Normal execution sees the patched page
        - When anti-cheat reads the page, it sees the original
        
        Args:
            page_address: Aligned page address (4KB boundary)
            patched_page: Patched page bytes (must be 4096 bytes)
            
        Returns:
            bool: True if hook mapped successfully
        """
        if self._device_handle is None or len(patched_page) != 4096:
            return False
        
        try:
            import ctypes
            from ctypes import wintypes
            kernel32 = ctypes.windll.kernel32
            
            # Hook structure: page_addr (8) + patched_data (4096)
            hook_struct = struct.pack('<Q', page_address) + patched_page
            bytes_returned = wintypes.DWORD()
            
            result = kernel32.DeviceIoControl(
                self._device_handle,
                self.IOCTL_HV_MAP_EPT_HOOK,
                hook_struct,
                len(hook_struct),
                None,
                0,
                ctypes.byref(bytes_returned),
                None
            )
            
            if result:
                # Store original for unhook
                original = self.read_original_page(page_address)
                if original:
                    self._hooked_pages[page_address] = original
            
            return bool(result)
            
        except Exception as e:
            logger.error("EPT hook mapping failed for 0x%X: %s", page_address, e)
            return False
    
    def read_original_page(self, page_address: int) -> Optional[bytes]:
        """
        Read the original (unpatched) page bytes.
        
        This is used by the hypervisor to return clean bytes when
        anti-cheat attempts to scan the page.
        
        Args:
            page_address: Aligned page address (4KB boundary)
            
        Returns:
            Original page bytes or None
        """
        if self._device_handle is None:
            return None
        
        try:
            import ctypes
            from ctypes import wintypes
            kernel32 = ctypes.windll.kernel32
            
            read_struct = struct.pack('<Q', page_address)
            buffer = ctypes.create_string_buffer(4096)
            bytes_returned = wintypes.DWORD()
            
            result = kernel32.DeviceIoControl(
                self._device_handle,
                self.IOCTL_HV_READ_ORIGINAL,
                read_struct,
                len(read_struct),
                buffer,
                4096,
                ctypes.byref(bytes_returned),
                None
            )
            
            if result and bytes_returned.value == 4096:
                return buffer.raw
            return None
            
        except Exception:
            return None


class DMABackend(MemoryBackend):
    """
    DMA-based memory backend using PCIe Leech / MemProcFS.
    
    This backend interfaces with custom FPGA hardware or DMA cards to perform
    high-speed asynchronous scatter/gather memory operations directly on
    physical pages, bypassing the OS entirely.
    
    Features:
    - Page-level caching to mitigate hardware latency
    - Asynchronous DMA operations for maximum throughput
    - Physical memory scanning support
    
    Requires vmm.dll (MemProcFS) or custom DMA driver.
    """
    
    # Cache configuration
    CACHE_TTL = 0.5  # 500ms cache TTL
    PAGE_SIZE = 4096  # 4KB pages
    
    def __init__(self) -> None:
        self._pid: Optional[int] = None
        self._vmm: Optional[Any] = None
        self._page_cache: Dict[int, Tuple[bytes, float]] = {}  # page_addr -> (data, timestamp)
        self._scatter_gather_list: List[Tuple[int, int]] = []  # [(addr, size), ...]
    
    def open(self, pid: int) -> bool:
        """Initialize DMA backend."""
        try:
            # Try MemProcFS (vmm.dll) first
            try:
                import ctypes
                vmm = ctypes.CDLL('vmm.dll')
                
                # Initialize VMM
                # MemProcFS VMM_Initialize returns a handle (non-zero = success, 0 = failure)
                result = vmm.VMM_Initialize()
                if result and result != 0:
                    self._vmm = vmm
                    self._pid = pid
                    logger.info("DMA backend opened via MemProcFS PID %d", pid)
                    return True
            except (ImportError, OSError):
                logger.debug("vmm.dll not available")
            
            # Try custom DMA driver
            if sys.platform == 'win32':
                import ctypes
                from ctypes import wintypes
                
                kernel32 = ctypes.windll.kernel32
                device_path = r"\\.\PCILeech"
                
                handle = kernel32.CreateFileW(
                    device_path,
                    0x80000000 | 0x40000000,
                    0, None, 3, 0, None
                )
                
                if handle and handle != -1:
                    self._vmm = handle
                    self._pid = pid
                    logger.info("DMA backend opened via PCILeech PID %d", pid)
                    return True
            
            return False
            
        except Exception as e:
            logger.debug("DMA backend open failed: %s", e)
            return False
    
    def close(self) -> None:
        """Close DMA backend."""
        if self._vmm is None:
            return
        
        try:
            import ctypes
            if hasattr(self._vmm, 'VMM_Close'):
                self._vmm.VMM_Close()
            else:
                kernel32 = ctypes.windll.kernel32
                kernel32.CloseHandle(self._vmm)
        except Exception:
            pass
        finally:
            self._vmm = None
            self._pid = None
            self._page_cache.clear()
            self._scatter_gather_list.clear()
    
    def read_bytes(self, address: int, size: int) -> Optional[bytes]:
        """Read memory via DMA with page caching."""
        if self._vmm is None:
            return None
        
        # Check page cache first
        page_addr = (address // self.PAGE_SIZE) * self.PAGE_SIZE
        current_time = time.time()
        
        if page_addr in self._page_cache:
            cached_data, cache_time = self._page_cache[page_addr]
            if (current_time - cache_time) < self.CACHE_TTL:
                offset = address - page_addr
                if offset + size <= len(cached_data):
                    return cached_data[offset:offset + size]
        
        # Read from DMA
        try:
            import ctypes
            
            if hasattr(self._vmm, 'VMM_ReadScatter'):
                # MemProcFS scatter read
                buffer = ctypes.create_string_buffer(size)
                result = self._vmm.VMM_ReadScatter(
                    self._pid,
                    1,
                    ctypes.byref(ctypes.c_uint64(address)),
                    ctypes.byref(ctypes.c_uint32(size)),
                    buffer
                )
                
                if result > 0:
                    data = buffer.raw[:result]
                else:
                    data = None
            else:
                # PCILeech direct read
                kernel32 = ctypes.windll.kernel32
                from ctypes import wintypes
                
                read_bytes = wintypes.DWORD()
                buffer = ctypes.create_string_buffer(size)
                
                kernel32.SetFilePointerEx(
                    self._vmm,
                    ctypes.c_longlong(address),
                    None,
                    0  # FILE_BEGIN
                )
                
                result = kernel32.ReadFile(
                    self._vmm,
                    buffer,
                    size,
                    ctypes.byref(read_bytes),
                    None
                )
                
                data = buffer.raw[:read_bytes.value] if result else None
            
            # Cache the page
            if data and len(data) == size:
                # Read full page for caching
                page_data = self._read_full_page(page_addr)
                if page_data:
                    self._page_cache[page_addr] = (page_data, current_time)
                
                return data
            
            return None
            
        except Exception as e:
            logger.error(
                "DMA read failed at 0x%X (size=%d): %s",
                address, size, str(e),
                extra={'details': f'address=0x{address:X}, size={size}'}
            )
            return None
    
    def _read_full_page(self, page_address: int) -> Optional[bytes]:
        """Read a full 4KB page for caching."""
        try:
            import ctypes
            
            if hasattr(self._vmm, 'VMM_ReadScatter'):
                buffer = ctypes.create_string_buffer(self.PAGE_SIZE)
                result = self._vmm.VMM_ReadScatter(
                    self._pid,
                    1,
                    ctypes.byref(ctypes.c_uint64(page_address)),
                    ctypes.byref(ctypes.c_uint32(self.PAGE_SIZE)),
                    buffer
                )
                return buffer.raw[:result] if result > 0 else None
            else:
                kernel32 = ctypes.windll.kernel32
                from ctypes import wintypes
                
                read_bytes = wintypes.DWORD()
                buffer = ctypes.create_string_buffer(self.PAGE_SIZE)
                
                kernel32.SetFilePointerEx(
                    self._vmm,
                    ctypes.c_longlong(page_address),
                    None,
                    0
                )
                
                result = kernel32.ReadFile(
                    self._vmm,
                    buffer,
                    self.PAGE_SIZE,
                    ctypes.byref(read_bytes),
                    None
                )
                
                return buffer.raw[:read_bytes.value] if result else None
                
        except Exception:
            return None
    
    def write_bytes(self, address: int, data: bytes) -> bool:
        """Write memory via DMA scatter/gather."""
        if self._vmm is None:
            return False
        
        # Invalidate page cache
        page_addr = (address // self.PAGE_SIZE) * self.PAGE_SIZE
        self._page_cache.pop(page_addr, None)
        
        try:
            import ctypes
            
            if hasattr(self._vmm, 'VMM_WriteScatter'):
                # MemProcFS scatter write
                buffer = ctypes.create_string_buffer(data)
                result = self._vmm.VMM_WriteScatter(
                    self._pid,
                    1,
                    ctypes.byref(ctypes.c_uint64(address)),
                    ctypes.byref(ctypes.c_uint32(len(data))),
                    buffer
                )
                return result > 0
            else:
                # PCILeech direct write
                kernel32 = ctypes.windll.kernel32
                from ctypes import wintypes
                
                written_bytes = wintypes.DWORD()
                buffer = ctypes.create_string_buffer(data)
                
                kernel32.SetFilePointerEx(
                    self._vmm,
                    ctypes.c_longlong(address),
                    None,
                    0
                )
                
                return bool(kernel32.WriteFile(
                    self._vmm,
                    buffer,
                    len(data),
                    ctypes.byref(written_bytes),
                    None
                ))
                
        except Exception as e:
            logger.error(
                "DMA write failed at 0x%X (size=%d): %s",
                address, len(data), str(e),
                extra={'details': f'address=0x{address:X}, size={len(data)}'}
            )
            return False
    
    def get_readable_regions(self) -> List[MemoryRegion]:
        """Get physical memory regions from DMA."""
        if not self._vmm:
            return []
        
        # DMA can access all physical memory
        # Return comprehensive regions
        return [
            {'address': 0x00000000, 'size': 0x80000000},  # Lower 2GB
            {'address': 0x00400000, 'size': 0x10000000},  # Executable region
            {'address': 0x10000000, 'size': 0x70000000},  # Heap/other
        ]
    
    @property
    def is_open(self) -> bool:
        return self._vmm is not None
    
    def search_bytes_physical(
        self,
        pattern: bytes,
        max_results: int = 1000
    ) -> List[int]:
        """
        Search physical memory directly using DMA scatter/gather.
        
        This bypasses virtual memory entirely and scans physical pages.
        Much faster for large memory ranges.
        
        Args:
            pattern: Byte pattern to search for
            max_results: Maximum results to return
            
        Returns:
            List of virtual addresses where pattern was found
        """
        if not self._vmm:
            return []
        
        results: List[int] = []
        
        try:
            import ctypes
            
            # Use MemProcFS physical scan if available
            if hasattr(self._vmm, 'VMM_ScanPhysical'):
                # Allocate result buffer
                result_buffer = (ctypes.c_uint64 * max_results)()
                count = ctypes.c_uint32()
                
                pattern_buffer = ctypes.create_string_buffer(pattern)
                
                result = self._vmm.VMM_ScanPhysical(
                    self._pid,
                    pattern_buffer,
                    len(pattern),
                    result_buffer,
                    max_results,
                    ctypes.byref(count)
                )
                
                if result and count.value > 0:
                    results = [result_buffer[i] for i in range(count.value)]
            
            return results
            
        except Exception as e:
            logger.error("Physical DMA scan failed: %s", e)
            return []


def create_backend(pid: int) -> Optional[MemoryBackend]:
    """
    Create the best available memory backend for the given PID.
    Tries backends in order of preference.
    """
    backends = get_backend_candidates()
    
    for backend_cls in backends:
        backend = backend_cls()
        if backend.open(pid):
            logger.info("Using memory backend: %s", backend_cls.__name__)
            return backend
        logger.debug("Backend %s not available", backend_cls.__name__)
    
    logger.error("No memory backend available for PID %d", pid)
    return None


def get_best_backend() -> Type[MemoryBackend]:
    """Return the preferred backend class for the current platform."""
    return get_backend_candidates()[0]


def get_backend_candidates() -> List[Type[MemoryBackend]]:
    """
    Return backend classes in priority order for the current runtime.

    Priority order (Windows):
    1. HypervisorBackend - Most stealthy (EPT shadow hooking)
    2. DMABackend - Hardware-based, bypasses OS
    3. PymemBackend - Standard Windows memory library
    4. PyMemoryEditorBackend - Alternative Windows library
    5. ProcMemBackend - Linux /proc/mem (fallback)

    Priority order (Linux native):
    1. DMABackend - Hardware-based if available
    2. ProcMemBackend - Direct /proc access
    3. PymemBackend - Wine/pymem
    4. PyMemoryEditorBackend - Alternative

    Priority order (Proton/Wine):
    1. DMABackend - Hardware-based if available
    2. HypervisorBackend - If hypervisor available
    3. PymemBackend - Wine-compatible
    4. PyMemoryEditorBackend - Alternative
    5. ProcMemBackend - Last resort
    """
    if get_platform() == 'linux':
        if is_proton():
            return [
                DMABackend,
                HypervisorBackend,
                PymemBackend,
                PyMemoryEditorBackend,
                ProcMemBackend,
            ]
        return [
            DMABackend,
            ProcMemBackend,
            PymemBackend,
            PyMemoryEditorBackend,
        ]

    # Windows
    return [
        HypervisorBackend,
        DMABackend,
        PymemBackend,
        PyMemoryEditorBackend,
        ProcMemBackend,
    ]
