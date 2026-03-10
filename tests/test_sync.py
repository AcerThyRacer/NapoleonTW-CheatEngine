"""
Tests for multi-process cheat synchronization.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import socket
import time
from src.trainer.sync import (
    CheatSyncManager,
    SyncMessageType,
    SyncMessage,
)


class TestSyncMessage:
    """Test SyncMessage serialization."""
    
    def test_message_serialization(self):
        """Test serializing a sync message to JSON."""
        message = SyncMessage(
            message_type=SyncMessageType.CHEAT_TOGGLED,
            cheat_type='god_mode',
            is_active=True,
            instance_id='test123',
            timestamp=1234567890.0,
        )
        
        json_str = message.to_json()
        
        assert 'god_mode' in json_str
        assert 'cheat_toggled' in json_str  # Lowercase in JSON
        assert 'test123' in json_str
    
    def test_message_deserialization(self):
        """Test deserializing a sync message from JSON."""
        json_str = '{"type": "cheat_toggled", "cheat_type": "unlimited_ammo", "is_active": false, "instance_id": "abc456", "timestamp": 1234567890.0}'
        
        message = SyncMessage.from_json(json_str)
        
        assert message is not None
        assert message.message_type == SyncMessageType.CHEAT_TOGGLED
        assert message.cheat_type == 'unlimited_ammo'
        assert message.is_active is False
        assert message.instance_id == 'abc456'
    
    def test_message_invalid_json(self):
        """Test deserializing invalid JSON."""
        message = SyncMessage.from_json('invalid json')
        
        assert message is None
    
    def test_message_heartbeat(self):
        """Test creating a heartbeat message."""
        message = SyncMessage(
            message_type=SyncMessageType.HEARTBEAT,
            instance_id='test123',
        )
        
        json_str = message.to_json()
        assert 'heartbeat' in json_str


class TestCheatSyncManager:
    """Test CheatSyncManager functionality."""
    
    @pytest.fixture
    def sync_manager(self):
        """Create a sync manager for testing."""
        with patch('socket.socket'):
            manager = CheatSyncManager(
                instance_id='test_instance',
                port_range=(27015, 27016),
                broadcast_interval=0.01,
            )
            yield manager
            manager.stop()
    
    def test_initialization(self, sync_manager):
        """Test sync manager initialization."""
        assert sync_manager.instance_id == 'test_instance'
        assert sync_manager.port_range == (27015, 27016)
        assert not sync_manager._running
    
    def test_start_stop(self, sync_manager):
        """Test starting and stopping the sync manager."""
        sync_manager.start()
        
        assert sync_manager._running is True
        assert sync_manager._thread is not None
        assert sync_manager._thread.is_alive()
        
        sync_manager.stop()
        
        assert sync_manager._running is False
    
    def test_ignore_overrides(self, sync_manager):
        """Test setting ignore overrides."""
        sync_manager.set_ignore_overrides({'god_mode', 'unlimited_ammo'})
        
        assert 'god_mode' in sync_manager._ignore_overrides
        assert 'unlimited_ammo' in sync_manager._ignore_overrides
    
    def test_add_ignore_override(self, sync_manager):
        """Test adding a single ignore override."""
        sync_manager.add_ignore_override('super_speed')
        
        assert 'super_speed' in sync_manager._ignore_overrides
    
    def test_remove_ignore_override(self, sync_manager):
        """Test removing an ignore override."""
        sync_manager.add_ignore_override('test_cheat')
        sync_manager.remove_ignore_override('test_cheat')
        
        assert 'test_cheat' not in sync_manager._ignore_overrides
    
    def test_remote_toggle_callback(self, sync_manager):
        """Test setting remote toggle callback."""
        callback = Mock()
        sync_manager.set_remote_toggle_callback(callback)
        
        assert sync_manager._on_remote_cheat_toggle == callback
    
    def test_broadcast_cheat_toggle(self, sync_manager):
        """Test broadcasting a cheat toggle."""
        sync_manager.start()
        
        # Mock the broadcast method
        with patch.object(sync_manager, '_broadcast_message') as mock_broadcast:
            sync_manager.broadcast_cheat_toggle('god_mode', True)
            
            # Should have been called
            assert mock_broadcast.called
            
            # Get the message that was broadcast
            call_args = mock_broadcast.call_args
            message = call_args[0][0]
            
            assert message.message_type == SyncMessageType.CHEAT_TOGGLED
            assert message.cheat_type == 'god_mode'
            assert message.is_active is True
    
    def test_sync_prevents_infinite_loop(self, sync_manager):
        """Test that syncing_cheats prevents infinite loops."""
        sync_manager._syncing_cheats.add('god_mode')
        
        # Try to broadcast while syncing
        with patch.object(sync_manager, '_broadcast_message') as mock_broadcast:
            sync_manager.broadcast_cheat_toggle('god_mode', True)
            
            # Should still broadcast but mark as syncing
            assert 'god_mode' in sync_manager._syncing_cheats
    
    def test_handle_message_from_self(self, sync_manager):
        """Test that messages from self are ignored."""
        message = SyncMessage(
            message_type=SyncMessageType.CHEAT_TOGGLED,
            cheat_type='test_cheat',
            is_active=True,
            instance_id='test_instance',  # Same as self
        )
        
        # Should not raise or do anything
        sync_manager._handle_message(message)
    
    def test_handle_disconnect_message(self, sync_manager):
        """Test handling disconnect messages."""
        # Add a known peer
        sync_manager._known_peers.add('peer123')
        
        # Receive disconnect from that peer
        message = SyncMessage(
            message_type=SyncMessageType.DISCONNECT,
            instance_id='peer123',
        )
        
        sync_manager._handle_message(message)
        
        # Peer should be removed
        assert 'peer123' not in sync_manager._known_peers
    
    def test_handle_message_with_ignore_override(self, sync_manager):
        """Test that ignore overrides prevent remote toggles."""
        sync_manager.add_ignore_override('god_mode')
        
        callback = Mock()
        sync_manager.set_remote_toggle_callback(callback)
        
        message = SyncMessage(
            message_type=SyncMessageType.CHEAT_TOGGLED,
            cheat_type='god_mode',
            is_active=True,
            instance_id='other_instance',
        )
        
        sync_manager._handle_message(message)
        
        # Callback should not be called
        callback.assert_not_called()
    
    def test_get_stats(self, sync_manager):
        """Test getting sync manager statistics."""
        sync_manager._known_peers.add('peer1')
        sync_manager._known_peers.add('peer2')
        sync_manager._messages_sent = 10
        sync_manager._messages_received = 5
        
        stats = sync_manager.get_stats()
        
        assert stats['instance_id'] == 'test_instance'
        assert len(stats['known_peers']) == 2
        assert stats['messages_sent'] == 10
        assert stats['messages_received'] == 5
        assert stats['is_running'] is False
    
    def test_peer_count(self, sync_manager):
        """Test getting peer count."""
        assert sync_manager.get_peer_count() == 0
        
        sync_manager._known_peers.add('peer1')
        sync_manager._known_peers.add('peer2')
        sync_manager._known_peers.add('peer3')
        
        assert sync_manager.get_peer_count() == 3


class TestSyncMessageTypes:
    """Test all sync message types."""
    
    def test_cheat_toggled_message(self):
        """Test CHEAT_TOGGLED message type."""
        message = SyncMessage(
            message_type=SyncMessageType.CHEAT_TOGGLED,
            cheat_type='infinite_gold',
            is_active=True,
        )
        
        assert message.message_type == SyncMessageType.CHEAT_TOGGLED
    
    def test_heartbeat_message(self):
        """Test HEARTBEAT message type."""
        message = SyncMessage(
            message_type=SyncMessageType.HEARTBEAT,
            instance_id='test',
        )
        
        assert message.message_type == SyncMessageType.HEARTBEAT
    
    def test_disconnect_message(self):
        """Test DISCONNECT message type."""
        message = SyncMessage(
            message_type=SyncMessageType.DISCONNECT,
            instance_id='test',
        )
        
        assert message.message_type == SyncMessageType.DISCONNECT


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
