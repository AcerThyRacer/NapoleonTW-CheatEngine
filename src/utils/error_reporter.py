import threading
import queue
import time
import logging
import json
from datetime import datetime
from pathlib import Path

from src.utils.events import EventEmitter, EventType

logger = logging.getLogger('napoleon.error_reporter')

class AsyncErrorReporter:
    """
    Background thread that batches errors and writes to a crash dump file.
    Optionally could send them to a log server.
    """

    def __init__(self, dump_file: str = "crash_dump.log", batch_size: int = 5, flush_interval: float = 5.0):
        self.dump_file = Path(dump_file)
        self.batch_size = batch_size
        self.flush_interval = flush_interval
        self._queue = queue.Queue()
        self._running = False
        self._thread = None

        # Subscribe to error events
        EventEmitter().on(EventType.ERROR_OCCURRED, self._on_error)

    def _on_error(self, event) -> None:
        """Callback when an error occurs."""
        error_data = {
            'timestamp': event.timestamp.isoformat(),
            'source': event.source,
            'error': event.data.get('error', 'Unknown error'),
            'details': event.data.get('details', {})
        }
        self._queue.put(error_data)

    def start(self):
        """Start the background reporter thread."""
        if self._running:
            return

        self._running = True
        self._thread = threading.Thread(
            target=self._process_queue,
            daemon=True,
            name="AsyncErrorReporter"
        )
        self._thread.start()
        logger.info("Async error reporter started")

    def stop(self):
        """Stop the reporter thread."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=2.0)
            self._thread = None

        # Flush remaining
        self._flush_queue()
        logger.info("Async error reporter stopped")

    def _process_queue(self):
        """Main loop for processing the error queue."""
        last_flush = time.time()

        while self._running:
            try:
                # Wait for items with timeout
                try:
                    # We peek at queue size, if it's large enough we flush
                    if self._queue.qsize() >= self.batch_size or (time.time() - last_flush) >= self.flush_interval:
                        self._flush_queue()
                        last_flush = time.time()
                except queue.Empty:
                    pass

                time.sleep(0.5)
            except Exception as e:
                logger.error("Error in AsyncErrorReporter thread: %s", e)

    def _flush_queue(self):
        """Write all queued errors to the dump file."""
        if self._queue.empty():
            return

        errors = []
        while not self._queue.empty():
            try:
                errors.append(self._queue.get_nowait())
            except queue.Empty:
                break

        if not errors:
            return

        try:
            with open(self.dump_file, "a") as f:
                for err in errors:
                    f.write(json.dumps(err) + "\n")
        except Exception as e:
            logger.error("Failed to write to crash dump file: %s", e)
