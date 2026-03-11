# Napoleon Total War Cheat Engine - Developer Guide

## Architecture Overview

```
src/
├── main.py              # Application entry point
├── memory/              # Memory scanning and editing
│   ├── process.py       # Process detection and attachment
│   ├── scanner.py       # Memory scanner implementation
│   └── cheats.py        # Pre-defined cheat definitions
├── files/               # File editing modules
│   ├── esf_editor.py    # .esf save game parser
│   ├── script_editor.py # Lua script editor
│   └── config_editor.py # Configuration file editor
├── pack/                # Pack file manipulation
│   ├── pack_parser.py   # .pack archive parser
│   ├── database_editor.py # Database table editor
│   └── mod_creator.py   # Mod pack creator
├── trainer/             # Runtime trainer
│   ├── hotkeys.py       # Hotkey management
│   ├── cheats.py        # Trainer cheat system
│   └── overlay.py       # Cheat status overlay
├── gui/                 # PyQt6 GUI
│   ├── main_window.py   # Main application window
│   ├── memory_tab.py    # Memory scanner tab
│   ├── file_editor_tab.py # File editor tab
│   ├── trainer_tab.py   # Trainer tab
│   └── settings_tab.py  # Settings tab
└── utils/               # Utilities
    ├── platform.py      # Cross-platform utilities
    └── __init__.py      # Utility exports
```

## Development Setup

### 1. Clone and Setup

```bash
git clone <repository>
cd NapoleonTWCheat
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows
python -m pip install -e ".[dev,gui,memory]"
```

### 2. Development Dependencies

```bash
python -m pytest --version
```

### 3. Running Tests

```bash
# Run all tests
python -m pytest tests/ -v

# Run specific test class
python -m pytest tests/test_main.py::TestMemoryScanner -v

# Run with coverage
python -m pytest tests/ --cov=src --cov-report=html
```

## Module Documentation

### Memory Module

**Purpose**: Real-time memory scanning and editing.

**Key Classes:**
- `ProcessManager`: Handles process detection and attachment
- `MemoryScanner`: Implements Cheat Engine-like scanning
- `CheatManager`: Manages pre-defined cheats
- `ValueType`: Enum for data types (INT_32, FLOAT, etc.)
- `ScanType`: Enum for scan types (EXACT, INCREASED, etc.)

**Example Usage:**
```python
from src.memory import ProcessManager, MemoryScanner, ValueType

pm = ProcessManager()
scanner = MemoryScanner(pm)

if scanner.attach():
    # Scan for exact value
    count = scanner.scan_exact_value(5000, ValueType.INT_32)
    print(f"Found {count} results")
    
    # Get results
    for result in scanner.get_results():
        print(f"0x{result.address:08X} = {result.value}")
    
    # Modify value
    scanner.write_value(result.address, 999999, ValueType.INT_32)
    
    scanner.detach()
```

### Files Module

**Purpose**: Edit game files (saves, scripts, configs).

#### ESFEditor

Parses and edits .esf save game files.

```python
from src.files import ESFEditor

editor = ESFEditor()
editor.load_file('save.esf')

# Find nodes
nodes = editor.find_nodes('treasury')
for node in nodes:
    print(f"Treasury: {node.value}")

# Modify value
editor.set_node_value('treasury', 999999)
editor.save_file()
```

#### ScriptEditor

Edits Lua script files.

```python
from src.files import ScriptEditor

editor = ScriptEditor()
editor.load_file('scripting.lua')

# Quick edits
editor.modify_faction_treasury('france', 999999)
editor.disable_fog_of_war()

# Manual editing
editor.content = editor.content.replace(
    'treasury = 0',
    'treasury = 999999'
)

editor.save_file()
```

#### ConfigEditor

Edits preferences.script configuration.

```python
from src.files import ConfigEditor

editor = ConfigEditor()
editor.load_file()  # Auto-detects location

# Set values
editor.set_value('battle_time_limit', -1)
editor.set_value('campaign_unit_multiplier', 2.5)

# Apply preset
editor.apply_preset('cheats')
editor.save_file()
```

### Pack Module

**Purpose**: Manipulate .pack archive files.

#### PackParser

Extracts files from .pack archives.

```python
from src.pack import PackParser

parser = PackParser()
parser.load_file('data.pack')

# List files
files = parser.list_files('*.lua')
for f in files:
    print(f)

# Extract file
data = parser.extract_file('data/campaigns/france/scripting.lua')

# Extract all
parser.extract_all('output_dir/')
```

#### DatabaseEditor

Edits database tables.

```python
from src.pack import DatabaseEditor

editor = DatabaseEditor()
editor.load_pack('data.pack')
editor.load_table('db/units_tables.tsv')

# Query table
results = editor.query_table(
    'db/units_tables.tsv',
    filters={'unit_key': 'infantry_test'}
)

# Update row
rows = editor.find_rows('db/units_tables.tsv', 'unit_key', 'infantry_test')
for index, row in rows:
    editor.update_row('db/units_tables.tsv', index, {'hit_points': 999})

# Export
editor.export_table('db/units_tables.tsv', 'modified_units.tsv')
```

#### ModCreator

Creates mod .pack files.

```python
from src.pack import ModCreator

creator = ModCreator()
creator.set_mod_info("My Mod", "Custom changes", "1.0")

# Add files
creator.add_file('data/campaigns/france/scripting.lua', lua_data)
creator.add_file_from_disk('modified.txt', 'data/text.txt')

# Add directory
creator.add_directory('my_mod/data', 'data')

# Save mod pack
creator.save_pack('my_mod.pack')
```

### Trainer Module

**Purpose**: Runtime cheat activation with hotkeys.

#### HotkeyManager

Manages global hotkey listeners.

```python
from src.trainer import HotkeyManager

manager = HotkeyManager()

# Register hotkey
manager.register_hotkey(
    key='f1',
    action=lambda: print("F1 pressed!"),
    description="Test hotkey",
    modifiers=['ctrl']
)

# Start listener
manager.start()

# Stop listener
manager.stop()
```

#### TrainerCheats

High-level cheat management.

```python
from src.memory import CheatManager, CheatType
from src.trainer import TrainerCheats

trainer = TrainerCheats(cheat_manager)

# Toggle cheats
trainer.toggle_cheat(CheatType.INFINITE_GOLD)
trainer.toggle_cheat(CheatType.GOD_MODE)

# Get status
active = trainer.get_active_cheats()
print(f"Active cheats: {active}")

# Deactivate all
trainer.deactivate_all_cheats()
```

## GUI Development

### Adding New Tabs

1. Create tab class in `src/gui/`:

```python
from PyQt6.QtWidgets import QWidget, QVBoxLayout

class MyCustomTab(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout()
        # Add widgets
        self.setLayout(layout)
```

2. Add to main window:

```python
# In main_window.py _create_tabs method
self.my_tab = MyCustomTab()
self.tab_widget.addTab(self.my_tab, "My Tab")
```

### Styling

The GUI uses a dark theme stylesheet in `main_window.py`. Customize by modifying the `_apply_stylesheet` method.

## Testing Guidelines

### Unit Tests

```python
def test_my_function():
    from src.mymodule import my_function
    
    result = my_function(5)
    assert result == 10
```

### Integration Tests

```python
def test_full_workflow():
    from src.memory import ProcessManager, MemoryScanner
    
    pm = ProcessManager()
    scanner = MemoryScanner(pm)
    
    # Test attachment (mock or skip if game not running)
    if scanner.attach():
        try:
            # Test scanning
            count = scanner.scan_exact_value(100, ValueType.INT_32)
            assert count >= 0
        finally:
            scanner.detach()
```

## Building for Release

### Windows

```bash
build.bat
```

Or manually:
```bash
pyinstaller --onefile --windowed --icon=icon.ico --name "NapoleonCheatEngine" src/main.py
```

### Linux

```bash
build.sh
```

Or manually:
```bash
pyinstaller --onefile --windowed --name "NapoleonCheatEngine" src/main.py
```

### Creating AppImage (Linux)

```bash
# After PyInstaller build
linuxdeploy-x86_64.AppImage --appdir AppDir -e dist/NapoleonCheatEngine
linuxdeploy-x86_64.AppImage --appdir AppDir --output appimage
```

## Code Style

### Formatting

Use Black for code formatting:
```bash
black src/ tests/
```

### Type Hints

Add type hints to all functions:
```python
def scan_value(
    self,
    value: int,
    value_type: ValueType = ValueType.INT_32
) -> int:
    """Scan for value in memory."""
    pass
```

### Documentation

Use docstrings for all public functions:
```python
def my_function(param: str) -> bool:
    """
    Brief description.
    
    Args:
        param: Description of parameter
        
    Returns:
        bool: Description of return value
    """
    pass
```

## Debugging

### Enable Debug Logging

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

### Memory Scanner Debugging

```python
# In scanner.py, add debug prints
print(f"Scanning address 0x{address:08X}")
print(f"Read value: {value}")
```

### GUI Debugging

Run without `--windowed` to see console output:
```bash
python src/main.py
```

## Performance Considerations

### Memory Scanning

- Scan in background threads to avoid GUI freezing
- Use efficient search algorithms
- Cache scan results

### File Operations

- Always backup before modifying
- Use atomic writes (write to temp, then rename)
- Validate files before saving

## Security Notes

- Never execute code from game files
- Validate all user inputs
- Don't expose sensitive system information
- Run with minimal required permissions

## Contributing

1. Fork the repository
2. Create feature branch
3. Make changes
4. Write tests
5. Submit pull request

## License

Educational purposes only. Use responsibly in single-player only.
