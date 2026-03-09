"""
Exception hierarchy for Napoleon Total War Cheat Engine.
Provides structured error handling across all modules.
"""


class CheatEngineError(Exception):
    """Base exception for all cheat engine errors."""
    def __init__(self, message: str, details: dict = None):
        super().__init__(message)
        self.details = details or {}


class ProcessError(CheatEngineError):
    """Errors related to process management."""
    pass

class ProcessNotFoundError(ProcessError):
    """Game process not found."""
    pass

class ProcessAccessDeniedError(ProcessError):
    """Insufficient permissions to access process."""
    pass

class ProcessDetachedError(ProcessError):
    """Operation attempted while not attached to process."""
    pass


class MemoryError(CheatEngineError):
    """Errors related to memory operations."""
    pass

class MemoryReadError(MemoryError):
    """Failed to read memory."""
    pass

class MemoryWriteError(MemoryError):
    """Failed to write memory."""
    pass

class MemoryScanError(MemoryError):
    """Memory scan failed."""
    pass

class MemoryScanTimeoutError(MemoryScanError):
    """Memory scan timed out."""
    pass


class FileError(CheatEngineError):
    """Errors related to file operations."""
    pass

class ESFParseError(FileError):
    """Failed to parse ESF file."""
    pass

class ESFSerializeError(FileError):
    """Failed to serialize ESF data."""
    pass

class PackParseError(FileError):
    """Failed to parse pack file."""
    pass

class PackCorruptError(PackParseError):
    """Pack file is corrupted."""
    pass

class BackupError(FileError):
    """Backup operation failed."""
    pass

class SecurityError(FileError):
    """Security violation detected (path traversal, etc)."""
    pass


class ConfigError(CheatEngineError):
    """Configuration errors."""
    pass

class ConfigLoadError(ConfigError):
    """Failed to load configuration."""
    pass

class ConfigSaveError(ConfigError):
    """Failed to save configuration."""
    pass

class ConfigValidationError(ConfigError):
    """Configuration validation failed."""
    pass


class TrainerError(CheatEngineError):
    """Trainer-related errors."""
    pass

class HotkeyError(TrainerError):
    """Hotkey system error."""
    pass

class CheatActivationError(TrainerError):
    """Failed to activate cheat."""
    pass


class PluginError(CheatEngineError):
    """Plugin system errors."""
    pass

class PluginLoadError(PluginError):
    """Failed to load plugin."""
    pass

class PluginExecutionError(PluginError):
    """Plugin execution failed."""
    pass
