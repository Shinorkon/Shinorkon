"""The radial fan. As a top-level window it is the overlay summoned during a drag;
as a child widget it is the practice wheel in onboarding."""
from __future__ import annotations

import math
import struct
import tempfile
import wave
from pathlib import Path

from PySide6.QtCore import QEasingCurve, QPointF, QRectF, Qt, QTimer, QUrl, QVariantAnimation, Signal
from PySide6.QtGui import (QBrush, QColor, QFont, QPainter, QPainterPath, QPen, QRadialGradient,
                           QLinearGradient)
try:
    from PySide6.QtMultimedia import QSoundEffect
except ImportError:  # sound is optional (needs PySide6-Addons)
    QSoundEffect = None
from PySide6.QtWidgets import QWidget

from . import core, geometry as geo, registry

ACCENT = QColor("#FF5200")
PAD = 34


def _tick_wav() -> str:
    """A 60 ms soft tick, generated locally (48 kHz stereo, 16-bit)."""
    path = Path(tempfile.gettempdir()) / "mandarin-highlight.wav"
    if not path.exists():
        n = int(48000 * 0.06)
        with wave.open(str(path), "wb") as w:
            w.setnchannels(2); w.setsampwidth(2); w.setframerate(48000)
            frames = bytearray()
            for i in range(n):
                v = int(9000 * math.sin(2 * math.pi * 1320 * i / 48000) * math.exp(-i / (n / 5)))
                frames += struct.pack("<hh", v, v)
            w.writeframes(bytes(frames))
    return str(path)


def human_size(n: int) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024 or unit == "GB":
            return f"{n:.0f} {unit}" if unit == "B" else f"{n:.1f} {unit}"
        n /= 1024


class WheelView(QWidget):
    chosen = Signal(str, str, list)   # mode, petal id, files
    hovered = Signal(int)

    def __init__(self, parent=None, overlay=False, sound=True, solid=False):
        super().__init__(parent)
        self.mode, self.files, self.petals, self.hot = "convert", [], [], None
        self.solid, self.sound_on, self.overlay = solid, sound, overlay
        self.scale = 1.0
        side = int((geo.OUTER + PAD) * 2)
        self.setFixedSize(side, side)
        self.setAcceptDrops(True)
        self.setMouseTracking(True)
        if overlay:
            self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool
                                | Qt.WindowDoesNotAcceptFocus | Qt.NoDropShadowWindowHint)
            self.setAttribute(Qt.WA_TranslucentBackground)
            self.setAttribute(Qt.WA_ShowWithoutActivating)
        self._snd = None
        if QSoundEffect:
            self._snd = QSoundEffect(self); self._snd.setSource(QUrl.fromLocalFile(_tick_wav()))
        self._anim = QVariantAnimation(self, duration=170)
        self._anim.setEasingCurve(QEasingCurve.OutBack)
        self._anim.valueChanged.connect(lambda v: (setattr(self, "scale", v), self.update()))
        self._hide_timer = QTimer(self, singleShot=True, interval=350)
        self._hide_timer.timeout.connect(self.dismiss)
        self._dropped = False

    # ---- state ----
    def set_files(self, files: list[Path]):
        self.files = [Path(f) for f in files]
        self.refresh()

    def set_mode(self, mode: str):
        self.mode = mode
        self.refresh()

    def refresh(self):
        self.petals = registry.petals(self.mode, self.files)
        self.hot = None
        self.update()

    def label_lines(self) -> tuple[str, str]:
        if not self.files:
            return {"convert": "Convert", "tools": "Tools", "actions": "Actions"}[self.mode], "drop here"
        k = registry.common_kind(self.files)
        size = human_size(sum(f.stat().st_size for f in self.files if f.exists()))
        head = self.files[0].suffix.lstrip(".").upper() if len(self.files) == 1 else f"{len(self.files)} files"
        if not self.petals:
            return head or "Folder", "nothing available" if k is None else "no options"
        return head or "Folder", size

    # ---- show/hide ----
    def summon(self, mode: str, center):
        self.mode = mode; self._dropped = False
        self.set_files(self.files if self.files else [])
        self.move(int(center.x() - self.width() / 2), int(center.y() - self.height() / 2))
        self.show(); self.raise_()
        self._anim.stop(); self._anim.setStartValue(0.82); self._anim.setEndValue(1.0); self._anim.start()

    def drag_released(self):
        if not self._dropped:
            self._hide_timer.start()

    def dismiss(self):
        self._hide_timer.stop(); self.files = []; self.petals = []; self.hot = None
        self.hide()

    # ---- painting ----
    def _petal_path(self, i: int, n: int) -> QPainterPath:
        span = geo.petal_span(n); start = 90 - i * span - geo.GAP_DEG / 2
        c = self.width() / 2
        outer = QRectF(c - geo.OUTER, c - geo.OUTER, 2 * geo.OUTER, 2 * geo.OUTER)
        inner = QRectF(c - geo.HUB, c - geo.HUB, 2 * geo.HUB, 2 * geo.HUB)
        ext = -(span - geo.GAP_DEG)
        p = QPainterPath(); p.arcMoveTo(outer, start); p.arcTo(outer, start, ext)
        p.arcTo(inner, start + ext, -ext); p.closeSubpath()
        return p

    def paintEvent(self, _):
        p = QPainter(self); p.setRenderHint(QPainter.Antialiasing)
        c = QPointF(self.width() / 2, self.height() / 2)
        p.translate(c); p.scale(self.scale, self.scale); p.translate(-c)
        n = len(self.petals)
        base_alpha = 255 if self.solid else 205
        # backdrop disc
        p.setPen(Qt.NoPen); p.setBrush(QColor(18, 16, 14, 120 if not self.solid else 255))
        p.drawEllipse(c, geo.OUTER + 10, geo.OUTER + 10)
        for i, (pid, label) in enumerate(self.petals):
            path = self._petal_path(i, n); hot = i == self.hot
            g = QLinearGradient(c.x(), c.y() - geo.OUTER, c.x(), c.y() + geo.OUTER)
            if hot:
                g.setColorAt(0, QColor(255, 120, 50, 255)); g.setColorAt(1, ACCENT)
            else:
                g.setColorAt(0, QColor(70, 62, 56, base_alpha)); g.setColorAt(1, QColor(42, 37, 33, base_alpha))
            p.setBrush(QBrush(g)); p.setPen(QPen(QColor(255, 255, 255, 60 if not hot else 120), 1))
            p.drawPath(path)
            x, y = geo.petal_center(i, n, (geo.OUTER + geo.HUB) / 2 + 6)
            f = QFont(self.font()); f.setBold(True); f.setPixelSize(13 if len(label) < 9 else 11); p.setFont(f)
            p.setPen(QColor("#fff7ef"))
            p.drawText(QRectF(c.x() + x - 40, c.y() + y - 14, 80, 28), Qt.AlignCenter | Qt.TextWordWrap, label)
        # hub
        hub = QRadialGradient(c, geo.HUB); hub.setColorAt(0, QColor(40, 35, 31, 250)); hub.setColorAt(1, QColor(26, 23, 20, 250))
        p.setBrush(hub); p.setPen(QPen(ACCENT, 2)); p.drawEllipse(c, geo.HUB - 2, geo.HUB - 2)
        head, sub = self.label_lines()
        f = QFont(self.font()); f.setBold(True); f.setPixelSize(15 if len(head) < 7 else 11); p.setFont(f)
        p.setPen(QColor("#fff7ef")); p.drawText(QRectF(c.x() - 40, c.y() - 22, 80, 24), Qt.AlignCenter, head)
        f.setBold(False); f.setPixelSize(10); p.setFont(f); p.setPen(QColor("#ffb48a"))
        p.drawText(QRectF(c.x() - 40, c.y() + 2, 80, 18), Qt.AlignCenter, sub)

    # ---- hit testing ----
    def _hit(self, pos) -> int | None:
        c = self.width() / 2
        return geo.petal_at((pos.x() - c) / self.scale, (pos.y() - c) / self.scale, len(self.petals))

    def _set_hot(self, i):
        if i != self.hot:
            self.hot = i; self.update()
            if i is not None:
                if self.sound_on and self._snd and self._snd.status() == QSoundEffect.Ready: self._snd.play()
                self.hovered.emit(i)

    def mouseMoveEvent(self, e): self._set_hot(self._hit(e.position()))

    def mousePressEvent(self, e):  # click-to-choose (no drag): practice wheel, fallback mode
        i = self._hit(e.position())
        if i is not None and self.files:
            self._choose(i)

    def leaveEvent(self, _): self._set_hot(None)

    def _choose(self, i: int):
        self._dropped = True
        pid = self.petals[i][0]; files = list(self.files); mode = self.mode
        if self.overlay: self.dismiss()
        self.chosen.emit(mode, pid, files)

    # ---- drag & drop target ----
    @staticmethod
    def _paths(md) -> list[Path]:
        return [Path(u.toLocalFile()) for u in md.urls() if u.isLocalFile()]

    def dragEnterEvent(self, e):
        if e.mimeData().hasUrls():
            self._hide_timer.stop()
            self.set_files(self._paths(e.mimeData())); e.acceptProposedAction()

    def dragMoveEvent(self, e):
        self._hide_timer.stop()
        self._set_hot(self._hit(e.position())); e.acceptProposedAction()

    def dragLeaveEvent(self, _): self._set_hot(None)

    def dropEvent(self, e):
        i = self._hit(e.position())
        e.acceptProposedAction()
        if i is None:
            self.dismiss(); return
        self._choose(i)
