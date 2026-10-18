import shutil
import subprocess
import pytest

from mandarin import geometry as geo, registry
from mandarin.monitor import mode_for


def test_petal_hit_testing():
    assert geo.petal_at(0, -100, 8) == 0          # 12 o'clock
    assert geo.petal_at(100, 0, 8) == 2           # 3 o'clock
    assert geo.petal_at(0, 10, 8) is None         # inside hub
    assert geo.petal_at(0, -200, 8) is None       # outside fan
    assert geo.petal_at(-1, -100, 8) == 7         # just left of 12 -> last petal


def test_mode_for_bindings():
    b = {"convert": "shift", "tools": "alt", "actions": "ctrl"}
    assert mode_for({"shift"}, b) == "convert"
    assert mode_for({"alt"}, b) == "tools"
    assert mode_for({"ctrl"}, b) == "actions"
    assert mode_for(set(), b) is None
    assert mode_for({"cmd"}, {**b, "tools": "super"}) == "tools"


def test_petals_filtered_by_kind(tmp_path):
    png = tmp_path / "a.png"; png.write_bytes(b"x")
    mp3 = tmp_path / "b.mp3"; mp3.write_bytes(b"x")
    ids = [p for p, _ in registry.petals("convert", [png])]
    assert "jpg" in ids and "png" not in ids and "mp3" not in ids
    assert registry.petals("convert", [png, mp3]) == []          # no shared output
    assert [p for p, _ in registry.petals("actions", [png])][0] == "float"
    assert "trim" in [p for p, _ in registry.petals("tools", [mp3])]


def test_pdf_merge_petal_for_multiple_pdfs(tmp_path):
    a = tmp_path / "a.pdf"; b = tmp_path / "b.pdf"; a.write_bytes(b"x"); b.write_bytes(b"x")
    assert registry.petals("tools", [a, b])[0][0] == "merge"


@pytest.mark.skipif(not shutil.which("ffmpeg"), reason="ffmpeg missing")
def test_wheel_click_runs_conversion(tmp_path):
    from PySide6.QtWidgets import QApplication
    from PySide6.QtCore import QPointF, QEventLoop, QTimer
    from PySide6.QtGui import QMouseEvent
    from PySide6.QtCore import Qt, QEvent
    from mandarin.wheelview import WheelView
    from mandarin.jobs import Job
    app = QApplication.instance() or QApplication([])
    src = tmp_path / "in.png"
    subprocess.run(["ffmpeg", "-v", "error", "-f", "lavfi", "-i", "testsrc=size=64x64", "-frames:v", "1", str(src)], check=True)
    w = WheelView(); w.set_files([src])
    picked = []
    w.chosen.connect(lambda m, p, f: picked.append((m, p, f)))
    c = w.width() / 2
    pos = QPointF(c, c - 100)       # petal 0 (first target = jpg)
    w.mousePressEvent(QMouseEvent(QEvent.MouseButtonPress, pos, Qt.LeftButton, Qt.LeftButton, Qt.NoModifier))
    assert picked and picked[0][1] == "jpg"
    job = Job(*picked[0]); results = []
    job.done.connect(lambda o, t, e: results.append((o, e)))
    loop = QEventLoop(); job.done.connect(lambda *_: loop.quit()); QTimer.singleShot(15000, loop.quit)
    job.start(); loop.exec(); job.wait()
    outs, errs = results[0]
    assert not errs and (tmp_path / "in.jpg").exists()
