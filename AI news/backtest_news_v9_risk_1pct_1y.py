from __future__ import annotations

import csv
import json
import math
import os
from collections import Counter
from datetime import date

import MetaTrader5 as mt5
import numpy as np

from backtest_news_v8_move_execution_3m import (
    ExecutionConfig,
    _event_ticks,
    _simulate_event,
    _utc,
)
from backtest_news_v8_one_year import _archived_hybrid_ticks
from news_core import ROOT


START = date(2025, 9, 10)
END = date(2026, 9, 10)
STARTING_BALANCE = 10_000.0
RISK_FRACTION = 0.01
SUPPORTED_EVENTS = ("NFP", "CPI", "FOMC")
DIRECTION_REPORT = ROOT / "news_v9_direction_1y_results.json"
OUTPUT_JSON = ROOT / "news_v9_risk_1pct_1y_results.json"
OUTPUT_CSV = ROOT / "news_v9_risk_1pct_1y_trades.csv"
OUTPUT_MD = ROOT / "NEWS_V9_RISK_1PCT_1Y_RESULTS.md"

CONFIG = ExecutionConfig(
    entry_offset_seconds=-5,
    stop_usd=4.0,
    take_profit_usd=None,
    trailing_trigger_usd=None,
    trailing_distance_usd=None,
    exit_after_seconds=900,
)


def _normalize_lot(raw_lot: float, info: object) -> float:
    step = float(info.volume_step)
    if step <= 0:
        raise RuntimeError("Broker returned an invalid volume step.")
    lot = math.floor((raw_lot + 1e-12) / step) * step
    lot = min(lot, float(info.volume_max))
    return round(lot, 8) if lot >= float(info.volume_min) else 0.0


def _risk_lot(balance: float, info: object) -> tuple[float, float, float]:
    budget = balance * RISK_FRACTION
    tick_size = float(info.trade_tick_size)
    loss_tick_value = float(getattr(info, "trade_tick_value_loss", 0.0))
    tick_value = loss_tick_value if loss_tick_value > 0 else float(info.trade_tick_value)
    if tick_size <= 0 or tick_value <= 0:
        raise RuntimeError("Broker returned invalid XAUUSD tick metadata.")
    loss_per_lot = float(CONFIG.stop_usd) * tick_value / tick_size
    lot = _normalize_lot(budget / loss_per_lot, info)
    return lot, budget, lot * loss_per_lot


def _drawdown(values: list[float]) -> tuple[float, float]:
    series = np.asarray(values, dtype=float)
    peaks = np.maximum.accumulate(series)
    amount = peaks - series
    percent = np.divide(
        amount, peaks, out=np.zeros_like(amount), where=peaks > 0
    )
    return float(np.max(amount)), 100 * float(np.max(percent))


def _streaks(trades: list[dict]) -> tuple[int, int]:
    max_win = max_loss = win = loss = 0
    for row in trades:
        if row["pnl_usd"] > 0:
            win += 1
            loss = 0
            max_win = max(max_win, win)
        else:
            loss += 1
            win = 0
            max_loss = max(max_loss, loss)
    return max_win, max_loss


def _metrics(trades: list[dict], tick_equity: list[float]) -> dict:
    wins = [row for row in trades if row["pnl_usd"] > 0]
    losses = [row for row in trades if row["pnl_usd"] < 0]
    gross_profit = sum(row["pnl_usd"] for row in wins)
    gross_loss = -sum(row["pnl_usd"] for row in losses)
    ending = trades[-1]["balance_after_usd"]
    net = ending - STARTING_BALANCE
    realized_dd, realized_dd_pct = _drawdown(
        [STARTING_BALANCE] + [row["balance_after_usd"] for row in trades]
    )
    tick_dd, tick_dd_pct = _drawdown(tick_equity)
    max_wins, max_losses = _streaks(trades)
    average_win = gross_profit / len(wins) if wins else 0.0
    average_loss = gross_loss / len(losses) if losses else 0.0
    return {
        "starting_balance_usd": round(STARTING_BALANCE, 2),
        "ending_balance_usd": round(ending, 2),
        "net_profit_usd": round(net, 2),
        "return_pct": round(100 * net / STARTING_BALANCE, 2),
        "executed_trades": len(trades),
        "wins": len(wins),
        "losses": len(losses),
        "win_rate_pct": round(100 * len(wins) / len(trades), 2),
        "gross_profit_usd": round(gross_profit, 2),
        "gross_loss_usd": round(gross_loss, 2),
        "profit_factor": round(gross_profit / gross_loss, 2),
        "average_trade_usd": round(net / len(trades), 2),
        "average_win_usd": round(average_win, 2),
        "average_loss_usd": round(average_loss, 2),
        "payoff_ratio": round(average_win / average_loss, 2),
        "average_realized_r": round(
            sum(row["realized_r"] for row in trades) / len(trades), 3
        ),
        "largest_win_usd": round(max(row["pnl_usd"] for row in wins), 2),
        "largest_loss_usd": round(min(row["pnl_usd"] for row in losses), 2),
        "maximum_consecutive_wins": max_wins,
        "maximum_consecutive_losses": max_losses,
        "maximum_realized_drawdown_usd": round(realized_dd, 2),
        "maximum_realized_drawdown_pct": round(realized_dd_pct, 2),
        "maximum_tick_equity_drawdown_usd": round(tick_dd, 2),
        "maximum_tick_equity_drawdown_pct": round(tick_dd_pct, 2),
        "minimum_tick_equity_usd": round(min(tick_equity), 2),
        "realized_recovery_factor": round(net / realized_dd, 2),
        "account_survived": ending > 0,
    }


def _event_breakdown(events: list[dict], trades: list[dict]) -> dict:
    by_release = {row["release_utc"]: row for row in trades}
    result = {}
    for name in SUPPORTED_EVENTS:
        selected = [row for row in events if row["event"] == name]
        event_trades = [by_release[row["release_utc"]] for row in selected]
        wins = [row for row in event_trades if row["pnl_usd"] > 0]
        losses = [row for row in event_trades if row["pnl_usd"] < 0]
        gross_profit = sum(row["pnl_usd"] for row in wins)
        gross_loss = -sum(row["pnl_usd"] for row in losses)
        direction_wins = sum(row["v9_direction"] == row["actual"] for row in selected)
        result[name] = {
            "releases": len(selected),
            "direction_wins": direction_wins,
            "direction_accuracy_pct": round(100 * direction_wins / len(selected), 2),
            "trade_wins": len(wins),
            "trade_losses": len(losses),
            "trade_win_rate_pct": round(100 * len(wins) / len(event_trades), 2),
            "net_profit_usd": round(gross_profit - gross_loss, 2),
            "profit_factor": round(gross_profit / gross_loss, 2),
            "average_realized_r": round(
                sum(row["realized_r"] for row in event_trades) / len(event_trades), 3
            ),
        }
    return result


def _tier_breakdown(trades: list[dict]) -> dict:
    result = {}
    for tier in ("TRADE", "LOW_CONFIDENCE"):
        selected = [row for row in trades if row["action_tier"] == tier]
        wins = [row for row in selected if row["pnl_usd"] > 0]
        losses = [row for row in selected if row["pnl_usd"] < 0]
        gross_profit = sum(row["pnl_usd"] for row in wins)
        gross_loss = -sum(row["pnl_usd"] for row in losses)
        result[tier] = {
            "trades": len(selected),
            "wins": len(wins),
            "losses": len(losses),
            "win_rate_pct": round(100 * len(wins) / len(selected), 2),
            "net_profit_usd": round(gross_profit - gross_loss, 2),
            "profit_factor": round(gross_profit / gross_loss, 2),
        }
    return result


def _load_events() -> list[dict]:
    payload = json.loads(DIRECTION_REPORT.read_text(encoding="utf-8"))
    events = []
    for row in payload["events"]:
        released = date.fromisoformat(row["release_utc"][:10])
        if START <= released < END:
            if row["event"] not in SUPPORTED_EVENTS:
                raise RuntimeError(f"Unsupported event leaked into V9: {row['event']}")
            events.append({**row, "prediction": row["v9_direction"]})
    events.sort(key=lambda row: row["release_utc"])
    expected = Counter({"NFP": 10, "CPI": 11, "FOMC": 8})
    observed = Counter(row["event"] for row in events)
    if observed != expected:
        raise RuntimeError(
            f"Expected {dict(expected)}, found {dict(observed)}."
        )
    return events


def _money(value: float, signed: bool = False) -> str:
    formatted = f"{value:+,.2f}" if signed else f"{value:,.2f}"
    return "$" + formatted


def _markdown(report: dict) -> str:
    metrics = report["performance"]
    lines = [
        "# Gold News V9 - One-Year 1% Risk Replay",
        "",
        "> NFP, CPI, and FOMC only. Entry is T-5 seconds, the XAUUSD stop "
        "is $4.00 from fill, there is no take profit or trailing stop, and "
        "positions exit at T+15 minutes.",
        "",
        "## Portfolio Performance",
        "",
        "| Measure | Result |",
        "|---|---:|",
        f"| Starting balance | {_money(metrics['starting_balance_usd'])} |",
        f"| Ending balance | {_money(metrics['ending_balance_usd'])} |",
        f"| Net profit | {_money(metrics['net_profit_usd'], True)} |",
        f"| Return | {metrics['return_pct']:.2f}% |",
        f"| Executed trades | {metrics['executed_trades']} |",
        f"| Wins / losses | {metrics['wins']} / {metrics['losses']} |",
        f"| Win rate | {metrics['win_rate_pct']:.2f}% |",
        f"| Direction accuracy | {report['direction']['accuracy_pct']:.2f}% |",
        f"| Profit factor | {metrics['profit_factor']:.2f} |",
        f"| Average trade | {_money(metrics['average_trade_usd'], True)} |",
        f"| Average realized R | {metrics['average_realized_r']:+.3f}R |",
        f"| Average win / loss | {_money(metrics['average_win_usd'])} / {_money(metrics['average_loss_usd'])} |",
        f"| Payoff ratio | {metrics['payoff_ratio']:.2f} |",
        f"| Largest win / loss | {_money(metrics['largest_win_usd'], True)} / {_money(metrics['largest_loss_usd'], True)} |",
        f"| Maximum consecutive wins / losses | {metrics['maximum_consecutive_wins']} / {metrics['maximum_consecutive_losses']} |",
        f"| Maximum realized DD | {_money(metrics['maximum_realized_drawdown_usd'])} ({metrics['maximum_realized_drawdown_pct']:.2f}%) |",
        f"| Maximum tick-equity DD | {_money(metrics['maximum_tick_equity_drawdown_usd'])} ({metrics['maximum_tick_equity_drawdown_pct']:.2f}%) |",
        f"| Minimum tick equity | {_money(metrics['minimum_tick_equity_usd'])} |",
        f"| Realized recovery factor | {metrics['realized_recovery_factor']:.2f} |",
        "",
        "Realized drawdown uses closed balances. Tick-equity drawdown includes "
        "adverse movement while a position is open.",
        "",
        "## Event Breakdown",
        "",
        "| Event | Releases | Direction | Trade wins | Win rate | Net P/L | PF | Average R |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for name in SUPPORTED_EVENTS:
        row = report["event_breakdown"][name]
        lines.append(
            f"| {name} | {row['releases']} | {row['direction_wins']}/{row['releases']} "
            f"({row['direction_accuracy_pct']:.2f}%) | "
            f"{row['trade_wins']}/{row['releases']} | "
            f"{row['trade_win_rate_pct']:.2f}% | "
            f"{_money(row['net_profit_usd'], True)} | "
            f"{row['profit_factor']:.2f} | {row['average_realized_r']:+.3f}R |"
        )
    lines.extend(
        [
            "",
            "## Action-Tier Breakdown",
            "",
            "| Tier | Trades | Wins | Win rate | Net P/L | PF |",
            "|---|---:|---:|---:|---:|---:|",
        ]
    )
    for tier in ("TRADE", "LOW_CONFIDENCE"):
        row = report["action_tier_breakdown"][tier]
        lines.append(
            f"| {tier} | {row['trades']} | {row['wins']} | "
            f"{row['win_rate_pct']:.2f}% | "
            f"{_money(row['net_profit_usd'], True)} | "
            f"{row['profit_factor']:.2f} |"
        )
    lines.extend(
        [
            "",
            "## Trade Replay",
            "",
            "| Date | Event | Call | Tier | Actual | Risk | Lot | Captured | Exit | P/L | R | Balance | Source |",
            "|---|---|---|---|---|---:|---:|---:|---|---:|---:|---:|---|",
        ]
    )
    for row in report["trades"]:
        lines.append(
            f"| {row['release_utc'][:10]} | {row['event']} | "
            f"{row['v9_direction']} | {row['action_tier']} | {row['actual']} | "
            f"{_money(row['risk_budget_usd'])} | {row['lot']:.2f} | "
            f"{row['captured_move_usd']:+.3f} USD | {row['exit_reason']} | "
            f"{_money(row['pnl_usd'], True)} | {row['realized_r']:+.3f}R | "
            f"{_money(row['balance_after_usd'])} | {row['data_source']} |"
        )
    lines.extend(
        [
            "",
            "## Assumptions and Limits",
            "",
            "- Risk is 1% of current balance before each event and therefore compounds.",
            "- Lot size is rounded down to the connected broker's volume step.",
            "- Nominal risk uses the $4.00 stop and XAUUSD tick value. A gap "
            "through the stop can lose more than 1%.",
            "- All directions are executed, including LOW_CONFIDENCE rows.",
            "- Exact MT5 ticks are used when available. Older rows may combine "
            "archived bid/ask ticks with M1 continuation.",
            "- Spread and tick-gap slippage are included where available. "
            "Commission, network latency, rejection, and market-depth impact are not.",
            "- This is retrospective research, not untouched validation or a guarantee.",
        ]
    )
    return "\n".join(lines) + "\n"


def run() -> dict:
    if not DIRECTION_REPORT.exists():
        raise FileNotFoundError(
            "Run backtest_news_v9_direction_1y.py before this replay."
        )
    events = _load_events()
    terminal = os.getenv("MT5_PATH", r"C:\Program Files\MetaTrader 5\terminal64.exe")
    if not mt5.initialize(path=terminal):
        raise RuntimeError(f"Could not initialize MT5: {mt5.last_error()}")
    try:
        account = mt5.account_info()
        info = mt5.symbol_info("XAUUSD")
        if account is None or info is None or not mt5.symbol_select("XAUUSD", True):
            raise RuntimeError("The connected MT5 account does not expose XAUUSD.")

        ticks_by_release = {}
        sources = {}
        for event in events:
            release = event["release_utc"]
            try:
                ticks_by_release[release] = _event_ticks("XAUUSD", _utc(release))
                sources[release] = "MT5 ticks"
            except RuntimeError:
                ticks_by_release[release] = _archived_hybrid_ticks(event)
                sources[release] = "archive ticks + M1 continuation"

        balance = STARTING_BALANCE
        equity_values = [STARTING_BALANCE]
        trades = []
        for event in events:
            lot, risk_budget, nominal_risk = _risk_lot(balance, info)
            if lot <= 0:
                raise RuntimeError("Calculated lot is below broker minimum.")
            before = balance
            execution = _simulate_event(
                ticks_by_release[event["release_utc"]],
                release=_utc(event["release_utc"]),
                direction=event["v9_direction"],
                config=CONFIG,
                balance=balance,
                info=info,
                leverage=int(account.leverage),
                lot=lot,
                include_path=True,
            )
            if execution["status"] != "EXECUTED":
                raise RuntimeError(
                    f"{event['release_utc']} failed: {execution['status']}"
                )
            balance += float(execution["pnl_usd"])
            equity_values.extend(execution.pop("equity_path").tolist())
            trades.append(
                {
                    **event,
                    "balance_before_usd": round(before, 2),
                    "risk_budget_usd": round(risk_budget, 2),
                    "nominal_risk_usd": round(nominal_risk, 2),
                    **execution,
                    "realized_r": round(execution["pnl_usd"] / nominal_risk, 4),
                    "balance_after_usd": round(balance, 2),
                    "data_source": sources[event["release_utc"]],
                }
            )
    finally:
        mt5.shutdown()

    direction_wins = sum(row["v9_direction"] == row["actual"] for row in events)
    report = {
        "status": "v9_one_year_1pct_risk_retrospective",
        "window": {"start": START.isoformat(), "end_exclusive": END.isoformat()},
        "scope": {
            "events": list(SUPPORTED_EVENTS),
            "action_tiers_executed": ["TRADE", "LOW_CONFIDENCE"],
        },
        "configuration": {
            "starting_balance_usd": STARTING_BALANCE,
            "risk_percent_of_current_balance": 100 * RISK_FRACTION,
            "entry_offset_seconds": CONFIG.entry_offset_seconds,
            "stop_distance_usd": CONFIG.stop_usd,
            "take_profit_usd": CONFIG.take_profit_usd,
            "trailing_stop": None,
            "exit_after_release_seconds": CONFIG.exit_after_seconds,
        },
        "broker": {
            "server": account.server,
            "symbol": info.name,
            "leverage": int(account.leverage),
            "contract_size": float(info.trade_contract_size),
            "volume_min": float(info.volume_min),
            "volume_max": float(info.volume_max),
            "volume_step": float(info.volume_step),
            "tick_size": float(info.trade_tick_size),
            "tick_value_loss": float(info.trade_tick_value_loss),
        },
        "direction": {
            "events": len(events),
            "wins": direction_wins,
            "losses": len(events) - direction_wins,
            "accuracy_pct": round(100 * direction_wins / len(events), 2),
            "coverage_pct": 100.0,
        },
        "performance": _metrics(trades, equity_values),
        "event_breakdown": _event_breakdown(events, trades),
        "action_tier_breakdown": _tier_breakdown(trades),
        "data_source_counts": dict(Counter(sources.values())),
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
    result = run()
    print(json.dumps(
        {
            "direction": result["direction"],
            "performance": result["performance"],
            "event_breakdown": result["event_breakdown"],
            "action_tier_breakdown": result["action_tier_breakdown"],
            "data_source_counts": result["data_source_counts"],
        },
        indent=2,
    ))
    print(f"Saved {OUTPUT_MD}")
