# 🎮 Napoleon Total War Trainer - Hotkey Guide

## ⚡ Quick Start

### Step 1: Launch the Game
Start **Napoleon: Total War** through Steam and load into a campaign or battle.

### Step 2: Launch the Trainer
Open a terminal and run:
```bash
cd /home/ace/Downloads/NapoleonTWCheat
./launch-trainer.sh
```

**Keep this terminal open** - the trainer runs in the background!

### Step 3: Use Hotkeys in Game
While playing, press the hotkeys listed below to activate cheats.

---

## 🎯 How It Works

The trainer is a **separate program** that:
1. Runs in a terminal window (or background)
2. Detects when Napoleon TW is running
3. Listens for your key presses
4. Activates cheats when you press the hotkeys

**Important:** The trainer terminal must stay open while you're playing!

---

## ⌨️ Hotkey Reference

### Campaign Mode (Shift + F-Keys)
*Use these while on the campaign map*

| Hotkey | Effect |
|--------|--------|
| **Shift+F1** | Toggle God Mode |
| **Shift+F2** | Add 10,000 Gold |
| **Shift+F3** | Instant Agent Training |
| **Shift+F4** | Free Construction |
| **Shift+F5** | Max Research Points |
| **Shift+F6** | Infinite Action Points |
| **Shift+F7** | Free Diplomatic Actions |
| **Shift+F8** | Invisible Armies |

### Battle Mode (Ctrl + F-Keys)
*Use these during battles*

| Hotkey | Effect |
|--------|--------|
| **Ctrl+F1** | Toggle God Mode |
| **Ctrl+F2** | Infinite Ammo |
| **Ctrl+F3** | Max Morale |
| **Ctrl+F4** | Infinite Stamina |
| **Ctrl+F5** | Instant Kill |
| **Ctrl+F6** | Speed Hack (2x) |
| **Ctrl+F7** | Infinite Unit Health |
| **Ctrl+F8** | Range Boost |

### General Hotkeys (Any Time)

| Hotkey | Effect |
|--------|--------|
| **F9** | Toggle Overlay |
| **F10** | Screenshot |
| **F11** | Toggle FPS Counter |
| **F12** | Reload Cheats |

---

## 🔧 Troubleshooting

### Hotkeys Not Working?

**Check 1: Is the trainer running?**
- You should see a terminal window with "Trainer is running!" message
- The terminal must stay open while playing

**Check 2: Is the game detected?**
- The trainer will say "✓ Game detected and attached!" when it finds Napoleon TW
- If it says "Waiting for game to launch..." - start the game first

**Check 3: Are you pressing the RIGHT keys?**
- Campaign cheats need **Shift** held down + F-key
- Battle cheats need **Ctrl** held down + F-key
- Make sure you're in the right mode (campaign vs battle)

**Check 4: Memory access permissions**
If you see "Permission denied" errors:
```bash
sudo setcap cap_sys_ptrace=eip $(readlink -f $(which python3))
```

### Wayland Users
If you're on Wayland (not X11), hotkeys may not work due to security restrictions.
Check your session type:
```bash
echo $XDG_SESSION_TYPE
```

If it says "wayland", either:
1. Switch to X11 session at login
2. Use the GUI mode instead: `./launch-cheat-engine.sh gui`

---

## 🎨 Alternative: GUI Mode

If hotkeys are problematic, use the full GUI interface:

```bash
./launch-cheat-engine.sh gui
```

This opens a window with:
- Buttons to activate cheats
- Live memory monitoring
- Visual effects
- All features accessible via mouse clicks

---

## 📋 Example Session

Here's a typical usage session:

```bash
# Terminal 1: Start the trainer
cd /home/ace/Downloads/NapoleonTWCheat
./launch-trainer.sh

# Output you'll see:
# ============================================================================
# Napoleon Total War Trainer - Hotkey Mode
# ============================================================================
# [TRAINER] Starting hotkey listener...
# [TRAINER] ✓ Trainer is running!
# [TRAINER] Waiting for Napoleon Total War to launch...

# Now start the game through Steam...

# [TRAINER] ✓ Game detected and attached!
# [TRAINER] Hotkeys are now active

# Play the game and press Shift+F2 for gold!
```

---

## 🛑 Stopping the Trainer

To stop the trainer:
1. Go to the terminal running it
2. Press **Ctrl+C**
3. It will cleanly shut down

---

## ⚙️ Advanced: Run in Background

To run the trainer in the background (no terminal window):

```bash
./launch-trainer.sh > /tmp/trainer.log 2>&1 &
```

To stop it later:
```bash
pkill -f launch-trainer.sh
```

---

## 📞 Still Having Issues?

1. **Check the trainer is running** - Look for the terminal output
2. **Check game is running** - Trainer must detect Napoleon TW
3. **Check hotkey permissions** - Run the setcap command above
4. **Try GUI mode** - `./launch-cheat-engine.sh gui`
5. **Check logs** - Look at `/tmp/trainer.log` if running in background

---

## ✅ Verification Checklist

Before hotkeys will work, ALL of these must be true:

- [ ] Virtual environment exists (`.venv/` directory)
- [ ] pynput is installed (`pip show pynput`)
- [ ] Trainer is running (terminal shows "Trainer is running!")
- [ ] Game is running (trainer says "Game detected")
- [ ] Memory access granted (setcap command run)
- [ ] Using correct hotkeys (Shift+F-keys for campaign, Ctrl+F-keys for battle)
- [ ] On X11 session (not Wayland)

---

**Quick Test:** Run this to verify everything is ready:

```bash
cd /home/ace/Downloads/NapoleonTWCheat
source .venv/bin/activate
python3 -c "from pynput.keyboard import Key; print('✓ Hotkeys ready!' if Key.f1 else '✗ Not ready')"
```

If it says "✓ Hotkeys ready!" - you're good to go!

---

**Happy Gaming!** ⚔️🎖️
