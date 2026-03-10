"""
Async error reporter for background error logging.
Batches errors and writes them to crash_dump.log without blocking the main thread.
"""

import logging
import threading
import time
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
import json

logger = logging.getLogger('napoleon.utils.error_reporter')


@dataclass
class ErrorEntry:
    """Represents a logged error entry."""
    timestamp: str
    level: str
    logger_name: str
    message: str
    module: str
    function: str
    line: int
    details: Optional[str] = None
    context: Dict[str, Any] = field(default_factory=dict)


class AsyncErrorReporter:
    """
    Background error reporter that batches errors and flushes them to disk.
    
    Features:
    - Non-blocking error logging via background thread
    - Batching to reduce I/O operations
    - Automatic flush on shutdown
    - Crash dump file in project root
    """
    
    def __init__(
        self,
        log_file: Optional[str] = None,
        batch_size: int = 10,
        flush_interval: float = 5.0,
    ):
        """
        Initialize async error reporter.
        
        Args:
            log_file: Path to crash dump log (default: ./crash_dump.log)
            batch_size: Number of errors to batch before flushing
            flush_interval: Auto-flush interval in seconds
        """
        self.log_file = Path(log_file) if log_file else Path.cwd() / 'crash_dump.log'
        self.batch_size = batch_size
        self.flush_interval = flush_interval
        
        self._error_queue: List[ErrorEntry] = []
        self._lock = threading.Lock()
        self._thread: Optional[threading.Thread] = None
        self._running = False
        self._last_flush = time.time()
        
        # Statistics
        self._total_errors = 0
        self._total_flushes = 0
        
    def start(self) -> None:
        """Start the background flusher thread."""
        if self._running:
            return
        
        self._running = True
        self._thread = threading.Thread(
            target=self._flush_loop,
            daemon=True,
            name="AsyncErrorReporter"
        )
        self._thread.start()
        logger.info("Async error reporter started")
    
    def stop(self) -> None:
        """Stop the reporter and flush remaining errors."""
        self._running = False
        
        if self._thread:
            self._thread.join(timeout=2.0)
            self._thread = None
        
        # Final flush
        self._flush_queue()
        logger.info("Async error reporter stopped")
    
    def report_error(
        self,
        message: str,
        level: str = 'ERROR',
        logger_name: str = 'napoleon',
        module: str = '',
        function: str = '',
        line: int = 0,
        details: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Report an error to be logged asynchronously.
        
        Args:
            message: Error message
            level: Log level (ERROR, CRITICAL, etc.)
            logger_name: Logger name
            module: Module name
            function: Function name
            line: Line number
            details: Additional error details
            context: Contextual information
        """
        entry = ErrorEntry(
            timestamp=datetime.now(timezone.utc).isoformat(),
            level=level,
            logger_name=logger_name,
            message=message,
            module=module,
            function=function,
            line=line,
            details=details,
            context=context or {},
        )
        
        with self._lock:
            self._error_queue.append(entry)
            self._total_errors += 1
            
            # Auto-flush if batch is full
            if len(self._error_queue) >= self.batch_size:
                self._flush_queue_unlocked()
    
    def report_exception(
        self,
        exc: Exception,
        context_msg: str = '',
        context: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Report an exception with optional context.
        
        Args:
            exc: Exception to report
            context_msg: Additional context message
            context: Contextual information
        """
        import traceback
        
        details = traceback.format_exc()
        self.report_error(
            message=context_msg or str(exc),
            level='ERROR',
            details=details,
            context=context or {},
        )
    
    def _flush_loop(self) -> None:
        """Background flush loop."""
        while self._running:
            try:
                time.sleep(self.flush_interval)
                
                # Check if auto-flush is needed
                with self._lock:
                    if self._error_queue and (time.time() - self._last_flush) >= self.flush_interval:
                        self._flush_queue_unlocked()
                        
            except Exception as e:
                logger.error("Error reporter flush loop error: %s", e)
    
    def _flush_queue_unlocked(self) -> None:
        """Flush the error queue (must be called with lock held)."""
        if not self._error_queue:
            return
        
        # Copy and clear
        errors_to_flush = self._error_queue.copy()
        self._error_queue.clear()
        
        # Write to file
        try:
            self._write_errors(errors_to_flush)
            self._last_flush = time.time()
            self._total_flushes += 1
        except Exception as e:
            logger.error("Failed to flush error queue: %s", e)
    
    def _flush_queue(self) -> None:
        """Flush the error queue (thread-safe)."""
        with self._lock:
            self._flush_queue_unlocked()
    
    def _write_errors(self, errors: List[ErrorEntry]) -> None:
        """Write errors to the crash dump file."""
        if not errors:
            return
        
        # Append to file
        with open(self.log_file, 'a', encoding='utf-8') as f:
            for error in errors:
                log_entry = {
                    'timestamp': error.timestamp,
                    'level': error.level,
                    'logger': error.logger_name,
                    'message': error.message,
                    'module': error.module,
                    'function': error.function,
                    'line': error.line,
                }
                
                if error.details:
                    log_entry['details'] = error.details
                
                if error.context:
                    log_entry['context'] = error.context
                
                f.write(json.dumps(log_entry) + '\n')
        
        logger.debug("Flushed %d errors to %s", len(errors), self.log_file)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get reporter statistics."""
        with self._lock:
            return {
                'total_errors': self._total_errors,
                'total_flushes': self._total_flushes,
                'queue_size': len(self._error_queue),
                'is_running': self._running,
            }
    
    def clear_queue(self) -> int:
        """Clear the error queue. Returns count of cleared errors."""
        with self._lock:
            count = len(self._error_queue)
            self._error_queue.clear()
            return count


# Global error reporter instance
_error_reporter: Optional[AsyncErrorReporter] = None


def get_error_reporter() -> Optional[AsyncErrorReporter]:
    """Get the global error reporter instance."""
    return _error_reporter


def init_error_reporter(
    log_file: Optional[str] = None,
    batch_size: int = 10,
    flush_interval: float = 5.0,
) -> AsyncErrorReporter:
    """
    Initialize and start the global error reporter.
    
    Args:
        log_file: Path to crash dump log
        batch_size: Batch size for flushing
        flush_interval: Auto-flush interval
        
    Returns:
        Initialized error reporter instance
    """
    global _error_reporter
    
    if _error_reporter is not None:
        return _error_reporter
    
    _error_reporter = AsyncErrorReporter(
        log_file=log_file,
        batch_size=batch_size,
        flush_interval=flush_interval,
    )
    _error_reporter.start()
    
    return _error_reporter


def shutdown_error_reporter() -> None:
    """Shutdown the global error reporter."""
    global _error_reporter
    
    if _error_reporter:
        _error_reporter.stop()
        _error_reporter = None
