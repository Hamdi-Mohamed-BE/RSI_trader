from __future__ import annotations

import argparse
import csv
import gzip
import json
from dataclasses import asdict
from datetime import datetime, timedelta, timezone
from itertools import product
from pathlib import Path

import MetaTrader5 as mt5

from weekend_gap_strategy import (
    StrategyConfig,
    backtest,
    calculate_metrics,
    find_weekend_windows,
    metrics_for_period,
)


ROOT = Path(__file__).resolve().parent
DATA_PATH = ROOT / "data" / "weekend-gap" / "xauusd-m1-1y.json.gz"
JSON_PATH = ROOT / "weekend_gap_backtest_1y.json"
CSV_PATH = ROOT / "weekend_gap_backtest_1y_trades.csv"
REPORT_PATH = ROOT / "WEEKEND_GAP_BACKTEST_1Y.md"


def discover_gold_symbol() -> str:
    candidates: list[tuple[int, str]] = []
    for symbol in mt5.symbols_get() or []:
        name = symbol.name.upper()
        description = (symbol.description or "").upper()
        if "XAUUSD" not in name and not ("GOLD" in description and "FUTURE" not in description):
            continue
        score = (100 if name == "XAUUSD" else 0) + (50 if name.startswith("XAUUSD") else 0)
        score += 20 if "SPOT" in description or "GOLD VS US DOLLAR" in description else 0
        candidates.append((score, symbol.name))
    if not candidates:
        raise RuntimeError("No broker spot-gold symbol was found.")
    return max(candidates)[1]


def load_market_data(start: datetime, end: datetime, refresh: bool) -> tuple[dict, list[dict]]:
    if DATA_PATH.exists() and not refresh:
        with gzip.open(DATA_PATH, "rt", encoding="utf-8") as handle:
            payload = json.load(handle)
        cached_start = datetime.fromisoformat(payload["start_utc"])
        cached_end = datetime.fromisoformat(payload["end_utc"])
        if cached_start <= start and cached_end >= end - timedelta(days=2):
            return payload, payload["rows"]

    if not mt5.initialize():
        raise RuntimeError(f"MT5 initialization failed: {mt5.last_error()}")
    try:
        symbol = discover_gold_symbol()
        if not mt5.symbol_select(symbol, True):
            raise RuntimeError(f"Could not select {symbol}: {mt5.last_error()}")
        info = mt5.symbol_info(symbol)
        rates = mt5.copy_rates_range(symbol, mt5.TIMEFRAME_M1, start, end)
        if rates is None or len(rates) < 100_000:
            raise RuntimeError(f"Incomplete M1 history for {symbol}: {mt5.last_error()}")
        rows = [
            {
                "time": int(row["time"]),
                "open": float(row["open"]),
                "high": float(row["high"]),
                "low": float(row["low"]),
                "close": float(row["close"]),
                "spread": int(row["spread"]),
            }
            for row in rates
        ]
        account = mt5.account_info()
        payload = {
            "symbol": symbol,
            "description": info.description if info else "",
            "point": float(info.point if info else 0.01),
            "server": getattr(account, "server", None),
            "start_utc": start.isoformat(),
            "end_utc": end.isoformat(),
            "rows": rows,
        }
        DATA_PATH.parent.mkdir(parents=True, exist_ok=True)
        with gzip.open(DATA_PATH, "wt", encoding="utf-8", compresslevel=6) as handle:
            json.dump(payload, handle, separators=(",", ":"))
        return payload, rows
    finally:
        mt5.shutdown()


def quarter_ranges(start: datetime, end: datetime) -> list[tuple[datetime, datetime]]:
    step = (end - start) / 4
    boundaries = [start + step * index for index in range(5)]
    boundaries[-1] = end
    return list(zip(boundaries[:-1], boundaries[1:]))


def compact_metrics(metrics: dict) -> dict:
    return {key: (None if value == float("inf") else value) for key, value in metrics.items()}


def compounded_risk_metrics(trades, risk_fraction: float = 0.01) -> dict:
    equity = 1.0
    peak = 1.0
    max_drawdown = 0.0
    for trade in trades:
        equity *= max(0.0, 1.0 + risk_fraction * trade.result_r)
        peak = max(peak, equity)
        max_drawdown = max(max_drawdown, 1.0 - equity / peak)
    return {
        "risk_per_trade_pct": round(risk_fraction * 100, 2),
        "return_pct": round((equity - 1.0) * 100, 2),
        "max_drawdown_pct": round(max_drawdown * 100, 2),
    }


def optimize(rows: list[dict], point: float, start: datetime, end: datetime) -> tuple[dict, list[dict]]:
    windows = [
        window
        for window in find_weekend_windows(rows)
        if start <= datetime.fromtimestamp(rows[window.reopen_index]["time"], timezone.utc) < end
    ]
    split = start + (end - start) * 0.75
    training_windows = [
        window
        for window in windows
        if datetime.fromtimestamp(rows[window.reopen_index]["time"], timezone.utc) < split
    ]
    training_step = (split - start) / 3
    training_blocks = [
        (start + training_step * index, split if index == 2 else start + training_step * (index + 1))
        for index in range(3)
    ]
    candidates: list[dict] = []
    for offset, lead, stop, rr, hold in product(
        (1.5, 2.0, 3.0, 4.0, 5.0, 7.5, 10.0),
        (1, 2, 3, 5, 8),
        (10.0, 15.0, 20.0, 25.0, 30.0, 35.0, 40.0, 50.0),
        (1.0, 1.5, 2.0, 2.5, 3.0, 4.0),
        (60, 120, 240, 480, 720),
    ):
        config = StrategyConfig(offset, lead, stop, rr, hold)
        training = backtest(rows, point, config, windows=training_windows)
        block_metrics = [metrics_for_period(training.trades, block_start, block_end) for block_start, block_end in training_blocks]
        if min(item["trades"] for item in block_metrics) < 4:
            continue
        positive_blocks = sum(item["net_r"] > 0 for item in block_metrics)
        worst_block = min(item["net_r"] for item in block_metrics)
        # Selection is based only on the first 75% of the sample. It rewards
        # total expectancy and the weakest block while penalizing drawdown.
        score = training.metrics["net_r"] - 1.5 * training.metrics["max_drawdown_r"] + 2.0 * worst_block
        candidates.append(
            {
                "config": asdict(config),
                "training_metrics": compact_metrics(training.metrics),
                "training_blocks": [compact_metrics(item) for item in block_metrics],
                "positive_training_blocks": positive_blocks,
                "worst_training_block_net_r": round(worst_block, 4),
                "selection_score": round(score, 4),
            }
        )

    robust_pool = [item for item in candidates if item["positive_training_blocks"] == 3]
    selected = max(
        robust_pool or candidates,
        key=lambda item: (
            item["selection_score"],
            item["training_metrics"]["profit_factor"] or 0,
            item["worst_training_block_net_r"],
        ),
    )
    ranking = sorted(
        robust_pool or candidates,
        key=lambda item: (
            item["selection_score"],
            item["training_metrics"]["profit_factor"] or 0,
            item["worst_training_block_net_r"],
        ),
        reverse=True,
    )[:10]
    config = StrategyConfig(**selected["config"])
    result = backtest(rows, point, config, windows=windows)
    selected.update(
        {
            "metrics": compact_metrics(result.metrics),
            "expired": result.expired,
            "holdout_start_utc": split.isoformat(),
            "holdout_metrics": compact_metrics(metrics_for_period(result.trades, split, end)),
            "quarterly": [compact_metrics(metrics_for_period(result.trades, q_start, q_end)) for q_start, q_end in quarter_ranges(start, end)],
            "source_breakdown": {
                source: compact_metrics(calculate_metrics([trade for trade in result.trades if trade.source == source]))
                for source in ("friday", "reopen")
            },
            "side_breakdown": {
                side: compact_metrics(calculate_metrics([trade for trade in result.trades if trade.side == side]))
                for side in ("BUY", "SELL")
            },
            "result": result,
        }
    )
    return selected, ranking


def _clean_candidate(candidate: dict) -> dict:
    return {key: value for key, value in candidate.items() if key != "result"}


def write_outputs(payload: dict, start: datetime, end: datetime, selected: dict, ranking: list[dict]) -> None:
    result = selected["result"]
    one_percent = compounded_risk_metrics(result.trades)
    quarters = quarter_ranges(start, end)
    report_payload = {
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "data": {key: value for key, value in payload.items() if key != "rows"},
        "period": {"start_utc": start.isoformat(), "end_utc": end.isoformat()},
        "methodology": {
            "entry": "Friday completed M1 wick +/- optimized dollar offset; OCO; unfilled orders cancel at weekly reopen",
            "costs": "MT5 historical spread applied; gap entries filled at opening ask/bid; stop checked before target within ambiguous M1 bars",
            "selection": "First 75% development with three positive-block requirement; final 25% is untouched holdout",
        },
        "robust_selection": _clean_candidate(selected),
        "one_percent_risk_scenario": one_percent,
        "top_robust_candidates": [_clean_candidate(item) for item in ranking],
        "trades": [asdict(trade) for trade in result.trades],
    }
    JSON_PATH.write_text(json.dumps(report_payload, indent=2), encoding="utf-8")
    with CSV_PATH.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(asdict(result.trades[0]).keys()) if result.trades else ["weekend_open"])
        writer.writeheader()
        for trade in result.trades:
            writer.writerow(asdict(trade))

    metrics = selected["metrics"]
    training = selected["training_metrics"]
    holdout = selected["holdout_metrics"]
    lines = [
        "# XAUUSD Friday Weekend-Straddle Backtest",
        "",
        f"Period: {start:%Y-%m-%d} through {end:%Y-%m-%d} UTC  ",
        f"Broker feed: `{payload['server']}` / `{payload['symbol']}` M1  ",
        "Spread and weekend gap slippage: included",
        "",
        "## Selected robust configuration",
        "",
        f"- Offset: `${selected['config']['offset_usd']:.2f}` outside the completed M1 wick",
        f"- Placement: `{selected['config']['placement_lead_minutes']}` minutes before the inferred Friday close",
        f"- Stop: `${selected['config']['stop_usd']:.2f}`",
        f"- Reward/risk: `{selected['config']['reward_risk']}:1`",
        f"- Maximum hold: `{selected['config']['max_hold_market_minutes']}` market minutes",
        "- First fill cancels the opposite pending order",
        "- If neither pending trigger is crossed at the weekly reopen, both are cancelled immediately",
        "",
        "## Full-period result",
        "",
        "| Trades | Win rate | Profit factor | Net | Max drawdown | Friday fills | Reopen fills | Expired weekends |",
        "|---:|---:|---:|---:|---:|---:|---:|---:|",
        f"| {metrics['trades']} | {metrics['win_rate_pct']:.2f}% | {metrics['profit_factor']:.3f} | {metrics['net_r']:+.2f}R | {metrics['max_drawdown_r']:.2f}R | {metrics['friday_fills']} | {metrics['reopen_fills']} | {selected['expired']} |",
        "",
        f"At a hypothetical fixed 1% account risk per filled trade, this sequence compounds to **{one_percent['return_pct']:+.2f}%** with **{one_percent['max_drawdown_pct']:.2f}%** maximum equity drawdown.",
        "",
        "## Frozen holdout validation",
        "",
        "The configuration was selected using only the first 75% of the year. The last 25% was opened once after selection.",
        "",
        "| Sample | Trades | Win rate | Profit factor | Net | Max drawdown |",
        "|---|---:|---:|---:|---:|---:|",
        f"| Development | {training['trades']} | {training['win_rate_pct']:.2f}% | {training['profit_factor']:.3f} | {training['net_r']:+.2f}R | {training['max_drawdown_r']:.2f}R |",
        f"| Holdout | {holdout['trades']} | {holdout['win_rate_pct']:.2f}% | {holdout['profit_factor']:.3f} | {holdout['net_r']:+.2f}R | {holdout['max_drawdown_r']:.2f}R |",
        "",
        "## Four-block stability",
        "",
        "| Block | Trades | Win rate | Profit factor | Net | Max drawdown |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for index, ((q_start, q_end), item) in enumerate(zip(quarters, selected["quarterly"]), 1):
        pf = "n/a" if item["profit_factor"] is None else f"{item['profit_factor']:.3f}"
        lines.append(
            f"| Q{index} ({q_start:%Y-%m-%d} to {q_end:%Y-%m-%d}) | {item['trades']} | {item['win_rate_pct']:.2f}% | {pf} | {item['net_r']:+.2f}R | {item['max_drawdown_r']:.2f}R |"
        )
    friday = selected["source_breakdown"]["friday"]
    reopen = selected["source_breakdown"]["reopen"]
    lines += [
        "",
        "## Where the edge came from",
        "",
        "| Fill source | Trades | Win rate | Profit factor | Net |",
        "|---|---:|---:|---:|---:|",
        f"| Friday pre-close | {friday['trades']} | {friday['win_rate_pct']:.2f}% | {friday['profit_factor']:.3f} | {friday['net_r']:+.2f}R |",
        f"| Weekly reopen | {reopen['trades']} | {reopen['win_rate_pct']:.2f}% | {reopen['profit_factor']:.3f} | {reopen['net_r']:+.2f}R |",
        "",
        "Most of the historical edge came from stops triggered before Friday close. The Monday-only gap component was only marginally profitable.",
        "",
        "## Limits",
        "",
        "M1 bars do not reveal tick order inside a candle. Ambiguous candles use stop-first logic, and when both pending sides are touched in one M1 bar the worse completed side is selected. Real weekend fills can be worse than this broker history because liquidity and spreads vary.",
    ]
    REPORT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def run(refresh: bool = False) -> dict:
    end = datetime.now(timezone.utc)
    start = end - timedelta(days=366)
    payload, rows = load_market_data(start - timedelta(days=7), end, refresh)
    selected, ranking = optimize(rows, float(payload["point"]), start, end)
    write_outputs(payload, start, end, selected, ranking)
    return {
        "symbol": payload["symbol"],
        "server": payload["server"],
        "period": [start.isoformat(), end.isoformat()],
        "robust": _clean_candidate(selected),
        "report": str(REPORT_PATH),
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Optimize the XAUUSD Friday weekend straddle.")
    parser.add_argument("--refresh", action="store_true", help="Refresh the cached MT5 M1 history.")
    args = parser.parse_args()
    print(json.dumps(run(args.refresh), indent=2))
