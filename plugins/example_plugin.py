"""
Example plugin for Napoleon Total War Cheat Engine.
Demonstrates the plugin API.
"""

from src.plugins.manager import PluginBase, PluginMetadata

import logging
logger = logging.getLogger('napoleon.plugins.example')


class ExamplePlugin(PluginBase):
    """Example plugin that logs cheat activations."""
    
    metadata = PluginMetadata(
        name="ExamplePlugin",
        version="1.0.0",
        author="Napoleon Cheat Engine",
        description="Example plugin - logs cheat activations and game state changes",
    )
    
    def on_load(self, engine) -> None:
        """Subscribe to events."""
        self._engine = engine
        logger.info("[ExamplePlugin] Loaded! Engine: %s", type(engine).__name__ if engine else 'None')
        
        # Subscribe to events if event system available
        try:
            from src.utils.events import EventEmitter, EventType
            emitter = EventEmitter()
            emitter.on(EventType.CHEAT_ACTIVATED, self._on_cheat_activated)
            emitter.on(EventType.CHEAT_DEACTIVATED, self._on_cheat_deactivated)
            emitter.on(EventType.ERROR_OCCURRED, self._on_error)
            logger.info("[ExamplePlugin] Subscribed to events")
        except ImportError:
            logger.warning("[ExamplePlugin] Event system not available")
    
    def on_unload(self) -> None:
        """Clean up."""
        logger.info("[ExamplePlugin] Unloaded")
        
        try:
            from src.utils.events import EventEmitter, EventType
            emitter = EventEmitter()
            emitter.off(EventType.CHEAT_ACTIVATED, self._on_cheat_activated)
            emitter.off(EventType.CHEAT_DEACTIVATED, self._on_cheat_deactivated)
            emitter.off(EventType.ERROR_OCCURRED, self._on_error)
        except ImportError:
            pass
    
    def _on_cheat_activated(self, event) -> None:
        logger.info("[ExamplePlugin] Cheat activated: %s", event.data.get('cheat_type', 'unknown'))
    
    def _on_cheat_deactivated(self, event) -> None:
        logger.info("[ExamplePlugin] Cheat deactivated: %s", event.data.get('cheat_type', 'unknown'))
    
    def _on_error(self, event) -> None:
        logger.warning("[ExamplePlugin] Error: %s", event.data.get('error', 'unknown'))
