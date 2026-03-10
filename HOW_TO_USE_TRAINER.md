# 🎮 How to Use the Napoleon Total War Trainer

## ⚡ **QUICK START - READ THIS FIRST!**

The trainer is **NOT** built into the game. It's a **separate program** that you run alongside the game.

### Here's Exactly What To Do:

**Step 1: Open a Terminal**
- Press `Ctrl+Alt+T` or open your terminal emulator

**Step 2: Navigate to the Cheat Engine**
```bash
cd /home/ace/Downloads/NapoleonTWCheat
```

**Step 3: Start the Trainer**
```bash
./launch-trainer.sh
```

**Step 4: Leave the Terminal Open**
- You'll see: `[TRAINER] ✓ Trainer is running!`
- You'll see: `[TRAINER] Waiting for Napoleon Total War to launch...`
- **DO NOT CLOSE THIS TERMINAL** - minimize it or move it to another workspace

**Step 5: Launch Napoleon Total War**
- Start the game through Steam as normal
- The trainer will automatically detect it and say:
  ```
  [TRAINER] ✓ Game detected (PID: 12345)
  [TRAINER] ✓ Memory scanner attached
  [TRAINER] Hotkeys are now ACTIVE!
  ```

**Step 6: Play the Game and Use Hotkeys**
- While in the game, press the hotkeys listed below
- The trainer terminal will show cheat activations

---

## ⌨️ **HOTKEY REFERENCE**

### Campaign Mode (Hold Shift + Press F-key)
*Use on the campaign map*

| Key | Effect |
|-----|--------|
| **Shift+F1** | God Mode |
| **Shift+F2** | +10,000 Gold |
| **Shift+F3** | Instant Agent Training |
| **Shift+F4** | Free Construction |
| **Shift+F5** | Max Research |
| **Shift+F6** | Infinite Action Points |
| **Shift+F7** | Free Diplomatic Actions |
| **Shift+F8** | Invisible Armies |

### Battle Mode (Hold Ctrl + Press F-key)
*Use during battles*

| Key | Effect |
|-----|--------|
| **Ctrl+F1** | God Mode |
| **Ctrl+F2** | Infinite Ammo |
| **Ctrl+F3** | Max Morale |
| **Ctrl+F4** | Infinite Stamina |
| **Ctrl+F5** | Instant Kill |
| **Ctrl+F6** | Speed Hack (2x) |
| **Ctrl+F7** | Infinite Unit Health |
| **Ctrl+F8** | Range Boost |

### General (Press Anytime)

| Key | Effect |
|-----|--------|
| **F9** | Toggle Overlay |
| **F10** | Screenshot |
| **F11** | FPS Counter |
| **F12** | Reload Cheats |

---

## 🛑 **How to Stop the Trainer**

1. Go back to the terminal running the trainer
2. Press **Ctrl+C**
3. It will cleanly shut down

---

## ❓ **TROUBLESHOOTING**

### "I don't see anything when I launch NTW"

**This is normal!** The trainer runs in a **separate terminal window**, not inside the game.

**What you should see:**
- A terminal window with the trainer running
- Messages like "Waiting for Napoleon Total War to launch..."
- When you start the game: "✓ Game detected"

**What you WON'T see:**
- No overlay in the game (unless you press F9)
- No menu in the game
- The game looks completely normal

### "None of the F buttons are working"

**Check these:**

1. **Is the trainer running?**
   - You need a terminal window open with the trainer
   - Run: `./launch-trainer.sh`

2. **Is the game detected?**
   - The trainer should say "✓ Game detected"
   - If not, start the game first

3. **Are you pressing the RIGHT keys?**
   - Campaign: Hold **Shift** then press F1-F8
   - Battle: Hold **Ctrl** then press F1-F8
   - Just pressing F1 alone won't work!

4. **Memory access permissions?**
   If you see permission errors, run this once:
   ```bash
   sudo setcap cap_sys_ptrace=eip $(readlink -f $(which python3))
   ```

### "I want a GUI with buttons instead"

Use the GUI mode instead of the trainer:
```bash
./launch-cheat-engine.sh gui
```

This opens a window with clickable buttons for all cheats.

---

## 📋 **EXAMPLE SESSION**

Here's exactly what to do:

```bash
# 1. Open terminal
# 2. Go to cheat directory
cd /home/ace/Downloads/NapoleonTWCheat

# 3. Start trainer
./launch-trainer.sh

# You'll see:
# ============================================================================
# Napoleon Total War Trainer - Hotkey Mode
# ============================================================================
# [TRAINER] ✓ Trainer is running!
# [TRAINER] Waiting for Napoleon Total War to launch...

# 4. Leave terminal open, start Napoleon TW through Steam

# Trainer will detect it:
# [TRAINER] ✓ Game detected (PID: 12345)
# [TRAINER] Hotkeys are now ACTIVE!

# 5. Play the game, press Shift+F2 for gold!
# 6. Check trainer terminal - it will show cheat activations
```

---

## 🎨 **Alternative: GUI Mode**

If you prefer clicking buttons over hotkeys:

```bash
./launch-cheat-engine.sh gui
```

This opens a full window with:
- ✅ Buttons for all cheats
- ✅ Live memory monitoring
- ✅ Visual effects
- ✅ No hotkeys needed

**Keep this window open while playing!**

---

## ✅ **Checklist - Make Sure:**

- [ ] Terminal is open with trainer running
- [ ] Trainer says "Waiting for Napoleon Total War"
- [ ] Game is launched through Steam
- [ ] Trainer says "Game detected"
- [ ] You're holding Shift or Ctrl when pressing F-keys
- [ ] Memory access is set up (run the setcap command if needed)

---

## 🆘 **Still Not Working?**

1. **Check trainer is running:**
   ```bash
   ps aux | grep trainer
   ```

2. **Check game is detected:**
   - Look at trainer terminal
   - Should say "Game detected"

3. **Try GUI mode instead:**
   ```bash
   ./launch-cheat-engine.sh gui
   ```

4. **Check logs:**
   ```bash
   cat ~/.napoleon-cheat/logs/*.log 2>/dev/null | tail -50
   ```

---

## 📞 **Quick Reference Commands**

```bash
# Start trainer
./launch-trainer.sh

# Start GUI
./launch-cheat-engine.sh gui

# Check if trainer is running
ps aux | grep -i trainer

# Stop all trainers
pkill -f launch-trainer

# Set memory permissions (run once)
sudo setcap cap_sys_ptrace=eip $(readlink -f $(which python3))
```

---

**Remember:** The trainer is a SEPARATE program that runs alongside the game, not inside it! 🎮

Keep the terminal open, start the game, and press the hotkeys!

Happy gaming! ⚔️
