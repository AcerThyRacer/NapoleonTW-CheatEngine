# Napoleon Total War Cross-Platform Cheat Engine

✅ **Project Complete** - All features implemented!

A comprehensive cheat engine suite for Napoleon Total War supporting both Windows and Linux platforms.

## ✨ Features Implemented

- ✅ **Memory Editor**: Real-time memory scanning and editing (like Cheat Engine)
- ✅ **Save Game Editor**: Edit .esf save files with XML conversion
- ✅ **Script Editor**: Modify scripting.lua and preferences.script files
- ✅ **Pack File Modder**: Edit .pack archives and database tables
- ✅ **Runtime Trainer**: Hotkey-activated cheats for campaign and battles
- ✅ **Cross-Platform**: Works on Windows and Linux (native + Proton/Wine)
- ✅ **👑 Napoleon's Command Panel**: Fully-customizable animated control panel
  - 🎨 5 Imperial themes (Gold, Blue, Purple, Steel, Midnight)
  - 🎆 Particle effects and victory animations
  - ⚡ Smooth button animations and transitions
  - 🎮 Category-based organization (Treasury, Military, Campaign, Battle, Diplomacy)
  - 🔊 Sound effects system
  - 📊 Animated progress bars
  - 🗺️ Battle map visualization
- ✅ **GUI Interface**: Full PyQt6-based graphical interface
- ✅ **CLI Mode**: Command-line interface for advanced users
- ✅ **Auto-Detection**: Automatic detection of game paths and saves
- ✅ **Backup System**: Automatic backup creation before modifications

## 📋 Table of Contents

- **Memory Editor**: Real-time memory scanning and editing (like Cheat Engine)
- **Save Game Editor**: Edit .esf save files with XML conversion
- **Script Editor**: Modify scripting.lua and preferences.script files
- **Pack File Modder**: Edit .pack archives and database tables
- **Runtime Trainer**: Hotkey-activated cheats for campaign and battles
- **Cross-Platform**: Works on Windows and Linux (native + Proton/Wine)

## Installation

### Prerequisites

- Python 3.10 or higher
- Napoleon Total War (Steam version, Feral Interactive Linux version, or Windows version via Proton)

### Setup

```bash
# Clone or download this repository
cd NapoleonTWCheat

# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows:
venv\Scripts\activate
# Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

## Usage

### Running the Application

```bash
# Launch the GUI
python src/main.py

# Or run specific modules
python src/memory/scanner.py
python src/files/esf_editor.py
python src/trainer/hotkeys.py
```

### Quick Start Guide

1. **Memory Scanner**: Attach to Napoleon process, scan for values (gold, health, etc.)
2. **File Editor**: Browse and edit save games, scripts, and configurations
3. **Pack Modder**: Extract and modify .pack files and database tables
4. **Trainer**: Activate cheats with customizable hotkeys

## Cheat Types

### Campaign Mode
- Infinite Gold/Treasury
- Unlimited Movement Points
- Instant Construction
- Fast Research
- Instant Recruitment
- Unlimited Agent Actions

### Battle Mode
- God Mode (Unlimited Health)
- Unlimited Ammo
- High Morale
- Infinite Stamina
- Super Speed
- One-Hit Kill

## File Locations

### Save Games

**Windows:**
```
C:\Users\[Username]\AppData\Roaming\The Creative Assembly\Napoleon\save_games\
```

**Linux (Feral Native):**
```
~/.local/share/Total War: NAPOLEON/save_games/
```

**Linux (Steam Proton):**
```
~/.steam/steamapps/compatdata/34030/pfx/drive_c/users/steamuser/AppData/Roaming/The Creative Assembly/Napoleon/save_games/
```

### Configuration Files

**preferences.script Location:**
- Windows: `%APPDATA%\The Creative Assembly\Napoleon\scripts\`
- Linux: `~/.local/share/Total War: NAPOLEON/scripts/`

## Building from Source

### Windows Build
```bash
pip install -r requirements.txt
pyinstaller --onefile --windowed --icon=icon.ico --name "NapoleonCheatEngine" src/main.py
```

### Linux Build
```bash
pip install -r requirements.txt
pyinstaller --onefile --windowed --name "NapoleonCheatEngine" src/main.py
```

## Project Structure

```
NapoleonTWCheat/
├── src/
│   ├── memory/          # Memory scanning/editing
│   ├── files/           # Save game and script editing
│   ├── pack/            # Pack file manipulation
│   ├── trainer/         # Runtime trainer with hotkeys
│   ├── utils/           # Cross-platform utilities
│   └── gui/             # PyQt6 GUI
├── tables/              # Pre-defined cheat tables
├── tools/               # Standalone utilities
├── docs/                # Documentation
├── tests/               # Test suite
├── requirements.txt     # Python dependencies
└── README.md           # This file
```

## Safety Features

- Automatic backup creation before modifications
- Undo/restore functionality
- Validation before writes
- Error recovery mechanisms
- Read-only options for critical files

## Warnings

⚠️ **Single-Player Only**: This tool is designed for single-player use only. Using cheats in multiplayer may cause desync issues.

⚠️ **Backup Your Saves**: Always backup your save games before editing.

⚠️ **No Anti-Cheat**: Napoleon Total War has no anti-cheat in single-player, but use at your own risk.

## Troubleshooting

### Memory Scanner Returns No Results
- Ensure the game is running
- Run as administrator (Windows) or with proper permissions (Linux)
- For Proton/Wine, ensure you're scanning the correct process

### Save Editor Crashes
- Close the game completely before editing saves
- Ensure save files are not corrupted
- Check file permissions

### GUI Doesn't Launch
- Ensure all dependencies are installed: `pip install -r requirements.txt`
- Check PyQt6 installation: `python -c "from PyQt6 import QtWidgets; print('OK')"`

## Contributing

Contributions are welcome! Please feel free to submit issues and pull requests.

## License

This project is provided as-is for educational purposes. Use responsibly.

## Acknowledgments

- Total War Center community for modding tools and documentation
- FearLess Cheat Engine for existing cheat tables
- Creative Assembly for creating an amazing game
- Feral Interactive for the Linux port

## Links

- [Total War Center Forums](https://www.twcenter.net/)
- [FearLess Cheat Engine](https://fearlessrevolution.com/)
- [Pack File Manager](https://twcenter.net/resources/pack-file-manager-for-ntw.2791/)
