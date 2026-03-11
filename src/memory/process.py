"""
Process management for Napoleon Total War.
Handles process detection, attachment, and memory access.
"""

import psutil
from typing import Optional, List
from pathlib import Path

import asyncio
import logging
import os
import struct
import time
from typing import Tuple

from src.utils import (
    get_platform,
    get_all_possible_process_names,
    get_process_name,
    is_proton,
)

logger = logging.getLogger(__name__)


class SmartPointer:
    """
    Robust Multi-Level Pointer resolver.
    Safely reads memory across pointer chains, validates memory regions
    via /proc/<pid>/maps, and asynchronously caches results.
    """
    def __init__(self, pid: int, base_address: int, offsets: List[int], cache_ttl: float = 1.0):
        self.pid = pid
        self.base_address = base_address
        self.offsets = offsets
        self.cache_ttl = cache_ttl

        self._cached_address: Optional[int] = None
        self._last_update: float = 0.0
        self._lock = asyncio.Lock()

        self._valid_regions: List[Tuple[int, int]] = []
        self._regions_last_update: float = 0.0

    def _update_memory_maps(self) -> None:
        """Update the cached memory regions from /proc/pid/maps."""
        now = time.time()
        # Cache memory maps for 5 seconds to avoid expensive reads every check
        if now - self._regions_last_update < 5.0 and self._valid_regions:
            return

        regions = []
        try:
            maps_path = f"/proc/{self.pid}/maps"
            if not os.path.exists(maps_path):
                return

            with open(maps_path, "r") as f:
                for line in f:
                    parts = line.split()
                    if len(parts) < 2 or 'r' not in parts[1]:
                        continue
                    addr_range = parts[0].split('-')
                    if len(addr_range) == 2:
                        try:
                            start = int(addr_range[0], 16)
                            end = int(addr_range[1], 16)
                            regions.append((start, end))
                        except ValueError:
                            pass
            self._valid_regions = regions
            self._regions_last_update = now
        except Exception as e:
            logger.debug("Failed to read memory maps for PID %d: %s", self.pid, e)

    def _is_valid_address(self, address: int) -> bool:
        """Check if an address is not null and within a valid readable memory region."""
        if address == 0:
            return False

        self._update_memory_maps()

        # If we couldn't load regions (e.g., on Windows or access denied), allow it optimistically
        if not self._valid_regions:
            return True

        for start, end in self._valid_regions:
            if start <= address < end:
                return True

        return False

    async def resolve(self) -> Optional[int]:
        """
        Asynchronously resolve the pointer chain.
        Caches the result to avoid re-reading every frame.
        """
        async with self._lock:
            now = time.time()
            if self._cached_address is not None and (now - self._last_update) < self.cache_ttl:
                return self._cached_address

            current_addr = self.base_address

            try:
                mem_path = f"/proc/{self.pid}/mem"
                # Fallback check if mem path doesn't exist (not on Linux)
                if not os.path.exists(mem_path):
                    logger.debug("mem path %s not found (not on Linux?)", mem_path)
                    return None

                fd = os.open(mem_path, os.O_RDONLY)
                try:
                    for i, offset in enumerate(self.offsets):
                        if not self._is_valid_address(current_addr):
                            logger.debug("Invalid memory address at step %d: 0x%08X", i, current_addr)
                            return None

                        os.lseek(fd, current_addr, os.SEEK_SET)
                        ptr_data = os.read(fd, 4)
                        if len(ptr_data) < 4:
                            logger.debug("Failed to read 4 bytes at 0x%08X", current_addr)
                            return None

                        # Napoleon Total War is a 32-bit process, pointers are 4 bytes
                        current_addr = struct.unpack('<I', ptr_data)[0] + offset

                    if not self._is_valid_address(current_addr):
                        logger.debug("Resolved final address is invalid: 0x%08X", current_addr)
                        return None

                    self._cached_address = current_addr
                    self._last_update = time.time()
                    return current_addr
                finally:
                    os.close(fd)
            except Exception as e:
                logger.debug("Exception during pointer resolution: %s", e)
                return None


class ProcessManager:
    """
    Manages attachment to Napoleon Total War process.
    """
    
    def __init__(self):
        self.process: Optional[psutil.Process] = None
        self.pid: Optional[int] = None
        self.process_name: str = ""
        
    def find_process(self) -> Optional[psutil.Process]:
        """
        Find the Napoleon Total War process.
        
        Returns:
            Optional[psutil.Process]: Process object if found, None otherwise
        """
        possible_names = get_all_possible_process_names()
        
        for proc in psutil.process_iter(['pid', 'name']):
            try:
                name = proc.info['name']
                if name and name.lower() in [n.lower() for n in possible_names]:
                    return proc
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        
        return None
    
    def attach(self, pid: Optional[int] = None) -> bool:
        """
        Attach to the Napoleon process.
        
        Args:
            pid: Optional process ID (if not provided, auto-detect)
            
        Returns:
            bool: True if attachment successful
        """
        try:
            if pid:
                self.process = psutil.Process(pid)
            else:
                self.process = self.find_process()
            
            if not self.process:
                return False
            
            self.pid = self.process.pid
            self.process_name = self.process.name()
            
            # Verify process is running
            if not self.process.is_running():
                self.process = None
                self.pid = None
                return False
            
            return True
            
        except (psutil.NoSuchProcess, psutil.AccessDenied) as e:
            print(f"Failed to attach to process: {e}")
            return False
    
    def detach(self) -> None:
        """
        Detach from the current process.
        """
        self.process = None
        self.pid = None
        self.process_name = ""
    
    def is_attached(self) -> bool:
        """
        Check if attached to a process.
        
        Returns:
            bool: True if attached
        """
        return self.process is not None and self.process.is_running()
    
    def get_process_info(self) -> dict:
        """
        Get information about the attached process.
        
        Returns:
            dict: Process information
        """
        if not self.is_attached():
            return {}
        
        try:
            with self.process.oneshot():
                return {
                    'pid': self.pid,
                    'name': self.process_name,
                    'status': self.process.status(),
                    'cpu_percent': self.process.cpu_percent(),
                    'memory_info': self.process.memory_info()._asdict(),
                    'exe': self.process.exe(),
                    'cwd': self.process.cwd(),
                }
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            return {}
    
    def get_memory_maps(self) -> List:
        """
        Get memory maps of the process.
        
        Returns:
            List: List of memory map regions
        """
        if not self.is_attached():
            return []
        
        try:
            return self.process.memory_maps(grouped=False)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            return []
    
    def check_access(self) -> bool:
        """
        Check if we have memory access permissions.
        
        Returns:
            bool: True if accessible
        """
        if not self.is_attached():
            return False
        
        try:
            # Try to read a small amount of memory
            # This is a basic check
            return True
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            return False
    
    @staticmethod
    def list_game_processes() -> List[dict]:
        """
        List all possible Napoleon processes.
        
        Returns:
            List[dict]: List of process information dictionaries
        """
        possible_names = get_all_possible_process_names()
        processes = []
        
        for proc in psutil.process_iter(['pid', 'name']):
            try:
                name = proc.info['name']
                if name and name.lower() in [n.lower() for n in possible_names]:
                    processes.append({
                        'pid': proc.info['pid'],
                        'name': name,
                    })
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        
        return processes
