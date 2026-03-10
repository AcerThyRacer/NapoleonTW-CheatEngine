#!/bin/bash
# ============================================================================
# Napoleon Total War Trainer - Hotkey Launcher
# Runs in background and activates cheats with F-keys while game is running
# ============================================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$SCRIPT_DIR/.venv"

echo "============================================================================"
echo "Napoleon Total War Trainer - Hotkey Mode"
echo "============================================================================"
echo ""

# Check if virtual environment exists
if [ ! -d "$VENV_DIR" ]; then
    echo "[ERROR] Virtual environment not found!"
    echo "Please run the installation first."
    exit 1
fi

# Activate virtual environment
source "$VENV_DIR/bin/activate"

echo "[INFO] Starting trainer with hotkey support..."
echo ""
echo "The trainer will run in the background and listen for hotkeys."
echo ""
echo "HOTKEYS (Press these WHILE in the game):"
echo "============================================================================"
echo ""
echo "CAMPAIGN MODE (Shift + F-key):"
echo "  Shift+F1  - Toggle God Mode"
echo "  Shift+F2  - Add 10,000 Gold"
echo "  Shift+F3  - Instant Agent Training"
echo "  Shift+F4  - Free Construction"
echo "  Shift+F5  - Max Research Points"
echo "  Shift+F6  - Infinite Action Points"
echo "  Shift+F7  - Free Diplomatic Actions"
echo "  Shift+F8  - Invisible Armies"
echo ""
echo "BATTLE MODE (Ctrl + F-key):"
echo "  Ctrl+F1   - Toggle God Mode"
echo "  Ctrl+F2   - Infinite Ammo"
echo "  Ctrl+F3   - Max Morale"
echo "  Ctrl+F4   - Infinite Stamina"
echo "  Ctrl+F5   - Instant Kill"
echo "  Ctrl+F6   - Speed Hack (2x)"
echo "  Ctrl+F7   - Infinite Unit Health"
echo "  Ctrl+F8   - Range Boost"
echo ""
echo "GENERAL:"
echo "  F9        - Toggle Overlay"
echo "  F10       - Screenshot"
echo "  F11       - Toggle FPS Counter"
echo "  F12       - Reload Cheats"
echo ""
echo "============================================================================"
echo ""
echo "[INFO] Starting trainer..."
echo "[INFO] Launch Napoleon Total War now (or switch to it)"
echo "[INFO] Press Ctrl+C in this terminal to stop the trainer"
echo ""

# Run trainer using the actual trainer module
python3 -m src.trainer
