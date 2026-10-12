#!/usr/bin/env python3
"""Build an unsigned XPI with deterministic ordering and timestamps."""
import json
from pathlib import Path
import zipfile

root = Path(__file__).resolve().parents[1]
extension = root / "extension"
manifest = json.loads((extension / "manifest.json").read_text())
output = root / "dist" / f"iina-ytdlp-{manifest['version']}-unsigned.xpi"
output.parent.mkdir(exist_ok=True)
with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as archive:
    for source in sorted(extension.rglob("*")):
        if source.is_file() and source.name != ".DS_Store":
            info = zipfile.ZipInfo(source.relative_to(extension).as_posix(), (2026, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            archive.writestr(info, source.read_bytes())
print(output)
