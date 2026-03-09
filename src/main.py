#!/usr/bin/env python3
"""
Napoleon Total War Cross-Platform Cheat Engine
Main entry point.
"""

import sys
import argparse
from pathlib import Path

__version__ = "2.1.0"


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Napoleon Total War Cheat Engine - Cross-platform cheat suite"
    )
    
    parser.add_argument(
        '--gui',
        action='store_true',
        help='Launch GUI interface (default)'
    )
    
    parser.add_argument(
        '--cli',
        action='store_true',
        help='Launch CLI interface'
    )
    
    parser.add_argument(
        '--trainer',
        action='store_true',
        help='Launch trainer only (hotkey-activated cheats)'
    )
    
    parser.add_argument(
        '--memory-scanner',
        action='store_true',
        help='Launch memory scanner only'
    )
    
    parser.add_argument(
        '--version',
        action='version',
        version=f'%(prog)s {__version__}'
    )
    
    args = parser.parse_args()
    
    # Default to GUI if no option specified
    if not any([args.gui, args.cli, args.trainer, args.memory_scanner]):
        args.gui = True
    
    if args.gui:
        launch_gui()
    elif args.cli:
        launch_cli()
    elif args.trainer:
        launch_trainer()
    elif args.memory_scanner:
        launch_memory_scanner()


def launch_gui():
    """Launch the GUI application."""
    try:
        # Try Napoleon Control Panel first (enhanced GUI)
        from src.gui.napoleon_panel import main as napoleon_main
        print("👑 Launching Napoleon's Command Panel...")
        napoleon_main()
    except ImportError as e:
        print(f"Enhanced GUI not available: {e}")
        print("Falling back to standard GUI...")
        try:
            from src.gui.main_window import main as gui_main
            gui_main()
        except ImportError as e2:
            print(f"Failed to launch GUI: {e2}")
            print("\nPyQt6 is required for the GUI.")
            print("Install with: pip install PyQt6")
            sys.exit(1)


def launch_cli():
    """Launch CLI interface."""
    from src.cli import InteractiveCLI
    from src.cli.interactive import main as cli_main
    cli_main()


def launch_trainer():
    """Launch trainer mode."""
    print("Napoleon Total War Trainer")
    print("=" * 50)
    
    hotkey_manager = None
    scanner = None
    try:
        from src.memory import ProcessManager, MemoryScanner, CheatManager
        from src.trainer import HotkeyManager, TrainerCheats
        from src.utils.game_state import GameStateMonitor
        
        print("\nInitializing trainer...")
        
        process_manager = ProcessManager()
        scanner = MemoryScanner(process_manager)
        cheat_manager = CheatManager(scanner)
        hotkey_manager = HotkeyManager()
        trainer_cheats = TrainerCheats(cheat_manager)
        
        # Initialize and start game state monitor
        game_monitor = GameStateMonitor(poll_interval=2.0, memory_scanner=scanner)
        game_monitor.start()

        print("\nWaiting for Napoleon Total War process...")
        print("Press Ctrl+C to exit")
        
        # Try to attach
        if not scanner.attach():
            print("\nCould not find Napoleon Total War process.")
            print("Please start the game first.")
            sys.exit(1)
        
        print(f"\n✓ Attached to: {process_manager.process_name} (PID: {process_manager.pid})")
        
        # Setup hotkeys
        hotkey_manager.start()
        trainer_cheats.setup_default_cheat_hotkeys(cheat_manager)
        
        print("\n✓ Hotkey listener started")
        print("\nAvailable Hotkeys:")
        print("-" * 50)
        print("Campaign (hold Shift + key):")
        print("  Shift+F2 - Infinite Gold")
        print("  Shift+F3 - Unlimited Movement")
        print("  Shift+F4 - Instant Construction")
        print("  Shift+F5 - Fast Research")
        print("\nBattle (hold Ctrl + key):")
        print("  Ctrl+F1 - God Mode")
        print("  Ctrl+F2 - Unlimited Ammo")
        print("  Ctrl+F3 - High Morale")
        print("  Ctrl+F4 - Infinite Stamina")
        print("  Ctrl+F5 - One-Hit Kill")
        print("  Ctrl+F6 - Super Speed")
        print("-" * 50)
        print("\nTrainer is now active. Switch to the game and use hotkeys!")
        
        # Keep running
        import time
        while True:
            time.sleep(1)
            
    except KeyboardInterrupt:
        print("\n\nTrainer stopped by user")
    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        if hotkey_manager:
            hotkey_manager.stop()
        if scanner:
            scanner.detach()


def launch_memory_scanner():
    """Launch memory scanner only."""
    print("Napoleon Total War Memory Scanner")
    print("=" * 50)
    
    try:
        from src.memory import ProcessManager, MemoryScanner, ValueType
        
        process_manager = ProcessManager()
        scanner = MemoryScanner(process_manager)
        
        print("\n1. Start Napoleon Total War")
        print("2. Press Enter to attach to process")
        input()
        
        if not scanner.attach():
            print("Failed to attach to process. Is the game running?")
            return
        
        print(f"\n✓ Attached to: {process_manager.process_name}")
        
        while True:
            print("\n--- Memory Scanner ---")
            print("1. Scan for exact value")
            print("2. Scan for increased value")
            print("3. Scan for decreased value")
            print("4. Clear results")
            print("5. Show results")
            print("6. Write value to address")
            print("7. Detach and exit")
            
            choice = input("\nChoose option: ").strip()
            
            if choice == '1':
                value = input("Enter value: ").strip()
                value_type = ValueType.INT_32
                count = scanner.scan_exact_value(int(value), value_type)
                print(f"Found {count} results")
                
            elif choice == '2':
                count = scanner.scan_increased_value()
                print(f"Found {count} results")
                
            elif choice == '3':
                count = scanner.scan_decreased_value()
                print(f"Found {count} results")
                
            elif choice == '4':
                scanner.clear_results()
                print("Results cleared")
                
            elif choice == '5':
                results = scanner.get_results()
                print(f"\nResults ({len(results)} found):")
                for i, result in enumerate(results[:20]):  # Show first 20
                    print(f"  {i+1}. 0x{result.address:08X} = {result.value} ({result.value_type.value})")
                if len(results) > 20:
                    print(f"  ... and {len(results) - 20} more")
                    
            elif choice == '6':
                addr = input("Enter address (0x...): ").strip()
                value = input("Enter value: ").strip()
                
                try:
                    address = int(addr, 16)
                    scanner.write_value(address, int(value))
                    print(f"✓ Wrote {value} to 0x{address:08X}")
                except ValueError as e:
                    print(f"Invalid input: {e}")
                    
            elif choice == '7':
                scanner.detach()
                print("Detached")
                break
            
            else:
                print("Invalid option")
        
    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
