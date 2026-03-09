"""
GUI module for Napoleon Total War Cheat Engine.
Provides PyQt6-based user interface.
"""

from importlib import import_module

_LAZY_EXPORTS = {
    'MainWindow': '.main_window',
    'MemoryScannerTab': '.memory_tab',
    'FileEditorTab': '.file_editor_tab',
    'TrainerTab': '.trainer_tab',
    'SettingsTab': '.settings_tab',
}


def __getattr__(name):
    """Lazily import GUI classes to avoid importing the full stack unnecessarily."""
    module_name = _LAZY_EXPORTS.get(name)
    if module_name is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

    module = import_module(module_name, __name__)
    return getattr(module, name)


__all__ = list(_LAZY_EXPORTS)
