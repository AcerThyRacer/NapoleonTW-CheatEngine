#!/usr/bin/env python3
"""
Napoleon Total War Cross-Platform Cheat Engine
Main entry point.
"""

import argparse
import logging
import sys

from src.engine_service import EngineService

__version__ = "2.1.0"
logger = logging.getLogger('napoleon.main')


def _service_or_default(service: EngineService | None) -> EngineService:
    """Return the provided service or a default one for direct entry-point use."""
    return service or EngineService()


def build_parser() -> argparse.ArgumentParser:
    """Create the canonical CLI parser for all startup modes."""
    parser = argparse.ArgumentParser(
        description="Napoleon Total War Cheat Engine - Cross-platform cheat suite"
    )
    parser.add_argument('--gui', action='store_true', help='Launch GUI interface (default)')
    parser.add_argument('--cli', action='store_true', help='Launch CLI interface')
    parser.add_argument('--trainer', action='store_true', help='Launch trainer only (hotkey-activated cheats)')
    parser.add_argument('--memory-scanner', action='store_true', help='Launch memory scanner only')
    parser.add_argument('--background', action='store_true', help='Launch background trainer (headless mode with hotkeys)')
    parser.add_argument('--panel', action='store_true', help='Launch Napoleon Control Panel (animated UI)')
    parser.add_argument('--web', action='store_true', help='Launch the web application backend')
    parser.add_argument('--debug', action='store_true', help='Enable debug logging')
    parser.add_argument('--verbose', '-v', action='store_true', help='Enable verbose output')
    parser.add_argument('--ini', type=str, default='napoleon.ini', help='Path to the INI configuration file (default: napoleon.ini)')
    parser.add_argument('--version', action='version', version=f'%(prog)s {__version__}')
    return parser


def _resolve_mode(args: argparse.Namespace) -> str:
    """Resolve the requested startup mode, defaulting to GUI."""
    if args.cli:
        return 'cli'
    if args.trainer:
        return 'trainer'
    if args.memory_scanner:
        return 'memory_scanner'
    if args.background:
        return 'background'
    if args.panel:
        return 'panel'
    if args.web:
        return 'web'
    return 'gui'


def main(argv=None):
    """Main entry point."""
    args = build_parser().parse_args(argv)
    service = EngineService(
        ini_path=args.ini,
        debug=args.debug,
        verbose=args.verbose,
    )

    mode = _resolve_mode(args)

    if mode == 'gui':
        return launch_gui(service)
    if mode == 'cli':
        return launch_cli(service)
    if mode == 'trainer':
        return launch_trainer(service)
    if mode == 'memory_scanner':
        return launch_memory_scanner(service)
    if mode == 'background':
        return launch_background_trainer(service)
    if mode == 'panel':
        return launch_panel(service)
    return launch_web(service)


def launch_gui(service: EngineService | None = None):
    """Launch the GUI application."""
    active_service = _service_or_default(service)

    def _launch(prepared_service: EngineService):
        try:
            from src.gui.napoleon_panel import main as napoleon_main
            print("👑 Launching Napoleon's Command Panel...")
            return napoleon_main(service=prepared_service)
        except ImportError as e:
            print(f"Enhanced GUI not available: {e}")
            print("Falling back to standard GUI...")
            try:
                from src.gui.main_window import main as gui_main
                return gui_main(service=prepared_service)
            except ImportError as e2:
                print(f"Failed to launch GUI: {e2}")
                print("\nPyQt6 is required for the GUI.")
                print("Install with: pip install PyQt6")
                sys.exit(1)

    return active_service.run(_launch, load_plugins=True)


def launch_cli(service: EngineService | None = None):
    """Launch CLI interface."""
    active_service = _service_or_default(service)
    from src.cli.interactive import run_cli
    return active_service.run(run_cli)


def launch_trainer(service: EngineService | None = None):
    """Launch trainer mode."""
    active_service = _service_or_default(service)

    def _launch(_prepared_service: EngineService):
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

            game_monitor = GameStateMonitor(poll_interval=2.0, memory_scanner=scanner)
            game_monitor.start()

            print("\nWaiting for Napoleon Total War process...")
            print("Press Ctrl+C to exit")

            if not scanner.attach():
                print("\nCould not find Napoleon Total War process.")
                print("Please start the game first.")
                sys.exit(1)

            print(f"\n✓ Attached to: {process_manager.process_name} (PID: {process_manager.pid})")

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

    return active_service.run(_launch)


def launch_background_trainer(service: EngineService | None = None):
    """Launch background trainer mode."""
    active_service = _service_or_default(service)

    def _launch(_prepared_service: EngineService):
        print("Napoleon Total War Background Trainer")
        print("=" * 50)
        print("\nStarting in background mode...")
        print("Hotkeys are active. Press Ctrl+F10 to open the GUI.")
        print("Press Ctrl+C to exit\n")

        try:
            from src.trainer.background import BackgroundTrainer

            trainer = BackgroundTrainer()
            trainer.start()

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

    return active_service.run(_launch)


def launch_panel(service: EngineService | None = None):
    """Launch Napoleon Control Panel (animated GUI)."""
    active_service = _service_or_default(service)

    def _launch(prepared_service: EngineService):
        print("Napoleon Total War - Napoleon's Command Panel")
        print("=" * 50)
        print("\n👑 Launching animated control panel...\n")

        try:
            from src.gui.napoleon_panel import main as panel_main
            return panel_main(service=prepared_service)
        except ImportError as e:
            print("Error: Napoleon Control Panel requires PyQt6")
            print("Install with: pip install PyQt6")
            print(f"\nDetails: {e}")
            sys.exit(1)
        except Exception as e:
            print(f"\nError launching panel: {e}")
            import traceback
            traceback.print_exc()
            sys.exit(1)

    return active_service.run(_launch, load_plugins=True)


def launch_memory_scanner(service: EngineService | None = None):
    """Launch memory scanner only."""
    active_service = _service_or_default(service)

    def _launch(_prepared_service: EngineService):
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

    return active_service.run(_launch)


def launch_web(service: EngineService | None = None):
    """Launch the web application backend."""
    active_service = _service_or_default(service)
    from src.server.websocket_server import run_server
    return active_service.run(run_server)


if __name__ == "__main__":
    main()
