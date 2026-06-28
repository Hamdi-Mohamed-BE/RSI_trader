from __future__ import annotations

import argparse
from datetime import datetime, timedelta
import json
from pathlib import Path
import sys
from typing import Any

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.mt5_client import MT5Client
from app.strategy_engine import detect_bias


FOREX_CURRENCIES = {"AUD", "CAD", "CHF", "EUR", "GBP", "JPY", "NZD", "USD"}


def is_forex(symbol: str) -> bool:
    value = symbol.upper()
    return len(value) == 6 and value[:3] in FOREX_CURRENCIES and value[3:] in FOREX_CURRENCIES


def direction_matches(direction: str, bias: str) -> bool:
    return (direction == "BUY" and bias == "bullish") or (direction == "SELL" and bias == "bearish")


def direction_opposes(direction: str, bias: str) -> bool:
    return (direction == "BUY" and bias == "bearish") or (direction == "SELL" and bias == "bullish")


def main() -> None:
    parser = argparse.ArgumentParser(description="Apply the live forex H1/H4/D1 agreement rule to saved backtest rows.")
    parser.add_argument("trade_csv")
    parser.add_argument("--output", default=None)
    args = parser.parse_args()

    source = Path(args.trade_csv).expanduser().resolve()
    frame = pd.read_csv(source)
    frame["opened_at"] = pd.to_datetime(frame["opened_at"], errors="coerce")
    frame = frame.dropna(subset=["opened_at"])
    output = Path(args.output).resolve() if args.output else source.with_name(f"{source.stem}_htf_filtered.csv")

    forex_symbols = sorted(symbol for symbol in frame["symbol"].astype(str).str.upper().unique() if is_forex(symbol))
    start = frame["opened_at"].min().to_pydatetime() - timedelta(days=760)
    end = frame["opened_at"].max().to_pydatetime() + timedelta(days=2)
    client = MT5Client()
    histories: dict[tuple[str, str], pd.DataFrame] = {}
    availability: list[dict[str, Any]] = []
    for symbol in forex_symbols:
        for timeframe in ("H1", "H4", "D1"):
            candles = client.fetch_candles(symbol, timeframe, start, end, max_bars=200000)
            count = 0 if candles is None else len(candles)
            availability.append({"symbol": symbol, "timeframe": timeframe, "candles": count})
            if candles is not None and count >= 80:
                history = candles.copy()
                history["time"] = pd.to_datetime(history["time"])
                histories[(symbol, timeframe)] = history.sort_values("time").reset_index(drop=True)
    client.shutdown()

    decisions: dict[tuple[str, str, str], tuple[bool, dict[str, str], str]] = {}
    unique = frame[["symbol", "opened_at", "direction"]].drop_duplicates()
    for row in unique.to_dict(orient="records"):
        symbol = str(row["symbol"]).upper()
        opened_at = pd.Timestamp(row["opened_at"]).to_pydatetime()
        direction = str(row["direction"]).upper()
        key = (symbol, opened_at.isoformat(), direction)
        if not is_forex(symbol):
            decisions[key] = (True, {}, "not_forex")
            continue
        biases: dict[str, str] = {}
        for timeframe in ("H1", "H4", "D1"):
            history = histories.get((symbol, timeframe))
            context = history[history["time"] <= opened_at] if history is not None else pd.DataFrame()
            biases[timeframe] = detect_bias(context.tail(1000), timeframe) if len(context) >= 80 else "unavailable"
        unavailable = any(value == "unavailable" for value in biases.values())
        align = sum(direction_matches(direction, value) for value in biases.values())
        oppose = sum(direction_opposes(direction, value) for value in biases.values())
        passed = not unavailable and align >= 2 and oppose == 0
        reason = "passed" if passed else f"align={align}, oppose={oppose}, unavailable={unavailable}"
        decisions[key] = (passed, biases, reason)

    passed_values: list[bool] = []
    bias_values: list[str] = []
    reason_values: list[str] = []
    for row in frame.to_dict(orient="records"):
        key = (
            str(row["symbol"]).upper(),
            pd.Timestamp(row["opened_at"]).to_pydatetime().isoformat(),
            str(row["direction"]).upper(),
        )
        passed, biases, reason = decisions[key]
        passed_values.append(passed)
        bias_values.append(json.dumps(biases, sort_keys=True))
        reason_values.append(reason)
    frame["htf_agreement"] = passed_values
    frame["htf_biases"] = bias_values
    frame["htf_reason"] = reason_values
    filtered = frame[frame["htf_agreement"]].copy()
    filtered.to_csv(output, index=False)

    report = {
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "source": str(source),
        "output": str(output),
        "input_rows": int(len(frame)),
        "kept_rows": int(len(filtered)),
        "blocked_rows": int(len(frame) - len(filtered)),
        "unique_entry_decisions": len(decisions),
        "availability": availability,
    }
    report_path = output.with_suffix(".report.json")
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
