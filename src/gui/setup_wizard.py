"""
Napoleon-themed first-run setup wizard.
"""

from __future__ import annotations

from typing import Dict, Optional

try:
    from PyQt6.QtCore import Qt
    from PyQt6.QtWidgets import (
        QCheckBox,
        QComboBox,
        QDialog,
        QDialogButtonBox,
        QFileDialog,
        QFormLayout,
        QFrame,
        QHBoxLayout,
        QLabel,
        QLineEdit,
        QPushButton,
        QTextBrowser,
        QVBoxLayout,
    )
    PYQT_AVAILABLE = True
except ImportError:
    PYQT_AVAILABLE = False

from src.config.settings import Config, ConfigManager
from src.trainer.overlay import OverlayAnimationStyle

PANEL_THEME_OPTIONS: Dict[str, str] = {
    "napoleon_gold": "Napoleon Gold",
    "imperial_blue": "Imperial Blue",
    "royal_purple": "Royal Purple",
    "battlefield_steel": "Battlefield Steel",
    "midnight_command": "Midnight Command",
}


def panel_theme_options() -> Dict[str, str]:
    """Return available control-panel themes."""
    return dict(PANEL_THEME_OPTIONS)


def normalize_panel_theme(value: Optional[str]) -> str:
    """Normalize a theme slug to a supported control-panel theme."""
    if value in PANEL_THEME_OPTIONS:
        return value
    return "napoleon_gold"


def panel_theme_name_for_value(value: Optional[str]) -> str:
    """Return the display label for a theme slug."""
    return PANEL_THEME_OPTIONS[normalize_panel_theme(value)]


def panel_theme_value_for_name(name: str) -> str:
    """Return the theme slug for a display label."""
    reverse = {label: value for value, label in PANEL_THEME_OPTIONS.items()}
    return reverse.get(name, "napoleon_gold")


def apply_setup_choices(
    config: Config,
    *,
    theme_name: str,
    overlay_preset: str,
    auto_backup: bool,
    game_path: str = "",
    backup_path: str = "",
) -> Config:
    """Apply first-run selections to the configuration."""
    config.ui_theme = panel_theme_value_for_name(theme_name)
    config.overlay_preset = overlay_preset
    config.overlay_animation = OverlayAnimationStyle.resolve_preset(overlay_preset)["animation"]
    config.auto_backup = auto_backup
    config.setup_completed = True
    config.paths.napoleon_install = game_path.strip() or None
    config.paths.backup_directory = backup_path.strip() or None
    return config


if PYQT_AVAILABLE:
    class FirstRunSetupWizard(QDialog):
        """Simple first-run setup wizard for the Napoleon control panel."""

        def __init__(self, config: Config, parent=None):
            super().__init__(parent)
            self._config = config
            self.setWindowTitle("👑 Napoleon Deployment Wizard")
            self.setMinimumSize(760, 560)
            self._init_ui()

        def _init_ui(self) -> None:
            """Build the dialog UI."""
            layout = QVBoxLayout(self)
            layout.setSpacing(16)

            title = QLabel("👑 Welcome, Marshal")
            title.setStyleSheet("font-size: 28px; font-weight: bold; color: #f1c40f;")
            layout.addWidget(title)

            subtitle = QLabel(
                "Set your first campaign preferences before Napoleon's command panel opens."
            )
            subtitle.setWordWrap(True)
            subtitle.setStyleSheet("font-size: 14px; color: #f8e7a1;")
            layout.addWidget(subtitle)

            overview = QTextBrowser()
            overview.setReadOnly(True)
            overview.setOpenExternalLinks(False)
            overview.setHtml(
                """
                <h3 style='color:#d4af37;'>What this mod gives you</h3>
                <ul>
                    <li>Hotkey-driven campaign and battle cheats</li>
                    <li>Overlay animations inspired by Napoleon Total War battles</li>
                    <li>Save-file and memory-editing tools for faster setup</li>
                </ul>
                <p>
                    Choose a command theme, decide how dramatic the overlay should feel,
                    and optionally point the engine at your Napoleon Total War install.
                </p>
                """
            )
            overview.setStyleSheet(
                "background-color: rgba(26, 37, 47, 230); color: #f0e6c8; border: 1px solid #d4af37;"
            )
            layout.addWidget(overview, 1)

            card = QFrame()
            card.setStyleSheet(
                """
                QFrame {
                    background-color: rgba(26, 37, 47, 230);
                    border: 1px solid #d4af37;
                    border-radius: 10px;
                }
                QLabel {
                    color: #f0e6c8;
                }
                QLineEdit, QComboBox {
                    background-color: #2c3e50;
                    color: #f8e7a1;
                    border: 1px solid #d4af37;
                    border-radius: 4px;
                    padding: 6px;
                }
                QCheckBox {
                    color: #f8e7a1;
                }
                QPushButton {
                    background-color: #2c3e50;
                    color: #f8e7a1;
                    border: 1px solid #d4af37;
                    border-radius: 4px;
                    padding: 6px 10px;
                }
                """
            )
            card_layout = QFormLayout(card)

            self.theme_combo = QComboBox()
            for _, label in panel_theme_options().items():
                self.theme_combo.addItem(label)
            self.theme_combo.setCurrentText(panel_theme_name_for_value(self._config.ui_theme))
            card_layout.addRow("Imperial theme:", self.theme_combo)

            self.overlay_preset_combo = QComboBox()
            preset_definitions = OverlayAnimationStyle.preset_definitions()
            for value, preset in preset_definitions.items():
                self.overlay_preset_combo.addItem(preset["name"], value)
            current_preset = self._config.overlay_preset or "balanced_command"
            current_index = self.overlay_preset_combo.findData(current_preset)
            if current_index >= 0:
                self.overlay_preset_combo.setCurrentIndex(current_index)
            self.overlay_preset_combo.currentIndexChanged.connect(self._update_preset_summary)
            card_layout.addRow("Overlay preset:", self.overlay_preset_combo)

            self.preset_summary = QLabel()
            self.preset_summary.setWordWrap(True)
            self.preset_summary.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
            card_layout.addRow("Preset briefing:", self.preset_summary)

            self.auto_backup_checkbox = QCheckBox("Create backups before major edits")
            self.auto_backup_checkbox.setChecked(self._config.auto_backup)
            card_layout.addRow(self.auto_backup_checkbox)

            self.game_path_edit = QLineEdit(self._config.paths.napoleon_install or "")
            self.game_path_edit.setPlaceholderText("Optional: point to your Napoleon Total War folder")
            game_path_row = QHBoxLayout()
            game_path_row.addWidget(self.game_path_edit)
            browse_game_button = QPushButton("Browse…")
            browse_game_button.clicked.connect(self._browse_game_path)
            game_path_row.addWidget(browse_game_button)
            card_layout.addRow("Game path:", game_path_row)

            self.backup_path_edit = QLineEdit(self._config.paths.backup_directory or "")
            self.backup_path_edit.setPlaceholderText("Optional: choose a backup folder")
            backup_row = QHBoxLayout()
            backup_row.addWidget(self.backup_path_edit)
            browse_backup_button = QPushButton("Browse…")
            browse_backup_button.clicked.connect(self._browse_backup_path)
            backup_row.addWidget(browse_backup_button)
            card_layout.addRow("Backup path:", backup_row)

            layout.addWidget(card)

            buttons = QDialogButtonBox(
                QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
            )
            buttons.button(QDialogButtonBox.StandardButton.Ok).setText("Deploy the Grand Armee")
            buttons.button(QDialogButtonBox.StandardButton.Cancel).setText("Retreat")
            buttons.accepted.connect(self.accept)
            buttons.rejected.connect(self.reject)
            layout.addWidget(buttons)

            self.setStyleSheet("QDialog { background-color: #141b22; }")
            self._update_preset_summary()

        def _browse_game_path(self) -> None:
            """Select the game installation directory."""
            directory = QFileDialog.getExistingDirectory(self, "Select Napoleon Total War Folder")
            if directory:
                self.game_path_edit.setText(directory)

        def _browse_backup_path(self) -> None:
            """Select a backup directory."""
            directory = QFileDialog.getExistingDirectory(self, "Select Backup Folder")
            if directory:
                self.backup_path_edit.setText(directory)

        def _update_preset_summary(self) -> None:
            """Refresh the preset description label."""
            preset_value = self.overlay_preset_combo.currentData()
            preset = OverlayAnimationStyle.resolve_preset(preset_value)
            self.preset_summary.setText(
                f"{preset['description']} Uses the {OverlayAnimationStyle.display_names()[preset['animation']]} animation."
            )

        def apply(self, config_manager: ConfigManager) -> bool:
            """Persist the selected setup values to the config manager."""
            apply_setup_choices(
                config_manager.config,
                theme_name=self.theme_combo.currentText(),
                overlay_preset=self.overlay_preset_combo.currentData(),
                auto_backup=self.auto_backup_checkbox.isChecked(),
                game_path=self.game_path_edit.text(),
                backup_path=self.backup_path_edit.text(),
            )
            return config_manager.save()


def run_first_run_setup(app, config_manager: ConfigManager) -> bool:
    """Show the first-run setup wizard if configuration is not completed."""
    if config_manager.config.setup_completed:
        return True

    if not PYQT_AVAILABLE:
        return False

    wizard = FirstRunSetupWizard(config_manager.config)
    if wizard.exec() != QDialog.DialogCode.Accepted:
        return False
    return wizard.apply(config_manager)
