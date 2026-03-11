# 🚀 Quick Start Guide - Web-Based UI

## Get Started in 3 Steps

### Step 1: Install Dependencies

```bash
# Navigate to the project
cd /home/ace/Downloads/NapoleonTWCheat

# Install the Python dev environment
pip install -e ".[dev,gui,memory]"

# Install Node.js dependencies
cd frontend
npm install
```

### Step 2: Start the Application

**Option A: Development Mode (Recommended for testing)**

```bash
# Terminal 1: Start WebSocket server
cd /home/ace/Downloads/NapoleonTWCheat
python -m src.server.websocket_server

# Terminal 2: Start React frontend
cd frontend
npm run dev
```

Then open your browser to: `http://localhost:3000`

**Option B: Tauri Desktop App (Best experience)**

```bash
cd frontend
npm run tauri dev
```

This launches a native desktop window with the UI.

### Step 3: Launch Your Game

1. Start Napoleon Total War through Steam
2. The cheat engine will auto-detect the game
3. Use the UI to activate cheats!

---

## 🎮 Using the UI

### Main Interface

The UI is organized into sections:

1. **Header** - Live stats (FPS, memory, game status)
2. **Category Navigation** - 6 cheat categories (icons)
3. **Cheat Panel** - Toggle switches and sliders
4. **Search Bar** - Find cheats quickly
5. **Settings** - Themes, presets, configuration

### Cheat Categories

Click the icons to switch categories:

- **💰 Treasury** - Infinite gold, resources
- **⚔️ Military** - Army buffs, combat bonuses
- **🏰 Campaign** - Construction, research, agents
- **🛡️ Battle** - God mode, ammo, morale
- **🤝 Diplomacy** - Relations, alliances
- **⚙️ Quality of Life** - Settings, utilities

### Activating Cheats

1. **Toggle Cheats:** Click the switch to enable/disable
2. **Slider Cheats:** Drag to adjust value (gold, points, etc.)
3. **Search:** Type to filter cheats by name
4. **Presets:** Click a preset to apply multiple cheats at once

### Live Monitoring

Watch the real-time stats:
- **Green** = Active
- **Gray** = Inactive
- **Memory graph** = Current memory usage
- **FPS counter** = Game performance

---

## ⚙️ Configuration

### Change Theme

1. Click the **Settings** icon (⚙️)
2. Choose from imperial themes:
   - Napoleon Gold (default)
   - Imperial Purple
   - Battle Gray
   - Royal Blue

### Manage Presets

**Save a Preset:**
1. Configure your cheats
2. Go to Presets tab
3. Click "Save Current Configuration"
4. Name your preset

**Load a Preset:**
1. Go to Presets tab
2. Click on a preset card
3. All cheats apply automatically

**Built-in Presets:**
- Balanced Command
- Grand Battery
- Winter Campaign
- Lightning Assault

### Keyboard Shortcuts

- `Ctrl+F` - Focus search bar
- `Esc` - Close panels
- `F9` - Toggle overlay (in-game)
- `F12` - Reload cheats

---

## 🛠️ Troubleshooting

### "Cannot connect to WebSocket"

**Solution:**
```bash
# Make sure the WebSocket server is running
python -m src.server.websocket_server

# Should see: "WebSocket server started on ws://localhost:8765"
```

### "Game not detected"

**Solutions:**
1. Make sure Napoleon Total War is running
2. Check Steam is launched
3. Verify game installation path
4. Try restarting both the game and cheat engine

### "Permission denied" (Linux)

**Solution:**
```bash
# Grant memory access permissions
sudo setcap cap_sys_ptrace=eip $(readlink -f $(which python3))
```

### UI Not Loading

**Solution:**
```bash
# Clear cache and rebuild
cd frontend
rm -rf node_modules dist
npm install
npm run build
```

### WebSocket Disconnects

**Solution:**
1. Check the WebSocket server terminal for errors
2. Restart the WebSocket server
3. Refresh the browser page
4. Check firewall isn't blocking port 8765

---

## 📊 Performance Tips

### For Best Performance

1. **Use Tauri desktop app** instead of browser
2. **Close browser dev tools** (they increase memory usage)
3. **Reduce overlay animations** in Settings
4. **Disable live graphs** if experiencing lag

### Memory Usage

Normal memory usage:
- **Idle:** ~50MB
- **Active:** ~100-150MB
- **With 3D battle map:** ~200-300MB

If memory usage exceeds 500MB, try:
1. Refreshing the UI
2. Restarting the WebSocket server
3. Disabling the 3D battle map

---

## 🎓 Advanced Features

### Memory Scanner

Access advanced memory scanning:
1. Open Settings panel
2. Enable "Developer Mode"
3. New "Memory Scanner" tab appears
4. Search for values, scan pointers, etc.

### Custom Overlays

Create custom in-game overlays:
1. Go to Settings → Overlay
2. Click "Create Custom Overlay"
3. Position elements with drag-and-drop
4. Save as preset

### Stream Integration

For content creators:
1. Enable "Stream Mode" in Settings
2. Configures OBS-compatible overlays
3. Hides sensitive information
4. Adds viewer interaction features

---

## 📝 Example Sessions

### Quick Gold Cheat

```bash
# 1. Start the UI
npm run tauri dev

# 2. Wait for "Game detected" message

# 3. Click Treasury category (💰)

# 4. Toggle "Imperial Treasury" ON

# 5. Set value to 999999

# 6. Check your in-game gold!
```

### Battle God Mode

```bash
# 1. Start a battle in Napoleon TW

# 2. Open cheat engine UI

# 3. Click Battle category (🛡️)

# 4. Enable:
#    - God Mode (Ctrl+F1)
#    - Infinite Ammo (Ctrl+F2)
#    - Max Morale (Ctrl+F3)

# 5. Watch your units dominate!
```

### Speed Run Preset

```bash
# 1. Open Presets tab

# 2. Click "Lightning Assault"

# 3. This applies:
#    - Speed Boost 2x
#    - Infinite Action Points
#    - Instant Construction
#    - Fast Research

# 4. Start your speed run!
```

---

## 🆘 Getting Help

### Check Logs

```bash
# View recent logs
tail -f ~/.napoleon-cheat/logs/*.log

# Or on Windows
Get-Content $env:APPDATA/napoleon-cheat/logs/*.log -Tail 50 -Wait
```

### Run Diagnostics

```bash
# Test WebSocket connection
python -c "import asyncio; from src.server.websocket_server import main; asyncio.run(main())"

# Test frontend build
cd frontend
npm run build
npm run preview
```

### Community Support

- **Total War Center:** https://www.twcenter.net/
- **Reddit r/totalwar:** https://reddit.com/r/totalwar
- **Discord:** Check project README for invite link

---

## ✅ Verification Checklist

Before playing, verify:

- [ ] WebSocket server running (check terminal)
- [ ] Frontend loaded (see UI in browser/app)
- [ ] Game detected (green indicator in header)
- [ ] At least one cheat category visible
- [ ] No error messages in console
- [ ] Memory graph showing activity

---

## 🎉 You're Ready!

The modern web-based UI is now your command center for dominating Napoleon Total War!

**Quick commands:**

```bash
# Start development mode
npm run tauri dev

# Start production build
npm run tauri build

# Run tests
npm test
```

**Have fun conquering Europe! ⚔️👑**

---

**Last Updated:** 2026-03-10  
**Version:** 2.2.0 (Web UI Edition)
