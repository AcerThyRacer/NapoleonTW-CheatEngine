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
from enum import Enum
from typing import Any, Dict, List, Optional, Set

from src.server.engine_service import EngineService

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
    """Mutable runtime UI/Session state shared across WebSocket clients.
    Note: Real engine state comes from EngineService.
    """

    def __init__(self) -> None:
        self.current_theme: str = "napoleon_gold"
        self.presets: List[Dict[str, Any]] = []


# ---------------------------------------------------------------------------
# WebSocket handler (framework-agnostic asyncio implementation)
# ---------------------------------------------------------------------------


class NapoleonWebServer:
    """Lightweight async WebSocket server.

    Uses only the Python standard library ``asyncio`` module so we have zero
    extra dependencies.  The ``create_app`` factory below wires everything up.
    """

    def __init__(
        self,
        state: Optional[ServerState] = None,
        engine_service: Optional[EngineService] = None
    ) -> None:
        self.state = state or ServerState()
        self.engine_service = engine_service or EngineService()
        self._clients: Set[asyncio.Queue] = set()  # type: ignore[type-arg]
        self._running = False

    def get_cheat_states(self) -> Dict[str, bool]:
        """Fetch real cheat state from the engine."""
        return self.engine_service.get_all_cheat_states()

    def active_count(self) -> int:
        return sum(1 for v in self.get_cheat_states().values() if v)

    def snapshot(self) -> Dict[str, Any]:
        """Full state snapshot sent on connection."""
        return {
            "type": "state_snapshot",
            "cheats": self.engine_service.get_cheat_catalog(),
            "cheat_states": self.get_cheat_states(),
            "categories": {
                k.value: v for k, v in CATEGORY_META.items()
            },
            "themes": THEMES,
            "current_theme": self.state.current_theme,
            "active_count": self.active_count(),
            "presets": self.state.presets,
        }


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
            return self.snapshot()
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

        valid_ids = {c["id"] for c in self.engine_service.get_cheat_catalog()}
        if cheat_id not in valid_ids:
            return {"type": "error", "message": f"Unknown cheat: {cheat_id}"}

        if not self.engine_service.is_attached():
            return {"type": "error", "message": "Engine not attached"}

        success = self.engine_service.toggle_cheat(cheat_id, bool(enabled))
        if not success:
            return {"type": "error", "message": f"Failed to toggle {cheat_id}"}

        # Query actual state to ensure sync
        actual_enabled = self.engine_service.get_cheat_status(cheat_id)

        update = {
            "type": "cheat_toggled",
            "cheat_id": cheat_id,
            "enabled": actual_enabled,
            "active_count": self.active_count(),
        }
        await self.broadcast(update)
        return update

    async def _handle_activate_all(self) -> Dict[str, Any]:
        if not self.engine_service.is_attached():
            return {"type": "error", "message": "Engine not attached"}

        self.engine_service.activate_all()

        update = {
            "type": "all_activated",
            "active_count": self.active_count(),
        }
        await self.broadcast(update)
        return update

    async def _handle_deactivate_all(self) -> Dict[str, Any]:
        self.engine_service.deactivate_all()
        update = {
            "type": "all_deactivated",
            "active_count": self.active_count(),
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
            "cheat_states": self.get_cheat_states(),
            "theme": self.state.current_theme,
            "created_at": time.time(),
        }
        self.state.presets.append(preset)
        return {"type": "preset_saved", "preset": preset}

    async def _handle_load_preset(self, msg: Dict[str, Any]) -> Dict[str, Any]:
        index = msg.get("index", -1)
        if index < 0 or index >= len(self.state.presets):
            return {"type": "error", "message": "Invalid preset index"}

        if not self.engine_service.is_attached():
            return {"type": "error", "message": "Engine not attached"}

        preset = self.state.presets[index]

        # Apply cheat states
        target_states = preset.get("cheat_states", {})
        for cheat_id, enabled in target_states.items():
            self.engine_service.toggle_cheat(cheat_id, enabled)

        if preset.get("theme"):
            self.state.current_theme = preset["theme"]

        update = {
            "type": "preset_loaded",
            "cheat_states": self.get_cheat_states(),
            "current_theme": self.state.current_theme,
            "active_count": self.active_count(),
        }
        await self.broadcast(update)
        return update

    def _handle_memory_heatmap(self) -> Dict[str, Any]:
        return {
            "type": "memory_heatmap",
            "data": self.engine_service.get_memory_heatmap(),
        }

    def _handle_resource_history(self) -> Dict[str, Any]:
        return {
            "type": "resource_history",
            "data": self.engine_service.get_resource_history(),
        }

    # -- HTTP helpers --------------------------------------------------------

    def get_rest_routes(self) -> Dict[str, Any]:
        """Return data for the simple REST-like GET endpoints."""
        return {
            "/api/cheats": self.engine_service.get_cheat_catalog(),
            "/api/state": self.snapshot(),
            "/api/themes": THEMES,
            "/api/categories": {
                k.value: v for k, v in CATEGORY_META.items()
            },
            "/api/presets": self.state.presets,
            "/api/memory/heatmap": self.engine_service.get_memory_heatmap(),
            "/api/resource/history": self.engine_service.get_resource_history(),
        }


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------


def create_app(
    state: Optional[ServerState] = None,
    engine_service: Optional[EngineService] = None
) -> NapoleonWebServer:
    """Create and return a configured ``NapoleonWebServer`` instance."""
    return NapoleonWebServer(state=state, engine_service=engine_service)
