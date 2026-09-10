from __future__ import annotations

import csv
import json
import math
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

import joblib
import MetaTrader5 as mt5

from fxmacrodata import FXMacroDataClient
from news_core import ROOT, extract_features, label_reaction
from news_v5 import artifact_prediction


START = datetime(2026, 6, 10, tzinfo=timezone.utc)
END = datetime(2026, 9, 10, tzinfo=timezone.utc)
BASE_REPORT = ROOT / "news_v5_3m_results.json"
MODEL_PATH = ROOT / "models" / "gold_news_v5.joblib"
OUTPUT_JSON = ROOT / "news_v6_fxmacro_3m_results.json"
OUTPUT_CSV = ROOT / "news_v6_fxmacro_3m_results.csv"
OUTPUT_MD = ROOT / "NEWS_V6_FXMACRO_3M_RESULTS.md"
EXTRA_EVENTS = (
    ("CPI", datetime(2026, 8, 12, 12, 30, tzinfo=timezone.utc)),
    ("NFP", datetime(2026, 9, 4, 12, 30, tzinfo=timezone.utc)),
)


def _wilson(wins: int, calls: int) -> list[float]:
    if not calls:
        return [0.0, 0.0]
    z = 1.959963984540054
    p = wins / calls
    denominator = 1 + z * z / calls
    center = (p + z * z / (2 * calls)) / denominator
    margin = z * math.sqrt((p * (1 - p) + z * z / (4 * calls)) / calls) / denominator
    return [round(100 * (center - margin), 2), round(100 * (center + margin), 2)]


def _metrics(rows: list[dict], key: str) -> dict:
    called = [row for row in rows if row.get(key) not in {None, "NO CALL"}]
    wins = sum(row[key] == row["actual"] for row in called)
    return {
        "events": len(rows),
        "calls": len(called),
        "wins": wins,
        "losses": len(called) - wins,
        "accuracy_pct": round(100 * wins / len(called), 2) if called else 0.0,
        "coverage_pct": round(100 * len(called) / len(rows), 2) if rows else 0.0,
        "wilson_95_pct": _wilson(wins, len(called)),
    }


def _discover_gold() -> str:
    symbols = [item.name for item in (mt5.symbols_get() or ())]
    ranked = sorted(
        (name for name in symbols if "XAUUSD" in name.upper().replace(".", "").replace("_", "")),
        key=lambda name: (name.upper() != "XAUUSD", len(name)),
    )
    for name in ranked:
        if mt5.symbol_select(name, True):
            return name
    raise RuntimeError("No XAUUSD broker symbol is available in the connected MT5 terminal.")


def _event_sides(symbol: str, release: datetime) -> tuple[dict, dict, list[dict], list[dict]]:
    info = mt5.symbol_info(symbol)
    if info is None:
        raise RuntimeError(f"MT5 returned no symbol information for {symbol}.")
    day_start = release.replace(hour=0, minute=0, second=0, microsecond=0)
    rates = mt5.copy_rates_range(
        symbol,
        mt5.TIMEFRAME_M1,
        day_start,
        day_start + timedelta(days=1) - timedelta(seconds=1),
    )
    if rates is None or len(rates) < 240:
        raise RuntimeError(f"MT5 M1 history is incomplete for {symbol} on {release.date()}.")
    bid: dict[int, dict] = {}
    ask: dict[int, dict] = {}
    bid_rows = []
    ask_rows = []
    for rate in rates:
        stamp = int(rate["time"]) * 1000
        spread = float(rate["spread"]) * float(info.point)
        bid_row = {
            "timestamp": stamp,
            "open": float(rate["open"]),
            "high": float(rate["high"]),
            "low": float(rate["low"]),
            "close": float(rate["close"]),
            "volume": float(rate["tick_volume"]),
        }
        ask_row = {
            **bid_row,
            **{
                key: bid_row[key] + spread
                for key in ("open", "high", "low", "close")
            },
        }
        bid[stamp] = bid_row
        ask[stamp] = ask_row
        bid_rows.append(bid_row)
        ask_rows.append(ask_row)
    return bid, ask, bid_rows, ask_rows


def _save_event_day(release: datetime, bid_rows: list[dict], ask_rows: list[dict]) -> None:
    directory = ROOT / "data" / "news-event-days"
    directory.mkdir(parents=True, exist_ok=True)
    day = release.date().isoformat()
    for side, rows in (("bid", bid_rows), ("ask", ask_rows)):
        path = directory / f"xauusd-m1-{side}-{day}.json"
        path.write_text(json.dumps(rows, separators=(",", ":")), encoding="utf-8")


def _new_event(
    artifact: dict,
    symbol: str,
    event: str,
    release: datetime,
) -> dict:
    bid, ask, bid_rows, ask_rows = _event_sides(symbol, release)
    _save_event_day(release, bid_rows, ask_rows)
    extracted_30 = extract_features(
        event,
        release,
        bid,
        ask,
        30,
        artifact["history_features"].get(event),
    )
    extracted_15 = extract_features(
        event,
        release,
        bid,
        ask,
        15,
        artifact["history_features"].get(event),
    )
    if extracted_30 is None or extracted_15 is None:
        raise RuntimeError(f"Could not build T-30/T-15 features for {event} {release.date()}.")
    features_30, context_30 = extracted_30
    features_15, context_15 = extracted_15
    decision = artifact_prediction(
        artifact,
        event,
        15,
        features_15,
        features_30,
    )
    reaction = label_reaction(release, bid, ask, float(context_15["atr_30m"]))
    if reaction is None:
        raise RuntimeError(f"Could not label the release minute for {event} {release.date()}.")
    actual = "POSITIVE" if float(reaction["release_move"]) >= 0 else "NEGATIVE"
    return {
        "release_utc": release.isoformat(),
        "event": event,
        "v5_prediction": decision["prediction"],
        "v5_bias": decision["bias"],
        "v5_confidence_pct": round(100 * float(decision["confidence"]), 2),
        "v5_strategy": decision["strategy"],
        "v5_failed_gates": decision["failed_gates"],
        "actual": actual,
        "release_move_usd": round(float(reaction["release_move"]), 4),
        "market_context": context_15,
        "t30_market_context": context_30,
        "point_in_time_source": "connected MT5 historical M1 bars",
    }


def _base_events() -> list[dict]:
    payload = json.loads(BASE_REPORT.read_text(encoding="utf-8"))
    output = []
    for row in payload["events"]:
        release = datetime.fromisoformat(row["release_utc"])
        if START <= release < END:
            output.append(
                {
                    "release_utc": row["release_utc"],
                    "event": row["event"],
                    "v5_prediction": row["v5_prediction"],
                    "v5_bias": row["v5_bias"],
                    "v5_confidence_pct": row["v5_confidence_pct"],
                    "v5_strategy": row["v5_strategy"],
                    "v5_failed_gates": row["v5_failed_gates"],
                    "actual": row["actual"],
                    "release_move_usd": row["release_move_usd"],
                    "point_in_time_source": row.get("point_in_time_source"),
                }
            )
    return output


def _markdown(report: dict) -> str:
    active = report["metrics"]["active_calls"]
    shadow = report["metrics"]["shadow_bias"]
    audit = report["fxmacrodata_audit"]
    lines = [
        "# Gold News Direction V6 - FXMacroData Three-Month Audit",
        "",
        "> FXMacroData is used for official timing, lagged releases, provenance, and forecast availability. It has zero directional weight until a stored-at-generation forecast archive passes chronological validation.",
        "",
        "## Summary",
        "",
        "| Measure | Result |",
        "|---|---:|",
        f"| Active calls | {active['calls']} / {active['events']} |",
        f"| Active-call accuracy | {active['accuracy_pct']:.2f}% |",
        f"| Coverage | {active['coverage_pct']:.2f}% |",
        f"| Shadow-bias accuracy | {shadow['accuracy_pct']:.2f}% |",
        f"| FXMacroData times verified | {audit['verified_event_times']} / {audit['events']} |",
        "",
        "## Event Replay",
        "",
        "| Date | Event | Final T-15 | Shadow | Confidence | Actual | Result | Gold move | FXMacroData |",
        "|---|---|---|---|---:|---|---|---:|---|",
    ]
    for row in report["events"]:
        result = "ABSTAIN" if row["prediction"] == "NO CALL" else (
            "WIN" if row["prediction"] == row["actual"] else "LOSS"
        )
        lines.append(
            f"| {row['release_utc'][:10]} | {row['event']} | {row['prediction']} | "
            f"{row['shadow_bias']} | {row['confidence_pct']:.2f}% | {row['actual']} | "
            f"{result} | {row['release_move_usd']:+.3f} USD | "
            f"{row['fxmacrodata'].get('event_time_verification', 'unavailable')} |"
        )
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "- NFP remains NO CALL. The shadow bias is shown for research but is not promoted.",
            "- CPI made three calls and lost the August 12 release-minute direction.",
            "- FXMacroData corrected the evidence pipeline and UTC checks; it did not improve directional accuracy in this replay because no authenticated, stored pre-release forecast archive was available.",
            "- The June 10 event falls just outside the anonymous 90-day FXMacroData window and is retained from the existing local archive.",
            "- These eight events are far too few to establish a stable 75% edge.",
        ]
    )
    return "\n".join(lines) + "\n"


def run() -> dict:
    if not BASE_REPORT.exists() or not MODEL_PATH.exists():
        raise FileNotFoundError("Run the V5 backtest before the FXMacroData audit.")
    artifact = joblib.load(MODEL_PATH)
    terminal = r"C:\Program Files\MetaTrader 5\terminal64.exe"
    if not mt5.initialize(path=terminal):
        raise RuntimeError(f"Could not initialize MT5: {mt5.last_error()}")
    try:
        symbol = _discover_gold()
        events = _base_events()
        existing = {row["release_utc"] for row in events}
        for event, release in EXTRA_EVENTS:
            if release.isoformat() not in existing:
                events.append(_new_event(artifact, symbol, event, release))
    finally:
        mt5.shutdown()

    client = FXMacroDataClient.from_env()
    for row in events:
        release = datetime.fromisoformat(row["release_utc"]).astimezone(timezone.utc)
        context = client.context(event=row["event"], release_utc=release, cutoff_utc=release - timedelta(minutes=15))
        row["prediction"] = row["v5_prediction"]
        row["shadow_bias"] = row["v5_bias"]
        row["confidence_pct"] = float(row["v5_confidence_pct"])
        row["fxmacrodata"] = context
    events.sort(key=lambda row: row["release_utc"])

    event_groups: dict[str, list[dict]] = defaultdict(list)
    for row in events:
        event_groups[row["event"]].append(row)
    report = {
        "status": "fxmacrodata_integrated_context_only",
        "methodology": {
            "window_start_utc": START.isoformat(),
            "window_end_utc_exclusive": END.isoformat(),
            "target": "Sign of the XAUUSD release-minute bid/ask midpoint move.",
            "prediction_cutoff": "T-15 minutes",
            "direction_policy": "Frozen V5 policy; FXMacroData decision weight is zero.",
            "leakage_control": (
                "The target release actual is excluded. Only announcements timestamped "
                "at or before T-15 are exposed as model context."
            ),
            "forecast_limit": (
                "FXMacroData forecast access is enabled, but only stored-at-generation "
                "records no later than T-15 are eligible."
                if client.api_key
                else "No FXMacroData API key is configured. Its prediction endpoint is "
                "not used, and retrospective forecasts are never reconstructed."
            ),
        },
        "symbol": symbol,
        "metrics": {
            "active_calls": _metrics(events, "prediction"),
            "shadow_bias": _metrics(events, "shadow_bias"),
            "by_event": {
                event: {
                    "active_calls": _metrics(rows, "prediction"),
                    "shadow_bias": _metrics(rows, "shadow_bias"),
                }
                for event, rows in sorted(event_groups.items())
            },
        },
        "fxmacrodata_audit": {
            "events": len(events),
            "verified_event_times": sum(
                row["fxmacrodata"].get("event_time_verification") == "verified"
                for row in events
            ),
            "events_with_lagged_history": sum(
                int(row["fxmacrodata"].get("known_release_count", 0)) > 0
                for row in events
            ),
            "stored_pre_release_forecasts": sum(
                row["fxmacrodata"].get("stored_pre_release_forecast") is not None
                for row in events
            ),
        },
        "events": events,
    }
    OUTPUT_JSON.write_text(json.dumps(report, indent=2), encoding="utf-8")
    with OUTPUT_CSV.open("w", newline="", encoding="utf-8") as handle:
        fields = [
            "release_utc",
            "event",
            "prediction",
            "shadow_bias",
            "confidence_pct",
            "actual",
            "release_move_usd",
            "result",
            "fxmacrodata_time_verification",
            "fxmacrodata_known_release_count",
        ]
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for row in events:
            writer.writerow(
                {
                    "release_utc": row["release_utc"],
                    "event": row["event"],
                    "prediction": row["prediction"],
                    "shadow_bias": row["shadow_bias"],
                    "confidence_pct": row["confidence_pct"],
                    "actual": row["actual"],
                    "release_move_usd": row["release_move_usd"],
                    "result": "ABSTAIN" if row["prediction"] == "NO CALL" else (
                        "WIN" if row["prediction"] == row["actual"] else "LOSS"
                    ),
                    "fxmacrodata_time_verification": row["fxmacrodata"].get("event_time_verification"),
                    "fxmacrodata_known_release_count": row["fxmacrodata"].get("known_release_count"),
                }
            )
    OUTPUT_MD.write_text(_markdown(report), encoding="utf-8")
    return report


if __name__ == "__main__":
    payload = run()
    print(json.dumps(payload["metrics"], indent=2))
    print(json.dumps(payload["fxmacrodata_audit"], indent=2))
    print(f"Saved {OUTPUT_MD}")
