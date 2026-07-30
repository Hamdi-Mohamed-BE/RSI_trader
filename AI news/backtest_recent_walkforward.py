from __future__ import annotations

import csv
import json
from collections import defaultdict
from datetime import date, datetime
from pathlib import Path

import numpy as np
from sklearn.ensemble import ExtraTreesClassifier

from news_core import (
    DATA_DIR,
    ROOT,
    annual_spreads,
    build_samples,
    complete_sides,
    load_day,
    nearest,
)


START_DATE = date(2026, 5, 30)
END_DATE = date(2026, 7, 30)
LEAD_MINUTES = 30
FEATURE_COUNT = 18
CONFIDENCE_THRESHOLD = 0.60
GOLD_PIP_SIZE = 0.01
OUTPUT_JSON = ROOT / "recent_2m_walkforward.json"
OUTPUT_CSV = ROOT / "recent_2m_walkforward.csv"
OUTPUT_MD = ROOT / "RECENT_2M_WALKFORWARD.md"


def model() -> ExtraTreesClassifier:
    return ExtraTreesClassifier(
        n_estimators=500,
        min_samples_leaf=8,
        max_features=0.75,
        class_weight="balanced",
        random_state=42,
        n_jobs=-1,
    )


def executable_pips(
    row: dict,
    prediction: str,
    bias: str,
    spread_by_year: dict[int, float],
) -> dict:
    release = row["release_utc"]
    day = release[:10]
    year = int(day[:4])
    bid, ask, imputed = complete_sides(
        load_day(day, "bid"),
        load_day(day, "ask"),
        spread_by_year[year],
    )
    release_ms = int(datetime.fromisoformat(release).timestamp() * 1000)
    before_bid = nearest(bid, release_ms - 60_000)
    before_ask = nearest(ask, release_ms - 60_000)
    release_bid = nearest(bid, release_ms)
    release_ask = nearest(ask, release_ms)
    if not all((before_bid, before_ask, release_bid, release_ask)):
        raise RuntimeError(f"Missing executable prices for {release}")

    before_mid = (before_bid["close"] + before_ask["close"]) / 2
    release_mid = (release_bid["close"] + release_ask["close"]) / 2
    actual_move_pips = (release_mid - before_mid) / GOLD_PIP_SIZE
    range_pips = (release_bid["high"] - release_ask["low"]) / GOLD_PIP_SIZE
    buy_pips = (release_bid["close"] - before_ask["close"]) / GOLD_PIP_SIZE
    sell_pips = (before_bid["close"] - release_ask["close"]) / GOLD_PIP_SIZE
    if prediction == "BUY":
        pnl_pips = buy_pips
        entry = before_ask["close"]
        exit_price = release_bid["close"]
    elif prediction == "SELL":
        pnl_pips = sell_pips
        entry = before_bid["close"]
        exit_price = release_ask["close"]
    else:
        pnl_pips = 0.0
        entry = before_mid
        exit_price = release_mid
    return {
        "entry": round(float(entry), 3),
        "exit": round(float(exit_price), 3),
        "actual_move_pips": round(float(actual_move_pips), 1),
        "release_range_pips": round(float(range_pips), 1),
        "captured_or_lost_pips": round(float(pnl_pips), 1),
        "bias_hypothetical_pips": round(
            float(buy_pips if bias == "BUY" else sell_pips),
            1,
        ),
        "spread_imputed": imputed,
    }


def run() -> dict:
    rows, audit = build_samples(LEAD_MINUTES)
    clear = [row for row in rows if row["target"] != "UNCERTAIN"]
    test = [
        row
        for row in rows
        if START_DATE <= date.fromisoformat(row["release_utc"][:10]) < END_DATE
    ]
    days = sorted({row["release_utc"][:10] for row in rows})
    spreads = annual_spreads(days)
    results = []

    for row in test:
        event_date = date.fromisoformat(row["release_utc"][:10])
        training = [
            item
            for item in clear
            if date.fromisoformat(item["release_utc"][:10]) < event_date
        ]
        x_train = np.asarray(
            [item["features"][:FEATURE_COUNT] for item in training],
            dtype=float,
        )
        y_train = np.asarray([item["target"] for item in training])
        fitted = model().fit(x_train, y_train)
        probabilities = fitted.predict_proba(
            np.asarray([row["features"][:FEATURE_COUNT]], dtype=float)
        )[0]
        probability_map = {
            label: float(value)
            for label, value in zip(fitted.classes_, probabilities)
        }
        bias = "BUY" if probability_map.get("BUY", 0) >= probability_map.get("SELL", 0) else "SELL"
        confidence = max(probability_map.get("BUY", 0), probability_map.get("SELL", 0))
        prediction = bias if confidence >= CONFIDENCE_THRESHOLD else "NO TRADE"
        execution = executable_pips(row, prediction, bias, spreads)
        results.append(
            {
                "date": row["release_utc"][:10],
                "release_utc": row["release_utc"],
                "event": row["event"],
                "training_samples": len(training),
                "prediction": prediction,
                "model_bias": bias,
                "confidence_pct": round(100 * confidence, 2),
                "actual_outcome": row["target"],
                "correct_when_called": (
                    prediction == row["target"]
                    if prediction in {"BUY", "SELL"}
                    else None
                ),
                **execution,
            }
        )

    called = [row for row in results if row["prediction"] in {"BUY", "SELL"}]
    directional_called = [
        row for row in called if row["actual_outcome"] in {"BUY", "SELL"}
    ]
    wins = [row for row in called if row["captured_or_lost_pips"] > 0]
    losses = [row for row in called if row["captured_or_lost_pips"] < 0]
    net_pips = sum(row["captured_or_lost_pips"] for row in called)
    bias_net_pips = sum(row["bias_hypothetical_pips"] for row in results)
    gross_win = sum(row["captured_or_lost_pips"] for row in wins)
    gross_loss = -sum(row["captured_or_lost_pips"] for row in losses)
    report = {
        "methodology": {
            "window": f"{START_DATE.isoformat()} through {END_DATE.isoformat()} exclusive",
            "lead_minutes": LEAD_MINUTES,
            "walk_forward": True,
            "training_rule": "Each model sees only clear releases dated before the event.",
            "feature_profile": "legacy stable 18-feature profile",
            "confidence_threshold": CONFIDENCE_THRESHOLD,
            "execution": (
                "Enter at the final pre-release M1 bid/ask close and exit at the release M1 "
                "bid/ask close. One XAUUSD pip is defined as $0.01."
            ),
            "no_trade_pips": 0,
        },
        "audit": audit,
        "summary": {
            "events": len(results),
            "called_trades": len(called),
            "no_trades": len(results) - len(called),
            "uncertain_actual_outcomes": sum(
                row["actual_outcome"] == "UNCERTAIN" for row in results
            ),
            "wins": len(wins),
            "losses": len(losses),
            "win_rate_pct": round(100 * len(wins) / len(called), 2) if called else 0.0,
            "direction_accuracy_pct": (
                round(
                    100
                    * sum(row["correct_when_called"] is True for row in directional_called)
                    / len(directional_called),
                    2,
                )
                if directional_called
                else 0.0
            ),
            "net_pips": round(net_pips, 1),
            "raw_bias_net_pips_without_confidence_filter": round(bias_net_pips, 1),
            "gross_win_pips": round(gross_win, 1),
            "gross_loss_pips": round(gross_loss, 1),
            "profit_factor_pips": (
                round(gross_win / gross_loss, 3)
                if gross_loss > 0
                else None
            ),
        },
        "events": results,
    }
    OUTPUT_JSON.write_text(json.dumps(report, indent=2), encoding="utf-8")
    with OUTPUT_CSV.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(results[0]))
        writer.writeheader()
        writer.writerows(results)

    lines = [
        "# Recent Two-Month Walk-Forward",
        "",
        "Every prediction was generated by a model trained only on earlier releases.",
        "",
        "| Date | Event | Prediction | Bias | Confidence | Actual | Move | Captured/lost | Raw-bias result |",
        "|---|---|---|---|---:|---|---:|---:|---:|",
    ]
    for row in results:
        lines.append(
            f"| {row['date']} | {row['event']} | {row['prediction']} | {row['model_bias']} | "
            f"{row['confidence_pct']:.2f}% | {row['actual_outcome']} | "
            f"{row['actual_move_pips']:+.1f} pips | "
            f"{row['captured_or_lost_pips']:+.1f} pips | "
            f"{row['bias_hypothetical_pips']:+.1f} pips |"
        )
    summary = report["summary"]
    lines.extend(
        [
            "",
            f"Called {summary['called_trades']} of {summary['events']} events; "
            f"win rate **{summary['win_rate_pct']:.2f}%**; net "
            f"**{summary['net_pips']:+.1f} pips**.",
            "",
            "A `NO TRADE` prediction records zero captured pips. Move is the signed midpoint "
            "change; captured/lost pips include bid/ask spread.",
        ]
    )
    OUTPUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return report


if __name__ == "__main__":
    print(json.dumps(run(), indent=2))
