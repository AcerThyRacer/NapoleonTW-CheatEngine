"""
WebSocket + HTTP server for the Napoleon TW Cheat Engine web UI.

Bridges all cheat / memory / configuration functionality from the
Python backend to a React / Tauri frontend over WebSocket and REST.
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from dataclasses import asdict, dataclass
from enum import Enum
from typing import Any, Dict, List, Optional, Set

logger = logging.getLogger("napoleon.server")

# ---------------------------------------------------------------------------
# Domain types (mirror napoleon_panel.py)
# ---------------------------------------------------------------------------


class CheatCategory(str, Enum):
    """Cheat categories – matches the PyQt panel."""

    TREASURY = "treasury"
    MILITARY = "military"
    CAMPAIGN = "campaign"
    BATTLE = "battle"
    DIPLOMACY = "diplomacy"
    QUALITY_OF_LIFE = "quality"


CATEGORY_META: Dict[str, Dict[str, str]] = {
    CheatCategory.TREASURY: {
        "icon": "treasury.svg",
        "emoji": "\U0001f4b0",
        "tooltip": "Treasury \u2014 Imperial finances",
    },
    CheatCategory.MILITARY: {
        "icon": "sword.svg",
        "emoji": "\u2694\ufe0f",
        "tooltip": "Military \u2014 Army commands",
    },
    CheatCategory.CAMPAIGN: {
        "icon": "campaign.svg",
        "emoji": "\U0001f3f0",
        "tooltip": "Campaign \u2014 Strategic options",
    },
    CheatCategory.BATTLE: {
        "icon": "shield.svg",
        "emoji": "\U0001f6e1\ufe0f",
        "tooltip": "Battle \u2014 Combat modifiers",
    },
    CheatCategory.DIPLOMACY: {
        "icon": "diplomacy.svg",
        "emoji": "\U0001f91d",
        "tooltip": "Diplomacy \u2014 Relations",
    },
    CheatCategory.QUALITY_OF_LIFE: {
        "icon": "quality.svg",
        "emoji": "\u2699\ufe0f",
        "tooltip": "Quality of Life",
    },
}


@dataclass
class CheatCommand:
    """Serialisable cheat descriptor."""

    id: str
    name: str
    description: str
    category: str
    icon: str
    default_value: int = 1
    min_value: int = 0
    max_value: int = 999999
    is_toggle: bool = True
    is_slider: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# All cheat commands – canonical list identical to napoleon_panel.py
CHEAT_COMMANDS: List[CheatCommand] = [
    CheatCommand(
        id="infinite_gold",
        name="Imperial Treasury",
        description="Fill the imperial coffers with unlimited gold",
        category=CheatCategory.TREASURY,
        icon="\U0001f4b0",
        default_value=999999,
    ),
    CheatCommand(
        id="instant_recruitment",
        name="Instant Recruitment",
        description="Recruit armies instantly across the empire",
        category=CheatCategory.MILITARY,
        icon="\u2694\ufe0f",
    ),
    CheatCommand(
        id="instant_construction",
        name="Rapid Construction",
        description="Complete buildings in one turn",
        category=CheatCategory.CAMPAIGN,
        icon="\U0001f3f0",
    ),
    CheatCommand(
        id="fast_research",
        name="Enlightenment Era",
        description="Complete technologies in one turn",
        category=CheatCategory.CAMPAIGN,
        icon="\U0001f4da",
    ),
    CheatCommand(
        id="unlimited_movement",
        name="Grand March",
        description="Armies never tire, unlimited movement",
        category=CheatCategory.MILITARY,
        icon="\U0001f6b6",
    ),
    CheatCommand(
        id="god_mode",
        name="Divine Protection",
        description="Your armies are invincible in battle",
        category=CheatCategory.BATTLE,
        icon="\U0001f6e1\ufe0f",
    ),
    CheatCommand(
        id="unlimited_ammo",
        name="Infinite Munitions",
        description="Never run out of ammunition",
        category=CheatCategory.BATTLE,
        icon="\U0001f52b",
    ),
    CheatCommand(
        id="high_morale",
        name="Grande Arm\u00e9e Spirit",
        description="Maximum morale for all units",
        category=CheatCategory.BATTLE,
        icon="\U0001f396\ufe0f",
    ),
    CheatCommand(
        id="one_hit_kill",
        name="Devastating Artillery",
        description="All attacks deal maximum damage",
        category=CheatCategory.BATTLE,
        icon="\U0001f4a5",
    ),
    CheatCommand(
        id="super_speed",
        name="Napoleonic Blitz",
        description="Accelerate time on the battlefield",
        category=CheatCategory.BATTLE,
        icon="\u26a1",
        is_slider=True,
        min_value=1,
        max_value=10,
        default_value=5,
    ),
    CheatCommand(
        id="max_agents",
        name="Master Spies",
        description="Unlimited agent action points",
        category=CheatCategory.DIPLOMACY,
        icon="\U0001f575\ufe0f",
    ),
    CheatCommand(
        id="free_diplomacy",
        name="Diplomatic Immunity",
        description="No penalties for diplomatic actions",
        category=CheatCategory.DIPLOMACY,
        icon="\U0001f91d",
    ),
]

# Theme definitions – mirrors napoleon_panel.py _apply_theme
THEMES: Dict[str, Dict[str, str]] = {
    "napoleon_gold": {
        "primary": "#d4af37",
        "secondary": "#f1c40f",
        "background": "#1a252f",
        "panel": "#2c3e50",
    },
    "imperial_blue": {
        "primary": "#3498db",
        "secondary": "#2980b9",
        "background": "#1a252f",
        "panel": "#2c3e50",
    },
    "royal_purple": {
        "primary": "#9b59b6",
        "secondary": "#8e44ad",
        "background": "#1a252f",
        "panel": "#2c3e50",
    },
    "battlefield_steel": {
        "primary": "#95a5a6",
        "secondary": "#7f8c8d",
        "background": "#1a252f",
        "panel": "#2c3e50",
    },
    "midnight_command": {
        "primary": "#e74c3c",
        "secondary": "#c0392b",
        "background": "#0f1419",
        "panel": "#1a252f",
    },
}


# ---------------------------------------------------------------------------
# Server state
# ---------------------------------------------------------------------------


class ServerState:
    """Mutable runtime state shared across WebSocket clients."""

    def __init__(self) -> None:
        self.cheat_states: Dict[str, bool] = {
            cmd.id: False for cmd in CHEAT_COMMANDS
        }
        self.current_theme: str = "napoleon_gold"
        self.memory_heatmap: List[Dict[str, Any]] = []
        self.resource_history: List[Dict[str, Any]] = []
        self.presets: List[Dict[str, Any]] = []

    # -- helpers -------------------------------------------------------------

    def active_count(self) -> int:
        return sum(1 for v in self.cheat_states.values() if v)

    def snapshot(self) -> Dict[str, Any]:
        """Full state snapshot sent on connection."""
        return {
            "type": "state_snapshot",
            "cheats": [cmd.to_dict() for cmd in CHEAT_COMMANDS],
            "cheat_states": self.cheat_states,
            "categories": {
                k.value: v for k, v in CATEGORY_META.items()
            },
            "themes": THEMES,
            "current_theme": self.current_theme,
            "active_count": self.active_count(),
            "presets": self.presets,
        }


# ---------------------------------------------------------------------------
# WebSocket handler (framework-agnostic asyncio implementation)
# ---------------------------------------------------------------------------


class NapoleonWebServer:
    """Lightweight async WebSocket server.

    Uses only the Python standard library ``asyncio`` module so we have zero
    extra dependencies.  The ``create_app`` factory below wires everything up.
    """

    def __init__(self, state: Optional[ServerState] = None) -> None:
        self.state = state or ServerState()
        self._clients: Set[asyncio.Queue] = set()  # type: ignore[type-arg]
        self._running = False

    # -- broadcasting --------------------------------------------------------

    async def broadcast(self, message: Dict[str, Any]) -> None:
        """Push *message* to every connected client queue."""
        payload = json.dumps(message)
        dead: list = []
        for q in self._clients:
            try:
                q.put_nowait(payload)
            except asyncio.QueueFull:
                dead.append(q)
        for q in dead:
            self._clients.discard(q)

    # -- message router ------------------------------------------------------

    async def handle_message(self, raw: str) -> Optional[Dict[str, Any]]:
        """Process one inbound JSON message and return an optional reply."""
        try:
            msg = json.loads(raw)
        except json.JSONDecodeError:
            return {"type": "error", "message": "Invalid JSON"}

        msg_type = msg.get("type", "")

        if msg_type == "toggle_cheat":
            return await self._handle_toggle(msg)
        if msg_type == "activate_all":
            return await self._handle_activate_all()
        if msg_type == "deactivate_all":
            return await self._handle_deactivate_all()
        if msg_type == "set_theme":
            return await self._handle_set_theme(msg)
        if msg_type == "get_state":
            return self.state.snapshot()
        if msg_type == "save_preset":
            return await self._handle_save_preset(msg)
        if msg_type == "load_preset":
            return await self._handle_load_preset(msg)
        if msg_type == "get_memory_heatmap":
            return self._handle_memory_heatmap()
        if msg_type == "get_resource_history":
            return self._handle_resource_history()

        return {"type": "error", "message": f"Unknown message type: {msg_type}"}

    # -- individual handlers ------------------------------------------------

    async def _handle_toggle(self, msg: Dict[str, Any]) -> Dict[str, Any]:
        cheat_id = msg.get("cheat_id", "")
        enabled = msg.get("enabled", False)
        if cheat_id not in self.state.cheat_states:
            return {"type": "error", "message": f"Unknown cheat: {cheat_id}"}
        self.state.cheat_states[cheat_id] = bool(enabled)

        # Record resource history sample for graph visualisation
        self.state.resource_history.append(
            {
                "timestamp": time.time(),
                "active_count": self.state.active_count(),
                "cheat_id": cheat_id,
                "enabled": enabled,
            }
        )

        update = {
            "type": "cheat_toggled",
            "cheat_id": cheat_id,
            "enabled": enabled,
            "active_count": self.state.active_count(),
        }
        await self.broadcast(update)
        return update

    async def _handle_activate_all(self) -> Dict[str, Any]:
        for k in self.state.cheat_states:
            self.state.cheat_states[k] = True
        update = {
            "type": "all_activated",
            "active_count": self.state.active_count(),
        }
        await self.broadcast(update)
        return update

    async def _handle_deactivate_all(self) -> Dict[str, Any]:
        for k in self.state.cheat_states:
            self.state.cheat_states[k] = False
        update = {
            "type": "all_deactivated",
            "active_count": 0,
        }
        await self.broadcast(update)
        return update

    async def _handle_set_theme(self, msg: Dict[str, Any]) -> Dict[str, Any]:
        theme = msg.get("theme", "napoleon_gold")
        if theme not in THEMES:
            return {"type": "error", "message": f"Unknown theme: {theme}"}
        self.state.current_theme = theme
        update = {"type": "theme_changed", "theme": theme}
        await self.broadcast(update)
        return update

    async def _handle_save_preset(self, msg: Dict[str, Any]) -> Dict[str, Any]:
        name = msg.get("name", "Unnamed")
        if not isinstance(name, str) or len(name) > 100:
            return {"type": "error", "message": "Invalid preset name"}
        # Strip control characters for safety
        name = "".join(ch for ch in name if ch.isprintable())
        if not name:
            name = "Unnamed"
        preset = {
            "name": name,
            "cheat_states": dict(self.state.cheat_states),
            "theme": self.state.current_theme,
            "created_at": time.time(),
        }
        self.state.presets.append(preset)
        return {"type": "preset_saved", "preset": preset}

    async def _handle_load_preset(self, msg: Dict[str, Any]) -> Dict[str, Any]:
        index = msg.get("index", -1)
        if index < 0 or index >= len(self.state.presets):
            return {"type": "error", "message": "Invalid preset index"}
        preset = self.state.presets[index]
        self.state.cheat_states.update(preset["cheat_states"])
        if preset.get("theme"):
            self.state.current_theme = preset["theme"]
        update = {
            "type": "preset_loaded",
            "cheat_states": self.state.cheat_states,
            "current_theme": self.state.current_theme,
            "active_count": self.state.active_count(),
        }
        await self.broadcast(update)
        return update

    def _handle_memory_heatmap(self) -> Dict[str, Any]:
        return {
            "type": "memory_heatmap",
            "data": self.state.memory_heatmap,
        }

    def _handle_resource_history(self) -> Dict[str, Any]:
        return {
            "type": "resource_history",
            "data": self.state.resource_history,
        }

    # -- HTTP helpers --------------------------------------------------------

    def get_rest_routes(self) -> Dict[str, Any]:
        """Return data for the simple REST-like GET endpoints."""
        return {
            "/api/cheats": [cmd.to_dict() for cmd in CHEAT_COMMANDS],
            "/api/state": self.state.snapshot(),
            "/api/themes": THEMES,
            "/api/categories": {
                k.value: v for k, v in CATEGORY_META.items()
            },
            "/api/presets": self.state.presets,
            "/api/memory/heatmap": self.state.memory_heatmap,
            "/api/resource/history": self.state.resource_history,
        }


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------


def create_app(state: Optional[ServerState] = None) -> NapoleonWebServer:
    """Create and return a configured ``NapoleonWebServer`` instance."""
    return NapoleonWebServer(state=state)
