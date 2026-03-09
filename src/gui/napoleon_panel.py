"""
Napoleon-Themed Control Panel with Animations
A fully customizable, animated control panel for Napoleon Total War cheats.

2026 edition — features parallax battle-scene background, motion-blur
particle effects, live statistics dashboard, icon-only category navigation
with tooltips, cheat search, and sound-effect integration.
"""

import sys
from pathlib import Path
from typing import Dict, List, Optional, Callable
from dataclasses import dataclass
from enum import Enum

try:
    from PyQt6.QtWidgets import (
        QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
        QLabel, QFrame, QGridLayout, QScrollArea, QSlider, QComboBox,
        QCheckBox, QGroupBox, QSpinBox, QDialog, QDialogButtonBox,
        QFormLayout, QSpacerItem, QSizePolicy, QGraphicsDropShadowEffect,
        QProgressBar, QStackedWidget, QLineEdit, QToolButton, QToolTip
    )
    from PyQt6.QtCore import (
        Qt, QTimer, QPropertyAnimation, QEasingCurve, QPoint, QSize,
        pyqtSignal, QParallelAnimationGroup, QSequentialAnimationGroup
    )
    from PyQt6.QtGui import (
        QFont, QColor, QPalette, QLinearGradient, QBrush, QIcon,
        QPainter, QPixmap, QPen, QFontDatabase
    )
    PYQT_AVAILABLE = True
except ImportError:
    PYQT_AVAILABLE = False
    print("PyQt6 required for GUI")

from src.config import ConfigManager
from src.gui.setup_wizard import (
    normalize_panel_theme,
    panel_theme_name_for_value,
    panel_theme_options,
    run_first_run_setup,
)
from src.trainer.overlay import OverlayAnimationStyle

ASSETS_DIR = Path(__file__).resolve().parents[2] / "assets"
ICONS_DIR = ASSETS_DIR / "icons"


class CheatCategory(Enum):
    """Categories of cheats for organization."""
    TREASURY = "treasury"
    MILITARY = "military"
    CAMPAIGN = "campaign"
    BATTLE = "battle"
    DIPLOMACY = "diplomacy"
    QUALITY_OF_LIFE = "quality"


# Maps each category to (SVG filename, fallback emoji, tooltip text).
CATEGORY_ICON_MAP: Dict[str, tuple] = {
    CheatCategory.TREASURY.value: ("treasury.svg", "💰", "Treasury — Imperial finances"),
    CheatCategory.MILITARY.value: ("sword.svg", "⚔️", "Military — Army commands"),
    CheatCategory.CAMPAIGN.value: ("campaign.svg", "🏰", "Campaign — Strategic options"),
    CheatCategory.BATTLE.value: ("shield.svg", "🛡️", "Battle — Combat modifiers"),
    CheatCategory.DIPLOMACY.value: ("diplomacy.svg", "🤝", "Diplomacy — Relations"),
    CheatCategory.QUALITY_OF_LIFE.value: ("quality.svg", "⚙️", "Quality of Life"),
}


def _load_category_icon(category_value: str, size: int = 32) -> "QIcon":
    """Load an SVG icon for *category_value*, falling back to an empty icon."""
    info = CATEGORY_ICON_MAP.get(category_value)
    if info is None:
        return QIcon()
    svg_name = info[0]
    path = ICONS_DIR / svg_name
    if path.exists():
        return QIcon(str(path))
    return QIcon()


@dataclass
class CheatCommand:
    """Represents a cheat command."""
    id: str
    name: str
    description: str
    category: CheatCategory
    icon: str  # Emoji or icon name
    default_value: int = 1
    min_value: int = 0
    max_value: int = 999999
    is_toggle: bool = True
    is_slider: bool = False


class AnimatedButton(QPushButton):
    """Custom button with Napoleon-themed animations."""
    
    def __init__(self, text: str, parent=None):
        super().__init__(text, parent)
        
        # Setup button styling
        self.setFixedHeight(60)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        
        # Create shadow effect
        self.shadow = QGraphicsDropShadowEffect()
        self.shadow.setBlurRadius(20)
        self.shadow.setXOffset(0)
        self.shadow.setYOffset(4)
        self.shadow.setColor(QColor(0, 0, 0, 100))
        self.setGraphicsEffect(self.shadow)
        
        # Animation for hover
        self.hover_animation = QPropertyAnimation(self, b"minimumSize")
        self.hover_animation.setDuration(200)
        self.hover_animation.setEasingCurve(QEasingCurve.Type.OutQuad)
        
        # Apply Napoleon theme
        self.apply_theme()
    
    def apply_theme(self):
        """Apply Napoleon-era styling."""
        self.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #2c3e50, stop:1 #1a252f);
                border: 2px solid #d4af37;
                border-radius: 8px;
                color: #d4af37;
                font-size: 16px;
                font-weight: bold;
                padding: 10px 20px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #34495e, stop:1 #2c3e50);
                border: 2px solid #f1c40f;
                color: #f1c40f;
            }
            QPushButton:pressed {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #1a252f, stop:1 #2c3e50);
                border: 2px solid #d4af37;
            }
            QPushButton:checked {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #d4af37, stop:1 #f1c40f);
                color: #1a252f;
                border: 2px solid #fff;
            }
        """)
    
    def enterEvent(self, event):
        """Animate on hover."""
        super().enterEvent(event)
        # Could add scale animation here
    
    def leaveEvent(self, event):
        """Reset on leave."""
        super().leaveEvent(event)


class CheatToggleButton(QWidget):
    """Custom toggle button for a cheat with visual feedback."""
    
    toggled = pyqtSignal(str, bool)  # cheat_id, state
    
    def __init__(self, command: CheatCommand, parent=None):
        super().__init__(parent)
        self.command = command
        self.is_active = False
        
        self._init_ui()
    
    def _init_ui(self):
        """Initialize the UI."""
        layout = QHBoxLayout()
        layout.setSpacing(10)
        layout.setContentsMargins(10, 10, 10, 10)
        
        # Icon/Emoji label
        self.icon_label = QLabel(self.command.icon)
        self.icon_label.setFont(QFont("Segoe UI Emoji", 24))
        self.icon_label.setFixedSize(50, 50)
        self.icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.icon_label)
        
        # Text container
        text_layout = QVBoxLayout()
        
        # Name
        self.name_label = QLabel(self.command.name)
        self.name_label.setFont(QFont("Georgia", 14, QFont.Weight.Bold))
        self.name_label.setStyleSheet("color: #d4af37;")
        text_layout.addWidget(self.name_label)
        
        # Description
        self.desc_label = QLabel(self.command.description)
        self.desc_label.setFont(QFont("Georgia", 10))
        self.desc_label.setStyleSheet("color: #95a5a6;")
        self.desc_label.setWordWrap(True)
        text_layout.addWidget(self.desc_label)
        
        layout.addLayout(text_layout)
        
        # Toggle switch
        self.toggle_btn = QPushButton("OFF")
        self.toggle_btn.setCheckable(True)
        self.toggle_btn.setFixedSize(80, 40)
        self.toggle_btn.clicked.connect(self._on_toggle)
        self._update_toggle_style()
        layout.addWidget(self.toggle_btn)
        
        self.setLayout(layout)
        
        # Apply frame styling
        self.setStyleSheet("""
            QWidget {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 rgba(44, 62, 80, 0.8), stop:1 rgba(26, 37, 47, 0.8));
                border: 1px solid #d4af37;
                border-radius: 8px;
            }
            QWidget:hover {
                border: 2px solid #f1c40f;
            }
        """)
    
    def _on_toggle(self, checked: bool):
        """Handle toggle."""
        self.is_active = checked
        self._update_toggle_style()
        self.toggled.emit(self.command.id, checked)
    
    def _update_toggle_style(self):
        """Update toggle button style."""
        if self.is_active:
            self.toggle_btn.setStyleSheet("""
                QPushButton {
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                        stop:0 #27ae60, stop:1 #2ecc71);
                    border: 2px solid #fff;
                    border-radius: 20px;
                    color: white;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                        stop:0 #2ecc71, stop:1 #27ae60);
                }
            """)
            self.toggle_btn.setText("ON")
        else:
            self.toggle_btn.setStyleSheet("""
                QPushButton {
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                        stop:0 #c0392b, stop:1 #e74c3c);
                    border: 2px solid #95a5a6;
                    border-radius: 20px;
                    color: white;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                        stop:0 #e74c3c, stop:1 #c0392b);
                }
            """)
            self.toggle_btn.setText("OFF")


class NapoleonControlPanel(QMainWindow):
    """
    Main Napoleon-themed control panel window.
    Fully customizable with animations and all commands.

    2026 edition with parallax battle-scene background, live stats dashboard,
    icon-only category navigation, cheat search bar, and sound effects.
    """

    def __init__(self, config_manager: Optional[ConfigManager] = None):
        super().__init__()

        self.config_manager = config_manager
        self.cheat_states: Dict[str, bool] = {}
        configured_theme = None
        if self.config_manager is not None:
            configured_theme = self.config_manager.config.ui_theme
        self.current_theme = normalize_panel_theme(configured_theme)

        # Lazy-load sound player
        try:
            from src.gui.animated_components import SoundEffectPlayer
            self._sound = SoundEffectPlayer(enabled=True)
        except Exception:
            self._sound = None

        self._toggle_widgets: List[CheatToggleButton] = []

        self._init_commands()
        self._init_ui()
        self._apply_theme()
    
    def _init_commands(self):
        """Initialize all cheat commands."""
        self.commands = [
            # Treasury Cheats
            CheatCommand(
                id="infinite_gold",
                name="Imperial Treasury",
                description="Fill the imperial coffers with unlimited gold",
                category=CheatCategory.TREASURY,
                icon="💰",
                default_value=999999
            ),
            CheatCommand(
                id="instant_recruitment",
                name="Instant Recruitment",
                description="Recruit armies instantly across the empire",
                category=CheatCategory.MILITARY,
                icon="⚔️",
                is_toggle=True
            ),
            CheatCommand(
                id="instant_construction",
                name="Rapid Construction",
                description="Complete buildings in one turn",
                category=CheatCategory.CAMPAIGN,
                icon="🏰",
                is_toggle=True
            ),
            CheatCommand(
                id="fast_research",
                name="Enlightenment Era",
                description="Complete technologies in one turn",
                category=CheatCategory.CAMPAIGN,
                icon="📚",
                is_toggle=True
            ),
            CheatCommand(
                id="unlimited_movement",
                name="Grand March",
                description="Armies never tire, unlimited movement",
                category=CheatCategory.MILITARY,
                icon="🚶",
                is_toggle=True
            ),
            CheatCommand(
                id="god_mode",
                name="Divine Protection",
                description="Your armies are invincible in battle",
                category=CheatCategory.BATTLE,
                icon="🛡️",
                is_toggle=True
            ),
            CheatCommand(
                id="unlimited_ammo",
                name="Infinite Munitions",
                description="Never run out of ammunition",
                category=CheatCategory.BATTLE,
                icon="🔫",
                is_toggle=True
            ),
            CheatCommand(
                id="high_morale",
                name="Grande Armée Spirit",
                description="Maximum morale for all units",
                category=CheatCategory.BATTLE,
                icon="🎖️",
                is_toggle=True
            ),
            CheatCommand(
                id="one_hit_kill",
                name="Devastating Artillery",
                description="All attacks deal maximum damage",
                category=CheatCategory.BATTLE,
                icon="💥",
                is_toggle=True
            ),
            CheatCommand(
                id="super_speed",
                name="Napoleonic Blitz",
                description="Accelerate time on the battlefield",
                category=CheatCategory.BATTLE,
                icon="⚡",
                is_slider=True,
                min_value=1,
                max_value=10,
                default_value=5
            ),
            CheatCommand(
                id="max_agents",
                name="Master Spies",
                description="Unlimited agent action points",
                category=CheatCategory.DIPLOMACY,
                icon="🕵️",
                is_toggle=True
            ),
            CheatCommand(
                id="free_diplomacy",
                name="Diplomatic Immunity",
                description="No penalties for diplomatic actions",
                category=CheatCategory.DIPLOMACY,
                icon="🤝",
                is_toggle=True
            ),
        ]
    
    def _init_ui(self):
        """Initialize the user interface."""
        self.setWindowTitle("👑 Napoleon's Command Panel")
        self.setMinimumSize(800, 600)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.resize(1400, 900)

        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        main_layout = QVBoxLayout()
        main_layout.setSpacing(0)
        main_layout.setContentsMargins(0, 0, 0, 0)
        central_widget.setLayout(main_layout)

        # --- Parallax battle-scene background (behind everything) ---
        try:
            from src.gui.animated_components import ParallaxBattleScene
            self._bg = ParallaxBattleScene(central_widget)
            self._bg.lower()
            self._bg.setGeometry(0, 0, self.width(), self.height())
        except Exception:
            self._bg = None

        # Header
        header = self._create_header()
        main_layout.addWidget(header)

        # --- Live Statistics Dashboard ---
        try:
            from src.gui.animated_components import LiveStatsDashboard
            self.stats_dashboard = LiveStatsDashboard()
        except Exception:
            self.stats_dashboard = None
        if self.stats_dashboard:
            main_layout.addWidget(self.stats_dashboard)

        # --- Search bar ---
        search_frame = QFrame()
        search_frame.setFixedHeight(44)
        search_frame.setStyleSheet("""
            QFrame {
                background: rgba(26, 37, 47, 220);
                border-bottom: 1px solid #d4af37;
            }
        """)
        search_layout = QHBoxLayout(search_frame)
        search_layout.setContentsMargins(16, 4, 16, 4)

        search_icon = QLabel("🔍")
        search_icon.setFixedWidth(24)
        search_layout.addWidget(search_icon)

        self._search_input = QLineEdit()
        self._search_input.setPlaceholderText("Search cheats…")
        self._search_input.setClearButtonEnabled(True)
        self._search_input.setStyleSheet("""
            QLineEdit {
                background: rgba(44, 62, 80, 180);
                border: 1px solid #d4af37;
                border-radius: 6px;
                color: #d4af37;
                padding: 4px 10px;
                font-size: 13px;
            }
            QLineEdit:focus {
                border: 1px solid #f1c40f;
            }
        """)
        self._search_input.textChanged.connect(self._on_search_changed)
        search_layout.addWidget(self._search_input)

        main_layout.addWidget(search_frame)

        # Category tabs
        self.category_tabs = self._create_category_tabs()
        main_layout.addWidget(self.category_tabs)

        # Status bar
        self._create_status_bar()
    
    def _create_header(self) -> QWidget:
        """Create Napoleon-themed header with cannon smoke."""
        header = QFrame()
        header.setFixedHeight(120)
        header.setStyleSheet("""
            QFrame {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #1a252f, stop:0.5 #2c3e50, stop:1 #1a252f);
                border-bottom: 3px solid #d4af37;
            }
        """)

        layout = QHBoxLayout()
        header.setLayout(layout)

        # Imperial eagle icon — try SVG first, fall back to emoji
        eagle_path = ICONS_DIR / "eagle.svg"
        if eagle_path.exists():
            eagle_label = QLabel()
            pm = QPixmap(str(eagle_path)).scaled(
                56, 56, Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            eagle_label.setPixmap(pm)
        else:
            eagle_label = QLabel("🦅")
            eagle_label.setFont(QFont("Segoe UI Emoji", 48))
        layout.addWidget(eagle_label)

        # Title
        title_layout = QVBoxLayout()

        title = QLabel("NAPOLEON'S COMMAND PANEL")
        title.setFont(QFont("Georgia", 28, QFont.Weight.Bold))
        title.setStyleSheet("color: #d4af37;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_layout.addWidget(title)

        subtitle = QLabel("Total War Control System")
        subtitle.setFont(QFont("Georgia", 14))
        subtitle.setStyleSheet("color: #95a5a6;")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_layout.addWidget(subtitle)

        layout.addLayout(title_layout)

        # Crown icon — try SVG first
        crown_path = ICONS_DIR / "crown.svg"
        if crown_path.exists():
            crown_label = QLabel()
            pm = QPixmap(str(crown_path)).scaled(
                56, 56, Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            crown_label.setPixmap(pm)
        else:
            crown_label = QLabel("👑")
            crown_label.setFont(QFont("Segoe UI Emoji", 48))
        layout.addWidget(crown_label)

        # Overlay cannon smoke on the header
        try:
            from src.gui.animated_components import CannonSmokeSystem
            self._header_smoke = CannonSmokeSystem(header)
            self._header_smoke.setGeometry(0, 0, 1400, 120)
            self._header_smoke.start_emitting()
            self._header_smoke.raise_()
        except Exception:
            self._header_smoke = None

        return header
    
    def _create_category_tabs(self) -> QStackedWidget:
        """Create category navigation tabs with icon-only buttons and tooltips."""
        self.stacked_widget = QStackedWidget()

        # Tab buttons
        tab_buttons = QWidget()
        tab_layout = QHBoxLayout()
        tab_layout.setSpacing(6)
        tab_buttons.setLayout(tab_layout)

        categories = [
            (CheatCategory.TREASURY,),
            (CheatCategory.MILITARY,),
            (CheatCategory.CAMPAIGN,),
            (CheatCategory.BATTLE,),
            (CheatCategory.DIPLOMACY,),
        ]

        self._tab_buttons: List[QToolButton] = []
        for (category,) in categories:
            info = CATEGORY_ICON_MAP.get(category.value, ("", "❓", category.value))
            svg_file, fallback_emoji, tooltip = info

            btn = QToolButton()
            btn.setCheckable(True)
            btn.setToolTip(tooltip)
            btn.setFixedSize(60, 60)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)

            icon = _load_category_icon(category.value)
            if not icon.isNull():
                btn.setIcon(icon)
                btn.setIconSize(QSize(36, 36))
            else:
                btn.setText(fallback_emoji)
                btn.setFont(QFont("Segoe UI Emoji", 22))

            btn.setStyleSheet("""
                QToolButton {
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                        stop:0 #34495e, stop:1 #2c3e50);
                    border: 2px solid #d4af37;
                    border-radius: 10px;
                }
                QToolButton:hover {
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                        stop:0 #3d566e, stop:1 #34495e);
                    border: 2px solid #f1c40f;
                }
                QToolButton:checked {
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                        stop:0 #d4af37, stop:1 #f1c40f);
                }
            """)

            btn.clicked.connect(
                lambda checked, cat=category: self._switch_category(cat)
            )
            tab_layout.addWidget(btn)
            self._tab_buttons.append(btn)

        # Settings button (gear icon)
        settings_btn = QToolButton()
        settings_btn.setCheckable(True)
        settings_btn.setToolTip("Settings — Theme, animations, presets")
        settings_btn.setFixedSize(60, 60)
        settings_btn.setCursor(Qt.CursorShape.PointingHandCursor)

        gear_icon_path = ICONS_DIR / "settings.svg"
        if gear_icon_path.exists():
            settings_btn.setIcon(QIcon(str(gear_icon_path)))
            settings_btn.setIconSize(QSize(36, 36))
        else:
            settings_btn.setText("⚙️")
            settings_btn.setFont(QFont("Segoe UI Emoji", 22))

        settings_btn.setStyleSheet("""
            QToolButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #34495e, stop:1 #2c3e50);
                border: 2px solid #d4af37;
                border-radius: 10px;
            }
            QToolButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #3d566e, stop:1 #34495e);
                border: 2px solid #f1c40f;
            }
            QToolButton:checked {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #d4af37, stop:1 #f1c40f);
            }
        """)
        settings_btn.clicked.connect(
            lambda checked: self._switch_category(None)
        )
        tab_layout.addWidget(settings_btn)
        self._tab_buttons.append(settings_btn)

        tab_layout.addStretch()

        # Content area
        content_widget = QWidget()
        content_layout = QVBoxLayout()
        content_widget.setLayout(content_layout)

        # Create pages for each category
        self.category_pages = {}
        for category in CheatCategory:
            page = self._create_category_page(category)
            self.stacked_widget.addWidget(page)
            self.category_pages[category] = page

        # Settings page
        settings_page = self._create_settings_page()
        self.stacked_widget.addWidget(settings_page)

        content_layout.addWidget(self.stacked_widget)

        # Container
        container = QWidget()
        container_layout = QVBoxLayout()
        container.setLayout(container_layout)
        container_layout.addWidget(tab_buttons)
        container_layout.addWidget(content_widget)

        return container
    
    def _create_category_page(self, category: CheatCategory) -> QWidget:
        """Create a page for a cheat category."""
        page = QWidget()
        layout = QGridLayout()
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)
        page.setLayout(layout)

        # Get commands for this category
        commands = [c for c in self.commands if c.category == category]

        # Add cheat toggles
        row = 0
        col = 0
        for i, command in enumerate(commands):
            toggle = CheatToggleButton(command)
            toggle.toggled.connect(self._on_cheat_toggled)
            self._toggle_widgets.append(toggle)

            layout.addWidget(toggle, row, col)

            col += 1
            if col >= 2:  # 2 columns
                col = 0
                row += 1

        # Add stretch to push content to top
        layout.setRowStretch(row + 1, 1)

        return page
    
    def _create_settings_page(self) -> QWidget:
        """Create settings page."""
        page = QWidget()
        layout = QVBoxLayout()
        page.setLayout(layout)
        
        # Theme selection
        theme_group = QGroupBox("🎨 Imperial Theme")
        theme_layout = QFormLayout()
        
        self.theme_combo = QComboBox()
        self.theme_combo.addItems(list(panel_theme_options().values()))
        self.theme_combo.setCurrentText(panel_theme_name_for_value(self.current_theme))
        self.theme_combo.currentTextChanged.connect(self._on_theme_changed)
        theme_layout.addRow("Theme:", self.theme_combo)
        
        theme_group.setLayout(theme_layout)
        layout.addWidget(theme_group)

        preset_group = QGroupBox("🎬 Overlay Presets")
        preset_layout = QFormLayout()

        self.overlay_preset_combo = QComboBox()
        preset_definitions = OverlayAnimationStyle.preset_definitions()
        for preset_name, preset in preset_definitions.items():
            self.overlay_preset_combo.addItem(preset["name"], preset_name)

        current_preset = "balanced_command"
        if self.config_manager is not None:
            current_preset = self.config_manager.config.overlay_preset or current_preset
        preset_index = self.overlay_preset_combo.findData(current_preset)
        if preset_index >= 0:
            self.overlay_preset_combo.setCurrentIndex(preset_index)
        self.overlay_preset_combo.currentIndexChanged.connect(self._on_overlay_preset_changed)
        preset_layout.addRow("Preset:", self.overlay_preset_combo)

        self.overlay_preset_summary = QLabel()
        self.overlay_preset_summary.setWordWrap(True)
        preset_layout.addRow("Field notes:", self.overlay_preset_summary)

        preset_group.setLayout(preset_layout)
        layout.addWidget(preset_group)
        
        # Animation settings
        anim_group = QGroupBox("⚡ Animation Settings")
        anim_layout = QFormLayout()
        
        self.animation_speed = QSlider(Qt.Orientation.Horizontal)
        self.animation_speed.setRange(1, 10)
        self.animation_speed.setValue(7)
        anim_layout.addRow("Animation Speed:", self.animation_speed)
        
        self.enable_sounds = QCheckBox("Enable Sound Effects")
        self.enable_sounds.setChecked(True)
        anim_layout.addRow(self.enable_sounds)
        
        anim_group.setLayout(anim_layout)
        layout.addWidget(anim_group)
        
        # Quick actions
        quick_group = QGroupBox("⚡ Quick Commands")
        quick_layout = QHBoxLayout()
        
        activate_all_btn = QPushButton("Activate All Cheats")
        activate_all_btn.clicked.connect(self._activate_all_cheats)
        quick_layout.addWidget(activate_all_btn)
        
        deactivate_all_btn = QPushButton("Deactivate All Cheats")
        deactivate_all_btn.clicked.connect(self._deactivate_all_cheats)
        quick_layout.addWidget(deactivate_all_btn)
        
        quick_group.setLayout(quick_layout)
        layout.addWidget(quick_group)
        
        layout.addStretch()
        self._update_overlay_preset_summary()
        return page
    
    def _switch_category(self, category: Optional[CheatCategory]):
        """Switch to a category page."""
        if category:
            index = list(CheatCategory).index(category)
            self.stacked_widget.setCurrentIndex(index)
        else:
            # Settings page
            self.stacked_widget.setCurrentIndex(len(CheatCategory))
    
    def _on_cheat_toggled(self, cheat_id: str, state: bool):
        """Handle cheat toggle."""
        self.cheat_states[cheat_id] = state

        # Play sound effect
        if self._sound:
            self._sound.play('activate' if state else 'deactivate')

        # Update live stats
        if self.stats_dashboard:
            active = sum(1 for v in self.cheat_states.values() if v)
            self.stats_dashboard.set_army_count(active)

        # Update status bar
        if state:
            command = next(c for c in self.commands if c.id == cheat_id)
            self.statusBar().showMessage(f"✓ Activated: {command.name}", 3000)
        else:
            self.statusBar().showMessage("Cheat deactivated", 2000)
    
    def _activate_all_cheats(self):
        """Activate all cheats."""
        for command in self.commands:
            self.cheat_states[command.id] = True
        if self._sound:
            self._sound.play('victory')
        if self.stats_dashboard:
            self.stats_dashboard.set_army_count(len(self.commands))
        self.statusBar().showMessage("🎉 All cheats activated! Vive l'Empereur!", 3000)

    def _deactivate_all_cheats(self):
        """Deactivate all cheats."""
        for command in self.commands:
            self.cheat_states[command.id] = False
        if self._sound:
            self._sound.play('deactivate')
        if self.stats_dashboard:
            self.stats_dashboard.set_army_count(0)
        self.statusBar().showMessage("All cheats deactivated", 2000)
    
    def _on_theme_changed(self, theme_name: str):
        """Handle theme change."""
        reverse_themes = {label: value for value, label in panel_theme_options().items()}
        self.current_theme = reverse_themes.get(theme_name, "napoleon_gold")
        self._apply_theme()
        if self.config_manager is not None:
            self.config_manager.config.ui_theme = self.current_theme
            self.config_manager.save()
        self.statusBar().showMessage(f"Theme changed to {theme_name}", 2000)

    def _on_overlay_preset_changed(self, index: int):
        """Handle overlay preset changes."""
        if index < 0:
            return
        self._update_overlay_preset_summary()
        preset_name = self.overlay_preset_combo.itemData(index)
        preset = OverlayAnimationStyle.resolve_preset(preset_name)
        if self.config_manager is not None:
            self.config_manager.config.overlay_preset = preset_name
            self.config_manager.config.overlay_animation = preset["animation"]
            self.config_manager.save()
        self.statusBar().showMessage(f"Overlay preset ready: {preset['name']}", 2000)

    def _update_overlay_preset_summary(self):
        """Refresh the overlay preset summary label."""
        if not hasattr(self, "overlay_preset_combo"):
            return
        preset_name = self.overlay_preset_combo.currentData()
        preset = OverlayAnimationStyle.resolve_preset(preset_name)
        animation_name = OverlayAnimationStyle.display_names()[preset["animation"]]
        self.overlay_preset_summary.setText(
            f"{preset['description']} Uses {animation_name} for the overlay."
        )
    
    def _apply_theme(self):
        """Apply current theme."""
        themes = {
            "napoleon_gold": {
                "primary": "#d4af37",
                "secondary": "#f1c40f",
                "background": "#1a252f",
                "panel": "#2c3e50",
            },
            "imperial_blue": {
                "primary": "#3498db",
                "secondary": "#2980b9",
                "background": "#1a252f",
                "panel": "#2c3e50",
            },
            "royal_purple": {
                "primary": "#9b59b6",
                "secondary": "#8e44ad",
                "background": "#1a252f",
                "panel": "#2c3e50",
            },
            "battlefield_steel": {
                "primary": "#95a5a6",
                "secondary": "#7f8c8d",
                "background": "#1a252f",
                "panel": "#2c3e50",
            },
            "midnight_command": {
                "primary": "#e74c3c",
                "secondary": "#c0392b",
                "background": "#0f1419",
                "panel": "#1a252f",
            },
        }
        
        theme = themes.get(self.current_theme, themes["napoleon_gold"])
        
        # Update stylesheet
        self.setStyleSheet(f"""
            QMainWindow {{
                background-color: {theme['background']};
            }}
            QStatusBar {{
                background-color: {theme['panel']};
                color: {theme['primary']};
                border-top: 2px solid {theme['primary']};
            }}
        """)
    
    def _create_status_bar(self):
        """Create status bar."""
        self.statusBar().showMessage("Ready - Attach to Napoleon Total War process to begin", 5000)
        self.statusBar().setStyleSheet("""
            QStatusBar {
                background-color: #2c3e50;
                color: #d4af37;
                border-top: 2px solid #d4af37;
                padding: 5px;
            }
        """)

    # ── Search & resize helpers ─────────────────────────────

    def _on_search_changed(self, text: str) -> None:
        """Filter visible cheat toggles based on the search query."""
        query = text.strip().lower()
        for toggle in self._toggle_widgets:
            if not query:
                toggle.setVisible(True)
            else:
                match = (
                    query in toggle.command.name.lower()
                    or query in toggle.command.description.lower()
                    or query in toggle.command.id.lower()
                )
                toggle.setVisible(match)

    def resizeEvent(self, event) -> None:  # noqa: N802
        """Keep the parallax background sized to the window."""
        super().resizeEvent(event)
        if getattr(self, "_bg", None) is not None:
            self._bg.setGeometry(0, 0, self.width(), self.height())


def main():
    """Main entry point for the control panel."""
    if not PYQT_AVAILABLE:
        print("PyQt6 is required. Install with: pip install PyQt6")
        sys.exit(1)
    
    from PyQt6.QtWidgets import QApplication
    from PyQt6.QtGui import QPalette, QColor
    
    app = QApplication(sys.argv)
    
    # Set dark palette
    palette = QPalette()
    palette.setColor(QPalette.ColorRole.Window, QColor(26, 37, 47))
    palette.setColor(QPalette.ColorRole.WindowText, QColor(212, 175, 55))
    palette.setColor(QPalette.ColorRole.Base, QColor(44, 62, 80))
    palette.setColor(QPalette.ColorRole.AlternateBase, QColor(26, 37, 47))
    palette.setColor(QPalette.ColorRole.Text, QColor(212, 175, 55))
    palette.setColor(QPalette.ColorRole.Button, QColor(44, 62, 80))
    palette.setColor(QPalette.ColorRole.ButtonText, QColor(212, 175, 55))
    palette.setColor(QPalette.ColorRole.Highlight, QColor(212, 175, 55))
    palette.setColor(QPalette.ColorRole.HighlightedText, QColor(26, 37, 47))
    app.setPalette(palette)

    config_manager = ConfigManager()
    config_manager.load()
    if not run_first_run_setup(app, config_manager):
        return

    window = NapoleonControlPanel(config_manager=config_manager)
    window.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
