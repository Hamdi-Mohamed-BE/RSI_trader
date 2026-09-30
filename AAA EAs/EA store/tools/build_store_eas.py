"""Build the license-gated Calyx store EX5 files into data/store-builds/.

Reads the original EA sources/SETs (never modifies them), writes wrappers and
copied include graphs, compiles them with the isolated MetaEditor
(0 errors, 0 warnings required) and writes data/store-builds/manifest.json.

    uv run python tools/build_store_eas.py                 # all builds
    uv run python tools/build_store_eas.py --source-only   # wrappers only, no compile
    uv run python tools/build_store_eas.py --only orb-volume-data-ea
    uv run python tools/build_store_eas.py --activation-url https://calyx.duckdns.org/api/license/check

CALYX_LICENSE_SECRET (environment or .env) must be the same value the website
uses, because each build embeds a secret derived from it. MetaEditor compiles
only; this never starts terminal64.exe or the Strategy Tester.
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ.setdefault("EA_STORE_DISABLE_MT5", "1")

from app.store import builds  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--source-only", action="store_true", help="write wrappers without compiling")
    parser.add_argument("--only", action="append", default=None, help="build family id (repeatable)")
    parser.add_argument("--activation-url", default=None)
    args = parser.parse_args()
    manifest = builds.build_all(compile_eas=not args.source_only, only=set(args.only) if args.only else None,
                                activation_url=args.activation_url)
    current = [b for b in manifest["builds"].values() if b.get("current")]
    compiled = [b for b in current if b.get("compiled")]
    print(f"{len(current)} current builds, {len(compiled)} compiled, {len(manifest['products'])} products, "
          f"{len(manifest['failures'])} failures")
    for failure in manifest["failures"]:
        print("FAILURE", failure["build"], failure["error"])
        for line in failure.get("details", []):
            print("   ", line)
    return 1 if manifest["failures"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
