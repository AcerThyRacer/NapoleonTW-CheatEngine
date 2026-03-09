"""
Game state detection for Napoleon Total War.
Monitors process lifecycle and detects campaign vs battle mode.
"""

import logging
import threading
import time
from typing import Optional, Callable, Dict, Any
from enum import Enum

import psutil

from .platform import get_all_possible_process_names
from .events import EventEmitter, EventType

logger = logging.getLogger('napoleon.utils.game_state')


class GameMode(Enum):
    """Current game mode."""
    NOT_RUNNING = 'not_running'
    LOADING = 'loading'
    MAIN_MENU = 'main_menu'
    CAMPAIGN = 'campaign'
    BATTLE = 'battle'
    UNKNOWN = 'unknown'


class GameStateMonitor:
    """
    Monitors Napoleon Total War process and detects game state changes.
    
    Features:
    - Auto-detect when game starts/stops
    - Poll for campaign vs battle mode via memory signatures
    - Emit events on state changes
    - Configurable polling interval
    """
    
    def __init__(self, poll_interval: float = 2.0, memory_scanner=None):
        """
        Initialize game state monitor.
        
        Args:
            poll_interval: How often to check game state (seconds)
        """
        self.memory_scanner = memory_scanner
        self.poll_interval = poll_interval
        self._thread: Optional[threading.Thread] = None
        self._running = False
        self._current_mode = GameMode.NOT_RUNNING
        self._process: Optional[psutil.Process] = None
        self._pid: Optional[int] = None
        self._lock = threading.Lock()
        
        # Callbacks
        self._on_game_started: Optional[Callable[[int], None]] = None
        self._on_game_stopped: Optional[Callable[[], None]] = None
        self._on_mode_changed: Optional[Callable[[GameMode, GameMode], None]] = None
        self._on_state_update: Optional[Callable[[Dict[str, Any]], None]] = None
    
    @property
    def mode(self) -> GameMode:
        """Get current game mode."""
        return self._current_mode
    
    @property
    def pid(self) -> Optional[int]:
        """Get current game PID."""
        return self._pid
    
    @property
    def is_running(self) -> bool:
        """Check if game is running."""
        return self._current_mode != GameMode.NOT_RUNNING
    
    def set_callbacks(
        self,
        on_game_started: Optional[Callable[[int], None]] = None,
        on_game_stopped: Optional[Callable[[], None]] = None,
        on_mode_changed: Optional[Callable[[GameMode, GameMode], None]] = None,
        on_state_update: Optional[Callable[[Dict[str, Any]], None]] = None,
    ) -> None:
        """Set event callbacks."""
        self._on_game_started = on_game_started
        self._on_game_stopped = on_game_stopped
        self._on_mode_changed = on_mode_changed
        self._on_state_update = on_state_update
    
    def start(self) -> None:
        """Start monitoring."""
        if self._running:
            return
        
        self._running = True
        self._thread = threading.Thread(
            target=self._monitor_loop,
            daemon=True,
            name="GameStateMonitor"
        )
        self._thread.start()
        logger.info("Game state monitor started (interval=%.1fs)", self.poll_interval)
    
    def stop(self) -> None:
        """Stop monitoring."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=5.0)
            self._thread = None
        logger.info("Game state monitor stopped")
    
    def _monitor_loop(self) -> None:
        """Main monitoring loop."""
        while self._running:
            try:
                self._check_game_state()
            except Exception as e:
                logger.error("Monitor error: %s", e)
            
            time.sleep(self.poll_interval)
    
    def _check_game_state(self) -> None:
        """Check current game state."""
        process = self._find_game_process()
        
        if process is None:
            # Game not running
            if self._current_mode != GameMode.NOT_RUNNING:
                old_mode = self._current_mode
                self._current_mode = GameMode.NOT_RUNNING
                self._process = None
                self._pid = None
                
                logger.info("Game stopped")

                # Emit event
                EventEmitter().emit(
                    EventType.PROCESS_DETACHED,
                    data={'pid': self._pid},
                    source='game_state_monitor'
                )

                if self._on_game_stopped:
                    self._on_game_stopped()
                if self._on_mode_changed:
                    self._on_mode_changed(old_mode, GameMode.NOT_RUNNING)
        else:
            was_not_running = self._current_mode == GameMode.NOT_RUNNING
            
            if was_not_running:
                self._process = process
                self._pid = process.pid
                logger.info("Game detected: PID %d", self._pid)
                
                # Emit event
                EventEmitter().emit(
                    EventType.PROCESS_ATTACHED,
                    data={'pid': self._pid},
                    source='game_state_monitor'
                )

                if self._on_game_started:
                    self._on_game_started(self._pid)
            
            # Detect game mode
            new_mode = self._detect_mode(process)
            
            if new_mode != self._current_mode:
                old_mode = self._current_mode
                self._current_mode = new_mode
                logger.info("Mode changed: %s -> %s", old_mode.value, new_mode.value)
                
                # Emit event
                EventEmitter().emit(
                    EventType.GAME_STATE_CHANGED,
                    data={'old_mode': old_mode.value, 'new_mode': new_mode.value},
                    source='game_state_monitor'
                )

                if self._on_mode_changed:
                    self._on_mode_changed(old_mode, new_mode)
            
            # Send state update
            if self._on_state_update:
                try:
                    with process.oneshot():
                        state = {
                            'pid': process.pid,
                            'name': process.name(),
                            'mode': self._current_mode.value,
                            'cpu_percent': process.cpu_percent(),
                            'memory_mb': process.memory_info().rss / (1024 * 1024),
                            'status': process.status(),
                        }
                    self._on_state_update(state)
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
    
    def _find_game_process(self) -> Optional[psutil.Process]:
        """Find the Napoleon Total War process."""
        # If we already have a process, verify it's still running
        if self._process:
            try:
                if self._process.is_running():
                    return self._process
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
            self._process = None
        
        # Search for process
        possible_names = get_all_possible_process_names()
        
        for proc in psutil.process_iter(['pid', 'name']):
            try:
                name = proc.info['name']
                if name and name.lower() in [n.lower() for n in possible_names]:
                    return proc
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        
        return None
    
    def _detect_mode(self, process: psutil.Process) -> GameMode:
        """
        Detect if game is in campaign or battle mode.
        
        Uses a multi-strategy approach:
        1. Memory signature detection (if attached)
        2. Window title analysis
        3. Thread count + memory heuristic (fallback)
        """
        # Strategy 1: Memory signature detection
        mode = self._detect_mode_by_memory()
        if mode != GameMode.UNKNOWN:
            return mode

        # Strategy 2: Try window title detection (most reliable on Linux)
        mode = self._detect_mode_by_title(process)
        if mode != GameMode.UNKNOWN:
            return mode
        
        # Strategy 3: Thread count + memory as rough heuristic
        try:
            with process.oneshot():
                cpu = process.cpu_percent()
                mem = process.memory_info()
                threads = process.num_threads()
                status = process.status()
            
            mem_mb = mem.rss / (1024 * 1024)
            
            if status in ('stopped', 'zombie'):
                return GameMode.NOT_RUNNING
            
            if mem_mb < 300:
                return GameMode.LOADING
            
            # Battle mode: higher thread count and CPU, 
            # as the battle engine spawns rendering/AI threads
            if threads > 15 and cpu > 30:
                return GameMode.BATTLE
            elif mem_mb > 400:
                return GameMode.CAMPAIGN
            else:
                return GameMode.UNKNOWN
                
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            return GameMode.UNKNOWN

    def _detect_mode_by_memory(self) -> GameMode:
        """
        Detect game mode by scanning memory for known signatures.
        Returns GameMode.UNKNOWN if detection fails or scanner is not available.
        """
        if getattr(self, 'memory_scanner', None) is None or not self.memory_scanner.is_attached():
            return GameMode.UNKNOWN

        try:
            from src.memory.advanced import PointerResolver, PointerChain

            resolver = PointerResolver(self.memory_scanner.backend, self.memory_scanner.process_manager.pid)

            # Use known campaign chain from napoleon_v1_6.json
            campaign_chain = PointerChain(
                module_name='napoleon.exe',
                base_offset=0x00A1B2C0,
                offsets=[0x4C, 0x10, 0x8],
                description='Campaign Treasury Check',
                value_type='int32'
            )

            # Use known campaign research chain from napoleon_v1_6.json
            research_chain = PointerChain(
                module_name='napoleon.exe',
                base_offset=0x00A3D4E0,
                offsets=[0x28, 0x10, 0xC],
                description='Campaign Research Check',
                value_type='int32'
            )

            val1 = resolver.resolve_and_read(campaign_chain)
            val2 = resolver.resolve_and_read(research_chain)
            if (val1 is not None and val1 >= 0) or (val2 is not None and val2 >= 0):
                return GameMode.CAMPAIGN

            # If we can't resolve campaign pointers, check if we can resolve battle ones.
            # While we don't have exact battle static pointers in the JSON, we can use
            # signature scanning or heuristic fallback. Let's assume if it's attached
            # and NOT campaign, it's either Battle or Main Menu/Loading.
            # We will fallback to window title/heuristic for Battle.

        except Exception as e:
            logger.debug(f"Memory state detection failed: {e}")

        return GameMode.UNKNOWN

    def _detect_mode_by_title(self, process: psutil.Process) -> GameMode:
        """
        Try to detect game mode by examining open file descriptors or 
        cmdline for battle-related map files.
        """
        try:
            cmdline = process.cmdline()
            cmdline_str = ' '.join(cmdline).lower()
            
            if 'battle' in cmdline_str:
                return GameMode.BATTLE
            if 'campaign' in cmdline_str:
                return GameMode.CAMPAIGN
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
        
        # Try open files — battle mode loads map files
        try:
            open_files = process.open_files()
            for f in open_files:
                path_lower = f.path.lower()
                if 'battle' in path_lower or 'terrain' in path_lower:
                    return GameMode.BATTLE
                if 'campaign' in path_lower or 'startpos' in path_lower:
                    return GameMode.CAMPAIGN
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
        
        return GameMode.UNKNOWN
    
    def get_state(self) -> Dict[str, Any]:
        """Get current state snapshot."""
        return {
            'mode': self._current_mode.value,
            'pid': self._pid,
            'is_running': self.is_running,
            'monitoring': self._running,
        }
