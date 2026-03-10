"""
Tests for memory watchpoints and conditional triggers.
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from src.memory.watchpoints import (
    WatchpointManager,
    ConditionalTriggerManager,
    MemoryWatchpoint,
    TriggerAction,
    ConditionType,
)


class TestMemoryWatchpoint:
    """Test MemoryWatchpoint dataclass."""
    
    def test_create_watchpoint(self):
        """Test creating a watchpoint."""
        watchpoint = MemoryWatchpoint(
            address=0x12345678,
            value_type='int32',
            condition=ConditionType.LESS_THAN,
            threshold=100,
            description="Test watchpoint",
        )
        
        assert watchpoint.address == 0x12345678
        assert watchpoint.value_type == 'int32'
        assert watchpoint.condition == ConditionType.LESS_THAN
        assert watchpoint.threshold == 100
        assert watchpoint.description == "Test watchpoint"
        assert watchpoint.enabled is True
        assert watchpoint.trigger_count == 0
    
    def test_watchpoint_defaults(self):
        """Test watchpoint default values."""
        watchpoint = MemoryWatchpoint(
            address=0x1000,
            value_type='float',
            condition=ConditionType.GREATER_THAN,
            threshold=50.5,
        )
        
        assert watchpoint.cooldown_ms == 100
        assert watchpoint.last_value is None
        assert watchpoint.trigger_count == 0


class TestWatchpointManager:
    """Test WatchpointManager functionality."""
    
    @pytest.fixture
    def mock_scanner(self):
        """Create a mock memory scanner."""
        scanner = Mock()
        scanner.is_attached.return_value = True
        scanner.backend = Mock()
        scanner.read_value.return_value = 50
        return scanner
    
    def test_add_watchpoint(self, mock_scanner):
        """Test adding a watchpoint."""
        manager = WatchpointManager(mock_scanner)
        
        success = manager.add_watchpoint(
            address=0x12345678,
            value_type='int32',
            condition=ConditionType.LESS_THAN,
            threshold=100,
            description="Health watchpoint",
        )
        
        assert success is True
        assert 0x12345678 in manager._watchpoints
        
        watchpoint = manager._watchpoints[0x12345678]
        assert watchpoint.description == "Health watchpoint"
        assert watchpoint.threshold == 100
    
    def test_add_watchpoint_not_attached(self, mock_scanner):
        """Test adding watchpoint when scanner not attached."""
        mock_scanner.is_attached.return_value = False
        manager = WatchpointManager(mock_scanner)
        
        success = manager.add_watchpoint(
            address=0x1000,
            value_type='int32',
            condition=ConditionType.EQUALS,
            threshold=42,
        )
        
        assert success is False
    
    def test_remove_watchpoint(self, mock_scanner):
        """Test removing a watchpoint."""
        manager = WatchpointManager(mock_scanner)
        manager.add_watchpoint(
            address=0x1000,
            value_type='int32',
            condition=ConditionType.EQUALS,
            threshold=100,
        )
        
        success = manager.remove_watchpoint(0x1000)
        
        assert success is True
        assert 0x1000 not in manager._watchpoints
    
    def test_remove_all_watchpoints(self, mock_scanner):
        """Test removing all watchpoints."""
        manager = WatchpointManager(mock_scanner)
        
        # Add multiple watchpoints
        for i in range(5):
            manager.add_watchpoint(
                address=0x1000 + i * 0x100,
                value_type='int32',
                condition=ConditionType.EQUALS,
                threshold=i * 10,
            )
        
        count = manager.remove_all_watchpoints()
        
        assert count == 5
        assert len(manager._watchpoints) == 0
    
    def test_add_action(self, mock_scanner):
        """Test adding an action to a watchpoint."""
        manager = WatchpointManager(mock_scanner)
        manager.add_watchpoint(
            address=0x1000,
            value_type='int32',
            condition=ConditionType.LESS_THAN,
            threshold=50,
        )
        
        action = TriggerAction(
            action_type='activate_cheat',
            target='god_mode',
        )
        
        success = manager.add_action(0x1000, action)
        
        assert success is True
        assert len(manager._actions[0x1000]) == 1
    
    def test_evaluate_condition_less_than(self, mock_scanner):
        """Test LESS_THAN condition evaluation."""
        manager = WatchpointManager(mock_scanner)
        
        result = manager._evaluate_condition(
            ConditionType.LESS_THAN,
            current_value=50,
            threshold=100,
            last_value=None,
        )
        
        assert result is True
        
        result = manager._evaluate_condition(
            ConditionType.LESS_THAN,
            current_value=150,
            threshold=100,
            last_value=None,
        )
        
        assert result is False
    
    def test_evaluate_condition_greater_than(self, mock_scanner):
        """Test GREATER_THAN condition evaluation."""
        manager = WatchpointManager(mock_scanner)
        
        result = manager._evaluate_condition(
            ConditionType.GREATER_THAN,
            current_value=150,
            threshold=100,
            last_value=None,
        )
        
        assert result is True
    
    def test_evaluate_condition_equals(self, mock_scanner):
        """Test EQUALS condition evaluation."""
        manager = WatchpointManager(mock_scanner)
        
        result = manager._evaluate_condition(
            ConditionType.EQUALS,
            current_value=42,
            threshold=42,
            last_value=None,
        )
        
        assert result is True
    
    def test_evaluate_condition_changed(self, mock_scanner):
        """Test CHANGED condition evaluation."""
        manager = WatchpointManager(mock_scanner)
        
        # Value changed
        result = manager._evaluate_condition(
            ConditionType.CHANGED,
            current_value=50,
            threshold=None,
            last_value=40,
        )
        
        assert result is True
        
        # Value unchanged
        result = manager._evaluate_condition(
            ConditionType.CHANGED,
            current_value=50,
            threshold=None,
            last_value=50,
        )
        
        assert result is False
    
    def test_get_stats(self, mock_scanner):
        """Test getting manager statistics."""
        manager = WatchpointManager(mock_scanner)
        
        manager.add_watchpoint(
            address=0x1000,
            value_type='int32',
            condition=ConditionType.EQUALS,
            threshold=100,
        )
        
        stats = manager.get_stats()
        
        assert stats['total_watchpoints'] == 1
        assert stats['enabled_watchpoints'] == 1
        # Note: is_running may be True if auto-start was triggered
        assert 'is_running' in stats
    
    def test_get_watchpoints_list(self, mock_scanner):
        """Test getting watchpoints list."""
        manager = WatchpointManager(mock_scanner)
        
        manager.add_watchpoint(
            address=0x12345678,
            value_type='float',
            condition=ConditionType.BELOW_THRESHOLD,
            threshold=25.5,
            description="Test watchpoint",
        )
        
        watchpoints = manager.get_watchpoints_list()
        
        assert len(watchpoints) == 1
        assert watchpoints[0]['address'] == '0x12345678'
        assert watchpoints[0]['type'] == 'float'
        assert watchpoints[0]['condition'] == 'below_threshold'


class TestConditionalTriggerManager:
    """Test ConditionalTriggerManager functionality."""
    
    @pytest.fixture
    def mock_components(self):
        """Create mock scanner and cheat manager."""
        scanner = Mock()
        scanner.is_attached.return_value = True
        scanner.backend = Mock()
        scanner.read_value.return_value = 50
        
        cheat_manager = Mock()
        
        return scanner, cheat_manager
    
    def test_add_conditional_cheat(self, mock_components):
        """Test adding a conditional cheat trigger."""
        scanner, cheat_manager = mock_components
        
        from src.memory import CheatType
        
        manager = ConditionalTriggerManager(scanner, cheat_manager)
        
        success = manager.add_conditional_cheat(
            cheat_type=CheatType.GOD_MODE,
            watch_address=0x12345678,
            value_type='float',
            condition=ConditionType.BELOW_THRESHOLD,
            threshold=25.0,
            action='activate',
            cooldown_ms=1000,
        )
        
        assert success is True
        assert 'god_mode' in manager._conditional_cheats
    
    def test_remove_conditional_cheat(self, mock_components):
        """Test removing a conditional cheat."""
        scanner, cheat_manager = mock_components
        
        from src.memory import CheatType
        
        manager = ConditionalTriggerManager(scanner, cheat_manager)
        manager.add_conditional_cheat(
            cheat_type=CheatType.GOD_MODE,
            watch_address=0x1000,
            value_type='float',
            condition=ConditionType.BELOW_THRESHOLD,
            threshold=25.0,
        )
        
        success = manager.remove_conditional_cheat(CheatType.GOD_MODE)
        
        assert success is True
        assert 'god_mode' not in manager._conditional_cheats
    
    def test_get_conditional_cheats(self, mock_components):
        """Test getting conditional cheats."""
        scanner, cheat_manager = mock_components
        
        from src.memory import CheatType
        
        manager = ConditionalTriggerManager(scanner, cheat_manager)
        manager.add_conditional_cheat(
            cheat_type=CheatType.GOD_MODE,
            watch_address=0x1000,
            value_type='float',
            condition=ConditionType.BELOW_THRESHOLD,
            threshold=25.0,
        )
        
        cheats = manager.get_conditional_cheats()
        
        assert 'god_mode' in cheats
        assert cheats['god_mode']['condition'] == 'below_threshold'


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
