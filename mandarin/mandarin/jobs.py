"""Run conversions/tools off the UI thread; emits progress and results via Qt signals."""
from __future__ import annotations

import os
import platform
import shutil
import subprocess
from pathlib import Path

from PySide6.QtCore import QObject, QThread, Signal

from . import core, registry


class Job(QThread):
    done = Signal(list, str, list)   # output paths, text result, error messages

    def __init__(self, mode: str, petal: str, files: list[Path], options: dict | None = None):
        super().__init__()
        self.mode, self.petal, self.files, self.options = mode, petal, files, options or {}

    def run(self):
        outs, text, errs = [], "", []
        try:
            if self.mode == "convert":
                for f in self.files:
                    try: outs.append(core.convert(f, self.petal))
                    except Exception as e: errs.append(f"{Path(f).name}: {e}")
            else:
                spec = registry.tool_spec(self.petal)
                if spec.get("multi"):
                    r = spec["run"](self.files, self.options); outs.append(r)
                else:
                    for f in self.files:
                        try:
                            r = spec["run"](f, self.options)
                            if spec.get("text"): text += f"{Path(f).name}\n{r}\n"
                            else: outs.extend(r if isinstance(r, list) else [r])
                        except Exception as e: errs.append(f"{Path(f).name}: {e}")
        except Exception as e:
            errs.append(str(e))
        self.done.emit([str(o) for o in outs], text, errs)


def reveal(path: Path) -> None:
    path = Path(path)
    if platform.system() == "Darwin":
        subprocess.Popen(["open", "-R", str(path)])
    else:
        subprocess.Popen(["xdg-open", str(path.parent)])


def open_terminal(folder: Path) -> None:
    folder = Path(folder) if Path(folder).is_dir() else Path(folder).parent
    if platform.system() == "Darwin":
        subprocess.Popen(["open", "-a", "Terminal", str(folder)])
        return
    for term in (os.environ.get("TERMINAL"), "x-terminal-emulator", "gnome-terminal", "konsole", "xterm"):
        if term and shutil.which(term):
            args = [term, "--working-directory", str(folder)] if term in ("gnome-terminal", "konsole") else [term]
            subprocess.Popen(args, cwd=folder)
            return
