#!/usr/bin/env python3
"""Render checked-in PNGs from the selected SVG (requires librsvg)."""
from pathlib import Path
import shutil
import subprocess

root = Path(__file__).resolve().parents[1]
renderer = shutil.which("rsvg-convert")
if not renderer:
    raise SystemExit("Install librsvg (brew install librsvg) to render SVG icons.")
for size in (16, 32, 48, 128):
    subprocess.run([renderer, "-w", str(size), "-h", str(size),
                    str(root / "extension/icon.svg"), "-o",
                    str(root / f"extension/icon{size}.png")], check=True)
(root / "extension/icon.png").write_bytes((root / "extension/icon128.png").read_bytes())
print("Rendered 16, 32, 48, and 128 px icons from extension/icon.svg")
