from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from news_pending_strategy import load_events


ROOT = Path(__file__).resolve().parent
START = datetime(2021, 8, 1, tzinfo=timezone.utc)
END = datetime(2026, 8, 1, tzinfo=timezone.utc)
EVENT_NAMES = {"NFP", "CPI", "PPI", "GDP", "FOMC"}
OUTPUT = ROOT / "data" / "xau-news-ticks-5y" / "manifest.json"


def main() -> None:
    rows = [
        {
            "event": event["event"],
            "release_utc": event["released"].isoformat(),
        }
        for event in load_events(START, END)
        if event["event"] in EVENT_NAMES
    ]
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(rows, indent=2), encoding="utf-8")
    print(f"Wrote {len(rows)} events to {OUTPUT}")


if __name__ == "__main__":
    main()
