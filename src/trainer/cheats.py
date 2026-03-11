"""
Trainer cheat implementations for Napoleon Total War.
Provides easy-to-use cheat activation functions.
"""

from typing import TYPE_CHECKING, Dict, Optional, Callable
from dataclasses import dataclass

from src.memory import CheatManager, CheatType
from src.trainer.sync import CheatSyncManager

if TYPE_CHECKING:
    from src.trainer.sync import CheatSyncManager


@dataclass
class CheatStatus:
    """Status of a cheat."""
    name: str
    active: bool
    hotkey: str
    description: str


class TrainerCheats:
    """
    High-level cheat manager for the trainer.
    """
    
    def __init__(
        self,
        cheat_manager: CheatManager,
        sync_manager: Optional['CheatSyncManager'] = None,
    ):
        """
        Initialize trainer cheats.
        
        Args:
            cheat_manager: CheatManager instance
            sync_manager: Optional CheatSyncManager instance
        """
        self.cheat_manager = cheat_manager
        self.sync_manager = sync_manager
        self.cheat_status: Dict[CheatType, CheatStatus] = {}
        self.custom_cheats: Dict[str, Callable] = {}
        self.sync_manager: Optional[CheatSyncManager] = None
        self._syncing_cheats: set = set()
        
        # Initialize status tracking
        self._init_cheat_status()

    def enable_sync(self, port_start: int = 27015, port_end: int = 27025) -> bool:
        """Enable multi-process cheat synchronization."""
        if not self.sync_manager:
            self.sync_manager = CheatSyncManager(port_start=port_start, port_end=port_end)
            self.sync_manager.set_callback(self._on_sync_received)
        return self.sync_manager.start()

    def disable_sync(self) -> None:
        """Disable multi-process cheat synchronization."""
        if self.sync_manager:
            self.sync_manager.stop()
            self.sync_manager = None

    def set_sync_override(self, cheat_type: CheatType, ignore: bool) -> None:
        """Configure per-instance override for a cheat type."""
        if self.sync_manager:
            self.sync_manager.set_override(cheat_type, ignore)

    def _on_sync_received(self, cheat_type: CheatType, is_active: bool) -> None:
        """Handle incoming sync events from other trainer instances."""
        current_active = self.cheat_manager.is_cheat_active(cheat_type)
        if current_active == is_active:
            return

        self._syncing_cheats.add(cheat_type)
        try:
            self.toggle_cheat(cheat_type)
        finally:
            self._syncing_cheats.discard(cheat_type)
    
    def _init_cheat_status(self) -> None:
        """Initialize cheat status tracking."""
        all_cheats = self.cheat_manager.get_all_cheats()
        
        for cheat in all_cheats:
            cheat_type = CheatType(cheat['type'])
            self.cheat_status[cheat_type] = CheatStatus(
                name=cheat['name'],
                active=False,
                hotkey="",
                description=cheat['description']
            )
    
    def toggle_cheat(
        self,
        cheat_type: CheatType,
        address: Optional[int] = None,
        sync_to_peers: bool = True,
    ) -> bool:
        """
        Toggle a cheat on/off.
        
        Args:
            cheat_type: Type of cheat to toggle
            address: Optional memory address
            sync_to_peers: Whether to broadcast to other instances
            
        Returns:
            bool: True if toggled successfully
        """
        success = self.cheat_manager.toggle_cheat(cheat_type, address)
        
        if success:
            # Update status
            if cheat_type in self.cheat_status:
                is_active = self.cheat_manager.is_cheat_active(cheat_type)
                
                # Sync to peers if enabled
                if sync_to_peers and self.sync_manager:
                    self.sync_manager.broadcast_cheat_toggle(
                        cheat_type.value,
                        is_active
                    )
                self.cheat_status[cheat_type].active = is_active
                
                action = "activated" if is_active else "deactivated"
                print(f"{self.cheat_status[cheat_type].name} {action}")

                # Broadcast to other instances if sync is enabled
                if self.sync_manager and cheat_type not in self._syncing_cheats:
                    if not self.sync_manager.is_overridden(cheat_type):
                        self.sync_manager.broadcast_toggle(cheat_type, is_active)
        
        return success
    
    def activate_all_campaign_cheats(self) -> None:
        """Activate all campaign mode cheats."""
        campaign_cheats = [
            CheatType.INFINITE_GOLD,
            CheatType.UNLIMITED_MOVEMENT,
            CheatType.INSTANT_CONSTRUCTION,
            CheatType.FAST_RESEARCH,
        ]
        
        for cheat_type in campaign_cheats:
            self.toggle_cheat(cheat_type)
    
    def activate_all_battle_cheats(self) -> None:
        """Activate all battle mode cheats."""
        battle_cheats = [
            CheatType.GOD_MODE,
            CheatType.UNLIMITED_AMMO,
            CheatType.HIGH_MORALE,
            CheatType.INFINITE_STAMINA,
        ]
        
        for cheat_type in battle_cheats:
            self.toggle_cheat(cheat_type)
    
    def deactivate_all_cheats(self) -> None:
        """Deactivate all active cheats."""
        self.cheat_manager.deactivate_all_cheats()
        
        # Update status
        for cheat_type in self.cheat_status:
            self.cheat_status[cheat_type].active = False
        
        print("All cheats deactivated")
    
    def get_active_cheats(self) -> list:
        """
        Get list of currently active cheats.
        
        Returns:
            list: List of active cheat names
        """
        return [
            status.name
            for status in self.cheat_status.values()
            if status.active
        ]
    
    def get_cheat_status(self, cheat_type: CheatType) -> Optional[CheatStatus]:
        """
        Get status of a specific cheat.
        
        Args:
            cheat_type: Type of cheat
            
        Returns:
            Optional[CheatStatus]: Cheat status or None
        """
        return self.cheat_status.get(cheat_type)
    
    def get_all_cheat_statuses(self) -> Dict[str, bool]:
        """
        Get status of all cheats.
        
        Returns:
            Dict[str, bool]: Dictionary of cheat name -> active status
        """
        return {
            status.name: status.active
            for status in self.cheat_status.values()
        }
    
    def register_custom_cheat(
        self,
        name: str,
        callback: Callable,
        description: str = ""
    ) -> None:
        """
        Register a custom cheat function.
        
        Args:
            name: Cheat name
            callback: Function to call when cheat activated
            description: Cheat description
        """
        self.custom_cheats[name] = callback
        print(f"Registered custom cheat: {name}")
    
    def execute_custom_cheat(self, name: str) -> bool:
        """
        Execute a custom cheat.
        
        Args:
            name: Cheat name
            
        Returns:
            bool: True if executed
        """
        if name in self.custom_cheats:
            try:
                self.custom_cheats[name]()
                return True
            except Exception as e:
                print(f"Custom cheat '{name}' failed: {e}")
                return False
        return False
    
    def get_summary(self) -> str:
        """
        Get summary of all cheats and their status.
        
        Returns:
            str: Summary string
        """
        lines = ["Cheat Status:", "=" * 40]
        
        for status in self.cheat_status.values():
            status_str = "✓ ACTIVE" if status.active else "✗ inactive"
            lines.append(f"{status.name:30} {status_str}")
        
        if self.custom_cheats:
            lines.append("\nCustom Cheats:")
            for name in self.custom_cheats.keys():
                lines.append(f"  - {name}")
        
        return '\n'.join(lines)
