#!/usr/bin/env python3
"""
Trainer entry point - runs hotkey-based cheat trainer for Napoleon Total War.
Works on both Windows and Linux.
"""

import sys
import time
import signal
import logging
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.trainer.hotkeys import HotkeyManager, CheatHotkeys
from src.memory.cheats import CheatManager, CheatType
from src.memory.scanner import MemoryScanner
from src.memory.process import ProcessManager
# Setup basic logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s [%(name)s] %(message)s'
)
logger = logging.getLogger('napoleon.trainer')

# Global flag for clean shutdown
running = True

def signal_handler(sig, frame):
    """Handle Ctrl+C gracefully."""
    global running
    print("\n\n[TRAINER] Received shutdown signal...")
    running = False

signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

def main():
    """Main trainer loop."""
    global running
    
    print("=" * 70)
    print("Napoleon Total War Trainer - F-Key Cheat Engine")
    print("=" * 70)
    print()
    print("HOTKEYS:")
    print("  CAMPAIGN (Shift+F-keys):")
    print("    Shift+F1  - God Mode")
    print("    Shift+F2  - Infinite Gold")
    print("    Shift+F3  - Unlimited Movement")
    print("    Shift+F4  - Instant Construction")
    print("    Shift+F5  - Fast Research")
    print()
    print("  BATTLE (Ctrl+F-keys):")
    print("    Ctrl+F1   - God Mode")
    print("    Ctrl+F2   - Unlimited Ammo")
    print("    Ctrl+F3   - High Morale")
    print("    Ctrl+F4   - Infinite Stamina")
    print("    Ctrl+F5   - One-Hit Kill")
    print("    Ctrl+F6   - Super Speed")
    print()
    print("=" * 70)
    print()
    
    # Initialize components
    print("[TRAINER] Initializing components...")
    process_manager = ProcessManager()
    memory_scanner = MemoryScanner(process_manager)
    cheat_manager = CheatManager(memory_scanner)
    hotkey_manager = HotkeyManager()
    cheat_hotkeys = CheatHotkeys(hotkey_manager)
    
    # Track attachment state
    attached = False
    game_pid = None
    
    print("[TRAINER] Starting hotkey listener...")
    hotkey_manager.start()
    
    print("[TRAINER] ✓ Trainer is running!")
    print("[TRAINER] Waiting for Napoleon Total War to launch...")
    print("[TRAINER] Launch the game now, then press the F-keys!")
    print()
    
    # Main monitoring loop
    try:
        while running:
            # Try to attach to game if not already attached
            if not attached:
                if process_manager.attach():
                    game_pid = process_manager.pid
                    print(f"\n{'='*70}")
                    print(f"[TRAINER] ✓ Game detected (PID: {game_pid})")
                    
                    # Attach memory scanner
                    if memory_scanner.attach():
                        print("[TRAINER] ✓ Memory scanner attached")
                        
                        # Setup hotkeys NOW that we're attached
                        print("[TRAINER] Setting up F-key hotkeys...")
                        if cheat_hotkeys.setup_default_cheat_hotkeys(cheat_manager):
                            attached = True
                            print("[TRAINER] ✓ Hotkeys configured and ACTIVE!")
                            print("[TRAINER] Press Shift+F-keys (campaign) or Ctrl+F-keys (battle)")
                            print(f"{'='*70}\n")
                        else:
                            print("[TRAINER] ✗ Failed to setup hotkeys")
                            memory_scanner.detach()
                            process_manager.detach()
                    else:
                        print("[TRAINER] ✗ Failed to attach memory scanner")
                        process_manager.detach()
                else:
                    # Wait 2 seconds before checking again
                    time.sleep(2)
            else:
                # Check if game is still running
                if not process_manager.is_attached():
                    print(f"\n{'='*70}")
                    print("[TRAINER] ✗ Game no longer detected")
                    print("[TRAINER] Waiting for game to relaunch...")
                    print(f"{'='*70}\n")
                    
                    # Clean up
                    memory_scanner.detach()
                    process_manager.detach()
                    attached = False
                else:
                    # Game is running, idle
                    time.sleep(0.1)
                    
    except Exception as e:
        print(f"\n[TRAINER] Error: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        # Cleanup
        print("\n[TRAINER] Shutting down...")
        
        hotkey_manager.stop()
        
        if attached:
            memory_scanner.detach()
        
        process_manager.detach()
        
        print("[TRAINER] ✓ Trainer stopped")

if __name__ == '__main__':
    main()
