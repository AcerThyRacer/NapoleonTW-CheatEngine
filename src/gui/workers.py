"""
Background worker threads for GUI operations.
Prevents UI freezing during long-running file and memory operations.
"""

import logging
import traceback
from typing import Any, Callable, Optional, Tuple

logger = logging.getLogger('napoleon.gui.workers')

try:
    from PyQt6.QtCore import QThread, pyqtSignal, QObject
    PYQT_AVAILABLE = True
except ImportError:
    PYQT_AVAILABLE = False
    # Provide stubs
    class QThread:
        pass
    class QObject:
        pass
    class pyqtSignal:
        def __init__(self, *args):
            pass


if PYQT_AVAILABLE:
    class WorkerSignals(QObject):
        """Signals for worker thread communication."""
        started = pyqtSignal()
        finished = pyqtSignal()
        error = pyqtSignal(str)
        result = pyqtSignal(object)
        progress = pyqtSignal(int, str)  # percent, message
    
    
    class AsyncWorker(QThread):
        """
        Generic async worker for running tasks off the UI thread.
        
        Usage:
            worker = AsyncWorker(some_function, arg1, arg2)
            worker.signals.result.connect(on_result)
            worker.signals.error.connect(on_error)
            worker.signals.progress.connect(on_progress)
            worker.start()
        """
        
        def __init__(self, fn: Callable, *args, **kwargs):
            super().__init__()
            self.fn = fn
            self.args = args
            self.kwargs = kwargs
            self.signals = WorkerSignals()
            self._cancelled = False
        
        def run(self):
            """Execute the worker function."""
            self.signals.started.emit()
            try:
                result = self.fn(*self.args, **self.kwargs)
                if not self._cancelled:
                    self.signals.result.emit(result)
            except Exception as e:
                logger.error("Worker error: %s", e)
                self.signals.error.emit(f"{type(e).__name__}: {e}")
            finally:
                self.signals.finished.emit()
        
        def cancel(self):
            """Request cancellation."""
            self._cancelled = True
    
    
    class FileScanWorker(AsyncWorker):
        """Worker for memory scanning operations."""
        
        def __init__(self, scanner, scan_type: str, value=None, value_type=None):
            self.scanner = scanner
            self.scan_type = scan_type
            self.value = value
            self.value_type = value_type
            super().__init__(self._do_scan)
        
        def _do_scan(self):
            """Run the scan."""
            self.signals.progress.emit(0, "Starting scan...")
            
            if self.scan_type == 'exact':
                count = self.scanner.scan_exact_value(self.value, self.value_type)
            elif self.scan_type == 'increased':
                count = self.scanner.scan_increased_value()
            elif self.scan_type == 'decreased':
                count = self.scanner.scan_decreased_value()
            else:
                raise ValueError(f"Unknown scan type: {self.scan_type}")
            
            self.signals.progress.emit(100, f"Found {count} results")
            return count
    
    
    class FileLoadWorker(AsyncWorker):
        """Worker for file loading operations."""
        
        def __init__(self, loader_fn: Callable, file_path: str):
            self.file_path = file_path
            super().__init__(loader_fn, file_path)
        
        def run(self):
            """Load file with progress updates."""
            self.signals.started.emit()
            self.signals.progress.emit(0, f"Loading {self.file_path}...")
            try:
                result = self.fn(self.file_path)
                self.signals.progress.emit(100, "Done")
                self.signals.result.emit(result)
            except Exception as e:
                self.signals.error.emit(str(e))
            finally:
                self.signals.finished.emit()
    
    
    class BatchWorker(AsyncWorker):
        """Worker for batch operations with per-item progress."""
        
        def __init__(self, items: list, process_fn: Callable):
            self.items = items
            self.process_fn = process_fn
            super().__init__(self._process_batch)
        
        def _process_batch(self):
            """Process items with progress updates."""
            results = []
            total = len(self.items)
            
            for i, item in enumerate(self.items):
                if self._cancelled:
                    break
                
                pct = int((i / total) * 100) if total > 0 else 0
                self.signals.progress.emit(pct, f"Processing {i+1}/{total}")
                
                try:
                    result = self.process_fn(item)
                    results.append(result)
                except Exception as e:
                    logger.warning("Batch item %d failed: %s", i, e)
                    results.append(None)
            
            self.signals.progress.emit(100, f"Completed {len(results)}/{total}")
            return results
    
    
    class MemoryScanWorker(AsyncWorker):
        """
        Worker for memory scanning operations.
        
        Runs scans on a background thread so the GUI stays responsive
        during multi-second region walks.
        """
        
        def __init__(self, scanner, scan_type: str, value=None, value_type=None, 
                     address=None, freeze: bool = False):
            self.scanner = scanner
            self.scan_type = scan_type
            self.value = value
            self.value_type = value_type
            self.address = address
            self.freeze = freeze
            super().__init__(self._do_scan)
        
        def _do_scan(self):
            """Run the memory scan."""
            self.signals.progress.emit(0, f"Starting {self.scan_type} scan...")
            
            if self.scan_type == 'exact':
                count = self.scanner.scan_exact_value(self.value, self.value_type)
            elif self.scan_type == 'exact_parallel':
                count = self.scanner.scan_exact_value_parallel(self.value, self.value_type)
            elif self.scan_type == 'increased':
                count = self.scanner.scan_increased_value()
            elif self.scan_type == 'decreased':
                count = self.scanner.scan_decreased_value()
            elif self.scan_type == 'freeze' and self.address is not None:
                self.scanner.freeze_value(self.address, self.value, self.value_type)
                self.signals.progress.emit(100, f"Frozen at 0x{self.address:X}")
                return 1
            elif self.scan_type == 'write' and self.address is not None:
                self.scanner.write_value(self.address, self.value, self.value_type)
                self.signals.progress.emit(100, f"Written to 0x{self.address:X}")
                return 1
            else:
                raise ValueError(f"Unknown scan type: {self.scan_type}")
            
            self.signals.progress.emit(100, f"Found {count} results")
            return count
    
    
    class CheatToggleWorker(AsyncWorker):
        """
        Worker for toggling cheats in the background.
        
        Cheat activation may involve pointer resolution which reads 
        many memory regions — keep it off the UI thread.
        """
        
        def __init__(self, cheat_mgr, cheat_name: str):
            self.cheat_mgr = cheat_mgr
            self.cheat_name = cheat_name
            super().__init__(self._toggle)
        
        def _toggle(self):
            """Toggle the cheat."""
            self.signals.progress.emit(0, f"Toggling {self.cheat_name}...")
            result = self.cheat_mgr.toggle_cheat(self.cheat_name)
            status = "ON" if result else "OFF"
            self.signals.progress.emit(100, f"{self.cheat_name}: {status}")
            return result

else:
    # Stubs when PyQt6 is not available
    class WorkerSignals:
        pass
    
    class AsyncWorker:
        def __init__(self, *args, **kwargs):
            raise RuntimeError("PyQt6 required for async workers")
    
    class FileScanWorker(AsyncWorker):
        pass
    
    class FileLoadWorker(AsyncWorker):
        pass
    
    class BatchWorker(AsyncWorker):
        pass
    
    class MemoryScanWorker(AsyncWorker):
        pass
    
    class CheatToggleWorker(AsyncWorker):
        pass
