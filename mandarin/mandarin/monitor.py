"""Global drag watcher. Only decides *when* to summon the wheel; the wheel window itself is the
drop target, so no accessibility hooks are needed to read the dragged files."""
from __future__ import annotations

import os
import select
import threading
from types import SimpleNamespace

from PySide6.QtCore import QObject, Signal

from . import settings as S

try:
    from pynput import keyboard, mouse
except Exception:  # headless or Wayland without an input backend
    keyboard = mouse = None

NAMES = {"shift": "shift", "shift_l": "shift", "shift_r": "shift", "ctrl": "ctrl", "ctrl_l": "ctrl",
         "ctrl_r": "ctrl", "alt": "alt", "alt_l": "alt", "alt_r": "alt", "alt_gr": "alt",
         "cmd": "cmd", "cmd_l": "cmd", "cmd_r": "cmd"}
DRAG_THRESHOLD = 8
EVDEV_KEYS = {"KEY_LEFTSHIFT": "shift", "KEY_RIGHTSHIFT": "shift", "KEY_LEFTCTRL": "ctrl",
              "KEY_RIGHTCTRL": "ctrl", "KEY_LEFTALT": "alt", "KEY_RIGHTALT": "alt",
              "KEY_LEFTMETA": "cmd", "KEY_RIGHTMETA": "cmd", "KEY_ESC": "esc"}


def wayland() -> bool:
    return os.environ.get("XDG_SESSION_TYPE") == "wayland"


class EvdevInput:
    """Reads /dev/input directly (needs membership of the `input` group). Works on any Wayland
    compositor because it bypasses the compositor; only relative motion/buttons/keys are used."""
    def __init__(self, on_move, on_click, on_press, on_release):
        self.cb = (on_move, on_click, on_press, on_release)
        self.devs = []; self.stop_flag = threading.Event(); self.x = self.y = 0

    @staticmethod
    def open_devices():
        import evdev
        out = []
        for path in evdev.list_devices():
            try:
                d = evdev.InputDevice(path)
            except OSError:
                continue
            caps = d.capabilities()
            if evdev.ecodes.EV_KEY in caps or evdev.ecodes.EV_REL in caps:
                out.append(d)
        return out

    def start(self):
        self.devs = self.open_devices()
        if not self.devs:
            raise PermissionError("no readable /dev/input devices (add yourself to the 'input' group)")
        t = threading.Thread(target=self._loop, daemon=True); t.start()

    def stop(self):
        self.stop_flag.set()

    def _loop(self):
        import evdev
        from evdev import ecodes as e
        on_move, on_click, on_press, on_release = self.cb
        fds = {d.fd: d for d in self.devs}
        while not self.stop_flag.is_set():
            r, _, _ = select.select(list(fds), [], [], 0.25)
            for fd in r:
                try:
                    for ev in fds[fd].read():
                        if ev.type == e.EV_REL and ev.code in (e.REL_X, e.REL_Y):
                            if ev.code == e.REL_X: self.x += ev.value
                            else: self.y += ev.value
                            on_move(self.x, self.y)
                        elif ev.type == e.EV_KEY:
                            if ev.code == e.BTN_LEFT:
                                on_click(self.x, self.y, "left", ev.value == 1)
                            else:
                                name = EVDEV_KEYS.get(e.KEY.get(ev.code) if isinstance(e.KEY.get(ev.code), str) else
                                                      (e.KEY.get(ev.code) or [None])[0])
                                if name and ev.value == 1: on_press(SimpleNamespace(name=name))
                                elif name and ev.value == 0: on_release(SimpleNamespace(name=name))
                except OSError:
                    fds.pop(fd, None)


def mode_for(mods: set[str], bindings: dict[str, str]) -> str | None:
    """bindings maps mode -> modifier name. 'super' is pynput's 'cmd' on Linux."""
    for mode in ("convert", "tools", "actions"):
        want = "cmd" if bindings[mode] == "super" else bindings[mode]
        if want in mods:
            return mode
    return None


class DragMonitor(QObject):
    summon = Signal(str)       # mode
    mode_changed = Signal(str)
    released = Signal()
    cancelled = Signal()

    def __init__(self, settings: S.Settings):
        super().__init__()
        self.settings = settings
        self.mods: set[str] = set(); self.down = False; self.origin = None; self.active = False
        self.mode = None; self._listeners = []

    @property
    def available(self) -> bool:
        if wayland():
            try:
                EvdevInput.open_devices.__func__  # noqa: B018 (import check below)
                return bool(EvdevInput.open_devices())
            except Exception:
                return False
        return mouse is not None

    def bindings(self) -> dict[str, str]:
        return {m: self.settings.get(f"mod/{m}") for m in ("convert", "tools", "actions")}

    def start(self):
        if not self.available: return
        if wayland():
            ev = EvdevInput(self._move, self._click, self._press, self._release)
            ev.start(); self._listeners = [ev]; return
        self._listeners = [mouse.Listener(on_move=self._move, on_click=self._click),
                           keyboard.Listener(on_press=self._press, on_release=self._release)]
        for l in self._listeners: l.daemon = True; l.start()

    def stop(self):
        for l in self._listeners: l.stop()

    def _key(self, k) -> str | None:
        return NAMES.get(getattr(k, "name", None) or "")

    def _press(self, k):
        n = self._key(k)
        if n: self.mods.add(n); self._retarget()
        elif getattr(k, "name", "") == "esc" and self.active:
            self.active = False; self.cancelled.emit()

    def _release(self, k):
        n = self._key(k)
        if n: self.mods.discard(n); self._retarget()

    def _retarget(self):
        if not self.active: return
        m = mode_for(self.mods, self.bindings())
        if m and m != self.mode:
            self.mode = m; self.mode_changed.emit(m)

    def _click(self, x, y, button, pressed):
        if getattr(button, "name", button) != "left": return
        self.down = pressed
        if pressed: self.origin = (x, y)
        else:
            self.origin = None
            if self.active:
                self.active = False; self.released.emit()

    def _move(self, x, y):
        if not self.down or self.active or not self.origin: return
        if abs(x - self.origin[0]) + abs(y - self.origin[1]) < DRAG_THRESHOLD: return
        m = mode_for(self.mods, self.bindings())
        if m:
            self.active = True; self.mode = m; self.summon.emit(m)
