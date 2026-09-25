"""Losslessly gzip bulky MT5 tester artifacts inside research folders before committing.

Compresses `journal.txt` and `*.htm` / `*.html` tester reports to `<name>.gz` (level 9). Every file is
verified by decompressing it and comparing SHA-256 with the original before the original is removed.
Each research folder gets `COMPRESSED-ARTIFACTS.json` recording path, original SHA-256, original and
compressed sizes, so native-report fingerprints stay auditable.

Never touches the EA Store (the website reads its source-run reports uncompressed) or already-tracked
Git files. Restore any file with:  python -c "import gzip,shutil,sys; shutil.copyfileobj(gzip.open(sys.argv[1]), open(sys.argv[1][:-3],'wb'))" FILE.gz
or `gzip -dk FILE.gz`.

Usage: python compress_research_artifacts.py "<research folder>" [more folders...] [--dry-run]
"""
from __future__ import annotations

import gzip
import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

PATTERNS = ("journal.txt", "*.htm", "*.html")
MANIFEST = "COMPRESSED-ARTIFACTS.json"


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def tracked(path: Path) -> bool:
    """True when the file is already committed (never rewrite committed evidence)."""
    r = subprocess.run(["git", "cat-file", "-e", f"HEAD:./{path.name}"], cwd=path.parent,
                       capture_output=True, text=True)
    return r.returncode == 0


def compress_folder(folder: Path, dry_run: bool) -> tuple[int, int, int]:
    if "EA store" in folder.resolve().parts:
        raise SystemExit(f"Refusing EA Store path (website reads these raw): {folder}")
    manifest_path = folder / MANIFEST
    manifest = json.loads(manifest_path.read_text(encoding="utf-8")) if manifest_path.exists() else {
        "purpose": "Lossless gzip of MT5 tester journals/reports; sha256 is of the ORIGINAL uncompressed file.",
        "files": {}}
    n = before = after = 0
    for pattern in PATTERNS:
        for src in sorted(folder.rglob(pattern)):
            if not src.is_file() or tracked(src):
                continue
            raw = src.read_bytes()
            packed = gzip.compress(raw, compresslevel=9, mtime=0)
            if gzip.decompress(packed) != raw:
                raise SystemExit(f"Verification failed: {src}")
            rel = src.relative_to(folder).as_posix()
            n, before, after = n + 1, before + len(raw), after + len(packed)
            if dry_run:
                continue
            dst = src.with_name(src.name + ".gz")
            dst.write_bytes(packed)
            if sha256(gzip.decompress(dst.read_bytes())) != sha256(raw):
                raise SystemExit(f"Written file does not verify: {dst}")
            manifest["files"][rel] = {"sha256": sha256(raw), "bytes": len(raw), "gz_bytes": len(packed)}
            src.unlink()
    if n and not dry_run:
        manifest["updated_utc"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
        manifest_path.write_text(json.dumps(manifest, indent=1, sort_keys=True), encoding="utf-8")
    return n, before, after


def main() -> None:
    args = [a for a in sys.argv[1:] if a != "--dry-run"]
    dry = "--dry-run" in sys.argv
    if not args:
        raise SystemExit(__doc__)
    total = [0, 0, 0]
    for a in args:
        n, b, c = compress_folder(Path(a), dry)
        total = [total[0] + n, total[1] + b, total[2] + c]
        print(f"{'DRY ' if dry else ''}{n:4d} files {b / 1e6:8.1f} MB -> {c / 1e6:7.1f} MB  {Path(a).name}")
    print(f"TOTAL {total[0]} files {total[1] / 1e6:.1f} MB -> {total[2] / 1e6:.1f} MB")


if __name__ == "__main__":
    main()
