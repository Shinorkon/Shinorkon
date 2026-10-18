import argparse
import sys
from pathlib import Path

from . import __version__, core, tools


def doctor() -> int:
    import os, platform, time
    print("OS:", platform.system(), "| session:", os.environ.get("XDG_SESSION_TYPE", "n/a"),
          "| desktop:", os.environ.get("XDG_CURRENT_DESKTOP", "n/a"))
    if os.environ.get("XDG_SESSION_TYPE") == "wayland":
        from .monitor import EvdevInput
        try:
            n = len(EvdevInput.open_devices())
        except Exception as e:
            n = 0; print("! evdev error:", e)
        if n:
            print(f"Wayland: reading {n} input devices via evdev. OK.")
            if os.environ.get("HYPRLAND_INSTANCE_SIGNATURE"): print("Hyprland detected: cursor position via hyprctl.")
            else: print("! Not Hyprland: overlay may not be placeable at the pointer; use `mandarin wheel FILE...` if so.")
            seen = {"move": 0, "click": 0, "key": set()}
            from types import SimpleNamespace
            ev = EvdevInput(lambda x, y: seen.__setitem__("move", seen["move"] + 1),
                            lambda *a: seen.__setitem__("click", seen["click"] + 1),
                            lambda k: seen["key"].add(k.name), lambda k: None)
            ev.start(); print("Listening 6s: move the mouse, click, press Shift/Ctrl/Alt...")
            time.sleep(6); ev.stop()
            print(f"mouse moves: {seen['move']}, left clicks: {seen['click']}, keys: {sorted(seen['key']) or 'none'}")
            return 0
        print("! Cannot read /dev/input. Fix: sudo usermod -aG input $USER   then log out and back in.")
        return 1
    try:
        from pynput import keyboard, mouse
    except Exception as e:
        print("! pynput unavailable:", e, "\n  fix: pip install pynput"); return 1
    seen = {"move": 0, "click": 0, "key": set()}
    ml = mouse.Listener(on_move=lambda x, y: seen.__setitem__("move", seen["move"] + 1),
                        on_click=lambda *a: seen.__setitem__("click", seen["click"] + 1))
    kl = keyboard.Listener(on_press=lambda k: seen["key"].add(getattr(k, "name", str(k))))
    ml.start(); kl.start()
    print("Listening 6s: move the mouse, click, and press Shift / Ctrl / Alt (Cmd on mac)...")
    time.sleep(6); ml.stop(); kl.stop()
    print(f"mouse moves: {seen['move']}, clicks: {seen['click']}, keys: {sorted(seen['key']) or 'none'}")
    if not seen["move"]:
        print("! No mouse events: input is blocked. macOS: System Settings > Privacy > Accessibility + Input Monitoring.")
    elif not seen["key"]:
        print("! Mouse works but no key events: check Input Monitoring (mac) / session type (Linux).")
    else:
        print("Input OK. If the wheel still doesn't show, run `mandarin tray` and keep it running while you drag.")
    return 0


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="mandarin", description="Offline file converter")
    p.add_argument("--version", action="version", version=__version__)
    sub = p.add_subparsers(dest="cmd")
    c = sub.add_parser("convert", help="convert files; output is saved beside the source")
    c.add_argument("files", nargs="+", type=Path); c.add_argument("--to", required=True)
    f = sub.add_parser("formats", help="list target formats for a file"); f.add_argument("file", type=Path)
    t = sub.add_parser("compress"); t.add_argument("files", nargs="+", type=Path)
    t.add_argument("--quality", type=int, default=70)
    s = sub.add_parser("strip", help="remove metadata"); s.add_argument("files", nargs="+", type=Path)
    tr = sub.add_parser("trim"); tr.add_argument("file", type=Path)
    tr.add_argument("start"); tr.add_argument("end")
    m = sub.add_parser("merge-pdf"); m.add_argument("files", nargs="+", type=Path)
    sp = sub.add_parser("split-pdf"); sp.add_argument("file", type=Path)
    q = sub.add_parser("qr"); q.add_argument("file", type=Path)
    sub.add_parser("doctor", help="diagnose why the drag wheel does not appear")
    sub.add_parser("tray", help="run the menu-bar/tray agent (drag with a modifier held to summon the wheel)")
    wh = sub.add_parser("wheel", help="open the wheel for given files (click a petal)"); wh.add_argument("files", nargs="+", type=Path)
    wh.add_argument("--mode", default="convert", choices=["convert", "tools", "actions"])
    a = p.parse_args(argv)
    if a.cmd == "doctor":
        return doctor()
    if a.cmd in (None, "tray", "wheel"):
        from .app import prepare_platform
        prepare_platform()
        from PySide6.QtWidgets import QApplication
        from .app import MandarinApp
        qapp = QApplication(sys.argv); qapp.setQuitOnLastWindowClosed(False)
        m = MandarinApp(qapp)
        if a.cmd == "wheel":
            m.show_for(a.files, a.mode)
        return qapp.exec()
    rc = 0
    try:
        if a.cmd == "formats":
            print(" ".join(core.targets(a.file)) or "unsupported")
        elif a.cmd == "merge-pdf":
            print(tools.merge_pdfs(a.files))
        elif a.cmd == "split-pdf":
            print(*tools.split_pdf(a.file), sep="\n")
        elif a.cmd == "trim":
            print(tools.trim(a.file, a.start, a.end))
        elif a.cmd == "qr":
            print(*tools.read_qr(a.file), sep="\n")
        else:
            for file in a.files:
                try:
                    if a.cmd == "convert": print(core.convert(file, a.to))
                    elif a.cmd == "compress": print(tools.compress(file, a.quality))
                    elif a.cmd == "strip": print(tools.strip_metadata(file))
                except core.ConvertError as e:
                    print(f"{file}: {e}", file=sys.stderr); rc = 1
    except core.ConvertError as e:
        print(e, file=sys.stderr); rc = 1
    return rc


if __name__ == "__main__":
    sys.exit(main())
