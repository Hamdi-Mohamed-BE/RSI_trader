from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
import sys

from .config import Config, ROOT


def run(refresh: bool = True) -> dict:
    config = Config.load()
    source = config.ai_news_root / "news_pending_2y_results.json"
    if refresh:
        subprocess.run([sys.executable, str(config.ai_news_root / "backtest_news_pending.py")], cwd=config.ai_news_root, check=True)
    payload = json.loads(source.read_text(encoding="utf-8"))
    gold = payload["symbols"]["XAUUSD"]
    report = {
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "validation": "chronological development plus untouched six-month holdout",
        "selected_config": gold["selected_config"],
        "allowed_events": gold["allowed_events"],
        "development": gold["development"]["performance"],
        "holdout": gold["holdout"]["performance"],
        "full": gold["full"]["performance"],
        "unfiltered_full": gold["unfiltered_full"]["performance"],
        "validated": bool(gold["holdout"]["performance"]["trades"] >= 4 and gold["holdout"]["performance"]["profit_factor"] >= 1.3),
        "caveat": "Provisional small-sample winner; model outputs remain prediction-only.",
    }
    reports = ROOT / "reports"
    reports.mkdir(exist_ok=True)
    (reports / "NEWS_PULSE_BACKTEST.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    def row(label: str, stats: dict) -> str:
        return f"| {label} | {stats['trades']} | {stats['win_rate_pct']:.2f}% | {stats['profit_factor']:.2f} | {stats['net_r']:+.2f}R | {stats['max_drawdown_pct']:.2f}% |"
    lines = [
        "# XAUUSD News Pulse Backtest", "", "PPI-only OCO, 5R, one re-entry; 1% compounded risk.", "",
        "| Sample | Trades | Win rate | PF | Net | Max DD |", "|---|---:|---:|---:|---:|---:|",
        row("Development", report["development"]), row("Untouched holdout", report["holdout"]), row("Full", report["full"]), row("Unfiltered stress", report["unfiltered_full"]),
        "", "**Status:** provisional/selection-biased; small holdout. Live execution is disabled by default.", "",
        "Historical simulation includes bid/ask triggers, spread, pessimistic M1 ordering, and compounding. It is not a guarantee.",
    ]
    (reports / "NEWS_PULSE_BACKTEST.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return report
