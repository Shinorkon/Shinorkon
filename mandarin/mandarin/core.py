"""Format registry, job planning and execution. Everything runs locally."""
from __future__ import annotations

import shutil
import subprocess
import tarfile
import zipfile
import gzip
import re
from dataclasses import dataclass
from pathlib import Path

IMAGE = {"jpg", "jpeg", "png", "webp", "heic", "tiff", "tif", "bmp", "gif", "avif"}
VIDEO = {"mp4", "mov", "mkv", "avi", "wmv", "webm"}
AUDIO = {"mp3", "m4a", "wav", "flac", "ogg", "opus", "aiff", "wma"}
DOC = {"docx", "doc", "odt", "rtf", "txt", "md", "html", "epub", "pptx", "ppt", "xlsx", "ods", "csv"}
SUBS = {"srt", "vtt"}
PDF = {"pdf"}
ARCHIVE = {"zip", "tar", "gz"}

OUTPUTS = {
    "image": ["jpg", "png", "webp", "tiff", "bmp", "gif", "avif", "pdf"],
    "video": ["mp4", "mov", "mkv", "avi", "webm", "gif", "mp3"],
    "audio": ["mp3", "m4a", "wav", "flac", "ogg", "opus", "aiff"],
    "doc": ["pdf", "docx", "odt", "txt", "html", "md", "epub"],
    "pdf": ["png", "jpg", "txt", "docx"],
    "subs": ["srt", "vtt"],
    "archive": ["zip", "tar", "gz"],
}


class ConvertError(RuntimeError):
    pass


def ext(path: Path) -> str:
    return path.suffix.lower().lstrip(".")


def kind(path: Path) -> str | None:
    e = ext(path)
    if path.suffix.lower() == ".gz" or e in ARCHIVE:
        return "archive"
    for name, group in (("image", IMAGE), ("video", VIDEO), ("audio", AUDIO),
                        ("subs", SUBS), ("pdf", PDF), ("doc", DOC)):
        if e in group:
            return name
    if path.is_dir():
        return "archive"
    return None


def targets(path: Path) -> list[str]:
    k = kind(path)
    if not k:
        return []
    return [t for t in OUTPUTS[k] if t != ext(path)]


def unique_output(src: Path, new_ext: str, suffix: str = "") -> Path:
    """Save beside the source, never overwriting an existing file."""
    base = src.with_name(src.stem + suffix) if src.is_file() else src.with_name(src.name + suffix)
    out = base.with_suffix("." + new_ext)
    n = 1
    while out.exists():
        out = base.with_name(f"{base.name} ({n})").with_suffix("." + new_ext)
        n += 1
    return out


def need(*tools: str) -> str:
    for t in tools:
        p = shutil.which(t)
        if p:
            return p
    raise ConvertError(f"Required tool not found: {' or '.join(tools)}. See README for install hints.")


def run(cmd: list[str]) -> None:
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        tail = (r.stderr or r.stdout).strip().splitlines()[-3:]
        raise ConvertError(f"{Path(cmd[0]).name} failed: " + " | ".join(tail))


# ---------- subtitles (pure python) ----------
def convert_subtitles(src: Path, out: Path) -> None:
    text = src.read_text(encoding="utf-8-sig", errors="replace").replace("\r\n", "\n")
    if ext(src) == "srt" and ext(out) == "vtt":
        text = re.sub(r"(\d{2}:\d{2}:\d{2}),(\d{3})", r"\1.\2", text)
        out.write_text("WEBVTT\n\n" + text.strip() + "\n", encoding="utf-8")
    elif ext(src) == "vtt" and ext(out) == "srt":
        text = re.sub(r"^WEBVTT.*?\n\n", "", text, flags=re.S)
        text = re.sub(r"(\d{2}:\d{2}:\d{2})\.(\d{3})", r"\1,\2", text)
        text = re.sub(r"(^|\n\n)(\d{2}:\d{2}[:.,])", lambda m: m.group(0), text)
        blocks = [b for b in text.strip().split("\n\n") if b.strip()]
        lines = []
        for i, b in enumerate(blocks, 1):
            parts = b.split("\n")
            if "-->" not in parts[0] and len(parts) > 1:
                parts = parts[1:]  # drop cue id
            lines.append(f"{i}\n" + "\n".join(parts))
        out.write_text("\n\n".join(lines) + "\n", encoding="utf-8")
    else:
        raise ConvertError("Unsupported subtitle conversion")


# ---------- archives (stdlib) ----------
def convert_archive(src: Path, out: Path) -> None:
    import tempfile
    with tempfile.TemporaryDirectory(prefix="mandarin-archive-") as tmp:
        tmpd = Path(tmp)
        if src.is_dir():
            work = src
        elif zipfile.is_zipfile(src):
            work = tmpd / "x"
            with zipfile.ZipFile(src) as z:
                for m in z.namelist():  # zip-slip guard
                    if not (work / m).resolve().is_relative_to(work.resolve()):
                        raise ConvertError("Unsafe path in archive")
                z.extractall(work)
        elif tarfile.is_tarfile(src):
            work = tmpd / "x"
            with tarfile.open(src) as t:
                t.extractall(work, filter="data")
        elif src.suffix.lower() == ".gz":
            work = tmpd / "x"; work.mkdir()
            with gzip.open(src, "rb") as f, open(work / src.with_suffix("").name, "wb") as o:
                shutil.copyfileobj(f, o)
        else:
            raise ConvertError("Unrecognised archive")
        o = ext(out)
        if o == "zip":
            with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
                for p in sorted(work.rglob("*")) if work.is_dir() else [work]:
                    z.write(p, p.relative_to(work if work.is_dir() else work.parent))
        elif o == "tar":
            with tarfile.open(out, "w") as t:
                t.add(work, arcname=src.stem)
        elif o == "gz":
            files = [p for p in work.rglob("*") if p.is_file()] if work.is_dir() else [work]
            if len(files) != 1:
                raise ConvertError("gzip holds a single file; choose zip or tar instead")
            with open(files[0], "rb") as f, gzip.open(out, "wb") as g:
                shutil.copyfileobj(f, g)


# ---------- command builders ----------
def convert(src: Path, target: str, progress=None) -> Path:
    src = Path(src)
    k = kind(src)
    target = target.lower().lstrip(".")
    if k is None:
        raise ConvertError(f"Unsupported file: {src.name}")
    if target not in targets(src):
        raise ConvertError(f"Cannot convert {ext(src) or 'folder'} to {target}")
    out = unique_output(src, target)
    try:
        if k == "subs":
            convert_subtitles(src, out)
        elif k == "archive":
            convert_archive(src, out)
        elif k == "image":
            _image(src, out, target)
        elif k == "pdf":
            _pdf(src, out, target)
        elif k in ("video", "audio"):
            _av(src, out, target)
        else:
            _doc(src, out, target)
    except Exception:
        out.unlink(missing_ok=True)
        raise
    return out


def _image(src: Path, out: Path, target: str) -> None:
    if target == "webp" and shutil.which("cwebp") and ext(src) in ("png", "jpg", "jpeg", "tiff", "tif"):
        run([need("cwebp"), "-q", "90", str(src), "-o", str(out)])
        return
    if target == "pdf":
        try:
            from PIL import Image
            with Image.open(src) as im:
                im.convert("RGB").save(out, "PDF")
            return
        except ImportError:
            pass
    run([need("ffmpeg"), "-v", "error", "-n", "-i", str(src), "-frames:v", "1", str(out)])


def _av(src: Path, out: Path, target: str) -> None:
    cmd = [need("ffmpeg"), "-v", "error", "-n", "-i", str(src)]
    if target == "gif":
        cmd += ["-vf", "fps=12,scale=640:-1:flags=lanczos"]
    elif target == "mp3":
        cmd += ["-vn", "-q:a", "2"]
    cmd.append(str(out))
    run(cmd)


def _doc(src: Path, out: Path, target: str) -> None:
    s = ext(src)
    office = s in {"docx", "doc", "odt", "rtf", "pptx", "ppt", "xlsx", "ods", "csv"}
    pandoc_ok = s in {"docx", "odt", "md", "html", "epub", "txt", "rtf"} and target in {
        "docx", "odt", "txt", "html", "md", "epub"}
    if pandoc_ok and shutil.which("pandoc"):
        run([need("pandoc"), str(src), "-o", str(out)])
        return
    if target == "pdf" and s == "md" and shutil.which("pandoc"):
        run([need("pandoc"), str(src), "-o", str(out)])
        return
    if office or target == "pdf" or s in {"txt", "html", "md"}:
        import tempfile
        with tempfile.TemporaryDirectory(prefix="mandarin-office-") as tmp:
            run([need("libreoffice", "soffice"), "--headless", "--convert-to", target,
                 "--outdir", tmp, str(src)])
            made = list(Path(tmp).glob("*." + target))
            if not made:
                raise ConvertError("LibreOffice produced no output")
            shutil.move(str(made[0]), out)
        return
    raise ConvertError(f"No converter available for {s} to {target}")


def _pdf(src: Path, out: Path, target: str) -> None:
    if target in ("png", "jpg"):
        import tempfile
        with tempfile.TemporaryDirectory(prefix="mandarin-pdf-") as tmp:
            run([need("pdftoppm"), "-r", "300", "-png" if target == "png" else "-jpeg", str(src), f"{tmp}/p"])
            pages = sorted(Path(tmp).glob("p*"))
            if not pages:
                raise ConvertError("PDF has no pages")
            if len(pages) == 1:
                shutil.move(str(pages[0]), out)
            else:  # one folder-free file per page, numbered beside the source
                shutil.move(str(pages[0]), out)
                for i, pg in enumerate(pages[1:], 2):
                    shutil.move(str(pg), unique_output(src, target, f"-page-{i}"))
    elif target == "txt":
        run([need("pdftotext"), "-layout", str(src), str(out)])
    else:
        import tempfile
        with tempfile.TemporaryDirectory(prefix="mandarin-office-") as tmp:
            run([need("libreoffice", "soffice"), "--headless", "--infilter=writer_pdf_import",
                 "--convert-to", target, "--outdir", tmp, str(src)])
            made = list(Path(tmp).glob("*." + target))
            if not made:
                raise ConvertError("LibreOffice produced no output")
            shutil.move(str(made[0]), out)
