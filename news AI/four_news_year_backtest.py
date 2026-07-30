from __future__ import annotations

import csv
import json
import os
from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import MetaTrader5 as mt5
import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, brier_score_loss
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from news_direction_backtest import Event, collect, rates, row_before
from xau_m1_buy_stop_grid import discover_xau_symbol, load_env_file


BASE_DIR = Path(__file__).resolve().parent
REPORT_JSON = BASE_DIR / "four_news_year_backtest_report.json"
REPORT_CSV = BASE_DIR / "four_news_year_predictions.csv"
START_BALANCE_USD = 100.0
FIXED_LOT = 0.08
LEVERAGE = 500.0


def event(time_utc: str, name: str) -> Event:
    return Event(f"{time_utc}:00+00:00", name)


# This full preceding year is training-only. Times are actual UTC release times.
TRAIN_EVENTS = [
    event("2024-07-31T18:00", "FOMC"),
    event("2024-08-02T12:30", "Payrolls"),
    event("2024-08-13T12:30", "PPI"),
    event("2024-08-14T12:30", "CPI"),
    event("2024-09-06T12:30", "Payrolls"),
    event("2024-09-11T12:30", "CPI"),
    event("2024-09-12T12:30", "PPI"),
    event("2024-09-18T18:00", "FOMC"),
    event("2024-10-04T12:30", "Payrolls"),
    event("2024-10-10T12:30", "CPI"),
    event("2024-10-11T12:30", "PPI"),
    event("2024-11-01T12:30", "Payrolls"),
    event("2024-11-07T19:00", "FOMC"),
    event("2024-11-13T13:30", "CPI"),
    event("2024-11-14T13:30", "PPI"),
    event("2024-12-06T13:30", "Payrolls"),
    event("2024-12-11T13:30", "CPI"),
    event("2024-12-12T13:30", "PPI"),
    event("2024-12-18T19:00", "FOMC"),
    event("2025-01-10T13:30", "Payrolls"),
    event("2025-01-14T13:30", "PPI"),
    event("2025-01-15T13:30", "CPI"),
    event("2025-01-29T19:00", "FOMC"),
    event("2025-02-07T13:30", "Payrolls"),
    event("2025-02-12T13:30", "CPI"),
    event("2025-02-13T13:30", "PPI"),
    event("2025-03-07T13:30", "Payrolls"),
    event("2025-03-12T12:30", "CPI"),
    event("2025-03-13T12:30", "PPI"),
    event("2025-03-19T18:00", "FOMC"),
    event("2025-04-04T12:30", "Payrolls"),
    event("2025-04-10T12:30", "CPI"),
    event("2025-04-11T12:30", "PPI"),
    event("2025-05-02T12:30", "Payrolls"),
    event("2025-05-07T18:00", "FOMC"),
    event("2025-05-13T12:30", "CPI"),
    event("2025-05-15T12:30", "PPI"),
    event("2025-06-06T12:30", "Payrolls"),
    event("2025-06-11T12:30", "CPI"),
    event("2025-06-12T12:30", "PPI"),
    event("2025-06-18T18:00", "FOMC"),
    event("2025-07-03T12:30", "Payrolls"),
    event("2025-07-15T12:30", "CPI"),
    event("2025-07-16T12:30", "PPI"),
]


# Requested untouched test year. Shutdown-delayed dates are the actual releases.
TEST_EVENTS = [
    event("2025-07-30T18:00", "FOMC"),
    event("2025-08-01T12:30", "Payrolls"),
    event("2025-08-12T12:30", "CPI"),
    event("2025-08-14T12:30", "PPI"),
    event("2025-09-05T12:30", "Payrolls"),
    event("2025-09-10T12:30", "PPI"),
    event("2025-09-11T12:30", "CPI"),
    event("2025-09-17T18:00", "FOMC"),
    event("2025-10-24T12:30", "CPI"),
    event("2025-10-29T18:00", "FOMC"),
    event("2025-11-20T13:30", "Payrolls"),
    event("2025-11-25T13:30", "PPI"),
    event("2025-12-10T19:00", "FOMC"),
    event("2025-12-16T13:30", "Payrolls"),
    event("2025-12-18T13:30", "CPI"),
    event("2026-01-09T13:30", "Payrolls"),
    event("2026-01-13T13:30", "CPI"),
    event("2026-01-14T13:30", "PPI"),
    event("2026-01-28T19:00", "FOMC"),
    event("2026-01-30T13:30", "PPI"),
    event("2026-02-11T13:30", "Payrolls"),
    event("2026-02-13T13:30", "CPI"),
    event("2026-02-27T13:30", "PPI"),
    event("2026-03-06T13:30", "Payrolls"),
    event("2026-03-11T12:30", "CPI"),
    event("2026-03-18T12:30", "PPI"),
    event("2026-03-18T18:00", "FOMC"),
    event("2026-04-03T12:30", "Payrolls"),
    event("2026-04-10T12:30", "CPI"),
    event("2026-04-14T12:30", "PPI"),
    event("2026-04-29T18:00", "FOMC"),
    event("2026-05-08T12:30", "Payrolls"),
    event("2026-05-12T12:30", "CPI"),
    event("2026-05-13T12:30", "PPI"),
    event("2026-06-05T12:30", "Payrolls"),
    event("2026-06-10T12:30", "CPI"),
    event("2026-06-11T12:30", "PPI"),
    event("2026-06-17T18:00", "FOMC"),
    event("2026-07-02T12:30", "Payrolls"),
    event("2026-07-14T12:30", "CPI"),
    event("2026-07-15T12:30", "PPI"),
    event("2026-07-29T18:00", "FOMC"),
]


def execution_result(
    news_event: Event,
    prediction: int,
    symbol: str,
    info: Any,
) -> dict[str, float | str]:
    bars = rates(symbol, news_event.timestamp)
    pre_index = row_before(bars, news_event.timestamp)
    release_index = row_before(bars, news_event.timestamp + 60)
    if pre_index is None or release_index is None:
        raise RuntimeError(f"No execution bars for {news_event.time_utc}.")

    pre = bars[pre_index]
    release = bars[release_index]
    point = float(info.point)
    pip = point * (10.0 if int(info.digits) in {3, 5} else 1.0)
    contract = float(info.trade_contract_size or 100.0)
    pre_spread = max(float(pre["spread"]) * point, point)
    release_spread = max(float(release["spread"]) * point, point)

    if prediction == 1:
        direction = "UP"
        entry = float(pre["close"]) + pre_spread
        exit_price = float(release["close"])
        signed_move = exit_price - entry
    else:
        direction = "DOWN"
        entry = float(pre["close"])
        exit_price = float(release["close"]) + release_spread
        signed_move = entry - exit_price

    net_pips = signed_move / pip
    raw_pnl = signed_move * contract * FIXED_LOT
    pnl = max(raw_pnl, -START_BALANCE_USD)
    margin = contract * entry * FIXED_LOT / LEVERAGE
    return {
        "direction": direction,
        "entry": round(entry, int(info.digits)),
        "exit": round(exit_price, int(info.digits)),
        "net_pips": round(net_pips, 1),
        "pnl_usd": round(pnl, 2),
        "raw_pnl_usd": round(raw_pnl, 2),
        "margin_required_usd": round(margin, 2),
        "result": "WIN" if pnl > 0 else "LOSS" if pnl < 0 else "FLAT",
    }


def aggregate(rows: list[dict[str, Any]]) -> dict[str, Any]:
    correct = sum(bool(row["correct"]) for row in rows)
    wins = sum(row["result"] == "WIN" for row in rows)
    gross_profit = sum(max(float(row["pnl_usd"]), 0.0) for row in rows)
    gross_loss = abs(sum(min(float(row["pnl_usd"]), 0.0) for row in rows))
    return {
        "events": len(rows),
        "direction_correct": correct,
        "direction_accuracy_pct": round(correct / len(rows) * 100.0, 2),
        "execution_wins": wins,
        "execution_win_rate_pct": round(wins / len(rows) * 100.0, 2),
        "net_pips": round(sum(float(row["net_pips"]) for row in rows), 1),
        "net_pnl_usd": round(sum(float(row["pnl_usd"]) for row in rows), 2),
        "average_pnl_per_event_usd": round(
            sum(float(row["pnl_usd"]) for row in rows) / len(rows), 2
        ),
        "profit_factor": (
            round(gross_profit / gross_loss, 2) if gross_loss else None
        ),
    }


def main() -> int:
    load_env_file()
    path = os.getenv("MT5_PATH", "").strip()
    initialized = mt5.initialize(path=path) if path else mt5.initialize()
    if not initialized:
        raise RuntimeError(f"MT5 initialization failed: {mt5.last_error()}")

    try:
        xau_symbol = discover_xau_symbol(os.getenv("XAU_SYMBOL", "XAUUSD"))
        dxy_symbol = "DXY"
        if not mt5.symbol_select(dxy_symbol, True):
            raise RuntimeError("DXY is unavailable on the connected account.")
        info = mt5.symbol_info(xau_symbol)
        if info is None:
            raise RuntimeError(f"No symbol information for {xau_symbol}.")

        train = collect(TRAIN_EVENTS, xau_symbol, dxy_symbol)
        test = collect(TEST_EVENTS, xau_symbol, dxy_symbol)
        if len(train) != len(TRAIN_EVENTS) or not test:
            raise RuntimeError(
                "Incomplete history: "
                f"train={len(train)}/{len(TRAIN_EVENTS)}, "
                f"test={len(test)}/{len(TEST_EVENTS)}."
            )
        available_test_times = {
            item["event"].time_utc for item in test
        }
        unavailable_events = [
            {
                "event_time_utc": item.time_utc,
                "event": item.name,
                "status": "NO_MARKET_DATA",
            }
            for item in TEST_EVENTS
            if item.time_utc not in available_test_times
        ]

        x_train = np.array([item["features"] for item in train], dtype=float)
        y_train = np.array([item["label"] for item in train], dtype=int)
        x_test = np.array([item["features"] for item in test], dtype=float)
        y_test = np.array([item["label"] for item in test], dtype=int)
        model = make_pipeline(
            StandardScaler(),
            LogisticRegression(
                C=0.5,
                class_weight="balanced",
                max_iter=2_000,
                random_state=42,
            ),
        )
        model.fit(x_train, y_train)
        probabilities = model.predict_proba(x_test)[:, 1]
        predictions = (probabilities >= 0.5).astype(int)

        rows: list[dict[str, Any]] = []
        for item, probability, prediction in zip(
            test, probabilities, predictions, strict=True
        ):
            news_event = item["event"]
            execution = execution_result(
                news_event, int(prediction), xau_symbol, info
            )
            actual = "UP" if item["label"] == 1 else "DOWN"
            rows.append(
                {
                    "event_time_utc": news_event.time_utc,
                    "event": news_event.name,
                    "prediction": execution["direction"],
                    "raw_up_probability_pct": round(float(probability) * 100.0, 2),
                    "actual_direction_60s": actual,
                    "correct": bool(prediction == item["label"]),
                    "actual_bid_move_usd": round(
                        float(item["move_60s_usd"]), 2
                    ),
                    **execution,
                }
            )

        grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for row in rows:
            grouped[str(row["event"])].append(row)

        report = {
            "method": {
                "training_window": "2024-07-31 through 2025-07-16",
                "test_window": "2025-07-30 through 2026-07-29",
                "training_events": len(train),
                "test_events": len(test),
                "scheduled_test_events": len(TEST_EVENTS),
                "unavailable_test_events": len(unavailable_events),
                "model": "frozen standardized balanced logistic regression, C=0.5",
                "features_cutoff": "strictly before T-30 minutes",
                "direction_target": "pre-release close to first M1 release close",
                "execution": (
                    "Predicted-direction market entry one minute before release, "
                    "exit after first release M1 candle, recorded MT5 spread."
                ),
                "account_per_event_usd": START_BALANCE_USD,
                "fixed_lot": FIXED_LOT,
                "leverage": LEVERAGE,
                "gold_pip_size": float(info.point),
                "loss_cap": (
                    "Each independent event is capped at -$100. Intrabar stop-out "
                    "and unrecorded tick slippage cannot be reconstructed from M1 bars."
                ),
            },
            "overall": {
                **aggregate(rows),
                "brier_score": round(
                    brier_score_loss(y_test, probabilities), 4
                ),
                "sklearn_accuracy_pct": round(
                    accuracy_score(y_test, predictions) * 100.0, 2
                ),
            },
            "by_event": {
                name: aggregate(event_rows)
                for name, event_rows in sorted(grouped.items())
            },
            "unavailable_events": unavailable_events,
            "predictions": rows,
        }
        REPORT_JSON.write_text(json.dumps(report, indent=2), encoding="utf-8")
        with REPORT_CSV.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)

        print(json.dumps(report, indent=2))
        return 0
    finally:
        mt5.shutdown()


if __name__ == "__main__":
    raise SystemExit(main())
