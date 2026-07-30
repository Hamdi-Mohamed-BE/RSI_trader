from __future__ import annotations

import csv
import json
import os
from dataclasses import asdict, dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path

import MetaTrader5 as mt5
import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, brier_score_loss
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from xau_m1_buy_stop_grid import discover_xau_symbol, load_env_file


BASE_DIR = Path(__file__).resolve().parent
REPORT_JSON = BASE_DIR / "news_direction_backtest_report.json"
REPORT_CSV = BASE_DIR / "news_direction_predictions.csv"
HISTORY_OFFSET_HOURS = 0


@dataclass(frozen=True)
class Event:
    time_utc: str
    name: str

    @property
    def timestamp(self) -> float:
        value = datetime.fromisoformat(self.time_utc).astimezone(UTC)
        return (value + timedelta(hours=HISTORY_OFFSET_HOURS)).timestamp()


TRAIN_EVENTS = [
    Event("2026-05-08T12:30:00+00:00", "Payrolls"),
    Event("2026-05-12T12:30:00+00:00", "CPI"),
    Event("2026-05-13T12:30:00+00:00", "PPI"),
    Event("2026-05-14T12:30:00+00:00", "Retail sales"),
    Event("2026-05-28T12:30:00+00:00", "GDP / PCE"),
    Event("2026-06-01T14:00:00+00:00", "ISM manufacturing"),
    Event("2026-06-05T12:30:00+00:00", "Payrolls"),
    Event("2026-06-10T12:30:00+00:00", "CPI"),
    Event("2026-06-11T12:30:00+00:00", "PPI"),
    Event("2026-06-17T12:30:00+00:00", "Retail sales"),
    Event("2026-06-17T18:00:00+00:00", "FOMC"),
    Event("2026-06-25T12:30:00+00:00", "GDP / PCE / durable goods"),
]

TEST_EVENTS = [
    Event("2026-07-01T12:15:00+00:00", "ADP"),
    Event("2026-07-01T14:00:00+00:00", "ISM manufacturing"),
    Event("2026-07-02T12:30:00+00:00", "Payrolls"),
    Event("2026-07-06T14:00:00+00:00", "ISM services"),
    Event("2026-07-07T12:30:00+00:00", "Trade balance"),
    Event("2026-07-08T18:00:00+00:00", "FOMC minutes"),
    Event("2026-07-09T12:30:00+00:00", "Jobless claims"),
    Event("2026-07-14T12:30:00+00:00", "CPI"),
    Event("2026-07-15T12:30:00+00:00", "PPI"),
    Event("2026-07-16T12:30:00+00:00", "Retail sales"),
    Event("2026-07-17T14:00:00+00:00", "Consumer sentiment"),
    Event("2026-07-23T12:30:00+00:00", "Jobless claims"),
    Event("2026-07-23T13:45:00+00:00", "Flash PMI"),
    Event("2026-07-27T12:30:00+00:00", "Durable goods"),
    Event("2026-07-28T14:00:00+00:00", "Consumer confidence"),
    Event("2026-07-29T18:00:00+00:00", "FOMC"),
]

FEATURE_NAMES = [
    "xau_return_5m_atr",
    "xau_return_15m_atr",
    "xau_return_30m_atr",
    "dxy_return_5m_atr",
    "dxy_return_15m_atr",
    "dxy_return_30m_atr",
    "xau_range_30m_atr",
    "xau_tick_volume_zscore",
]


def rates(symbol: str, event_timestamp: float) -> list[dict[str, float]]:
    start = datetime.fromtimestamp(event_timestamp - 4 * 3600, tz=UTC)
    end = datetime.fromtimestamp(event_timestamp + 5 * 60, tz=UTC)
    raw = mt5.copy_rates_range(symbol, mt5.TIMEFRAME_M1, start, end)
    if raw is None:
        return []
    return [
        {name: float(row[name]) for name in raw.dtype.names}
        for row in raw
    ]


def row_before(rows: list[dict[str, float]], timestamp: float) -> int | None:
    indexes = [index for index, row in enumerate(rows) if row["time"] < timestamp]
    return indexes[-1] if indexes else None


def atr(rows: list[dict[str, float]], end_index: int, length: int = 14) -> float:
    start = max(0, end_index - length + 1)
    values = [row["high"] - row["low"] for row in rows[start : end_index + 1]]
    return max(float(np.mean(values)), 1e-9)


def feature_row(
    event: Event,
    xau_rows: list[dict[str, float]],
    dxy_rows: list[dict[str, float]],
) -> tuple[list[float], int, float, float] | None:
    event_timestamp = event.timestamp
    cutoff = event_timestamp - 30 * 60
    xau_index = row_before(xau_rows, cutoff)
    dxy_index = row_before(dxy_rows, cutoff)
    event_index = row_before(xau_rows, event_timestamp + 60)
    pre_event_index = row_before(xau_rows, event_timestamp)
    if None in {xau_index, dxy_index, event_index, pre_event_index}:
        return None
    if min(xau_index, dxy_index) < 125:
        return None

    xau_atr = atr(xau_rows, xau_index)
    dxy_atr = atr(dxy_rows, dxy_index)
    xau_close = xau_rows[xau_index]["close"]
    dxy_close = dxy_rows[dxy_index]["close"]

    def normalized_return(
        rows: list[dict[str, float]],
        index: int,
        lookback: int,
        scale: float,
    ) -> float:
        return (rows[index]["close"] - rows[index - lookback]["close"]) / scale

    prior_volume = np.array(
        [row["tick_volume"] for row in xau_rows[xau_index - 120 : xau_index]],
        dtype=float,
    )
    volume_mean = float(prior_volume.mean())
    volume_std = max(float(prior_volume.std()), 1.0)
    volume_zscore = (xau_rows[xau_index]["tick_volume"] - volume_mean) / volume_std
    range_rows = xau_rows[xau_index - 29 : xau_index + 1]
    range_30m = max(row["high"] for row in range_rows) - min(
        row["low"] for row in range_rows
    )

    features = [
        normalized_return(xau_rows, xau_index, 5, xau_atr),
        normalized_return(xau_rows, xau_index, 15, xau_atr),
        normalized_return(xau_rows, xau_index, 30, xau_atr),
        normalized_return(dxy_rows, dxy_index, 5, dxy_atr),
        normalized_return(dxy_rows, dxy_index, 15, dxy_atr),
        normalized_return(dxy_rows, dxy_index, 30, dxy_atr),
        range_30m / xau_atr,
        volume_zscore,
    ]
    pre_price = xau_rows[pre_event_index]["close"]
    post_price = xau_rows[event_index]["close"]
    move = post_price - pre_price
    label = 1 if move > 0 else 0
    return features, label, pre_price, move


def collect(
    events: list[Event],
    xau_symbol: str,
    dxy_symbol: str,
) -> list[dict[str, object]]:
    collected: list[dict[str, object]] = []
    for event in events:
        item = feature_row(
            event,
            rates(xau_symbol, event.timestamp),
            rates(dxy_symbol, event.timestamp),
        )
        if item is None:
            continue
        features, label, pre_price, move = item
        collected.append(
            {
                "event": event,
                "features": features,
                "label": label,
                "pre_price": pre_price,
                "move_60s_usd": move,
            }
        )
    return collected


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

        train = collect(TRAIN_EVENTS, xau_symbol, dxy_symbol)
        test = collect(TEST_EVENTS, xau_symbol, dxy_symbol)
        if len(train) < 6 or not test:
            raise RuntimeError(
                f"Insufficient history: train={len(train)}, test={len(test)}."
            )

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
        up_probabilities = model.predict_proba(x_test)[:, 1]
        predictions = (up_probabilities >= 0.5).astype(int)

        rows: list[dict[str, object]] = []
        for item, probability, prediction in zip(
            test, up_probabilities, predictions, strict=True
        ):
            raw_confidence = max(probability, 1.0 - probability) * 100.0
            capped_confidence = min(raw_confidence, 55.0)
            event = item["event"]
            rows.append(
                {
                    "event_time_utc": event.time_utc,
                    "event": event.name,
                    "prediction": "UP" if prediction == 1 else "DOWN",
                    "raw_up_probability": round(float(probability) * 100.0, 2),
                    "raw_confidence": round(float(raw_confidence), 2),
                    "agent_confidence_capped": round(float(capped_confidence), 2),
                    "agent_action": "NO_TRADE",
                    "actual_direction_60s": "UP" if item["label"] == 1 else "DOWN",
                    "actual_move_60s_usd": round(float(item["move_60s_usd"]), 2),
                    "correct": bool(prediction == item["label"]),
                }
            )

        report = {
            "method": {
                "training_window": "2026-05-08 through 2026-06-25",
                "test_window": "2026-07-01 through 2026-07-29",
                "prediction_cutoff": "T-30 minutes",
                "target": "XAUUSD direction over first 60 seconds",
                "features": FEATURE_NAMES,
                "model": "standardized balanced logistic regression, C=0.5",
                "missing_historical_inputs": [
                    "timestamped consensus snapshots",
                    "timestamped institutional nowcasts",
                    "Treasury yield history",
                    "options skew",
                    "CME gold order book",
                ],
                "confidence_rule": (
                    "Prompt cap of 55% because timestamped consensus is missing."
                ),
            },
            "sample": {
                "training_events_available": len(train),
                "test_events_available": len(test),
            },
            "results": {
                "directional_accuracy_pct": round(
                    accuracy_score(y_test, predictions) * 100.0, 2
                ),
                "correct": int((predictions == y_test).sum()),
                "incorrect": int((predictions != y_test).sum()),
                "brier_score": round(
                    brier_score_loss(y_test, up_probabilities), 4
                ),
                "actionable_predictions": 0,
                "no_trade_predictions": len(test),
            },
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
