import zipfile
from pathlib import Path

import pytest

from mandarin import core


def test_kind_and_targets(tmp_path):
    f = tmp_path / "a.png"; f.write_bytes(b"x")
    assert core.kind(f) == "image" and "jpg" in core.targets(f) and "png" not in core.targets(f)


def test_unique_output_never_overwrites(tmp_path):
    src = tmp_path / "a.srt"; src.write_text("x")
    (tmp_path / "a.vtt").write_text("old")
    assert core.unique_output(src, "vtt").name == "a (1).vtt"


def test_srt_vtt_roundtrip(tmp_path):
    src = tmp_path / "s.srt"
    src.write_text("1\n00:00:01,000 --> 00:00:02,500\nHello\n")
    vtt = core.convert(src, "vtt")
    assert "00:00:01.000" in vtt.read_text() and vtt.read_text().startswith("WEBVTT")
    back = core.convert(vtt, "srt")
    assert "00:00:01,000 --> 00:00:02,500" in back.read_text()


def test_zip_to_tar(tmp_path):
    z = tmp_path / "p.zip"
    with zipfile.ZipFile(z, "w") as zf: zf.writestr("d/x.txt", "hi")
    assert core.convert(z, "tar").exists()


def test_unsupported(tmp_path):
    f = tmp_path / "a.xyz"; f.write_text("x")
    with pytest.raises(core.ConvertError): core.convert(f, "png")
