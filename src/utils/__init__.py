"""
Utility functions and helpers for Napoleon Total War Cheat Engine.
"""

from .platform import (
    get_platform,
    is_proton,
    get_steam_path,
    get_napoleon_install_path,
    get_save_game_directory,
    get_scripts_directory,
    get_game_data_path,
    check_memory_access_permissions,
    detect_display_server,
    get_hotkey_compatibility_warning,
    normalize_path,
    create_backup,
    get_process_name,
    get_all_possible_process_names,
)

from .events import (
    EventEmitter,
    Event,
    EventType,
    emit_cheat_activated,
    emit_cheat_deactivated,
    emit_error,
)

from .exceptions import (
    CheatEngineError, ProcessError, ProcessNotFoundError, ProcessAccessDeniedError,
    ProcessDetachedError, MemoryReadError, MemoryWriteError, MemoryScanError,
    MemoryScanTimeoutError, FileError, ESFParseError, ESFSerializeError,
    PackParseError, PackCorruptError, BackupError, SecurityError,
    ConfigError, ConfigLoadError, ConfigSaveError, ConfigValidationError,
    TrainerError, HotkeyError, CheatActivationError,
    PluginError, PluginLoadError, PluginExecutionError,
)
from .game_state import GameStateMonitor, GameMode
from .logging_config import setup_logging, get_logger


def format_address(address: int) -> str:
    """
    Format a memory address as a hexadecimal string.
    
    Args:
        address: Memory address as integer
        
    Returns:
        str: Formatted address (e.g., '0x004A5F2C')
    """
    return f"0x{address:08X}"


def parse_address(address_str: str) -> int:
    """
    Parse a memory address from string format.
    
    Args:
        address_str: Address string (e.g., '0x004A5F2C' or '4A5F2C')
        
    Returns:
        int: Memory address as integer
    """
    address_str = address_str.strip().lower()
    if address_str.startswith('0x'):
        return int(address_str, 16)
    return int(address_str, 16)


def format_value(value, value_type: str = '4 Bytes') -> str:
    """
    Format a value based on its type.
    
    Args:
        value: The value to format
        value_type: Type string ('4 Bytes', 'Float', 'Double', etc.)
        
    Returns:
        str: Formatted value string
    """
    if value_type in ['4 Bytes', '2 Bytes', '1 Byte']:
        return str(int(value))
    elif value_type == 'Float':
        return f"{float(value):.6f}"
    elif value_type == 'Double':
        return f"{float(value):.12f}"
    elif value_type == 'String':
        return str(value)
    return str(value)


def validate_value(value_str: str, value_type: str) -> tuple:
    """
    Validate and convert a value string to the appropriate type.
    
    Args:
        value_str: Value as string
        value_type: Type string
        
    Returns:
        tuple: (success: bool, value: converted value or error message)
    """
    try:
        if value_type in ['4 Bytes', '2 Bytes', '1 Byte']:
            return True, int(value_str)
        elif value_type == 'Float':
            return True, float(value_str)
        elif value_type == 'Double':
            return True, float(value_str)
        elif value_type == 'String':
            return True, value_str
        else:
            return False, f"Unknown value type: {value_type}"
    except ValueError as e:
        return False, f"Invalid value: {str(e)}"


__all__ = [
    # Platform utilities
    'get_platform',
    'is_proton',
    'get_steam_path',
    'get_napoleon_install_path',
    'get_save_game_directory',
    'get_scripts_directory',
    'get_game_data_path',
    'check_memory_access_permissions',
    'detect_display_server',
    'get_hotkey_compatibility_warning',
    'normalize_path',
    'create_backup',
    'get_process_name',
    'get_all_possible_process_names',
    
    # General utilities
    'format_address',
    'parse_address',
    'format_value',
    'validate_value',
    
    # Game state
    'GameStateMonitor',
    'GameMode',
]
