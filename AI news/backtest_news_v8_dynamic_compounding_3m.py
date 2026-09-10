from __future__ import annotations

import csv
import json
import math
import os
from dataclasses import asdict
from datetime import date

import MetaTrader5 as mt5
import numpy as np

from backtest_news_v8_move_execution_3m import (
    DIRECTION_RESULTS,
    RECENT_START,
    ExecutionConfig,
    _event_ticks,
    _simulate_event,
    _utc,
)
from news_core import ROOT


END = date(2026, 9, 10)
STARTING_BALANCE = 100.0
LOT_PER_100_USD = 0.06
BALANCE_STEP_USD = 100.0
OUTPUT_JSON = ROOT / "news_v8_dynamic_006_per_100_3m_results.json"
OUTPUT_CSV = ROOT / "news_v8_dynamic_006_per_100_3m_trades.csv"
OUTPUT_MD = ROOT / "NEWS_V8_DYNAMIC_006_PER_100_3M_RESULTS.md"

CONFIG = ExecutionConfig(
    entry_offset_seconds=-5,
    stop_usd=4.0,
    take_profit_usd=None,
    trailing_trigger_usd=None,
    trailing_distance_usd=None,
    exit_after_seconds=900,
)


def _dynamic_lot(balance: float, info: object) -> tuple[int, float]:
    tranches = math.floor((balance + 1e-9) / BALANCE_STEP_USD)
    if tranches < 1:
        return 0, 0.0
    requested = tranches * LOT_PER_100_USD
    step = float(info.volume_step)
    normalized = math.floor((requested + 1e-12) / step) * step
    normalized = min(normalized, float(info.volume_max))
    if normalized < float(info.volume_min):
        return tranches, 0.0
    return tranches, round(normalized, 8)


def _metrics(trades: list[dict], equity_values: list[float]) -> dict:
    executed = [row for row in trades if row["status"] == "EXECUTED"]
    wins = [row for row in executed if row["pnl_usd"] > 0]
    losses = [row for row in executed if row["pnl_usd"] < 0]
    gross_profit = sum(float(row["pnl_usd"]) for row in wins)
    gross_loss = -sum(float(row["pnl_usd"]) for row in losses)
    ending = float(trades[-1]["balance_after_usd"]) if trades else STARTING_BALANCE

    realized = np.asarray(
        [STARTING_BALANCE] + [float(row["balance_after_usd"]) for row in trades],
        dtype=float,
    )
    realized_peaks = np.maximum.accumulate(realized)
    realized_dd = realized_peaks - realized
    realized_pct = np.divide(
        realized_dd,
        realized_peaks,
        out=np.zeros_like(realized_dd),
        where=realized_peaks > 0,
    )

    equity = np.asarray(equity_values, dtype=float)
    equity_peaks = np.maximum.accumulate(equity)
    equity_dd = equity_peaks - equity
    equity_pct = np.divide(
        equity_dd,
        equity_peaks,
        out=np.zeros_like(equity_dd),
        where=equity_peaks > 0,
    )
    return {
        "starting_balance_usd": STARTING_BALANCE,
        "ending_balance_usd": round(ending, 2),
        "net_profit_usd": round(ending - STARTING_BALANCE, 2),
        "executed_trades": len(executed),
        "wins": len(wins),
        "losses": len(losses),
        "win_rate_pct": round(100 * len(wins) / len(executed), 2),
        "gross_profit_usd": round(gross_profit, 2),
        "gross_loss_usd": round(gross_loss, 2),
        "profit_factor": round(gross_profit / gross_loss, 2),
        "maximum_realized_drawdown_usd": round(float(np.max(realized_dd)), 2),
        "maximum_realized_drawdown_pct": round(100 * float(np.max(realized_pct)), 2),
        "maximum_tick_equity_drawdown_usd": round(float(np.max(equity_dd)), 2),
        "maximum_tick_equity_drawdown_pct": round(100 * float(np.max(equity_pct)), 2),
        "minimum_tick_equity_usd": round(float(np.min(equity)), 2),
        "account_survived": ending > 0
        and all(row["status"] == "EXECUTED" for row in trades),
    }


def _markdown(report: dict) -> str:
    metrics = report["metrics"]
    lines = [
        "# Gold News V8 - Dynamic 0.06 Lot per $100, Three-Month Replay",
        "",
        "> Before every event: lot = floor(balance / $100) x 0.06. Trading stops below $100. The frozen execution is T-5 seconds, $4 gold-price stop, no take profit, no trailing, and T+15-minute exit.",
        "",
        "## Summary",
        "",
        "| Measure | Result |",
        "|---|---:|",
        f"| Starting balance | ${metrics['starting_balance_usd']:.2f} |",
        f"| Ending balance | ${metrics['ending_balance_usd']:.2f} |",
        f"| Net P/L | ${metrics['net_profit_usd']:+.2f} |",
        f"| Wins / losses | {metrics['wins']} / {metrics['losses']} |",
        f"| Win rate | {metrics['win_rate_pct']:.2f}% |",
        f"| Profit factor | {metrics['profit_factor']:.2f} |",
        f"| Maximum realized drawdown | ${metrics['maximum_realized_drawdown_usd']:.2f} ({metrics['maximum_realized_drawdown_pct']:.2f}%) |",
        f"| Maximum tick-equity drawdown | ${metrics['maximum_tick_equity_drawdown_usd']:.2f} ({metrics['maximum_tick_equity_drawdown_pct']:.2f}%) |",
        f"| Minimum tick equity | ${metrics['minimum_tick_equity_usd']:.2f} |",
        "",
        "## Trades",
        "",
        "| Date | Event | Call | Balance before | $100 units | Lot | Captured | Exit | P/L | Balance after |",
        "|---|---|---|---:|---:|---:|---:|---|---:|---:|",
    ]
    for row in report["trades"]:
        captured = (
            f"{row['captured_move_usd']:+.3f} USD"
            if "captured_move_usd" in row
            else "-"
        )
        lines.append(
            f"| {row['release_utc'][:10]} | {row['event']} | {row['direction']} | "
            f"${row['balance_before_usd']:.2f} | {row['balance_units']} | "
            f"{row['lot']:.2f} | {captured} | {row.get('exit_reason', row['status'])} | "
            f"${row['pnl_usd']:+.2f} | ${row['balance_after_usd']:.2f} |"
        )
    lines.extend(
        [
            "",
            "## Important",
            "",
            "- This is extreme compounding. A normal $4 stop is about $24 per $100 tranche before spread and slippage.",
            "- Historical MT5 bid/ask ticks include observed spread and tick-gap slippage. Commission, latency, rejection, and future broker rules are unavailable.",
            "- The execution configuration was selected using June 10-July 29, so the full three-month result is partly in-sample and not a clean prospective estimate.",
        ]
    )
    return "\n".join(lines) + "\n"


def run() -> dict:
    direction = json.loads(DIRECTION_RESULTS.read_text(encoding="utf-8"))
    events = [
        row
        for row in direction["events"]
        if RECENT_START <= date.fromisoformat(row["release_utc"][:10]) < END
    ]
    terminal = os.getenv("MT5_PATH", r"C:\Program Files\MetaTrader 5\terminal64.exe")
    if not mt5.initialize(path=terminal):
        raise RuntimeError(f"Could not initialize MT5: {mt5.last_error()}")
    try:
        account = mt5.account_info()
        info = mt5.symbol_info("XAUUSD")
        if account is None or info is None or not mt5.symbol_select("XAUUSD", True):
            raise RuntimeError("The connected MT5 account does not expose XAUUSD.")
        ticks_by_release = {
            event["release_utc"]: _event_ticks("XAUUSD", _utc(event["release_utc"]))
            for event in events
        }

        balance = STARTING_BALANCE
        trades = []
        equity_values = [STARTING_BALANCE]
        for event in events:
            units, lot = _dynamic_lot(balance, info)
            before = balance
            if lot <= 0:
                result = {"status": "BALANCE_BELOW_100", "pnl_usd": 0.0, "lot": 0.0}
            else:
                result = _simulate_event(
                    ticks_by_release[event["release_utc"]],
                    release=_utc(event["release_utc"]),
                    direction=event["prediction"],
                    config=CONFIG,
                    balance=balance,
                    info=info,
                    leverage=int(account.leverage),
                    lot=lot,
                    include_path=True,
                )
            balance += float(result["pnl_usd"])
            if "equity_path" in result:
                equity_values.extend(result.pop("equity_path").tolist())
            trades.append(
                {
                    "release_utc": event["release_utc"],
                    "event": event["event"],
                    "direction": event["prediction"],
                    "actual_direction": event["actual"],
                    "balance_units": units,
                    "balance_before_usd": round(before, 2),
                    **result,
                    "balance_after_usd": round(balance, 2),
                }
            )
    finally:
        mt5.shutdown()

    report = {
        "window": {"start": RECENT_START.isoformat(), "end_exclusive": END.isoformat()},
        "broker": {
            "server": account.server,
            "symbol": "XAUUSD",
            "leverage": int(account.leverage),
            "contract_size": float(info.trade_contract_size),
            "volume_step": float(info.volume_step),
            "volume_max": float(info.volume_max),
        },
        "position_sizing": {
            "formula": "floor(balance / 100) * 0.06 lot",
            "lot_per_100_usd": LOT_PER_100_USD,
            "balance_step_usd": BALANCE_STEP_USD,
            "below_100_usd": "do not trade",
        },
        "execution_configuration": asdict(CONFIG),
        "metrics": _metrics(trades, equity_values),
        "trades": trades,
    }
    OUTPUT_JSON.write_text(json.dumps(report, indent=2), encoding="utf-8")
    with OUTPUT_CSV.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(trades[0]))
        writer.writeheader()
        writer.writerows(trades)
    OUTPUT_MD.write_text(_markdown(report), encoding="utf-8")
    return report


if __name__ == "__main__":
    print(json.dumps(run(), indent=2))
