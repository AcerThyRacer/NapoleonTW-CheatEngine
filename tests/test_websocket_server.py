"""
Tests for the Napoleon TW Cheat Engine WebSocket backend server.

Validates all message handlers, state management, REST routes,
cheat commands, themes, and preset functionality.
"""

import asyncio
import json
import time
from typing import Dict, List, Any
import pytest

from src.server.websocket_server import (
    NapoleonWebServer,
    ServerState,
    create_app,
    THEMES,
    CATEGORY_META,
    CheatCategory,
)
from src.server.engine_service import EngineService

# Helper static list matching the mock engine setup
MOCK_CHEAT_COMMANDS = [
    {
        "id": "infinite_gold",
        "name": "Imperial Treasury",
        "description": "Fill the imperial coffers with unlimited gold",
        "category": "treasury",
        "icon": "⚙️",
        "default_value": 999999,
        "min_value": 0,
        "max_value": 999999,
        "is_toggle": True,
        "is_slider": False
    },
    {
        "id": "god_mode",
        "name": "Divine Protection",
        "description": "Your armies are invincible in battle",
        "category": "battle",
        "icon": "⚙️",
        "default_value": 1,
        "min_value": 0,
        "max_value": 999999,
        "is_toggle": True,
        "is_slider": False
    },
    {
        "id": "super_speed",
        "name": "Napoleonic Blitz",
        "description": "Accelerate time on the battlefield",
        "category": "battle",
        "icon": "⚙️",
        "default_value": 5,
        "min_value": 0,
        "max_value": 999999,
        "is_toggle": True,
        "is_slider": True
    }
]

class MockEngineService(EngineService):
    def __init__(self):
        super().__init__()
        self._attached = True
        self._states: Dict[str, bool] = {cmd["id"]: False for cmd in MOCK_CHEAT_COMMANDS}
        self.history: List[Dict[str, Any]] = []

    def get_cheat_catalog(self) -> List[Dict[str, Any]]:
        return MOCK_CHEAT_COMMANDS

    def is_attached(self) -> bool:
        return self._attached

    def toggle_cheat(self, cheat_id: str, enabled: bool) -> bool:
        if not self._attached:
            return False
        if cheat_id in self._states:
            self._states[cheat_id] = enabled
            self.history.append({"cheat_id": cheat_id, "enabled": enabled})
            return True
        return False

    def activate_all(self) -> None:
        if not self._attached:
            return
        for k in self._states:
            self._states[k] = True

    def deactivate_all(self) -> None:
        for k in self._states:
            self._states[k] = False

    def get_cheat_status(self, cheat_id: str) -> bool:
        return self._states.get(cheat_id, False)

    def get_all_cheat_states(self) -> Dict[str, bool]:
        return dict(self._states)

    def get_resource_history(self) -> List[Dict[str, Any]]:
        return self.history


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def state():
    return ServerState()

@pytest.fixture
def engine_service():
    return MockEngineService()


@pytest.fixture
def server(state, engine_service):
    return NapoleonWebServer(state=state, engine_service=engine_service)


# ---------------------------------------------------------------------------
# CheatCommand and domain model tests
# ---------------------------------------------------------------------------

class TestCheatCommands:
    """Tests for the cheat command definitions provided by engine."""

    def test_all_commands_have_ids(self, server):
        for cmd in server.engine_service.get_cheat_catalog():
            assert cmd["id"], f"Command missing id: {cmd}"

    def test_all_commands_have_names(self, server):
        for cmd in server.engine_service.get_cheat_catalog():
            assert cmd["name"], f"Command missing name: {cmd}"

    def test_all_commands_have_categories(self, server):
        valid = {c.value for c in CheatCategory}
        for cmd in server.engine_service.get_cheat_catalog():
            assert cmd["category"] in valid, f"Invalid category for {cmd['id']}: {cmd['category']}"

    def test_command_count_matches_engine(self, server):
        assert len(server.engine_service.get_cheat_catalog()) == len(MOCK_CHEAT_COMMANDS)

    def test_slider_cheat_has_range(self, server):
        slider_cheats = [c for c in server.engine_service.get_cheat_catalog() if c.get("is_slider")]
        assert len(slider_cheats) >= 1
        for cmd in slider_cheats:
            assert cmd["min_value"] < cmd["max_value"]

    def test_unique_ids(self, server):
        ids = [c["id"] for c in server.engine_service.get_cheat_catalog()]
        assert len(ids) == len(set(ids)), "Duplicate cheat IDs found"


class TestCategoryMeta:
    """Tests for category metadata."""

    def test_all_categories_have_meta(self):
        for cat in CheatCategory:
            assert cat in CATEGORY_META, f"Missing metadata for {cat}"

    def test_meta_has_required_fields(self):
        for cat, meta in CATEGORY_META.items():
            assert "icon" in meta
            assert "emoji" in meta
            assert "tooltip" in meta


class TestThemes:
    """Tests for theme definitions."""

    def test_all_themes_present(self):
        expected = {"napoleon_gold", "imperial_blue", "royal_purple",
                    "battlefield_steel", "midnight_command"}
        assert set(THEMES.keys()) == expected

    def test_theme_has_required_colors(self):
        for name, colors in THEMES.items():
            assert "primary" in colors, f"Missing primary in {name}"
            assert "secondary" in colors, f"Missing secondary in {name}"
            assert "background" in colors, f"Missing background in {name}"
            assert "panel" in colors, f"Missing panel in {name}"

    def test_colors_are_hex(self):
        for name, colors in THEMES.items():
            for key, value in colors.items():
                assert value.startswith("#"), f"{name}.{key} not hex: {value}"


# ---------------------------------------------------------------------------
# ServerState tests
# ---------------------------------------------------------------------------

class TestServerState:
    """Tests for ServerState."""

    def test_initial_state(self, server):
        assert server.active_count() == 0
        assert server.state.current_theme == "napoleon_gold"
        assert len(server.get_cheat_states()) == len(MOCK_CHEAT_COMMANDS)
        assert all(v is False for v in server.get_cheat_states().values())

    def test_active_count(self, server):
        server.engine_service.toggle_cheat("infinite_gold", True)
        assert server.active_count() == 1

    def test_snapshot(self, server):
        snap = server.snapshot()
        assert snap["type"] == "state_snapshot"
        assert len(snap["cheats"]) == len(MOCK_CHEAT_COMMANDS)
        assert "cheat_states" in snap
        assert "themes" in snap
        assert "categories" in snap
        assert snap["active_count"] == 0

    def test_snapshot_reflects_state(self, server):
        server.engine_service.toggle_cheat("god_mode", True)
        server.state.current_theme = "imperial_blue"
        snap = server.snapshot()
        assert snap["active_count"] == 1
        assert snap["current_theme"] == "imperial_blue"


# ---------------------------------------------------------------------------
# WebSocket message handler tests
# ---------------------------------------------------------------------------

class TestMessageHandlers:
    """Tests for NapoleonWebServer message handlers."""

    @pytest.mark.asyncio
    async def test_get_state(self, server):
        reply = await server.handle_message('{"type": "get_state"}')
        assert reply["type"] == "state_snapshot"
        assert len(reply["cheats"]) == len(MOCK_CHEAT_COMMANDS)

    @pytest.mark.asyncio
    async def test_toggle_cheat_on(self, server):
        msg = json.dumps({"type": "toggle_cheat", "cheat_id": "infinite_gold", "enabled": True})
        reply = await server.handle_message(msg)
        assert reply["type"] == "cheat_toggled"
        assert reply["cheat_id"] == "infinite_gold"
        assert reply["enabled"] is True
        assert reply["active_count"] == 1
        assert server.engine_service.get_cheat_status("infinite_gold") is True

    @pytest.mark.asyncio
    async def test_toggle_cheat_off(self, server):
        server.engine_service.toggle_cheat("god_mode", True)
        msg = json.dumps({"type": "toggle_cheat", "cheat_id": "god_mode", "enabled": False})
        reply = await server.handle_message(msg)
        assert reply["enabled"] is False
        assert server.engine_service.get_cheat_status("god_mode") is False

    @pytest.mark.asyncio
    async def test_toggle_cheat_unattached(self, server):
        server.engine_service._attached = False
        msg = json.dumps({"type": "toggle_cheat", "cheat_id": "infinite_gold", "enabled": True})
        reply = await server.handle_message(msg)
        assert reply["type"] == "error"
        assert "Engine not attached" in reply["message"]

    @pytest.mark.asyncio
    async def test_toggle_unknown_cheat(self, server):
        msg = json.dumps({"type": "toggle_cheat", "cheat_id": "nonexistent", "enabled": True})
        reply = await server.handle_message(msg)
        assert reply["type"] == "error"
        assert "Unknown cheat" in reply["message"]

    @pytest.mark.asyncio
    async def test_activate_all(self, server):
        reply = await server.handle_message('{"type": "activate_all"}')
        assert reply["type"] == "all_activated"
        assert reply["active_count"] == len(MOCK_CHEAT_COMMANDS)
        assert all(v is True for v in server.get_cheat_states().values())

    @pytest.mark.asyncio
    async def test_deactivate_all(self, server):
        # First activate some
        server.engine_service.toggle_cheat("god_mode", True)
        reply = await server.handle_message('{"type": "deactivate_all"}')
        assert reply["type"] == "all_deactivated"
        assert reply["active_count"] == 0
        assert all(v is False for v in server.get_cheat_states().values())

    @pytest.mark.asyncio
    async def test_set_theme(self, server):
        msg = json.dumps({"type": "set_theme", "theme": "imperial_blue"})
        reply = await server.handle_message(msg)
        assert reply["type"] == "theme_changed"
        assert reply["theme"] == "imperial_blue"
        assert server.state.current_theme == "imperial_blue"

    @pytest.mark.asyncio
    async def test_set_invalid_theme(self, server):
        msg = json.dumps({"type": "set_theme", "theme": "nope"})
        reply = await server.handle_message(msg)
        assert reply["type"] == "error"
        assert "Unknown theme" in reply["message"]

    @pytest.mark.asyncio
    async def test_save_preset(self, server):
        server.engine_service.toggle_cheat("god_mode", True)
        msg = json.dumps({"type": "save_preset", "name": "Test Preset"})
        reply = await server.handle_message(msg)
        assert reply["type"] == "preset_saved"
        assert reply["preset"]["name"] == "Test Preset"
        assert reply["preset"]["cheat_states"]["god_mode"] is True
        assert len(server.state.presets) == 1

    @pytest.mark.asyncio
    async def test_load_preset(self, server):
        # Save first
        server.engine_service.toggle_cheat("god_mode", True)
        await server.handle_message(json.dumps({"type": "save_preset", "name": "P1"}))
        # Reset state
        server.engine_service.toggle_cheat("god_mode", False)
        # Load
        reply = await server.handle_message(json.dumps({"type": "load_preset", "index": 0}))
        assert reply["type"] == "preset_loaded"
        assert server.engine_service.get_cheat_status("god_mode") is True

    @pytest.mark.asyncio
    async def test_load_invalid_preset(self, server):
        reply = await server.handle_message(json.dumps({"type": "load_preset", "index": 99}))
        assert reply["type"] == "error"

    @pytest.mark.asyncio
    async def test_save_preset_name_too_long(self, server):
        msg = json.dumps({"type": "save_preset", "name": "A" * 200})
        reply = await server.handle_message(msg)
        assert reply["type"] == "error"
        assert "Invalid preset name" in reply["message"]

    @pytest.mark.asyncio
    async def test_save_preset_strips_control_chars(self, server):
        msg = json.dumps({"type": "save_preset", "name": "Test\x00Preset"})
        reply = await server.handle_message(msg)
        assert reply["type"] == "preset_saved"
        assert reply["preset"]["name"] == "TestPreset"

    @pytest.mark.asyncio
    async def test_get_memory_heatmap(self, server):
        reply = await server.handle_message('{"type": "get_memory_heatmap"}')
        assert reply["type"] == "memory_heatmap"
        assert isinstance(reply["data"], list)

    @pytest.mark.asyncio
    async def test_get_resource_history(self, server):
        reply = await server.handle_message('{"type": "get_resource_history"}')
        assert reply["type"] == "resource_history"
        assert isinstance(reply["data"], list)

    @pytest.mark.asyncio
    async def test_unknown_message(self, server):
        reply = await server.handle_message('{"type": "unknown_cmd"}')
        assert reply["type"] == "error"

    @pytest.mark.asyncio
    async def test_invalid_json(self, server):
        reply = await server.handle_message("not json")
        assert reply["type"] == "error"
        assert "Invalid JSON" in reply["message"]

    @pytest.mark.asyncio
    async def test_toggle_records_history(self, server):
        msg = json.dumps({"type": "toggle_cheat", "cheat_id": "god_mode", "enabled": True})
        await server.handle_message(msg)
        history = server.engine_service.get_resource_history()
        assert len(history) == 1
        entry = history[0]
        assert entry["cheat_id"] == "god_mode"
        assert entry["enabled"] is True


# ---------------------------------------------------------------------------
# Broadcast tests
# ---------------------------------------------------------------------------

class TestBroadcast:
    """Tests for the broadcast mechanism."""

    @pytest.mark.asyncio
    async def test_broadcast_reaches_clients(self, server):
        q1: asyncio.Queue = asyncio.Queue()
        q2: asyncio.Queue = asyncio.Queue()
        server._clients.add(q1)
        server._clients.add(q2)

        await server.broadcast({"type": "test", "data": 42})

        msg1 = json.loads(q1.get_nowait())
        msg2 = json.loads(q2.get_nowait())
        assert msg1["type"] == "test"
        assert msg2["data"] == 42

    @pytest.mark.asyncio
    async def test_broadcast_removes_full_queues(self, server):
        full_q: asyncio.Queue = asyncio.Queue(maxsize=1)
        full_q.put_nowait("filler")
        server._clients.add(full_q)

        await server.broadcast({"type": "overflow"})
        # Full queue should have been removed
        assert full_q not in server._clients


# ---------------------------------------------------------------------------
# REST routes tests
# ---------------------------------------------------------------------------

class TestRestRoutes:
    """Tests for the REST endpoint data."""

    def test_rest_routes_keys(self, server):
        routes = server.get_rest_routes()
        assert "/api/cheats" in routes
        assert "/api/state" in routes
        assert "/api/themes" in routes
        assert "/api/categories" in routes
        assert "/api/presets" in routes
        assert "/api/memory/heatmap" in routes
        assert "/api/resource/history" in routes

    def test_cheats_route_returns_list(self, server):
        routes = server.get_rest_routes()
        assert isinstance(routes["/api/cheats"], list)
        assert len(routes["/api/cheats"]) == len(MOCK_CHEAT_COMMANDS)

    def test_themes_route(self, server):
        routes = server.get_rest_routes()
        assert "napoleon_gold" in routes["/api/themes"]


# ---------------------------------------------------------------------------
# Factory test
# ---------------------------------------------------------------------------

class TestFactory:
    """Tests for the create_app factory."""

    def test_create_app_default(self):
        app = create_app()
        assert isinstance(app, NapoleonWebServer)
        assert isinstance(app.state, ServerState)

    def test_create_app_with_state(self, state):
        state.current_theme = "royal_purple"
        app = create_app(state=state)
        assert app.state.current_theme == "royal_purple"
