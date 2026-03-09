"""
Background thread for live memory reading and real-time value updates.
Polls game memory at configurable intervals and emits signals when values change.
"""

import logging
import time
from typing import Dict, Optional, Any

logger = logging.getLogger('napoleon.gui.memory_monitor')

try:
    from PyQt6.QtCore import QThread, pyqtSignal
    PYQT_AVAILABLE = True
except ImportError:
    PYQT_AVAILABLE = False

    class QThread:
        """Stub when PyQt6 is not available."""
        pass

    class pyqtSignal:
        def __init__(self, *args):
            pass


class MemoryMonitor(QThread):
    """
    Background thread that continuously reads game memory and emits
    signals when monitored values change.

    Signals:
        value_changed(cheat_id: str, new_value: int):
            Emitted whenever a monitored memory value changes.
        status_changed(cheat_id: str, status: str):
            Emitted when a cheat's health status changes
            ('ok', 'modified', 'broken').
        error_occurred(cheat_id: str, message: str):
            Emitted when a read error occurs for a monitored address.
    """

    if PYQT_AVAILABLE:
        value_changed = pyqtSignal(str, object)    # cheat_id, new_value
        status_changed = pyqtSignal(str, str)       # cheat_id, status
        error_occurred = pyqtSignal(str, str)        # cheat_id, message

    def __init__(self, scanner=None, parent=None):
        """
        Initialise the memory monitor.

        Args:
            scanner: A MemoryScanner (or compatible) instance used for reads.
            parent: Optional QObject parent.
        """
        if PYQT_AVAILABLE:
            super().__init__(parent)
        self._scanner = scanner
        self._running = False
        self._interval: float = 0.1  # 10 updates/sec
        self._monitored: Dict[str, Dict[str, Any]] = {}
        self._last_values: Dict[str, Any] = {}
        self._expected_values: Dict[str, Any] = {}

    # ------------------------------------------------------------------
    # Public API (called from the GUI thread)
    # ------------------------------------------------------------------

    def set_scanner(self, scanner) -> None:
        """Attach or replace the memory scanner instance."""
        self._scanner = scanner

    def set_interval(self, seconds: float) -> None:
        """Set polling interval (minimum 0.01 s)."""
        self._interval = max(0.01, seconds)

    def monitor(self, cheat_id: str, address: int, value_type=None) -> None:
        """
        Register an address for continuous monitoring.

        Args:
            cheat_id:   Logical name, e.g. ``"infinite_gold"``.
            address:    Memory address to read.
            value_type: A ``ValueType`` enum member (default ``INT_32``).
        """
        if value_type is None:
            from src.memory.scanner import ValueType
            value_type = ValueType.INT_32

        self._monitored[cheat_id] = {
            'address': address,
            'value_type': value_type,
        }

    def unmonitor(self, cheat_id: str) -> None:
        """Stop monitoring a specific cheat."""
        self._monitored.pop(cheat_id, None)
        self._last_values.pop(cheat_id, None)
        self._expected_values.pop(cheat_id, None)

    def set_expected_value(self, cheat_id: str, value: Any) -> None:
        """
        Set the expected (frozen/written) value for a cheat so
        the monitor can detect when the game overwrites it.
        """
        self._expected_values[cheat_id] = value

    def clear_expected_value(self, cheat_id: str) -> None:
        """Remove the expected-value check for a cheat."""
        self._expected_values.pop(cheat_id, None)

    def get_last_value(self, cheat_id: str) -> Optional[Any]:
        """Return the most recently read value for *cheat_id*."""
        return self._last_values.get(cheat_id)

    def get_all_values(self) -> Dict[str, Any]:
        """Return a snapshot of all last-read values."""
        return dict(self._last_values)

    def stop(self) -> None:
        """Request a graceful stop."""
        self._running = False

    # ------------------------------------------------------------------
    # Thread entry-point
    # ------------------------------------------------------------------

    def run(self) -> None:  # noqa: D401
        """Main polling loop — runs in the background QThread."""
        self._running = True
        logger.info("MemoryMonitor started (interval=%.3fs)", self._interval)

        while self._running:
            if self._scanner is None or not self._scanner.is_attached():
                time.sleep(self._interval)
                continue

            for cheat_id, info in list(self._monitored.items()):
                if not self._running:
                    break
                self._poll_address(cheat_id, info)

            time.sleep(self._interval)

        logger.info("MemoryMonitor stopped")

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _poll_address(self, cheat_id: str, info: Dict[str, Any]) -> None:
        """Read one address and emit signals as needed."""
        address = info['address']
        value_type = info['value_type']

        try:
            new_value = self._scanner.read_value(address, value_type)
        except Exception as exc:
            logger.debug("Read error for %s @ 0x%08X: %s", cheat_id, address, exc)
            if PYQT_AVAILABLE:
                self.error_occurred.emit(cheat_id, str(exc))
            return

        if new_value is None:
            return

        old_value = self._last_values.get(cheat_id)
        self._last_values[cheat_id] = new_value

        # Emit on change
        if new_value != old_value:
            if PYQT_AVAILABLE:
                self.value_changed.emit(cheat_id, new_value)

        # Check health status
        if cheat_id in self._expected_values:
            expected = self._expected_values[cheat_id]
            if new_value == expected:
                status = 'modified'  # value matches our cheat
            else:
                status = 'broken'    # game has overwritten our cheat
        else:
            status = 'ok'

        if PYQT_AVAILABLE:
            self.status_changed.emit(cheat_id, status)
