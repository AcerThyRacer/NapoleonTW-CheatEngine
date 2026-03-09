"""
Hotkey management system for the trainer.
Uses pynput for cross-platform keyboard hooks.
"""

import logging
from typing import Dict, Callable, Optional, List, Set
from dataclasses import dataclass
from enum import Enum
import threading
import time

logger = logging.getLogger('napoleon.trainer.hotkeys')

try:
    from pynput.keyboard import Key, KeyCode, Listener
    PYNPUT_AVAILABLE = True
except ImportError:
    PYNPUT_AVAILABLE = False
    logger.warning("pynput not installed. Hotkeys will not work. Install with: pip install pynput")
    
    # Mock Key class so class definitions don't crash
    class _MockKey:
        f1 = f2 = f3 = f4 = f5 = f6 = f7 = f8 = f9 = f10 = f11 = f12 = None
        insert = delete = home = end = page_up = page_down = None
        up = down = left = right = space = tab = enter = esc = None
        ctrl_l = ctrl_r = alt_l = alt_r = shift_l = shift_r = None
    
    Key = _MockKey()
    KeyCode = type(None)
    Listener = None


class ModifierKey(Enum):
    """Modifier keys for hotkey combinations."""
    CTRL = 'ctrl'
    ALT = 'alt'
    SHIFT = 'shift'
    WIN = 'win'


@dataclass
class HotkeyBinding:
    """Represents a hotkey binding."""
    key: str
    modifiers: List[ModifierKey]
    action: Callable
    description: str
    enabled: bool = True


class HotkeyManager:
    """
    Cross-platform hotkey manager using pynput.
    """
    
    def __init__(self):
        """Initialize hotkey manager."""
        self.bindings: Dict[str, HotkeyBinding] = {}
        self.active_modifiers: Set[ModifierKey] = set()
        self.listener: Optional[object] = None
        self.is_running: bool = False
        self.lock = threading.Lock()
        self.error_count: int = 0
        self.max_errors_before_restart: int = 5
        self.last_error_time: float = 0
        self.error_cooldown: float = 1.0
        self.status_callback: Optional[Callable[[str], None]] = None
        
        # Build key mappings only if pynput is available
        self._key_mappings: Dict[str, object] = {}
        if PYNPUT_AVAILABLE:
            self._key_mappings = {
                'f1': Key.f1, 'f2': Key.f2, 'f3': Key.f3, 'f4': Key.f4,
                'f5': Key.f5, 'f6': Key.f6, 'f7': Key.f7, 'f8': Key.f8,
                'f9': Key.f9, 'f10': Key.f10, 'f11': Key.f11, 'f12': Key.f12,
                'insert': Key.insert, 'delete': Key.delete,
                'home': Key.home, 'end': Key.end,
                'page_up': Key.page_up, 'page_down': Key.page_down,
                'up': Key.up, 'down': Key.down, 'left': Key.left, 'right': Key.right,
                'space': Key.space, 'tab': Key.tab,
                'enter': Key.enter, 'escape': Key.esc,
            }
        
    def register_hotkey(
        self,
        key: str,
        action: Callable,
        description: str,
        modifiers: Optional[List[str]] = None
    ) -> bool:
        """
        Register a hotkey binding.
        
        Args:
            key: Key name (e.g., 'f1', 'insert', 'a')
            action: Callback function to execute
            description: Description of the hotkey
            modifiers: Optional list of modifier keys ('ctrl', 'alt', 'shift')
            
        Returns:
            bool: True if registered successfully
        """
        if not PYNPUT_AVAILABLE:
            logger.error("pynput not available, cannot register hotkey")
            return False
        
        modifier_keys = []
        if modifiers:
            for mod in modifiers:
                try:
                    modifier_keys.append(ModifierKey(mod.lower()))
                except ValueError:
                    logger.error("Invalid modifier: %s", mod)
                    return False
        
        binding = HotkeyBinding(
            key=key.lower(),
            modifiers=modifier_keys,
            action=action,
            description=description,
            enabled=True
        )
        
        mod_str = '-'.join([m.value for m in modifier_keys])
        binding_id = f"{mod_str}-{key}" if mod_str else key
        
        with self.lock:
            self.bindings[binding_id] = binding
        
        logger.info("Registered hotkey: %s - %s", binding_id, description)
        return True
    
    def unregister_hotkey(self, binding_id: str) -> bool:
        """Unregister a hotkey."""
        with self.lock:
            if binding_id in self.bindings:
                del self.bindings[binding_id]
                logger.info("Unregistered hotkey: %s", binding_id)
                return True
        return False
    
    def enable_hotkey(self, binding_id: str, enabled: bool = True) -> bool:
        """Enable or disable a hotkey."""
        with self.lock:
            if binding_id in self.bindings:
                self.bindings[binding_id].enabled = enabled
                return True
        return False
    
    def start(self) -> bool:
        """Start the hotkey listener."""
        if not PYNPUT_AVAILABLE:
            logger.error("Cannot start hotkey listener: pynput not available")
            return False
        
        if self.is_running:
            logger.warning("Hotkey listener already running")
            return False
        
        try:
            self.listener = Listener(
                on_press=self._on_press,
                on_release=self._on_release
            )
            self.listener.start()
            self.is_running = True
            logger.info("Hotkey listener started")
            return True
            
        except Exception as e:
            logger.error("Failed to start hotkey listener: %s", e)
            return False
    
    def stop(self) -> None:
        """Stop the hotkey listener."""
        if self.listener and self.is_running:
            try:
                self.listener.stop()
            except Exception as e:
                logger.debug("Error stopping listener: %s", e)
            self.is_running = False
            logger.info("Hotkey listener stopped")
    
    def _on_press(self, key) -> None:
        """Handle key press events with error recovery."""
        try:
            if not PYNPUT_AVAILABLE:
                return
                
            if key == Key.ctrl_l or key == Key.ctrl_r:
                self.active_modifiers.add(ModifierKey.CTRL)
            elif key == Key.alt_l or key == Key.alt_r:
                self.active_modifiers.add(ModifierKey.ALT)
            elif key == Key.shift_l or key == Key.shift_r:
                self.active_modifiers.add(ModifierKey.SHIFT)
            
            self._check_hotkey(key)
            
        except Exception as e:
            self._handle_error(f"Key press handler error: {e}")
    
    def _on_release(self, key) -> None:
        """Handle key release events with error recovery."""
        try:
            if not PYNPUT_AVAILABLE:
                return
                
            if key == Key.ctrl_l or key == Key.ctrl_r:
                self.active_modifiers.discard(ModifierKey.CTRL)
            elif key == Key.alt_l or key == Key.alt_r:
                self.active_modifiers.discard(ModifierKey.ALT)
            elif key == Key.shift_l or key == Key.shift_r:
                self.active_modifiers.discard(ModifierKey.SHIFT)
            
        except Exception as e:
            self._handle_error(f"Key release handler error: {e}")
    
    def _check_hotkey(self, key) -> None:
        """Check if pressed key matches a registered hotkey."""
        with self.lock:
            for binding_id, binding in self.bindings.items():
                if not binding.enabled:
                    continue
                
                if set(binding.modifiers) != self.active_modifiers:
                    continue
                
                if self._keys_match(key, binding.key):
                    try:
                        logger.debug("Hotkey triggered: %s", binding_id)
                        binding.action()
                    except Exception as e:
                        logger.error("Hotkey action failed (%s): %s", binding_id, e)
    
    def _keys_match(self, key, key_name: str) -> bool:
        """Check if pressed key matches key name."""
        if key_name in self._key_mappings:
            return key == self._key_mappings[key_name]
        
        if PYNPUT_AVAILABLE and isinstance(key, KeyCode):
            if key.char and key.char.lower() == key_name.lower():
                return True
        
        return False
    
    def get_registered_hotkeys(self) -> List[Dict]:
        """Get list of registered hotkeys."""
        return [
            {
                'id': binding_id,
                'key': binding.key,
                'modifiers': [m.value for m in binding.modifiers],
                'description': binding.description,
                'enabled': binding.enabled,
            }
            for binding_id, binding in self.bindings.items()
        ]
    
    def is_listening(self) -> bool:
        """Check if listener is running."""
        return self.is_running
    
    def _handle_error(self, error_msg: str) -> None:
        """Handle errors with recovery logic."""
        current_time = time.time()
        self.error_count += 1
        
        logger.warning("Hotkey error (%d): %s", self.error_count, error_msg)
        
        if self.error_count >= self.max_errors_before_restart:
            time_since_last = current_time - self.last_error_time
            
            if time_since_last > self.error_cooldown:
                logger.info("Too many errors, attempting to restart listener...")
                self._attempt_reconnect()
                self.error_count = 0
                self.last_error_time = current_time
        
        if self.status_callback:
            self.status_callback(f"Error: {error_msg}")
    
    def _attempt_reconnect(self) -> bool:
        """Attempt to reconnect the hotkey listener."""
        try:
            if self.listener:
                self.listener.stop()
                self.listener = None
            
            self.is_running = False
            time.sleep(0.5)
            
            if self.start():
                logger.info("Hotkey listener restarted successfully")
                if self.status_callback:
                    self.status_callback("Hotkey listener reconnected")
                return True
            else:
                logger.error("Failed to restart hotkey listener")
                if self.status_callback:
                    self.status_callback("Failed to reconnect hotkeys")
                return False
                
        except Exception as e:
            logger.error("Reconnection failed: %s", e)
            if self.status_callback:
                self.status_callback(f"Reconnection failed: {e}")
            return False
    
    def set_status_callback(self, callback: Callable[[str], None]) -> None:
        """Set a callback for status updates."""
        self.status_callback = callback
    
    def reset_error_count(self) -> None:
        """Reset error counter."""
        self.error_count = 0


class CheatHotkeys:
    """
    Pre-defined hotkey configurations for common cheats.
    """
    
    def __init__(self, hotkey_manager: HotkeyManager):
        """Initialize cheat hotkeys."""
        self.hotkey_manager = hotkey_manager
        self.cheat_callbacks: Dict[str, Callable] = {}
    
    def register_cheat_hotkey(
        self,
        cheat_name: str,
        key: str,
        callback: Callable,
        modifiers: Optional[List[str]] = None
    ) -> bool:
        """Register a hotkey for a cheat."""
        self.cheat_callbacks[cheat_name] = callback
        
        return self.hotkey_manager.register_hotkey(
            key=key,
            action=callback,
            description=f"Toggle {cheat_name}",
            modifiers=modifiers
        )
    
    def setup_default_cheat_hotkeys(self, cheat_manager) -> bool:
        """Setup default hotkeys for common cheats."""
        from src.memory.cheats import CheatType
        
        # Campaign cheats - actually call cheat_manager now
        self.register_cheat_hotkey(
            "Infinite Gold", "f2",
            lambda: self._toggle_campaign_cheat(cheat_manager, CheatType.INFINITE_GOLD),
            modifiers=['shift']
        )
        
        self.register_cheat_hotkey(
            "Unlimited Movement", "f3",
            lambda: self._toggle_campaign_cheat(cheat_manager, CheatType.UNLIMITED_MOVEMENT),
            modifiers=['shift']
        )
        
        self.register_cheat_hotkey(
            "Instant Construction", "f4",
            lambda: self._toggle_campaign_cheat(cheat_manager, CheatType.INSTANT_CONSTRUCTION),
            modifiers=['shift']
        )
        
        self.register_cheat_hotkey(
            "Fast Research", "f5",
            lambda: self._toggle_campaign_cheat(cheat_manager, CheatType.FAST_RESEARCH),
            modifiers=['shift']
        )
        
        # Battle cheats
        self.register_cheat_hotkey(
            "God Mode", "f1",
            lambda: self._toggle_battle_cheat(cheat_manager, CheatType.GOD_MODE),
            modifiers=['ctrl']
        )
        
        self.register_cheat_hotkey(
            "Unlimited Ammo", "f2",
            lambda: self._toggle_battle_cheat(cheat_manager, CheatType.UNLIMITED_AMMO),
            modifiers=['ctrl']
        )
        
        self.register_cheat_hotkey(
            "High Morale", "f3",
            lambda: self._toggle_battle_cheat(cheat_manager, CheatType.HIGH_MORALE),
            modifiers=['ctrl']
        )
        
        self.register_cheat_hotkey(
            "Infinite Stamina", "f4",
            lambda: self._toggle_battle_cheat(cheat_manager, CheatType.INFINITE_STAMINA),
            modifiers=['ctrl']
        )
        
        self.register_cheat_hotkey(
            "One-Hit Kill", "f5",
            lambda: self._toggle_battle_cheat(cheat_manager, CheatType.ONE_HIT_KILL),
            modifiers=['ctrl']
        )
        
        self.register_cheat_hotkey(
            "Super Speed", "f6",
            lambda: self._toggle_battle_cheat(cheat_manager, CheatType.SUPER_SPEED),
            modifiers=['ctrl']
        )
        
        return True
    
    def _toggle_campaign_cheat(self, cheat_manager, cheat_type) -> None:
        """Toggle a campaign cheat - actually calls cheat_manager."""
        try:
            result = cheat_manager.toggle_cheat(cheat_type)
            is_active = cheat_manager.is_cheat_active(cheat_type)
            status = "ACTIVATED" if is_active else "DEACTIVATED"
            logger.info("Campaign cheat %s: %s (success=%s)", cheat_type.value, status, result)
        except Exception as e:
            logger.error("Failed to toggle campaign cheat %s: %s", cheat_type.value, e)
    
    def _toggle_battle_cheat(self, cheat_manager, cheat_type) -> None:
        """Toggle a battle cheat - actually calls cheat_manager."""
        try:
            result = cheat_manager.toggle_cheat(cheat_type)
            is_active = cheat_manager.is_cheat_active(cheat_type)
            status = "ACTIVATED" if is_active else "DEACTIVATED"
            logger.info("Battle cheat %s: %s (success=%s)", cheat_type.value, status, result)
        except Exception as e:
            logger.error("Failed to toggle battle cheat %s: %s", cheat_type.value, e)
