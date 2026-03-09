"""
Tests for the event system.
"""

import os
import sys
from pathlib import Path
from unittest.mock import Mock

import pytest
import psutil

# Patch psutil._common.pmmap if missing (some psutil versions lack it)
if not hasattr(psutil._common, 'pmmap'):
    psutil._common.pmmap = type('pmmap', (), {})

# Ensure src is importable
sys.path.insert(0, str(Path(__file__).parent.parent))


class TestEvents:
    """Tests for the event system."""

    def test_event_emitter_singleton(self):
        from src.utils.events import EventEmitter
        ee1 = EventEmitter()
        ee2 = EventEmitter()
        assert ee1 is ee2

    def test_event_subscription_and_emit(self):
        from src.utils.events import EventEmitter, EventType
        ee = EventEmitter()
        received = []

        def handler(event):
            received.append(event)

        ee.on(EventType.CHEAT_ACTIVATED, handler)
        ee.emit(EventType.CHEAT_ACTIVATED, data={'test': 'value'})

        assert len(received) >= 1
        assert received[-1].data['test'] == 'value'

    def test_event_once(self):
        from src.utils.events import EventEmitter, EventType
        ee = EventEmitter()
        count = [0]

        def handler(event):
            count[0] += 1

        ee.once(EventType.STATUS_CHANGED, handler)
        ee.emit(EventType.STATUS_CHANGED)
        ee.emit(EventType.STATUS_CHANGED)
        assert count[0] == 1

    def test_event_priority_ordering(self):
        from src.utils.events import EventEmitter, EventType
        ee = EventEmitter()
        order = []

        def low(event): order.append('low')
        def high(event): order.append('high')

        ee.on(EventType.ERROR_OCCURRED, low, priority=1)
        ee.on(EventType.ERROR_OCCURRED, high, priority=10)
        ee.emit(EventType.ERROR_OCCURRED)

        assert order == ['high', 'low']

    def test_event_off(self):
        from src.utils.events import EventEmitter, EventType
        ee = EventEmitter()
        handler = Mock()
        ee.on(EventType.FILE_LOADED, handler)
        removed = ee.off(EventType.FILE_LOADED, handler)
        assert removed >= 1
