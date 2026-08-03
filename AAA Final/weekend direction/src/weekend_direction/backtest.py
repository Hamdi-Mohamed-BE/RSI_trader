from __future__ import annotations

from datetime import datetime, timezone
import json
import subprocess
import sys

from .config import Config, ROOT


def run(refresh: bool = True) -> dict:
    config = Config.load()
    if refresh:
        subprocess.run([sys.executable, str(config.ai_news_root / "backtest_predicted_weekend_hold.py")], cwd=config.ai_news_root, check=True)
    payload = json.loads((config.ai_news_root / "predicted_weekend_hold_backtest.json").read_text(encoding="utf-8"))
    rejected = payload["selected"]
    provisional = payload["best_observed_after_rr_comparison"]
    report = {
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "model_validated": False,
        "default_live_action": "NO_TRADE",
        "selected_rejected_model": {"config": rejected["config"], "development": rejected["development"], "holdout": rejected["holdout"], "full": rejected["full"]},
        "provisional_momentum": {"config": provisional["config"], "development": provisional["development"], "holdout": provisional["holdout"], "full": provisional["full"], "validated": False},
        "caveat": "The momentum result was selected after comparing RR families and is not live-authorized.",
    }
    reports = ROOT / "reports"
    reports.mkdir(exist_ok=True)
    (reports / "WEEKEND_DIRECTION_BACKTEST.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    def row(label: str, stats: dict) -> str:
        return f"| {label} | {stats['trades']} | {stats['win_rate_pct']:.2f}% | {stats['profit_factor']:.3f} | {stats['net_r']:+.2f}R | {stats['max_drawdown_r']:.2f}R |"
    lines = [
        "# XAUUSD Friday Weekend-Direction Backtest", "", "## Rejected selected ML model", "", "| Sample | Trades | Win rate | PF | Net | Max DD |", "|---|---:|---:|---:|---:|---:|",
        row("Development", rejected["development"]), row("Untouched holdout", rejected["holdout"]), row("Full", rejected["full"]),
        "", "## Provisional momentum research", "", "This mode follows strong Friday 24-hour momentum four minutes before the inferred close and exits at the first weekly reopen tick.", "",
        "| Sample | Trades | Win rate | PF | Net | Max DD |", "|---|---:|---:|---:|---:|---:|",
        row("Development", provisional["development"]), row("Holdout", provisional["holdout"]), row("Full", provisional["full"]),
        "", "**Deployment verdict: NO_TRADE.** The ML model failed its untouched holdout. The momentum result is selection-biased and demo-only when explicitly enabled.", "",
        "Gap losses are executed at unfavorable reopen prices. Historical M1 simulation is not a guarantee.",
    ]
    (reports / "WEEKEND_DIRECTION_BACKTEST.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return report
