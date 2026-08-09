from __future__ import annotations

import argparse
import json
import os
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path

import joblib
import MetaTrader5 as mt5

from economic_context import EconomicContextStore
from fomc_pipeline import (
    fomc_release_phases,
    pricing_context,
)
from news_core import ROOT, complete_sides, extract_features, normalize_rows
from official_nowcasts import OfficialNowcastStore
from point_in_time_store import context_for_prediction
from point_in_time_store import save_macro_snapshot, save_market_snapshot
from news_v5 import SUPPORTED_EVENTS, artifact_prediction


PREDICTION_DIR = ROOT / "predictions"
RELATED_MARKETS = {
    "gold": ("XAUUSD", "GOLD"),
    "usd_index": ("DXY", "USDX", "USDINDEX"),
    "us_2y_yield": ("US02Y", "US2Y", "UST2Y"),
    "us_10y_yield": ("US10Y", "UST10Y", "TNX"),
    "nasdaq": ("US100", "NAS100", "USTEC", "NDX"),
    "sp500": ("US500", "SPX500", "SP500"),
    "usdjpy": ("USDJPY",),
}


def load_env() -> None:
    path = ROOT / ".env"
    if not path.exists():
        return
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def compact(value: str) -> str:
    return re.sub(r"[^A-Z0-9]", "", value.upper())


def discover_gold() -> str:
    wanted = compact(os.getenv("XAU_SYMBOL", "XAUUSD"))
    symbols = mt5.symbols_get()
    if not symbols:
        raise RuntimeError(f"MT5 returned no symbols: {mt5.last_error()}")
    names = [item.name for item in symbols]
    ranked = sorted(
        names,
        key=lambda name: (
            compact(name) != wanted,
            not compact(name).startswith(wanted),
            len(name),
        ),
    )
    for name in ranked:
        if wanted in compact(name) and mt5.symbol_select(name, True):
            return name
    raise RuntimeError("Could not discover an XAUUSD broker symbol.")


def discover_related_symbols() -> dict[str, str]:
    symbols = mt5.symbols_get() or ()
    names = [item.name for item in symbols]
    discovered = {}
    for label, aliases in RELATED_MARKETS.items():
        ranked = sorted(
            names,
            key=lambda name: (
                min(
                    (
                        0 if compact(name) == compact(alias)
                        else 1 if compact(name).startswith(compact(alias))
                        else 2 if compact(alias) in compact(name)
                        else 3
                    )
                    for alias in aliases
                ),
                len(name),
            ),
        )
        for name in ranked:
            if any(compact(alias) in compact(name) for alias in aliases):
                if mt5.symbol_select(name, True):
                    discovered[label] = name
                    break
    return discovered


def _return(values: list[float], minutes: int) -> float | None:
    if len(values) <= minutes or values[-1 - minutes] == 0:
        return None
    return float(values[-1] / values[-1 - minutes] - 1)


def related_market_metrics(symbol: str) -> dict[str, float | int | str | None]:
    rates = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_M1, 1, 65)
    if rates is None or len(rates) < 31:
        return {"symbol": symbol, "status": "insufficient_history"}
    closes = [float(row["close"]) for row in rates]
    highs = [float(row["high"]) for row in rates]
    lows = [float(row["low"]) for row in rates]
    volumes = [float(row["tick_volume"]) for row in rates]
    tick = mt5.symbol_info_tick(symbol)
    spread = (
        float(tick.ask - tick.bid)
        if tick is not None and tick.ask > tick.bid
        else None
    )
    book_imbalance = None
    if mt5.market_book_add(symbol):
        try:
            book = mt5.market_book_get(symbol) or ()
            buy_types = {
                getattr(mt5, "BOOK_TYPE_BUY", -1),
                getattr(mt5, "BOOK_TYPE_BUY_MARKET", -2),
            }
            sell_types = {
                getattr(mt5, "BOOK_TYPE_SELL", -3),
                getattr(mt5, "BOOK_TYPE_SELL_MARKET", -4),
            }
            buy_volume = sum(
                float(getattr(item, "volume_dbl", item.volume))
                for item in book
                if item.type in buy_types
            )
            sell_volume = sum(
                float(getattr(item, "volume_dbl", item.volume))
                for item in book
                if item.type in sell_types
            )
            if buy_volume + sell_volume > 0:
                book_imbalance = (buy_volume - sell_volume) / (buy_volume + sell_volume)
        finally:
            mt5.market_book_release(symbol)
    return {
        "symbol": symbol,
        "status": "ok",
        "last_close": closes[-1],
        "return_5m": _return(closes, 5),
        "return_15m": _return(closes, 15),
        "return_30m": _return(closes, 30),
        "range_30m_pct": (
            (max(highs[-30:]) - min(lows[-30:])) / closes[-1]
            if closes[-1]
            else None
        ),
        "volume_5_to_30": (
            (sum(volumes[-5:]) / 5) / (sum(volumes[-30:]) / 30)
            if sum(volumes[-30:]) > 0
            else None
        ),
        "spread": spread,
        "book_imbalance": book_imbalance,
    }


def capture_related_markets(
    release_utc: datetime,
    observed_at_utc: datetime,
) -> dict[str, dict]:
    instruments = {
        label: related_market_metrics(symbol)
        for label, symbol in discover_related_symbols().items()
    }
    if instruments:
        save_market_snapshot(
            release_utc=release_utc,
            observed_at_utc=observed_at_utc,
            instruments=instruments,
            source="connected MT5 terminal",
        )
    return instruments


def bars_for_prediction(symbol: str, release_utc: datetime) -> tuple[dict, dict]:
    now = datetime.now(timezone.utc)
    last_complete = now.replace(second=0, microsecond=0) - timedelta(minutes=1)
    start = release_utc.replace(tzinfo=timezone.utc).timestamp() - 5 * 60 * 60
    rates = mt5.copy_rates_range(
        symbol,
        mt5.TIMEFRAME_M1,
        datetime.fromtimestamp(start, timezone.utc),
        min(last_complete, release_utc),
    )
    if rates is None or len(rates) < 150:
        raise RuntimeError(f"Insufficient MT5 M1 history for {symbol}: {mt5.last_error()}")
    rows = normalize_rows(
        [
            {
                "time": int(row["time"]),
                "open": row["open"],
                "high": row["high"],
                "low": row["low"],
                "close": row["close"],
                "tick_volume": row["tick_volume"],
            }
            for row in rates
        ]
    )
    bid = {round(row["timestamp"] / 60_000) * 60_000: row for row in rows}
    info = mt5.symbol_info(symbol)
    tick = mt5.symbol_info_tick(symbol)
    spread = (
        float(tick.ask - tick.bid)
        if tick is not None and tick.ask > tick.bid
        else float(info.spread * info.point)
    )
    _, ask, _ = complete_sides(bid, {}, spread)
    return bid, ask


def choose_lead(minutes_before: float) -> int:
    return 30 if minutes_before > 15 else 15


def reason_lines(context: dict, event: str) -> list[str]:
    reasons = []
    momentum = context["momentum_15_atr"]
    if momentum > 0.25:
        reasons.append("Gold has bullish pre-release 15-minute momentum.")
    elif momentum < -0.25:
        reasons.append("Gold has bearish pre-release 15-minute momentum.")
    else:
        reasons.append("Gold pre-release momentum is neutral.")
    if abs(context["volume_z"]) > 1:
        reasons.append("Pre-release tick volume is unusually elevated.")
    reasons.append(f"The model uses the historical {event} reaction profile.")
    return reasons


def make_prediction(
    event: str,
    release_utc: datetime,
    forecast: str | None = None,
    previous: str | None = None,
    source_url: str | None = None,
    fomc_current_lower: float | None = None,
    fomc_current_upper: float | None = None,
    fomc_cut_25_probability: float | None = None,
    fomc_hold_probability: float | None = None,
    fomc_hike_25_probability: float | None = None,
    fomc_cut_50_probability: float | None = None,
    fomc_hike_50_probability: float | None = None,
) -> dict:
    event = event.upper()
    now = datetime.now(timezone.utc)
    minutes_before = (release_utc - now).total_seconds() / 60
    if event not in SUPPORTED_EVENTS:
        return {
            "event": event,
            "release_time_utc": release_utc.isoformat(),
            "gold_impact": "UNKNOWN",
            "confidence_pct": 0.0,
            "data_quality": "unsupported event",
            "reason": (
                f"V5 supports only {', '.join(SUPPORTED_EVENTS)}; "
                f"{event} is intentionally disabled."
            ),
        }
    if minutes_before <= 0:
        raise RuntimeError("Pre-release predictions cannot be generated after the event has started.")
    if not 8 <= minutes_before <= 30:
        raise RuntimeError(
            f"Query is {minutes_before:.1f} minutes before release; the supported window is 8-30 minutes."
        )

    lead = choose_lead(minutes_before)
    artifact_path = ROOT / "models" / "gold_news_v5.joblib"
    if not artifact_path.exists():
        raise RuntimeError(
            "The V5 gold direction artifact is missing. Run backtest_news_v5.py first."
        )
    artifact = joblib.load(artifact_path)
    if forecast or previous:
        save_macro_snapshot(
            event=event,
            release_utc=release_utc,
            observed_at_utc=now,
            forecast=forecast,
            previous=previous,
            source="pre-release user/calendar input",
            source_url=source_url,
        )
    terminal = os.getenv("MT5_PATH", r"C:\Program Files\MetaTrader 5\terminal64.exe")
    if not mt5.initialize(path=terminal):
        raise RuntimeError(f"Could not initialize MT5: {mt5.last_error()}")
    try:
        symbol = discover_gold()
        bid, ask = bars_for_prediction(symbol, release_utc)
        captured_markets = capture_related_markets(release_utc, now)

        def snapshot(snapshot_lead: int) -> tuple[list[float], dict]:
            extracted = extract_features(
                event,
                release_utc,
                bid,
                ask,
                snapshot_lead,
                artifact["history_features"].get(event),
            )
            if extracted is None:
                raise RuntimeError(
                    f"The canonical T-{snapshot_lead} M1 feature window is incomplete."
                )
            features, snapshot_context = extracted
            return features, snapshot_context

        features_30, context_30 = snapshot(30)
        features_15 = None
        context_15 = None
        if lead == 15:
            features_15, context_15 = snapshot(15)
        fomc_pricing = (
            pricing_context(
                current_lower=fomc_current_lower,
                current_upper=fomc_current_upper,
                cut_25_probability=fomc_cut_25_probability,
                hold_probability=fomc_hold_probability,
                hike_25_probability=fomc_hike_25_probability,
                cut_50_probability=fomc_cut_50_probability,
                hike_50_probability=fomc_hike_50_probability,
            )
            if event == "FOMC"
            else None
        )
        decision = artifact_prediction(
            artifact,
            event,
            lead,
            features_15 or features_30,
            features_30,
        )
        direction = decision["prediction"]
        bias = decision["bias"]
        confidence = decision["confidence"]
        context = context_15 or context_30
        expected = artifact["expected_release_range_by_event"].get(event, {})
        external_context = context_for_prediction(event, release_utc, now)
        economic_context = EconomicContextStore().context(
            event,
            release_utc,
            forecast=forecast,
            previous=previous,
        )
        official_nowcast = OfficialNowcastStore().context(
            event,
            release_utc,
        )
        available_external = [
            name for name, value in external_context.items() if value is not None
        ]
        if direction == "NO CALL":
            invalidation = (
                "No active direction: "
                + ", ".join(decision["failed_gates"])
                + ". The shadow bias is informational only."
            )
        else:
            invalidation = (
                "A materially stronger-than-forecast USD release can reverse a POSITIVE gold call."
                if direction == "POSITIVE"
                else "A materially weaker-than-forecast USD release can reverse a NEGATIVE gold call."
            )
        result = {
            "generated_at_utc": now.isoformat(),
            "event": event,
            "release_time_utc": release_utc.isoformat(),
            "minutes_before_release": round(minutes_before, 2),
            "symbol": symbol,
            "gold_impact": direction,
            "prediction": direction,
            "directional_model_bias": bias,
            "confidence_pct": round(100 * confidence, 2),
            "probabilities": {
                "POSITIVE": round(100 * decision["probability_positive"], 2),
                "NEGATIVE": round(100 * decision["probability_negative"], 2),
            },
            "expected_impulse_range_usd": {
                "median": expected.get("median_usd"),
            },
            "expected_reaction_window": "release minute; the trained archive is M1 bid/ask",
            "main_reasons": [
                *reason_lines(context, event),
                (
                    f"V5 strategy: {decision['strategy'].replace('_', ' ')}."
                ),
                (
                    "The confidence and agreement gates passed."
                    if direction != "NO CALL"
                    else "No active call because: " + ", ".join(decision["failed_gates"]) + "."
                ),
                *(
                    [
                        (
                            "The FOMC history and T-30 model "
                            f"{'agree.' if not decision['failed_gates'] else 'do not agree.'}"
                        ),
                    ]
                    if event == "FOMC"
                    else []
                ),
            ],
            "key_invalidation_condition": invalidation,
            "alternative_scenario": "The opposite gold impact becomes more likely when the published surprise clearly contradicts the pre-release estimate.",
            "data_quality": (
                "enhanced"
                if len(available_external) == len(external_context)
                else "partial: live XAUUSD M1 is available; missing point-in-time context is not fabricated"
            ),
            "model": {
                "name": "event-specific gold-impact V5",
                "lead_minutes": lead,
                "estimator": decision["strategy"],
                "feature_profile": f"canonical_t{lead}",
                "active_call_allowed": lead == 15,
                "trained_through": artifact["trained_through"],
                "artifact_version": artifact["artifact_version"],
            },
            "market_context": context,
            "point_in_time_context": external_context,
            "economic_consensus_context": economic_context,
            "official_nowcast_context": official_nowcast,
            "captured_related_markets": sorted(captured_markets),
            "probability_context": {
                "market_model_positive_pct": round(100 * decision["probability_positive"], 2),
                "shadow_bias": bias,
                "history_bias": (
                    "POSITIVE" if decision["history_bias"] == "BUY"
                    else "NEGATIVE" if decision["history_bias"] == "SELL"
                    else None
                ),
                "gates": decision["gates"],
                "failed_gates": decision["failed_gates"],
                "fomc_pricing_context_only": fomc_pricing,
            },
            "fomc_release_phases": (
                fomc_release_phases(release_utc)
                if event == "FOMC"
                else None
            ),
            "execution_capability": False,
        }
    finally:
        mt5.shutdown()

    PREDICTION_DIR.mkdir(exist_ok=True)
    filename = f"{release_utc.strftime('%Y%m%dT%H%M%SZ')}-{event.lower()}.json"
    path = PREDICTION_DIR / filename
    if path.exists():
        raise RuntimeError(f"A prediction is already permanently saved for this event: {path}")
    path.write_text(json.dumps(result, indent=2), encoding="utf-8")
    result["saved_to"] = str(path)
    return result


def parse_release(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise argparse.ArgumentTypeError("Release time must include a timezone or Z.")
    return parsed.astimezone(timezone.utc)


def main() -> None:
    load_env()
    parser = argparse.ArgumentParser(description="Predict the immediate XAUUSD news impulse.")
    parser.add_argument("--event", required=True, help="NFP, CPI, or FOMC")
    parser.add_argument("--release", required=True, type=parse_release, help="ISO-8601 release time")
    parser.add_argument("--forecast")
    parser.add_argument("--previous")
    parser.add_argument("--source-url")
    parser.add_argument("--fomc-current-lower", type=float)
    parser.add_argument("--fomc-current-upper", type=float)
    parser.add_argument("--fomc-cut-25-probability", type=float)
    parser.add_argument("--fomc-hold-probability", type=float)
    parser.add_argument("--fomc-hike-25-probability", type=float)
    parser.add_argument("--fomc-cut-50-probability", type=float)
    parser.add_argument("--fomc-hike-50-probability", type=float)
    args = parser.parse_args()
    print(
        json.dumps(
            make_prediction(
                args.event,
                args.release,
                forecast=args.forecast,
                previous=args.previous,
                source_url=args.source_url,
                fomc_current_lower=args.fomc_current_lower,
                fomc_current_upper=args.fomc_current_upper,
                fomc_cut_25_probability=args.fomc_cut_25_probability,
                fomc_hold_probability=args.fomc_hold_probability,
                fomc_hike_25_probability=args.fomc_hike_25_probability,
                fomc_cut_50_probability=args.fomc_cut_50_probability,
                fomc_hike_50_probability=args.fomc_hike_50_probability,
            ),
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
