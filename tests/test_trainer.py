"""
Tests for trainer cheats and hotkey manager.
"""

import os
import sys
from pathlib import Path
from unittest.mock import Mock, MagicMock, patch, PropertyMock

import pytest
import psutil

# Patch psutil._common.pmmap if missing (some psutil versions lack it)
if not hasattr(psutil._common, 'pmmap'):
    psutil._common.pmmap = type('pmmap', (), {})

# Ensure src is importable
sys.path.insert(0, str(Path(__file__).parent.parent))


class TestTrainerCheats:
    """Tests for trainer cheat system."""

    def test_init(self):
        from src.memory import ProcessManager, MemoryScanner, CheatManager
        from src.trainer import TrainerCheats
        pm = ProcessManager()
        scanner = MemoryScanner(pm)
        cheat_manager = CheatManager(scanner)
        trainer = TrainerCheats(cheat_manager)
        assert trainer is not None
        assert len(trainer.cheat_status) > 0

    def test_get_summary(self):
        from src.memory import ProcessManager, MemoryScanner, CheatManager
        from src.trainer import TrainerCheats
        pm = ProcessManager()
        scanner = MemoryScanner(pm)
        cheat_manager = CheatManager(scanner)
        trainer = TrainerCheats(cheat_manager)
        summary = trainer.get_summary()
        assert isinstance(summary, str)
        assert len(summary) > 0

    def test_get_all_cheat_statuses(self):
        from src.memory import ProcessManager, MemoryScanner, CheatManager
        from src.trainer import TrainerCheats
        pm = ProcessManager()
        scanner = MemoryScanner(pm)
        cheat_manager = CheatManager(scanner)
        trainer = TrainerCheats(cheat_manager)
        statuses = trainer.get_all_cheat_statuses()
        assert isinstance(statuses, dict)
        assert all(isinstance(v, bool) for v in statuses.values())


class TestHotkeyManager:
    """Tests for the hotkey manager."""

    def test_init(self):
        from src.trainer.hotkeys import HotkeyManager
        hm = HotkeyManager()
        assert hm is not None
        assert hm.bindings == {}

    @patch('src.trainer.hotkeys.PYNPUT_AVAILABLE', True)
    def test_register_hotkey_with_pynput(self):
        from src.trainer.hotkeys import HotkeyManager
        hm = HotkeyManager()
        callback = Mock()
        result = hm.register_hotkey('f1', callback, 'Test hotkey')
        assert result is True
        assert len(hm.bindings) == 1

    @patch('src.trainer.hotkeys.PYNPUT_AVAILABLE', True)
    def test_unregister_hotkey(self):
        from src.trainer.hotkeys import HotkeyManager
        hm = HotkeyManager()
        callback = Mock()
        hm.register_hotkey('f1', callback, 'Test hotkey')
        binding_id = list(hm.bindings.keys())[0]
        result = hm.unregister_hotkey(binding_id)
        assert result is True
        assert len(hm.bindings) == 0

    @patch('src.trainer.hotkeys.PYNPUT_AVAILABLE', True)
    def test_get_registered_hotkeys(self):
        from src.trainer.hotkeys import HotkeyManager
        hm = HotkeyManager()
        callback = Mock()
        hm.register_hotkey('f2', callback, 'Another hotkey')
        hotkeys = hm.get_registered_hotkeys()
        assert len(hotkeys) == 1
        assert hotkeys[0]['key'] == 'f2'

    def test_register_without_pynput_returns_false(self):
        """Verify graceful failure when pynput is missing."""
        from src.trainer.hotkeys import HotkeyManager, PYNPUT_AVAILABLE
        if PYNPUT_AVAILABLE:
            pytest.skip("pynput is installed")
        hm = HotkeyManager()
        result = hm.register_hotkey('f1', Mock(), 'Test')
        assert result is False
