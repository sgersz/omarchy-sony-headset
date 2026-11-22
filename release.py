#!/usr/bin/env python3
"""Build a reproducible source ZIP from an explicit, privacy-reviewed file list."""
import hashlib
import json
from pathlib import Path
import zipfile
from install import FILES

root = Path(__file__).resolve().parent
version = json.loads((root / "manifest.json").read_text())["version"]
name = f"omarchy-sony-headset-{version}"
files = list(FILES) + ["install.py", "release.py", ".gitignore", "QA.md"]
files += [str(path.relative_to(root)) for path in sorted((root / "tests").iterdir()) if path.is_file() and path.suffix in {".py", ".cjs", ".in"}]
files += [f"screenshots/{name}.png" for name in ["noise", "equalizer", "features"]]
destination = root / "dist"
destination.mkdir(exist_ok=True)
archive = destination / (name + ".zip")
with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED) as output:
    for relative in sorted(set(files)):
        source = root / relative
        if not source.is_file() or source.is_symlink():
            raise SystemExit(f"Missing or unexpected release file: {relative}")
        info = zipfile.ZipInfo(name + "/" + relative, date_time=(1980, 1, 1, 0, 0, 0))
        info.compress_type = zipfile.ZIP_DEFLATED
        info.external_attr = 0o100644 << 16
        output.writestr(info, source.read_bytes())
digest = hashlib.sha256(archive.read_bytes()).hexdigest()
checksum = archive.with_suffix(".zip.sha256")
checksum.write_text(f"{digest}  {archive.name}\n")
print(archive)
print(checksum)
