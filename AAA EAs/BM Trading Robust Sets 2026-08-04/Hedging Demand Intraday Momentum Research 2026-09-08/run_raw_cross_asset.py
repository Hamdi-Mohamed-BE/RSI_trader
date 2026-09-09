from __future__ import annotations

import csv
import importlib.util
import json
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parent
RUNNER_PATH = ROOT / "run_raw_paper_test.py"


def load_runner():
    spec = importlib.util.spec_from_file_location("raw_intraday_runner", RUNNER_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError("Unable to load the raw MT5 runner")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


RUNNER = load_runner()

# The paper states these U.S.-listed futures hours in Eastern time.
# GBPJPY is explicitly labelled an extension because it is not one of the
# individual currency futures in the source paper.
MARKETS = [
    {"symbol": "XAUUSD", "market": "Gold", "open": 8 + 20 / 60, "close": 13.5, "paper_direct": True, "monday": False, "friday": True},
    {"symbol": "XAGUSD", "market": "Silver", "open": 8 + 25 / 60, "close": 13 + 25 / 60, "paper_direct": True, "monday": True, "friday": True},
    {"symbol": "EURUSD", "market": "Euro FX", "open": 7 + 20 / 60, "close": 14.0, "paper_direct": True, "monday": True, "friday": True},
    {"symbol": "GBPUSD", "market": "British pound", "open": 7 + 20 / 60, "close": 14.0, "paper_direct": True, "monday": True, "friday": True},
    {"symbol": "GBPJPY", "market": "GBPJPY cross extension", "open": 7 + 20 / 60, "close": 14.0, "paper_direct": False, "monday": True, "friday": True},
    {"symbol": "US30", "market": "Dow Jones", "open": 9.5, "close": 16.0, "paper_direct": True, "monday": False, "friday": False},
]


def compact(row: dict) -> dict:
    return {key: value for key, value in row.items() if key != "deals"}


def main() -> None:
    RUNNER.prepare()
    periods = [
        ("3y", "2023.09.01", "2026.09.01"),
        ("1y", "2025.09.01", "2026.09.01"),
    ]
    rows: list[dict] = []
    sequence = 200
    for period, start, end in periods:
        for market in MARKETS:
            sequence += 1
            signal_hour = market["close"] - 0.5
            row = RUNNER.run_case(
                "ROD-main",
                0,
                period,
                start,
                end,
                sequence,
                symbol=market["symbol"],
                cash_open=market["open"],
                signal_hour=signal_hour,
                cash_close=market["close"],
                trade_monday=market["monday"],
                trade_friday=market["friday"],
            )
            row["symbol"] = market["symbol"]
            row["market"] = market["market"]
            row["paper_direct"] = market["paper_direct"]
            row["session_open_et"] = market["open"]
            row["signal_et"] = signal_hour
            row["session_close_et"] = market["close"]
            rows.append(row)

    audit = {
        "strategy": "Last-30-Minute Hedging Momentum — raw cross-asset check",
        "paper": "Baltussen, Da, Lammers and Martens (2021), Journal of Financial Economics",
        "paper_url": "https://academicweb.nd.edu/~zda/intramom.pdf",
        "rule": "At 30 minutes before the paper-defined market close, trade in the sign of the return from the prior market close; exit at the close.",
        "risk": "1% equity at a 10x M15 ATR catastrophic stop; no optimization, TP, management, or filters.",
        "costs": "Native MT5 Every Tick, broker spread, commission, swap and random execution delay.",
        "scope_note": "GBPJPY is a cross-rate extension. BTC is excluded because the paper does not define a cash-market close for 24/7 crypto. XAU Monday and US30 Monday/Friday were skipped because this broker does not provide an executable final 30-minute window on those sessions.",
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "rows": [compact(row) for row in rows],
    }
    (ROOT / "raw-cross-asset-audit.json").write_text(json.dumps(audit, indent=2), encoding="utf-8")

    with (ROOT / "raw-cross-asset-results.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow([
            "period", "symbol", "market", "paper_direct", "return_pct", "net_profit",
            "profit_factor", "win_rate_pct", "max_drawdown_pct", "trades", "sharpe",
            "recovery_factor", "expected_payoff", "history_quality",
        ])
        for row in rows:
            writer.writerow([
                row["period"], row["symbol"], row["market"], row["paper_direct"],
                row["return_pct"], row["net_profit"], row["profit_factor"],
                row["win_rate_pct"], row["max_drawdown_pct"], row["trades"],
                row["sharpe"], row["recovery_factor"], row["expected_payoff"],
                row["history_quality"],
            ])
    print(f"SAVED {ROOT / 'raw-cross-asset-audit.json'}", flush=True)


if __name__ == "__main__":
    main()
