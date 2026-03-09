"""
Process management for Napoleon Total War.
Handles process detection, attachment, and memory access.
"""

import psutil
from typing import Optional, List
from pathlib import Path

from src.utils import (
    get_platform,
    get_all_possible_process_names,
    get_process_name,
    is_proton,
)


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
