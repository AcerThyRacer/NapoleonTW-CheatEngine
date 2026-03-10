"""
Runtime trainer module for Napoleon Total War.
Provides hotkey-activated cheats and real-time memory manipulation.
"""

from .hotkeys import HotkeyManager, CheatHotkeys
from .cheats import TrainerCheats
from .background import BackgroundTrainer
from .overlay import CheatOverlay
from .effects_overlay import EffectsOverlay

__all__ = [
    'HotkeyManager',
    'CheatHotkeys',
    'TrainerCheats',
    'BackgroundTrainer',
    'CheatOverlay',
    'EffectsOverlay',
]
