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

import ctypes
from ctypes import wintypes
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


class HypervisorBackend(MemoryBackend):
    """
    Hardware-assisted backend utilizing EPT (Extended Page Table) hooking
    via a lightweight hypervisor or kernel driver.

    Provides shadow hooking: reads yield original bytes, execution yields patched bytes.
    """

    # Example IOCTLs for a custom hypervisor/driver (placeholder values)
    IOCTL_HV_ATTACH = 0x222000
    IOCTL_HV_DETACH = 0x222004
    IOCTL_HV_READ   = 0x222008
    IOCTL_HV_WRITE  = 0x22200C
    IOCTL_HV_MAP_EPT_HOOK = 0x222010

    def __init__(self) -> None:
        self._pid: Optional[int] = None
        self._driver_handle: Optional[int] = None

    def open(self, pid: int) -> bool:
        if get_platform() != 'windows':
            return False

        try:
            # Open handle to the hypothetical hypervisor driver
            # In a real implementation, you'd CreateFileW to a specific device like "\\\\.\\MyHvDev"
            self._driver_handle = ctypes.windll.kernel32.CreateFileW(
                "\\\\.\\NapoleonHypervisor",
                0xC0000000, # GENERIC_READ | GENERIC_WRITE
                0,
                None,
                3, # OPEN_EXISTING
                0,
                None
            )

            if self._driver_handle == -1: # INVALID_HANDLE_VALUE
                logger.debug("Hypervisor driver not found.")
                self._driver_handle = None
                return False

            # Attach to PID via IOCTL
            bytes_returned = wintypes.DWORD()
            pid_buffer = ctypes.c_uint32(pid)

            success = ctypes.windll.kernel32.DeviceIoControl(
                self._driver_handle,
                self.IOCTL_HV_ATTACH,
                ctypes.byref(pid_buffer),
                ctypes.sizeof(pid_buffer),
                None,
                0,
                ctypes.byref(bytes_returned),
                None
            )

            if not success:
                logger.error("Failed to attach hypervisor to PID %d", pid)
                self.close()
                return False

            self._pid = pid
            logger.info("HypervisorBackend attached to PID %d", pid)
            return True

        except Exception as e:
            logger.error("HypervisorBackend open failed: %s", e)
            self.close()
            return False

    def close(self) -> None:
        if self._driver_handle is not None and self._driver_handle != -1:
            if self._pid is not None:
                bytes_returned = wintypes.DWORD()
                pid_buffer = ctypes.c_uint32(self._pid)
                ctypes.windll.kernel32.DeviceIoControl(
                    self._driver_handle,
                    self.IOCTL_HV_DETACH,
                    ctypes.byref(pid_buffer),
                    ctypes.sizeof(pid_buffer),
                    None,
                    0,
                    ctypes.byref(bytes_returned),
                    None
                )
            ctypes.windll.kernel32.CloseHandle(self._driver_handle)
            self._driver_handle = None
        self._pid = None

    def read_bytes(self, address: int, size: int) -> Optional[bytes]:
        if not self.is_open:
            return None

        # Define a structure to hold the read request
        class ReadRequest(ctypes.Structure):
            _fields_ = [
                ("pid", ctypes.c_uint32),
                ("address", ctypes.c_uint64),
                ("size", ctypes.c_uint32)
            ]

        req = ReadRequest(self._pid, address, size)
        buffer = ctypes.create_string_buffer(size)
        bytes_returned = wintypes.DWORD()

        success = ctypes.windll.kernel32.DeviceIoControl(
            self._driver_handle,
            self.IOCTL_HV_READ,
            ctypes.byref(req),
            ctypes.sizeof(req),
            buffer,
            size,
            ctypes.byref(bytes_returned),
            None
        )

        if success and bytes_returned.value == size:
            return buffer.raw
        return None

    def write_bytes(self, address: int, data: bytes) -> bool:
        """
        Write bytes. For standard writes, this might just write to memory.
        For EPT hooks, we use _map_ept_hook directly instead.
        """
        if not self.is_open:
            return False

        class WriteRequest(ctypes.Structure):
            _fields_ = [
                ("pid", ctypes.c_uint32),
                ("address", ctypes.c_uint64),
                ("size", ctypes.c_uint32)
            ]

        req = WriteRequest(self._pid, address, len(data))

        # We need a continuous buffer for the request and data.
        # Alternatively, the IOCTL can take req as input and use a different mechanism,
        # but for simplicity let's assume the driver reads the struct, then the data buffer.

        # Realistically, DeviceIoControl takes an input buffer. We can create a custom buffer:
        in_buf = (ctypes.c_char * (ctypes.sizeof(req) + len(data)))()
        ctypes.memmove(in_buf, ctypes.byref(req), ctypes.sizeof(req))
        ctypes.memmove(ctypes.addressof(in_buf) + ctypes.sizeof(req), data, len(data))

        bytes_returned = wintypes.DWORD()
        success = ctypes.windll.kernel32.DeviceIoControl(
            self._driver_handle,
            self.IOCTL_HV_WRITE,
            in_buf,
            ctypes.sizeof(in_buf),
            None,
            0,
            ctypes.byref(bytes_returned),
            None
        )
        return bool(success)

    def _map_ept_hook(self, target_address: int, shadow_page_data: bytes) -> bool:
        """
        Maps a shadow page via EPT to achieve stealth hooking.
        The shadow_page_data should be exactly 4096 bytes (a page).
        When the CPU reads, it reads the original physical page.
        When it executes, the hypervisor swaps to this shadow page.
        """
        if not self.is_open or len(shadow_page_data) != 4096:
            return False

        class EPTHookRequest(ctypes.Structure):
            _fields_ = [
                ("pid", ctypes.c_uint32),
                ("address", ctypes.c_uint64)
            ]

        req = EPTHookRequest(self._pid, target_address)
        in_buf = (ctypes.c_char * (ctypes.sizeof(req) + 4096))()
        ctypes.memmove(in_buf, ctypes.byref(req), ctypes.sizeof(req))
        ctypes.memmove(ctypes.addressof(in_buf) + ctypes.sizeof(req), shadow_page_data, 4096)

        bytes_returned = wintypes.DWORD()
        success = ctypes.windll.kernel32.DeviceIoControl(
            self._driver_handle,
            self.IOCTL_HV_MAP_EPT_HOOK,
            in_buf,
            ctypes.sizeof(in_buf),
            None,
            0,
            ctypes.byref(bytes_returned),
            None
        )
        return bool(success)

    def _allocate_shadow_page(self, target_address: int, payload: bytes, patch_offset: int) -> Optional[bytes]:
        """
        Helper: Reads the original page, applies the patch, and returns the full 4KB page.
        """
        page_base = target_address & ~0xFFF
        orig_page = self.read_bytes(page_base, 4096)
        if not orig_page:
            return None

        # Apply patch to the copy
        patched_page = bytearray(orig_page)
        patched_page[patch_offset:patch_offset + len(payload)] = payload
        return bytes(patched_page)

    def get_readable_regions(self) -> List[MemoryRegion]:
        # Fallback implementation, in a real scenario the HV driver would expose MmMapIoSpace/ZwQueryVirtualMemory
        return [
            {'address': 0x00400000, 'size': 0x02000000},
            {'address': 0x10000000, 'size': 0x10000000},
        ]

    @property
    def is_open(self) -> bool:
        return self._driver_handle is not None and self._driver_handle != -1


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
        HypervisorBackend,
        PymemBackend,
        PyMemoryEditorBackend,
        ProcMemBackend,
    ]
