import argparse
import sys
from pathlib import Path

from . import __version__, core, tools


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
    sub.add_parser("tray", help="run the menu-bar/tray agent (drag with a modifier held to summon the wheel)")
    wh = sub.add_parser("wheel", help="open the wheel for given files (click a petal)"); wh.add_argument("files", nargs="+", type=Path)
    wh.add_argument("--mode", default="convert", choices=["convert", "tools", "actions"])
    a = p.parse_args(argv)
    if a.cmd in (None, "tray", "wheel"):
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
