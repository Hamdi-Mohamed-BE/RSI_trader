"""Restore published research originals after a clone; verify hashes and never overwrite."""
from pathlib import Path
import argparse
import gzip
import hashlib
import json
import shutil

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]


def sha(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def safe_path(relative):
    path = (ROOT / relative).resolve()
    if not path.is_relative_to(ROOT.resolve()):
        raise ValueError("Manifest path escapes the repository")
    return path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--restore", action="store_true", help="Create missing originals; otherwise check archives only")
    args = parser.parse_args()
    manifest = json.loads((HERE / "Compression manifest.json").read_text(encoding="utf-8"))
    for row in manifest["files"]:
        original, archive = safe_path(row["original_path"]), safe_path(row["compressed_path"])
        if sha(archive) != row["compressed_sha256"]:
            raise ValueError(f"Changed archive: {row['compressed_path']}")
        with gzip.open(archive, "rb") as stream:
            restored = hashlib.file_digest(stream, "sha256").hexdigest()
        if restored != row["original_sha256"]:
            raise ValueError(f"Archive round-trip mismatch: {row['compressed_path']}")
        if original.exists():
            if sha(original) != row["original_sha256"]:
                raise ValueError(f"Refusing to replace a different original: {row['original_path']}")
        elif args.restore:
            with gzip.open(archive, "rb") as source, original.open("xb") as target:
                shutil.copyfileobj(source, target)
            if sha(original) != row["original_sha256"]:
                raise ValueError(f"Restore verification failed: {row['original_path']}")
    print(f"PASS: {len(manifest['files'])} lossless archives verified. No existing original overwritten.")


if __name__ == "__main__":
    main()
