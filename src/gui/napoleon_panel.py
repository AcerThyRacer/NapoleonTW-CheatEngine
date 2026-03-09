"""
Napoleon-Themed Control Panel with Animations
A fully customizable, animated control panel for Napoleon Total War cheats.
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
        QProgressBar, QStackedWidget
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


class CheatCategory(Enum):
    """Categories of cheats for organization."""
    TREASURY = "treasury"
    MILITARY = "military"
    CAMPAIGN = "campaign"
    BATTLE = "battle"
    DIPLOMACY = "diplomacy"
    QUALITY_OF_LIFE = "quality"


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
    """
    
    def __init__(self):
        super().__init__()
        
        self.cheat_states: Dict[str, bool] = {}
        self.current_theme = "napoleon_gold"
        
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
        
        # Header
        header = self._create_header()
        main_layout.addWidget(header)
        
        # Category tabs
        self.category_tabs = self._create_category_tabs()
        main_layout.addWidget(self.category_tabs)
        
        # Status bar
        self._create_status_bar()
    
    def _create_header(self) -> QWidget:
        """Create Napoleon-themed header."""
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
        
        # Imperial eagle icon
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
        
        # Crown icon
        crown_label = QLabel("👑")
        crown_label.setFont(QFont("Segoe UI Emoji", 48))
        layout.addWidget(crown_label)
        
        return header
    
    def _create_category_tabs(self) -> QStackedWidget:
        """Create category navigation tabs."""
        self.stacked_widget = QStackedWidget()
        
        # Tab buttons
        tab_buttons = QWidget()
        tab_layout = QHBoxLayout()
        tab_buttons.setLayout(tab_layout)
        
        categories = [
            ("💰", "Treasury", CheatCategory.TREASURY),
            ("⚔️", "Military", CheatCategory.MILITARY),
            ("🏰", "Campaign", CheatCategory.CAMPAIGN),
            ("🛡️", "Battle", CheatCategory.BATTLE),
            ("🤝", "Diplomacy", CheatCategory.DIPLOMACY),
            ("⚙️", "Settings", None),
        ]
        
        for icon, name, category in categories:
            btn = QPushButton(f"{icon} {name}")
            btn.setCheckable(True)
            btn.setFont(QFont("Georgia", 12, QFont.Weight.Bold))
            btn.setStyleSheet("""
                QPushButton {
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                        stop:0 #34495e, stop:1 #2c3e50);
                    border: 2px solid #d4af37;
                    border-radius: 8px;
                    color: #d4af37;
                    padding: 15px 25px;
                    min-width: 150px;
                }
                QPushButton:hover {
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                        stop:0 #3d566e, stop:1 #34495e);
                    border: 2px solid #f1c40f;
                }
                QPushButton:checked {
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                        stop:0 #d4af37, stop:1 #f1c40f);
                    color: #1a252f;
                }
            """)
            
            if category:
                btn.clicked.connect(
                    lambda checked, cat=category: self._switch_category(cat)
                )
            else:
                btn.clicked.connect(
                    lambda checked: self._switch_category(None)
                )
            
            tab_layout.addWidget(btn)
        
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
        self.theme_combo.addItems([
            "Napoleon Gold",
            "Imperial Blue",
            "Royal Purple",
            "Battlefield Steel",
            "Midnight Command"
        ])
        self.theme_combo.currentTextChanged.connect(self._on_theme_changed)
        theme_layout.addRow("Theme:", self.theme_combo)
        
        theme_group.setLayout(theme_layout)
        layout.addWidget(theme_group)
        
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
        self.statusBar().showMessage("🎉 All cheats activated! Vive l'Empereur!", 3000)
    
    def _deactivate_all_cheats(self):
        """Deactivate all cheats."""
        for command in self.commands:
            self.cheat_states[command.id] = False
        self.statusBar().showMessage("All cheats deactivated", 2000)
    
    def _on_theme_changed(self, theme_name: str):
        """Handle theme change."""
        self.current_theme = theme_name.lower().replace(" ", "_")
        self._apply_theme()
        self.statusBar().showMessage(f"Theme changed to {theme_name}", 2000)
    
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
    
    window = NapoleonControlPanel()
    window.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
