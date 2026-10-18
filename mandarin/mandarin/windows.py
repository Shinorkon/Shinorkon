from __future__ import annotations

import shutil
from pathlib import Path

from PySide6.QtCore import QMimeData, Qt, QTimer, QUrl
from PySide6.QtGui import QDrag, QGuiApplication
from PySide6.QtWidgets import (QCheckBox, QComboBox, QDialog, QDialogButtonBox, QFileDialog, QFormLayout,
                               QHBoxLayout, QLabel, QLineEdit, QListWidget, QListWidgetItem, QMessageBox,
                               QPlainTextEdit, QProgressBar, QPushButton, QSlider, QVBoxLayout, QWidget)

from . import registry, settings as S
from .jobs import reveal
from .wheelview import WheelView

QSS = """
QWidget { background:#1e1b18; color:#fff4e6; font-size:13px; }
QPushButton { background:#3a312a; border:1px solid #55483d; border-radius:8px; padding:6px 14px; }
QPushButton:hover { background:#FF5200; border-color:#FF5200; }
QProgressBar { background:#3a312a; border:none; border-radius:4px; height:8px; }
QProgressBar::chunk { background:#FF5200; border-radius:4px; }
QLineEdit, QComboBox, QPlainTextEdit, QListWidget { background:#2a2521; border:1px solid #55483d; border-radius:6px; padding:4px; }
QSlider::groove:horizontal { height:6px; background:#3a312a; border-radius:3px; }
QSlider::sub-page:horizontal { background:#FF5200; border-radius:3px; }
QSlider::handle:horizontal { background:#fff4e6; width:14px; margin:-5px 0; border-radius:7px; }
"""


class ProgressWindow(QWidget):
    def __init__(self, title: str, count: int):
        super().__init__(None, Qt.Tool | Qt.WindowStaysOnTopHint)
        self.setWindowTitle("Mandarin is working"); self.setStyleSheet(QSS); self.setFixedWidth(340)
        v = QVBoxLayout(self)
        self.title = QLabel(f"{title} · {count} file{'s' if count != 1 else ''}"); v.addWidget(self.title)
        self.bar = QProgressBar(); self.bar.setRange(0, 0); self.bar.setTextVisible(False); v.addWidget(self.bar)
        self.msg = QLabel("Working…"); self.msg.setWordWrap(True); v.addWidget(self.msg)
        self.btn = QPushButton("Close"); self.btn.clicked.connect(self.close); self.btn.hide(); v.addWidget(self.btn)

    def finish(self, outs: list[str], errs: list[str], reveal_files=True):
        self.bar.setRange(0, 1); self.bar.setValue(1)
        self.setWindowTitle("Mandarin is ready")
        self.msg.setText((f"Saved {len(outs)} file{'s' if len(outs) != 1 else ''} beside the original" if outs else "") +
                         ("\n" + "\n".join(errs) if errs else ""))
        self.btn.show()
        if outs and reveal_files:
            reveal(Path(outs[0]))
        if outs and not errs:
            QTimer.singleShot(2500, self.close)


class OptionsDialog(QDialog):
    """Generic form generated from a registry field spec."""
    def __init__(self, title: str, fields: list, parent=None):
        super().__init__(parent); self.setWindowTitle(title); self.setStyleSheet(QSS)
        form = QFormLayout(self); self.getters = {}
        for key, label, typ, *rest in fields:
            if typ == "slider":
                lo, hi, default = rest
                s = QSlider(Qt.Horizontal); s.setRange(lo, hi); s.setValue(default)
                val = QLabel(str(default)); s.valueChanged.connect(lambda v, l=val: l.setText(str(v)))
                row = QHBoxLayout(); row.addWidget(s); row.addWidget(val); form.addRow(label, row)
                self.getters[key] = s.value
            elif typ == "choice":
                opts, default = rest
                c = QComboBox(); c.addItems(opts); c.setCurrentText(default); form.addRow(label, c)
                self.getters[key] = c.currentText
            else:
                e = QLineEdit(rest[0]); form.addRow(label, e); self.getters[key] = e.text
        bb = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        bb.accepted.connect(self.accept); bb.rejected.connect(self.reject); form.addRow(bb)

    def values(self) -> dict:
        return {k: g() for k, g in self.getters.items()}


class TextResult(QDialog):
    def __init__(self, title: str, text: str):
        super().__init__(); self.setWindowTitle(title); self.setStyleSheet(QSS); self.resize(520, 380)
        v = QVBoxLayout(self); t = QPlainTextEdit(text); t.setReadOnly(True); v.addWidget(t)
        b = QPushButton("Copy"); b.clicked.connect(lambda: QGuiApplication.clipboard().setText(text)); v.addWidget(b)


class FloatPanel(QWidget):
    """Always-on-top staging shelf: park files, drag them back out later."""
    def __init__(self):
        super().__init__(None, Qt.Tool | Qt.WindowStaysOnTopHint)
        self.setWindowTitle("Float"); self.setStyleSheet(QSS); self.resize(260, 300); self.setAcceptDrops(True)
        v = QVBoxLayout(self)
        self.list = QListWidget(); self.list.setSelectionMode(QListWidget.ExtendedSelection)
        self.list.setDragEnabled(True); self.list.startDrag = self._start_drag; v.addWidget(self.list)
        row = QHBoxLayout()
        rm = QPushButton("Remove from Float"); rm.clicked.connect(self.remove_selected)
        cl = QPushButton("Close"); cl.setToolTip("Close Float without deleting files"); cl.clicked.connect(self.hide)
        row.addWidget(rm); row.addWidget(cl); v.addLayout(row)

    def add(self, files):
        have = {self.list.item(i).data(Qt.UserRole) for i in range(self.list.count())}
        for f in files:
            if str(f) not in have:
                it = QListWidgetItem(Path(f).name); it.setData(Qt.UserRole, str(f)); it.setToolTip(str(f))
                self.list.addItem(it)
        self.show(); self.raise_()

    def remove_selected(self):
        for it in self.list.selectedItems(): self.list.takeItem(self.list.row(it))

    def _start_drag(self, _actions):
        items = self.list.selectedItems() or [self.list.currentItem()]
        md = QMimeData(); md.setUrls([QUrl.fromLocalFile(i.data(Qt.UserRole)) for i in items if i])
        d = QDrag(self); d.setMimeData(md); d.exec(Qt.CopyAction | Qt.MoveAction)

    def dragEnterEvent(self, e):
        if e.mimeData().hasUrls(): e.acceptProposedAction()

    def dropEvent(self, e):
        self.add([Path(u.toLocalFile()) for u in e.mimeData().urls() if u.isLocalFile()])


class SettingsDialog(QDialog):
    def __init__(self, st: S.Settings, on_change):
        super().__init__(); self.setWindowTitle("Mandarin Settings"); self.setStyleSheet(QSS)
        self.st = st; form = QFormLayout(self); self.on_change = on_change
        for mode, info in registry.MODES.items():
            c = QComboBox(); c.addItems(S.MOD_CHOICES); c.setCurrentText(st.get(f"mod/{mode}"))
            c.currentTextChanged.connect(lambda v, m=mode: self.set(f"mod/{m}", v))
            form.addRow(f"{info['title']} wheel — hold while dragging", c)
        theme = QComboBox(); theme.addItems(["glass", "solid"]); theme.setCurrentText(st.get("theme"))
        theme.currentTextChanged.connect(lambda v: self.set("theme", v)); form.addRow("Wheel theme", theme)
        for key, label in (("sound", "Highlight sound"), ("autostart", "Launch at login")):
            cb = QCheckBox(label); cb.setChecked(st.get(key)); cb.toggled.connect(lambda v, k=key: self.set(k, v))
            form.addRow(cb)

    def set(self, k, v): self.st.set(k, v); self.on_change()


class WelcomeDialog(QDialog):
    def __init__(self, st: S.Settings, on_done):
        super().__init__(); self.setWindowTitle("Welcome to Mandarin"); self.setStyleSheet(QSS)
        self.st, self.on_done = st, on_done
        h = QHBoxLayout(self); left = QVBoxLayout(); h.addLayout(left)
        mods = {m: st.get(f"mod/{m}").capitalize() for m in registry.MODES}
        text = QLabel(
            "<h2 style='color:#FF5200'>Convert files where you already are</h2>"
            f"<p>Hold <b>{mods['convert']}</b> while dragging a file: a wheel of output formats appears "
            "at your pointer. Drop on a petal — the copy is saved beside the original.</p>"
            f"<p><b>{mods['tools']}</b> opens tools for that file type; <b>{mods['actions']}</b> opens file actions "
            "(Float, Copy, Move, Copy Path, Terminal).</p>"
            "<p>Everything runs on your computer. Nothing is uploaded.</p>"
            "<p>Try the practice wheel →  (hover a petal)</p>")
        text.setWordWrap(True); text.setFixedWidth(300); left.addWidget(text)
        cb = QCheckBox("Launch at login"); cb.toggled.connect(lambda v: st.set("autostart", v)); left.addWidget(cb)
        go = QPushButton("Get started"); go.clicked.connect(self.finish); left.addWidget(go)
        practice = WheelView(self, sound=st.get("sound"), solid=st.get("theme") == "solid")
        practice.files = []; practice.petals = [(t, t.upper()) for t in ("jpg", "png", "webp", "heic", "tiff", "avif", "bmp", "pdf")]
        practice.mode = "convert"; practice.label_lines = lambda: ("PNG", "practice")
        h.addWidget(practice)

    def finish(self):
        self.st.set("welcome_done", True); self.on_done(); self.accept()
