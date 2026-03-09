"""
Advanced Animated Components for Napoleon Control Panel
Includes particle effects, victory animations, and sound system.
"""

import sys
from pathlib import Path
from typing import List, Optional
import math

try:
    from PyQt6.QtWidgets import (
        QWidget, QLabel, QVBoxLayout, QHBoxLayout, QGraphicsView,
        QGraphicsScene, QGraphicsEllipseItem, QGraphicsTextItem,
        QApplication, QMainWindow, QPushButton, QFrame, QSizePolicy
    )
    from PyQt6.QtCore import (
        Qt, QTimer, QPointF, QPropertyAnimation, QEasingCurve,
        QParallelAnimationGroup, QSequentialAnimationGroup, pyqtSignal
    )
    from PyQt6.QtGui import (
        QFont, QColor, QPen, QBrush, QPainter, QPainterPath,
        QGradient, QLinearGradient, QRadialGradient
    )
    PYQT_AVAILABLE = True
except ImportError:
    PYQT_AVAILABLE = False


class Particle:
    """Represents a particle in an animation effect."""
    
    def __init__(self, x: float, y: float, vx: float, vy: float, color: QColor, size: float):
        self.x = x
        self.y = y
        self.vx = vx
        self.vy = vy
        self.color = color
        self.size = size
        self.alpha = 255
        self.lifetime = 1.0
        self.age = 0.0


class ParticleSystem(QWidget):
    """Particle system for visual effects."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(400, 300)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.particles: List[Particle] = []
        
        self.timer = QTimer()
        self.timer.timeout.connect(self._update)
        self.timer.start(16)  # ~60 FPS
    
    def emit_particles(self, x: float, y: float, count: int = 50, 
                       color: QColor = QColor(212, 175, 55),
                       spread: float = 360.0):
        """Emit particles from a point."""
        for _ in range(count):
            angle = (spread / count) * _ if spread > 0 else 0
            speed = 2.0 + (_ % 3)
            vx = math.cos(math.radians(angle)) * speed
            vy = math.sin(math.radians(angle)) * speed
            
            particle = Particle(x, y, vx, vy, color, 3.0 + (_ % 4))
            self.particles.append(particle)
        
        if not self.timer.isActive():
            self.timer.start(16)
    
    def _update(self):
        """Update particle positions."""
        for particle in self.particles:
            particle.x += particle.vx
            particle.y += particle.vy
            particle.vy += 0.1  # Gravity
            particle.age += 0.02
            particle.alpha = int(255 * (1.0 - particle.age))
        
        # Remove dead particles
        self.particles = [p for p in self.particles if p.age < 1.0]
        
        if not self.particles:
            self.timer.stop()
        
        self.update()
    
    def paintEvent(self, event):
        """Render particles."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        for particle in self.particles:
            color = QColor(particle.color)
            color.setAlpha(particle.alpha)
            painter.setBrush(QBrush(color))
            painter.setPen(QPen(color, 0))
            painter.drawEllipse(QPointF(particle.x, particle.y), particle.size, particle.size)


class VictoryAnimation(QWidget):
    """Victory celebration animation."""
    
    animation_complete = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(400, 300)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.phase = 0
        self.timer = QTimer()
        self.timer.timeout.connect(self._animate)
        
        self.texts = ["VICTORY!", "VIVE L'EMPEREUR!", "TRIOMPHE!", "GLOIRE!"]
        self.current_text_index = 0
        self.scale = 0.0
        self.rotation = 0.0
        
    def play(self):
        """Play victory animation."""
        self.phase = 0
        self.current_text_index = 0
        self.scale = 0.0
        self.timer.start(50)
    
    def _animate(self):
        """Animate victory sequence."""
        if self.phase == 0:
            self.scale += 0.1
            if self.scale >= 1.0:
                self.scale = 1.0
                self.phase = 1
                self.timer.setInterval(1000)
        elif self.phase == 1:
            self.current_text_index = (self.current_text_index + 1) % len(self.texts)
            self.phase = 2
            self.timer.setInterval(50)
        elif self.phase == 2:
            self.rotation += 5
            if self.rotation >= 360:
                self.rotation = 0
            self.scale -= 0.05
            if self.scale <= 0.0:
                self.timer.stop()
                self.animation_complete.emit()
        
        self.update()
    
    def paintEvent(self, event):
        """Render victory animation."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        painter.translate(self.width() / 2, self.height() / 2)
        painter.rotate(self.rotation)
        painter.scale(self.scale, self.scale)
        
        # Draw laurel wreath
        painter.setPen(QPen(QColor(212, 175, 55), 3))
        painter.setBrush(QBrush(QColor(212, 175, 55, 100)))
        painter.drawEllipse(-100, -100, 200, 200)
        
        # Draw text
        painter.resetTransform()
        painter.setPen(QPen(QColor(241, 196, 15), 2))
        font = QFont("Georgia", 36, QFont.Weight.Bold)
        painter.setFont(font)
        text = self.texts[self.current_text_index]
        painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, text)


class AnimatedProgressBar(QFrame):
    """Animated progress bar with Napoleon theme."""
    
    def __init__(self, label: str = "", parent=None):
        super().__init__(parent)
        self.setFixedHeight(40)
        self.value = 0
        self.maximum = 100
        self.label = label
        self.animation = QPropertyAnimation(self, b"value")
        self.animation.setDuration(1000)
        self.animation.setEasingCurve(QEasingCurve.Type.OutQuad)
        
        self.setStyleSheet("""
            QFrame {
                background: #1a252f;
                border: 2px solid #d4af37;
                border-radius: 8px;
            }
        """)
    
    def setValue(self, value: int, animate: bool = True):
        """Set progress value."""
        if animate:
            self.animation.setEndValue(value)
            self.animation.start()
        else:
            self.value = value
            self.update()
    
    def paintEvent(self, event):
        """Render progress bar."""
        super().paintEvent(event)
        
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Draw progress
        progress_width = int((self.value / self.maximum) * (self.width() - 16))
        
        gradient = QLinearGradient(0, 0, progress_width, 0)
        gradient.setColorAt(0, QColor(212, 175, 55))
        gradient.setColorAt(1, QColor(241, 196, 15))
        
        painter.setBrush(QBrush(gradient))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(8, 8, progress_width, self.height() - 16, 4, 4)
        
        # Draw label
        painter.setPen(QPen(QColor(212, 175, 55)))
        font = QFont("Georgia", 12, QFont.Weight.Bold)
        painter.setFont(font)
        painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, self.label)


class ImperialNotification(QWidget):
    """Imperial-style notification popup."""
    
    def __init__(self, title: str, message: str, parent=None):
        super().__init__(parent)
        self.setFixedSize(400, 150)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        self.opacity = 0.0
        self.title = title
        self.message = message
        
        # Animation
        self.fade_animation = QPropertyAnimation(self, b"opacity")
        self.fade_animation.setDuration(300)
        
        # Auto-close timer
        self.timer = QTimer()
        self.timer.timeout.connect(self._fade_out)
    
    def show_notification(self):
        """Show notification with animation."""
        self.opacity = 0.0
        self.fade_animation.setEndValue(1.0)
        self.fade_animation.start()
        self.show()
        
        self.timer.singleShot(3000, self._fade_out)
    
    def _fade_out(self):
        """Fade out and close."""
        self.fade_animation.setEndValue(0.0)
        self.fade_animation.start()
        self.fade_animation.finished.connect(self.close)
    
    def paintEvent(self, event):
        """Render notification."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setOpacity(self.opacity)
        
        # Background
        gradient = QLinearGradient(0, 0, 0, self.height())
        gradient.setColorAt(0, QColor(44, 62, 80, 230))
        gradient.setColorAt(1, QColor(26, 37, 47, 230))
        
        painter.setBrush(QBrush(gradient))
        painter.setPen(QPen(QColor(212, 175, 55), 2))
        painter.drawRoundedRect(self.rect(), 10, 10)
        
        # Title
        painter.setPen(QPen(QColor(241, 196, 15)))
        font = QFont("Georgia", 16, QFont.Weight.Bold)
        painter.setFont(font)
        painter.drawText(20, 40, self.title)
        
        # Message
        painter.setPen(QPen(QColor(212, 175, 55)))
        font = QFont("Georgia", 12)
        painter.setFont(font)
        painter.drawText(20, 70, self.width() - 40, 60, Qt.TextFlag.TextWordWrap, self.message)


class SoundEffectPlayer:
    """Sound effect player for Napoleon-themed sounds."""
    
    def __init__(self, enabled: bool = True):
        self.enabled = enabled
        self.sounds = {
            'activate': 'sounds/activate.wav',
            'deactivate': 'sounds/deactivate.wav',
            'victory': 'sounds/victory.wav',
            'click': 'sounds/click.wav',
        }
        
        # For now, just print (would integrate with pygame.mixer or similar)
        print("🔊 Sound system initialized")
    
    def play(self, sound_name: str):
        """Play a sound effect."""
        if self.enabled and sound_name in self.sounds:
            # In production: pygame.mixer.Sound(self.sounds[sound_name]).play()
            print(f"🔊 Playing: {sound_name}")


class NapoleonBattleMap(QWidget):
    """Animated battle map visualization."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(600, 400)
        self.armies = []
        self.timer = QTimer()
        self.timer.timeout.connect(self._update_armies)
        
        self.setStyleSheet("""
            QWidget {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #1a252f, stop:1 #2c3e50);
                border: 3px solid #d4af37;
                border-radius: 10px;
            }
        """)
    
    def add_army(self, x: int, y: int, is_player: bool = True):
        """Add an army to the map."""
        self.armies.append({
            'x': x,
            'y': y,
            'is_player': is_player,
            'target_x': x,
            'target_y': y,
        })
        self.update()
    
    def move_army(self, index: int, target_x: int, target_y: int):
        """Move an army to new position."""
        if 0 <= index < len(self.armies):
            self.armies[index]['target_x'] = target_x
            self.armies[index]['target_y'] = target_y
            self.timer.start(50)
    
    def _update_armies(self):
        """Update army positions."""
        moving = False
        for army in self.armies:
            dx = army['target_x'] - army['x']
            dy = army['target_y'] - army['y']
            
            if abs(dx) > 5 or abs(dy) > 5:
                army['x'] += dx * 0.1
                army['y'] += dy * 0.1
                moving = True
        
        if not moving:
            self.timer.stop()
        
        self.update()
    
    def paintEvent(self, event):
        """Render battle map."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Draw grid
        painter.setPen(QPen(QColor(212, 175, 55, 50), 1))
        for i in range(0, self.width(), 50):
            painter.drawLine(i, 0, i, self.height())
        for i in range(0, self.height(), 50):
            painter.drawLine(0, i, self.width(), i)
        
        # Draw armies
        for army in self.armies:
            color = QColor(46, 204, 113) if army['is_player'] else QColor(231, 76, 60)
            painter.setBrush(QBrush(color))
            painter.setPen(QPen(color.darker(120), 2))
            
            # Draw army icon (circle with cross)
            x, y = int(army['x']), int(army['y'])
            painter.drawEllipse(x - 15, y - 15, 30, 30)
            painter.drawLine(x - 10, y, x + 10, y)
            painter.drawLine(x, y - 10, x, y + 10)


def demo_animations():
    """Demo all animations."""
    if not PYQT_AVAILABLE:
        print("PyQt6 required")
        return
    
    app = QApplication(sys.argv)
    
    window = QMainWindow()
    window.setWindowTitle("Napoleon Animation Demo")
    window.setGeometry(100, 100, 1000, 800)
    
    central = QWidget()
    layout = QVBoxLayout()
    central.setLayout(layout)
    
    # Particle system
    particles = ParticleSystem()
    layout.addWidget(particles)
    
    # Victory animation
    victory = VictoryAnimation()
    layout.addWidget(victory)
    
    # Progress bars
    progress1 = AnimatedProgressBar("Imperial Treasury")
    progress1.setValue(75)
    layout.addWidget(progress1)
    
    progress2 = AnimatedProgressBar("Army Morale")
    progress2.setValue(90)
    layout.addWidget(progress2)
    
    # Buttons to trigger effects
    btn_layout = QHBoxLayout()
    
    particle_btn = QPushButton("🎆 Particle Explosion")
    particle_btn.clicked.connect(lambda: particles.emit_particles(400, 50, 100))
    btn_layout.addWidget(particle_btn)
    
    victory_btn = QPushButton("🏆 Victory!")
    victory_btn.clicked.connect(lambda: victory.play())
    btn_layout.addWidget(victory_btn)
    
    layout.addLayout(btn_layout)
    
    window.setCentralWidget(central)
    window.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    demo_animations()
