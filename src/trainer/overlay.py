"""
Overlay display for showing active cheats.
Provides visual feedback during gameplay.
"""

import threading
import time
from typing import Dict, List, Optional

try:
    from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QApplication
    from PyQt6.QtCore import Qt, QTimer
    from PyQt6.QtGui import QFont
    PYQT_AVAILABLE = True
except ImportError:
    PYQT_AVAILABLE = False


class CheatOverlay:
    """
    Overlay window showing active cheats.
    """
    
    def __init__(self):
        """Initialize cheat overlay."""
        self.window: Optional[QWidget] = None
        self.labels: Dict[str, QLabel] = {}
        self.timer: Optional[QTimer] = None
        self.visible: bool = False
        
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
            self.window.setGeometry(
                screen.width() - 300,
                100,
                280,
                400
            )
            
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
            
            self.window.setLayout(layout)
            
            print("Cheat overlay created")
            return True
            
        except Exception as e:
            print(f"Failed to create overlay: {e}")
            return False
    
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
        
        # Clear existing cheat labels (keep title)
        while layout.count() > 1:
            item = layout.takeAt(1)
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
        """Show the overlay."""
        if self.window:
            self.window.show()
            self.visible = True
    
    def hide(self) -> None:
        """Hide the overlay."""
        if self.window:
            self.window.hide()
            self.visible = False
    
    def toggle(self) -> None:
        """Toggle overlay visibility."""
        if self.visible:
            self.hide()
        else:
            self.show()
    
    def close(self) -> None:
        """Close the overlay."""
        if self.window:
            self.window.close()
            self.window = None
    
    def is_visible(self) -> bool:
        """Check if overlay is visible."""
        return self.visible


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
