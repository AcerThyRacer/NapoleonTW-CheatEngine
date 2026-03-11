"""
WebSocket server module for the Napoleon TW Cheat Engine web UI.

Provides a real-time bridge between the React/Tauri frontend and the
Python memory-hacking backend via HTTP + WebSocket endpoints.
"""

from src.server.websocket_server import NapoleonWebServer, create_app, main, run_server

__all__ = ["NapoleonWebServer", "create_app", "run_server", "main"]
