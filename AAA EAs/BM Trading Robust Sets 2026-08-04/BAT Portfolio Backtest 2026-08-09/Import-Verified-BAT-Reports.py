from __future__ import annotations

import shutil
from pathlib import Path


ROOT = Path(__file__).resolve().parent
PACKAGE = ROOT.parent
DESTINATION = PACKAGE / "_Backtests" / "MT5-Isolated-20260805" / "reports" / "bat-portfolio-20260809"
RETEST = PACKAGE / "Retest All Bots 2026-08-07" / "MT5 Reports"
ORB = PACKAGE / "ORB Volume Data EA" / "Volume Profile Reports"

MAP = {
    "01-lta-volume-profile": (RETEST, "20-lta-volume-profile"),
    "02-orb-volume-profile": (ORB, "final-xau-control"),
    "03-atr-candle-breakout": (RETEST, "14-atr-candle-breakout"),
    "04-aaa-final-asia-breakout": (RETEST, "02-aaa-final-asia-breakout"),
    "05-aaa-final-dmc": (RETEST, "03-aaa-final-dmc-xau"),
    "06-go-long": (RETEST, "15-go-long"),
    "07-aaa-final-ema3": (RETEST, "01-aaa-final-ema3"),
    "08-aaa-final-xau-weakness": (RETEST, "11-aaa-final-xau-weakness"),
    "09-ninja-turtle-scalper": (RETEST, "16-ninja-turtle-scalper"),
    "10-nasdaq-overnight": (RETEST, "21-nasdaq-overnight-negative-day"),
    "11-turnaround-tuesday": (RETEST, "19-turnaround-tuesday"),
    "12-aaa-final-us100-weakness": (RETEST, "07-aaa-final-us100-weakness"),
    "13-aaa-final-news-pulse": (RETEST, "08-aaa-final-news-pulse"),
}


def main() -> None:
    DESTINATION.mkdir(parents=True, exist_ok=True)
    copied_reports = 0
    for target_stem, (source_dir, source_stem) in MAP.items():
        source_report = source_dir / f"{source_stem}.htm"
        if not source_report.exists():
            raise FileNotFoundError(source_report)
        for source in source_dir.glob(f"{source_stem}*"):
            if not source.is_file():
                continue
            suffix = source.name[len(source_stem):]
            shutil.copy2(source, DESTINATION / f"{target_stem}{suffix}")
        copied_reports += 1
    print(f"Imported {copied_reports} input-verified native MT5 reports.")


if __name__ == "__main__":
    main()
