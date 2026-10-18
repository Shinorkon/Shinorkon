"""Data-driven wheel contents: tools per file kind, option schemas, and file actions."""
from __future__ import annotations

from pathlib import Path

from . import core, tools

# field: (key, label, type, ...)  types: slider(min,max,default) | text(default) | choice(options, default)
TOOLS = {
    "compress": dict(label="Compress", fields=[("quality", "Quality (higher = larger file)", "slider", 1, 99, 70)],
                     run=lambda f, o: tools.compress(f, int(o["quality"]))),
    "resize": dict(label="Resize", fields=[("percent", "Scale %", "slider", 5, 200, 50)],
                   run=lambda f, o: tools.resize(f, int(o["percent"]))),
    "rotate": dict(label="Rotate", fields=[("degrees", "Degrees", "choice", ["90", "180", "270"], "90")],
                   run=lambda f, o: tools.rotate(f, int(o["degrees"]))),
    "strip": dict(label="Remove metadata", fields=[], run=lambda f, o: tools.strip_metadata(f)),
    "metadata": dict(label="Read metadata", fields=[], text=True, run=lambda f, o: tools.read_metadata(f)),
    "trim": dict(label="Trim", fields=[("start", "Start (s or HH:MM:SS)", "text", "0"),
                                       ("end", "End (s or HH:MM:SS)", "text", "10")],
                 run=lambda f, o: tools.trim(f, o["start"], o["end"])),
    "speed": dict(label="Speed", fields=[("factor", "Speed (0.25–4×)", "text", "2")],
                  run=lambda f, o: tools.speed(f, float(o["factor"]))),
    "snapshot": dict(label="Snapshot", fields=[("at", "Time", "text", "00:00:01")],
                     run=lambda f, o: tools.snapshot(f, o["at"])),
    "normalize": dict(label="Normalize", fields=[("lufs", "Target LUFS", "text", "-16")],
                      run=lambda f, o: tools.normalize(f, float(o["lufs"]))),
    "split": dict(label="Split pages", fields=[], run=lambda f, o: tools.split_pdf(f)),
    "qr": dict(label="Read QR", fields=[], text=True, run=lambda f, o: "\n".join(tools.read_qr(f)) or "No QR code found"),
}
MERGE = dict(label="Merge PDFs", fields=[], multi=True, run=lambda fs, o: tools.merge_pdfs(fs))

TOOLS_BY_KIND = {
    "image": ["compress", "resize", "rotate", "strip", "metadata", "qr"],
    "video": ["compress", "trim", "speed", "snapshot", "strip", "metadata"],
    "audio": ["compress", "trim", "speed", "normalize", "strip", "metadata"],
    "pdf": ["compress", "split", "metadata"],
    "doc": [], "subs": [], "archive": [],
}

ACTIONS = ["float", "copy", "move", "copy-path", "terminal"]
ACTION_LABELS = {"float": "Float", "copy": "Copy", "move": "Move", "copy-path": "Copy Path", "terminal": "Terminal"}

MODES = {
    "convert": dict(title="Convert", default_mod="shift"),
    "tools": dict(title="Tools", default_mod="cmd"),
    "actions": dict(title="Actions", default_mod="ctrl"),
}


def common_kind(files: list[Path]) -> str | None:
    kinds = {core.kind(Path(f)) for f in files}
    return kinds.pop() if len(kinds) == 1 else None


def petals(mode: str, files: list[Path]) -> list[tuple[str, str]]:
    """(id, label) petals for a mode, filtered by what every dropped file supports."""
    if not files:
        return []
    if mode == "actions":
        return [(a, ACTION_LABELS[a]) for a in ACTIONS]
    if mode == "convert":
        common = set(core.targets(Path(files[0])))
        for f in files[1:]:
            common &= set(core.targets(Path(f)))
        order = core.OUTPUTS.get(common_kind(files) or "", [])
        return [(t, t.upper()) for t in order if t in common]
    k = common_kind(files)
    if k is None:
        return []
    ids = [t for t in TOOLS_BY_KIND.get(k, []) if not (len(files) > 1 and t in ("metadata", "qr"))]
    out = [(t, TOOLS[t]["label"]) for t in ids]
    if k == "pdf" and len(files) > 1:
        out.insert(0, ("merge", MERGE["label"]))
    return out


def tool_spec(tool_id: str) -> dict:
    return MERGE if tool_id == "merge" else TOOLS[tool_id]
