"""File tools: compress, strip metadata, trim, PDF merge/split, QR read."""
from __future__ import annotations

import shutil
from pathlib import Path

from .core import ConvertError, ext, kind, need, run, unique_output


def compress(src: Path, quality: int = 70) -> Path:
    """quality 1-100; higher is better quality / larger file."""
    src = Path(src); k = kind(src); e = ext(src)
    out = unique_output(src, e if e != "jpeg" else "jpg", "-compressed")
    ff = need("ffmpeg")
    if k == "image":
        if e in ("jpg", "jpeg"):
            run([ff, "-v", "error", "-n", "-i", str(src), "-q:v", str(max(2, 31 - quality * 29 // 100)), str(out)])
        elif e == "webp":
            run([ff, "-v", "error", "-n", "-i", str(src), "-quality", str(quality), str(out)])
        elif e == "png":
            run([ff, "-v", "error", "-n", "-i", str(src), "-compression_level", "9", str(out)])
        else:
            raise ConvertError(f"Compression for .{e} images is not supported")
    elif k == "video":
        crf = 40 - quality * 17 // 100  # q100->23, q0->40
        run([ff, "-v", "error", "-n", "-i", str(src), "-c:v", "libx264", "-crf", str(crf),
             "-preset", "medium", "-c:a", "aac", "-b:a", "128k", str(out)])
    elif k == "audio":
        br = f"{64 + quality * 256 // 100}k"
        run([ff, "-v", "error", "-n", "-i", str(src), "-b:a", br, str(out)])
    elif e == "pdf":
        gs = need("gs")
        setting = "/screen" if quality < 40 else "/ebook" if quality < 75 else "/printer"
        run([gs, "-q", "-sDEVICE=pdfwrite", f"-dPDFSETTINGS={setting}", "-dNOPAUSE", "-dBATCH",
             f"-sOutputFile={out}", str(src)])
    else:
        raise ConvertError("Nothing to compress for this file type")
    return out


def strip_metadata(src: Path) -> Path:
    src = Path(src)
    out = unique_output(src, ext(src), "-clean")
    if shutil.which("exiftool") and kind(src) == "image":
        shutil.copy2(src, out)
        run([need("exiftool"), "-all=", "-overwrite_original", str(out)])
    else:
        run([need("ffmpeg"), "-v", "error", "-n", "-i", str(src), "-map_metadata", "-1",
             "-map", "0", "-c", "copy", str(out)])
    return out


def trim(src: Path, start: str, end: str) -> Path:
    """start/end as seconds or HH:MM:SS. Stream-copies for speed."""
    src = Path(src)
    if kind(src) not in ("video", "audio"):
        raise ConvertError("Trim works on audio and video")
    out = unique_output(src, ext(src), "-trim")
    run([need("ffmpeg"), "-v", "error", "-n", "-ss", str(start), "-to", str(end),
         "-i", str(src), "-c", "copy", str(out)])
    return out


def merge_pdfs(files: list[Path]) -> Path:
    if len(files) < 2:
        raise ConvertError("Pick at least two PDFs to merge")
    out = unique_output(Path(files[0]), "pdf", "-merged")
    if shutil.which("qpdf"):
        run([need("qpdf"), "--empty", "--pages", *map(str, files), "--", str(out)])
    else:
        run([need("pdfunite"), *map(str, files), str(out)])
    return out


def split_pdf(src: Path) -> list[Path]:
    src = Path(src)
    pdfsep = need("pdfseparate")
    pattern = unique_output(src, "pdf", "-page-%d")
    run([pdfsep, str(src), str(pattern)])
    return sorted(pattern.parent.glob(pattern.name.replace("%d", "*")))


def read_qr(src: Path) -> list[str]:
    r = __import__("subprocess").run([need("zbarimg"), "--quiet", "--raw", str(src)],
                                     capture_output=True, text=True)
    return [l for l in r.stdout.splitlines() if l]


def _ff(src: Path, out: Path, *args: str) -> Path:
    run([need("ffmpeg"), "-v", "error", "-n", "-i", str(src), *args, str(out)])
    return out


def resize(src: Path, percent: int = 50) -> Path:
    src = Path(src)
    return _ff(src, unique_output(src, ext(src), "-resized"), "-vf", f"scale=iw*{percent}/100:-2")


def rotate(src: Path, degrees: int = 90) -> Path:
    src = Path(src)
    vf = {90: "transpose=1", 180: "transpose=1,transpose=1", 270: "transpose=2"}.get(int(degrees))
    if not vf:
        raise ConvertError("Rotation must be 90, 180 or 270")
    return _ff(src, unique_output(src, ext(src), "-rotated"), "-vf", vf)


def speed(src: Path, factor: float = 2.0) -> Path:
    src = Path(src); f = float(factor)
    if not 0.25 <= f <= 4:
        raise ConvertError("Choose a speed between 0.25x and 4x")
    out = unique_output(src, ext(src), f"-{f:g}x")
    atempo = []; r = f  # atempo accepts 0.5..2 per stage
    while r > 2: atempo.append(2.0); r /= 2
    while r < 0.5: atempo.append(0.5); r /= 0.5
    atempo.append(r)
    af = ",".join(f"atempo={a}" for a in atempo)
    if kind(src) == "audio":
        return _ff(src, out, "-af", af)
    return _ff(src, out, "-filter_complex", f"[0:v]setpts=PTS/{f}[v];[0:a]{af}[a]", "-map", "[v]", "-map", "[a]")


def snapshot(src: Path, at: str = "00:00:01") -> Path:
    src = Path(src)
    out = unique_output(src, "png", "-snapshot")
    run([need("ffmpeg"), "-v", "error", "-n", "-ss", str(at), "-i", str(src), "-frames:v", "1", str(out)])
    return out


def normalize(src: Path, lufs: float = -16.0) -> Path:
    src = Path(src)
    return _ff(src, unique_output(src, ext(src), "-normalized"), "-af", f"loudnorm=I={lufs}:TP=-1.5:LRA=11")


def read_metadata(src: Path) -> str:
    if shutil.which("exiftool"):
        r = __import__("subprocess").run([need("exiftool"), "-G1", "-s", str(src)], capture_output=True, text=True)
        return r.stdout
    r = __import__("subprocess").run([need("ffprobe"), "-v", "error", "-show_format", "-show_streams", str(src)],
                                     capture_output=True, text=True)
    return r.stdout
