# 🚀 Quick Start - Napoleon's Command Panel

## ⚡ 30-Second Setup

### Step 1: Install Dependencies (10 seconds)
```bash
cd /home/ace/Downloads/NapoleonTWCheat
pip install PyQt6
```

### Step 2: Launch Panel (5 seconds)
```bash
python launch_panel.py --panel
```

### Step 3: Activate Cheats! (15 seconds)
1. Start Napoleon Total War
2. Click category tabs to browse cheats
3. Toggle cheats ON
4. Enjoy! 🎉

---

## 🎮 Full Installation Guide

### Prerequisites
- Python 3.10 or higher
- Napoleon Total War (any version)
- pip (Python package manager)

### Installation Steps

#### 1. Navigate to Project
```bash
cd /home/ace/Downloads/NapoleonTWCheat
```

#### 2. Create Virtual Environment (Recommended)
```bash
# Linux
python3 -m venv venv
source venv/bin/activate

# Windows
python -m venv venv
venv\Scripts\activate
```

#### 3. Install Dependencies
```bash
pip install PyQt6 pynput psutil PyMemoryEditor
```

#### 4. Test Installation
```bash
python launch_panel.py --test
```

Expected output:
```
🧪 Testing Components...
✓ Control Panel imported
✓ Animated Components imported
✓ Cheat Command created: Test Command
✅ All tests completed!
```

---

## 🎨 Launch Options

### Option 1: Napoleon Control Panel (Recommended)
```bash
python launch_panel.py --panel
```
**Features:**
- 👑 Beautiful Napoleon-themed interface
- 🎆 Particle effects and animations
- 🎮 All cheats organized by category
- ⚙️ Fully customizable themes

### Option 2: Animation Demo
```bash
python launch_panel.py --demo
```
**Shows:**
- Particle system demo
- Victory animations
- Progress bar animations
- All visual effects

### Option 3: Standard GUI
```bash
python src/main.py --gui
```
**Features:**
- Traditional tabbed interface
- Memory scanner
- File editors
- All original features

### Option 4: Trainer Only
```bash
python src/main.py --trainer
```
**Features:**
- Hotkey-activated cheats
- Minimal interface
- Background operation

---

## 🎯 First Time Usage

### 1. Launch Control Panel
```bash
python launch_panel.py --panel
```

### 2. You'll See:
- **Header**: "NAPOLEON'S COMMAND PANEL" with eagle 🦅 and crown 👑
- **Category Tabs**: Treasury, Military, Campaign, Battle, Diplomacy, Settings
- **Cheat Cards**: Organized toggles with icons and descriptions

### 3. Navigate Categories:
- **💰 Treasury**: Economic cheats
- **⚔️ Military**: Army enhancements
- **🏰 Campaign**: Campaign modifications
- **🛡️ Battle**: Combat advantages
- **🤝 Diplomacy**: Diplomatic bonuses
- **⚙️ Settings**: Customization

### 4. Activate Your First Cheat:
1. Click **💰 Treasury** tab
2. Find **"Imperial Treasury"** card
3. Click toggle to **ON** (green)
4. See gold particle explosion! 🎆
5. Check status bar: "✓ Activated: Imperial Treasury"

### 5. Start Game:
1. Launch Napoleon Total War
2. Load your save or start new campaign
3. Enjoy infinite gold! 💰

---

## 🎨 Customization Guide

### Change Theme
1. Go to **⚙️ Settings** tab
2. Select theme from dropdown:
   - **Napoleon Gold** (Classic)
   - **Imperial Blue**
   - **Royal Purple**
   - **Battlefield Steel**
   - **Midnight Command**
3. Theme changes instantly!

### Adjust Animations
1. Go to **⚙️ Settings** tab
2. Use **Animation Speed** slider:
   - Left (1): Slow, dramatic
   - Right (10): Fast, snappy
3. Toggle **Sound Effects** on/off

### Quick Commands
In **⚙️ Settings** tab:
- **Activate All Cheats**: Enable everything
- **Deactivate All Cheats**: Return to vanilla

---

## 🎮 Cheat Quick Reference

### Most Popular Cheats

#### 💰 Infinite Gold
**Location**: Treasury Tab  
**Effect**: Treasury = 999,999  
**Animation**: Gold particle burst  
**Hotkey**: None (panel only)

#### ⚔️ Instant Recruitment
**Location**: Military Tab  
**Effect**: Recruit armies immediately  
**Animation**: Green particles  
**Hotkey**: None

#### 🏰 Rapid Construction
**Location**: Campaign Tab  
**Effect**: Buildings complete in 1 turn  
**Animation**: Blue particles  
**Hotkey**: None

#### 🛡️ God Mode
**Location**: Battle Tab  
**Effect**: Units invincible  
**Animation**: Red particle burst  
**Hotkey**: None

#### ⚡ Super Speed
**Location**: Battle Tab  
**Effect**: Game speed 1-10x  
**Control**: Slider  
**Animation**: Speed lines

---

## 🔧 Troubleshooting

### Panel Won't Start
```bash
# Check Python version
python3 --version  # Should be 3.10+

# Reinstall PyQt6
pip uninstall PyQt6
pip install PyQt6

# Try direct launch
python src/gui/napoleon_panel.py
```

### Black Screen / No Display
```bash
# Check for errors
python launch_panel.py --panel 2>&1

# Try software rendering
export LIBGL_ALWAYS_SOFTWARE=1
python launch_panel.py --panel
```

### Animations Laggy
1. Go to Settings
2. Reduce Animation Speed to 3-4
3. Use simpler theme (Battlefield Steel)
4. Close other applications

### Sounds Not Working
1. Check Settings → Enable Sound Effects
2. Verify system volume
3. Check sound files exist in `sounds/` folder

### Game Crashes After Cheat
1. **Always backup saves!**
2. Don't set extreme values (>999999)
3. Activate one cheat at a time
4. Test in battle first

---

## 🎆 Animation Showcase

### See All Effects
```bash
python launch_panel.py --demo
```

**Demo includes:**
- Particle explosions (all colors)
- Victory animation sequence
- Progress bar animations
- Button hover effects

### Trigger Effects Manually
In Python console:
```python
from src.gui.animated_components import *

# Create particle explosion
particles = ParticleSystem()
particles.emit_particles(400, 300, 100, QColor(212, 175, 55))

# Play victory
victory = VictoryAnimation()
victory.play()
```

---

## 📊 Performance Tips

### For Best Performance:
1. **Reduce Animation Speed**: Settings → Speed 5 or lower
2. **Use Simple Theme**: Battlefield Steel (least effects)
3. **Disable Particles**: Future update will add toggle
4. **Close Background Apps**: Free up RAM

### Recommended Specs:
- **CPU**: Dual-core 2.0 GHz+
- **RAM**: 4GB+ (panel uses ~50MB)
- **GPU**: Any with OpenGL 2.0+
- **Python**: 3.10+

---

## 🎯 Pro Tips

### Tip 1: Category Workflow
Organize your cheating by phase:
1. **Early Game**: Treasury + Rapid Construction
2. **Mid Game**: Military + Enlightenment
3. **Late Game**: Battle + Diplomacy

### Tip 2: Save Configurations
Screenshot your favorite cheat combinations in Settings for quick reference!

### Tip 3: Test Battles
Always test battle cheats in custom battles before campaign use.

### Tip 4: Backup Saves
Panel creates backups, but manual backups are safer:
```bash
cp -r ~/.local/share/Total War: NAPOLEON/save_games/ ~/backups/
```

### Tip 5: Theme Matching
Match theme to your faction:
- **France**: Napoleon Gold
- **Britain**: Imperial Blue
- **Russia**: Battlefield Steel
- **Spain**: Midnight Command
- **Austria**: Royal Purple

---

## 📞 Getting Help

### Documentation
- **Main README**: Installation and overview
- **USER_GUIDE.md**: Comprehensive usage
- **NAPOLEON_PANEL_GUIDE.md**: Panel-specific guide
- **ANIMATION_SHOWCASE.md**: All animations explained

### Community
- **Total War Center**: https://www.twcenter.net/
- **FearLess Cheat Engine**: https://fearlessrevolution.com/

### Report Issues
- GitHub Issues (if hosted)
- Community forums
- Discord servers

---

## 🎉 You're Ready!

You now have access to:
- ✅ Stunning Napoleon-themed interface
- ✅ All cheat categories organized
- ✅ Beautiful animations and effects
- ✅ Full customization options
- ✅ Sound effects system
- ✅ Battle map visualization

**Launch with:**
```bash
python launch_panel.py --panel
```

**Vive l'Empereur! Long live the Emperor!** 👑🦅🎆

---

## Quick Command Reference

| Command | Description |
|---------|-------------|
| `python launch_panel.py --panel` | Launch control panel |
| `python launch_panel.py --demo` | Animation demo |
| `python launch_panel.py --test` | Test components |
| `python src/main.py --trainer` | Hotkey trainer |
| `python src/main.py --gui` | Standard GUI |

**Happy Gaming!** 🎮⚔️🏰
