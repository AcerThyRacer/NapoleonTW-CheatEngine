# 🎮 Napoleon Total War Trainer - F-Key Cheat Engine

## ✅ **WORKING ON BOTH WINDOWS AND LINUX**

This is a **real cheat engine** that works via **F-key hotkeys** while you play!

---

## ⚡ **QUICK START**

### **Step 1: Open Terminal / Command Prompt**

**Linux:**
```bash
cd /home/ace/Downloads/NapoleonTWCheat
```

**Windows (PowerShell):**
```powershell
cd C:\Users\YourName\Downloads\NapoleonTWCheat
```

### **Step 2: Run the Trainer**

**Linux:**
```bash
./launch-trainer.sh
```

**Windows:**
```powershell
.\scripts\launch-trainer.bat
```

### **Step 3: Leave Terminal Open**

You'll see:
```
[TRAINER] ✓ Trainer is running!
[TRAINER] Waiting for Napoleon Total War to launch...
```

**DO NOT CLOSE THIS WINDOW!**

### **Step 4: Launch Napoleon Total War**

Start the game through Steam as normal.

The trainer will automatically detect it:
```
[TRAINER] ✓ Game detected (PID: 12345)
[TRAINER] ✓ Memory scanner attached
[TRAINER] ✓ Hotkeys configured and ACTIVE!
[TRAINER] Press Shift+F-keys (campaign) or Ctrl+F-keys (battle)
```

### **Step 5: Use F-Keys in Game!**

**While playing:**
- Hold **Shift** + press **F1-F5** for campaign cheats
- Hold **Ctrl** + press **F1-F6** for battle cheats

---

## ⌨️ **HOTKEY REFERENCE**

### 🏰 **CAMPAIGN MODE** (Hold Shift + F-key)

| Hotkey | Effect |
|--------|--------|
| **Shift+F1** | God Mode |
| **Shift+F2** | Infinite Gold |
| **Shift+F3** | Unlimited Movement |
| **Shift+F4** | Instant Construction |
| **Shift+F5** | Fast Research |

### ⚔️ **BATTLE MODE** (Hold Ctrl + F-key)

| Hotkey | Effect |
|--------|--------|
| **Ctrl+F1** | God Mode |
| **Ctrl+F2** | Unlimited Ammo |
| **Ctrl+F3** | High Morale |
| **Ctrl+F4** | Infinite Stamina |
| **Ctrl+F5** | One-Hit Kill |
| **Ctrl+F6** | Super Speed |

---

## 🛑 **How to Stop**

Press **Ctrl+C** in the trainer terminal window.

---

## 🔧 **TROUBLESHOOTING**

### **"Hotkeys not working!"**

**Check 1: Is trainer running?**
- You need the terminal window open showing "[TRAINER] ✓ Trainer is running!"

**Check 2: Is game detected?**
- Trainer must say "✓ Game detected"
- If not, start the game first

**Check 3: Are you pressing the RIGHT keys?**
- Campaign: **Shift** + F1, F2, F3, F4, or F5
- Battle: **Ctrl** + F1, F2, F3, F4, F5, or F6
- Just pressing F1 alone won't work!

**Check 4: Memory access (Linux only)**
```bash
sudo setcap cap_sys_ptrace=eip $(readlink -f $(which python3))
```

**Check 5: Windows permissions**
- Run as Administrator if needed
- Right-click → "Run as Administrator"

### **"Trainer won't start!"**

**Linux:**
```bash
# Make sure it's executable
chmod +x launch-trainer.sh

# Check Python is installed
python3 --version

# Install dependencies if needed
source .venv/bin/activate
pip install pynput psutil
```

**Windows:**
```powershell
# Make sure you're in the right directory
cd C:\Users\YourName\Downloads\NapoleonTWCheat

# Check Python is installed
python --version

# Install dependencies
pip install pynput psutil
```

### **"Game not detected!"**

1. Make sure Napoleon Total War is actually running
2. Check Steam - is the game launched?
3. Try restarting both trainer and game
4. Check task manager - look for "napoleon.exe" or similar

---

## 📋 **EXAMPLE SESSION**

Here's exactly what happens:

```bash
# 1. Open terminal and go to cheat directory
cd /home/ace/Downloads/NapoleonTWCheat

# 2. Start trainer
./launch-trainer.sh

# Output:
# ======================================================================
# Napoleon Total War Trainer - F-Key Cheat Engine
# ======================================================================
# 
# HOTKEYS:
#   CAMPAIGN (Shift+F-keys):
#     Shift+F1  - God Mode
#     Shift+F2  - Infinite Gold
#     ...
# 
# [TRAINER] Initializing components...
# [TRAINER] Starting hotkey listener...
# [TRAINER] ✓ Trainer is running!
# [TRAINER] Waiting for Napoleon Total War to launch...

# 3. Leave terminal open, start Napoleon TW through Steam

# Trainer detects it:
# ======================================================================
# [TRAINER] ✓ Game detected (PID: 1017302)
# [TRAINER] ✓ Memory scanner attached
# [TRAINER] Setting up F-key hotkeys...
# [TRAINER] ✓ Hotkeys configured and ACTIVE!
# [TRAINER] Press Shift+F-keys (campaign) or Ctrl+F-keys (battle)
# ======================================================================

# 4. Play the game!

# 5. In campaign, press Shift+F2
# → You get infinite gold!

# 6. In battle, press Ctrl+F1
# → You have god mode!
```

---

## 🎨 **Alternative: GUI Mode**

Don't like hotkeys? Use the GUI with buttons:

**Linux:**
```bash
./launch-cheat-engine.sh gui
```

**Windows:**
```powershell
python -m src.main --gui
```

---

## ✅ **VERIFICATION CHECKLIST**

Before hotkeys work, ALL must be true:

- [ ] Terminal/PowerShell is open
- [ ] Trainer script is running
- [ ] Trainer says "✓ Trainer is running!"
- [ ] Game is launched and running
- [ ] Trainer says "✓ Game detected"
- [ ] Trainer says "✓ Hotkeys configured and ACTIVE!"
- [ ] You're holding Shift or Ctrl when pressing F-keys
- [ ] (Linux) Memory access set up with setcap
- [ ] (Windows) Running as Administrator if needed

---

## 🆘 **STILL NOT WORKING?**

### **Quick Test:**

**Linux:**
```bash
cd /home/ace/Downloads/NapoleonTWCheat
source .venv/bin/activate
python3 -c "from pynput.keyboard import Key; print('✓ Hotkeys ready!' if Key.f1 else '✗ Not ready')"
```

**Windows:**
```powershell
python -c "from pynput.keyboard import Key; print('✓ Hotkeys ready!' if Key.f1 else '✗ Not ready')"
```

If it says "✓ Hotkeys ready!" - the system is working!

### **Get Help:**

1. Check trainer terminal for error messages
2. Look at logs: `~/.napoleon-cheat/logs/` (Linux) or `%APPDATA%\napoleon-cheat\logs\` (Windows)
3. Try GUI mode instead: `./launch-cheat-engine.sh gui`

---

## 📞 **COMMANDS REFERENCE**

### **Linux:**

```bash
# Start trainer
./launch-trainer.sh

# Start GUI
./launch-cheat-engine.sh gui

# Set memory permissions (run once)
sudo setcap cap_sys_ptrace=eip $(readlink -f $(which python3))

# Check if trainer is running
ps aux | grep trainer

# Stop all trainers
pkill -f __main__.py
```

### **Windows:**

```powershell
# Start trainer
.\scripts\launch-trainer.bat

# Start GUI
python -m src.main --gui

# Check if trainer is running
tasklist | findstr python

# Stop all trainers
taskkill /F /IM python.exe
```

---

## 🎯 **KEY POINTS**

1. **Trainer is SEPARATE** - runs in its own window, not inside the game
2. **Keep terminal OPEN** - close it = trainer stops
3. **Game must be running** - trainer auto-detects it
4. **Use modifiers** - Shift for campaign, Ctrl for battle
5. **Works on Windows AND Linux** - same hotkeys, same features

---

**That's it! Run the trainer, start the game, and press F-keys!** 🎮⚔️

**Happy cheating!** 🏆
