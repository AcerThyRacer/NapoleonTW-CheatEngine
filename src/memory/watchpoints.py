"""
Watchpoints and conditional triggers for memory addresses.
"""

import logging
import threading
import time
from typing import Any, Callable, Dict, List, Optional
from dataclasses import dataclass, field
from enum import Enum

from src.utils.events import EventEmitter, EventType
from src.utils.game_state import GameMode
from src.memory.advanced import PointerChain, PointerResolver

logger = logging.getLogger('napoleon.memory.watchpoints')

class ConditionType(Enum):
    """Types of conditions that can trigger a watchpoint."""
    EQUALS = 'equals'
    NOT_EQUALS = 'not_equals'
    GREATER_THAN = 'greater_than'
    LESS_THAN = 'less_than'
    CHANGED = 'changed'

@dataclass
class WatchpointCondition:
    """A condition to evaluate against a memory value."""
    condition_type: ConditionType
    value: Any

    def evaluate(self, current_value: Any, previous_value: Any) -> bool:
        if current_value is None:
            return False

        if self.condition_type == ConditionType.EQUALS:
            return current_value == self.value
        elif self.condition_type == ConditionType.NOT_EQUALS:
            return current_value != self.value
        elif self.condition_type == ConditionType.GREATER_THAN:
            return current_value > self.value
        elif self.condition_type == ConditionType.LESS_THAN:
            return current_value < self.value
        elif self.condition_type == ConditionType.CHANGED:
            return current_value != previous_value

        return False

@dataclass
class MemoryWatchpoint:
    """A watchpoint that monitors a memory address or pointer chain."""
    id: str
    description: str
    address: Optional[int] = None
    pointer_chain: Optional[PointerChain] = None
    value_type: str = 'int32'
    conditions: List[WatchpointCondition] = field(default_factory=list)
    actions: List[Callable[[Any, Any], None]] = field(default_factory=list)
    enabled: bool = True
    last_value: Any = None
    first_run: bool = True

class WatchpointManager:
    """
    Background thread system that continuously monitors watchpoints and evaluates conditions.
    """

    def __init__(self, editor: Optional[Any] = None, pid: Optional[int] = None):
        self.editor = editor
        self.pid = pid
        self.watchpoints: Dict[str, MemoryWatchpoint] = {}
        self._thread: Optional[threading.Thread] = None
        self._running = False
        self._lock = threading.Lock()
        self._interval_ms = 100
        self._pointer_resolver = PointerResolver(editor=editor, pid=pid)

    def set_editor(self, editor: Any, pid: int) -> None:
        """Set the memory editor and process ID."""
        self.editor = editor
        self.pid = pid
        self._pointer_resolver.set_editor(editor, pid)

    def add_watchpoint(self, watchpoint: MemoryWatchpoint) -> bool:
        """Add a watchpoint to monitor."""
        with self._lock:
            self.watchpoints[watchpoint.id] = watchpoint

        logger.info(f"Added watchpoint: {watchpoint.id} - {watchpoint.description}")

        if not self._running:
            self.start()

        return True

    def remove_watchpoint(self, watchpoint_id: str) -> bool:
        """Remove a watchpoint."""
        with self._lock:
            if watchpoint_id in self.watchpoints:
                del self.watchpoints[watchpoint_id]
                logger.info(f"Removed watchpoint: {watchpoint_id}")

                if not self.watchpoints and self._running:
                    self.stop()

                return True
        return False

    def enable_watchpoint(self, watchpoint_id: str, enabled: bool = True) -> bool:
        """Enable or disable a watchpoint."""
        with self._lock:
            if watchpoint_id in self.watchpoints:
                self.watchpoints[watchpoint_id].enabled = enabled
                return True
        return False

    def start(self) -> None:
        """Start the watchpoint thread."""
        with self._lock:
            if self._running:
                return

            self._running = True
            self._thread = threading.Thread(
                target=self._watch_loop,
                daemon=True,
                name="WatchpointManager"
            )
            self._thread.start()
        logger.info("Watchpoint manager started")

    def stop(self) -> None:
        """Stop the watchpoint thread."""
        with self._lock:
            self._running = False
            thread = self._thread
            self._thread = None

        if thread:
            thread.join(timeout=2.0)
        logger.info("Watchpoint manager stopped")

    def _read_value(self, watchpoint: MemoryWatchpoint) -> Any:
        """Read the value for a watchpoint."""
        if not self.editor:
            return None

        if watchpoint.address is not None:
            try:
                import struct
                fmt_map = {
                    'int8': ('<b', 1), 'int16': ('<h', 2), 'int32': ('<i', 4),
                    'int64': ('<q', 8), 'float': ('<f', 4), 'double': ('<d', 8),
                }
                fmt, size = fmt_map.get(watchpoint.value_type, ('<i', 4))

                if hasattr(self.editor, 'read_bytes'):
                    data = self.editor.read_bytes(watchpoint.address, size)
                else:
                    data = self.editor.read_process_memory(watchpoint.address, size)

                if data and len(data) >= size:
                    return struct.unpack(fmt, data[:size])[0]
            except Exception as e:
                logger.debug(f"Failed to read watchpoint address {watchpoint.address}: {e}")
                return None
        elif watchpoint.pointer_chain is not None:
            return self._pointer_resolver.resolve_and_read(watchpoint.pointer_chain)

        return None

    def _watch_loop(self) -> None:
        """Main watchpoint loop - runs in background thread."""
        while self._running:
            try:
                with self._lock:
                    watchpoints = list(self.watchpoints.values())

                for wp in watchpoints:
                    if not wp.enabled:
                        continue

                    current_value = self._read_value(wp)

                    if wp.first_run:
                        wp.last_value = current_value
                        wp.first_run = False
                        continue

                    if current_value is not None:
                        # Evaluate conditions
                        for condition in wp.conditions:
                            if condition.evaluate(current_value, wp.last_value):
                                logger.info(f"Watchpoint {wp.id} triggered condition {condition.condition_type.value}")

                                # Emit event
                                EventEmitter().emit(
                                    EventType.STATUS_CHANGED,
                                    data={
                                        'type': 'watchpoint_triggered',
                                        'watchpoint_id': wp.id,
                                        'description': wp.description,
                                        'condition': condition.condition_type.value,
                                        'current_value': current_value,
                                        'previous_value': wp.last_value
                                    },
                                    source='watchpoint_manager'
                                )

                                # Execute actions
                                for action in wp.actions:
                                    try:
                                        action(current_value, wp.last_value)
                                    except Exception as e:
                                        logger.error(f"Watchpoint action failed: {e}")

                    wp.last_value = current_value

                time.sleep(self._interval_ms / 1000.0)

            except Exception as e:
                logger.error(f"Watchpoint loop error: {e}")
                time.sleep(0.1)

class ConditionalTriggerManager:
    """
    Manages high-level conditional triggers based on game state and watchpoints.
    """
    def __init__(self, watchpoint_manager: WatchpointManager, cheat_manager: Any):
        self.watchpoint_manager = watchpoint_manager
        self.cheat_manager = cheat_manager

        # Listen for game state changes
        EventEmitter().on(EventType.GAME_STATE_CHANGED, self._on_game_state_changed)

        self.game_mode_triggers: Dict[GameMode, List[Callable]] = {}

    def add_game_mode_trigger(self, mode: GameMode, action: Callable) -> None:
        """Add a trigger that fires when the game mode changes."""
        if mode not in self.game_mode_triggers:
            self.game_mode_triggers[mode] = []
        self.game_mode_triggers[mode].append(action)
        logger.info(f"Added game mode trigger for {mode.value}")

    def _on_game_state_changed(self, event) -> None:
        """Handle game state changes."""
        new_mode_str = event.data.get('new_mode', 'unknown')
        try:
            new_mode = GameMode(new_mode_str)

            if new_mode in self.game_mode_triggers:
                for action in self.game_mode_triggers[new_mode]:
                    try:
                        action()
                    except Exception as e:
                        logger.error(f"Game mode trigger action failed: {e}")

        except ValueError:
            pass

    def add_memory_trigger(
        self,
        trigger_id: str,
        description: str,
        pointer_chain: PointerChain,
        condition_type: ConditionType,
        condition_value: Any,
        action: Callable[[Any, Any], None]
    ) -> bool:
        """Add a trigger based on a memory value."""
        condition = WatchpointCondition(condition_type, condition_value)

        wp = MemoryWatchpoint(
            id=trigger_id,
            description=description,
            pointer_chain=pointer_chain,
            value_type=pointer_chain.value_type,
            conditions=[condition],
            actions=[action]
        )

        return self.watchpoint_manager.add_watchpoint(wp)
