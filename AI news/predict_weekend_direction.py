from __future__ import annotations

import argparse
from datetime import datetime, timedelta, timezone

import joblib
import MetaTrader5 as mt5
import numpy as np

from train_weekend_direction_model import MODEL_PATH, _series_from_rates, discover_symbol
from weekend_direction_model import build_weekend_dataset, feature_vector_at


def main() -> None:
    parser = argparse.ArgumentParser(description="Produce a prediction-only XAUUSD weekend direction estimate")
    parser.add_argument("--force", action="store_true", help="Allow an informational estimate outside Friday")
    args = parser.parse_args()
    if not MODEL_PATH.exists():
        raise SystemExit("Model is missing. Run train_weekend_direction_model.py first.")
    bundle = joblib.load(MODEL_PATH)
    if not mt5.initialize():
        raise SystemExit(f"MT5 initialization failed: {mt5.last_error()}")
    try:
        end = datetime.now(timezone.utc)
        start = end - timedelta(days=150)
        series = {}
        for canonical, timeframe, seconds in (
            ("XAUUSD", mt5.TIMEFRAME_M1, 60),
            ("XAGUSD", mt5.TIMEFRAME_H1, 3600),
            ("US30", mt5.TIMEFRAME_H1, 3600),
            ("BTCUSD", mt5.TIMEFRAME_H1, 3600),
        ):
            symbol = discover_symbol(canonical)
            if not symbol:
                continue
            mt5.symbol_select(symbol, True)
            info = mt5.symbol_info(symbol)
            rates = mt5.copy_rates_range(symbol, timeframe, start, end)
            if rates is not None and len(rates):
                series[canonical] = _series_from_rates(symbol, float(info.point), seconds, rates)
        gold = series["XAUUSD"]
        latest = datetime.fromtimestamp(int(gold.time[-1]), timezone.utc)
        if latest.weekday() != 4 and not args.force:
            raise SystemExit(
                f"Latest completed bar is {latest:%A %Y-%m-%d %H:%M UTC}. "
                "Run on Friday near the broker close, or add --force for research."
            )
        cross = {key: value for key, value in series.items() if key != "XAUUSD"}
        historical = build_weekend_dataset(gold, cross)
        previous_gaps = [record.gap_pct for record in historical]
        vector = feature_vector_at(gold, len(gold.time) - 1, cross, previous_gaps)
        probability_up = float(bundle["model"].predict_proba(np.asarray([vector], dtype=float))[:, 1][0])
        direction = "UP" if probability_up >= 0.5 else "DOWN"
        confidence = max(probability_up, 1.0 - probability_up)
        threshold = float(bundle["confidence_threshold"])
        validated = bool(bundle.get("validated", False))
        decision = direction if validated and confidence >= threshold else "NO TRADE"
        print(f"As of: {latest.isoformat()}")
        print(f"Broker symbol: {gold.symbol}")
        print(f"Probability UP: {probability_up:.1%}")
        print(f"Probability DOWN: {1.0 - probability_up:.1%}")
        print(f"Confidence gate: {threshold:.1%}")
        print(f"Frozen-test status: {'VALIDATED' if validated else 'REJECTED'}")
        print(f"Model decision: {decision}")
        print("Prediction only. This script never sends an MT5 order.")
    finally:
        mt5.shutdown()


if __name__ == "__main__":
    main()
