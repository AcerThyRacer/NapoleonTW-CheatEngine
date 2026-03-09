# Napoleon Total War Cheat Engine - User Guide

## Table of Contents

1. [Introduction](#introduction)
2. [Installation](#installation)
3. [Quick Start](#quick-start)
4. [Features](#features)
5. [Memory Scanner](#memory-scanner)
6. [File Editor](#file-editor)
7. [Trainer](#trainer)
8. [Pack Modder](#pack-modder)
9. [Troubleshooting](#troubleshooting)
10. [FAQ](#faq)

---

## Introduction

The Napoleon Total War Cheat Engine is a comprehensive tool suite for modifying Napoleon Total War. It provides:

- **Memory Scanning**: Real-time memory editing like Cheat Engine
- **Save Game Editing**: Modify .esf save files
- **Script Editing**: Edit Lua scripts for permanent changes
- **Configuration Editing**: Modify game settings
- **Pack File Modding**: Edit .pack archives
- **Runtime Trainer**: Hotkey-activated cheats

**Platform Support**: Windows and Linux (native Feral version + Proton/Wine)

---

## Installation

### Prerequisites

- Python 3.10 or higher
- Napoleon Total War (any version)
- pip (Python package manager)

### Step 1: Clone or Download

```bash
cd NapoleonTWCheat
```

### Step 2: Create Virtual Environment

**Windows:**
```bash
python -m venv venv
venv\Scripts\activate
```

**Linux:**
```bash
python3 -m venv venv
source venv/bin/activate
```

### Step 3: Install Dependencies

```bash
pip install -r requirements.txt
```

### Step 4: Run the Application

```bash
python src/main.py --gui
```

---

## Quick Start

### Method 1: GUI (Recommended for Beginners)

1. Launch: `python src/main.py --gui`
2. Click "Attach to Process" in Memory Scanner tab
3. Start Napoleon Total War
4. Scan for values (e.g., gold amount)
5. Modify values and apply

### Method 2: Trainer (Recommended for Gameplay)

1. Launch: `python src/main.py --trainer`
2. Start Napoleon Total War
3. Use hotkeys in-game:
   - **Shift+F2**: Infinite Gold
   - **Ctrl+F1**: God Mode
   - etc.

### Method 3: File Editing (For Permanent Changes)

1. Navigate to File Editor tab
2. Open save game or script file
3. Make modifications
4. Save and launch game

---

## Features

### Memory Scanner

Scan and modify game memory in real-time.

**Use Cases:**
- Change gold/treasury values
- Modify unit health
- Edit movement points
- Change ammo counts

**How to Use:**
1. Attach to process
2. Enter value to scan (e.g., current gold: 5000)
3. Click "New Scan"
4. Change value in-game (spend some gold)
5. Enter new value (e.g., 4500)
6. Click "Next Scan"
7. Repeat until few addresses remain
8. Double-click to modify value

### File Editor

#### Save Game Editor (.esf files)

Edit saved games directly.

**Location:**
- Windows: `%APPDATA%\The Creative Assembly\Napoleon\save_games\`
- Linux: `~/.local/share/Total War: NAPOLEON/save_games/`

**Steps:**
1. Open File Editor tab → Save Games
2. Load .esf file
3. Navigate tree structure
4. Modify values (treasury, turn number, etc.)
5. Save changes

#### Script Editor (.lua files)

Modify game scripts for permanent changes.

**Example - Infinite Gold:**
```lua
-- In scripting.lua, find:
local function OnFactionTurnStart(context)

-- Add:
if context.faction:name() == "france" then
    treasury = 999999
end
```

**Steps:**
1. Open File Editor tab → Scripts
2. Load `scripting.lua` from `data/campaigns/[campaign]/`
3. Use Quick Edits or manual editing
4. Save and backup

#### Configuration Editor

Modify `preferences.script` for gameplay tweaks.

**Common Settings:**
- `battle_time_limit = -1` (unlimited battle time)
- `campaign_unit_multiplier = 2.5` (larger units)
- `default_camera_type = 2` (free camera)

**Presets:**
- **Enable Cheats**: Activates all cheat settings
- **Performance**: Optimizes for lower-end systems
- **Ultra Graphics**: Maximum visual quality

### Trainer

Hotkey-activated cheats during gameplay.

**Launch:**
```bash
python src/main.py --trainer
```

**Campaign Hotkeys (hold Shift + key):**
- **Shift+F2**: Infinite Gold
- **Shift+F3**: Unlimited Movement
- **Shift+F4**: Instant Construction
- **Shift+F5**: Fast Research

**Battle Hotkeys (hold Ctrl + key):**
- **Ctrl+F1**: God Mode
- **Ctrl+F2**: Unlimited Ammo
- **Ctrl+F3**: High Morale
- **Ctrl+F4**: Infinite Stamina
- **Ctrl+F5**: One-Hit Kill
- **Ctrl+F6**: Super Speed

### Pack Modder

Edit .pack archive files.

**Features:**
- Extract files from .pack archives
- Edit database tables (TSV format)
- Create custom mod packs
- Modify unit stats, buildings, technologies

**Steps:**
1. Open Pack Modder tab
2. Load .pack file (e.g., `data.pack`)
3. Navigate to database table
4. Export to TSV for editing
5. Import modified TSV
6. Save as new .pack or mod

---

## Troubleshooting

### Memory Scanner Returns No Results

**Problem:** Scanning doesn't find any addresses.

**Solutions:**
1. Ensure game is running
2. Run as administrator (Windows)
3. Check process name matches
4. For Proton: Ensure scanning correct process

### Game Crashes After Editing

**Problem:** Game crashes when loading save or starting.

**Solutions:**
1. Always backup saves before editing
2. Don't set values to extreme numbers (use 999999, not 999999999)
3. Verify .esf file wasn't corrupted
4. Restore from backup

### Trainer Hotkeys Don't Work

**Problem:** Hotkeys don't activate cheats.

**Solutions:**
1. Ensure trainer is attached to process
2. Check hotkey listener is running
3. Disable conflicting software (Discord overlay, etc.)
4. Run as administrator

### Save File Won't Load

**Problem:** ESF editor can't open save file.

**Solutions:**
1. Ensure game is closed
2. Check file isn't corrupted
3. Try XML export/import method
4. Use ESFviaXML tool for complex edits

### GUI Won't Start

**Problem:** PyQt6 errors or blank window.

**Solutions:**
```bash
# Reinstall PyQt6
pip uninstall PyQt6
pip install PyQt6

# Or use CLI mode
python src/main.py --cli
```

---

## FAQ

### Is this safe to use?

Yes, for single-player only. Napoleon Total War has no anti-cheat in single-player. **Do not use in multiplayer** as it may cause desync.

### Will I get banned?

No. There is no anti-cheat system for Napoleon Total War. Steam achievements still unlock when using cheats.

### Does this work with the Definitive Edition?

Yes, it works with:
- Original Napoleon Total War
- Definitive Edition
- Feral Interactive Linux version
- Windows version via Proton/Wine

### Can I use this online?

**No.** Using cheats in multiplayer will cause desync errors and ruin the experience for others.

### My antivirus flags the executable

This is a false positive. Game hacking tools are often flagged because they modify memory. You can:
1. Add an exception
2. Build from source yourself
3. Use CLI mode instead

### How do I uninstall?

Simply delete the NapoleonTWCheat folder. No system changes are made.

### Can I create mods with this?

Yes! Use the Pack Modder to create .pack files that can be shared with others.

### Where can I get help?

- Check the [README.md](README.md) for basic info
- Visit [Total War Center forums](https://www.twcenter.net/)
- Check [FearLess Cheat Engine](https://fearlessrevolution.com/) for tables

---

## Advanced Usage

### Creating Custom Cheat Tables

Save scan results for reuse:

```python
from src.memory import ProcessManager, MemoryScanner, ValueType

pm = ProcessManager()
scanner = MemoryScanner(pm)
scanner.attach()

# Scan for gold
scanner.scan_exact_value(5000, ValueType.INT_32)

# Save addresses
addresses = [r.address for r in scanner.get_results()]
print(f"Gold addresses: {addresses}")
```

### Batch Save Editing

Edit multiple saves:

```python
from src.files import ESFEditor
from pathlib import Path

save_dir = Path.home() / '.local/share/Total War: NAPOLEON/save_games'

for save_file in save_dir.glob('*.esf'):
    editor = ESFEditor()
    editor.load_file(str(save_file))
    editor.set_node_value('treasury', 999999)
    editor.save_file()
```

### Automated Mod Building

Script mod creation:

```python
from src.pack import ModCreator

creator = ModCreator()
creator.set_mod_info("My Mod", "Custom modifications")

# Add modified files
creator.add_file_from_disk(
    "modified_scripting.lua",
    "data/campaigns/france/scripting.lua"
)

# Save mod pack
creator.save_pack("my_mod.pack")
```

---

## Credits

- **Total War Center Community**: For modding tools and documentation
- **FearLess Cheat Engine**: For existing cheat tables
- **Creative Assembly**: For creating Napoleon Total War
- **Feral Interactive**: For Linux port

---

## License

This tool is provided as-is for educational purposes. Use responsibly and only in single-player.
