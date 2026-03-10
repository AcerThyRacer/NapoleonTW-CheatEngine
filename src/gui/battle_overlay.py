"""
Battle Map Integration Overlay for Napoleon Total War Cheat Engine.

Provides a transparent overlay that sits on top of the game window, showing
active cheats, unit statistics, and quick-toggle controls.  The overlay is
designed to be minimal and non-intrusive so that it can remain visible during
gameplay without obscuring the battle map.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from src.memory import CheatManager, CheatType

logger = logging.getLogger("napoleon.gui.battle_overlay")

try:
    from PyQt6.QtWidgets import (
        QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
        QFrame, QScrollArea, QGridLayout, QGroupBox, QGraphicsOpacityEffect,
        QSizePolicy, QApplication,
    )
    from PyQt6.QtCore import (
        Qt, pyqtSignal, QTimer, QPropertyAnimation, QEasingCurve,
        QPoint, QSize, QRect,
    )
    from PyQt6.QtGui import QFont, QColor, QPainter, QBrush, QPen, QCursor
    PYQT_AVAILABLE = True
except ImportError:
    PYQT_AVAILABLE = False


# ---------------------------------------------------------------------------
# Cheat category definitions  (always importable, no PyQt6 dependency)
# ---------------------------------------------------------------------------

_CAMPAIGN_CHEATS: List[Dict[str, Any]] = [
    {"type": CheatType.INFINITE_GOLD,            "label": "Infinite Gold",            "icon": "💰"},
    {"type": CheatType.UNLIMITED_MOVEMENT,        "label": "Unlimited Movement",       "icon": "🏃"},
    {"type": CheatType.INSTANT_CONSTRUCTION,      "label": "Instant Construction",     "icon": "🏗️"},
    {"type": CheatType.FAST_RESEARCH,             "label": "Fast Research",            "icon": "🔬"},
    {"type": CheatType.INFINITE_ACTION_POINTS,    "label": "Infinite Action Points",   "icon": "⚡"},
    {"type": CheatType.MAX_RESEARCH_POINTS,       "label": "Max Research Points",      "icon": "📚"},
    {"type": CheatType.INSTANT_AGENT_TRAINING,    "label": "Instant Agent Training",   "icon": "🕵️"},
    {"type": CheatType.FREE_DIPLOMATIC_ACTIONS,   "label": "Free Diplomacy",           "icon": "🤝"},
    {"type": CheatType.INVISIBLE_ARMIES,          "label": "Invisible Armies",         "icon": "👻"},
    {"type": CheatType.INSTANT_VICTORY,           "label": "Instant Victory",          "icon": "🏆"},
    {"type": CheatType.MAX_PUBLIC_ORDER,          "label": "Max Public Order",         "icon": "⚖️"},
    {"type": CheatType.ZERO_ATTRITION,            "label": "Zero Attrition",           "icon": "🛡️"},
    {"type": CheatType.FREE_UPGRADES,             "label": "Free Upgrades",            "icon": "⬆️"},
]

_BATTLE_CHEATS: List[Dict[str, Any]] = [
    {"type": CheatType.GOD_MODE,              "label": "God Mode",            "icon": "🛡️"},
    {"type": CheatType.UNLIMITED_AMMO,        "label": "Unlimited Ammo",      "icon": "🎯"},
    {"type": CheatType.HIGH_MORALE,           "label": "High Morale",         "icon": "📯"},
    {"type": CheatType.INFINITE_STAMINA,      "label": "Infinite Stamina",    "icon": "💪"},
    {"type": CheatType.ONE_HIT_KILL,          "label": "One-Hit Kill",        "icon": "💀"},
    {"type": CheatType.SUPER_SPEED,           "label": "Super Speed",         "icon": "⚡"},
    {"type": CheatType.INFINITE_MORALE,       "label": "Infinite Morale",     "icon": "🔥"},
    {"type": CheatType.INSTANT_RELOAD,        "label": "Instant Reload",      "icon": "🔄"},
    {"type": CheatType.RANGE_BOOST,           "label": "Range Boost",         "icon": "🏹"},
    {"type": CheatType.INFINITE_UNIT_HEALTH,  "label": "Infinite Unit HP",    "icon": "❤️"},
]

_STRATEGIC_CHEATS: List[Dict[str, Any]] = [
    {"type": CheatType.SPEED_BOOST,  "label": "Speed Boost",  "icon": "🚀"},
]

_ALL_CHEATS = _CAMPAIGN_CHEATS + _BATTLE_CHEATS + _STRATEGIC_CHEATS
_CHEAT_LOOKUP: Dict[CheatType, Dict[str, Any]] = {e["type"]: e for e in _ALL_CHEATS}


# ---------------------------------------------------------------------------
# Qt widgets (only defined when PyQt6 is available)
# ---------------------------------------------------------------------------

if PYQT_AVAILABLE:

    # ---- small reusable widgets -----------------------------------------

    class _CheatToggleButton(QPushButton):
        """A compact toggle button for a single cheat."""

        toggled_cheat = pyqtSignal(object, bool)  # (CheatType, new_state)

        def __init__(self, cheat_entry: Dict[str, Any], parent: Optional[QWidget] = None):
            super().__init__(parent)
            self._ct = cheat_entry["type"]
            self._icon_text = cheat_entry["icon"]
            self._label_text = cheat_entry["label"]
            self._active = False
            self._update_display()
            self.setCheckable(True)
            self.setFixedHeight(32)
            self.setMinimumWidth(140)
            self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
            self.clicked.connect(self._on_click)

        def _update_display(self) -> None:
            self.setText(f"{self._icon_text} {self._label_text}")
            if self._active:
                self.setStyleSheet(
                    "QPushButton { background: rgba(0,180,80,180); color: #fff; "
                    "border: 1px solid #00cc55; border-radius: 4px; padding: 2px 8px; "
                    "font-size: 11px; font-weight: bold; }"
                    "QPushButton:hover { background: rgba(0,200,90,200); }"
                )
            else:
                self.setStyleSheet(
                    "QPushButton { background: rgba(60,60,60,180); color: #aaa; "
                    "border: 1px solid #555; border-radius: 4px; padding: 2px 8px; "
                    "font-size: 11px; }"
                    "QPushButton:hover { background: rgba(80,80,80,200); }"
                )

        def set_active(self, active: bool) -> None:
            self._active = active
            self.setChecked(active)
            self._update_display()

        def _on_click(self) -> None:
            self._active = self.isChecked()
            self._update_display()
            self.toggled_cheat.emit(self._ct, self._active)

    # ---- Unit stats widget ----------------------------------------------

    class _UnitStatsWidget(QFrame):
        """
        Displays unit statistics in the overlay such as active unit count,
        total health, morale average, etc.
        """

        def __init__(self, parent: Optional[QWidget] = None):
            super().__init__(parent)
            self.setFrameShape(QFrame.Shape.StyledPanel)
            self.setStyleSheet(
                "QFrame { background: rgba(30,30,30,200); border: 1px solid #444; "
                "border-radius: 6px; }"
            )
            layout = QGridLayout(self)
            layout.setContentsMargins(8, 6, 8, 6)
            layout.setSpacing(4)

            self._labels: Dict[str, QLabel] = {}
            stats = [
                ("units", "Units"),
                ("health", "Avg HP"),
                ("morale", "Avg Morale"),
                ("ammo", "Avg Ammo"),
                ("kills", "Total Kills"),
            ]
            for row, (key, display) in enumerate(stats):
                name_lbl = QLabel(f"{display}:")
                name_lbl.setStyleSheet("color: #aaa; font-size: 11px;")
                value_lbl = QLabel("—")
                value_lbl.setStyleSheet("color: #fff; font-size: 11px; font-weight: bold;")
                value_lbl.setAlignment(Qt.AlignmentFlag.AlignRight)
                layout.addWidget(name_lbl, row, 0)
                layout.addWidget(value_lbl, row, 1)
                self._labels[key] = value_lbl

        def update_stats(self, stats: Dict[str, Any]) -> None:
            """Update displayed statistics from a dict."""
            for key, lbl in self._labels.items():
                val = stats.get(key)
                lbl.setText(str(val) if val is not None else "—")

    # ---- Active cheats summary ------------------------------------------

    class _ActiveCheatsSummary(QFrame):
        """
        Compact summary strip showing which cheats are currently active.
        """

        def __init__(self, parent: Optional[QWidget] = None):
            super().__init__(parent)
            self.setFrameShape(QFrame.Shape.StyledPanel)
            self.setStyleSheet(
                "QFrame { background: rgba(20,20,20,210); border: 1px solid #444; "
                "border-radius: 6px; }"
            )
            self._layout = QHBoxLayout(self)
            self._layout.setContentsMargins(8, 4, 8, 4)
            self._layout.setSpacing(6)

            self._title = QLabel("Active:")
            self._title.setStyleSheet(
                "color: #00cc55; font-size: 11px; font-weight: bold;"
            )
            self._layout.addWidget(self._title)

            self._cheats_label = QLabel("None")
            self._cheats_label.setStyleSheet("color: #ccc; font-size: 11px;")
            self._cheats_label.setWordWrap(True)
            self._layout.addWidget(self._cheats_label, 1)

        def update_active_cheats(self, active_types: List[CheatType]) -> None:
            if not active_types:
                self._cheats_label.setText("None")
                self._cheats_label.setStyleSheet("color: #888; font-size: 11px;")
                return
            parts = []
            for ct in active_types:
                entry = _CHEAT_LOOKUP.get(ct)
                if entry:
                    parts.append(f"{entry['icon']} {entry['label']}")
                else:
                    parts.append(ct.value)
            self._cheats_label.setText("  •  ".join(parts))
            self._cheats_label.setStyleSheet("color: #ccc; font-size: 11px;")

    # ---- Main overlay window --------------------------------------------

    class BattleMapOverlay(QWidget):
        """
        Transparent overlay window designed to sit on top of the game view.

        Features:
          - Semi-transparent background that doesn't steal focus.
          - Active cheats summary bar at the top.
          - Collapsible cheat toggle panels (Campaign / Battle / Strategic).
          - Unit statistics widget.
          - Auto-refresh timer that polls the cheat manager.
          - Drag-to-move support.
          - Opacity slider.
        """

        overlay_closed = pyqtSignal()

        def __init__(
            self,
            cheat_manager: Optional[CheatManager] = None,
            parent: Optional[QWidget] = None,
        ):
            super().__init__(parent)
            self.cheat_manager = cheat_manager
            self._drag_pos: Optional[QPoint] = None
            self._toggle_buttons: Dict[CheatType, _CheatToggleButton] = {}
            self._collapsed: Dict[str, bool] = {
                "campaign": False,
                "battle": False,
                "strategic": True,
            }

            self._setup_window()
            self._build_ui()

            # Refresh timer – polls cheat states every 500 ms
            self._timer = QTimer(self)
            self._timer.timeout.connect(self._refresh_state)
            self._timer.setInterval(500)

        # ---- window flags / styling ------------------------------------

        def _setup_window(self) -> None:
            self.setWindowTitle("Battle Overlay")
            self.setWindowFlags(
                Qt.WindowType.FramelessWindowHint
                | Qt.WindowType.WindowStaysOnTopHint
                | Qt.WindowType.Tool
            )
            self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
            self.setMinimumSize(320, 200)
            self.resize(380, 560)

        # ---- UI construction -------------------------------------------

        def _build_ui(self) -> None:
            root = QVBoxLayout(self)
            root.setContentsMargins(0, 0, 0, 0)
            root.setSpacing(0)

            # Container with semi-transparent background
            container = QFrame()
            container.setStyleSheet(
                "QFrame { background: rgba(15,15,15,210); "
                "border: 1px solid #555; border-radius: 8px; }"
            )
            container_layout = QVBoxLayout(container)
            container_layout.setContentsMargins(10, 8, 10, 8)
            container_layout.setSpacing(6)

            # Title bar
            title_bar = QHBoxLayout()
            title_lbl = QLabel("⚔️ Battle Overlay")
            title_lbl.setStyleSheet(
                "color: #fff; font-size: 14px; font-weight: bold; background: transparent; border: none;"
            )
            title_bar.addWidget(title_lbl)
            title_bar.addStretch()

            # Opacity control
            opacity_down = QPushButton("−")
            opacity_down.setFixedSize(24, 24)
            opacity_down.setStyleSheet(self._small_btn_style())
            opacity_down.setToolTip("Decrease opacity")
            opacity_down.clicked.connect(lambda: self._adjust_opacity(-0.1))
            title_bar.addWidget(opacity_down)

            opacity_up = QPushButton("+")
            opacity_up.setFixedSize(24, 24)
            opacity_up.setStyleSheet(self._small_btn_style())
            opacity_up.setToolTip("Increase opacity")
            opacity_up.clicked.connect(lambda: self._adjust_opacity(0.1))
            title_bar.addWidget(opacity_up)

            close_btn = QPushButton("✕")
            close_btn.setFixedSize(24, 24)
            close_btn.setStyleSheet(
                "QPushButton { background: rgba(180,0,0,180); color: #fff; "
                "border: none; border-radius: 4px; font-weight: bold; }"
                "QPushButton:hover { background: rgba(220,0,0,220); }"
            )
            close_btn.setToolTip("Close overlay")
            close_btn.clicked.connect(self.hide_overlay)
            title_bar.addWidget(close_btn)

            container_layout.addLayout(title_bar)

            # Active cheats summary
            self._summary = _ActiveCheatsSummary()
            container_layout.addWidget(self._summary)

            # Scrollable cheat toggles
            scroll = QScrollArea()
            scroll.setWidgetResizable(True)
            scroll.setStyleSheet(
                "QScrollArea { background: transparent; border: none; }"
                "QScrollBar:vertical { background: #222; width: 8px; }"
                "QScrollBar::handle:vertical { background: #555; border-radius: 4px; }"
            )
            scroll_widget = QWidget()
            scroll_layout = QVBoxLayout(scroll_widget)
            scroll_layout.setContentsMargins(0, 0, 0, 0)
            scroll_layout.setSpacing(4)

            # Campaign cheats group
            self._campaign_group = self._make_cheat_group(
                "Campaign Cheats", _CAMPAIGN_CHEATS, "campaign"
            )
            scroll_layout.addWidget(self._campaign_group)

            # Battle cheats group
            self._battle_group = self._make_cheat_group(
                "Battle Cheats", _BATTLE_CHEATS, "battle"
            )
            scroll_layout.addWidget(self._battle_group)

            # Strategic cheats group
            self._strategic_group = self._make_cheat_group(
                "Strategic Cheats", _STRATEGIC_CHEATS, "strategic"
            )
            scroll_layout.addWidget(self._strategic_group)

            scroll_layout.addStretch()
            scroll.setWidget(scroll_widget)
            container_layout.addWidget(scroll, 1)

            # Unit stats
            self._unit_stats = _UnitStatsWidget()
            container_layout.addWidget(self._unit_stats)

            # Bottom bar
            bottom = QHBoxLayout()
            self._status_label = QLabel("Overlay ready")
            self._status_label.setStyleSheet(
                "color: #888; font-size: 10px; background: transparent; border: none;"
            )
            bottom.addWidget(self._status_label)
            bottom.addStretch()
            container_layout.addLayout(bottom)

            root.addWidget(container)

        def _make_cheat_group(
            self,
            title: str,
            cheats: List[Dict[str, Any]],
            group_key: str,
        ) -> QWidget:
            """Build a collapsible group of cheat toggle buttons."""
            group = QWidget()
            group.setStyleSheet("background: transparent; border: none;")
            layout = QVBoxLayout(group)
            layout.setContentsMargins(0, 0, 0, 0)
            layout.setSpacing(2)

            # Header row
            header = QPushButton(f"▼ {title}" if not self._collapsed.get(group_key) else f"▶ {title}")
            header.setStyleSheet(
                "QPushButton { background: rgba(50,50,50,180); color: #ddd; "
                "border: 1px solid #444; border-radius: 4px; padding: 4px 8px; "
                "font-size: 12px; font-weight: bold; text-align: left; }"
                "QPushButton:hover { background: rgba(70,70,70,200); }"
            )
            header.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
            layout.addWidget(header)

            # Content frame
            content = QFrame()
            content.setStyleSheet("background: transparent; border: none;")
            content_layout = QGridLayout(content)
            content_layout.setContentsMargins(4, 2, 4, 2)
            content_layout.setSpacing(3)

            for idx, entry in enumerate(cheats):
                btn = _CheatToggleButton(entry)
                btn.toggled_cheat.connect(self._on_cheat_toggled)
                content_layout.addWidget(btn, idx // 2, idx % 2)
                self._toggle_buttons[entry["type"]] = btn

            content.setVisible(not self._collapsed.get(group_key, False))
            layout.addWidget(content)

            # Wire collapse toggle
            def toggle_collapse(checked=False, _c=content, _h=header, _k=group_key):
                vis = not _c.isVisible()
                _c.setVisible(vis)
                self._collapsed[_k] = not vis
                _h.setText(f"▼ {title}" if vis else f"▶ {title}")

            header.clicked.connect(toggle_collapse)
            return group

        @staticmethod
        def _small_btn_style() -> str:
            return (
                "QPushButton { background: rgba(60,60,60,180); color: #ccc; "
                "border: 1px solid #555; border-radius: 4px; font-weight: bold; }"
                "QPushButton:hover { background: rgba(90,90,90,200); }"
            )

        # ---- cheat toggling --------------------------------------------

        def _on_cheat_toggled(self, cheat_type: CheatType, active: bool) -> None:
            if self.cheat_manager is None:
                return
            try:
                if active:
                    self.cheat_manager.activate_cheat(cheat_type)
                else:
                    self.cheat_manager.deactivate_cheat(cheat_type)
            except Exception as exc:
                logger.warning("Failed to toggle %s: %s", cheat_type, exc)
            self._refresh_state()

        # ---- periodic state refresh ------------------------------------

        def _refresh_state(self) -> None:
            """Poll the cheat manager and update all toggle buttons + summary."""
            if self.cheat_manager is None:
                return

            active_types: List[CheatType] = []
            for ct, btn in self._toggle_buttons.items():
                is_active = self.cheat_manager.is_cheat_active(ct)
                btn.set_active(is_active)
                if is_active:
                    active_types.append(ct)

            self._summary.update_active_cheats(active_types)
            count = len(active_types)
            self._status_label.setText(
                f"{count} cheat{'s' if count != 1 else ''} active"
            )

        # ---- drag-to-move ----------------------------------------------

        def mousePressEvent(self, event) -> None:
            if event.button() == Qt.MouseButton.LeftButton:
                self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
                event.accept()

        def mouseMoveEvent(self, event) -> None:
            if self._drag_pos is not None and event.buttons() & Qt.MouseButton.LeftButton:
                self.move(event.globalPosition().toPoint() - self._drag_pos)
                event.accept()

        def mouseReleaseEvent(self, event) -> None:
            self._drag_pos = None

        # ---- opacity control -------------------------------------------

        def _adjust_opacity(self, delta: float) -> None:
            current = self.windowOpacity()
            new_val = max(0.2, min(1.0, current + delta))
            self.setWindowOpacity(new_val)

        # ---- public API ------------------------------------------------

        def show_overlay(self) -> None:
            """Show the overlay and start the refresh timer."""
            self.show()
            self._timer.start()
            self._refresh_state()

        def hide_overlay(self) -> None:
            """Hide the overlay and stop the refresh timer."""
            self._timer.stop()
            self.hide()
            self.overlay_closed.emit()

        def set_cheat_manager(self, cm: CheatManager) -> None:
            self.cheat_manager = cm

        def cleanup(self) -> None:
            """Stop timers and release resources."""
            self._timer.stop()

else:
    # ----- Stubs when PyQt6 is unavailable -----

    class _UnitStatsWidget:  # type: ignore[no-redef]
        """Stub for _UnitStatsWidget when PyQt6 is not installed."""

        def __init__(self, *args: Any, **kwargs: Any):
            pass

        def update_stats(self, stats: Dict[str, Any]) -> None:
            pass

    class _ActiveCheatsSummary:  # type: ignore[no-redef]
        """Stub for _ActiveCheatsSummary when PyQt6 is not installed."""

        def __init__(self, *args: Any, **kwargs: Any):
            pass

        def update_active_cheats(self, active_types: list) -> None:
            pass

    class BattleMapOverlay:  # type: ignore[no-redef]
        """Stub when PyQt6 is unavailable."""

        def __init__(self, *args: Any, **kwargs: Any):
            self.cheat_manager = kwargs.get("cheat_manager")
            self._visible = False

        class overlay_closed:
            """Fake signal stub."""
            @staticmethod
            def connect(*a: Any, **kw: Any) -> None:
                pass

            @staticmethod
            def emit(*a: Any, **kw: Any) -> None:
                pass

        def show_overlay(self) -> None:
            self._visible = True

        def hide_overlay(self) -> None:
            self._visible = False

        def isVisible(self) -> bool:
            return self._visible

        def set_cheat_manager(self, cm: Any) -> None:
            self.cheat_manager = cm

        def cleanup(self) -> None:
            pass
