from __future__ import annotations

import argparse
from datetime import date, datetime, timedelta
import json
import time
from pathlib import Path
from typing import Any

from .config import REPORTS_DIR
from .news_effect import openai_news_bias, upcoming_news_events
from .strategy_suite import backtest_strategy_suite, suite_bot_configs


WORKER_DIR = REPORTS_DIR / "strategy_workers"
WORKER_DIR.mkdir(parents=True, exist_ok=True)


def heartbeat_path(bot_id: str) -> Path:
    return WORKER_DIR / f"{bot_id}_heartbeat.json"


def events_path(bot_id: str) -> Path:
    return WORKER_DIR / f"{bot_id}_events.jsonl"


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")


def append_jsonl(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, default=str) + "\n")


def run_worker(bot_id: str, interval_seconds: int) -> None:
    configs = suite_bot_configs()
    if bot_id not in configs:
        raise SystemExit(f"Unknown suite bot: {bot_id}")
    config = configs[bot_id]
    print(f"{config.name} worker started.")
    print(f"Symbols: {', '.join(config.symbols)} | timeframe={config.timeframe} | RR=1:{config.rr:g}")
    print("This worker scans and reports. Live order placement for suite bots is intentionally off by default.")
    print("Press Ctrl+C to stop.")
    while True:
        now = datetime.now()
        write_json(
            heartbeat_path(bot_id),
            {
                "bot_id": bot_id,
                "name": config.name,
                "status": "scanning",
                "updated_at": now.isoformat(timespec="seconds"),
                "symbols": config.symbols,
                "timeframe": config.timeframe,
            },
        )
        try:
            if bot_id == "news":
                news_events = upcoming_news_events()
                for event in news_events[:5]:
                    bias = openai_news_bias(event, tuple(config.symbols))
                    append_jsonl(
                        events_path(bot_id),
                        {
                            "time": datetime.now().isoformat(timespec="seconds"),
                            "event": "news_bias",
                            "news": event,
                            "bias": bias,
                        },
                    )
                    print(
                        f"[{datetime.now().isoformat(timespec='seconds')}] "
                        f"news bias {event.get('title') or event.get('event') or event.get('time')}: "
                        f"{bias.get('bias')} confidence={bias.get('confidence')}"
                    )
            report = backtest_strategy_suite(
                start=date.today() - timedelta(days=3),
                end=date.today(),
                starting_balance=300.0,
                risk_pct=config.risk_pct,
                bot_ids=(bot_id,),
            )
            summary = report.get("summary") or {}
            append_jsonl(
                events_path(bot_id),
                {
                    "time": datetime.now().isoformat(timespec="seconds"),
                    "event": "scan_complete",
                    "summary": summary,
                    "report": report.get("path"),
                },
            )
            print(
                f"[{datetime.now().isoformat(timespec='seconds')}] "
                f"{bot_id}: trades={summary.get('trades', 0)} "
                f"win_rate={summary.get('win_rate', 0)}% "
                f"net_r={summary.get('net_r', 0)}"
            )
        except Exception as exc:
            append_jsonl(
                events_path(bot_id),
                {
                    "time": datetime.now().isoformat(timespec="seconds"),
                    "event": "scan_error",
                    "error": str(exc),
                },
            )
            print(f"[{datetime.now().isoformat(timespec='seconds')}] {bot_id}: error={exc}")
        time.sleep(max(15, int(interval_seconds)))


def main() -> None:
    parser = argparse.ArgumentParser(description="Experimental strategy-suite bot worker.")
    parser.add_argument("--bot", required=True, help="grid, trend, mean_reversion, dca, news, arbitrage")
    parser.add_argument("--interval", type=int, default=300)
    args = parser.parse_args()
    run_worker(args.bot.strip().lower(), args.interval)


if __name__ == "__main__":
    main()
