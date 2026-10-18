# Mandarin

An offline, local-only "drag → wheel → drop" file converter for **Linux and macOS**. Same workflow
as the app that inspired it, written from scratch (own code, icon, sound and copy; a different name).

Hold a modifier while dragging a file anywhere (Finder, Nautilus, Dolphin, Thunar…): a radial wheel
appears at the pointer. Drop on a petal and the result is saved **beside the original** (never
overwriting). Nothing is uploaded.

| Hold while dragging | Wheel | Petals |
|---|---|---|
| **Shift** | Convert | output formats valid for every dragged file |
| **Command** (mac) / **Alt** (Linux) | Tools | compress, resize, rotate, trim, speed, snapshot, normalize, metadata, QR, merge/split PDF |
| **Control** | Actions | Float, Copy, Move, Copy Path, Terminal |

Modifiers, theme (glass/solid), sound and launch-at-login are in tray → Settings. Switch modifiers
mid-drag to switch wheels; Esc cancels. Float is an always-on-top shelf you can drag files back out of.

## How the overlay works
A global listener (pynput) only decides *when* to show the wheel (button down + movement + modifier).
The wheel window is itself the drop target, so it receives the file list directly from the drag
source: no accessibility-API reading of Finder/Nautilus. It is frameless, translucent, always on
top and never takes focus.

## Install
    pip install .[input]                 # PySide6 + pynput; add PySide6-Addons for the highlight sound
    mandarin tray                        # run the agent (tray icon + wheel)
    # engines (install what you need):
    #   Linux: sudo apt install ffmpeg pandoc libreoffice poppler-utils qpdf ghostscript libimage-exiftool-perl zbar-tools webp
    #   macOS: brew install ffmpeg pandoc poppler qpdf ghostscript exiftool zbar webp && brew install --cask libreoffice
macOS: grant Accessibility/Input Monitoring to your terminal or Python so the drag listener works.

## Fallbacks (important)
- **Wayland (GNOME/Mutter):** apps can't observe global input or position windows, so the drag-summoned
  wheel can't appear. Use tray → *Convert files…* or `mandarin wheel FILE… [--mode tools]`; the wheel opens
  and you **click** a petal. X11, XWayland sessions and macOS get the full drag behaviour; KDE/Sway Wayland is untested.
- Without `pynput`, the tray still works the same way.

## CLI (headless, same engine)
    mandarin convert a.png b.png --to webp | formats clip.mov | compress v.mp4 --quality 60 | strip photo.jpg
    mandarin trim song.mp3 00:10 00:40 | merge-pdf a.pdf b.pdf | split-pdf big.pdf | qr code.png

## Engines
ffmpeg (images/audio/video; cwebp for WebP when present), pandoc / LibreOffice (documents), poppler
(PDF→image/text), ExifTool, qpdf/poppler, zbar, plus pure-Python SRT⇄VTT and ZIP/TAR/GZIP.

## Status / not done
Verified here (headless): engine paths, tools, wheel geometry/rendering, click→job→output, tests.
**Not verified on a real desktop:** global drag summon and OS drop onto the overlay (Linux X11, macOS) — needs a
manual pass. Not implemented: RAR, PAGES/iWork, annotation/redaction/collage editors, AirDrop,
trial/licensing, packaging. Run tests: `pip install pytest && pytest`.
