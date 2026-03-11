import json
import logging
from pathlib import Path
from typing import Dict, Any, List

logger = logging.getLogger('napoleon.utils.crash_recovery')

class CrashRecoveryManager:
    """Manages crash recovery and session persistence for cheats."""
    def __init__(self, save_path: str = "cheat_session_state.json"):
        self.save_path = Path(save_path)

    def save_state(self, active_cheats: Dict[str, Any], game_version: str) -> bool:
        """Saves the current active cheat state to disk, merging with history."""
        try:
            # Load existing history to preserve it
            history = {}
            if self.save_path.exists():
                with open(self.save_path, "r") as f:
                    history = json.load(f)

            # Ensure version entry exists
            if game_version not in history:
                history[game_version] = {"cheats": {}}

            version_state = history[game_version]["cheats"]

            count = 0
            for cheat_type_val, cheat_info in active_cheats.items():
                if isinstance(cheat_info, dict):
                    cheat_def = cheat_info.get("definition")
                    address = cheat_info.get("address")
                    is_hook = cheat_info.get("is_hook", False)
                    pattern_name = cheat_info.get("pattern_name")
                else:
                    cheat_def = getattr(cheat_info, "definition", None)
                    address = getattr(cheat_info, "address", None)
                    is_hook = getattr(cheat_info, "is_hook", False)
                    pattern_name = getattr(cheat_info, "pattern_name", None)

                if not cheat_def:
                    continue

                # Update or add the cheat to the history
                version_state[cheat_type_val] = {
                    "cheat_type": cheat_type_val,
                    "address": address, # Address is saved but should not be relied upon across sessions due to ASLR
                    "is_hook": is_hook,
                    "pattern_name": pattern_name,
                    "last_active": True # Mark it as active during the crash
                }
                count += 1

            # Mark other cheats as inactive
            for cheat_type_val in version_state.keys():
                if cheat_type_val not in active_cheats:
                     version_state[cheat_type_val]["last_active"] = False

            with open(self.save_path, "w") as f:
                json.dump(history, f, indent=4)
            logger.info(f"Saved {count} active cheats to {self.save_path} for version {game_version}")
            return True
        except Exception as e:
            logger.error(f"Failed to save cheat state: {e}")
            return False

    def load_state(self, current_game_version: str) -> List[Dict[str, Any]]:
        """Loads the saved cheat state from disk for the specific game version."""
        if not self.save_path.exists():
            return []

        try:
            with open(self.save_path, "r") as f:
                history = json.load(f)

            if current_game_version not in history:
                logger.info(f"No history found for game version {current_game_version}")
                return []

            version_state = history[current_game_version]["cheats"]

            # Only return cheats that were active during the last save
            cheats = [cheat_data for cheat_data in version_state.values() if cheat_data.get("last_active", False)]

            logger.info(f"Loaded {len(cheats)} active cheats from {self.save_path} for version {current_game_version}")
            return cheats
        except Exception as e:
            logger.error(f"Failed to load cheat state: {e}")
            return []

    def get_preferred_resolution_method(self, current_game_version: str, cheat_type: str) -> Dict[str, Any]:
        """Gets the previously successful resolution method for a cheat from history."""
        if not self.save_path.exists():
            return {}

        try:
            with open(self.save_path, "r") as f:
                history = json.load(f)

            if current_game_version not in history:
                return {}

            version_state = history[current_game_version]["cheats"]
            return version_state.get(cheat_type, {})
        except Exception as e:
            logger.error(f"Failed to load preferred method: {e}")
            return {}

    def clear_state(self) -> bool:
        """Clears the saved state from disk."""
        try:
            if self.save_path.exists():
                self.save_path.unlink()
                logger.info("Cleared saved cheat state.")
            return True
        except Exception as e:
            logger.error(f"Failed to clear cheat state: {e}")
            return False
