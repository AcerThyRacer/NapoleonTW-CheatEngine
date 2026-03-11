"""
Engine service boundary for the Napoleon TW Cheat Engine.
Acts as a bridge between the WebSocket/HTTP server and the real memory
cheats engine.
"""

from typing import Any, Dict, List, Optional
from src.memory.cheats import CheatManager, CheatType
from src.trainer.cheats import TrainerCheats

class EngineService:
    """Abstract interface or wrapper for real cheat engine actions."""

    def __init__(self, trainer: Optional[TrainerCheats] = None):
        """
        Initialize the service.
        If trainer is not provided, this acts as a stub (e.g. for tests).
        """
        self.trainer = trainer

    def is_attached(self) -> bool:
        """Check if the cheat engine is actually attached to the game process."""
        if self.trainer and self.trainer.cheat_manager.memory_scanner:
            return self.trainer.cheat_manager.memory_scanner.is_attached()
        return False

    def toggle_cheat(self, cheat_id: str, enabled: bool) -> bool:
        """Toggle a cheat in the engine layer."""
        if not self.is_attached():
            return False

        try:
            cheat_type = CheatType(cheat_id)
        except ValueError:
            return False

        if self.trainer:
            # The trainer expects to toggle by just calling toggle_cheat
            # But we might need to know its current state to ensure we get to `enabled`
            is_active = self.trainer.cheat_manager.is_cheat_active(cheat_type)
            if is_active != enabled:
                return self.trainer.toggle_cheat(cheat_type)
            return True # Already in requested state
        return True # Mock success

    def activate_all(self) -> None:
        """Activate all cheats."""
        if not self.is_attached():
            return

        if self.trainer:
            # We can use trainer.activate_all_campaign_cheats and battle cheats, or just use cheat manager
            manager = self.trainer.cheat_manager
            for cheat in manager.cheat_definitions:
                if not manager.is_cheat_active(cheat.cheat_type):
                    self.trainer.toggle_cheat(cheat.cheat_type)

    def deactivate_all(self) -> None:
        """Deactivate all cheats."""
        if self.trainer:
            self.trainer.deactivate_all_cheats()

    def get_cheat_status(self, cheat_id: str) -> bool:
        """Get the actual active status of a cheat."""
        if self.trainer:
            try:
                cheat_type = CheatType(cheat_id)
                return self.trainer.cheat_manager.is_cheat_active(cheat_type)
            except ValueError:
                return False
        return False

    def get_all_cheat_states(self) -> Dict[str, bool]:
        """Get dictionary mapping cheat IDs to their active status."""
        states = {}
        if self.trainer:
            manager = self.trainer.cheat_manager
            for cheat in manager.cheat_definitions:
                states[cheat.cheat_type.value] = manager.is_cheat_active(cheat.cheat_type)
        return states

    def get_memory_heatmap(self) -> List[Dict[str, Any]]:
        """Mock or fetch actual memory heatmap."""
        return []

    def get_resource_history(self) -> List[Dict[str, Any]]:
        """Mock or fetch actual resource history."""
        return []

    def get_cheat_catalog(self) -> List[Dict[str, Any]]:
        """Return the list of all available cheats."""
        if self.trainer:
            # Reformat to match what UI expects (CheatCommand dict format)
            cheats = []
            for cheat in self.trainer.cheat_manager.cheat_definitions:
                category = "quality" # fallback
                mode = cheat.mode
                if mode == "campaign":
                    category = "campaign"
                elif mode == "battle":
                    category = "battle"
                elif mode == "strategic":
                    category = "diplomacy"

                # Provide a basic mapping for legacy UI fields
                cheats.append({
                    "id": cheat.cheat_type.value,
                    "name": cheat.name,
                    "description": cheat.description,
                    "category": category,
                    "icon": "⚙️",
                    "default_value": cheat.default_value if cheat.default_value is not None else 1,
                    "min_value": 0,
                    "max_value": 999999,
                    "is_toggle": True,
                    "is_slider": False
                })
            return cheats
        return []
