# Napoleon Total War - Plugin Development Guide

## Overview

The Napoleon Total War Cheat Engine supports hot-loadable Python plugins that can extend functionality through event hooks. Plugins can listen for game events, modify behavior, and add custom features without modifying the core codebase.

## Quick Start

### 1. Create Plugin Directory

```bash
mkdir -p plugins
```

### 2. Create Your First Plugin

Create `plugins/hello_world.py`:

```python
"""
Hello World Plugin - Example plugin for Napoleon TW Cheat Engine
"""

from src.plugins.manager import PluginBase, PluginMetadata

class HelloWorldPlugin(PluginBase):
    """Example plugin that logs messages on load/unload."""
    
    metadata = PluginMetadata(
        name="HelloWorld",
        version="1.0.0",
        author="Your Name",
        description="Example plugin demonstrating basic plugin structure"
    )
    
    def on_load(self, engine):
        """Called when plugin is loaded."""
        print("🎮 HelloWorld Plugin loaded!")
        print(f"Engine: {engine}")
        
        # Subscribe to events here
        # engine.events.subscribe('game_state_changed', self.on_game_state)
    
    def on_unload(self):
        """Called when plugin is unloaded."""
        print("👋 HelloWorld Plugin unloaded!")
    
    def on_enable(self):
        """Called when plugin is enabled."""
        print("✓ HelloWorld Plugin enabled")
        super().on_enable()
    
    def on_disable(self):
        """Called when plugin is disabled."""
        print("✗ HelloWorld Plugin disabled")
        super().on_disable()
```

### 3. Load the Plugin

In the GUI:
- Go to Settings → Plugins
- Click "Load Plugin"
- Select `plugins/hello_world.py`

Or via code:
```python
from src.plugins.manager import PluginManager

manager = PluginManager(plugin_dirs=[Path('plugins')])
manager.load_plugin('hello_world')
```

## Plugin Lifecycle

```
┌─────────────┐
│  on_load()  │ Called once when plugin is loaded
└──────┬──────┘
       │
       ▼
┌──────────────┐
│  on_enable() │ Called when plugin is enabled
└──────┬───────┘
       │
       ▼
┌────────────────┐
│ Event Handlers │ Called when events occur
└──────┬─────────┘
       │
       ▼
┌───────────────┐
│  on_disable() │ Called when plugin is disabled
└──────┬────────┘
       │
       ▼
┌──────────────┐
│  on_unload() │ Called once when plugin is unloaded
└──────────────┘
```

## Event System

Plugins can subscribe to engine events to react to game state changes.

### Available Events

#### Game State Events
- `game_launched` - Game process detected
- `game_closed` - Game process ended
- `game_state_changed` - Campaign/battle/loading state changed
- `mode_changed` - Switched between campaign and battle modes

#### Memory Events
- `memory_scan_complete` - Memory scan finished
- `cheat_activated` - Cheat was enabled
- `cheat_deactivated` - Cheat was disabled
- `address_found` - Memory address located

#### Trainer Events
- `hotkey_pressed` - Hotkey was pressed
- `overlay_shown` - Battle overlay displayed
- `overlay_hidden` - Battle overlay hidden

### Subscribing to Events

```python
class EventPlugin(PluginBase):
    metadata = PluginMetadata(
        name="EventWatcher",
        version="1.0.0",
        description="Listens for game events"
    )
    
    def on_load(self, engine):
        self.engine = engine
        
        # Subscribe to events
        engine.events.subscribe('game_state_changed', self.on_game_state)
        engine.events.subscribe('cheat_activated', self.on_cheat)
    
    def on_unload(self):
        # Unsubscribe from events
        self.engine.events.unsubscribe('game_state_changed', self.on_game_state)
        self.engine.events.unsubscribe('cheat_activated', self.on_cheat)
    
    def on_game_state(self, event_data):
        """Handle game state changes."""
        print(f"Game state changed: {event_data}")
    
    def on_cheat(self, event_data):
        """Handle cheat activation."""
        cheat_type = event_data.get('cheat_type')
        print(f"Cheat activated: {cheat_type}")
```

## Accessing Engine Services

Plugins have access to the engine's services through the `engine` parameter:

```python
class AdvancedPlugin(PluginBase):
    metadata = PluginMetadata(
        name="AdvancedPlugin",
        version="1.0.0",
        description="Demonstrates engine service access"
    )
    
    def on_load(self, engine):
        self.engine = engine
        
        # Access memory scanner
        scanner = engine.memory_scanner
        addresses = scanner.scan_exact(1000, value_type='i32')
        
        # Access cheat manager
        cheat_mgr = engine.cheat_manager
        cheat_mgr.toggle_cheat('infinite_gold')
        
        # Access game state
        game_state = engine.game_state
        if game_state.is_in_battle:
            print("Currently in battle!")
        
        # Access logger
        logger = engine.logger
        logger.info("Plugin loaded successfully")
```

## Plugin Metadata

Plugin metadata is used for identification and dependency management:

```python
metadata = PluginMetadata(
    name="MyPlugin",           # Unique identifier (required)
    version="1.0.0",           # Semantic versioning (optional, default: "1.0.0")
    author="Your Name",        # Author name (optional)
    description="Does cool stuff",  # Description (optional)
    requires=["OtherPlugin"]   # Dependencies (optional)
)
```

## Hot Reloading

Plugins can be hot-reloaded without restarting the application:

```python
# Reload a plugin
manager.reload_plugin('my_plugin')

# Reload all plugins
manager.reload_all()
```

This is useful for development - make changes and reload to test immediately.

## Error Handling

Plugins should handle errors gracefully:

```python
class RobustPlugin(PluginBase):
    metadata = PluginMetadata(
        name="RobustPlugin",
        version="1.0.0",
        description="Demonstrates error handling"
    )
    
    def on_load(self, engine):
        try:
            self.engine = engine
            # Risky operation
            self.setup_hooks()
        except Exception as e:
            print(f"Plugin load failed: {e}")
            # Plugin will be marked as failed but won't crash the app
    
    def on_event(self, data):
        try:
            self.process_event(data)
        except Exception as e:
            # Log error but continue
            print(f"Event handler error: {e}")
```

## Plugin Security

### Allowlist Mode

For production, use allowlist mode to only load trusted plugins:

```python
# Generate SHA-256 hash of plugin
import hashlib

with open('plugins/my_plugin.py', 'rb') as f:
    plugin_hash = hashlib.sha256(f.read()).hexdigest()

print(f"Plugin hash: {plugin_hash}")

# Add hash to allowlist
manager = PluginManager(
    plugin_dirs=[Path('plugins')],
    require_allowlist=True
)
manager.add_to_allowlist(plugin_hash)
```

### Best Practices

1. **Validate Input**: Always validate event data
2. **Handle Exceptions**: Catch and log errors
3. **Resource Cleanup**: Clean up in `on_unload()`
4. **Minimal Permissions**: Only access necessary services
5. **No Blocking Operations**: Use async for long operations

## Example Plugins

### 1. Auto-Save Plugin

```python
"""Auto-save plugin that triggers saves periodically."""

import time
from src.plugins.manager import PluginBase, PluginMetadata

class AutoSavePlugin(PluginBase):
    metadata = PluginMetadata(
        name="AutoSave",
        version="1.0.0",
        author="Community",
        description="Automatically saves game every 5 minutes"
    )
    
    def on_load(self, engine):
        self.engine = engine
        self.save_interval = 300  # 5 minutes
        self.last_save = time.time()
        
        engine.events.subscribe('game_state_changed', self.on_state_change)
    
    def on_unload(self):
        self.engine.events.unsubscribe('game_state_changed', self.on_state_change)
    
    def on_state_change(self, event):
        current_time = time.time()
        if current_time - self.last_save >= self.save_interval:
            self.trigger_save()
            self.last_save = current_time
    
    def trigger_save(self):
        """Trigger game save."""
        print("📀 Auto-saving game...")
        # Implementation depends on game's save API
```

### 2. Battle Statistics Tracker

```python
"""Tracks battle statistics and displays overlay."""

from src.plugins.manager import PluginBase, PluginMetadata

class BattleStatsPlugin(PluginBase):
    metadata = PluginMetadata(
        name="BattleStats",
        version="1.0.0",
        description="Tracks and displays battle statistics"
    )
    
    def __init__(self):
        super().__init__()
        self.stats = {
            'kills': 0,
            'losses': 0,
            'battles_won': 0,
            'battles_lost': 0,
        }
    
    def on_load(self, engine):
        self.engine = engine
        engine.events.subscribe('battle_ended', self.on_battle_end)
        engine.events.subscribe('unit_killed', self.on_unit_killed)
    
    def on_unload(self):
        self.engine.events.unsubscribe('battle_ended', self.on_battle_end)
        self.engine.events.unsubscribe('unit_killed', self.on_unit_killed)
    
    def on_battle_end(self, event):
        winner = event.get('winner')
        if winner == 'player':
            self.stats['battles_won'] += 1
        else:
            self.stats['battles_lost'] += 1
        self.show_stats()
    
    def on_unit_killed(self, event):
        if event.get('side') == 'enemy':
            self.stats['kills'] += 1
        else:
            self.stats['losses'] += 1
    
    def show_stats(self):
        """Display battle statistics."""
        print("📊 Battle Statistics:")
        print(f"  Kills: {self.stats['kills']}")
        print(f"  Losses: {self.stats['losses']}")
        print(f"  Battles Won: {self.stats['battles_won']}")
        print(f"  Battles Lost: {self.stats['battles_lost']}")
```

### 3. Custom Hotkey Plugin

```python
"""Adds custom hotkeys for complex cheat combinations."""

from src.plugins.manager import PluginBase, PluginMetadata

class CustomHotkeysPlugin(PluginBase):
    metadata = PluginMetadata(
        name="CustomHotkeys",
        version="1.0.0",
        description="Adds F12 hotkey for god mode + infinite ammo combo"
    )
    
    def on_load(self, engine):
        self.engine = engine
        engine.events.subscribe('hotkey_pressed', self.on_hotkey)
        
        # Register custom hotkey
        engine.hotkey_manager.register(
            key='F12',
            modifiers=['Ctrl', 'Shift'],
            callback=self.activate_combo,
            description="God Mode + Infinite Ammo"
        )
    
    def on_unload(self):
        self.engine.events.unsubscribe('hotkey_pressed', self.on_hotkey)
        self.engine.hotkey_manager.unregister('F12')
    
    def activate_combo(self):
        """Activate cheat combination."""
        print("⚡ Activating god mode + infinite ammo combo!")
        self.engine.cheat_manager.toggle_cheat('god_mode')
        self.engine.cheat_manager.toggle_cheat('unlimited_ammo')
    
    def on_hotkey(self, event):
        if event.get('key') == 'F12':
            self.activate_combo()
```

## Debugging Plugins

### Enable Plugin Debug Logging

```python
import logging
logging.getLogger('napoleon.plugins').setLevel(logging.DEBUG)
```

### Plugin Development Tips

1. **Use Logging**: `logger.info()`, `logger.debug()`, `logger.error()`
2. **Test Incrementally**: Load plugin, test one feature, repeat
3. **Check Logs**: Look for error messages in application logs
4. **Use Hot Reload**: Make changes and reload without restarting
5. **Start Simple**: Begin with basic plugin, add complexity gradually

## Plugin API Reference

### PluginBase Methods

| Method | Description | When Called |
|--------|-------------|-------------|
| `on_load(engine)` | Initialize plugin | Once when loaded |
| `on_unload()` | Cleanup resources | Once when unloaded |
| `on_enable()` | Enable plugin | When enabled |
| `on_disable()` | Disable plugin | When disabled |

### PluginBase Properties

| Property | Type | Description |
|----------|------|-------------|
| `name` | str | Plugin name from metadata |
| `enabled` | bool | Whether plugin is enabled |
| `metadata` | PluginMetadata | Plugin metadata object |

### PluginManager Methods

| Method | Description |
|--------|-------------|
| `load_plugin(name)` | Load plugin by name |
| `unload_plugin(name)` | Unload plugin |
| `reload_plugin(name)` | Reload plugin |
| `enable_plugin(name)` | Enable plugin |
| `disable_plugin(name)` | Disable plugin |
| `list_plugins()` | List all loaded plugins |
| `get_plugin(name)` | Get plugin instance |

## Troubleshooting

### Plugin Won't Load

**Symptoms**: Plugin doesn't appear in plugin list

**Solutions**:
1. Check plugin file is in correct directory
2. Verify plugin class inherits from `PluginBase`
3. Check for syntax errors: `python -m py_compile plugins/my_plugin.py`
4. Look for import errors in logs

### Plugin Crashes on Load

**Symptoms**: Application logs show exception

**Solutions**:
1. Wrap `on_load()` in try-except
2. Check engine service availability
3. Verify event subscriptions are valid
4. Test with minimal plugin first

### Events Not Firing

**Symptoms**: Event handler never called

**Solutions**:
1. Verify event name is correct
2. Check subscription in `on_load()`
3. Ensure plugin is enabled
4. Test with simple event like `game_state_changed`

## Best Practices

### Do ✅
- Keep plugins focused and small
- Handle all exceptions
- Clean up resources in `on_unload()`
- Use logging for debugging
- Test with hot reload
- Document your plugin

### Don't ❌
- Modify core engine code
- Block the main thread
- Ignore exceptions
- Leak resources
- Access private attributes (start with `_`)
- Assume engine state

## Publishing Plugins

### Plugin Structure

```
my_plugin/
├── README.md          # Plugin documentation
├── plugin.py          # Main plugin file
├── requirements.txt   # Dependencies (if any)
└── LICENSE            # License file
```

### README Template

```markdown
# My Plugin Name

## Description
What does your plugin do?

## Installation
1. Copy `plugin.py` to `plugins/` directory
2. Load via Settings → Plugins

## Features
- Feature 1
- Feature 2

## Configuration
(If applicable)

## Known Issues
(List any)

## Version History
- 1.0.0 - Initial release
```

## Resources

- [Developer Guide](DEVELOPER_GUIDE.md) - Core architecture details
- [API Documentation](../src/plugins/README.md) - Full API reference
- [Example Plugins](../examples/plugins/) - More examples
- [Security Guide](SECURITY.md) - Security best practices

## Support

For plugin development questions:
- Check existing documentation
- Review example plugins
- Enable debug logging
- Check application logs for errors

---

**Happy Plugin Development!** 🎮⚔️
