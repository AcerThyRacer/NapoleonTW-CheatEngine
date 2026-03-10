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
            logger.error("PymemBackend.read_bytes: backend not open")
            return None
        try:
            return self._pm.read_bytes(address, size)
        except Exception as e:
            logger.error("Pymem read error at 0x%X (size %d): %s", address, size, e)
            return None
    
    def write_bytes(self, address: int, data: bytes) -> bool:
        if not self._pm:
            logger.error("PymemBackend.write_bytes: backend not open")
            return False
        try:
            self._pm.write_bytes(address, data, len(data))
            return True
        except Exception as e:
            logger.error("Pymem write error at 0x%X: %s", address, e)
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
            logger.error("PyMemoryEditorBackend.read_bytes: backend not open")
            return None
        try:
            return self._editor.read_process_memory(address, bytes, size)
        except Exception as e:
            logger.error("PyMemoryEditor read error at 0x%X (size %d): %s", address, size, e)
            return None
    
    def write_bytes(self, address: int, data: bytes) -> bool:
        if not self._editor:
            logger.error("PyMemoryEditorBackend.write_bytes: backend not open")
            return False
        try:
            self._editor.write_process_memory(address, data)
            return True
        except Exception as e:
            logger.error("PyMemoryEditor write error at 0x%X: %s", address, e)
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
            logger.error("ProcMemBackend.read_bytes: backend not open")
            return None
        try:
            os.lseek(self._mem_fd, address, os.SEEK_SET)
            return os.read(self._mem_fd, size)
        except Exception as e:
            logger.error("ProcMem read error at 0x%X (size %d): %s", address, size, e)
            return None
    
    def write_bytes(self, address: int, data: bytes) -> bool:
        if self._mem_fd is None:
            logger.error("ProcMemBackend.write_bytes: backend not open")
            return False
        try:
            os.lseek(self._mem_fd, address, os.SEEK_SET)
            os.write(self._mem_fd, data)
            return True
        except Exception as e:
            logger.error("ProcMem write error at 0x%X: %s", address, e)
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
                PymemBackend,
                PyMemoryEditorBackend,
                ProcMemBackend,
            ]
        return [
            ProcMemBackend,
            PymemBackend,
            PyMemoryEditorBackend,
        ]

    return [
        PymemBackend,
        PyMemoryEditorBackend,
        ProcMemBackend,
    ]
