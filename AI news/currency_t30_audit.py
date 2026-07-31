from __future__ import annotations

import csv
import json
import math
import re
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

from news_pending_strategy import ROOT, load_day


START = datetime(2026, 5, 31, tzinfo=timezone.utc)
END = datetime(2026, 7, 31, tzinfo=timezone.utc)
PREDICTIONS_PATH = ROOT / "news_v3_results.csv"
OUTPUT_CSV = ROOT / "currency_t30_2m_audit.csv"
OUTPUT_JSON = ROOT / "currency_t30_2m_audit.json"
OUTPUT_MD = ROOT / "CURRENCY_T30_2M_RESULTS.md"

PAIRS = {
    "AUD": {"symbol": "AUDUSD", "usd_position": "quote", "pip_size": 0.0001},
    "CAD": {"symbol": "USDCAD", "usd_position": "base", "pip_size": 0.0001},
    "CHF": {"symbol": "USDCHF", "usd_position": "base", "pip_size": 0.0001},
    "CNY": {"symbol": "USDCNH", "usd_position": "base", "pip_size": 0.0001},
    "EUR": {"symbol": "EURUSD", "usd_position": "quote", "pip_size": 0.0001},
    "GBP": {"symbol": "GBPUSD", "usd_position": "quote", "pip_size": 0.0001},
    "JPY": {"symbol": "USDJPY", "usd_position": "base", "pip_size": 0.01},
    "NZD": {"symbol": "NZDUSD", "usd_position": "quote", "pip_size": 0.0001},
}


def load_t30_predictions() -> list[dict]:
    rows = []
    with PREDICTIONS_PATH.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            released = datetime.fromisoformat(row["release_utc"]).astimezone(timezone.utc)
            if not START <= released < END:
                continue
            match = re.search(r"\b(BUY|SELL)\b", row["display_30m"].upper())
            if not match:
                continue
            gold_side = match.group(1)
            rows.append(
                {
                    "release_utc": released,
                    "event": row["event"],
                    "gold_side": gold_side,
                    "usd_side": "SELL" if gold_side == "BUY" else "BUY",
                }
            )
    return sorted(rows, key=lambda row: row["release_utc"])


def pair_prediction(usd_side: str, usd_position: str) -> str:
    if usd_position == "base":
        return usd_side
    return "SELL" if usd_side == "BUY" else "BUY"


def usd_direction(pair_side: str, usd_position: str) -> str:
    if pair_side == "UNCERTAIN":
        return "UNCERTAIN"
    if usd_position == "base":
        return pair_side
    return "SELL" if pair_side == "BUY" else "BUY"


def _atr(
    bid: dict[int, dict[str, float]],
    release_stamp: int,
) -> float | None:
    bars = []
    for stamp in range(release_stamp - 31 * 60_000, release_stamp - 60_000, 60_000):
        if stamp in bid:
            bars.append(bid[stamp])
    if len(bars) < 25:
        return None
    ranges = []
    for index in range(1, len(bars)):
        previous = bars[index - 1]["close"]
        current = bars[index]
        ranges.append(
            max(
                current["high"] - current["low"],
                abs(current["high"] - previous),
                abs(current["low"] - previous),
            )
        )
    return sum(ranges) / len(ranges) if ranges else None


def evaluate_pair(currency: str, prediction: dict) -> dict:
    config = PAIRS[currency]
    symbol = config["symbol"].lower()
    released = prediction["release_utc"]
    day = released.date().isoformat()
    bid = load_day(symbol, day, "bid")
    ask = load_day(symbol, day, "ask")
    if not bid or not ask:
        return {
            "date": day,
            "release_utc": released.isoformat(),
            "event": prediction["event"],
            "currency": currency,
            "symbol": config["symbol"],
            "predicted_usd": prediction["usd_side"],
            "predicted_pair": pair_prediction(
                prediction["usd_side"],
                config["usd_position"],
            ),
            "status": "MISSING_BID_ASK",
        }

    release_stamp = int(released.timestamp() * 1000)
    before_stamp = release_stamp - 60_000
    after_stamp = release_stamp + 15 * 60_000
    if before_stamp not in bid or before_stamp not in ask or after_stamp not in bid or after_stamp not in ask:
        return {
            "date": day,
            "release_utc": released.isoformat(),
            "event": prediction["event"],
            "currency": currency,
            "symbol": config["symbol"],
            "predicted_usd": prediction["usd_side"],
            "predicted_pair": pair_prediction(
                prediction["usd_side"],
                config["usd_position"],
            ),
            "status": "MISSING_REACTION_WINDOW",
        }

    before_bid = bid[before_stamp]
    before_ask = ask[before_stamp]
    after_bid = bid[after_stamp]
    after_ask = ask[after_stamp]
    before_mid = (before_bid["close"] + before_ask["close"]) / 2
    after_mid = (after_bid["close"] + after_ask["close"]) / 2
    move = after_mid - before_mid
    spread = before_ask["close"] - before_bid["close"]
    atr = _atr(bid, release_stamp)
    if atr is None or not math.isfinite(atr):
        actual_pair = "UNCERTAIN"
        threshold = None
    else:
        threshold = max(2.0 * spread, 0.15 * atr)
        if move > threshold:
            actual_pair = "BUY"
        elif move < -threshold:
            actual_pair = "SELL"
        else:
            actual_pair = "UNCERTAIN"

    predicted_pair = pair_prediction(prediction["usd_side"], config["usd_position"])
    if predicted_pair == "BUY":
        executable_pips = (
            after_bid["close"] - before_ask["close"]
        ) / config["pip_size"]
    else:
        executable_pips = (
            before_bid["close"] - after_ask["close"]
        ) / config["pip_size"]
    actual_usd = usd_direction(actual_pair, config["usd_position"])
    return {
        "date": day,
        "release_utc": released.isoformat(),
        "event": prediction["event"],
        "currency": currency,
        "symbol": config["symbol"],
        "predicted_usd": prediction["usd_side"],
        "predicted_pair": predicted_pair,
        "actual_pair": actual_pair,
        "actual_usd": actual_usd,
        "correct": actual_pair == predicted_pair if actual_pair != "UNCERTAIN" else None,
        "move_pips": round(move / config["pip_size"], 2),
        "executable_pips": round(executable_pips, 2),
        "spread_pips": round(spread / config["pip_size"], 2),
        "threshold_pips": None
        if threshold is None
        else round(threshold / config["pip_size"], 2),
        "status": "OK",
    }


def summarize(rows: list[dict]) -> dict:
    decided = [row for row in rows if row.get("correct") is not None]
    correct = sum(bool(row["correct"]) for row in decided)
    executable = [float(row["executable_pips"]) for row in rows if row["status"] == "OK"]
    return {
        "observations": len(rows),
        "decided": len(decided),
        "uncertain": sum(
            row.get("actual_pair") == "UNCERTAIN"
            for row in rows
            if row["status"] == "OK"
        ),
        "missing": sum(row["status"] != "OK" for row in rows),
        "correct": correct,
        "win_rate_pct": 100.0 * correct / len(decided) if decided else 0.0,
        "net_executable_pips": round(sum(executable), 2),
        "positive_executable_events": sum(value > 0 for value in executable),
    }


def run() -> dict:
    predictions = load_t30_predictions()
    rows = [
        evaluate_pair(currency, prediction)
        for prediction in predictions
        for currency in PAIRS
    ]
    by_currency = {
        currency: summarize([row for row in rows if row["currency"] == currency])
        for currency in PAIRS
    }
    by_event = {
        event: summarize([row for row in rows if row["event"] == event])
        for event in ("NFP", "CPI", "PPI", "FOMC")
    }

    usd_rows = []
    grouped: dict[str, list[dict]] = defaultdict(list)
    for row in rows:
        if row["status"] == "OK" and row.get("actual_usd") != "UNCERTAIN":
            grouped[row["release_utc"]].append(row)
    for prediction in predictions:
        release = prediction["release_utc"].isoformat()
        votes = Counter(row["actual_usd"] for row in grouped.get(release, []))
        if votes["BUY"] == votes["SELL"]:
            actual_usd = "UNCERTAIN"
            correct = None
        else:
            actual_usd = "BUY" if votes["BUY"] > votes["SELL"] else "SELL"
            correct = actual_usd == prediction["usd_side"]
        usd_rows.append(
            {
                "date": prediction["release_utc"].date().isoformat(),
                "event": prediction["event"],
                "predicted_usd": prediction["usd_side"],
                "actual_usd_majority": actual_usd,
                "correct": correct,
                "votes_buy": votes["BUY"],
                "votes_sell": votes["SELL"],
            }
        )
    usd_summary = summarize(
        [
            {
                "status": "OK",
                "correct": row["correct"],
                "actual_pair": row["actual_usd_majority"],
                "executable_pips": 0.0,
            }
            for row in usd_rows
        ]
    )

    payload = {
        "period": {"start": START.isoformat(), "end": END.isoformat()},
        "method": {
            "reaction_horizon_minutes": 15,
            "actual_threshold": "max(2x pre-release spread, 0.15x pre-release 30m ATR)",
            "execution": "Predicted BUY enters ask/exits bid; SELL enters bid/exits ask.",
            "cny_proxy": "USDCNH",
        },
        "predictions": [
            {
                **prediction,
                "release_utc": prediction["release_utc"].isoformat(),
            }
            for prediction in predictions
        ],
        "by_currency": by_currency,
        "by_event": by_event,
        "usd_majority": {"summary": usd_summary, "events": usd_rows},
        "rows": rows,
    }
    OUTPUT_JSON.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    with OUTPUT_CSV.open("w", newline="", encoding="utf-8") as handle:
        fieldnames = sorted({key for row in rows for key in row})
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    lines = [
        "# T-30 USD Direction Across Currency Pairs",
        "",
        f"Period: {START.date()} through {END.date()}",
        "",
        "| Currency | Pair | Decided | Correct | Win rate | Uncertain | Missing | Executable pips |",
        "|---|---|---:|---:|---:|---:|---:|---:|",
    ]
    for currency, stats in by_currency.items():
        lines.append(
            f"| {currency} | {PAIRS[currency]['symbol']} | {stats['decided']} | "
            f"{stats['correct']} | {stats['win_rate_pct']:.1f}% | "
            f"{stats['uncertain']} | {stats['missing']} | "
            f"{stats['net_executable_pips']:+.1f} |"
        )
    lines.extend(
        [
            f"| USD | Majority of normalized crosses | {usd_summary['decided']} | "
            f"{usd_summary['correct']} | {usd_summary['win_rate_pct']:.1f}% | "
            f"{usd_summary['uncertain']} | {usd_summary['missing']} | n/a |",
            "",
            "## Per event",
            "",
            "| Event | Decided | Correct | Win rate | Uncertain | Missing | Executable pips |",
            "|---|---:|---:|---:|---:|---:|---:|",
        ]
    )
    for event, stats in by_event.items():
        lines.append(
            f"| {event} | {stats['decided']} | {stats['correct']} | "
            f"{stats['win_rate_pct']:.1f}% | {stats['uncertain']} | "
            f"{stats['missing']} | {stats['net_executable_pips']:+.1f} |"
        )
    lines.extend(
        [
            "",
            "Direction accuracy excludes reactions classified as uncertain. Pips are a diagnostic one-lot-free price measure, not account profit.",
        ]
    )
    OUTPUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return payload


if __name__ == "__main__":
    result = run()
    print(OUTPUT_MD)
    print(json.dumps(result["by_currency"], indent=2))
