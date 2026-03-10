import pytest
import time
import socket
import threading
from unittest.mock import MagicMock, patch

from src.trainer.sync import CheatSyncManager
from src.memory.cheats import CheatType

class MockSocket:
    def __init__(self, *args, **kwargs):
        self.data_queue = []
        self.closed = False
        self.timeout = None

    def bind(self, address):
        self.address = address

    def setsockopt(self, level, optname, value):
        pass

    def recvfrom(self, bufsize):
        if self.closed:
            raise socket.error("Socket closed")

        # Simulate blocking behavior
        start = time.time()
        while not self.data_queue and not self.closed:
            if self.timeout is not None and (time.time() - start) > self.timeout:
                raise socket.timeout("timeout")
            time.sleep(0.01)

        if self.closed:
            raise socket.error("Socket closed")

        if self.data_queue:
            return self.data_queue.pop(0), ('127.0.0.1', 27015)
        return b"", ('127.0.0.1', 27015)

    def sendto(self, data, address):
        pass

    def close(self):
        self.closed = True

    def settimeout(self, timeout):
        self.timeout = timeout

@pytest.fixture
def sync_manager():
    manager = CheatSyncManager(port_start=27015, port_end=27025)
    yield manager
    if manager.running:
        manager.stop()

def test_sync_manager_start_stop(sync_manager):
    assert not sync_manager.running
    assert sync_manager.start()
    assert sync_manager.running

    # Starting again should return True without issues
    assert sync_manager.start()

    sync_manager.stop()
    assert not sync_manager.running
    assert sync_manager._socket is None

def test_sync_manager_override(sync_manager):
    sync_manager.set_override(CheatType.INFINITE_GOLD, True)
    assert sync_manager.is_overridden(CheatType.INFINITE_GOLD)

    sync_manager.set_override(CheatType.INFINITE_GOLD, False)
    assert not sync_manager.is_overridden(CheatType.INFINITE_GOLD)

@patch('socket.socket')
def test_sync_manager_receive_toggle(mock_socket_class, sync_manager):
    mock_sock = MockSocket()
    # We yield MockSocket so bind works
    mock_socket_class.return_value = mock_sock

    callback_called = False
    received_type = None
    received_active = None

    def mock_callback(cheat_type, is_active):
        nonlocal callback_called, received_type, received_active
        callback_called = True
        received_type = cheat_type
        received_active = is_active

    sync_manager.set_callback(mock_callback)
    sync_manager.start()

    # Inject fake network data
    payload = b'{"action": "toggle", "cheat_type": "infinite_gold", "active": true}'
    mock_sock.data_queue.append(payload)

    # Give the thread time to process
    time.sleep(0.1)

    assert callback_called
    assert received_type == CheatType.INFINITE_GOLD
    assert received_active is True

@patch('socket.socket')
def test_sync_manager_receive_overridden(mock_socket_class, sync_manager):
    mock_sock = MockSocket()
    mock_socket_class.return_value = mock_sock

    callback_called = False

    def mock_callback(cheat_type, is_active):
        nonlocal callback_called
        callback_called = True

    sync_manager.set_callback(mock_callback)
    sync_manager.set_override(CheatType.INFINITE_GOLD, True)
    sync_manager.start()

    # Inject fake network data
    payload = b'{"action": "toggle", "cheat_type": "infinite_gold", "active": true}'
    mock_sock.data_queue.append(payload)

    # Give the thread time to process
    time.sleep(0.1)

    # Should be ignored because it's overridden
    assert not callback_called
