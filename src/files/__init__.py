"""
File editing module for Napoleon Total War.
Handles .esf save games, scripting.lua, and configuration files.
"""

from .esf_editor import ESFEditor, ESFNode
from .script_editor import ScriptEditor
from .config_editor import ConfigEditor

__all__ = [
    'ESFEditor',
    'ESFNode',
    'ScriptEditor',
    'ConfigEditor',
]
