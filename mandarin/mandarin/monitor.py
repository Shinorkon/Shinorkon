"""Global drag watcher. Only decides *when* to summon the wheel; the wheel window itself is the
drop target, so no accessibility hooks are needed to read the dragged files."""
from __future__ import annotations

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
        return mouse is not None

    def bindings(self) -> dict[str, str]:
        return {m: self.settings.get(f"mod/{m}") for m in ("convert", "tools", "actions")}

    def start(self):
        if not self.available: return
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
        if button != mouse.Button.left: return
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
