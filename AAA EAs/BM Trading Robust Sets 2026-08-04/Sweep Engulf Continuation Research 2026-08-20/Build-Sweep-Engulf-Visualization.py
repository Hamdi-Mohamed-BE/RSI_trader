from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent
DATA_PATH = ROOT / "sweep-engulf-live-results.json"
TEMPLATE_PATH = ROOT / "sweep-engulf-visualization-template.html"
OUTPUT = Path(r"C:\Users\hama101\.codex\visualizations\2026\08\04\019fcad5-6b3d-7de2-b1b2-01580f22a7c0\sweep-engulf-mt5-results.html")


def main() -> None:
    payload = json.loads(DATA_PATH.read_text(encoding="utf-8"))
    compact = json.dumps(payload, separators=(",", ":"))
    html = TEMPLATE_PATH.read_text(encoding="utf-8").replace("__PAYLOAD__", compact)
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(html, encoding="utf-8")
    print(OUTPUT)


if __name__ == "__main__":
    main()
