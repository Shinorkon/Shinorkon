"""Tray agent: summons the wheel during a modifier-drag and runs the chosen job."""
from __future__ import annotations

import shutil
import sys
from pathlib import Path

from PySide6.QtCore import QPoint, Qt
from PySide6.QtGui import QAction, QColor, QCursor, QGuiApplication, QIcon, QPainter, QPixmap
from PySide6.QtCore import QMimeData, QUrl
from PySide6.QtWidgets import (QApplication, QFileDialog, QMenu, QMessageBox, QSystemTrayIcon)

from . import registry, settings as S
from .jobs import Job, open_terminal
from .monitor import DragMonitor
from .windows import (FloatPanel, OptionsDialog, ProgressWindow, SettingsDialog, TextResult, WelcomeDialog)
from .wheelview import WheelView, ACCENT


def cursor_pos():
    """Wayland hides the pointer from XWayland clients, so ask Hyprland where it is."""
    import json, os, subprocess
    if os.environ.get("HYPRLAND_INSTANCE_SIGNATURE") and shutil.which("hyprctl"):
        try:
            r = subprocess.run(["hyprctl", "cursorpos", "-j"], capture_output=True, text=True, timeout=0.3)
            d = json.loads(r.stdout); return QPoint(int(d["x"]), int(d["y"]))
        except Exception:
            pass
    return QCursor.pos()


def make_icon() -> QIcon:
    pm = QPixmap(64, 64); pm.fill(Qt.transparent)
    p = QPainter(pm); p.setRenderHint(QPainter.Antialiasing)
    p.setBrush(ACCENT); p.setPen(Qt.NoPen); p.drawEllipse(6, 8, 52, 52)
    p.setBrush(QColor("#3a8f3a")); p.drawEllipse(30, 2, 18, 12); p.end()
    return QIcon(pm)


class MandarinApp:
    def __init__(self, app: QApplication, settings: S.Settings | None = None):
        self.app, self.st = app, settings or S.Settings()
        self.jobs: list = []; self.windows: list = []; self.float = FloatPanel()
        self.wheel = WheelView(overlay=True)
        self.apply_settings()
        self.wheel.chosen.connect(self.on_chosen)
        self.monitor = DragMonitor(self.st)
        self.monitor.summon.connect(lambda m: self.wheel.summon(m, cursor_pos()))
        self.monitor.mode_changed.connect(self.wheel.set_mode)
        self.monitor.released.connect(self.wheel.drag_released)
        self.monitor.cancelled.connect(self.wheel.dismiss)
        self.tray = QSystemTrayIcon(make_icon()); self.tray.setToolTip("Mandarin")
        menu = QMenu()
        for text, fn in (("Convert files…", self.pick_and_show), ("Show Float", lambda: self.float.show()),
                         ("Settings…", self.open_settings), ("Welcome…", self.open_welcome)):
            a = QAction(text, menu); a.triggered.connect(fn); menu.addAction(a)
        menu.addSeparator(); q = QAction("Quit Mandarin", menu); q.triggered.connect(app.quit); menu.addAction(q)
        self.tray.setContextMenu(menu); self.tray.show(); self.menu = menu
        self.monitor.start()
        if not self.st.get("welcome_done"):
            self.open_welcome()
        elif not self.monitor.available:
            self.tray.showMessage("Mandarin", "Global drag detection unavailable; use the tray menu → Convert files…")

    def apply_settings(self):
        self.wheel.solid = self.st.get("theme") == "solid"
        self.wheel.sound_on = self.st.get("sound")

    # ---- entry points ----
    def pick_and_show(self):
        files, _ = QFileDialog.getOpenFileNames(None, "Choose files")
        if files:
            self.show_for(files, "convert")

    def show_for(self, files, mode="convert"):
        """Fallback when no drag is happening (Wayland/GNOME, CLI): click a petal instead."""
        self.wheel.files = [Path(f) for f in files]
        self.wheel.summon(mode, QGuiApplication.primaryScreen().geometry().center())
        self.wheel.activateWindow()

    def open_settings(self):
        d = SettingsDialog(self.st, self.apply_settings); self.windows.append(d); d.show()

    def open_welcome(self):
        d = WelcomeDialog(self.st, self.apply_settings); self.windows.append(d); d.show()

    # ---- wheel selection ----
    def on_chosen(self, mode: str, pid: str, files: list):
        files = [Path(f) for f in files]
        if mode == "actions":
            return self.do_action(pid, files)
        options = {}
        if mode == "tools":
            spec = registry.tool_spec(pid)
            if spec["fields"]:
                dlg = OptionsDialog(spec["label"], spec["fields"])
                if dlg.exec() != dlg.Accepted:
                    return
                options = dlg.values()
        title = ("Converting to " + pid.upper()) if mode == "convert" else registry.tool_spec(pid)["label"]
        win = ProgressWindow(title, len(files)); win.show(); self.windows.append(win)
        job = Job(mode, pid, files, options); self.jobs.append(job)
        job.done.connect(lambda outs, text, errs, w=win, j=job: self.job_done(w, j, outs, text, errs))
        job.start()

    def job_done(self, win, job, outs, text, errs):
        win.finish(outs, errs, reveal_files=not text)
        if text:
            r = TextResult("Result", text); self.windows.append(r); r.show()
        if job in self.jobs: self.jobs.remove(job)

    def do_action(self, action: str, files: list[Path]):
        cb = QGuiApplication.clipboard()
        if action == "float":
            self.float.add(files)
        elif action == "copy":
            md = QMimeData(); md.setUrls([QUrl.fromLocalFile(str(f)) for f in files]); cb.setMimeData(md)
        elif action == "copy-path":
            cb.setText("\n".join(str(f) for f in files))
        elif action == "terminal":
            open_terminal(files[0])
        elif action == "move":
            dest = QFileDialog.getExistingDirectory(None, "Move to…")
            if dest:
                for f in files:
                    try: shutil.move(str(f), str(Path(dest) / f.name))
                    except Exception as e: QMessageBox.warning(None, "Move failed", f"{f.name}: {e}")


def prepare_platform() -> None:
    """On Wayland, run Qt via XWayland (xcb): it lets us place a frameless overlay under the pointer."""
    import os
    if os.environ.get("XDG_SESSION_TYPE") == "wayland" and "QT_QPA_PLATFORM" not in os.environ:
        os.environ["QT_QPA_PLATFORM"] = "xcb"


def main_tray(argv=None) -> int:
    app = QApplication(argv or sys.argv); app.setQuitOnLastWindowClosed(False)
    m = MandarinApp(app)
    return app.exec()
