"""
Event system for decoupled architecture.
Provides publish/subscribe pattern for cheat activation, UI updates, and logging.
"""

from typing import Dict, List, Callable, Any, Optional
from dataclasses import dataclass, field
from enum import Enum
import threading
from datetime import datetime


class EventType(Enum):
    """Types of events in the system."""
    CHEAT_ACTIVATED = 'cheat_activated'
    CHEAT_DEACTIVATED = 'cheat_deactivated'
    PROCESS_ATTACHED = 'process_attached'
    PROCESS_DETACHED = 'process_detached'
    MEMORY_SCANNED = 'memory_scanned'
    FILE_LOADED = 'file_loaded'
    FILE_SAVED = 'file_saved'
    ERROR_OCCURRED = 'error_occurred'
    STATUS_CHANGED = 'status_changed'
    HOTKEY_PRESSED = 'hotkey_pressed'
    GAME_STATE_CHANGED = 'game_state_changed'


@dataclass
class Event:
    """Represents an event in the system."""
    event_type: EventType
    timestamp: datetime = field(default_factory=datetime.now)
    data: Dict[str, Any] = field(default_factory=dict)
    source: Optional[str] = None


@dataclass
class EventSubscription:
    """Represents an event subscription."""
    callback: Callable[[Event], None]
    once: bool = False  # If True, unsubscribe after first event
    priority: int = 0  # Higher priority callbacks execute first


class EventEmitter:
    """
    Central event bus for the application.
    Thread-safe publish/subscribe implementation.
    """
    
    _instance: Optional['EventEmitter'] = None
    _lock = threading.Lock()
    
    def __new__(cls) -> 'EventEmitter':
        """Singleton pattern."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        """Initialize event emitter."""
        if hasattr(self, '_initialized') and self._initialized:
            return
        
        self._subscribers: Dict[EventType, List[EventSubscription]] = {}
        self._event_history: List[Event] = []
        self._max_history = 100
        self._lock = threading.Lock()
        self._initialized = True
    
    def on(
        self,
        event_type: EventType,
        callback: Callable[[Event], None],
        once: bool = False,
        priority: int = 0
    ) -> None:
        """
        Subscribe to an event.
        
        Args:
            event_type: Type of event to subscribe to
            callback: Function to call when event occurs
            once: If True, unsubscribe after first event
            priority: Execution priority (higher = earlier)
        """
        with self._lock:
            if event_type not in self._subscribers:
                self._subscribers[event_type] = []
            
            subscription = EventSubscription(
                callback=callback,
                once=once,
                priority=priority
            )
            
            self._subscribers[event_type].append(subscription)
            # Sort by priority (descending)
            self._subscribers[event_type].sort(
                key=lambda s: s.priority,
                reverse=True
            )
    
    def off(
        self,
        event_type: EventType,
        callback: Optional[Callable[[Event], None]] = None
    ) -> int:
        """
        Unsubscribe from an event.
        
        Args:
            event_type: Type of event
            callback: Optional specific callback to remove (None removes all)
            
        Returns:
            int: Number of subscriptions removed
        """
        with self._lock:
            if event_type not in self._subscribers:
                return 0
            
            if callback is None:
                count = len(self._subscribers[event_type])
                del self._subscribers[event_type]
                return count
            
            original_count = len(self._subscribers[event_type])
            self._subscribers[event_type] = [
                s for s in self._subscribers[event_type]
                if s.callback != callback
            ]
            return original_count - len(self._subscribers[event_type])
    
    def emit(self, event_type: EventType, data: Dict[str, Any] = None, source: Optional[str] = None) -> None:
        """
        Emit an event to all subscribers.
        
        Args:
            event_type: Type of event
            data: Optional event data
            source: Optional source identifier
        """
        event = Event(
            event_type=event_type,
            data=data or {},
            source=source
        )
        
        with self._lock:
            # Add to history
            self._event_history.append(event)
            if len(self._event_history) > self._max_history:
                self._event_history.pop(0)
            
            # Get subscribers
            if event_type not in self._subscribers:
                return
            
            # Copy list to avoid modification during iteration
            subscribers = self._subscribers[event_type].copy()
        
        # Execute callbacks (outside lock to prevent deadlocks)
        to_remove = []
        
        for subscription in subscribers:
            try:
                subscription.callback(event)
                
                if subscription.once:
                    to_remove.append(subscription.callback)
                    
            except Exception as e:
                print(f"Event callback error ({event_type.value}): {e}")
        
        # Remove one-time subscriptions
        if to_remove:
            with self._lock:
                if event_type in self._subscribers:
                    self._subscribers[event_type] = [
                        s for s in self._subscribers[event_type]
                        if s.callback not in to_remove
                    ]
    
    def get_history(
        self,
        event_type: Optional[EventType] = None,
        limit: int = 50
    ) -> List[Event]:
        """
        Get event history.
        
        Args:
            event_type: Optional filter by type
            limit: Maximum number of events to return
            
        Returns:
            List[Event]: List of events
        """
        with self._lock:
            if event_type:
                events = [e for e in self._event_history if e.event_type == event_type]
            else:
                events = self._event_history.copy()
            
            return events[-limit:]
    
    def clear_history(self) -> None:
        """Clear event history."""
        with self._lock:
            self._event_history.clear()
    
    @classmethod
    def reset_instance(cls) -> None:
        """Reset the singleton instance. Used for test isolation."""
        with cls._lock:
            if cls._instance is not None:
                instance = cls._instance
                instance._subscribers.clear()
                instance._event_history.clear()
            cls._instance = None
    
    def once(
        self,
        event_type: EventType,
        callback: Callable[[Event], None],
        priority: int = 0
    ) -> None:
        """
        Subscribe to an event only once.
        
        Args:
            event_type: Type of event
            callback: Function to call
            priority: Execution priority
        """
        self.on(event_type, callback, once=True, priority=priority)


# Convenience functions for common events
def emit_cheat_activated(cheat_type: str, address: Optional[int] = None) -> None:
    """Emit cheat activated event."""
    EventEmitter().emit(
        EventType.CHEAT_ACTIVATED,
        data={'cheat_type': cheat_type, 'address': address},
        source='cheat_manager'
    )


def emit_cheat_deactivated(cheat_type: str) -> None:
    """Emit cheat deactivated event."""
    EventEmitter().emit(
        EventType.CHEAT_DEACTIVATED,
        data={'cheat_type': cheat_type},
        source='cheat_manager'
    )


def emit_error(error_msg: str, source: str = 'unknown') -> None:
    """Emit error event."""
    EventEmitter().emit(
        EventType.ERROR_OCCURRED,
        data={'error': error_msg},
        source=source
    )
