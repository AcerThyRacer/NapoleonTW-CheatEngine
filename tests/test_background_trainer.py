"""
Tests for background trainer mode.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock, call
import time
from src.trainer.background import BackgroundTrainer
from src.utils.game_state import GameMode


class TestBackgroundTrainer:
    """Test BackgroundTrainer functionality."""
    
    @pytest.fixture
    def background_trainer(self):
        """Create a background trainer for testing."""
        mock_pm = Mock()
        mock_scanner = Mock()
        mock_cheat_manager = Mock()
        mock_hotkey_manager = Mock()
        mock_trainer_cheats = Mock()
        mock_game_monitor = Mock()
        
        with patch('src.trainer.background.ProcessManager', return_value=mock_pm), \
             patch('src.trainer.background.MemoryScanner', return_value=mock_scanner), \
             patch('src.trainer.background.CheatManager', return_value=mock_cheat_manager), \
             patch('src.trainer.background.HotkeyManager', return_value=mock_hotkey_manager), \
             patch('src.trainer.background.TrainerCheats', return_value=mock_trainer_cheats), \
             patch('src.trainer.background.GameStateMonitor', return_value=mock_game_monitor):
            
            trainer = BackgroundTrainer()
            yield trainer
            trainer.stop()
    
    def test_initialization(self, background_trainer):
        """Test background trainer initialization."""
        assert background_trainer._running is False
        assert background_trainer._attached is False
        assert background_trainer._retry_count == 0
        # Components are initialized in _init_components which is called in start()
        # So they should be None initially
        assert background_trainer.process_manager is None
        assert background_trainer.scanner is None
    
    def test_start_stop(self, background_trainer):
        """Test starting and stopping the trainer."""
        # Mock the main loop to exit immediately
        with patch.object(background_trainer, '_run_main_loop') as mock_loop:
            background_trainer.start()
            
            assert background_trainer._running is True
            assert mock_loop.called
            
            background_trainer.stop()
            
            assert background_trainer._running is False
    
    def test_attach_to_game(self, background_trainer):
        """Test attaching to game process."""
        background_trainer.scanner = Mock()
        background_trainer.scanner.attach.return_value = True
        background_trainer.process_manager = Mock()
        background_trainer.process_manager.process_name = 'napoleon.exe'
        background_trainer.process_manager.pid = 12345
        
        success = background_trainer._try_attach()
        
        assert success is True
        assert background_trainer._attached is True
        assert background_trainer._retry_count == 0
    
    def test_attach_retry_logic(self, background_trainer):
        """Test attach retry logic."""
        background_trainer.scanner = Mock()
        background_trainer.scanner.attach.return_value = False
        
        # First attempt
        success = background_trainer._try_attach()
        
        assert success is False
        assert background_trainer._retry_count == 1
        
        # Second attempt
        success = background_trainer._try_attach()
        
        assert success is False
        assert background_trainer._retry_count == 2
    
    def test_detach_from_game(self, background_trainer):
        """Test detaching from game process."""
        background_trainer._attached = True
        
        # Mock cheat manager and scanner
        background_trainer.cheat_manager = Mock()
        background_trainer.cheat_manager.deactivate_all_cheats.return_value = None
        background_trainer.scanner = Mock()
        
        background_trainer._try_detach()
        
        assert background_trainer._attached is False
        background_trainer.cheat_manager.deactivate_all_cheats.assert_called_once()
        background_trainer.scanner.detach.assert_called_once()
    
    def test_on_game_started(self, background_trainer):
        """Test game started callback."""
        background_trainer._try_attach = Mock(return_value=True)
        
        background_trainer._on_game_started(12345)
        
        assert background_trainer._retry_count == 0
        background_trainer._try_attach.assert_called_once()
    
    def test_on_game_stopped(self, background_trainer):
        """Test game stopped callback."""
        background_trainer._attached = True
        background_trainer._try_detach = Mock()
        
        background_trainer._on_game_stopped()
        
        background_trainer._try_detach.assert_called_once()
        assert background_trainer._last_game_mode is None
    
    def test_on_mode_changed(self, background_trainer):
        """Test game mode changed callback."""
        background_trainer._try_attach = Mock(return_value=True)
        background_trainer._attached = False
        
        # Mode changed to campaign
        background_trainer._on_mode_changed(GameMode.LOADING, GameMode.CAMPAIGN)
        
        assert background_trainer._last_game_mode == GameMode.CAMPAIGN
        background_trainer._try_attach.assert_called_once()
    
    def test_get_state(self, background_trainer):
        """Test getting trainer state."""
        background_trainer._running = True
        background_trainer._attached = True
        background_trainer._retry_count = 2
        background_trainer._last_game_mode = GameMode.CAMPAIGN
        background_trainer._active_cheats = {'god_mode': True}
        
        state = background_trainer.get_state()
        
        assert state['running'] is True
        assert state['attached'] is True
        assert state['game_mode'] == 'campaign'
        assert state['retry_count'] == 2
        assert state['active_cheats'] == {'god_mode': True}
    
    def test_open_gui(self, background_trainer):
        """Test opening GUI on demand."""
        background_trainer._running = True
        
        with patch('threading.Thread') as mock_thread:
            success = background_trainer.open_gui()
            
            assert success is True
            mock_thread.assert_called_once()
    
    def test_open_gui_when_not_running(self, background_trainer):
        """Test opening GUI when trainer not running."""
        background_trainer._running = False
        
        success = background_trainer.open_gui()
        
        assert success is False
    
    def test_main_loop_retry(self, background_trainer):
        """Test main loop retry logic."""
        background_trainer._running = True
        background_trainer.game_monitor = Mock()
        background_trainer.game_monitor.is_running = True
        background_trainer._attached = False
        background_trainer._try_attach = Mock(return_value=False)
        
        # Simulate one iteration of main loop by calling it directly
        # Just verify it doesn't crash
        try:
            background_trainer._run_main_loop()
        except Exception:
            pass  # Expected since we're mocking
        
        # Should have tried to attach
        assert background_trainer._try_attach.called
    
    def test_hotkey_compatibility_warning(self):
        """Test hotkey compatibility warning check."""
        mock_pm = Mock()
        mock_scanner = Mock()
        mock_cheat_manager = Mock()
        mock_hotkey_manager = Mock()
        mock_trainer_cheats = Mock()
        mock_game_monitor = Mock()
        
        with patch('src.trainer.background.get_hotkey_compatibility_warning') as mock_warning:
            mock_warning.return_value = "Wayland warning"
            
            with patch('src.trainer.background.ProcessManager', return_value=mock_pm), \
                 patch('src.trainer.background.MemoryScanner', return_value=mock_scanner), \
                 patch('src.trainer.background.CheatManager', return_value=mock_cheat_manager), \
                 patch('src.trainer.background.HotkeyManager', return_value=mock_hotkey_manager), \
                 patch('src.trainer.background.TrainerCheats', return_value=mock_trainer_cheats), \
                 patch('src.trainer.background.GameStateMonitor', return_value=mock_game_monitor):
                
                trainer = BackgroundTrainer()
                
                # Warning should have been called
                mock_warning.assert_called_once()
    
    def test_component_initialization_failure(self):
        """Test handling component initialization failure."""
        with patch('src.trainer.background.ProcessManager') as mock_pm:
            mock_pm.side_effect = Exception("Initialization failed")
            
            with pytest.raises(Exception):
                # This should fail during __init__
                trainer = BackgroundTrainer()
                # Force initialization
                trainer._init_components()
    
    def test_is_attached(self, background_trainer):
        """Test checking attachment status."""
        background_trainer._attached = True
        
        assert background_trainer.is_attached() is True
        
        background_trainer._attached = False
        
        assert background_trainer.is_attached() is False


class TestBackgroundTrainerIntegration:
    """Test background trainer integration with other components."""
    
    def test_cheat_deactivation_on_detach(self):
        """Test that cheats are deactivated on detach."""
        mock_pm = Mock()
        mock_scanner = Mock()
        mock_cheat_manager = Mock()
        mock_hotkey_manager = Mock()
        mock_trainer_cheats = Mock()
        mock_game_monitor = Mock()
        
        with patch('src.trainer.background.ProcessManager', return_value=mock_pm), \
             patch('src.trainer.background.MemoryScanner', return_value=mock_scanner), \
             patch('src.trainer.background.CheatManager', return_value=mock_cheat_manager), \
             patch('src.trainer.background.HotkeyManager', return_value=mock_hotkey_manager), \
             patch('src.trainer.background.TrainerCheats', return_value=mock_trainer_cheats), \
             patch('src.trainer.background.GameStateMonitor', return_value=mock_game_monitor):
            
            trainer = BackgroundTrainer()
            trainer._attached = True
            
            # Mock cheat manager deactivate
            trainer.cheat_manager.deactivate_all_cheats = Mock()
            
            trainer._try_detach()
            
            trainer.cheat_manager.deactivate_all_cheats.assert_called_once()
    
    def test_game_monitor_callbacks_registered(self):
        """Test that game monitor callbacks are registered on start."""
        with patch('src.trainer.background.ProcessManager'), \
             patch('src.trainer.background.MemoryScanner'), \
             patch('src.trainer.background.CheatManager'), \
             patch('src.trainer.background.HotkeyManager'), \
             patch('src.trainer.background.TrainerCheats'), \
             patch('src.trainer.background.GameStateMonitor') as mock_gm:
            
            trainer = BackgroundTrainer()
            
            mock_monitor_instance = Mock()
            mock_gm.return_value = mock_monitor_instance
            
            with patch.object(trainer, '_run_main_loop'):
                trainer.start()
            
            # Callbacks should be registered
            mock_monitor_instance.set_callbacks.assert_called_once()
            
            # Verify callback functions are passed
            call_kwargs = mock_monitor_instance.set_callbacks.call_args[1]
            assert 'on_game_started' in call_kwargs
            assert 'on_game_stopped' in call_kwargs
            assert 'on_mode_changed' in call_kwargs


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
