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
import sys
from typing import Any, List, Optional, Type, TypedDict
from abc import ABC, abstractmethod

from src.utils.platform import get_platform, is_proton


import time
import ctypes
from ctypes import POINTER, Structure, byref, c_bool, c_char_p, c_int, c_size_t, c_ubyte, c_uint32, c_uint64, c_void_p

# --- DMA VMM.DLL CTYPES BINDINGS ---
class VMMDLL_SCATTER_DATA(Structure):
    _fields_ = [
        ("qwA", c_uint64),
        ("pb", POINTER(c_ubyte)),
        ("cb", c_uint32),
        ("f", c_uint32),
        ("cbRead", c_uint32),
    ]

class VMMDLL_MAP_PHYSMEM_ENTRY(Structure):
    _fields_ = [
        ("pa", c_uint64),
        ("cb", c_uint64),
    ]

class VMMDLL_MAP_PHYSMEM(Structure):
    _fields_ = [
        ("dwVersion", c_uint32),
        ("cMap", c_uint32),
        ("pMap", POINTER(VMMDLL_MAP_PHYSMEM_ENTRY)),
    ]

try:
    if sys.platform == 'win32':
        _vmm = ctypes.WinDLL('vmm.dll')
    else:
        _vmm = ctypes.CDLL('vmm.so')

    _VMMDLL_Initialize = _vmm.VMMDLL_Initialize
    _VMMDLL_Initialize.argtypes = [c_int, POINTER(c_char_p)]
    _VMMDLL_Initialize.restype = c_void_p

    _VMMDLL_Close = _vmm.VMMDLL_Close
    _VMMDLL_Close.argtypes = [c_void_p]
    _VMMDLL_Close.restype = None

    _VMMDLL_MemReadScatter = _vmm.VMMDLL_MemReadScatter
    _VMMDLL_MemReadScatter.argtypes = [c_void_p, c_uint32, c_uint32, POINTER(VMMDLL_SCATTER_DATA)]
    _VMMDLL_MemReadScatter.restype = c_uint32

    _VMMDLL_MemWrite = _vmm.VMMDLL_MemWrite
    _VMMDLL_MemWrite.argtypes = [c_void_p, c_uint32, c_uint64, POINTER(c_ubyte), c_uint32]
    _VMMDLL_MemWrite.restype = c_bool

    _VMMDLL_Map_GetPhysMem = _vmm.VMMDLL_Map_GetPhysMem
    _VMMDLL_Map_GetPhysMem.argtypes = [c_void_p, POINTER(POINTER(VMMDLL_MAP_PHYSMEM))]
    _VMMDLL_Map_GetPhysMem.restype = c_bool

    _VMMDLL_MemFree = _vmm.VMMDLL_MemFree
    _VMMDLL_MemFree.argtypes = [c_void_p]
    _VMMDLL_MemFree.restype = None

    VMM_AVAILABLE = True
except Exception as e:
    VMM_AVAILABLE = False


logger = logging.getLogger('napoleon.memory.backend')


class MemoryRegion(TypedDict):
    """Readable process memory region."""
    address: int
    size: int


class MemoryBackend(ABC):
    """Abstract memory access backend."""
    
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



class DMABackend(MemoryBackend):
    """
    High-speed DMA backend interfacing with PCIe Leech / FPGA hardware.
    Utilizes scatter/gather for reads and implements page-level caching to
    mitigate hardware latency.
    """

    CACHE_TTL = 0.05  # 50ms cache TTL
    PAGE_SIZE = 4096

    def __init__(self) -> None:
        self._hVMM: Optional[c_void_p] = None
        self._pid: Optional[int] = None
        self._cache: dict = {}  # {page_addr: (timestamp, bytes)}

    def open(self, pid: int) -> bool:
        if not VMM_AVAILABLE:
            return False
        try:
            args = [b"-printf", b"-v", b"-device", b"fpga"]
            argv = (c_char_p * len(args))(*args)
            self._hVMM = _VMMDLL_Initialize(len(args), argv)
            if not self._hVMM:
                return False
            self._pid = pid
            logger.info("DMABackend opened PID %d via PCIe FPGA", pid)
            return True
        except Exception as e:
            logger.error("DMABackend open failed: %s", e)
            return False

    def close(self) -> None:
        if self._hVMM:
            try:
                _VMMDLL_Close(self._hVMM)
            except Exception:
                pass
            self._hVMM = None
            self._pid = None
            self._cache.clear()

    @property
    def is_open(self) -> bool:
        return self._hVMM is not None

    def _read_scatter_pages(self, page_addrs: List[int]) -> None:
        if not self._hVMM or not self._pid:
            return

        now = time.monotonic()
        to_read = [p for p in page_addrs if p not in self._cache or (now - self._cache[p][0]) > self.CACHE_TTL]
        if not to_read:
            return

        flags = 0
        scatter_array = (VMMDLL_SCATTER_DATA * len(to_read))()
        buffers = []

        for i, pa in enumerate(to_read):
            buf = (c_ubyte * self.PAGE_SIZE)()
            buffers.append(buf)
            scatter_array[i].qwA = pa
            scatter_array[i].pb = ctypes.cast(buf, POINTER(c_ubyte))
            scatter_array[i].cb = self.PAGE_SIZE
            scatter_array[i].f = flags

        _VMMDLL_MemReadScatter(self._hVMM, self._pid, len(to_read), scatter_array)

        for i, pa in enumerate(to_read):
            if scatter_array[i].cbRead > 0:
                self._cache[pa] = (now, bytes(buffers[i][:scatter_array[i].cbRead]))
            else:
                self._cache[pa] = (now, b'')

    def read_bytes(self, address: int, size: int) -> Optional[bytes]:
        if not self._hVMM or not self._pid:
            return None

        start_page = address & ~(self.PAGE_SIZE - 1)
        end_page = (address + size - 1) & ~(self.PAGE_SIZE - 1)

        needed_pages = []
        p = start_page
        while p <= end_page:
            needed_pages.append(p)
            p += self.PAGE_SIZE

        self._read_scatter_pages(needed_pages)

        result = bytearray()
        curr_addr = address
        remaining = size

        while remaining > 0:
            page = curr_addr & ~(self.PAGE_SIZE - 1)
            page_offset = curr_addr - page
            chunk_size = min(remaining, self.PAGE_SIZE - page_offset)

            cached_data = self._cache.get(page)
            if not cached_data or not cached_data[1]:
                return None

            page_bytes = cached_data[1]
            if page_offset + chunk_size > len(page_bytes):
                return None

            result.extend(page_bytes[page_offset:page_offset + chunk_size])
            curr_addr += chunk_size
            remaining -= chunk_size

        return bytes(result)

    def write_bytes(self, address: int, data: bytes) -> bool:
        if not self._hVMM or not self._pid:
            return False

        buf = (c_ubyte * len(data)).from_buffer_copy(data)
        res = _VMMDLL_MemWrite(self._hVMM, self._pid, address, buf, len(data))

        start_page = address & ~(self.PAGE_SIZE - 1)
        end_page = (address + len(data) - 1) & ~(self.PAGE_SIZE - 1)
        p = start_page
        while p <= end_page:
            self._cache.pop(p, None)
            p += self.PAGE_SIZE

        return bool(res)

    def get_readable_regions(self) -> List[MemoryRegion]:
        if not self._hVMM:
            return []
        return [
            {'address': 0x00400000, 'size': 0x02000000},
            {'address': 0x10000000, 'size': 0x10000000},
        ]

    def get_physical_regions(self) -> List[MemoryRegion]:
        if not self._hVMM:
            return []

        pMap = POINTER(VMMDLL_MAP_PHYSMEM)()
        if not _VMMDLL_Map_GetPhysMem(self._hVMM, byref(pMap)):
            return []

        regions = []
        map_struct = pMap.contents
        for i in range(map_struct.cMap):
            entry = map_struct.pMap[i]
            regions.append({'address': entry.pa, 'size': entry.cb})

        _VMMDLL_MemFree(pMap)
        return regions

    def read_physical_bytes(self, address: int, size: int) -> Optional[bytes]:
        if not self._hVMM:
            return None
        flags = 0
        buf = (c_ubyte * size)()
        scatter = VMMDLL_SCATTER_DATA(address, ctypes.cast(buf, POINTER(c_ubyte)), size, flags, 0)
        _VMMDLL_MemReadScatter(self._hVMM, 4, 1, byref(scatter))
        if scatter.cbRead == size:
            return bytes(buf)
        return None

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
            logger.debug("Pymem write error at 0x%X: %s", address, e)
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
        except Exception:
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
        except Exception:
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

    Native Linux should prefer direct /proc access first because it is the
    most reliable option and does not depend on third-party memory libraries.
    Proton/Wine still prefers the Windows-oriented backends first.
    """
    if get_platform() == 'linux':
        if is_proton():
            return [
                DMABackend,
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

    return [
        DMABackend,
        PymemBackend,
        PyMemoryEditorBackend,
        ProcMemBackend,
    ]
