# Napoleon Total War Cheat Engine - Quick Reference

## 🚀 Quick Start

### Launch Commands
```bash
# GUI Mode (Recommended)
python src/main.py --gui

# Trainer Mode (Hotkeys Only)
python src/main.py --trainer

# Memory Scanner Only
python src/main.py --memory-scanner

# CLI Mode
python src/main.py --cli
```

## 🎮 Hotkey Reference

### Campaign Cheats (Hold Shift + Key)
| Hotkey | Cheat | Description |
|--------|-------|-------------|
| Shift+F2 | Infinite Gold | Set treasury to 999,999 |
| Shift+F3 | Unlimited Movement | Never run out of movement points |
| Shift+F4 | Instant Construction | Buildings complete in 1 turn |
| Shift+F5 | Fast Research | Technologies research in 1 turn |

### Battle Cheats (Hold Ctrl + Key)
| Hotkey | Cheat | Description |
|--------|-------|-------------|
| Ctrl+F1 | God Mode | Units have unlimited health |
| Ctrl+F2 | Unlimited Ammo | Never run out of ammunition |
| Ctrl+F3 | High Morale | Maximum morale always |
| Ctrl+F4 | Infinite Stamina | Units never tire |
| Ctrl+F5 | One-Hit Kill | Maximum damage dealt |
| Ctrl+F6 | Super Speed | 5x game speed |

## 📁 File Locations

### Save Games
**Windows:**
```
%APPDATA%\The Creative Assembly\Napoleon\save_games\
```

**Linux (Feral):**
```
~/.local/share/Total War: NAPOLEON/save_games/
```

**Linux (Proton):**
```
~/.steam/steamapps/compatdata/34030/pfx/drive_c/users/steamuser/AppData/Roaming/The Creative Assembly/Napoleon/save_games/
```

### Configuration
**Windows:**
```
%APPDATA%\The Creative Assembly\Napoleon\scripts\preferences.script
```

**Linux:**
```
~/.local/share/Total War: NAPOLEON/scripts/preferences.script
```

### Game Scripts
```
[Napoleon Install]/data/campaigns/[campaign_name]/scripting.lua
```

## 🔍 Memory Scanning Guide

### Step-by-Step: Find Gold Address

1. **Note current gold** (e.g., 5000)
2. **New Scan** → Enter `5000` → Select `4 Bytes` → Scan
3. **Spend gold** in-game (e.g., recruit unit)
4. **Note new gold** (e.g., 4800)
5. **Next Scan** → Enter `4800` → Scan
6. **Repeat** until 1-3 addresses remain
7. **Double-click** value to change to `999999`

### Value Types Reference
| Type | Use For |
|------|---------|
| 4 Bytes | Gold, ammo, counts |
| Float | Health, movement, stamina |
| Double | Precise decimal values |
| String | Names, text |

## ⚙️ Configuration Presets

### Enable Cheats Preset
```lua
battle_time_limit = -1
campaign_unit_multiplier = 2.5
default_camera_type = 2
campaign_fog_of_war = false
```

### Performance Preset
```lua
gfx_detail_level = "low"
gfx_video_memory = 1073741824
resolution_width = 1280
resolution_height = 720
vsync = false
```

### Ultra Graphics Preset
```lua
gfx_detail_level = "ultra"
gfx_video_memory = 8589934592
resolution_width = 3840
resolution_height = 2160
vsync = true
```

## 🛠️ Common Tasks

### Add Infinite Gold to Save
1. Open File Editor → Save Games
2. Load your save (.esf file)
3. Find treasury node
4. Set value to `999999`
5. Save and close

### Edit Campaign Script
1. Open File Editor → Scripts
2. Load `scripting.lua`
3. Click "Set Treasury to 999999"
4. Save file
5. **Backup original first!**

### Create Mod Pack
1. Open Pack Modder
2. Add modified files
3. Click "Create Mod Pack"
4. Save as `.pack` file
5. Place in game directory

## 🐛 Troubleshooting Quick Fixes

| Problem | Solution |
|---------|----------|
| Can't attach to process | Run as administrator / Check game is running |
| No scan results | Try different value type / Verify game not paused |
| Hotkeys don't work | Start hotkey listener / Disable Discord overlay |
| Save won't load | Close game completely / Check file not corrupted |
| GUI won't start | Install PyQt6: `pip install PyQt6` |

## 📞 Getting Help

- **Documentation:** See `docs/` folder
- **Total War Center:** https://www.twcenter.net/
- **FearLess Cheat Engine:** https://fearlessrevolution.com/

## ⚠️ Important Warnings

1. **Single-player only** - Do not use in multiplayer
2. **Backup saves** - Always backup before editing
3. **Start small** - Don't set values to extreme numbers
4. **Test frequently** - Load save after each modification

---

**Version:** 1.0.0  
**Platform:** Windows & Linux  
**Python:** 3.10+ required
