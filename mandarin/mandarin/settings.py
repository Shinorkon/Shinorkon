from __future__ import annotations

import platform
import sys
from pathlib import Path

from PySide6.QtCore import QSettings

MAC = platform.system() == "Darwin"
MOD_CHOICES = ["shift", "ctrl", "alt", "cmd"] if MAC else ["shift", "ctrl", "alt", "super"]
DEFAULTS = {
    "mod/convert": "shift",
    "mod/tools": "cmd" if MAC else "alt",
    "mod/actions": "ctrl",
    "theme": "glass",      # glass | solid
    "sound": True,
    "welcome_done": False,
    "autostart": False,
}


class Settings:
    def __init__(self, path: str | None = None):
        self.q = QSettings(path, QSettings.IniFormat) if path else QSettings("mandarin", "mandarin")

    def get(self, key):
        v = self.q.value(key, DEFAULTS[key])
        if isinstance(DEFAULTS[key], bool):
            return v in (True, "true", "1", 1)
        return v

    def set(self, key, value):
        self.q.setValue(key, value)
        if key == "autostart":
            set_autostart(bool(value))


def set_autostart(on: bool) -> None:
    exe = f"{sys.executable} -m mandarin tray"
    if MAC:
        p = Path.home() / "Library/LaunchAgents/io.mandarin.plist"
        if on:
            args = "".join(f"<string>{a}</string>" for a in exe.split())
            p.write_text('<?xml version="1.0" encoding="UTF-8"?><plist version="1.0"><dict>'
                         '<key>Label</key><string>io.mandarin</string><key>RunAtLoad</key><true/>'
                         f"<key>ProgramArguments</key><array>{args}</array></dict></plist>")
        else:
            p.unlink(missing_ok=True)
    else:
        p = Path.home() / ".config/autostart/mandarin.desktop"
        if on:
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(f"[Desktop Entry]\nType=Application\nName=Mandarin\nExec={exe}\n")
        else:
            p.unlink(missing_ok=True)
