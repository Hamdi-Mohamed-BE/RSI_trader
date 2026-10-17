"""Publish large pending research data losslessly; never access MT5 or delete originals."""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
import gzip
import hashlib
import json
import subprocess

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
THRESHOLD = 5 * 1024 * 1024
CHUNK = 1024 * 1024


def digest_stream(stream):
    digest = hashlib.sha256()
    size = 0
    for block in iter(lambda: stream.read(CHUNK), b""):
        digest.update(block)
        size += len(block)
    return digest.hexdigest(), size


def compress_one(relative):
    source = ROOT / relative
    archive = source.with_name(source.name + ".gz")
    before = source.stat()
    with source.open("rb") as stream:
        original_hash, original_size = digest_stream(stream)
    if archive.exists():
        with gzip.open(archive, "rb") as stream:
            restored_hash, restored_size = digest_stream(stream)
        if (restored_hash, restored_size) != (original_hash, original_size):
            raise ValueError(f"Refusing to replace a different existing archive: {relative}")
    else:
        temporary = archive.with_name(archive.name + ".publishing.tmp")
        with source.open("rb") as stream, temporary.open("xb") as output:
            with gzip.GzipFile(filename="", mode="wb", fileobj=output, mtime=0, compresslevel=6) as zipped:
                for block in iter(lambda: stream.read(CHUNK), b""):
                    zipped.write(block)
        with gzip.open(temporary, "rb") as stream:
            restored_hash, restored_size = digest_stream(stream)
        if (restored_hash, restored_size) != (original_hash, original_size):
            raise ValueError(f"Lossless round-trip check failed: {relative}")
        temporary.rename(archive)
    after = source.stat()
    if (before.st_size, before.st_mtime_ns) != (after.st_size, after.st_mtime_ns):
        raise ValueError(f"Original changed during publication: {relative}")
    with archive.open("rb") as stream:
        compressed_hash, compressed_size = digest_stream(stream)
    return dict(original_path=relative, original_bytes=original_size,
                original_sha256=original_hash,
                compressed_path=archive.relative_to(ROOT).as_posix(),
                compressed_bytes=compressed_size, compressed_sha256=compressed_hash,
                round_trip_verified=True)


def main():
    raw = subprocess.check_output(
        ["git", "ls-files", "--others", "--exclude-standard", "-z"], cwd=ROOT
    ).decode("utf-8")
    selected = sorted(name for name in raw.split("\0") if name
                      and Path(name).suffix.lower() in {".json", ".csv", ".tsv"}
                      and (ROOT / name).stat().st_size >= THRESHOLD)
    if not selected:
        print("No new large research data requires compression.", flush=True)
        return
    print(f"Preparing {len(selected)} lossless research archives; originals remain unchanged.", flush=True)
    rows = []
    with ThreadPoolExecutor(max_workers=4) as pool:
        tasks = [pool.submit(compress_one, name) for name in selected]
        for future in as_completed(tasks):
            rows.append(future.result())
            if len(rows) % 10 == 0 or len(rows) == len(tasks):
                print(f"Verified {len(rows)}/{len(tasks)} archives", flush=True)
    rows.sort(key=lambda row: row["original_path"])
    manifest = dict(date="2026-10-17", format="lossless gzip", originals_preserved=True,
                    files=rows)
    (HERE / "Compression manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
    )
    # Apply exact-path Git exclusions separately after reviewing this manifest.
    # The program itself never changes source files or repository configuration.
    print(json.dumps(dict(files=len(rows), original_bytes=sum(row["original_bytes"] for row in rows),
                          compressed_bytes=sum(row["compressed_bytes"] for row in rows),
                          all_round_trips_verified=True)), flush=True)


if __name__ == "__main__":
    main()
