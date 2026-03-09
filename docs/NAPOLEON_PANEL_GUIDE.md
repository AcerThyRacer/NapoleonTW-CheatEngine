# Napoleon Control Panel - User Guide

## 👑 Welcome to Napoleon's Command Panel

The enhanced, fully-animated Napoleon-themed control panel provides an immersive interface for managing all your cheats with stunning visual effects!

## 🎨 Features

### Visual Excellence
- **Napoleon-Era Aesthetic**: Gold-trimmed, imperial-themed interface
- **Animated Buttons**: Smooth hover and click animations
- **Particle Effects**: Celebratory explosions when activating cheats
- **Victory Animations**: Triumphant sequences for major achievements
- **Dynamic Progress Bars**: Animated treasury and morale indicators
- **Battle Map Visualization**: Real-time army movement display

### Full Customization
- **5 Imperial Themes**:
  - Napoleon Gold (Classic)
  - Imperial Blue
  - Royal Purple
  - Battlefield Steel
  - Midnight Command

- **Adjustable Animation Speed**: 1-10 scale
- **Sound Effects Toggle**: Enable/disable audio feedback
- **Customizable Layout**: Rearrange panels

### All Commands Organized

#### 💰 Treasury Category
- **Imperial Treasury** 💰 - Fill coffers with 999,999 gold
- Quick-set amounts: 10k, 50k, 100k, 999k

#### ⚔️ Military Category
- **Instant Recruitment** ⚔️ - Recruit armies immediately
- **Grand March** 🚶 - Unlimited movement points
- **Veteran Armies** 🎖️ - Start with max experience

#### 🏰 Campaign Category
- **Rapid Construction** 🏰 - Buildings complete in 1 turn
- **Enlightenment Era** 📚 - Technologies in 1 turn
- **Imperial Vision** 👁️ - Reveal entire map

#### 🛡️ Battle Category
- **Divine Protection** 🛡️ - God mode for all units
- **Infinite Munitions** 🔫 - Unlimited ammo
- **Grande Armée Spirit** 🎖️ - Maximum morale
- **Devastating Artillery** 💥 - One-hit kills
- **Napoleonic Blitz** ⚡ - Game speed control (1-10x)

#### 🤝 Diplomacy Category
- **Master Spies** 🕵️ - Unlimited agent actions
- **Diplomatic Immunity** 🤝 - No diplomatic penalties

## 🎮 How to Use

### Launching the Control Panel

```bash
# Standard launch
python src/main.py --gui

# Or directly
python src/gui/napoleon_panel.py
```

### Basic Operation

1. **Start Napoleon Total War**
2. **Launch Control Panel**
3. **Navigate Categories**: Click category tabs at top
4. **Activate Cheats**: Toggle switches to ON position
5. **Enjoy**: Cheats activate immediately with visual feedback

### Category Navigation

The panel is organized into 6 sections:

1. **💰 Treasury** - Economic cheats
2. **⚔️ Military** - Army and recruitment
3. **🏰 Campaign** - Campaign-wide modifications
4. **🛡️ Battle** - In-battle advantages
5. **🤝 Diplomacy** - Diplomatic enhancements
6. **⚙️ Settings** - Customization options

## 🎨 Customization

### Changing Themes

1. Go to **⚙️ Settings** tab
2. Select theme from dropdown:
   - **Napoleon Gold**: Classic gold and navy
   - **Imperial Blue**: Blue and silver
   - **Royal Purple**: Purple and gold
   - **Battlefield Steel**: Gray and red
   - **Midnight Command**: Dark and aggressive

Theme changes apply instantly with smooth transitions!

### Animation Settings

- **Animation Speed**: Slider from 1-10
  - Lower = slower, more dramatic
  - Higher = faster, snappier
  
- **Sound Effects**: Toggle on/off
  - Click sounds
  - Activation chimes
  - Victory fanfares

## 🎆 Visual Effects

### Particle System

When you activate certain cheats, particle effects will erupt:
- **Gold particles** for treasury cheats
- **Red particles** for battle cheats
- **Blue particles** for diplomatic cheats
- **Green particles** for military cheats

### Victory Animations

Major achievements trigger victory sequences:
- Activating all cheats in a category
- Setting treasury to maximum
- Winning a battle with god mode enabled

The animation displays:
- "VICTORY!"
- "VIVE L'EMPEREUR!"
- "TRIOMPHE!"
- "GLOIRE!"

### Progress Bars

Animated progress bars show:
- **Imperial Treasury**: Current gold amount
- **Army Morale**: Average unit morale
- **Research Progress**: Current technology
- **Construction Queue**: Buildings in progress

## ⚡ Quick Commands

### Activate All Cheats
One button to rule them all! Found in Settings tab.

### Deactivate All Cheats
Return to vanilla gameplay instantly.

### Preset Configurations
Coming soon: Save and load cheat configurations!

## 🎯 Pro Tips

1. **Use Category Tabs**: Organize cheats by gameplay aspect
2. **Watch for Animations**: Visual feedback confirms activation
3. **Customize Theme**: Match your mood or playstyle
4. **Adjust Animations**: Lower speed for performance, higher for flair
5. **Battle Map**: Visualize army movements in real-time

## 🔧 Troubleshooting

### Panel Won't Launch
```bash
# Ensure PyQt6 is installed
pip install PyQt6

# Check for errors
python src/gui/napoleon_panel.py
```

### Animations Laggy
- Reduce animation speed in Settings
- Disable particle effects (future update)
- Use simpler theme (Battlefield Steel)

### Sounds Not Playing
- Enable "Sound Effects" in Settings
- Check system volume
- Sound files in `sounds/` directory

## 🎵 Sound Effects

Sound system uses standard WAV files:
- `activate.wav` - Cheat activation
- `deactivate.wav` - Cheat deactivation
- `victory.wav` - Victory fanfare
- `click.wav` - Button clicks

Place WAV files in `sounds/` directory or edit paths in code.

## 📊 Statistics Tracking

Future updates will track:
- Cheats activated per session
- Most used cheats
- Victory count with cheats
- Animation triggers

## 🎨 Theme Creation

Create custom themes by editing the theme dictionary in `napoleon_panel.py`:

```python
themes = {
    "my_custom_theme": {
        "primary": "#FF0000",
        "secondary": "#00FF00",
        "background": "#000000",
        "panel": "#333333",
    }
}
```

## 🚀 Performance

The control panel is optimized for:
- **60 FPS** animations
- **Minimal CPU** usage when idle
- **Efficient rendering** with Qt
- **Low memory** footprint (~50MB)

## 🎖️ Achievements

Hidden achievements to discover:
- **Le Petit Caporal**: Activate first cheat
- **Emperor of France**: Activate all cheats
- **Waterloo Reversed**: Win battle with all battle cheats
- **Economy Master**: Reach 1M gold
- **Speed Demon**: Use 10x game speed

## 📞 Support

- **Documentation**: See main README.md
- **Issues**: GitHub Issues
- **Community**: Total War Center forums

---

**Vive l'Empereur! Long live the Emperor!** 👑🦅
