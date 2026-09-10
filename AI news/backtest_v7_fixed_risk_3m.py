from __future__ import annotations

import csv
import json
import os
from datetime import datetime, timedelta, timezone

import MetaTrader5 as mt5

from news_core import ROOT


INPUT_PATH = ROOT / "news_v7_full_coverage_results.json"
OUTPUT_JSON = ROOT / "v7_fixed_risk_3m_results.json"
OUTPUT_CSV = ROOT / "v7_fixed_risk_3m_results.csv"
OUTPUT_MD = ROOT / "V7_FIXED_RISK_3M_RESULTS.md"

STARTING_BALANCE = 100.0
LOT = 0.08
STOP_USD_PRICE = 12.0
TARGET_USD_PRICE = 46.0
TRAIL_TRIGGER_R = 2.0
TRAIL_DISTANCE_USD_PRICE = STOP_USD_PRICE
ENTRY_SECONDS_BEFORE = 30
MAX_HOLD_MINUTES = 60


def _utc(value: str) -> datetime:
    return datetime.fromisoformat(value).astimezone(timezone.utc)


def _pnl(info: object, direction: str, entry: float, exit_price: float) -> float:
    move = exit_price - entry if direction == "POSITIVE" else entry - exit_price
    return move / float(info.trade_tick_size) * float(info.trade_tick_value) * LOT


def _margin(info: object, price: float, leverage: int) -> float:
    return float(info.trade_contract_size) * LOT * price / leverage


def _event_ticks(symbol: str, release: datetime):
    start = release - timedelta(seconds=ENTRY_SECONDS_BEFORE + 10)
    end = release + timedelta(minutes=MAX_HOLD_MINUTES)
    ticks = mt5.copy_ticks_range(symbol, start, end, mt5.COPY_TICKS_ALL)
    if ticks is None or len(ticks) < 20:
        raise RuntimeError(
            f"MT5 tick history is incomplete for {release.isoformat()}: {mt5.last_error()}"
        )
    return ticks


def _simulate(
    ticks,
    *,
    release: datetime,
    direction: str,
    info: object,
    balance: float,
    equity_peak: float,
    leverage: int,
    stop_out_pct: float,
) -> dict:
    requested_ms = int(
        (release - timedelta(seconds=ENTRY_SECONDS_BEFORE)).timestamp() * 1000
    )
    eligible = ticks[ticks["time_msc"] >= requested_ms]
    if len(eligible) == 0:
        raise RuntimeError(f"No entry tick at T-{ENTRY_SECONDS_BEFORE}s for {release}.")
    entry_tick = eligible[0]
    entry_bid = float(entry_tick["bid"])
    entry_ask = float(entry_tick["ask"])
    entry = entry_ask if direction == "POSITIVE" else entry_bid
    required_margin = _margin(info, entry, leverage)
    if balance < required_margin:
        return {
            "status": "MARGIN_REJECTED",
            "entry_price": entry,
            "exit_price": None,
            "entry_spread_usd": round(entry_ask - entry_bid, 4),
            "required_margin_usd": round(required_margin, 2),
            "pnl_usd": 0.0,
            "equity_peak_after_usd": round(equity_peak, 2),
            "maximum_equity_drawdown_usd": 0.0,
            "maximum_equity_drawdown_pct": 0.0,
        }

    if direction == "POSITIVE":
        stop = entry - STOP_USD_PRICE
        target = entry + TARGET_USD_PRICE
    else:
        stop = entry + STOP_USD_PRICE
        target = entry - TARGET_USD_PRICE

    active_trail = False
    max_favorable = float("-inf")
    max_adverse = 0.0
    max_equity_drawdown = 0.0
    max_equity_drawdown_pct = 0.0
    exit_reason = "TIME_EXIT_T_PLUS_60"
    exit_tick = eligible[-1]
    exit_price = float(exit_tick["bid"] if direction == "POSITIVE" else exit_tick["ask"])

    for tick in eligible:
        bid = float(tick["bid"])
        ask = float(tick["ask"])
        executable = bid if direction == "POSITIVE" else ask
        favorable = executable - entry if direction == "POSITIVE" else entry - executable
        max_favorable = max(max_favorable, favorable)
        max_adverse = max(max_adverse, -favorable)
        floating_pnl = _pnl(info, direction, entry, executable)
        equity = balance + floating_pnl
        equity_peak = max(equity_peak, equity)
        equity_drawdown = max(0.0, equity_peak - equity)
        max_equity_drawdown = max(max_equity_drawdown, equity_drawdown)
        if equity_peak > 0:
            max_equity_drawdown_pct = max(
                max_equity_drawdown_pct,
                100 * equity_drawdown / equity_peak,
            )

        if (direction == "POSITIVE" and executable >= target) or (
            direction == "NEGATIVE" and executable <= target
        ):
            exit_reason = "TAKE_PROFIT"
            exit_tick = tick
            exit_price = executable
            break

        stop_hit = (
            direction == "POSITIVE" and executable <= stop
        ) or (
            direction == "NEGATIVE" and executable >= stop
        )
        if stop_hit:
            exit_reason = "TRAILING_STOP" if active_trail else "STOP_LOSS"
            exit_tick = tick
            exit_price = executable
            break

        current_margin = _margin(info, (bid + ask) / 2, leverage)
        if balance + floating_pnl <= current_margin * stop_out_pct / 100:
            exit_reason = "BROKER_STOP_OUT"
            exit_tick = tick
            exit_price = executable
            break

        if favorable >= TRAIL_TRIGGER_R * STOP_USD_PRICE:
            active_trail = True
            candidate = (
                executable - TRAIL_DISTANCE_USD_PRICE
                if direction == "POSITIVE"
                else executable + TRAIL_DISTANCE_USD_PRICE
            )
            stop = max(stop, candidate) if direction == "POSITIVE" else min(stop, candidate)

    pnl = _pnl(info, direction, entry, exit_price)
    return {
        "status": "EXECUTED",
        "entry_time_utc": datetime.fromtimestamp(
            int(entry_tick["time_msc"]) / 1000, timezone.utc
        ).isoformat(),
        "exit_time_utc": datetime.fromtimestamp(
            int(exit_tick["time_msc"]) / 1000, timezone.utc
        ).isoformat(),
        "entry_price": round(entry, 3),
        "exit_price": round(exit_price, 3),
        "initial_stop_price": round(
            entry - STOP_USD_PRICE if direction == "POSITIVE" else entry + STOP_USD_PRICE,
            3,
        ),
        "target_price": round(target, 3),
        "final_trailing_stop_price": round(stop, 3) if active_trail else None,
        "trailing_activated": active_trail,
        "exit_reason": exit_reason,
        "entry_spread_usd": round(entry_ask - entry_bid, 4),
        "required_margin_usd": round(required_margin, 2),
        "maximum_favorable_move_usd": round(max(0.0, max_favorable), 3),
        "maximum_adverse_move_usd": round(max_adverse, 3),
        "pnl_usd": round(pnl, 2),
        "equity_peak_after_usd": round(equity_peak, 2),
        "maximum_equity_drawdown_usd": round(max_equity_drawdown, 2),
        "maximum_equity_drawdown_pct": round(max_equity_drawdown_pct, 2),
    }


def _markdown(report: dict) -> str:
    s = report["summary"]
    lines = [
        "# V7 Fixed 0.08-Lot News Replay - Three Months",
        "",
        "> Market entry at T-30 seconds using MT5 bid/ask ticks. $12 initial gold-price stop, $46 target, and $12 trailing distance activated at +$24 (2R). Positions still open at T+60 are closed at the available quote.",
        "",
        "## Summary",
        "",
        "| Measure | Result |",
        "|---|---:|",
        f"| Starting balance | ${s['starting_balance_usd']:.2f} |",
        f"| Ending balance | ${s['ending_balance_usd']:.2f} |",
        f"| Net profit | ${s['net_profit_usd']:+.2f} |",
        f"| Return on start | {s['return_pct']:+.2f}% |",
        f"| Executed trades | {s['executed_trades']} |",
        f"| Wins / losses | {s['wins']} / {s['losses']} |",
        f"| Execution win rate | {s['win_rate_pct']:.2f}% |",
        f"| Profit factor | {s['profit_factor']:.2f} |",
        f"| Maximum realized drawdown | ${s['maximum_realized_drawdown_usd']:.2f} ({s['maximum_realized_drawdown_pct']:.2f}%) |",
        f"| Largest tick-level equity drawdown | ${s['maximum_equity_drawdown_usd']:.2f} |",
        f"| Worst tick-level drawdown percentage | {s['maximum_equity_drawdown_pct']:.2f}% |",
        "",
        "## Trades",
        "",
        "| Date | Event | Direction | Entry | Exit | Exit reason | Trail | P/L | Balance |",
        "|---|---|---|---:|---:|---|---|---:|---:|",
    ]
    for row in report["trades"]:
        lines.append(
            f"| {row['release_utc'][:10]} | {row['event']} | {row['direction']} | "
            f"{row.get('entry_price', 0):.3f} | {row.get('exit_price', 0):.3f} | "
            f"{row.get('exit_reason', row['status'])} | "
            f"{'YES' if row.get('trailing_activated') else 'NO'} | "
            f"${row['pnl_usd']:+.2f} | ${row['balance_after_usd']:.2f} |"
        )
    lines.extend(
        [
            "",
            "## Assumptions",
            "",
            f"- Fixed {LOT:.2f} lot on every event; no compounding of lot size.",
            f"- Gross stop risk at exact fill is ${STOP_USD_PRICE * 100 * LOT:.2f}; spread and gaps can change it.",
            "- Bid/ask spread and tick gaps are included. Commission, swap, latency, and rejected fills are not available historically and are excluded.",
            f"- Margin uses the connected account's 1:{report['broker']['leverage']} leverage and {report['broker']['stop_out_pct']:.0f}% stop-out level.",
            "- This is a retrospective simulation; prediction accuracy and execution results are separate measurements.",
        ]
    )
    return "\n".join(lines) + "\n"


def run() -> dict:
    payload = json.loads(INPUT_PATH.read_text(encoding="utf-8"))
    events = [
        row
        for row in payload["events"]
        if row["release_utc"][:10] >= "2026-06-10"
    ]
    terminal = os.getenv("MT5_PATH", r"C:\Program Files\MetaTrader 5\terminal64.exe")
    if not mt5.initialize(path=terminal):
        raise RuntimeError(f"Could not initialize MT5: {mt5.last_error()}")
    try:
        account = mt5.account_info()
        info = mt5.symbol_info("XAUUSD")
        if account is None or info is None or not mt5.symbol_select("XAUUSD", True):
            raise RuntimeError("The connected MT5 account does not expose XAUUSD.")
        leverage = int(account.leverage)
        stop_out_pct = float(account.margin_so_so)
        balance = STARTING_BALANCE
        peak = balance
        max_drawdown = 0.0
        max_drawdown_pct = 0.0
        equity_peak = balance
        max_equity_drawdown = 0.0
        max_equity_drawdown_pct = 0.0
        trades = []
        for event in events:
            release = _utc(event["release_utc"])
            result = _simulate(
                _event_ticks("XAUUSD", release),
                release=release,
                direction=event["prediction"],
                info=info,
                balance=balance,
                equity_peak=equity_peak,
                leverage=leverage,
                stop_out_pct=stop_out_pct,
            )
            before = balance
            balance += float(result["pnl_usd"])
            equity_peak = max(equity_peak, float(result["equity_peak_after_usd"]))
            max_equity_drawdown = max(
                max_equity_drawdown,
                float(result["maximum_equity_drawdown_usd"]),
            )
            max_equity_drawdown_pct = max(
                max_equity_drawdown_pct,
                float(result["maximum_equity_drawdown_pct"]),
            )
            peak = max(peak, balance)
            drawdown = max(0.0, peak - balance)
            max_drawdown = max(max_drawdown, drawdown)
            if peak > 0:
                max_drawdown_pct = max(max_drawdown_pct, 100 * drawdown / peak)
            trades.append(
                {
                    "release_utc": release.isoformat(),
                    "event": event["event"],
                    "direction": event["prediction"],
                    "prediction_correct": bool(event["correct"]),
                    "balance_before_usd": round(before, 2),
                    **result,
                    "balance_after_usd": round(balance, 2),
                }
            )
    finally:
        mt5.shutdown()

    executed = [row for row in trades if row["status"] == "EXECUTED"]
    wins = [row for row in executed if row["pnl_usd"] > 0]
    losses = [row for row in executed if row["pnl_usd"] < 0]
    gross_profit = sum(row["pnl_usd"] for row in wins)
    gross_loss = -sum(row["pnl_usd"] for row in losses)
    summary = {
        "starting_balance_usd": STARTING_BALANCE,
        "ending_balance_usd": round(balance, 2),
        "net_profit_usd": round(balance - STARTING_BALANCE, 2),
        "return_pct": round(100 * (balance / STARTING_BALANCE - 1), 2),
        "executed_trades": len(executed),
        "wins": len(wins),
        "losses": len(losses),
        "breakeven": len(executed) - len(wins) - len(losses),
        "win_rate_pct": round(100 * len(wins) / len(executed), 2) if executed else 0.0,
        "gross_profit_usd": round(gross_profit, 2),
        "gross_loss_usd": round(gross_loss, 2),
        "profit_factor": round(gross_profit / gross_loss, 2) if gross_loss else None,
        "maximum_realized_drawdown_usd": round(max_drawdown, 2),
        "maximum_realized_drawdown_pct": round(max_drawdown_pct, 2),
        "maximum_equity_drawdown_usd": round(max_equity_drawdown, 2),
        "maximum_equity_drawdown_pct": round(max_equity_drawdown_pct, 2),
    }
    report = {
        "configuration": {
            "entry_seconds_before_release": ENTRY_SECONDS_BEFORE,
            "lot": LOT,
            "stop_gold_price_usd": STOP_USD_PRICE,
            "target_gold_price_usd": TARGET_USD_PRICE,
            "trailing_trigger_r": TRAIL_TRIGGER_R,
            "trailing_distance_gold_price_usd": TRAIL_DISTANCE_USD_PRICE,
            "maximum_hold_minutes": MAX_HOLD_MINUTES,
        },
        "broker": {
            "server": account.server,
            "symbol": "XAUUSD",
            "leverage": leverage,
            "stop_out_pct": stop_out_pct,
            "contract_size": float(info.trade_contract_size),
            "tick_size": float(info.trade_tick_size),
            "tick_value_per_lot_usd": float(info.trade_tick_value),
        },
        "summary": summary,
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
