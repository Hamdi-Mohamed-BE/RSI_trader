from __future__ import annotations

import argparse
import json
import os
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path

import joblib
import MetaTrader5 as mt5
import numpy as np

from economic_context import EconomicContextStore
from gold_direction_rules import live_rule_probability
from macro_regime import MacroRegimeStore
from news_core import EVENTS, ROOT, complete_sides, extract_features, normalize_rows
from official_nowcasts import OfficialNowcastStore
from point_in_time_store import context_for_prediction
from point_in_time_store import save_macro_snapshot, save_market_snapshot


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


def _direction_vector(
    profile: str,
    features_15: list[float] | None,
    features_30: list[float],
    macro_features: list[float],
) -> np.ndarray:
    vector_30 = np.asarray(features_30, dtype=float)
    vector_macro = np.asarray(macro_features, dtype=float)
    if profile == "t30":
        return vector_30
    if profile == "t30_macro":
        return np.concatenate((vector_30, vector_macro))
    if features_15 is None:
        raise RuntimeError(f"The {profile} model requires the canonical T-15 snapshot.")
    vector_15 = np.asarray(features_15, dtype=float)
    if profile == "t15":
        return vector_15
    dual = np.concatenate((vector_15, vector_30, vector_15 - vector_30))
    if profile == "dual":
        return dual
    if profile == "dual_macro":
        return np.concatenate((dual, vector_macro))
    raise RuntimeError(f"Unsupported gold-direction feature profile: {profile}")


def _impact_decision(
    mode_artifact: dict,
    event: str,
    artifact: dict,
    vector: np.ndarray,
) -> dict:
    prior_probability = float(
        artifact["event_prior_probability_positive"][event]
    )
    rule_policy = artifact.get("direction_rule_policy")
    if rule_policy:
        rule = rule_policy["rules"][event]
        reliability = float(rule_policy["reliability"][event])
        probability_positive = live_rule_probability(
            rule,
            artifact["event_direction_history"].get(event, []),
            reliability,
        )
        impact = (
            "POSITIVE" if probability_positive >= 0.5 else "NEGATIVE"
        )
        return {
            "gold_impact": impact,
            "confidence": max(
                probability_positive,
                1 - probability_positive,
            ),
            "probability_positive": probability_positive,
            "probability_negative": 1 - probability_positive,
            "market_probability_positive": prior_probability,
            "historical_probability_positive": prior_probability,
            "market_model_weight": 0.0,
            "direction_rule": rule,
        }
    model_weight = float(mode_artifact["model_weight"])
    market_probability = prior_probability
    if model_weight > 0:
        model = mode_artifact["model"]
        classes = list(model.classes_)
        market_probability = float(
            model.predict_proba(vector.reshape(1, -1))[0][classes.index("POSITIVE")]
        )
    probability_positive = (
        model_weight * market_probability
        + (1 - model_weight) * prior_probability
    )
    impact = "POSITIVE" if probability_positive >= 0.5 else "NEGATIVE"
    raw_confidence = max(probability_positive, 1 - probability_positive)
    confidence = float(
        mode_artifact["confidence_calibrator"].predict([raw_confidence])[0]
    )
    return {
        "gold_impact": impact,
        "confidence": confidence,
        "probability_positive": probability_positive,
        "probability_negative": 1 - probability_positive,
        "market_probability_positive": market_probability,
        "historical_probability_positive": prior_probability,
        "market_model_weight": model_weight,
        "direction_rule": "legacy_event_model_blend",
    }


def make_prediction(
    event: str,
    release_utc: datetime,
    forecast: str | None = None,
    previous: str | None = None,
    source_url: str | None = None,
) -> dict:
    event = event.upper()
    now = datetime.now(timezone.utc)
    minutes_before = (release_utc - now).total_seconds() / 60
    if event not in EVENTS:
        return {
            "event": event,
            "release_time_utc": release_utc.isoformat(),
            "gold_impact": "UNKNOWN",
            "confidence_pct": 0.0,
            "data_quality": "unsupported event",
            "reason": f"The trained archive does not yet cover {event}.",
        }
    if minutes_before <= 0:
        raise RuntimeError("Pre-release predictions cannot be generated after the event has started.")
    if not 8 <= minutes_before <= 30:
        raise RuntimeError(
            f"Query is {minutes_before:.1f} minutes before release; the supported window is 8-30 minutes."
        )

    lead = choose_lead(minutes_before)
    artifact_path = ROOT / "models" / "gold_news_direction.joblib"
    if not artifact_path.exists():
        raise RuntimeError(
            "The gold direction artifact is missing. Run backtest_gold_direction.py first."
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
        mode = "early" if lead == 30 else "final"
        if lead == 15:
            features_15, context_15 = snapshot(15)
        mode_artifact = artifact[mode]
        vector = np.empty(0, dtype=float)
        if float(mode_artifact["model_weight"]) > 0:
            profile = mode_artifact["candidate"]["profile"]
            macro_features = (
                MacroRegimeStore().features(release_utc)
                if "macro" in profile
                else []
            )
            vector = _direction_vector(
                profile,
                features_15,
                features_30,
                macro_features,
            )
        decision = _impact_decision(mode_artifact, event, artifact, vector)
        direction = decision["gold_impact"]
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
        invalidation = (
            "A materially stronger-than-forecast USD release can reverse a POSITIVE gold forecast."
            if direction == "POSITIVE"
            else "A materially weaker-than-forecast USD release can reverse a NEGATIVE gold forecast."
        )
        result = {
            "generated_at_utc": now.isoformat(),
            "event": event,
            "release_time_utc": release_utc.isoformat(),
            "minutes_before_release": round(minutes_before, 2),
            "symbol": symbol,
            "gold_impact": direction,
            "prediction": direction,
            "directional_model_bias": direction,
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
                    f"The validated event rule is "
                    f"{decision['direction_rule'].replace('_', ' ')}."
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
                "name": "binary gold-impact model",
                "lead_minutes": lead,
                "estimator": mode_artifact["candidate"]["name"],
                "feature_profile": mode_artifact["candidate"]["profile"],
                "market_model_weight": decision["market_model_weight"],
                "trained_through": artifact["trained_through"],
                "artifact_version": artifact["artifact_version"],
            },
            "market_context": context,
            "point_in_time_context": external_context,
            "economic_consensus_context": economic_context,
            "official_nowcast_context": official_nowcast,
            "captured_related_markets": sorted(captured_markets),
            "probability_context": {
                "historical_event_positive_pct": round(
                    100 * decision["historical_probability_positive"],
                    2,
                ),
                "market_model_positive_pct": round(
                    100 * decision["market_probability_positive"],
                    2,
                ),
                "direction_rule": decision["direction_rule"],
            },
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
    parser.add_argument("--event", required=True, help="NFP, GDP, CPI, PPI, or FOMC")
    parser.add_argument("--release", required=True, type=parse_release, help="ISO-8601 release time")
    parser.add_argument("--forecast")
    parser.add_argument("--previous")
    parser.add_argument("--source-url")
    args = parser.parse_args()
    print(
        json.dumps(
            make_prediction(
                args.event,
                args.release,
                forecast=args.forecast,
                previous=args.previous,
                source_url=args.source_url,
            ),
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
