"""
Main window for Napoleon Total War Cheat Engine.
"""

import sys
from pathlib import Path

try:
    from PyQt6.QtWidgets import (
        QMainWindow, QApplication, QTabWidget, QWidget,
        QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
        QStatusBar, QMenuBar, QMenu, QMessageBox
    )
    from PyQt6.QtCore import Qt
    from PyQt6.QtGui import QIcon
    PYQT_AVAILABLE = True
except ImportError:
    PYQT_AVAILABLE = False
    print("Warning: PyQt6 not installed. GUI will not be available.")
    print("Install with: pip install PyQt6")

from .memory_tab import MemoryScannerTab
from .file_editor_tab import FileEditorTab
from .trainer_tab import TrainerTab
from .settings_tab import SettingsTab
from .battle_overlay import BattleMapOverlay
from .preset_manager import PresetManagerTab
from src.config import ConfigManager
from .setup_wizard import run_first_run_setup


class MainWindow(QMainWindow):
    """
    Main application window.
    """
    
    def __init__(self):
        """Initialize main window."""
        if not PYQT_AVAILABLE:
            raise ImportError("PyQt6 is required for the GUI")
        
        super().__init__()
        
        self.setWindowTitle("Napoleon Total War Cheat Engine")
        self.setGeometry(100, 100, 1200, 800)
        
        # Create central widget and layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        
        # Create tab widget
        self.tab_widget = QTabWidget()
        main_layout.addWidget(self.tab_widget)
        
        # Add tabs
        self._create_tabs()
        
        # Create menu bar
        self._create_menu_bar()
        
        # Create status bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Ready")
        
        # Apply stylesheet
        self._apply_stylesheet()
        
        print("Main window initialized")
    
    def _create_tabs(self) -> None:
        """Create and add all tabs."""
        # Memory Scanner Tab
        self.memory_tab = MemoryScannerTab()
        self.tab_widget.addTab(self.memory_tab, "🔍 Memory Scanner")
        
        # File Editor Tab
        self.file_editor_tab = FileEditorTab()
        self.tab_widget.addTab(self.file_editor_tab, "📁 File Editor")
        
        # Trainer Tab
        self.trainer_tab = TrainerTab()
        self.tab_widget.addTab(self.trainer_tab, "🎮 Trainer")
        
        # Preset Manager Tab
        self.preset_tab = PresetManagerTab(
            cheat_manager=self.trainer_tab.cheat_manager
        )
        self.tab_widget.addTab(self.preset_tab, "📦 Presets")

        # Settings Tab
        self.settings_tab = SettingsTab()
        self.tab_widget.addTab(self.settings_tab, "⚙️ Settings")

        # Battle Map Overlay (hidden by default)
        self.battle_overlay = BattleMapOverlay(
            cheat_manager=self.trainer_tab.cheat_manager
        )
        self.battle_overlay.overlay_closed.connect(
            lambda: self.status_bar.showMessage("Battle overlay hidden")
        )
        
        # Connect tab change event
        self.tab_widget.currentChanged.connect(self._on_tab_changed)
    
    def _create_menu_bar(self) -> None:
        """Create menu bar."""
        menubar = self.menuBar()
        
        # File menu
        file_menu = menubar.addMenu("&File")
        
        exit_action = file_menu.addAction("E&xit")
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.close)
        
        # View menu
        view_menu = menubar.addMenu("&View")
        
        panel_action = view_menu.addAction("&Napoleon Control Panel")
        panel_action.setShortcut("Ctrl+Shift+P")
        panel_action.triggered.connect(self._launch_panel)
        
        # Tools menu
        tools_menu = menubar.addMenu("&Tools")
        
        overlay_action = tools_menu.addAction("&Battle Map Overlay")
        overlay_action.setShortcut("Ctrl+Shift+O")
        overlay_action.triggered.connect(self._toggle_battle_overlay)
        
        # Help menu
        help_menu = menubar.addMenu("&Help")
        
        about_action = help_menu.addAction("&About")
        about_action.triggered.connect(self._show_about)
        
        docs_action = help_menu.addAction("&Documentation")
        docs_action.triggered.connect(self._show_docs)
    
    def _on_tab_changed(self, index: int) -> None:
        """Handle tab change event."""
        tab_name = self.tab_widget.tabText(index)
        self.status_bar.showMessage(f"Active tab: {tab_name}")
    
    def _apply_stylesheet(self) -> None:
        """Apply application stylesheet."""
        stylesheet = """
        QMainWindow {
            background-color: #1e1e1e;
        }
        
        QTabWidget::pane {
            border: 1px solid #3c3c3c;
            background-color: #252525;
            border-radius: 5px;
        }
        
        QTabBar::tab {
            background-color: #2d2d2d;
            color: #cccccc;
            padding: 8px 16px;
            margin-right: 2px;
            border-top-left-radius: 5px;
            border-top-right-radius: 5px;
        }
        
        QTabBar::tab:selected {
            background-color: #3c3c3c;
            color: #ffffff;
        }
        
        QTabBar::tab:hover {
            background-color: #404040;
        }
        
        QPushButton {
            background-color: #0e639c;
            color: white;
            border: none;
            padding: 8px 16px;
            border-radius: 4px;
            font-weight: bold;
        }
        
        QPushButton:hover {
            background-color: #1177bb;
        }
        
        QPushButton:pressed {
            background-color: #0d5a8f;
        }
        
        QPushButton:disabled {
            background-color: #3c3c3c;
            color: #888888;
        }
        
        QLabel {
            color: #cccccc;
        }
        
        QStatusBar {
            background-color: #007acc;
            color: white;
        }
        
        QMenuBar {
            background-color: #3c3c3c;
            color: white;
        }
        
        QMenuBar::item:selected {
            background-color: #505050;
        }
        
        QMenu {
            background-color: #3c3c3c;
            color: white;
        }
        
        QMenu::item:selected {
            background-color: #505050;
        }
        """
        
        self.setStyleSheet(stylesheet)
    
    def _show_about(self) -> None:
        """Show about dialog."""
        QMessageBox.about(
            self,
            "About Napoleon Total War Cheat Engine",
            """<h2>Napoleon Total War Cheat Engine</h2>
            <p>Version 1.0.0</p>
            <p>A comprehensive cheat engine suite for Napoleon Total War.</p>
            <p>Features:</p>
            <ul>
                <li>Memory scanning and editing</li>
                <li>Save game editor (.esf files)</li>
                <li>Script file editor (Lua)</li>
                <li>Pack file modding</li>
                <li>Runtime trainer with hotkeys</li>
            </ul>
            <p>Supports Windows and Linux (native + Proton)</p>
            """
        )
    
    def _show_docs(self) -> None:
        """Show documentation info."""
        QMessageBox.information(
            self,
            "Documentation",
            """Documentation is available in the docs/ directory.
            
            Quick Start:
            1. Go to Memory Scanner tab to scan for values
            2. Use File Editor to modify saves and scripts
            3. Use Trainer tab for hotkey-activated cheats
            4. Configure settings in the Settings tab
            
            See README.md for detailed instructions.
            """
        )
    
    def _toggle_battle_overlay(self) -> None:
        """Toggle the battle map overlay on/off."""
        if self.battle_overlay.isVisible():
            self.battle_overlay.hide_overlay()
            self.status_bar.showMessage("Battle overlay hidden")
        else:
            self.battle_overlay.show_overlay()
            self.status_bar.showMessage("Battle overlay shown (Ctrl+Shift+O to toggle)")
    
    def _launch_panel(self) -> None:
        """Launch the Napoleon Control Panel in a new window."""
        try:
            from .napoleon_panel import NapoleonControlPanel
            self.panel_window = NapoleonControlPanel(config_manager=self.settings_tab.config_manager if hasattr(self.settings_tab, 'config_manager') else None)
            self.panel_window.show()
            self.status_bar.showMessage("Napoleon Control Panel opened (Ctrl+Shift+P)")
        except ImportError:
            self.status_bar.showMessage("PyQt6 required for Napoleon Control Panel")
            QMessageBox.warning(
                self,
                "PyQt6 Required",
                "The Napoleon Control Panel requires PyQt6. Please install it with: pip install PyQt6"
            )

    def closeEvent(self, event) -> None:
        """Handle window close event."""
        # Clean up resources
        self.memory_tab.cleanup()
        self.file_editor_tab.cleanup()
        self.trainer_tab.cleanup()
        self.preset_tab.cleanup()
        self.battle_overlay.cleanup()
        
        event.accept()


def main():
    """Main entry point for the GUI application."""
    if not PYQT_AVAILABLE:
        print("PyQt6 is required. Install with: pip install PyQt6")
        sys.exit(1)
    
    app = QApplication(sys.argv)
    app.setApplicationName("Napoleon Total War Cheat Engine")
    app.setOrganizationName("NTWCheat")

    config_manager = ConfigManager()
    config_manager.load()
    if not run_first_run_setup(app, config_manager):
        return
    
    # Set dark palette
    from PyQt6.QtGui import QPalette, QColor
    from PyQt6.QtWidgets import QStyleFactory
    
    app.setStyle(QStyleFactory.create("Fusion"))
    
    palette = QPalette()
    palette.setColor(QPalette.ColorRole.Window, QColor(30, 30, 30))
    palette.setColor(QPalette.ColorRole.WindowText, QColor(204, 204, 204))
    palette.setColor(QPalette.ColorRole.Base, QColor(37, 37, 37))
    palette.setColor(QPalette.ColorRole.AlternateBase, QColor(30, 30, 30))
    palette.setColor(QPalette.ColorRole.ToolTipBase, QColor(204, 204, 204))
    palette.setColor(QPalette.ColorRole.ToolTipText, QColor(204, 204, 204))
    palette.setColor(QPalette.ColorRole.Text, QColor(204, 204, 204))
    palette.setColor(QPalette.ColorRole.Button, QColor(45, 45, 45))
    palette.setColor(QPalette.ColorRole.ButtonText, QColor(204, 204, 204))
    palette.setColor(QPalette.ColorRole.BrightText, QColor(255, 255, 255))
    palette.setColor(QPalette.ColorRole.Link, QColor(42, 130, 218))
    palette.setColor(QPalette.ColorRole.Highlight, QColor(42, 130, 218))
    palette.setColor(QPalette.ColorRole.HighlightedText, QColor(255, 255, 255))
    app.setPalette(palette)
    
    window = MainWindow()
    window.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
