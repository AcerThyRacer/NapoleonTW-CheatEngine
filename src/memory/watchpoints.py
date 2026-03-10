"""
Memory watchpoints and conditional trigger system.
Monitors memory addresses and triggers actions based on conditions.
"""

import logging
import threading
import time
from typing import List, Optional, Dict, Any, Callable
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime

from .advanced import PointerResolver, PointerChain

logger = logging.getLogger('napoleon.memory.watchpoints')


class ConditionType(Enum):
    """Types of conditions for watchpoints."""
    LESS_THAN = 'less_than'
    GREATER_THAN = 'greater_than'
    EQUALS = 'equals'
    NOT_EQUALS = 'not_equals'
    CHANGED = 'changed'
    UNCHANGED = 'unchanged'
    BELOW_THRESHOLD = 'below_threshold'
    ABOVE_THRESHOLD = 'above_threshold'


@dataclass
class MemoryWatchpoint:
    """Represents a memory watchpoint."""
    address: int
    value_type: str  # 'int8', 'int16', 'int32', 'int64', 'float', 'double'
    condition: ConditionType
    threshold: Any
    description: str = ""
    enabled: bool = True
    last_value: Optional[Any] = None
    trigger_count: int = 0
    last_trigger_time: Optional[float] = None
    cooldown_ms: int = 100  # Minimum time between triggers


@dataclass
class TriggerAction:
    """Action to execute when a watchpoint triggers."""
    action_type: str  # 'activate_cheat', 'deactivate_cheat', 'toggle_cheat', 'callback'
    target: Any  # CheatType or callback function
    data: Optional[Dict[str, Any]] = None


class WatchpointManager:
    """
    Background thread that monitors memory watchpoints.
    
    Features:
    - Poll multiple watchpoints at configurable intervals
    - Evaluate conditions and trigger actions
    - Cooldown support to prevent spam
    - Thread-safe operation
    """
    
    def __init__(
        self,
        memory_scanner: Any,
        poll_interval_ms: int = 50,
    ):
        """
        Initialize watchpoint manager.
        
        Args:
            memory_scanner: MemoryScanner instance for reading values
            poll_interval_ms: Polling interval in milliseconds
        """
        self.memory_scanner = memory_scanner
        self.poll_interval_ms = poll_interval_ms
        
        self._watchpoints: Dict[int, MemoryWatchpoint] = {}
        self._actions: Dict[int, List[TriggerAction]] = {}
        self._thread: Optional[threading.Thread] = None
        self._running = False
        self._lock = threading.Lock()
        
        # Statistics
        self._total_triggers = 0
        self._last_poll_time: Optional[float] = None
    
    def add_watchpoint(
        self,
        address: int,
        value_type: str,
        condition: ConditionType,
        threshold: Any,
        description: str = "",
        cooldown_ms: int = 100,
    ) -> bool:
        """
        Add a memory watchpoint.
        
        Args:
            address: Memory address to monitor
            value_type: Type of value
            condition: Condition to check
            threshold: Threshold value for comparison
            description: Human-readable description
            cooldown_ms: Cooldown between triggers
            
        Returns:
            bool: True if added successfully
        """
        if not self.memory_scanner.is_attached():
            logger.warning("Cannot add watchpoint: scanner not attached")
            return False
        
        watchpoint = MemoryWatchpoint(
            address=address,
            value_type=value_type,
            condition=condition,
            threshold=threshold,
            description=description,
            cooldown_ms=cooldown_ms,
        )
        
        with self._lock:
            self._watchpoints[address] = watchpoint
            self._actions[address] = []
        
        logger.info(
            "Watchpoint added: 0x%X (%s) condition=%s threshold=%s",
            address, description, condition.value, threshold
        )
        
        # Auto-start if not running
        if not self._running:
            self.start()
        
        return True
    
    def add_action(self, address: int, action: TriggerAction) -> bool:
        """
        Add an action to a watchpoint.
        
        Args:
            address: Watchpoint address
            action: Action to execute on trigger
            
        Returns:
            bool: True if added successfully
        """
        with self._lock:
            if address not in self._actions:
                logger.warning("No watchpoint at 0x%X", address)
                return False
            
            self._actions[address].append(action)
        
        logger.debug("Action added to watchpoint 0x%X: %s", address, action.action_type)
        return True
    
    def remove_watchpoint(self, address: int) -> bool:
        """
        Remove a watchpoint.
        
        Args:
            address: Watchpoint address
            
        Returns:
            bool: True if removed successfully
        """
        with self._lock:
            if address in self._watchpoints:
                del self._watchpoints[address]
                if address in self._actions:
                    del self._actions[address]
                logger.info("Watchpoint removed: 0x%X", address)
                return True
        return False
    
    def remove_all_watchpoints(self) -> int:
        """
        Remove all watchpoints.
        
        Returns:
            Number of watchpoints removed
        """
        with self._lock:
            count = len(self._watchpoints)
            self._watchpoints.clear()
            self._actions.clear()
            logger.info("Removed %d watchpoints", count)
            return count
    
    def start(self) -> None:
        """Start the watchpoint monitoring thread."""
        if self._running:
            return
        
        self._running = True
        self._thread = threading.Thread(
            target=self._monitor_loop,
            daemon=True,
            name="WatchpointManager"
        )
        self._thread.start()
        logger.info("Watchpoint manager started (interval=%dms)", self.poll_interval_ms)
    
    def stop(self) -> None:
        """Stop the watchpoint monitoring thread."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=2.0)
            self._thread = None
        logger.info("Watchpoint manager stopped")
    
    def _monitor_loop(self) -> None:
        """Main monitoring loop."""
        while self._running:
            try:
                current_time = time.time()
                self._last_poll_time = current_time
                
                with self._lock:
                    watchpoints = list(self._watchpoints.values())
                
                for watchpoint in watchpoints:
                    if not watchpoint.enabled:
                        continue
                    
                    self._check_watchpoint(watchpoint, current_time)
                
                # Sleep for poll interval
                time.sleep(self.poll_interval_ms / 1000.0)
                
            except Exception as e:
                logger.error("Watchpoint monitor error: %s", e)
                time.sleep(0.1)
    
    def _check_watchpoint(self, watchpoint: MemoryWatchpoint, current_time: float) -> None:
        """Check a single watchpoint."""
        if not self.memory_scanner.backend:
            return
        
        # Read current value
        try:
            current_value = self.memory_scanner.read_value(
                watchpoint.address,
                watchpoint.value_type
            )
            
            if current_value is None:
                return
            
            # Check condition
            triggered = self._evaluate_condition(
                watchpoint.condition,
                current_value,
                watchpoint.threshold,
                watchpoint.last_value
            )
            
            if triggered:
                # Check cooldown
                if watchpoint.last_trigger_time:
                    elapsed_ms = (current_time - watchpoint.last_trigger_time) * 1000
                    if elapsed_ms < watchpoint.cooldown_ms:
                        return
                
                # Trigger actions
                self._trigger_watchpoint(watchpoint, current_value, current_time)
            
            # Update last value
            watchpoint.last_value = current_value
            
        except Exception as e:
            logger.debug("Error checking watchpoint 0x%X: %s", watchpoint.address, e)
    
    def _evaluate_condition(
        self,
        condition: ConditionType,
        current_value: Any,
        threshold: Any,
        last_value: Optional[Any],
    ) -> bool:
        """Evaluate a condition."""
        try:
            if condition == ConditionType.LESS_THAN:
                return current_value < threshold
            elif condition == ConditionType.GREATER_THAN:
                return current_value > threshold
            elif condition == ConditionType.EQUALS:
                return current_value == threshold
            elif condition == ConditionType.NOT_EQUALS:
                return current_value != threshold
            elif condition == ConditionType.CHANGED:
                return last_value is not None and current_value != last_value
            elif condition == ConditionType.UNCHANGED:
                return last_value is not None and current_value == last_value
            elif condition == ConditionType.BELOW_THRESHOLD:
                return current_value < threshold
            elif condition == ConditionType.ABOVE_THRESHOLD:
                return current_value > threshold
            else:
                return False
        except Exception:
            return False
    
    def _trigger_watchpoint(
        self,
        watchpoint: MemoryWatchpoint,
        current_value: Any,
        current_time: float,
    ) -> None:
        """Execute watchpoint trigger actions."""
        watchpoint.trigger_count += 1
        watchpoint.last_trigger_time = current_time
        self._total_triggers += 1
        
        logger.info(
            "Watchpoint triggered: 0x%X (%s) value=%s trigger #%d",
            watchpoint.address, watchpoint.description, current_value, watchpoint.trigger_count
        )
        
        # Execute actions
        with self._lock:
            actions = self._actions.get(watchpoint.address, [])
        
        for action in actions:
            try:
                self._execute_action(action, watchpoint, current_value)
            except Exception as e:
                logger.error("Action execution failed: %s", e)
    
    def _execute_action(
        self,
        action: TriggerAction,
        watchpoint: MemoryWatchpoint,
        current_value: Any,
    ) -> None:
        """Execute a trigger action."""
        if action.action_type == 'callback' and callable(action.target):
            action.target(watchpoint, current_value)
        
        # Other action types (activate_cheat, etc.) would be handled by CheatManager
    
    def get_stats(self) -> Dict[str, Any]:
        """Get watchpoint manager statistics."""
        with self._lock:
            return {
                'total_watchpoints': len(self._watchpoints),
                'enabled_watchpoints': sum(1 for w in self._watchpoints.values() if w.enabled),
                'total_triggers': self._total_triggers,
                'is_running': self._running,
                'last_poll_time': self._last_poll_time,
            }
    
    def get_watchpoints_list(self) -> List[Dict[str, Any]]:
        """Get list of all watchpoints."""
        with self._lock:
            return [
                {
                    'address': f'0x{w.address:08X}',
                    'description': w.description,
                    'type': w.value_type,
                    'condition': w.condition.value,
                    'threshold': w.threshold,
                    'enabled': w.enabled,
                    'triggers': w.trigger_count,
                    'last_value': w.last_value,
                }
                for w in self._watchpoints.values()
            ]


class ConditionalTriggerManager:
    """
    High-level manager for conditional cheat triggers.
    Integrates WatchpointManager with CheatManager.
    """
    
    def __init__(
        self,
        memory_scanner: Any,
        cheat_manager: Any,
    ):
        """
        Initialize conditional trigger manager.
        
        Args:
            memory_scanner: MemoryScanner instance
            cheat_manager: CheatManager instance
        """
        self.memory_scanner = memory_scanner
        self.cheat_manager = cheat_manager
        self.watchpoint_manager = WatchpointManager(memory_scanner)
        
        self._conditional_cheats: Dict[str, Dict[str, Any]] = {}
    
    def add_conditional_cheat(
        self,
        cheat_type: Any,  # CheatType
        watch_address: int,
        value_type: str,
        condition: ConditionType,
        threshold: Any,
        action: str = 'activate',  # 'activate', 'deactivate', 'toggle'
        cooldown_ms: int = 1000,
    ) -> bool:
        """
        Add a conditional cheat trigger.
        
        Args:
            cheat_type: Type of cheat to trigger
            watch_address: Address to monitor
            value_type: Type of value to monitor
            condition: Condition to check
            threshold: Threshold value
            action: Action to take when triggered
            cooldown_ms: Cooldown between triggers
            
        Returns:
            bool: True if added successfully
        """
        # Add watchpoint
        success = self.watchpoint_manager.add_watchpoint(
            address=watch_address,
            value_type=value_type,
            condition=condition,
            threshold=threshold,
            description=f"Conditional trigger for {cheat_type.value}",
            cooldown_ms=cooldown_ms,
        )
        
        if not success:
            return False
        
        # Add action
        from .watchpoints import TriggerAction
        
        action_obj = TriggerAction(
            action_type=f'{action}_cheat',
            target=cheat_type,
        )
        
        self.watchpoint_manager.add_action(watch_address, action_obj)
        
        # Store conditional cheat info
        self._conditional_cheats[cheat_type.value] = {
            'watch_address': watch_address,
            'condition': condition.value,
            'threshold': threshold,
            'action': action,
            'enabled': True,
        }
        
        logger.info(
            "Conditional cheat added: %s triggers when 0x%X %s %s",
            cheat_type.value, watch_address, condition.value, threshold
        )
        
        return True
    
    def remove_conditional_cheat(self, cheat_type: Any) -> bool:
        """
        Remove a conditional cheat trigger.
        
        Args:
            cheat_type: Type of cheat to remove
            
        Returns:
            bool: True if removed successfully
        """
        if cheat_type.value not in self._conditional_cheats:
            return False
        
        info = self._conditional_cheats[cheat_type.value]
        self.watchpoint_manager.remove_watchpoint(info['watch_address'])
        del self._conditional_cheats[cheat_type.value]
        
        logger.info("Conditional cheat removed: %s", cheat_type.value)
        return True
    
    def remove_all_conditional_cheats(self) -> int:
        """
        Remove all conditional cheats.
        
        Returns:
            Number of cheats removed
        """
        count = len(self._conditional_cheats)
        self.watchpoint_manager.remove_all_watchpoints()
        self._conditional_cheats.clear()
        logger.info("Removed %d conditional cheats", count)
        return count
    
    def get_conditional_cheats(self) -> Dict[str, Dict[str, Any]]:
        """Get all conditional cheats."""
        return self._conditional_cheats.copy()
