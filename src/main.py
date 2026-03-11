#!/usr/bin/env python3
"""
Napoleon Total War Cross-Platform Cheat Engine
Main entry point.
"""

import sys
import argparse
import logging
from pathlib import Path

__version__ = "2.1.0"
logger = logging.getLogger('napoleon.main')
_startup_plugin_manager = None


def _load_startup_plugins():
    """Load startup plugins from the configured plugin directories."""
    global _startup_plugin_manager

    try:
        from src.plugins.manager import PluginManager

        _startup_plugin_manager = PluginManager()
        _startup_plugin_manager.load_all()
    except Exception as e:
        logger.warning("Failed to load startup plugins: %s", e)


def main():
    """Main entry point."""
    import os

    # Start global async error reporter
    from src.utils.error_reporter import AsyncErrorReporter
    reporter = AsyncErrorReporter()
    reporter.start()

    if hasattr(os, 'geteuid') and os.geteuid() == 0:
        print("\n\033[1;31m[SECURITY WARNING]\033[0m")
        print("You are running this tool as root (sudo). This is a severe security risk!")
        print("It is highly recommended to run the tool as a regular user and use:")
        print("  sudo setcap cap_sys_ptrace=eip $(which python3)")
        print("to grant memory access without running the entire application as root.")
        print("If you continue, the tool may create files in your home directory owned by root.\n")

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
        '--background',
        action='store_true',
        help='Launch background trainer (headless mode with hotkeys)'
    )
    
    parser.add_argument(
        '--panel',
        action='store_true',
        help='Launch Napoleon Control Panel (animated UI)'
    )
    
    parser.add_argument(
        '--debug',
        action='store_true',
        help='Enable debug logging'
    )
    
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Enable verbose logging (DEBUG level)'
    )
    
    parser.add_argument(
        '--ini',
        type=str,
        default='napoleon.ini',
        help='Path to configuration INI file (default: napoleon.ini)'
    )
    
    parser.add_argument(
        '--version',
        action='version',
        version=f'%(prog)s {__version__}'
    )
    
    args = parser.parse_args()
    
    # Default to GUI if no option specified
    if not any([args.gui, args.cli, args.trainer, args.memory_scanner, args.background, args.panel]):
        args.gui = True
    
    # Parse INI configuration if it exists
    log_level = logging.DEBUG if (args.debug or args.verbose) else logging.INFO
    ini_path = Path(args.ini)
    
    if ini_path.exists():
        try:
            import configparser
            config = configparser.ConfigParser()
            config.read(ini_path)
            
            if 'logging' in config:
                level_str = config.get('logging', 'level', fallback='INFO')
                if not (args.debug or args.verbose):
                    log_level = getattr(logging, level_str.upper(), logging.INFO)
        except Exception as e:
            logger.debug("Failed to parse INI config: %s", e)
    
    # Initialize logging with project root directory
    from src.utils.logging_config import setup_logging
    setup_logging(level=log_level, log_dir=Path.cwd())
    
    # Initialize async error reporter
    from src.utils.error_reporter import init_error_reporter
    init_error_reporter().start()
    
    if args.gui:
        launch_gui()
    elif args.cli:
        launch_cli()
    elif args.trainer:
        launch_trainer()
    elif args.memory_scanner:
        launch_memory_scanner()
    elif args.background:
        launch_background_trainer()
    elif args.panel:
        launch_panel()


def launch_gui():
    """Launch the GUI application."""
    _load_startup_plugins()

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
        from src.utils.platform import get_hotkey_compatibility_warning
        
        print("\nInitializing trainer...")
        hotkey_warning = get_hotkey_compatibility_warning()
        if hotkey_warning:
            print(f"\n{hotkey_warning}")
        
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


def launch_background_trainer():
    """Launch background trainer mode."""
    print("Napoleon Total War Background Trainer")
    print("=" * 50)
    print("\nStarting in background mode...")
    print("Hotkeys are active. Press Ctrl+F10 to open the GUI.")
    print("Press Ctrl+C to exit\n")
    
    try:
        from src.trainer.background import BackgroundTrainer
        
        trainer = BackgroundTrainer()
        trainer.start()
        
        # Keep running
        import time
        while True:
            time.sleep(1)
            
    except KeyboardInterrupt:
        print("\nBackground trainer stopped by user")
    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


def launch_panel():
    """Launch Napoleon Control Panel (animated GUI)."""
    print("Napoleon Total War - Napoleon's Command Panel")
    print("=" * 50)
    print("\n👑 Launching animated control panel...\n")
    
    try:
        from src.gui.napoleon_panel import main as panel_main
        panel_main()
    except ImportError as e:
        print(f"Error: Napoleon Control Panel requires PyQt6")
        print(f"Install with: pip install PyQt6")
        print(f"\nDetails: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\nError launching panel: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


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
