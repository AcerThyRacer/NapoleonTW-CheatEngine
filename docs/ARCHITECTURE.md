# Napoleon Total War Cheat Engine - Architecture Overview

## System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        Entry Points                              │
│  ┌─────────┬─────────┬──────────┬──────────────┬────────────┐  │
│  │   GUI   │   CLI   │ Trainer  │   Panel      │ Background │  │
│  │  main() │  main() │  main()  │   main()     │  Trainer   │  │
│  └────┬────┴────┬────┴────┬─────┴──────┬───────┴─────┬──────┘  │
│       │         │         │            │             │          │
└───────┼─────────┼─────────┼────────────┼─────────────┼──────────┘
        │         │         │            │             │
        └─────────┴─────────┴────────────┴─────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Core Services Layer                         │
│  ┌──────────────┐  ┌──────────────┐  ┌─────────────────────┐   │
│  │    Memory    │  │   Trainer    │  │       Config        │   │
│  │   Scanner    │  │   Hotkeys    │  │      Manager        │   │
│  └──────┬───────┘  └──────┬───────┘  └──────────┬──────────┘   │
│         │                 │                      │              │
│  ┌──────▼───────┐  ┌──────▼───────┐  ┌──────────▼──────────┐   │
│  │    Cheats    │  │   Overlay    │  │       Events        │   │
│  │   Manager    │  │   System     │  │      System         │   │
│  └──────┬───────┘  └──────┬───────┘  └──────────┬──────────┘   │
│         │                 │                      │              │
│  ┌──────▼───────┐  ┌──────▼───────┐  ┌──────────▼──────────┐   │
│  │    Memory    │  │    Battle    │  │       Plugin        │   │
│  │   Freezer    │  │    Map       │  │      Manager        │   │
│  │              │  │  Overlay     │  │                     │   │
│  └──────────────┘  └──────────────┘  └─────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Memory Abstraction Layer                      │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │              MemoryBackend (Cross-Platform)               │   │
│  │  ┌────────────┐  ┌────────────┐  ┌────────────────────┐  │   │
│  │  │  Windows   │  │   Linux    │  │      Proton        │  │   │
│  │  │  Backend   │  │  Backend   │  │    (Wine)          │  │   │
│  │  └────────────┘  └────────────┘  └────────────────────┘  │   │
│  └──────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Operating System                            │
│              Windows  │  Linux (Native)  │  Proton/Wine         │
└─────────────────────────────────────────────────────────────────┘
```

## Module Dependencies

```
src/
├── main.py                    # Entry point - all modes
│
├── gui/                       # User Interface
│   ├── __init__.py           # Lazy exports
│   ├── main_window.py        # Classic tabbed GUI
│   ├── napoleon_panel.py     # Animated Napoleon UI
│   ├── memory_tab.py         # Memory scanner UI
│   ├── trainer_tab.py        # Trainer controls UI
│   ├── battle_overlay.py     # Battle map overlay
│   ├── preset_manager.py     # Cheat presets
│   └── setup_wizard.py       # First-run setup
│
├── memory/                    # Memory Operations
│   ├── __init__.py           # Public API exports
│   ├── backend.py            # Cross-platform memory access
│   ├── scanner.py            # Value/pattern scanning
│   ├── cheats.py             # Cheat definitions
│   ├── advanced.py           # Freezer, hooks, AOB
│   ├── watchpoints.py        # Conditional breakpoints
│   ├── ml_predictor.py       # ML address prediction
│   ├── signatures.py         # Pattern database
│   ├── speedhack.py          # Time manipulation
│   └── teleport.py           # Coordinate changes
│
├── trainer/                   # Runtime Trainer
│   ├── __init__.py           # Public API
│   ├── cheats.py             # High-level cheat API
│   ├── hotkeys.py            # Keyboard hooks
│   ├── overlay.py            # Visual overlays
│   ├── background.py         # Headless mode
│   ├── sync.py               # Multi-instance sync
│   └── effects_overlay.py    # Cheat effects
│
├── plugins/                   # Plugin System
│   ├── __init__.py           # Public API
│   └── manager.py            # Plugin lifecycle
│
├── files/                     # File Operations
│   ├── esf_editor.py         # Save game parser
│   ├── script_editor.py      # Lua/config editor
│   └── dxvk_installer.py     # Vulkan setup
│
├── pack/                      # Pack File Tools
│   └── mod_creator.py        # Mod creation
│
├── utils/                     # Utilities
│   ├── game_state.py         # Process monitoring
│   ├── events.py             # Event system
│   ├── logging_config.py     # Logging setup
│   ├── platform.py           # OS detection
│   └── error_reporter.py     # Error handling
│
└── config.py                  # Configuration management
```

## Data Flow

### Memory Scanning Flow

```
User Input (GUI/CLI)
       │
       ▼
┌──────────────┐
│ MemoryScanner│
└──────┬───────┘
       │ scan_exact(value, type)
       ▼
┌──────────────┐
│ChunkedScanner│ ← Parallel multi-threaded scan
└──────┬───────┘
       │ read_memory(address, size)
       ▼
┌──────────────┐
│MemoryBackend │ ← Platform-specific implementation
└──────┬───────┘
       │
       ▼
Game Process Memory
```

### Cheat Activation Flow

```
Hotkey Pressed
       │
       ▼
┌──────────────┐
│ HotkeyManager│
└──────┬───────┘
       │ on_hotkey(cheat_id)
       ▼
┌──────────────┐
│ CheatManager │
└──────┬───────┘
       │ toggle_cheat(cheat_id)
       ▼
┌──────────────┐
│MemoryFreezer │ OR │PointerResolver│
└──────┬───────┘     └──────┬────────┘
       │                    │
       └────────┬───────────┘
                │
                ▼
       ┌────────────────┐
       │ MemoryBackend  │ ← Write to game memory
       └────────────────┘
```

### Event System Flow

```
┌──────────────┐
│ Game Process │
└──────┬───────┘
       │ Process State Change
       ▼
┌──────────────┐
│ GameState    │
│ Monitor      │
└──────┬───────┘
       │ emit('game_state_changed', data)
       ▼
┌──────────────┐
│ EventEmitter │
└──────┬───────┘
       │ Broadcast to subscribers
       ▼
┌─────────┬─────────┬──────────┐
│Trainer  │ Overlay │  Plugin  │
│         │         │          │
└─────────┴─────────┴──────────┘
```

## Key Design Patterns

### 1. Backend Abstraction

```python
# Platform-independent interface
class MemoryBackend:
    def read_bytes(self, address: int, size: int) -> bytes:
        pass
    
    def write_bytes(self, address: int, data: bytes) -> bool:
        pass

# Platform-specific implementations
class WindowsBackend(MemoryBackend):
    def read_bytes(self, address, size):
        # Use Windows API (ReadProcessMemory)
        pass

class LinuxBackend(MemoryBackend):
    def read_bytes(self, address, size):
        # Use /proc/[pid]/mem or ptrace
        pass
```

### 2. Event-Driven Architecture

```python
# Publish-Subscribe pattern
class EventEmitter:
    def subscribe(self, event: str, callback: Callable):
        self._subscribers[event].append(callback)
    
    def emit(self, event: str, data: Any):
        for callback in self._subscribers[event]:
            callback(data)

# Usage
events.subscribe('cheat_activated', lambda e: print(f"Cheat: {e}"))
events.emit('cheat_activated', 'infinite_gold')
```

### 3. Lazy Loading

```python
# Import modules only when needed
_LAZY_EXPORTS = {
    'MainWindow': '.main_window',
    'TrainerTab': '.trainer_tab',
}

def __getattr__(name):
    module = import_module(_LAZY_EXPORTS[name], __name__)
    return getattr(module, name)
```

### 4. Circuit Breaker Pattern

```python
# Prevent cascading failures
class FrozenAddress:
    error_count: int = 0
    cooldown_until: float = 0.0
    
    def write(self, value):
        if time.time() < self.cooldown_until:
            return  # In cooldown
        
        try:
            # Attempt write
            pass
        except Exception:
            self.error_count += 1
            if self.error_count >= 3:
                # Enter cooldown
                self.cooldown_until = time.time() + 60.0
```

## Configuration System

### INI File Structure

```ini
[paths]
game_path = /path/to/napoleon.exe
save_dir = /path/to/saves

[logging]
level = INFO
file = napoleon.log

[ui]
theme = napoleon_gold
overlay_preset = balanced_command

[hotkeys]
god_mode = F1
infinite_gold = F2

[plugins]
allowlist_enabled = false
plugin_dirs = plugins/
```

### Config Management

```python
from src.config import ConfigManager

config = ConfigManager()
config.load()  # Read from napoleon.ini

# Access settings
game_path = config.config.game_path
theme = config.config.ui_theme

# Modify and save
config.config.ui_theme = 'imperial_blue'
config.save()
```

## Security Model

### Plugin Security

1. **Allowlist Mode**: Only load plugins with known SHA-256 hashes
2. **Sandboxing**: Plugins run in same process (trusted model)
3. **Validation**: Plugin metadata validated before loading
4. **Error Isolation**: Plugin errors don't crash main application

### Memory Access Security

1. **Process Validation**: Verify target process is Napoleon TW
2. **Signature Validation**: Use AOB patterns instead of hardcoded addresses
3. **Error Handling**: Graceful degradation on access failures
4. **Permission Checks**: Validate OS-level permissions

## Performance Optimizations

### Memory Scanning

- **Chunked Reading**: Read memory in 1MB chunks (cache-friendly)
- **Parallel Scanning**: Multi-threaded scanning across CPU cores
- **Index-Based Search**: Skip non-matching regions quickly
- **Direct Bytes Comparison**: 10-50x faster for non-wildcard patterns

### Memory Freezing

- **Lazy Value Freezing**: Only write if value has drifted
- **Circuit Breaker**: Cooldown on repeated failures
- **Configurable Intervals**: Balance CPU usage vs. freeze accuracy
- **Background Thread**: Non-blocking freeze loop

### UI Performance

- **Lazy Loading**: Import GUI modules only when needed
- **Animated Components**: GPU-accelerated PyQt6 animations
- **Event Debouncing**: Limit rapid event firing
- **Async Operations**: Long operations run in background threads

## Extension Points

### 1. Custom Cheats

```python
from src.memory.cheats import CheatDefinition, PointerChain

class CustomCheat(CheatDefinition):
    name = "My Custom Cheat"
    pointer_chain = PointerChain(
        base_address=0x12345678,
        offsets=[0x10, 0x20, 0x30]
    )
    value_type = 'i32'
    cheat_value = 9999
```

### 2. Custom Overlays

```python
from src.trainer.overlay import BattleMapOverlay

class CustomOverlay(BattleMapOverlay):
    def _render(self, painter):
        # Custom rendering logic
        painter.drawText(0, 0, "Custom Overlay")
```

### 3. Custom Plugins

See [PLUGIN_GUIDE.md](PLUGIN_GUIDE.md) for detailed plugin development guide.

## Testing Strategy

### Unit Tests

```bash
# Run all tests
pytest tests/ -v

# Run specific test file
pytest tests/test_memory.py -v

# Run with coverage
pytest tests/ --cov=src --cov-report=html
```

### Integration Tests

- Memory scanning against real game process
- Hotkey registration and triggering
- Plugin load/unload lifecycle
- GUI component rendering

### Test Categories

1. **Unit Tests**: Individual functions/classes
2. **Integration Tests**: Module interactions
3. **Live Tests**: Real game process (optional)
4. **Performance Tests**: Scan speed, CPU usage

## Deployment

### Platform Support

| Platform | Status | Notes |
|----------|--------|-------|
| Windows 10/11 | ✅ Native | Full support |
| Linux (Native) | ✅ Native | Requires ptrace permissions |
| Linux (Proton) | ✅ Supported | Wine compatibility layer |
| macOS | ❌ Not Supported | Different executable format |

### Installation

```bash
# Clone repository
git clone https://github.com/yourusername/NapoleonTWCheat.git
cd NapoleonTWCheat

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # Linux
.venv\Scripts\activate     # Windows

# Install dependencies
pip install -r requirements.txt

# Run
python -m src.main --gui
```

### Launch Modes

```bash
# GUI mode (default)
python -m src.main

# Napoleon Panel (animated UI)
python -m src.main --panel

# Trainer mode (hotkeys only)
python -m src.main --trainer

# Background trainer (headless)
python -m src.main --background

# Memory scanner only
python -m src.main --memory-scanner

# CLI mode
python -m src.main --cli
```

## Version History

### v2.1.0 (Current)
- Background trainer with auto-attach
- Battle map overlay with presets
- Napoleon Control Panel (animated UI)
- Optimized memory scanning
- Watchpoints and conditional triggers
- ML predictor for address resolution
- Multi-instance sync
- Plugin system

### v2.0.0
- Cross-platform support (Windows/Linux)
- Memory freezer with lazy writes
- Speedhack/time manipulation
- Teleport manager
- AOB pattern scanning
- Pointer chain resolution

### v1.0.0
- Initial release
- Basic memory scanning
- Simple cheat toggles
- Windows only

## Contributing

### Code Style

- **TypeScript-like Python**: Use type hints everywhere
- **Functional over OOP**: Prefer functions to classes
- **Small Functions**: < 50 lines per function
- **Test-Driven**: Write tests first
- **Documentation**: Docstrings for all public APIs

### Pull Request Process

1. Fork repository
2. Create feature branch
3. Write tests
4. Implement feature
5. Run linter: `flake8 src/ tests/`
6. Run tests: `pytest tests/ -v`
7. Submit PR with description

### Architecture Decisions

Major changes should include:
- Architecture Decision Record (ADR)
- Performance impact analysis
- Security review
- Backward compatibility plan

## Resources

- [Plugin Guide](PLUGIN_GUIDE.md) - Plugin development
- [Developer Guide](DEVELOPER_GUIDE.md) - Detailed development guide
- [User Guide](USER_GUIDE.md) - End-user documentation
- [Security Guide](SECURITY.md) - Security best practices
- [Quick Reference](QUICK_REFERENCE_V2.md) - Quick command reference

---

**Architecture documentation last updated**: March 10, 2026  
**Version**: 2.1.0
