"""
Settings tab for the GUI.
"""

try:
    from PyQt6.QtWidgets import (
        QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
        QGroupBox, QFormLayout, QLineEdit, QFileDialog, QCheckBox,
        QComboBox, QMessageBox
    )
    from PyQt6.QtCore import Qt
    PYQT_AVAILABLE = True
except ImportError:
    PYQT_AVAILABLE = False

from src.utils import (
    get_platform,
    get_steam_path,
    get_napoleon_install_path,
    get_save_game_directory,
    get_scripts_directory,
)


class SettingsTab(QWidget):
    """
    Settings tab widget.
    """
    
    def __init__(self):
        """Initialize settings tab."""
        super().__init__()
        
        self.settings = {}
        self._load_settings()
        self._init_ui()
    
    def _init_ui(self) -> None:
        """Initialize user interface."""
        layout = QVBoxLayout()
        
        # Platform info
        platform_group = self._create_platform_group()
        layout.addWidget(platform_group)
        
        # Paths configuration
        paths_group = self._create_paths_group()
        layout.addWidget(paths_group)
        
        # Application settings
        app_group = self._create_app_settings_group()
        layout.addWidget(app_group)
        
        # Backup settings
        backup_group = self._create_backup_group()
        layout.addWidget(backup_group)
        
        # Action buttons
        button_layout = QHBoxLayout()
        
        self.save_settings_btn = QPushButton("Save Settings")
        self.save_settings_btn.clicked.connect(self._save_settings)
        button_layout.addWidget(self.save_settings_btn)
        
        self.reset_settings_btn = QPushButton("Reset to Defaults")
        self.reset_settings_btn.clicked.connect(self._reset_settings)
        button_layout.addWidget(self.reset_settings_btn)
        
        self.detect_paths_btn = QPushButton("Auto-Detect Paths")
        self.detect_paths_btn.clicked.connect(self._detect_paths)
        button_layout.addWidget(self.detect_paths_btn)
        
        layout.addLayout(button_layout)
        
        self.setLayout(layout)
    
    def _create_platform_group(self) -> QGroupBox:
        """Create platform information group."""
        group = QGroupBox("Platform Information")
        layout = QFormLayout()
        
        platform_name = get_platform()
        
        layout.addRow("Platform:", QLabel(platform_name.capitalize()))
        layout.addRow("Python Version:", QLabel(f"{__import__('sys').version}"))
        
        # PyQt6 version
        try:
            from PyQt6.QtCore import PYQT_VERSION_STR
            layout.addRow("PyQt6 Version:", QLabel(PYQT_VERSION_STR))
        except ImportError:
            layout.addRow("PyQt6 Version:", QLabel("Not installed"))
        
        group.setLayout(layout)
        return group
    
    def _create_paths_group(self) -> QGroupBox:
        """Create paths configuration group."""
        group = QGroupBox("Game Paths")
        layout = QFormLayout()
        
        # Game installation path
        self.game_path_edit = QLineEdit()
        self.game_path_edit.setPlaceholderText("Auto-detect...")
        game_browse_btn = QPushButton("Browse...")
        game_browse_btn.clicked.connect(self._browse_game_path)
        
        game_path_layout = QHBoxLayout()
        game_path_layout.addWidget(self.game_path_edit)
        game_path_layout.addWidget(game_browse_btn)
        layout.addRow("Game Installation:", game_path_layout)
        
        # Save game directory
        self.save_path_edit = QLineEdit()
        self.save_path_edit.setPlaceholderText("Auto-detect...")
        save_browse_btn = QPushButton("Browse...")
        save_browse_btn.clicked.connect(self._browse_save_path)
        
        save_path_layout = QHBoxLayout()
        save_path_layout.addWidget(self.save_path_edit)
        save_path_layout.addWidget(save_browse_btn)
        layout.addRow("Save Games:", save_path_layout)
        
        # Scripts directory
        self.scripts_path_edit = QLineEdit()
        self.scripts_path_edit.setPlaceholderText("Auto-detect...")
        scripts_browse_btn = QPushButton("Browse...")
        scripts_browse_btn.clicked.connect(self._browse_scripts_path)
        
        scripts_path_layout = QHBoxLayout()
        scripts_path_layout.addWidget(self.scripts_path_edit)
        scripts_path_layout.addWidget(scripts_browse_btn)
        layout.addRow("Scripts:", scripts_path_layout)
        
        group.setLayout(layout)
        return group
    
    def _create_app_settings_group(self) -> QGroupBox:
        """Create application settings group."""
        group = QGroupBox("Application Settings")
        layout = QFormLayout()
        
        # Language
        self.language_combo = QComboBox()
        self.language_combo.addItems(["English", "French", "German", "Spanish", "Russian"])
        layout.addRow("Language:", self.language_combo)
        
        # Theme
        self.theme_combo = QComboBox()
        self.theme_combo.addItems(["Dark", "Light", "System"])
        layout.addRow("Theme:", self.theme_combo)
        
        # Auto-save
        self.auto_save_checkbox = QCheckBox("Enable auto-save before modifications")
        self.auto_save_checkbox.setChecked(True)
        layout.addRow(self.auto_save_checkbox)
        
        # Confirm deletions
        self.confirm_delete_checkbox = QCheckBox("Confirm before deleting files")
        self.confirm_delete_checkbox.setChecked(True)
        layout.addRow(self.confirm_delete_checkbox)
        
        group.setLayout(layout)
        return group
    
    def _create_backup_group(self) -> QGroupBox:
        """Create backup settings group."""
        group = QGroupBox("Backup Settings")
        layout = QFormLayout()
        
        # Backup directory
        self.backup_path_edit = QLineEdit()
        self.backup_path_edit.setPlaceholderText("Default: Same directory as file")
        backup_browse_btn = QPushButton("Browse...")
        backup_browse_btn.clicked.connect(self._browse_backup_path)
        
        backup_path_layout = QHBoxLayout()
        backup_path_layout.addWidget(self.backup_path_edit)
        backup_path_layout.addWidget(backup_browse_btn)
        layout.addRow("Backup Directory:", backup_path_layout)
        
        # Max backups
        self.max_backups_edit = QLineEdit("5")
        layout.addRow("Maximum Backups per File:", self.max_backups_edit)
        
        # Backup on load
        self.backup_on_load_checkbox = QCheckBox("Create backup when loading files")
        self.backup_on_load_checkbox.setChecked(True)
        layout.addRow(self.backup_on_load_checkbox)
        
        group.setLayout(layout)
        return group
    
    def _load_settings(self) -> None:
        """Load saved settings."""
        # Default settings
        self.settings = {
            'game_path': '',
            'save_path': '',
            'scripts_path': '',
            'backup_path': '',
            'language': 'English',
            'theme': 'Dark',
            'auto_save': True,
            'confirm_delete': True,
            'max_backups': 5,
            'backup_on_load': True,
        }
        
        # Would load from config file here
    
    def _save_settings(self) -> None:
        """Save settings."""
        self.settings['game_path'] = self.game_path_edit.text()
        self.settings['save_path'] = self.save_path_edit.text()
        self.settings['scripts_path'] = self.scripts_path_edit.text()
        self.settings['backup_path'] = self.backup_path_edit.text()
        self.settings['language'] = self.language_combo.currentText()
        self.settings['theme'] = self.theme_combo.currentText()
        self.settings['auto_save'] = self.auto_save_checkbox.isChecked()
        self.settings['confirm_delete'] = self.confirm_delete_checkbox.isChecked()
        
        try:
            self.settings['max_backups'] = int(self.max_backups_edit.text())
        except ValueError:
            pass
        
        self.settings['backup_on_load'] = self.backup_on_load_checkbox.isChecked()
        
        # Would save to config file here
        
        QMessageBox.information(self, "Success", "Settings saved successfully")
    
    def _reset_settings(self) -> None:
        """Reset settings to defaults."""
        self._load_settings()
        self._update_ui_from_settings()
        QMessageBox.information(self, "Success", "Settings reset to defaults")
    
    def _update_ui_from_settings(self) -> None:
        """Update UI controls from settings."""
        self.game_path_edit.setText(self.settings.get('game_path', ''))
        self.save_path_edit.setText(self.settings.get('save_path', ''))
        self.scripts_path_edit.setText(self.settings.get('scripts_path', ''))
        self.backup_path_edit.setText(self.settings.get('backup_path', ''))
        
        language_index = self.language_combo.findText(self.settings.get('language', 'English'))
        if language_index >= 0:
            self.language_combo.setCurrentIndex(language_index)
        
        theme_index = self.theme_combo.findText(self.settings.get('theme', 'Dark'))
        if theme_index >= 0:
            self.theme_combo.setCurrentIndex(theme_index)
        
        self.auto_save_checkbox.setChecked(self.settings.get('auto_save', True))
        self.confirm_delete_checkbox.setChecked(self.settings.get('confirm_delete', True))
        self.max_backups_edit.setText(str(self.settings.get('max_backups', 5)))
        self.backup_on_load_checkbox.setChecked(self.settings.get('backup_on_load', True))
    
    def _detect_paths(self) -> None:
        """Auto-detect game paths."""
        detected = False
        
        # Detect game installation
        game_path = get_napoleon_install_path()
        if game_path:
            self.game_path_edit.setText(str(game_path))
            detected = True
        
        # Detect save directory
        save_path = get_save_game_directory()
        if save_path:
            self.save_path_edit.setText(str(save_path))
            detected = True
        
        # Detect scripts directory
        scripts_path = get_scripts_directory()
        if scripts_path:
            self.scripts_path_edit.setText(str(scripts_path))
            detected = True
        
        if detected:
            QMessageBox.information(
                self,
                "Detection Complete",
                "Successfully detected game paths."
            )
        else:
            QMessageBox.warning(
                self,
                "Detection Failed",
                "Could not auto-detect game paths. Please set them manually."
            )
    
    def _browse_game_path(self) -> None:
        """Browse for game installation path."""
        path = QFileDialog.getExistingDirectory(
            self,
            "Select Game Installation Directory"
        )
        if path:
            self.game_path_edit.setText(path)
    
    def _browse_save_path(self) -> None:
        """Browse for save game directory."""
        path = QFileDialog.getExistingDirectory(
            self,
            "Select Save Game Directory"
        )
        if path:
            self.save_path_edit.setText(path)
    
    def _browse_scripts_path(self) -> None:
        """Browse for scripts directory."""
        path = QFileDialog.getExistingDirectory(
            self,
            "Select Scripts Directory"
        )
        if path:
            self.scripts_path_edit.setText(path)
    
    def _browse_backup_path(self) -> None:
        """Browse for backup directory."""
        path = QFileDialog.getExistingDirectory(
            self,
            "Select Backup Directory"
        )
        if path:
            self.backup_path_edit.setText(path)
    
    def cleanup(self) -> None:
        """Cleanup resources."""
        self._save_settings()
