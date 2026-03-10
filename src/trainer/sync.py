import socket
import threading
import json
import logging
from typing import Set, Callable, Optional, Dict, Any

from src.memory.cheats import CheatType

logger = logging.getLogger('napoleon.trainer.sync')

class CheatSyncManager:
    """
    Synchronises active cheats across multiple linked Napoleon Total War instances.
    Uses UDP broadcast on localhost to communicate between trainer instances.
    """

    DEFAULT_PORT_START = 27015
    DEFAULT_PORT_END = 27025
    DEFAULT_HOST = '127.0.0.1'

    def __init__(self, port_start: int = DEFAULT_PORT_START, port_end: int = DEFAULT_PORT_END):
        self.port_start = port_start
        self.port_end = port_end
        self.bound_port: Optional[int] = None
        self.host = self.DEFAULT_HOST
        self.running = False
        self._listener_thread: Optional[threading.Thread] = None
        self._socket: Optional[socket.socket] = None
        self._overrides: Set[CheatType] = set()
        self._on_sync_received: Optional[Callable[[CheatType, bool], None]] = None

    def set_callback(self, callback: Callable[[CheatType, bool], None]) -> None:
        """Set the callback to execute when a sync event is received."""
        self._on_sync_received = callback

    def set_override(self, cheat_type: CheatType, ignore: bool) -> None:
        """
        Configure per-instance override for a cheat type.
        If ignore is True, sync events for this cheat will be ignored.
        """
        if ignore:
            self._overrides.add(cheat_type)
        else:
            self._overrides.discard(cheat_type)

    def is_overridden(self, cheat_type: CheatType) -> bool:
        """Check if a cheat is configured to ignore sync events."""
        return cheat_type in self._overrides

    def start(self) -> bool:
        """Start the synchronization listener by binding to the first available port in the range."""
        if self.running:
            return True

        self._socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        # We don't use SO_REUSEADDR here because we want each instance to have a unique port
        # within the port range for reliable unicast delivery.

        for port in range(self.port_start, self.port_end + 1):
            try:
                self._socket.bind((self.host, port))
                self.bound_port = port
                self.running = True
                break
            except OSError:
                continue

        if not self.running:
            logger.error(f"Failed to start CheatSyncManager: No available ports in range {self.port_start}-{self.port_end}")
            self._socket.close()
            self._socket = None
            return False

        self._listener_thread = threading.Thread(target=self._listen_loop, daemon=True)
        self._listener_thread.start()
        logger.info(f"CheatSyncManager listening on {self.host}:{self.bound_port}")
        return True

    def stop(self) -> None:
        """Stop the synchronization listener."""
        self.running = False
        if self._socket and self.bound_port is not None:
            try:
                # Send a dummy packet to wake up the blocking recvfrom
                dummy_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                dummy_sock.sendto(b'{"action":"stop"}', (self.host, self.bound_port))
                dummy_sock.close()
                self._socket.close()
            except Exception:
                pass
            self._socket = None
            self.bound_port = None

        if self._listener_thread and self._listener_thread.is_alive():
            self._listener_thread.join(timeout=1.0)

    def broadcast_toggle(self, cheat_type: CheatType, is_active: bool) -> None:
        """Send a cheat toggle event to all other instances in the port range."""
        if not self.running or self.bound_port is None:
            return

        payload = {
            "action": "toggle",
            "cheat_type": cheat_type.value,
            "active": is_active
        }

        try:
            data = json.dumps(payload).encode('utf-8')
            send_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

            # Send to all ports in the range except our own
            for target_port in range(self.port_start, self.port_end + 1):
                if target_port != self.bound_port:
                    try:
                        send_sock.sendto(data, (self.host, target_port))
                    except Exception:
                        pass

            send_sock.close()
        except Exception as e:
            logger.debug(f"Failed to broadcast sync event: {e}")

    def _listen_loop(self) -> None:
        """Background thread loop to listen for sync events."""
        while self.running and self._socket:
            try:
                data, addr = self._socket.recvfrom(1024)
                if not self.running:
                    break

                payload = json.loads(data.decode('utf-8'))

                if payload.get("action") == "stop":
                    continue

                if payload.get("action") == "toggle":
                    cheat_type_str = payload.get("cheat_type")
                    is_active = payload.get("active")

                    if cheat_type_str is None or is_active is None:
                        continue

                    try:
                        cheat_type = CheatType(cheat_type_str)
                    except ValueError:
                        continue

                    if self.is_overridden(cheat_type):
                        continue

                    if self._on_sync_received:
                        self._on_sync_received(cheat_type, is_active)

            except socket.timeout:
                continue
            except json.JSONDecodeError:
                continue
            except Exception as e:
                if self.running:
                    logger.debug(f"Error in sync listener: {e}")
