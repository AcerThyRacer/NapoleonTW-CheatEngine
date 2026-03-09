"""
Advanced Animated Components for Napoleon Control Panel
Includes particle effects, victory animations, parallax battle scene,
motion-blur particle system, cannon smoke, FPS counter, and sound system.
"""

import sys
import time
import random
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
        QParallelAnimationGroup, QSequentialAnimationGroup, pyqtSignal,
        QRectF
    )
    from PyQt6.QtGui import (
        QFont, QColor, QPen, QBrush, QPainter, QPainterPath,
        QGradient, QLinearGradient, QRadialGradient, QPixmap
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
    """Sound effect player for Napoleon-themed sounds.

    Discovers wav files from the ``assets/sounds/`` directory relative to
    the repository root.  Falls back to a silent no-op when files are
    missing or PyQt6 multimedia is unavailable.
    """

    _SOUND_MAP = {
        'activate': 'cheat_activate.wav',
        'deactivate': 'cheat_deactivate.wav',
        'victory': 'victory_fanfare.wav',
        'click': 'cheat_activate.wav',
    }

    def __init__(self, enabled: bool = True):
        self.enabled = enabled
        self._sounds_dir = Path(__file__).resolve().parents[2] / "assets" / "sounds"
        self._cache: dict = {}
        self._mixer_available = False

        try:
            from PyQt6.QtMultimedia import QSoundEffect  # noqa: F401
            self._mixer_available = True
        except ImportError:
            pass

    def play(self, sound_name: str) -> None:
        """Play a sound effect by logical name."""
        if not self.enabled:
            return
        filename = self._SOUND_MAP.get(sound_name)
        if filename is None:
            return
        path = self._sounds_dir / filename
        if not path.exists():
            return
        if self._mixer_available:
            self._play_qt(path)

    def _play_qt(self, path: Path) -> None:
        """Play a sound via QSoundEffect (non-blocking)."""
        try:
            from PyQt6.QtMultimedia import QSoundEffect
            from PyQt6.QtCore import QUrl

            key = str(path)
            if key not in self._cache:
                effect = QSoundEffect()
                effect.setSource(QUrl.fromLocalFile(key))
                effect.setVolume(0.5)
                self._cache[key] = effect
            self._cache[key].play()
        except Exception:
            pass


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


class CannonSmokeParticle:
    """A single cannon smoke particle with drift and fade."""

    def __init__(self, x: float, y: float):
        self.x = x
        self.y = y
        self.vx = random.uniform(-0.8, 0.8)
        self.vy = random.uniform(-2.0, -0.5)
        self.radius = random.uniform(4.0, 10.0)
        self.alpha = random.randint(120, 200)
        self.decay = random.uniform(1.5, 3.5)
        self.alive = True


class CannonSmokeSystem(QWidget):
    """Continuous cannon-smoke particle emitter.

    Creates wisps of grey-white smoke that drift upward and fade,
    simulating a Napoleonic battlefield.
    """

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.particles: List[CannonSmokeParticle] = []
        self._emitting = False
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(33)  # ~30 FPS

    def start_emitting(self) -> None:
        self._emitting = True

    def stop_emitting(self) -> None:
        self._emitting = False

    def _tick(self) -> None:
        if self._emitting:
            for _ in range(random.randint(1, 3)):
                x = random.uniform(0, max(self.width(), 1))
                y = float(self.height())
                self.particles.append(CannonSmokeParticle(x, y))

        alive: List[CannonSmokeParticle] = []
        for p in self.particles:
            p.x += p.vx
            p.y += p.vy
            p.alpha -= p.decay
            p.radius += 0.15
            if p.alpha > 0:
                alive.append(p)
        self.particles = alive
        self.update()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        for p in self.particles:
            a = max(0, int(p.alpha))
            grad = QRadialGradient(QPointF(p.x, p.y), p.radius)
            grad.setColorAt(0, QColor(200, 200, 200, a))
            grad.setColorAt(1, QColor(120, 120, 120, 0))
            painter.setBrush(QBrush(grad))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(QPointF(p.x, p.y), p.radius, p.radius)


class MotionBlurParticle:
    """Particle that renders a short motion-blur trail."""

    def __init__(self, x: float, y: float, vx: float, vy: float,
                 color: QColor, size: float):
        self.x = x
        self.y = y
        self.vx = vx
        self.vy = vy
        self.prev_x = x
        self.prev_y = y
        self.color = color
        self.size = size
        self.alpha = 255
        self.age = 0.0

    def step(self) -> None:
        self.prev_x = self.x
        self.prev_y = self.y
        self.x += self.vx
        self.y += self.vy
        self.vy += 0.12
        self.age += 0.02
        self.alpha = max(0, int(255 * (1.0 - self.age)))


class MotionBlurParticleSystem(QWidget):
    """Particle system where each particle draws a short directional trail
    to simulate motion blur — a 2026-level visual effect.
    """

    TRAIL_STEPS = 4

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.particles: List[MotionBlurParticle] = []
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(16)  # ~60 FPS

    def emit_burst(self, x: float, y: float, count: int = 40,
                   color: QColor = QColor(212, 175, 55),
                   speed_range: tuple = (2.0, 6.0)) -> None:
        """Emit a radial burst of motion-blur particles."""
        for i in range(count):
            angle = (360.0 / count) * i + random.uniform(-5, 5)
            speed = random.uniform(*speed_range)
            vx = math.cos(math.radians(angle)) * speed
            vy = math.sin(math.radians(angle)) * speed
            sz = random.uniform(2.0, 5.0)
            self.particles.append(MotionBlurParticle(x, y, vx, vy, color, sz))
        if not self._timer.isActive():
            self._timer.start(16)

    def _tick(self) -> None:
        for p in self.particles:
            p.step()
        self.particles = [p for p in self.particles if p.age < 1.0]
        if not self.particles:
            self._timer.stop()
        self.update()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        for p in self.particles:
            # Draw trail segments (fading older copies)
            dx = p.x - p.prev_x
            dy = p.y - p.prev_y
            for t in range(self.TRAIL_STEPS, -1, -1):
                frac = t / self.TRAIL_STEPS
                tx = p.x - dx * frac
                ty = p.y - dy * frac
                a = int(p.alpha * (1.0 - frac * 0.7))
                c = QColor(p.color)
                c.setAlpha(max(0, a))
                painter.setBrush(QBrush(c))
                painter.setPen(Qt.PenStyle.NoPen)
                r = p.size * (1.0 - frac * 0.4)
                painter.drawEllipse(QPointF(tx, ty), r, r)


class ParallaxLayer:
    """A single scrolling layer in a parallax battle scene."""

    def __init__(self, speed: float, elements: list):
        self.speed = speed
        self.offset = 0.0
        self.elements = elements  # list of (rel_x, y, size, color)


class ParallaxBattleScene(QWidget):
    """Animated parallax scrolling battlefield background.

    Three depth layers scroll at different speeds to create a
    convincing depth-of-field illusion behind the control panel.
    """

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        # Build layers: far (sky/hills), mid (trees/camps), near (soldiers/cannons)
        self._layers = [
            ParallaxLayer(0.3, self._generate_hills(12)),
            ParallaxLayer(0.7, self._generate_camps(8)),
            ParallaxLayer(1.2, self._generate_units(15)),
        ]

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._scroll)
        self._timer.start(33)

    @staticmethod
    def _generate_hills(n: int) -> list:
        return [
            (random.uniform(0, 1), random.uniform(0.55, 0.7),
             random.uniform(60, 120), QColor(35, 50, 40, 60))
            for _ in range(n)
        ]

    @staticmethod
    def _generate_camps(n: int) -> list:
        return [
            (random.uniform(0, 1), random.uniform(0.5, 0.65),
             random.uniform(8, 16), QColor(180, 140, 60, 80))
            for _ in range(n)
        ]

    @staticmethod
    def _generate_units(n: int) -> list:
        colors = [QColor(46, 204, 113, 100), QColor(231, 76, 60, 100)]
        return [
            (random.uniform(0, 1), random.uniform(0.6, 0.85),
             random.uniform(4, 8), random.choice(colors))
            for _ in range(n)
        ]

    def _scroll(self) -> None:
        w = max(self.width(), 1)
        for layer in self._layers:
            layer.offset = (layer.offset + layer.speed) % w
        self.update()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w = self.width()
        h = self.height()

        # Sky gradient
        sky = QLinearGradient(0, 0, 0, h)
        sky.setColorAt(0, QColor(15, 20, 30, 180))
        sky.setColorAt(0.4, QColor(30, 42, 55, 160))
        sky.setColorAt(1, QColor(20, 28, 38, 140))
        painter.fillRect(self.rect(), QBrush(sky))

        # Draw each parallax layer
        for layer in self._layers:
            for (rel_x, rel_y, size, color) in layer.elements:
                x = (rel_x * w + layer.offset) % w
                y = rel_y * h
                painter.setBrush(QBrush(color))
                painter.setPen(Qt.PenStyle.NoPen)
                if size > 30:
                    # Hill blobs
                    painter.drawEllipse(QPointF(x, y), size, size * 0.4)
                else:
                    painter.drawEllipse(QPointF(x, y), size, size)


class FPSCounter(QLabel):
    """Lightweight FPS counter overlay widget.

    Updates once per second and displays the average frame rate
    measured between consecutive paint ticks of a target widget.
    """

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setStyleSheet(
            "QLabel { color: #d4af37; background: rgba(0,0,0,160); "
            "border-radius: 4px; padding: 2px 6px; font-size: 11px; }"
        )
        self.setText("-- FPS")
        self.setFixedSize(72, 22)
        self._frame_count = 0
        self._last_time = time.monotonic()
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._refresh)
        self._timer.start(1000)

    def tick(self) -> None:
        """Call once per rendered frame."""
        self._frame_count += 1

    def _refresh(self) -> None:
        now = time.monotonic()
        elapsed = now - self._last_time
        if elapsed > 0:
            fps = self._frame_count / elapsed
            self.setText(f"{fps:.0f} FPS")
        self._frame_count = 0
        self._last_time = now


class LiveStatsDashboard(QFrame):
    """Real-time statistics dashboard showing gold, army count, turn, and FPS.

    The dashboard is a compact horizontal bar designed to sit beneath the
    header in the Napoleon control panel.
    """

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setFixedHeight(48)
        self.setStyleSheet("""
            QFrame {
                background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
                    stop:0 rgba(26,37,47,220), stop:1 rgba(44,62,80,220));
                border-bottom: 1px solid #d4af37;
            }
        """)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 4, 16, 4)
        layout.setSpacing(24)

        self.gold_label = self._make_stat("💰", "0")
        self.army_label = self._make_stat("⚔️", "0")
        self.turn_label = self._make_stat("🏁", "1")
        self.fps_counter = FPSCounter()

        layout.addWidget(self.gold_label)
        layout.addWidget(self.army_label)
        layout.addWidget(self.turn_label)
        layout.addStretch()
        layout.addWidget(self.fps_counter)

    @staticmethod
    def _make_stat(icon: str, initial: str) -> QLabel:
        lbl = QLabel(f"{icon} {initial}")
        lbl.setFont(QFont("Georgia", 12, QFont.Weight.Bold))
        lbl.setStyleSheet("QLabel { color: #d4af37; background: transparent; }")
        return lbl

    def set_gold(self, value: int) -> None:
        self.gold_label.setText(f"💰 {value:,}")

    def set_army_count(self, value: int) -> None:
        self.army_label.setText(f"⚔️ {value}")

    def set_turn(self, value: int) -> None:
        self.turn_label.setText(f"🏁 Turn {value}")


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
