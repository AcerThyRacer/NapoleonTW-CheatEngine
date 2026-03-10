"""
Multi-process cheat synchronization system.
Synchronizes cheat states across multiple trainer instances using UDP.

EXPERIMENTAL FEATURE:
This module enables LAN party synchronization where multiple trainer instances
can share cheat states. Uses UDP broadcast on port 9999 for communication.

Network Protocol:
- Message Format: JSON over UDP
- Discovery: Broadcast heartbeat every 5 seconds
- Sync: Cheat toggle events broadcast to all instances
- Conflict Resolution: Last-write-wins (simplest approach)

Status: Experimental - network configuration may be required for firewalls.
"""

import logging
import socket
import threading
import json
from typing import Dict, Any, Optional, Set, Callable
from dataclasses import dataclass
from enum import Enum
import time

logger = logging.getLogger('napoleon.trainer.sync')


class SyncMessageType(Enum):
    """Types of sync messages."""
    CHEAT_TOGGLED = 'cheat_toggled'
    CHEAT_STATE = 'cheat_state'
    HEARTBEAT = 'heartbeat'
    DISCONNECT = 'disconnect'


@dataclass
class SyncMessage:
    """Represents a synchronization message."""
    message_type: SyncMessageType
    cheat_type: Optional[str] = None
    is_active: bool = False
    instance_id: Optional[str] = None
    timestamp: Optional[float] = None
    
    def to_json(self) -> str:
        """Serialize to JSON."""
        return json.dumps({
            'type': self.message_type.value,
            'cheat_type': self.cheat_type,
            'is_active': self.is_active,
            'instance_id': self.instance_id,
            'timestamp': self.timestamp or time.time(),
        })
    
    @classmethod
    def from_json(cls, data: str) -> Optional['SyncMessage']:
        """Deserialize from JSON."""
        try:
            obj = json.loads(data)
            return cls(
                message_type=SyncMessageType(obj['type']),
                cheat_type=obj.get('cheat_type'),
                is_active=obj.get('is_active', False),
                instance_id=obj.get('instance_id'),
                timestamp=obj.get('timestamp'),
            )
        except (json.JSONDecodeError, KeyError, ValueError):
            return None


class CheatSyncManager:
    """
    Synchronizes cheat states across multiple trainer instances.
    
    Features:
    - UDP unicast communication on ports 27015-27025
    - Per-instance overrides to ignore specific cheats
    - Infinite loop prevention via _syncing_cheats tracking
    - Automatic peer discovery and heartbeat
    """
    
    def __init__(
        self,
        instance_id: Optional[str] = None,
        port_range: tuple = (27015, 27025),
        broadcast_interval: float = 0.1,
    ):
        """
        Initialize cheat sync manager.
        
        Args:
            instance_id: Unique instance identifier (auto-generated if None)
            port_range: Port range for UDP communication
            broadcast_interval: Interval between broadcasts in seconds
        """
        import uuid
        self.instance_id = instance_id or str(uuid.uuid4())[:8]
        self.port_range = port_range
        self.broadcast_interval = broadcast_interval
        
        self._socket: Optional[socket.socket] = None
        self._thread: Optional[threading.Thread] = None
        self._running = False
        
        # State tracking
        self._syncing_cheats: Set[str] = set()  # Prevent infinite loops
        self._ignore_overrides: Set[str] = set()  # Cheats to ignore from others
        self._known_peers: Set[str] = set()
        self._last_broadcast = 0.0
        
        # Callbacks
        self._on_remote_cheat_toggle: Optional[Callable[[str, bool], None]] = None
        
        # Statistics
        self._messages_sent = 0
        self._messages_received = 0
        
        # Bind to port
        self._bind_socket()
    
    def _bind_socket(self) -> bool:
        """Bind to a UDP port in the configured range."""
        for port in range(self.port_range[0], self.port_range[1] + 1):
            try:
                self._socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                self._socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                self._socket.bind(('127.0.0.1', port))
                self._socket.settimeout(0.1)  # Non-blocking
                logger.info("CheatSync bound to port %d", port)
                return True
            except OSError:
                if self._socket:
                    self._socket.close()
                    self._socket = None
        
        logger.error("Failed to bind to any port in range %s", self.port_range)
        return False
    
    def set_ignore_overrides(self, cheat_types: Set[str]) -> None:
        """
        Set cheats to ignore from remote instances.
        
        Args:
            cheat_types: Set of cheat type strings to ignore
        """
        self._ignore_overrides = cheat_types.copy()
        logger.debug("Sync ignore overrides set: %s", self._ignore_overrides)
    
    def add_ignore_override(self, cheat_type: str) -> None:
        """Add a single cheat type to ignore overrides."""
        self._ignore_overrides.add(cheat_type)
        logger.debug("Sync ignore override added: %s", cheat_type)
    
    def remove_ignore_override(self, cheat_type: str) -> None:
        """Remove a cheat type from ignore overrides."""
        self._ignore_overrides.discard(cheat_type)
    
    def set_remote_toggle_callback(
        self,
        callback: Callable[[str, bool], None],
    ) -> None:
        """
        Set callback for remote cheat toggles.
        
        Args:
            callback: Function(cheat_type, is_active) to call on remote toggle
        """
        self._on_remote_cheat_toggle = callback
    
    def start(self) -> None:
        """Start the sync manager."""
        if self._running or not self._socket:
            return
        
        self._running = True
        self._thread = threading.Thread(
            target=self._sync_loop,
            daemon=True,
            name=f"CheatSync-{self.instance_id}"
        )
        self._thread.start()
        logger.info("CheatSync started (instance=%s)", self.instance_id)
    
    def stop(self) -> None:
        """Stop the sync manager."""
        self._running = False
        
        # Send disconnect message
        self._broadcast_message(SyncMessage(
            message_type=SyncMessageType.DISCONNECT,
            instance_id=self.instance_id,
        ))
        
        if self._thread:
            self._thread.join(timeout=2.0)
            self._thread = None
        
        if self._socket:
            self._socket.close()
            self._socket = None
        
        logger.info("CheatSync stopped")
    
    def _sync_loop(self) -> None:
        """Main sync loop."""
        while self._running:
            try:
                # Receive messages
                self._receive_messages()
                
                # Send heartbeat periodically
                current_time = time.time()
                if current_time - self._last_broadcast > 5.0:
                    self._broadcast_message(SyncMessage(
                        message_type=SyncMessageType.HEARTBEAT,
                        instance_id=self.instance_id,
                    ))
                
                time.sleep(self.broadcast_interval)
                
            except Exception as e:
                logger.error("Sync loop error: %s", e)
                time.sleep(0.5)
    
    def _receive_messages(self) -> None:
        """Receive and process incoming messages."""
        if not self._socket:
            return
        
        try:
            data, addr = self._socket.recvfrom(4096)
            message = SyncMessage.from_json(data.decode('utf-8'))
            
            if message:
                self._messages_received += 1
                
                # Track peer
                if message.instance_id and message.instance_id != self.instance_id:
                    self._known_peers.add(message.instance_id)
                
                # Process message
                self._handle_message(message)
                
        except socket.timeout:
            pass
        except Exception as e:
            logger.debug("Receive error: %s", e)
    
    def _handle_message(self, message: SyncMessage) -> None:
        """Handle an incoming sync message."""
        if message.instance_id == self.instance_id:
            return  # Ignore own messages
        
        if message.message_type == SyncMessageType.CHEAT_TOGGLED:
            # Check ignore overrides
            if message.cheat_type in self._ignore_overrides:
                logger.debug("Ignoring remote toggle for %s (override)", message.cheat_type)
                return
            
            # Prevent infinite loop
            if message.cheat_type in self._syncing_cheats:
                logger.debug("Skipping sync for %s (already syncing)", message.cheat_type)
                return
            
            # Trigger callback
            if self._on_remote_cheat_toggle:
                logger.info(
                    "Remote cheat toggle: %s from %s (active=%s)",
                    message.cheat_type, message.instance_id, message.is_active
                )
                self._on_remote_cheat_toggle(message.cheat_type, message.is_active)
        
        elif message.message_type == SyncMessageType.DISCONNECT:
            # Remove peer
            if message.instance_id in self._known_peers:
                self._known_peers.discard(message.instance_id)
                logger.info("Peer disconnected: %s", message.instance_id)
    
    def broadcast_cheat_toggle(self, cheat_type: str, is_active: bool) -> None:
        """
        Broadcast a cheat toggle to all peers.
        
        Args:
            cheat_type: Type of cheat toggled
            is_active: Whether cheat is now active
        """
        if not self._running or not self._socket:
            return
        
        # Mark as syncing to prevent loop
        self._syncing_cheats.add(cheat_type)
        
        message = SyncMessage(
            message_type=SyncMessageType.CHEAT_TOGGLED,
            cheat_type=cheat_type,
            is_active=is_active,
            instance_id=self.instance_id,
        )
        
        self._broadcast_message(message)
        
        # Clear syncing flag after short delay
        def clear_syncing():
            time.sleep(0.5)
            self._syncing_cheats.discard(cheat_type)
        
        threading.Thread(target=clear_syncing, daemon=True).start()
    
    def _broadcast_message(self, message: SyncMessage) -> None:
        """Broadcast a message to all ports in range."""
        if not self._socket:
            return
        
        data = message.to_json().encode('utf-8')
        
        for port in range(self.port_range[0], self.port_range[1] + 1):
            try:
                self._socket.sendto(data, ('127.0.0.1', port))
            except Exception:
                pass
        
        self._messages_sent += 1
        self._last_broadcast = time.time()
    
    def get_stats(self) -> Dict[str, Any]:
        """Get sync manager statistics."""
        return {
            'instance_id': self.instance_id,
            'is_running': self._running,
            'known_peers': list(self._known_peers),
            'messages_sent': self._messages_sent,
            'messages_received': self._messages_received,
            'syncing_cheats': list(self._syncing_cheats),
            'ignore_overrides': list(self._ignore_overrides),
        }
    
    def get_peer_count(self) -> int:
        """Get number of known peers."""
        return len(self._known_peers)
