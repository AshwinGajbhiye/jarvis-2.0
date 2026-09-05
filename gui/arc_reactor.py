"""
Arc Reactor Widget — Iron Man inspired animated avatar for Jarvis.
Custom-painted using QPainter with state-driven animations.
"""

import math
import random
from PyQt6.QtWidgets import QWidget
from PyQt6.QtCore import Qt, QTimer, QPointF, QRectF
from PyQt6.QtGui import (
    QPainter, QColor, QRadialGradient, QConicalGradient,
    QPen, QBrush, QFont
)


class Particle:
    """A small glowing dot that orbits the reactor."""
    def __init__(self, radius, angle, speed, size):
        self.radius = radius
        self.angle = angle
        self.speed = speed
        self.size = size
        self.alpha = random.randint(120, 255)

    def update(self, dt):
        self.angle += self.speed * dt
        if self.angle > 360:
            self.angle -= 360


class ArcReactorWidget(QWidget):
    """
    A custom-painted Iron Man Arc Reactor that animates based on Jarvis's state.
    
    States: 'idle', 'listening', 'thinking', 'speaking', 'error', 'booting'
    """

    WIDGET_SIZE = 180

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(self.WIDGET_SIZE, self.WIDGET_SIZE)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        # Animation state
        self._state = "idle"
        self._tick = 0.0           # Master clock in seconds
        self._ring_rotation = 0.0  # Degrees
        self._pulse = 0.0          # 0..1 sine pulse
        self._sonar_radius = 0.0   # For listening sonar effect
        self._ripples = []         # For speaking ripple effect

        # Colors per state
        self._colors = {
            "idle":      QColor(0, 255, 255),       # Cyan
            "listening": QColor(0, 255, 120),       # Green-cyan
            "thinking":  QColor(0, 200, 255),       # Bright cyan
            "speaking":  QColor(180, 240, 255),     # White-cyan
            "error":     QColor(255, 60, 60),       # Red
            "booting":   QColor(0, 255, 255),       # Cyan
        }

        # Particles
        self._particles = []
        self._init_particles()

        # Animation timer (~33ms = ~30fps)
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._animate)
        self._timer.start(33)

    def _init_particles(self):
        """Create a set of orbiting particles."""
        self._particles = []
        for _ in range(12):
            p = Particle(
                radius=random.uniform(50, 75),
                angle=random.uniform(0, 360),
                speed=random.uniform(20, 60),
                size=random.uniform(1.5, 3.5),
            )
            self._particles.append(p)

    def set_state(self, state: str):
        """Change the animation state."""
        if state not in self._colors:
            state = "idle"
        if state != self._state:
            self._state = state
            # Reset sonar on entering listening
            if state == "listening":
                self._sonar_radius = 0.0
            # Reset ripples on entering speaking
            if state == "speaking":
                self._ripples = []

    def _animate(self):
        """Called every frame to advance the animation."""
        dt = 0.033  # ~30fps

        self._tick += dt
        self._pulse = (math.sin(self._tick * 3.0) + 1.0) / 2.0  # 0..1

        # State-dependent speeds
        if self._state == "thinking":
            rotation_speed = 180.0  # Fast
            particle_mult = 3.0
        elif self._state == "speaking":
            rotation_speed = 40.0
            particle_mult = 1.5
        elif self._state == "listening":
            rotation_speed = 25.0
            particle_mult = 1.0
        elif self._state == "error":
            rotation_speed = 10.0
            particle_mult = 0.5
        else:  # idle / booting
            rotation_speed = 15.0
            particle_mult = 1.0

        self._ring_rotation += rotation_speed * dt
        if self._ring_rotation > 360:
            self._ring_rotation -= 360

        # Update particles
        for p in self._particles:
            p.update(dt * particle_mult)

        # Sonar effect for listening
        if self._state == "listening":
            self._sonar_radius += 80 * dt
            if self._sonar_radius > 90:
                self._sonar_radius = 0.0

        # Ripple effect for speaking
        if self._state == "speaking":
            if random.random() < 0.15:
                self._ripples.append(0.0)
            self._ripples = [r + 100 * dt for r in self._ripples]
            self._ripples = [r for r in self._ripples if r < 90]

        self.update()  # Trigger repaint

    def paintEvent(self, event):
        """Draw the Arc Reactor."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        cx = self.WIDGET_SIZE / 2.0
        cy = self.WIDGET_SIZE / 2.0
        color = self._colors.get(self._state, self._colors["idle"])

        # ── 1. Background Glow ────────────────────────────
        glow_intensity = 0.25 + 0.15 * self._pulse
        if self._state == "thinking":
            glow_intensity = 0.35 + 0.2 * self._pulse
        elif self._state == "error":
            glow_intensity = 0.2 + 0.3 * (self._pulse if random.random() > 0.1 else 0)

        glow = QRadialGradient(QPointF(cx, cy), 88)
        glow.setColorAt(0.0, QColor(color.red(), color.green(), color.blue(), int(255 * glow_intensity)))
        glow.setColorAt(0.5, QColor(color.red(), color.green(), color.blue(), int(80 * glow_intensity)))
        glow.setColorAt(1.0, QColor(0, 0, 0, 0))
        painter.setBrush(QBrush(glow))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(QPointF(cx, cy), 88, 88)

        # ── 2. Outer Ring (rotating arc segments) ─────────
        ring_alpha = int(180 + 75 * self._pulse)
        pen = QPen(QColor(color.red(), color.green(), color.blue(), ring_alpha))
        pen.setWidthF(2.0)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)

        outer_rect = QRectF(cx - 72, cy - 72, 144, 144)
        # Draw 4 arc segments with gaps, rotated
        for i in range(4):
            start = int((self._ring_rotation + i * 90) * 16)
            span = int(60 * 16)  # 60 degree arcs with 30 degree gaps
            painter.drawArc(outer_rect, start, span)

        # ── 3. Middle Ring (counter-rotating) ─────────────
        mid_pen = QPen(QColor(color.red(), color.green(), color.blue(), int(ring_alpha * 0.7)))
        mid_pen.setWidthF(1.5)
        painter.setPen(mid_pen)

        mid_rect = QRectF(cx - 56, cy - 56, 112, 112)
        for i in range(6):
            start = int((-self._ring_rotation * 1.5 + i * 60) * 16)
            span = int(35 * 16)
            painter.drawArc(mid_rect, start, span)

        # ── 4. Inner Ring (solid, subtle pulse) ───────────
        inner_alpha = int(120 + 100 * self._pulse)
        inner_pen = QPen(QColor(color.red(), color.green(), color.blue(), inner_alpha))
        inner_pen.setWidthF(1.2)
        painter.setPen(inner_pen)
        inner_rect = QRectF(cx - 38, cy - 38, 76, 76)
        painter.drawEllipse(inner_rect)

        # ── 5. Thin accent ring ───────────────────────────
        accent_pen = QPen(QColor(color.red(), color.green(), color.blue(), 60))
        accent_pen.setWidthF(0.8)
        painter.setPen(accent_pen)
        accent_rect = QRectF(cx - 46, cy - 46, 92, 92)
        painter.drawEllipse(accent_rect)

        # ── 6. Core (bright glowing center) ───────────────
        core_size = 14 + 4 * self._pulse
        if self._state == "speaking":
            core_size = 14 + 8 * self._pulse  # Bigger pulse when speaking

        core_glow = QRadialGradient(QPointF(cx, cy), core_size)
        core_glow.setColorAt(0.0, QColor(255, 255, 255, 240))
        core_glow.setColorAt(0.3, QColor(color.red(), color.green(), color.blue(), 220))
        core_glow.setColorAt(1.0, QColor(color.red(), color.green(), color.blue(), 0))
        painter.setBrush(QBrush(core_glow))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(QPointF(cx, cy), core_size, core_size)

        # Bright white center dot
        white_dot = QRadialGradient(QPointF(cx, cy), 6)
        white_dot.setColorAt(0.0, QColor(255, 255, 255, 255))
        white_dot.setColorAt(1.0, QColor(255, 255, 255, 0))
        painter.setBrush(QBrush(white_dot))
        painter.drawEllipse(QPointF(cx, cy), 6, 6)

        # ── 7. Particles ─────────────────────────────────
        for p in self._particles:
            angle_rad = math.radians(p.angle)
            px = cx + p.radius * math.cos(angle_rad)
            py = cy + p.radius * math.sin(angle_rad)

            p_alpha = p.alpha
            if self._state == "error":
                p_alpha = int(p_alpha * 0.4)
            elif self._state == "thinking":
                p_alpha = min(255, int(p_alpha * 1.3))

            p_color = QColor(color.red(), color.green(), color.blue(), p_alpha)

            p_glow = QRadialGradient(QPointF(px, py), p.size * 2)
            p_glow.setColorAt(0.0, p_color)
            p_glow.setColorAt(1.0, QColor(color.red(), color.green(), color.blue(), 0))
            painter.setBrush(QBrush(p_glow))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(QPointF(px, py), p.size * 2, p.size * 2)

        # ── 8. Sonar Rings (listening state) ──────────────
        if self._state == "listening" and self._sonar_radius > 0:
            sonar_alpha = int(180 * (1.0 - self._sonar_radius / 90.0))
            sonar_pen = QPen(QColor(color.red(), color.green(), color.blue(), sonar_alpha))
            sonar_pen.setWidthF(1.5)
            painter.setPen(sonar_pen)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawEllipse(QPointF(cx, cy), self._sonar_radius, self._sonar_radius)

        # ── 9. Speaking Ripples ───────────────────────────
        if self._state == "speaking":
            for r in self._ripples:
                ripple_alpha = int(140 * (1.0 - r / 90.0))
                if ripple_alpha > 0:
                    ripple_pen = QPen(QColor(color.red(), color.green(), color.blue(), ripple_alpha))
                    ripple_pen.setWidthF(1.0)
                    painter.setPen(ripple_pen)
                    painter.setBrush(Qt.BrushStyle.NoBrush)
                    painter.drawEllipse(QPointF(cx, cy), 20 + r, 20 + r)

        # ── 10. Cross-hairs (subtle HUD feel) ────────────
        ch_pen = QPen(QColor(color.red(), color.green(), color.blue(), 35))
        ch_pen.setWidthF(0.5)
        painter.setPen(ch_pen)
        # Horizontal
        painter.drawLine(QPointF(cx - 85, cy), QPointF(cx - 30, cy))
        painter.drawLine(QPointF(cx + 30, cy), QPointF(cx + 85, cy))
        # Vertical
        painter.drawLine(QPointF(cx, cy - 85), QPointF(cx, cy - 30))
        painter.drawLine(QPointF(cx, cy + 30), QPointF(cx, cy + 85))

        # ── 11. Small tick marks around outer edge ────────
        tick_pen = QPen(QColor(color.red(), color.green(), color.blue(), 50))
        tick_pen.setWidthF(0.8)
        painter.setPen(tick_pen)
        for i in range(36):
            angle_rad = math.radians(i * 10 + self._ring_rotation * 0.3)
            inner_r = 78
            outer_r = 83
            x1 = cx + inner_r * math.cos(angle_rad)
            y1 = cy + inner_r * math.sin(angle_rad)
            x2 = cx + outer_r * math.cos(angle_rad)
            y2 = cy + outer_r * math.sin(angle_rad)
            painter.drawLine(QPointF(x1, y1), QPointF(x2, y2))

        painter.end()
