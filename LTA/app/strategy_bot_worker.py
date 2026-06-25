from __future__ import annotations

import argparse
from datetime import date, datetime, timedelta
import json
import os
import time
from pathlib import Path
from typing import Any

from .config import REPORTS_DIR
from .news_effect import openai_news_bias, upcoming_news_events
from .news_trader import NewsStraddleTrader
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


def _int_env(name: str, default: int) -> int:
    try:
        return int(float(os.getenv(name, str(default)) or default))
    except ValueError:
        return default


def run_worker(bot_id: str, interval_seconds: int) -> None:
    configs = suite_bot_configs()
    if bot_id not in configs:
        raise SystemExit(f"Unknown suite bot: {bot_id}")
    config = configs[bot_id]
    news_trader = NewsStraddleTrader(config.symbols) if bot_id == "news" else None
    report_interval_seconds = max(60, _int_env("NEWS_REPORT_INTERVAL_SECONDS", 300)) if bot_id == "news" else 0
    last_report_at: datetime | None = None
    print(f"{config.name} worker started.")
    print(f"Symbols: {', '.join(config.symbols)} | timeframe={config.timeframe} | RR=1:{config.rr:g}")
    if news_trader:
        print(
            "News pending straddle: "
            f"live={news_trader.live_trading}; place_pending={news_trader.place_pending}; "
            f"pre-place={news_trader.preplace_seconds}s before news; "
            f"window={news_trader.preplace_window_seconds}s; magic={news_trader.magic}."
        )
    else:
        print("This worker scans and reports. Live order placement for this suite bot is off unless its code enables it.")
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
                trade_summary = news_trader.process() if news_trader else {}
                append_jsonl(
                    events_path(bot_id),
                    {
                        "time": datetime.now().isoformat(timespec="seconds"),
                        "event": "news_straddle_cycle",
                        "summary": trade_summary,
                    },
                )
                compact_messages = trade_summary.get("messages", [])[:4] if isinstance(trade_summary, dict) else []
                print(
                    f"[{datetime.now().isoformat(timespec='seconds')}] "
                    f"news straddle: events={trade_summary.get('events_seen', 0)} "
                    f"window={trade_summary.get('events_in_window', 0)} "
                    f"prepared={trade_summary.get('prepared', 0)} "
                    f"placed={trade_summary.get('placed', 0)} "
                    f"blocked={trade_summary.get('blocked', 0)}"
                )
                for message in compact_messages:
                    print(f"  {message}")
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
            should_report = bot_id != "news" or last_report_at is None or (datetime.now() - last_report_at).total_seconds() >= report_interval_seconds
            if should_report:
                last_report_at = datetime.now()
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
        min_sleep = 5 if bot_id == "news" else 15
        time.sleep(max(min_sleep, int(interval_seconds)))


def main() -> None:
    parser = argparse.ArgumentParser(description="Experimental strategy-suite bot worker.")
    parser.add_argument("--bot", required=True, help="grid, trend, mean_reversion, dca, news, arbitrage")
    parser.add_argument("--interval", type=int, default=300)
    args = parser.parse_args()
    bot_id = args.bot.strip().lower()
    interval = args.interval
    if bot_id == "news" and interval == 300:
        interval = _int_env("NEWS_SCAN_INTERVAL_SECONDS", 10)
    run_worker(bot_id, interval)


if __name__ == "__main__":
    main()
