"""
Background trainer mode for Napoleon Total War.
Runs headless with hotkey support and auto-attach/detach capabilities.
"""

import logging
import threading
import time
from typing import Optional, Dict, Any

from src.memory import ProcessManager, MemoryScanner, CheatManager
from src.trainer import HotkeyManager, TrainerCheats
from src.utils.game_state import GameStateMonitor, GameMode
from src.utils.platform import get_hotkey_compatibility_warning

logger = logging.getLogger('napoleon.trainer.background')


class BackgroundTrainer:
    """
    Background trainer that runs headless with auto-attach/detach.
    
    Features:
    - Auto-detect and attach to game process
    - Keep hotkeys active in headless mode
    - Retry on state updates
    - Ctrl+F10 to launch GUI on demand
    """
    
    def __init__(self):
        """Initialize background trainer."""
        self.process_manager: Optional[ProcessManager] = None
        self.scanner: Optional[MemoryScanner] = None
        self.cheat_manager: Optional[CheatManager] = None
        self.hotkey_manager: Optional[HotkeyManager] = None
        self.trainer_cheats: Optional[TrainerCheats] = None
        self.game_monitor: Optional[GameStateMonitor] = None
        
        self._running = False
        self._attached = False
        self._retry_count = 0
        self._max_retries = 5
        self._retry_delay = 2.0
        
        # State tracking
        self._last_game_mode: Optional[GameMode] = None
        self._active_cheats: Dict[str, bool] = {}
        
    def start(self) -> None:
        """Start the background trainer."""
        if self._running:
            return
        
        logger.info("Starting background trainer")
        self._running = True
        
        # Initialize components
        self._init_components()
        
        # Start game monitor
        if self.game_monitor:
            self.game_monitor.set_callbacks(
                on_game_started=self._on_game_started,
                on_game_stopped=self._on_game_stopped,
                on_mode_changed=self._on_mode_changed,
            )
            self.game_monitor.start()
        
        # Start hotkey manager
        if self.hotkey_manager:
            self.hotkey_manager.start()
        
        # Setup default hotkeys
        if self.trainer_cheats and self.cheat_manager:
            self.trainer_cheats.setup_default_cheat_hotkeys(self.cheat_manager)
        
        logger.info("Background trainer started (hotkeys active)")
        
        # Main loop with retry logic
        self._run_main_loop()
    
    def stop(self) -> None:
        """Stop the background trainer."""
        logger.info("Stopping background trainer")
        self._running = False
        
        # Stop hotkey manager
        if self.hotkey_manager:
            self.hotkey_manager.stop()
        
        # Stop game monitor
        if self.game_monitor:
            self.game_monitor.stop()
        
        # Detach scanner
        if self.scanner:
            self.scanner.detach()
        
        logger.info("Background trainer stopped")
    
    def _init_components(self) -> None:
        """Initialize trainer components."""
        try:
            self.process_manager = ProcessManager()
            self.scanner = MemoryScanner(self.process_manager)
            self.cheat_manager = CheatManager(self.scanner)
            self.hotkey_manager = HotkeyManager()
            self.trainer_cheats = TrainerCheats(self.cheat_manager)
            self.game_monitor = GameStateMonitor(poll_interval=2.0, memory_scanner=self.scanner)
            
            # Check for Wayland compatibility
            hotkey_warning = get_hotkey_compatibility_warning()
            if hotkey_warning:
                logger.warning(hotkey_warning)
            
            logger.info("Background trainer components initialized")
            
        except Exception as e:
            logger.error("Failed to initialize components: %s", e)
            raise
    
    def _run_main_loop(self) -> None:
        """Main loop with retry logic."""
        while self._running:
            try:
                time.sleep(1.0)
                
                # Check if we need to retry attachment
                if not self._attached and self.game_monitor and self.game_monitor.is_running:
                    self._try_attach()
                
            except KeyboardInterrupt:
                logger.info("Interrupted by user")
                break
            except Exception as e:
                logger.error("Main loop error: %s", e)
                time.sleep(1.0)
    
    def _try_attach(self) -> bool:
        """Attempt to attach to the game process."""
        if not self.scanner or not self.game_monitor:
            return False
        
        if self._attached:
            return True
        
        try:
            if self.scanner.attach():
                logger.info(
                    "Attached to %s (PID: %d)",
                    self.process_manager.process_name,
                    self.process_manager.pid
                )
                self._attached = True
                self._retry_count = 0
                return True
            else:
                self._retry_count += 1
                logger.debug(
                    "Attach attempt %d/%d failed",
                    self._retry_count,
                    self._max_retries
                )
                
                if self._retry_count >= self._max_retries:
                    logger.warning("Max attach retries reached")
                    self._retry_count = 0
                
                return False
                
        except Exception as e:
            logger.error("Attach failed: %s", e)
            self._retry_count += 1
            return False
    
    def _try_detach(self) -> None:
        """Detach from the game process."""
        if not self.scanner:
            return
        
        if self._attached:
            # Deactivate all cheats before detaching
            if self.cheat_manager:
                self.cheat_manager.deactivate_all_cheats()
            
            self.scanner.detach()
            self._attached = False
            
            logger.info("Detached from game process")
    
    def _on_game_started(self, pid: int) -> None:
        """Callback when game starts."""
        logger.info("Game started (PID: %d)", pid)
        self._retry_count = 0
        self._try_attach()
    
    def _on_game_stopped(self) -> None:
        """Callback when game stops."""
        logger.info("Game stopped")
        self._try_detach()
        self._last_game_mode = None
    
    def _on_mode_changed(self, old_mode: GameMode, new_mode: GameMode) -> None:
        """Callback when game mode changes."""
        logger.info("Game mode changed: %s -> %s", old_mode.value, new_mode.value)
        self._last_game_mode = new_mode
        
        # Re-attach if needed
        if new_mode != GameMode.NOT_RUNNING and not self._attached:
            self._try_attach()
    
    def is_attached(self) -> bool:
        """Check if trainer is attached to game."""
        return self._attached
    
    def get_state(self) -> Dict[str, Any]:
        """Get trainer state."""
        return {
            'running': self._running,
            'attached': self._attached,
            'game_mode': self._last_game_mode.value if self._last_game_mode else None,
            'retry_count': self._retry_count,
            'active_cheats': self._active_cheats,
        }
    
    def open_gui(self) -> bool:
        """
        Open the GUI on demand (e.g., via Ctrl+F10).
        
        Returns:
            bool: True if GUI opened successfully
        """
        if not self._running:
            return False
        
        try:
            # Launch GUI in a new thread
            gui_thread = threading.Thread(
                target=self._launch_gui_thread,
                daemon=True,
                name="BackgroundTrainerGUI"
            )
            gui_thread.start()
            
            logger.info("GUI launch requested")
            return True
            
        except Exception as e:
            logger.error("Failed to launch GUI: %s", e)
            return False
    
    def _launch_gui_thread(self) -> None:
        """Launch GUI in a separate thread."""
        try:
            from src.gui.napoleon_panel import main as napoleon_main
            napoleon_main()
        except ImportError:
            try:
                from src.gui.main_window import main as gui_main
                gui_main()
            except Exception as e:
                logger.error("GUI launch failed: %s", e)
