"""
Background trainer service that auto-attaches to the game and keeps hotkeys active.
Designed to run headless and work on both Windows and Linux.
"""

from __future__ import annotations

import logging
import os
import subprocess
import sys
from pathlib import Path
from typing import Callable, Optional

from src.memory import CheatManager, MemoryScanner, ProcessManager
from src.trainer.hotkeys import HotkeyManager
from src.trainer.cheats import TrainerCheats
from src.utils.game_state import GameStateMonitor

logger = logging.getLogger("napoleon.trainer.background")


class BackgroundTrainer:
    """Headless trainer that follows the game lifecycle and keeps hotkeys running."""

    def __init__(
        self,
        *,
        poll_interval: float = 2.0,
        process_manager: Optional[ProcessManager] = None,
        memory_scanner: Optional[MemoryScanner] = None,
        cheat_manager: Optional[CheatManager] = None,
        hotkey_manager: Optional[HotkeyManager] = None,
        cheat_hotkeys: Optional[TrainerCheats] = None,
        game_monitor: Optional[GameStateMonitor] = None,
        gui_launcher: Optional[Callable[[], None]] = None,
    ):
        self.process_manager = process_manager or ProcessManager()
        self.memory_scanner = memory_scanner or MemoryScanner(self.process_manager)
        self.cheat_manager = cheat_manager or CheatManager(self.memory_scanner)
        self.hotkey_manager = hotkey_manager or HotkeyManager()
        self.cheat_hotkeys = cheat_hotkeys or TrainerCheats(self.cheat_manager)
        self.monitor = game_monitor or GameStateMonitor(
            poll_interval=poll_interval, memory_scanner=self.memory_scanner
        )

        self.monitor.set_callbacks(
            on_game_started=self._on_game_started,
            on_game_stopped=self._on_game_stopped,
            on_state_update=self._on_state_update,
        )

        self._hotkeys_registered = False
        self._attached = False
        self._gui_launcher: Callable[[], None] = gui_launcher or self._launch_gui

    def start(self) -> bool:
        """Start monitoring and hotkeys."""
        self._register_hotkeys()

        if not self.hotkey_manager.is_listening():
            if not self.hotkey_manager.start():
                logger.warning("Hotkey listener failed to start in background mode")

        self.monitor.start()
        logger.info("Background trainer started (poll=%.1fs)", self.monitor.poll_interval)
        return True

    def stop(self) -> None:
        """Stop monitoring and detach from the game."""
        self.monitor.stop()
        self._detach_from_game()
        self.hotkey_manager.stop()
        logger.info("Background trainer stopped")

    def _register_hotkeys(self) -> None:
        """Register default cheat hotkeys and the GUI launcher."""
        if self._hotkeys_registered:
            return

        self.cheat_hotkeys.setup_default_cheat_hotkeys(self.cheat_manager)
        self.hotkey_manager.register_hotkey(
            key="f10",
            modifiers=["ctrl"],
            action=self._gui_launcher,
            description="Launch GUI control panel",
        )
        self._hotkeys_registered = True
        logger.info("Background trainer hotkeys registered (includes Ctrl+F10 GUI toggle)")

    def _on_game_started(self, pid: int) -> None:
        """Attempt to attach when the game starts."""
        if self.memory_scanner.is_attached():
            return

        if self.memory_scanner.attach():
            self._attached = True
            logger.info("Attached to game process (PID %s) in background mode", pid)
        else:
            logger.warning("Detected game PID %s but could not attach; will retry", pid)

    def _on_state_update(self, state: Optional[dict] = None) -> None:
        """Re-attempt attachment while the game is running."""
        if state and not self.memory_scanner.is_attached() and state.get("pid"):
            self._on_game_started(state["pid"])

    def _on_game_stopped(self) -> None:
        """Detach and clear cheats when the game stops."""
        self._detach_from_game()

    def _detach_from_game(self) -> None:
        """Detach from the game process and clean up cheats."""
        if not self.memory_scanner.is_attached() and not self._attached:
            return

        try:
            self.cheat_manager.deactivate_all_cheats()
        except Exception as exc:  # pragma: no cover - best-effort cleanup
            logger.debug("Error deactivating cheats during detach: %s", exc)

        self.memory_scanner.detach()
        self._attached = False
        logger.info("Detached from game process in background mode")

    def _launch_gui(self) -> None:
        """Launch the GUI in a separate process via hotkey."""
        main_path = Path(__file__).resolve().parents[1] / "main.py"
        cmd = [sys.executable, str(main_path), "--gui"]

        popen_kwargs = {"stdout": subprocess.DEVNULL, "stderr": subprocess.DEVNULL}
        if os.name == "nt":
            popen_kwargs["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.DETACHED_PROCESS
        else:
            popen_kwargs["start_new_session"] = True

        try:
            subprocess.Popen(cmd, **popen_kwargs)
            logger.info("Launched GUI from background hotkey")
        except Exception as exc:  # pragma: no cover - platform dependent
            logger.error("Failed to launch GUI: %s", exc)
