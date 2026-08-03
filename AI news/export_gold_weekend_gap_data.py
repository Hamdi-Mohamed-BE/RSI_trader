from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

import MetaTrader5 as mt5


ROOT = Path(__file__).resolve().parent
DEFAULT_OUTPUT = ROOT / "data" / "gold-weekend-gaps" / "xauusd-m1-2026-05-01-2026-08-02.json"


def _discover_gold_symbol() -> str:
    candidates = []
    for symbol in mt5.symbols_get() or []:
        name = symbol.name.upper()
        description = (symbol.description or "").upper()
        if "XAUUSD" not in name and not ("GOLD" in description and "FUTURE" not in description):
            continue
        score = 0
        if name == "XAUUSD":
            score += 100
        if name.startswith("XAUUSD"):
            score += 50
        if "SPOT" in description or "GOLD VS US DOLLAR" in description:
            score += 20
        candidates.append((score, symbol.name))
    if not candidates:
        raise RuntimeError("No broker gold symbol was found.")
    return max(candidates)[1]


def run(start: datetime, end: datetime, output: Path) -> Path:
    if not mt5.initialize():
        raise RuntimeError(f"MT5 initialization failed: {mt5.last_error()}")
    try:
        symbol = _discover_gold_symbol()
        if not mt5.symbol_select(symbol, True):
            raise RuntimeError(f"Could not select {symbol}: {mt5.last_error()}")
        rates = mt5.copy_rates_range(symbol, mt5.TIMEFRAME_M1, start, end)
        if rates is None or len(rates) < 1_000:
            raise RuntimeError(f"Incomplete M1 history for {symbol}: {mt5.last_error()}")
        rows = [
            {
                "time": int(row["time"]),
                "open": float(row["open"]),
                "high": float(row["high"]),
                "low": float(row["low"]),
                "close": float(row["close"]),
                "tick_volume": int(row["tick_volume"]),
                "spread": int(row["spread"]),
            }
            for row in rates
        ]
        terminal = mt5.terminal_info()
        account = mt5.account_info()
        payload = {
            "symbol": symbol,
            "description": (mt5.symbol_info(symbol).description if mt5.symbol_info(symbol) else ""),
            "server": getattr(account, "server", None),
            "terminal_company": getattr(terminal, "company", None),
            "start_utc": start.isoformat(),
            "end_utc": end.isoformat(),
            "rows": rows,
        }
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(payload), encoding="utf-8")
        return output
    finally:
        mt5.shutdown()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--start", default="2026-05-01T00:00:00+00:00")
    parser.add_argument("--end", default="2026-08-02T00:00:00+00:00")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    path = run(
        datetime.fromisoformat(args.start).astimezone(timezone.utc),
        datetime.fromisoformat(args.end).astimezone(timezone.utc),
        args.output,
    )
    print(path)
