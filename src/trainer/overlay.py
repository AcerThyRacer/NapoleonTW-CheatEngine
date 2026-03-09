"""
Overlay display for showing active cheats.
Provides visual feedback during gameplay with Napoleon Total War themed animations.
"""

from __future__ import annotations

import threading
import time
from enum import Enum
from typing import Dict, List, Optional

try:
    from PyQt6.QtWidgets import (
        QWidget, QVBoxLayout, QHBoxLayout, QLabel, QApplication,
        QComboBox, QFrame, QGraphicsOpacityEffect
    )
    from PyQt6.QtCore import (
        Qt, QTimer, QPropertyAnimation, QEasingCurve, QRect, QPoint,
        QParallelAnimationGroup, QSequentialAnimationGroup
    )
    from PyQt6.QtGui import QFont, QColor
    PYQT_AVAILABLE = True
except ImportError:
    PYQT_AVAILABLE = False


class OverlayAnimationStyle(Enum):
    """Napoleon Total War themed animation styles for the overlay."""
    NONE = "none"
    IMPERIAL_MARCH = "imperial_march"
    CANNON_FIRE = "cannon_fire"
    EAGLE_STANDARD = "eagle_standard"
    SMOKE_SCREEN = "smoke_screen"
    BATTLE_FORMATION = "battle_formation"
    CAVALRY_CHARGE = "cavalry_charge"
    NAVAL_BROADSIDE = "naval_broadside"
    VIVE_EMPEREUR = "vive_empereur"
    ARTILLERY_BARRAGE = "artillery_barrage"
    GRAPESHOT = "grapeshot"
    OLD_GUARD = "old_guard"
    RUSSIAN_WINTER = "russian_winter"
    LIGHTNING_STRIKE = "lightning_strike"
    FLAG_WAVE = "flag_wave"
    CANNONBALL_TRAIL = "cannonball_trail"
    MORALE_BOOST = "morale_boost"

    @classmethod
    def display_names(cls) -> Dict[str, str]:
        """Return mapping of enum values to user-friendly display names."""
        return {
            cls.NONE.value: "None (Instant)",
            cls.IMPERIAL_MARCH.value: "⚔️ Imperial March — Slide from right",
            cls.CANNON_FIRE.value: "💥 Cannon Fire — Bounce scale",
            cls.EAGLE_STANDARD.value: "🦅 Eagle Standard — Drop from top",
            cls.SMOKE_SCREEN.value: "🌫️ Smoke Screen — Fade in/out",
            cls.BATTLE_FORMATION.value: "🏰 Battle Formation — Rise from bottom",
            cls.CAVALRY_CHARGE.value: "🐴 Cavalry Charge — Dash from left",
            cls.NAVAL_BROADSIDE.value: "⚓ Naval Broadside — Slide with bounce",
            cls.VIVE_EMPEREUR.value: "👑 Vive l'Empereur — Scale from center",
            cls.ARTILLERY_BARRAGE.value: "🔥 Artillery Barrage — Shake & fade",
            cls.GRAPESHOT.value: "💣 Grapeshot — Rapid multi-bounce",
            cls.OLD_GUARD.value: "🛡️ Old Guard — Slow majestic fade-slide",
            cls.RUSSIAN_WINTER.value: "❄️ Russian Winter — Drift down with fade",
            cls.LIGHTNING_STRIKE.value: "⚡ Lightning Strike — Quick flash",
            cls.FLAG_WAVE.value: "🇫🇷 Flag Wave — French tricolor wave",
            cls.CANNONBALL_TRAIL.value: "💫 Cannonball Trail — Arc with trail",
            cls.MORALE_BOOST.value: "💚 Morale Boost — Pulsing green aura",
        }

    @classmethod
    def preset_definitions(cls) -> Dict[str, Dict[str, str]]:
        """Return curated overlay presets backed by animation styles."""
        return {
            "balanced_command": {
                "name": "Balanced Command",
                "animation": cls.SMOKE_SCREEN.value,
                "description": "A readable default with quick fades that stays out of your way.",
            },
            "shock_assault": {
                "name": "Shock Assault",
                "animation": cls.CAVALRY_CHARGE.value,
                "description": "Fast-moving notifications for aggressive battle pacing.",
            },
            "grand_battery": {
                "name": "Grand Battery",
                "animation": cls.ARTILLERY_BARRAGE.value,
                "description": "Loud battlefield feedback inspired by massed cannon fire.",
            },
            "old_guard": {
                "name": "Old Guard",
                "animation": cls.OLD_GUARD.value,
                "description": "A slower, more stately overlay fit for Napoleon's elite.",
            },
            "winter_campaign": {
                "name": "Winter Campaign",
                "animation": cls.RUSSIAN_WINTER.value,
                "description": "Cold, drifting notifications with a dramatic campaign feel.",
            },
        }

    @classmethod
    def resolve_preset(cls, preset_name: Optional[str]) -> Dict[str, str]:
        """Resolve an overlay preset by name, defaulting to Balanced Command."""
        presets = cls.preset_definitions()
        return presets.get(preset_name or "", presets["balanced_command"])

    @classmethod
    def from_value(cls, value: str) -> 'OverlayAnimationStyle':
        """Get enum member from string value, defaulting to NONE."""
        for member in cls:
            if member.value == value:
                return member
        return cls.NONE


class OverlayAnimationManager:
    """
    Manages Napoleon Total War themed open/close animations for the overlay.
    Each animation style is inspired by a Napoleonic warfare element.
    """

    ANIMATION_DURATION_MS = 400

    def __init__(self, style: OverlayAnimationStyle = OverlayAnimationStyle.SMOKE_SCREEN):
        """
        Initialize animation manager.

        Args:
            style: The animation style to use
        """
        self.style = style
        self._active_group: Optional[QParallelAnimationGroup] = None

    @property
    def animation_style(self) -> OverlayAnimationStyle:
        """Get current animation style."""
        return self.style

    @animation_style.setter
    def animation_style(self, value: OverlayAnimationStyle) -> None:
        """Set animation style."""
        self.style = value

    def animate_open(self, widget: QWidget, target_rect: QRect) -> None:
        """
        Play the opening animation on the widget.

        Args:
            widget: The overlay widget to animate
            target_rect: The final geometry of the widget
        """
        self._stop_active()

        if self.style == OverlayAnimationStyle.NONE:
            widget.setGeometry(target_rect)
            widget.show()
            return

        handler = self._get_handler(opening=True)
        handler(widget, target_rect)

    def animate_close(self, widget: QWidget, callback=None) -> None:
        """
        Play the closing animation on the widget.

        Args:
            widget: The overlay widget to animate
            callback: Optional callable invoked after animation completes
        """
        self._stop_active()

        if self.style == OverlayAnimationStyle.NONE:
            widget.hide()
            if callback:
                callback()
            return

        handler = self._get_handler(opening=False)
        handler(widget, callback)

    def _stop_active(self) -> None:
        """Stop any currently running animation group."""
        if self._active_group is not None:
            self._active_group.stop()
            self._active_group = None

    def _get_handler(self, opening: bool):
        """Return the appropriate animation handler method."""
        handlers = {
            OverlayAnimationStyle.IMPERIAL_MARCH: (
                self._open_imperial_march, self._close_imperial_march),
            OverlayAnimationStyle.CANNON_FIRE: (
                self._open_cannon_fire, self._close_cannon_fire),
            OverlayAnimationStyle.EAGLE_STANDARD: (
                self._open_eagle_standard, self._close_eagle_standard),
            OverlayAnimationStyle.SMOKE_SCREEN: (
                self._open_smoke_screen, self._close_smoke_screen),
            OverlayAnimationStyle.BATTLE_FORMATION: (
                self._open_battle_formation, self._close_battle_formation),
            OverlayAnimationStyle.CAVALRY_CHARGE: (
                self._open_cavalry_charge, self._close_cavalry_charge),
            OverlayAnimationStyle.NAVAL_BROADSIDE: (
                self._open_naval_broadside, self._close_naval_broadside),
            OverlayAnimationStyle.VIVE_EMPEREUR: (
                self._open_vive_empereur, self._close_vive_empereur),
            OverlayAnimationStyle.ARTILLERY_BARRAGE: (
                self._open_artillery_barrage, self._close_artillery_barrage),
            OverlayAnimationStyle.GRAPESHOT: (
                self._open_grapeshot, self._close_grapeshot),
            OverlayAnimationStyle.OLD_GUARD: (
                self._open_old_guard, self._close_old_guard),
            OverlayAnimationStyle.RUSSIAN_WINTER: (
                self._open_russian_winter, self._close_russian_winter),
            OverlayAnimationStyle.LIGHTNING_STRIKE: (
                self._open_lightning_strike, self._close_lightning_strike),
            OverlayAnimationStyle.FLAG_WAVE: (
                self._open_flag_wave, self._close_flag_wave),
            OverlayAnimationStyle.CANNONBALL_TRAIL: (
                self._open_cannonball_trail, self._close_cannonball_trail),
            OverlayAnimationStyle.MORALE_BOOST: (
                self._open_morale_boost, self._close_morale_boost),
        }
        pair = handlers.get(self.style, (self._open_smoke_screen, self._close_smoke_screen))
        return pair[0] if opening else pair[1]

    # ── Helpers ──────────────────────────────────────────────

    def _ensure_opacity_effect(self, widget: QWidget) -> QGraphicsOpacityEffect:
        """Ensure widget has an opacity effect and return it."""
        effect = widget.graphicsEffect()
        if not isinstance(effect, QGraphicsOpacityEffect):
            effect = QGraphicsOpacityEffect(widget)
            widget.setGraphicsEffect(effect)
        return effect

    def _make_geometry_anim(self, widget, start, end, duration=None, curve=None):
        duration = duration or self.ANIMATION_DURATION_MS
        if curve is None:
            curve = QEasingCurve.Type.OutCubic
        anim = QPropertyAnimation(widget, b"geometry")
        anim.setDuration(duration)
        anim.setStartValue(start)
        anim.setEndValue(end)
        anim.setEasingCurve(curve)
        return anim

    def _make_opacity_anim(self, effect, start, end, duration=None, curve=None):
        duration = duration or self.ANIMATION_DURATION_MS
        if curve is None:
            curve = QEasingCurve.Type.OutCubic
        anim = QPropertyAnimation(effect, b"opacity")
        anim.setDuration(duration)
        anim.setStartValue(start)
        anim.setEndValue(end)
        anim.setEasingCurve(curve)
        return anim

    def _run_open(self, widget, group):
        self._active_group = group
        widget.show()
        group.start()

    def _run_close(self, widget, group, callback=None):
        self._active_group = group
        def _on_done():
            widget.hide()
            self._active_group = None
            if callback:
                callback()
        group.finished.connect(_on_done)
        group.start()

    # ── 1. Imperial March — slide from right ─────────────────

    def _open_imperial_march(self, widget, target):
        start = QRect(target.x() + 400, target.y(), target.width(), target.height())
        widget.setGeometry(start)
        effect = self._ensure_opacity_effect(widget)
        effect.setOpacity(0.0)
        group = QParallelAnimationGroup()
        group.addAnimation(self._make_geometry_anim(widget, start, target, curve=QEasingCurve.Type.OutQuart))
        group.addAnimation(self._make_opacity_anim(effect, 0.0, 1.0))
        self._run_open(widget, group)

    def _close_imperial_march(self, widget, callback=None):
        rect = widget.geometry()
        end = QRect(rect.x() + 400, rect.y(), rect.width(), rect.height())
        effect = self._ensure_opacity_effect(widget)
        group = QParallelAnimationGroup()
        group.addAnimation(self._make_geometry_anim(widget, rect, end, curve=QEasingCurve.Type.InQuart))
        group.addAnimation(self._make_opacity_anim(effect, 1.0, 0.0))
        self._run_close(widget, group, callback)

    # ── 2. Cannon Fire — bounce scale ────────────────────────

    def _open_cannon_fire(self, widget, target):
        cx, cy = target.x() + target.width() // 2, target.y() + target.height() // 2
        start = QRect(cx, cy, 0, 0)
        widget.setGeometry(start)
        effect = self._ensure_opacity_effect(widget)
        effect.setOpacity(1.0)
        anim = self._make_geometry_anim(widget, start, target, curve=QEasingCurve.Type.OutBounce)
        group = QParallelAnimationGroup()
        group.addAnimation(anim)
        self._run_open(widget, group)

    def _close_cannon_fire(self, widget, callback=None):
        rect = widget.geometry()
        cx, cy = rect.x() + rect.width() // 2, rect.y() + rect.height() // 2
        end = QRect(cx, cy, 0, 0)
        anim = self._make_geometry_anim(widget, rect, end, curve=QEasingCurve.Type.InBack)
        group = QParallelAnimationGroup()
        group.addAnimation(anim)
        self._run_close(widget, group, callback)

    # ── 3. Eagle Standard — drop from top ────────────────────

    def _open_eagle_standard(self, widget, target):
        start = QRect(target.x(), target.y() - 500, target.width(), target.height())
        widget.setGeometry(start)
        effect = self._ensure_opacity_effect(widget)
        effect.setOpacity(1.0)
        anim = self._make_geometry_anim(widget, start, target, curve=QEasingCurve.Type.OutBounce)
        group = QParallelAnimationGroup()
        group.addAnimation(anim)
        self._run_open(widget, group)

    def _close_eagle_standard(self, widget, callback=None):
        rect = widget.geometry()
        end = QRect(rect.x(), rect.y() - 500, rect.width(), rect.height())
        effect = self._ensure_opacity_effect(widget)
        group = QParallelAnimationGroup()
        group.addAnimation(self._make_geometry_anim(widget, rect, end, curve=QEasingCurve.Type.InQuad))
        group.addAnimation(self._make_opacity_anim(effect, 1.0, 0.0))
        self._run_close(widget, group, callback)

    # ── 4. Smoke Screen — fade in/out ────────────────────────

    def _open_smoke_screen(self, widget, target):
        widget.setGeometry(target)
        effect = self._ensure_opacity_effect(widget)
        effect.setOpacity(0.0)
        anim = self._make_opacity_anim(effect, 0.0, 1.0, curve=QEasingCurve.Type.InOutQuad)
        group = QParallelAnimationGroup()
        group.addAnimation(anim)
        self._run_open(widget, group)

    def _close_smoke_screen(self, widget, callback=None):
        effect = self._ensure_opacity_effect(widget)
        anim = self._make_opacity_anim(effect, 1.0, 0.0, curve=QEasingCurve.Type.InOutQuad)
        group = QParallelAnimationGroup()
        group.addAnimation(anim)
        self._run_close(widget, group, callback)

    # ── 5. Battle Formation — rise from bottom ───────────────

    def _open_battle_formation(self, widget, target):
        screen = QApplication.primaryScreen().geometry()
        start = QRect(target.x(), screen.height(), target.width(), target.height())
        widget.setGeometry(start)
        effect = self._ensure_opacity_effect(widget)
        effect.setOpacity(0.3)
        group = QParallelAnimationGroup()
        group.addAnimation(self._make_geometry_anim(widget, start, target, curve=QEasingCurve.Type.OutCubic))
        group.addAnimation(self._make_opacity_anim(effect, 0.3, 1.0))
        self._run_open(widget, group)

    def _close_battle_formation(self, widget, callback=None):
        rect = widget.geometry()
        screen = QApplication.primaryScreen().geometry()
        end = QRect(rect.x(), screen.height(), rect.width(), rect.height())
        effect = self._ensure_opacity_effect(widget)
        group = QParallelAnimationGroup()
        group.addAnimation(self._make_geometry_anim(widget, rect, end, curve=QEasingCurve.Type.InCubic))
        group.addAnimation(self._make_opacity_anim(effect, 1.0, 0.0))
        self._run_close(widget, group, callback)

    # ── 6. Cavalry Charge — dash from left ───────────────────

    def _open_cavalry_charge(self, widget, target):
        start = QRect(-target.width(), target.y(), target.width(), target.height())
        widget.setGeometry(start)
        effect = self._ensure_opacity_effect(widget)
        effect.setOpacity(0.5)
        group = QParallelAnimationGroup()
        group.addAnimation(self._make_geometry_anim(
            widget, start, target, duration=300, curve=QEasingCurve.Type.OutExpo))
        group.addAnimation(self._make_opacity_anim(effect, 0.5, 1.0, duration=300))
        self._run_open(widget, group)

    def _close_cavalry_charge(self, widget, callback=None):
        rect = widget.geometry()
        end = QRect(-rect.width(), rect.y(), rect.width(), rect.height())
        effect = self._ensure_opacity_effect(widget)
        group = QParallelAnimationGroup()
        group.addAnimation(self._make_geometry_anim(
            widget, rect, end, duration=300, curve=QEasingCurve.Type.InExpo))
        group.addAnimation(self._make_opacity_anim(effect, 1.0, 0.0, duration=300))
        self._run_close(widget, group, callback)

    # ── 7. Naval Broadside — slide with bounce ───────────────

    def _open_naval_broadside(self, widget, target):
        start = QRect(target.x() - 400, target.y(), target.width(), target.height())
        widget.setGeometry(start)
        effect = self._ensure_opacity_effect(widget)
        effect.setOpacity(0.0)
        group = QParallelAnimationGroup()
        group.addAnimation(self._make_geometry_anim(widget, start, target, curve=QEasingCurve.Type.OutBounce))
        group.addAnimation(self._make_opacity_anim(effect, 0.0, 1.0))
        self._run_open(widget, group)

    def _close_naval_broadside(self, widget, callback=None):
        rect = widget.geometry()
        end = QRect(rect.x() - 400, rect.y(), rect.width(), rect.height())
        effect = self._ensure_opacity_effect(widget)
        group = QParallelAnimationGroup()
        group.addAnimation(self._make_geometry_anim(widget, rect, end, curve=QEasingCurve.Type.InQuad))
        group.addAnimation(self._make_opacity_anim(effect, 1.0, 0.0))
        self._run_close(widget, group, callback)

    # ── 8. Vive l'Empereur — scale from center ───────────────

    def _open_vive_empereur(self, widget, target):
        cx, cy = target.x() + target.width() // 2, target.y() + target.height() // 2
        start = QRect(cx - 10, cy - 10, 20, 20)
        widget.setGeometry(start)
        effect = self._ensure_opacity_effect(widget)
        effect.setOpacity(0.0)
        group = QParallelAnimationGroup()
        group.addAnimation(self._make_geometry_anim(widget, start, target, curve=QEasingCurve.Type.OutBack))
        group.addAnimation(self._make_opacity_anim(effect, 0.0, 1.0))
        self._run_open(widget, group)

    def _close_vive_empereur(self, widget, callback=None):
        rect = widget.geometry()
        cx, cy = rect.x() + rect.width() // 2, rect.y() + rect.height() // 2
        end = QRect(cx - 10, cy - 10, 20, 20)
        effect = self._ensure_opacity_effect(widget)
        group = QParallelAnimationGroup()
        group.addAnimation(self._make_geometry_anim(widget, rect, end, curve=QEasingCurve.Type.InBack))
        group.addAnimation(self._make_opacity_anim(effect, 1.0, 0.0))
        self._run_close(widget, group, callback)

    # ── 9. Artillery Barrage — shake + fade ──────────────────

    def _open_artillery_barrage(self, widget, target):
        widget.setGeometry(target)
        effect = self._ensure_opacity_effect(widget)
        effect.setOpacity(0.0)
        seq = QSequentialAnimationGroup()
        seq.addAnimation(self._make_opacity_anim(effect, 0.0, 1.0, duration=150))
        offsets = [15, -15, 10, -10, 5, -5, 0]
        for dx in offsets:
            shifted = QRect(target.x() + dx, target.y(), target.width(), target.height())
            seq.addAnimation(self._make_geometry_anim(widget, widget.geometry(), shifted, duration=40,
                                                       curve=QEasingCurve.Type.Linear))
        seq.addAnimation(self._make_geometry_anim(widget, widget.geometry(), target, duration=60))
        group = QParallelAnimationGroup()
        group.addAnimation(seq)
        self._run_open(widget, group)

    def _close_artillery_barrage(self, widget, callback=None):
        rect = widget.geometry()
        effect = self._ensure_opacity_effect(widget)
        seq = QSequentialAnimationGroup()
        offsets = [10, -10, 7, -7, 3, -3]
        for dx in offsets:
            shifted = QRect(rect.x() + dx, rect.y(), rect.width(), rect.height())
            seq.addAnimation(self._make_geometry_anim(widget, widget.geometry(), shifted, duration=35,
                                                       curve=QEasingCurve.Type.Linear))
        seq.addAnimation(self._make_opacity_anim(effect, 1.0, 0.0, duration=200))
        group = QParallelAnimationGroup()
        group.addAnimation(seq)
        self._run_close(widget, group, callback)

    # ── 10. Grapeshot — rapid multi-bounce ───────────────────

    def _open_grapeshot(self, widget, target):
        start = QRect(target.x(), target.y() - 300, target.width(), target.height())
        widget.setGeometry(start)
        effect = self._ensure_opacity_effect(widget)
        effect.setOpacity(1.0)
        anim = self._make_geometry_anim(widget, start, target, duration=500,
                                         curve=QEasingCurve.Type.OutBounce)
        group = QParallelAnimationGroup()
        group.addAnimation(anim)
        self._run_open(widget, group)

    def _close_grapeshot(self, widget, callback=None):
        rect = widget.geometry()
        end = QRect(rect.x(), rect.y() + 600, rect.width(), rect.height())
        effect = self._ensure_opacity_effect(widget)
        group = QParallelAnimationGroup()
        group.addAnimation(self._make_geometry_anim(widget, rect, end, duration=350,
                                                     curve=QEasingCurve.Type.InQuad))
        group.addAnimation(self._make_opacity_anim(effect, 1.0, 0.0, duration=350))
        self._run_close(widget, group, callback)

    # ── 11. Old Guard — slow majestic fade-slide ─────────────

    def _open_old_guard(self, widget, target):
        start = QRect(target.x() + 80, target.y(), target.width(), target.height())
        widget.setGeometry(start)
        effect = self._ensure_opacity_effect(widget)
        effect.setOpacity(0.0)
        group = QParallelAnimationGroup()
        group.addAnimation(self._make_geometry_anim(widget, start, target, duration=700,
                                                     curve=QEasingCurve.Type.OutQuad))
        group.addAnimation(self._make_opacity_anim(effect, 0.0, 1.0, duration=700,
                                                    curve=QEasingCurve.Type.InOutSine))
        self._run_open(widget, group)

    def _close_old_guard(self, widget, callback=None):
        rect = widget.geometry()
        end = QRect(rect.x() + 80, rect.y(), rect.width(), rect.height())
        effect = self._ensure_opacity_effect(widget)
        group = QParallelAnimationGroup()
        group.addAnimation(self._make_geometry_anim(widget, rect, end, duration=700,
                                                     curve=QEasingCurve.Type.InQuad))
        group.addAnimation(self._make_opacity_anim(effect, 1.0, 0.0, duration=700,
                                                    curve=QEasingCurve.Type.InOutSine))
        self._run_close(widget, group, callback)

    # ── 12. Russian Winter — drift down with fade ────────────

    def _open_russian_winter(self, widget, target):
        start = QRect(target.x() + 30, target.y() - 200, target.width(), target.height())
        widget.setGeometry(start)
        effect = self._ensure_opacity_effect(widget)
        effect.setOpacity(0.0)
        group = QParallelAnimationGroup()
        group.addAnimation(self._make_geometry_anim(widget, start, target, duration=600,
                                                     curve=QEasingCurve.Type.OutSine))
        group.addAnimation(self._make_opacity_anim(effect, 0.0, 1.0, duration=600,
                                                    curve=QEasingCurve.Type.InOutQuad))
        self._run_open(widget, group)

    def _close_russian_winter(self, widget, callback=None):
        rect = widget.geometry()
        end = QRect(rect.x() - 30, rect.y() + 200, rect.width(), rect.height())
        effect = self._ensure_opacity_effect(widget)
        group = QParallelAnimationGroup()
        group.addAnimation(self._make_geometry_anim(widget, rect, end, duration=600,
                                                     curve=QEasingCurve.Type.InSine))
        group.addAnimation(self._make_opacity_anim(effect, 1.0, 0.0, duration=600,
                                                    curve=QEasingCurve.Type.InOutQuad))
        self._run_close(widget, group, callback)

    # ── 13. Lightning Strike — quick flash ────────────────────

    def _open_lightning_strike(self, widget, target):
        widget.setGeometry(target)
        effect = self._ensure_opacity_effect(widget)
        effect.setOpacity(0.0)
        seq = QSequentialAnimationGroup()
        # Flash to full opacity
        seq.addAnimation(self._make_opacity_anim(effect, 0.0, 1.0, duration=50,
                                                  curve=QEasingCurve.Type.Linear))
        # Motion blur micro-shifts
        left = QRect(target.x() - 8, target.y(), target.width(), target.height())
        right = QRect(target.x() + 8, target.y(), target.width(), target.height())
        seq.addAnimation(self._make_geometry_anim(widget, target, left, duration=30,
                                                   curve=QEasingCurve.Type.Linear))
        seq.addAnimation(self._make_geometry_anim(widget, left, right, duration=30,
                                                   curve=QEasingCurve.Type.Linear))
        seq.addAnimation(self._make_geometry_anim(widget, right, target, duration=30,
                                                   curve=QEasingCurve.Type.Linear))
        # Settle at target
        seq.addAnimation(self._make_geometry_anim(widget, target, target, duration=60,
                                                   curve=QEasingCurve.Type.OutCubic))
        group = QParallelAnimationGroup()
        group.addAnimation(seq)
        self._run_open(widget, group)

    def _close_lightning_strike(self, widget, callback=None):
        rect = widget.geometry()
        effect = self._ensure_opacity_effect(widget)
        seq = QSequentialAnimationGroup()
        # Quick shake for motion blur
        left = QRect(rect.x() - 5, rect.y(), rect.width(), rect.height())
        right = QRect(rect.x() + 5, rect.y(), rect.width(), rect.height())
        seq.addAnimation(self._make_geometry_anim(widget, rect, left, duration=25,
                                                   curve=QEasingCurve.Type.Linear))
        seq.addAnimation(self._make_geometry_anim(widget, left, right, duration=25,
                                                   curve=QEasingCurve.Type.Linear))
        seq.addAnimation(self._make_geometry_anim(widget, right, rect, duration=25,
                                                   curve=QEasingCurve.Type.Linear))
        # Instant fade out
        seq.addAnimation(self._make_opacity_anim(effect, 1.0, 0.0, duration=80,
                                                  curve=QEasingCurve.Type.Linear))
        group = QParallelAnimationGroup()
        group.addAnimation(seq)
        self._run_close(widget, group, callback)

    # ── 14. Flag Wave — French tricolor wave ──────────────────

    def _open_flag_wave(self, widget, target):
        start = QRect(target.x() + 60, target.y(), target.width(), target.height())
        widget.setGeometry(start)
        effect = self._ensure_opacity_effect(widget)
        effect.setOpacity(0.0)
        seq_geo = QSequentialAnimationGroup()
        # Wave motion: swing left, then right, then settle
        wave_left = QRect(target.x() - 30, target.y(), target.width(), target.height())
        wave_right = QRect(target.x() + 20, target.y(), target.width(), target.height())
        seq_geo.addAnimation(self._make_geometry_anim(widget, start, wave_left, duration=160,
                                                       curve=QEasingCurve.Type.InOutSine))
        seq_geo.addAnimation(self._make_geometry_anim(widget, wave_left, wave_right, duration=160,
                                                       curve=QEasingCurve.Type.InOutSine))
        seq_geo.addAnimation(self._make_geometry_anim(widget, wave_right, target, duration=180,
                                                       curve=QEasingCurve.Type.OutSine))
        group = QParallelAnimationGroup()
        group.addAnimation(seq_geo)
        group.addAnimation(self._make_opacity_anim(effect, 0.0, 1.0, duration=500,
                                                    curve=QEasingCurve.Type.InOutQuad))
        self._run_open(widget, group)

    def _close_flag_wave(self, widget, callback=None):
        rect = widget.geometry()
        effect = self._ensure_opacity_effect(widget)
        seq_geo = QSequentialAnimationGroup()
        # Wave out: right, then left, then off-screen right
        wave_right = QRect(rect.x() + 30, rect.y(), rect.width(), rect.height())
        wave_left = QRect(rect.x() - 20, rect.y(), rect.width(), rect.height())
        offscreen = QRect(rect.x() + 100, rect.y(), rect.width(), rect.height())
        seq_geo.addAnimation(self._make_geometry_anim(widget, rect, wave_right, duration=140,
                                                       curve=QEasingCurve.Type.InOutSine))
        seq_geo.addAnimation(self._make_geometry_anim(widget, wave_right, wave_left, duration=140,
                                                       curve=QEasingCurve.Type.InOutSine))
        seq_geo.addAnimation(self._make_geometry_anim(widget, wave_left, offscreen, duration=220,
                                                       curve=QEasingCurve.Type.InSine))
        group = QParallelAnimationGroup()
        group.addAnimation(seq_geo)
        group.addAnimation(self._make_opacity_anim(effect, 1.0, 0.0, duration=500,
                                                    curve=QEasingCurve.Type.InOutQuad))
        self._run_close(widget, group, callback)

    # ── 15. Cannonball Trail — arc with trail ─────────────────

    def _open_cannonball_trail(self, widget, target):
        start = QRect(target.x() - 300, target.y() - 200, target.width(), target.height())
        widget.setGeometry(start)
        effect = self._ensure_opacity_effect(widget)
        effect.setOpacity(0.3)
        seq_geo = QSequentialAnimationGroup()
        # Arc down to target
        seq_geo.addAnimation(self._make_geometry_anim(widget, start, target, duration=350,
                                                       curve=QEasingCurve.Type.OutQuad))
        # Bounce at end for impact
        seq_geo.addAnimation(self._make_geometry_anim(widget, target, target, duration=100,
                                                       curve=QEasingCurve.Type.OutBounce))
        group = QParallelAnimationGroup()
        group.addAnimation(seq_geo)
        group.addAnimation(self._make_opacity_anim(effect, 0.3, 1.0, duration=450,
                                                    curve=QEasingCurve.Type.OutCubic))
        self._run_open(widget, group)

    def _close_cannonball_trail(self, widget, callback=None):
        rect = widget.geometry()
        end = QRect(rect.x() - 300, rect.y() - 200, rect.width(), rect.height())
        effect = self._ensure_opacity_effect(widget)
        seq_geo = QSequentialAnimationGroup()
        # Reverse arc upward
        seq_geo.addAnimation(self._make_geometry_anim(widget, rect, end, duration=450,
                                                       curve=QEasingCurve.Type.InQuad))
        group = QParallelAnimationGroup()
        group.addAnimation(seq_geo)
        group.addAnimation(self._make_opacity_anim(effect, 1.0, 0.0, duration=450,
                                                    curve=QEasingCurve.Type.InCubic))
        self._run_close(widget, group, callback)

    # ── 16. Morale Boost — pulsing green aura ─────────────────

    def _open_morale_boost(self, widget, target):
        cx = target.x() + target.width() // 2
        cy = target.y() + target.height() // 2
        start = QRect(cx - 5, cy - 5, 10, 10)
        widget.setGeometry(start)
        effect = self._ensure_opacity_effect(widget)
        effect.setOpacity(0.0)
        # Overshoot rect at 110% scale
        ow = int(target.width() * 1.1)
        oh = int(target.height() * 1.1)
        overshoot = QRect(target.x() - (ow - target.width()) // 2,
                          target.y() - (oh - target.height()) // 2, ow, oh)
        seq_geo = QSequentialAnimationGroup()
        # Scale out from center to 110%
        seq_geo.addAnimation(self._make_geometry_anim(widget, start, overshoot, duration=350,
                                                       curve=QEasingCurve.Type.OutCubic))
        # Settle back to 100%
        seq_geo.addAnimation(self._make_geometry_anim(widget, overshoot, target, duration=250,
                                                       curve=QEasingCurve.Type.InOutSine))
        group = QParallelAnimationGroup()
        group.addAnimation(seq_geo)
        group.addAnimation(self._make_opacity_anim(effect, 0.0, 1.0, duration=600,
                                                    curve=QEasingCurve.Type.OutCubic))
        self._run_open(widget, group)

    def _close_morale_boost(self, widget, callback=None):
        rect = widget.geometry()
        cx = rect.x() + rect.width() // 2
        cy = rect.y() + rect.height() // 2
        end = QRect(cx - 5, cy - 5, 10, 10)
        effect = self._ensure_opacity_effect(widget)
        # Pulse rect at 105% scale
        pw = int(rect.width() * 1.05)
        ph = int(rect.height() * 1.05)
        pulse = QRect(rect.x() - (pw - rect.width()) // 2,
                      rect.y() - (ph - rect.height()) // 2, pw, ph)
        seq_geo = QSequentialAnimationGroup()
        # Pulse out slightly
        seq_geo.addAnimation(self._make_geometry_anim(widget, rect, pulse, duration=150,
                                                       curve=QEasingCurve.Type.OutSine))
        # Shrink to center
        seq_geo.addAnimation(self._make_geometry_anim(widget, pulse, end, duration=450,
                                                       curve=QEasingCurve.Type.InCubic))
        group = QParallelAnimationGroup()
        group.addAnimation(seq_geo)
        group.addAnimation(self._make_opacity_anim(effect, 1.0, 0.0, duration=600,
                                                    curve=QEasingCurve.Type.InCubic))
        self._run_close(widget, group, callback)


class CheatOverlay:
    """
    Overlay window showing active cheats with customizable
    Napoleon Total War themed open/close animations.
    """

    def __init__(self, animation_style: str = "smoke_screen"):
        """
        Initialize cheat overlay.

        Args:
            animation_style: Name of the animation style (see OverlayAnimationStyle values)
        """
        self.window: Optional[QWidget] = None
        self.labels: Dict[str, QLabel] = {}
        self.timer: Optional[QTimer] = None
        self.visible: bool = False
        self._target_rect: Optional[QRect] = None
        self._animation_style_value = animation_style
        self._animation_mgr: Optional[OverlayAnimationManager] = None
        self._animation_combo: Optional[QComboBox] = None

    @property
    def animation_style(self) -> str:
        """Get current animation style value string."""
        if self._animation_mgr:
            return self._animation_mgr.animation_style.value
        return self._animation_style_value

    @animation_style.setter
    def animation_style(self, value: str) -> None:
        """Set animation style by value string."""
        self._animation_style_value = value
        style = OverlayAnimationStyle.from_value(value)
        if self._animation_mgr:
            self._animation_mgr.animation_style = style

    def create_overlay(self) -> bool:
        """
        Create the overlay window.

        Returns:
            bool: True if created successfully
        """
        if not PYQT_AVAILABLE:
            print("PyQt6 not available. Overlay disabled.")
            return False

        try:
            style = OverlayAnimationStyle.from_value(self._animation_style_value)
            self._animation_mgr = OverlayAnimationManager(style)

            # Create window
            self.window = QWidget()
            self.window.setWindowTitle("Active Cheats")
            self.window.setWindowFlags(
                Qt.WindowType.FramelessWindowHint |
                Qt.WindowType.WindowStaysOnTopHint |
                Qt.WindowType.Tool
            )
            self.window.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
            self.window.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)

            # Set position (top-right corner)
            screen = QApplication.primaryScreen().geometry()
            self._target_rect = QRect(
                screen.width() - 300,
                100,
                280,
                400
            )
            self.window.setGeometry(self._target_rect)

            # Layout
            layout = QVBoxLayout()

            # Title
            title = QLabel("🎮 Active Cheats")
            title.setStyleSheet("""
                QLabel {
                    color: #00ff00;
                    font-size: 16px;
                    font-weight: bold;
                    padding: 10px;
                    background-color: rgba(0, 0, 0, 200);
                    border-radius: 5px;
                }
            """)
            layout.addWidget(title)

            # Animation style selector (in-overlay customization)
            anim_frame = QFrame()
            anim_frame.setStyleSheet("""
                QFrame {
                    background-color: rgba(0, 0, 0, 180);
                    border-radius: 5px;
                    padding: 4px;
                }
            """)
            anim_layout = QHBoxLayout()
            anim_layout.setContentsMargins(6, 4, 6, 4)
            anim_label = QLabel("🎬")
            anim_label.setStyleSheet("QLabel { color: #d4af37; font-size: 14px; }")
            anim_layout.addWidget(anim_label)

            self._animation_combo = QComboBox()
            self._animation_combo.setStyleSheet("""
                QComboBox {
                    background-color: rgba(26, 37, 47, 220);
                    color: #d4af37;
                    border: 1px solid #d4af37;
                    border-radius: 3px;
                    padding: 3px 6px;
                    font-size: 11px;
                }
                QComboBox::drop-down {
                    border: none;
                }
                QComboBox QAbstractItemView {
                    background-color: #1a252f;
                    color: #d4af37;
                    selection-background-color: #2c3e50;
                    border: 1px solid #d4af37;
                }
            """)
            display_names = OverlayAnimationStyle.display_names()
            current_index = 0
            for idx, (value, name) in enumerate(display_names.items()):
                self._animation_combo.addItem(name, value)
                if value == self._animation_style_value:
                    current_index = idx
            self._animation_combo.setCurrentIndex(current_index)
            self._animation_combo.currentIndexChanged.connect(self._on_animation_changed)
            anim_layout.addWidget(self._animation_combo)
            anim_frame.setLayout(anim_layout)
            layout.addWidget(anim_frame)

            self.window.setLayout(layout)

            print("Cheat overlay created")
            return True

        except Exception as e:
            print(f"Failed to create overlay: {e}")
            return False

    def _on_animation_changed(self, index: int) -> None:
        """Handle animation style selection change."""
        if self._animation_combo is None:
            return
        value = self._animation_combo.itemData(index)
        if value is not None:
            self.animation_style = value

    def update_cheats(self, active_cheats: List[str]) -> None:
        """
        Update the overlay with active cheats.

        Args:
            active_cheats: List of active cheat names
        """
        if not self.window:
            return

        layout = self.window.layout()
        if not layout:
            return

        # Clear existing cheat labels (keep title at 0 and animation selector at 1)
        while layout.count() > 2:
            item = layout.takeAt(2)
            if item.widget():
                item.widget().deleteLater()

        # Add active cheats
        if active_cheats:
            for cheat_name in active_cheats:
                label = QLabel(f"✓ {cheat_name}")
                label.setStyleSheet("""
                    QLabel {
                        color: #00ff00;
                        font-size: 12px;
                        padding: 5px;
                        background-color: rgba(0, 50, 0, 150);
                        border-radius: 3px;
                        margin: 2px;
                    }
                """)
                layout.addWidget(label)
        else:
            label = QLabel("No active cheats")
            label.setStyleSheet("""
                QLabel {
                    color: #888888;
                    font-size: 12px;
                    padding: 5px;
                    font-style: italic;
                }
            """)
            layout.addWidget(label)

    def show(self) -> None:
        """Show the overlay with the configured animation."""
        if self.window:
            if self._animation_mgr and self._target_rect:
                self._animation_mgr.animate_open(self.window, self._target_rect)
            else:
                self.window.show()
            self.visible = True

    def hide(self) -> None:
        """Hide the overlay with the configured animation."""
        if self.window:
            if self._animation_mgr:
                self._animation_mgr.animate_close(
                    self.window,
                    callback=self._on_hide_complete,
                )
            else:
                self.window.hide()
            self.visible = False

    def _on_hide_complete(self) -> None:
        """Callback invoked when the hide animation finishes."""
        self.visible = False

    def toggle(self) -> None:
        """Toggle overlay visibility."""
        if self.visible:
            self.hide()
        else:
            self.show()

    def close(self) -> None:
        """Close the overlay."""
        if self._animation_mgr:
            self._animation_mgr._stop_active()
        if self.window:
            self.window.close()
            self.window = None

    def is_visible(self) -> bool:
        """Check if overlay is visible."""
        return self.visible

    def get_available_animations(self) -> Dict[str, str]:
        """
        Get all available animation styles with display names.

        Returns:
            Dict mapping style value strings to display name strings
        """
        return OverlayAnimationStyle.display_names()

    def get_available_presets(self) -> Dict[str, str]:
        """Get curated overlay presets with display labels."""
        return {
            preset_name: preset["name"]
            for preset_name, preset in OverlayAnimationStyle.preset_definitions().items()
        }


class SimpleOverlay:
    """
    Simple console-based overlay fallback.
    For when PyQt6 is not available.
    """

    def __init__(self):
        """Initialize simple overlay."""
        self.active_cheats: List[str] = []
        self.last_update: float = 0

    def update_cheats(self, active_cheats: List[str]) -> None:
        """Update active cheats list."""
        self.active_cheats = active_cheats

    def show(self) -> None:
        """Show cheat status."""
        if self.active_cheats:
            print(f"\n🎮 Active Cheats: {', '.join(self.active_cheats)}\n")
        else:
            print("\n🎮 No active cheats\n")

    def hide(self) -> None:
        """Hide (no-op for console)."""
        pass

    def toggle(self) -> None:
        """Toggle display."""
        self.show()

    def close(self) -> None:
        """Close (no-op for console)."""
        self.active_cheats = []
