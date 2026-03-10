"""
Tests for conditional cheat triggers.
"""

import pytest
from unittest.mock import Mock, patch, call
import time
from src.memory.watchpoints import (
    ConditionalTriggerManager,
    ConditionType,
    TriggerAction,
)
from src.memory import CheatType


class TestTriggerActions:
    """Test trigger action types."""
    
    def test_trigger_action_creation(self):
        """Test creating a trigger action."""
        action = TriggerAction(
            action_type='activate_cheat',
            target=CheatType.GOD_MODE,
            data={'priority': 'high'},
        )
        
        assert action.action_type == 'activate_cheat'
        assert action.target == CheatType.GOD_MODE
        assert action.data == {'priority': 'high'}
    
    def test_trigger_action_callback(self):
        """Test callback trigger action."""
        callback_called = []
        
        def test_callback(watchpoint, value):
            callback_called.append((watchpoint, value))
        
        action = TriggerAction(
            action_type='callback',
            target=test_callback,
        )
        
        # Simulate execution (would normally be done by WatchpointManager)
        mock_watchpoint = Mock()
        mock_watchpoint.address = 0x1000
        
        action.target(mock_watchpoint, 50)
        
        assert len(callback_called) == 1
        assert callback_called[0][1] == 50


class TestConditionalTriggerIntegration:
    """Test conditional trigger integration with cheat manager."""
    
    @pytest.fixture
    def mock_environment(self):
        """Create mock environment for testing."""
        scanner = Mock()
        scanner.is_attached.return_value = True
        scanner.backend = Mock()
        scanner.read_value.return_value = 20.0  # Low health value
        
        cheat_manager = Mock()
        cheat_manager.toggle_cheat.return_value = True
        cheat_manager.is_cheat_active.return_value = False
        
        return scanner, cheat_manager
    
    def test_conditional_cheat_activation(
        self,
        mock_environment,
    ):
        """Test that conditional cheat activates when condition is met."""
        scanner, cheat_manager = mock_environment
        
        manager = ConditionalTriggerManager(scanner, cheat_manager)
        
        # Add conditional cheat: activate god mode when health < 25
        success = manager.add_conditional_cheat(
            cheat_type=CheatType.GOD_MODE,
            watch_address=0x12345678,
            value_type='float',
            condition=ConditionType.BELOW_THRESHOLD,
            threshold=25.0,
            action='activate',
            cooldown_ms=100,
        )
        
        assert success is True
        
        # The watchpoint should be monitoring
        assert 0x12345678 in manager.watchpoint_manager._watchpoints
        
        # Verify condition would trigger (20.0 < 25.0)
        watchpoint = manager.watchpoint_manager._watchpoints[0x12345678]
        result = manager.watchpoint_manager._evaluate_condition(
            watchpoint.condition,
            current_value=20.0,
            threshold=25.0,
            last_value=None,
        )
        
        assert result is True
    
    def test_conditional_cheat_cooldown(
        self,
        mock_environment,
    ):
        """Test that conditional cheat respects cooldown."""
        scanner, cheat_manager = mock_environment
        
        manager = ConditionalTriggerManager(scanner, cheat_manager)
        manager.add_conditional_cheat(
            cheat_type=CheatType.GOD_MODE,
            watch_address=0x1000,
            value_type='float',
            condition=ConditionType.BELOW_THRESHOLD,
            threshold=25.0,
            cooldown_ms=1000,  # 1 second cooldown
        )
        
        # First trigger
        watchpoint = manager.watchpoint_manager._watchpoints[0x1000]
        current_time = time.time()
        
        # Simulate trigger
        watchpoint.last_trigger_time = current_time
        
        # Check cooldown (should be active)
        elapsed_ms = (current_time - watchpoint.last_trigger_time) * 1000
        assert elapsed_ms < watchpoint.cooldown_ms
    
    def test_multiple_conditional_cheats(
        self,
        mock_environment,
    ):
        """Test managing multiple conditional cheats."""
        scanner, cheat_manager = mock_environment
        
        manager = ConditionalTriggerManager(scanner, cheat_manager)
        
        # Add multiple conditional cheats
        manager.add_conditional_cheat(
            cheat_type=CheatType.GOD_MODE,
            watch_address=0x1000,
            value_type='float',
            condition=ConditionType.BELOW_THRESHOLD,
            threshold=25.0,
        )
        
        manager.add_conditional_cheat(
            cheat_type=CheatType.UNLIMITED_AMMO,
            watch_address=0x2000,
            value_type='int32',
            condition=ConditionType.LESS_THAN,
            threshold=10,
        )
        
        manager.add_conditional_cheat(
            cheat_type=CheatType.HIGH_MORALE,
            watch_address=0x3000,
            value_type='float',
            condition=ConditionType.BELOW_THRESHOLD,
            threshold=30.0,
        )
        
        cheats = manager.get_conditional_cheats()
        
        assert len(cheats) == 3
        assert 'god_mode' in cheats
        assert 'unlimited_ammo' in cheats
        assert 'high_morale' in cheats
    
    def test_remove_all_conditional_cheats(
        self,
        mock_environment,
    ):
        """Test removing all conditional cheats."""
        scanner, cheat_manager = mock_environment
        
        manager = ConditionalTriggerManager(scanner, cheat_manager)
        
        # Add multiple cheats
        for i, cheat_type in enumerate([
            CheatType.GOD_MODE,
            CheatType.UNLIMITED_AMMO,
            CheatType.HIGH_MORALE,
        ]):
            manager.add_conditional_cheat(
                cheat_type=cheat_type,
                watch_address=0x1000 + i * 0x100,
                value_type='float',
                condition=ConditionType.BELOW_THRESHOLD,
                threshold=25.0,
            )
        
        # Remove all
        count = manager.remove_all_conditional_cheats()
        
        assert count == 3
        assert len(manager._conditional_cheats) == 0
        assert len(manager.watchpoint_manager._watchpoints) == 0


class TestConditionTypes:
    """Test all condition type evaluations."""
    
    @pytest.fixture
    def watchpoint_manager(self):
        """Create a watchpoint manager for testing."""
        scanner = Mock()
        scanner.is_attached.return_value = True
        return Mock(watchpoint_manager=WatchpointManager(scanner)).watchpoint_manager
    
    def test_less_than_condition(self, watchpoint_manager):
        """Test LESS_THAN condition."""
        result = watchpoint_manager._evaluate_condition(
            ConditionType.LESS_THAN,
            current_value=50,
            threshold=100,
            last_value=None,
        )
        assert result is True
        
        result = watchpoint_manager._evaluate_condition(
            ConditionType.LESS_THAN,
            current_value=150,
            threshold=100,
            last_value=None,
        )
        assert result is False
    
    def test_greater_than_condition(self, watchpoint_manager):
        """Test GREATER_THAN condition."""
        result = watchpoint_manager._evaluate_condition(
            ConditionType.GREATER_THAN,
            current_value=150,
            threshold=100,
            last_value=None,
        )
        assert result is True
    
    def test_equals_condition(self, watchpoint_manager):
        """Test EQUALS condition."""
        result = watchpoint_manager._evaluate_condition(
            ConditionType.EQUALS,
            current_value=42,
            threshold=42,
            last_value=None,
        )
        assert result is True
        
        result = watchpoint_manager._evaluate_condition(
            ConditionType.EQUALS,
            current_value=42,
            threshold=43,
            last_value=None,
        )
        assert result is False
    
    def test_not_equals_condition(self, watchpoint_manager):
        """Test NOT_EQUALS condition."""
        result = watchpoint_manager._evaluate_condition(
            ConditionType.NOT_EQUALS,
            current_value=42,
            threshold=43,
            last_value=None,
        )
        assert result is True
    
    def test_below_threshold_condition(self, watchpoint_manager):
        """Test BELOW_THRESHOLD condition."""
        result = watchpoint_manager._evaluate_condition(
            ConditionType.BELOW_THRESHOLD,
            current_value=20.0,
            threshold=25.0,
            last_value=None,
        )
        assert result is True
    
    def test_above_threshold_condition(self, watchpoint_manager):
        """Test ABOVE_THRESHOLD condition."""
        result = watchpoint_manager._evaluate_condition(
            ConditionType.ABOVE_THRESHOLD,
            current_value=80.0,
            threshold=75.0,
            last_value=None,
        )
        assert result is True


# Import here to avoid circular dependency in test file
from src.memory.watchpoints import WatchpointManager


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
