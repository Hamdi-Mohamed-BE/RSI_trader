from __future__ import annotations

import argparse
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import joblib
import MetaTrader5 as mt5
import numpy as np

from backtest_weekend_direction_v2 import MODEL_PATH
from train_weekend_direction_model import _series_from_rates, discover_symbol
from weekend_direction_model import WeekendRecord, build_weekend_dataset, feature_vector_at
from weekend_direction_v2 import fetch_gold_cot, load_macro_context, v2_feature_vector


ROOT = Path(__file__).resolve().parent
OUTPUT_PATH = ROOT / "predictions" / "gold_weekend_direction_v2_latest.json"


def _latest_completed_index(times: np.ndarray, timeframe_seconds: int, now: datetime) -> int:
    latest_start = int(now.timestamp()) - timeframe_seconds
    index = int(np.searchsorted(times, latest_start, side="right") - 1)
    if index < 0:
        raise RuntimeError("No completed XAUUSD bar is available")
    return index


def main() -> None:
    parser = argparse.ArgumentParser(description="Prediction-only XAUUSD weekend direction V2 estimate")
    parser.add_argument("--force", action="store_true", help="Show an informational estimate outside Friday")
    parser.add_argument("--refresh-context", action="store_true", help="Refresh official FRED and CFTC caches")
    args = parser.parse_args()
    if not MODEL_PATH.exists():
        raise SystemExit("V2 model is missing. Run backtest_weekend_direction_v2.py first.")

    bundle = joblib.load(MODEL_PATH)
    if not mt5.initialize():
        raise SystemExit(f"MT5 initialization failed: {mt5.last_error()}")
    try:
        now = datetime.now(timezone.utc)
        start = now - timedelta(days=260)
        series = {}
        for canonical, timeframe, seconds in (
            ("XAUUSD", mt5.TIMEFRAME_M1, 60),
            ("XAGUSD", mt5.TIMEFRAME_H1, 3600),
            ("US30", mt5.TIMEFRAME_H1, 3600),
            ("BTCUSD", mt5.TIMEFRAME_H1, 3600),
        ):
            symbol = discover_symbol(canonical)
            if not symbol:
                if canonical == "XAUUSD":
                    raise RuntimeError("No broker XAUUSD symbol was found")
                continue
            mt5.symbol_select(symbol, True)
            info = mt5.symbol_info(symbol)
            rates = mt5.copy_rates_range(symbol, timeframe, start, now)
            if info is not None and rates is not None and len(rates):
                series[canonical] = _series_from_rates(symbol, float(info.point), seconds, rates)

        gold = series["XAUUSD"]
        cutoff_index = _latest_completed_index(gold.time, gold.timeframe_seconds, now)
        latest = datetime.fromtimestamp(int(gold.time[cutoff_index]), timezone.utc)
        if latest.weekday() != 4 and not args.force:
            raise SystemExit(
                f"Latest completed bar is {latest:%A %Y-%m-%d %H:%M UTC}. "
                "Run on Friday near the broker close, or add --force for research."
            )

        cross = {key: value for key, value in series.items() if key != "XAUUSD"}
        historical = build_weekend_dataset(gold, cross)
        if len(historical) < 26:
            raise RuntimeError(f"Only {len(historical)} completed weekends are available; 26 are required")
        previous_gaps = [record.gap_pct for record in historical]
        base_vector = feature_vector_at(gold, cutoff_index, cross, previous_gaps)
        synthetic = WeekendRecord(
            feature_time_utc=latest.isoformat(),
            friday_close_utc=latest.isoformat(),
            reopen_utc=latest.isoformat(),
            friday_mid_close=float(gold.close[cutoff_index]),
            reopen_mid_open=float(gold.close[cutoff_index]),
            gap_usd=0.0,
            gap_pct=0.0,
            label_up=0,
            feature_values=base_vector,
        )
        macro = load_macro_context(refresh=args.refresh_context)
        cot = fetch_gold_cot(refresh=args.refresh_context)
        vector = np.asarray([v2_feature_vector(synthetic, macro, cot)], dtype=float)
        significant_probability = float(bundle["significant_model"].predict_proba(vector)[:, 1][0])
        direction_probability_up = float(bundle["direction_model"].predict_proba(vector)[:, 1][0])
        direction_confidence = max(direction_probability_up, 1.0 - direction_probability_up)
        policy = bundle["policy"]
        direction = "UP" if direction_probability_up >= 0.5 else "DOWN"
        passes_gates = (
            significant_probability >= float(policy["significant_threshold"])
            and direction_confidence >= float(policy["direction_threshold"])
        )
        validated = bool(bundle.get("validated", False))
        decision = direction if validated and passes_gates else "NO TRADE"
        gap_threshold_pct = float(np.quantile(np.abs(previous_gaps[-26:]), 0.70))
        gap_threshold_usd = gap_threshold_pct * float(gold.close[cutoff_index])

        payload = {
            "as_of_utc": latest.isoformat(),
            "broker_symbol": gold.symbol,
            "gold_price": round(float(gold.close[cutoff_index]), 4),
            "meaningful_gap_threshold_pct": gap_threshold_pct,
            "meaningful_gap_threshold_usd": round(gap_threshold_usd, 4),
            "meaningful_gap_probability": significant_probability,
            "probability_up": direction_probability_up,
            "probability_down": 1.0 - direction_probability_up,
            "raw_direction": direction,
            "gates_passed": passes_gates,
            "validation_status": "VALIDATED" if validated else "REJECTED",
            "decision": decision,
            "purpose": "Prediction only; no orders are sent",
        }
        OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
        OUTPUT_PATH.write_text(json.dumps(payload, indent=2), encoding="utf-8")

        print(f"As of: {payload['as_of_utc']}")
        print(f"Broker symbol: {payload['broker_symbol']} at {payload['gold_price']}")
        print(f"Meaningful gap threshold: ${gap_threshold_usd:.2f} ({gap_threshold_pct:.3%})")
        print(f"Probability of meaningful gap: {significant_probability:.1%}")
        print(f"Probability UP: {direction_probability_up:.1%}")
        print(f"Probability DOWN: {1.0 - direction_probability_up:.1%}")
        print(f"Nested-test status: {payload['validation_status']}")
        print(f"Model decision: {decision}")
        print("Prediction only. This script never sends an MT5 order.")
    finally:
        mt5.shutdown()


if __name__ == "__main__":
    main()
