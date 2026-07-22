from __future__ import annotations

import itertools
import json
import math
from dataclasses import asdict, dataclass
from datetime import timedelta
from pathlib import Path
from typing import Iterable

import MetaTrader5 as mt5
import pandas as pd

from news_events import NEWS_EVENTS, NewsEvent


ROOT = Path(__file__).resolve().parent
TERMINAL_PATH = r"C:\Program Files\MetaTrader 5\terminal64.exe"


@dataclass(frozen=True)
class StrategyConfig:
    symbol: str = "XAUUSDm"
    event_filter: str = "tier1"
    setup_candle_minutes_before: int = 1
    buffer_points: float = 2.0
    sl_extra_points: float = 2.0
    tp_r: float = 3.0
    be_at_r: float | None = 1.0
    trigger_window_minutes: int = 3
    max_hold_minutes: int = 60
    max_setup_range_points: float = 12.0
    entry_slippage_points: float = 1.0
    exit_slippage_points: float = 1.0
    same_bar_policy: str = "skip"


EVENT_FILTERS: dict[str, set[str]] = {
    "tier1": {"CPI", "NFP", "FOMC"},
    "tier1_pce": {"CPI", "NFP", "FOMC", "PCE"},
    "inflation_jobs": {"CPI", "PPI", "PCE", "NFP", "JOLTS"},
    "all_major": {"CPI", "PPI", "PCE", "NFP", "FOMC", "Retail", "JOLTS", "Inflation", "LaborCosts"},
}


def connect_mt5() -> None:
    if not mt5.initialize(path=TERMINAL_PATH):
        raise RuntimeError(f"MT5 initialize failed: {mt5.last_error()}")


def fetch_m1(symbol: str, event: NewsEvent) -> pd.DataFrame | None:
    start = event.release_utc - timedelta(minutes=10)
    end = event.release_utc + timedelta(minutes=130)
    rates = mt5.copy_rates_range(symbol, mt5.TIMEFRAME_M1, start, end)
    if rates is None or len(rates) < 20:
        return None
    df = pd.DataFrame(rates)
    df["time"] = pd.to_datetime(df["time"], unit="s", utc=True)
    return df


def iter_events(config: StrategyConfig) -> Iterable[NewsEvent]:
    allowed = EVENT_FILTERS[config.event_filter]
    return (e for e in NEWS_EVENTS if e.event_type in allowed)


def simulate_event(df: pd.DataFrame, event: NewsEvent, config: StrategyConfig) -> dict:
    release = pd.Timestamp(event.release_utc)
    setup_start = release - pd.Timedelta(minutes=config.setup_candle_minutes_before + 1)
    setup_end = release - pd.Timedelta(minutes=config.setup_candle_minutes_before)
    setup = df[(df["time"] >= setup_start) & (df["time"] < setup_end)]
    if setup.empty:
        return {"status": "no_setup_candle", "r": 0.0}

    candle = setup.iloc[-1]
    setup_high = float(candle.high)
    setup_low = float(candle.low)
    setup_range = setup_high - setup_low
    if setup_range <= 0:
        return {"status": "bad_setup_range", "r": 0.0}
    if setup_range > config.max_setup_range_points:
        return {"status": "filtered_big_setup_candle", "r": 0.0, "setup_range": setup_range}

    buy_entry_raw = setup_high + config.buffer_points
    sell_entry_raw = setup_low - config.buffer_points
    buy_sl = setup_low - config.sl_extra_points
    sell_sl = setup_high + config.sl_extra_points
    buy_risk = buy_entry_raw - buy_sl
    sell_risk = sell_sl - sell_entry_raw
    if buy_risk <= 0 or sell_risk <= 0:
        return {"status": "bad_risk", "r": 0.0}

    trigger_end = release + pd.Timedelta(minutes=config.trigger_window_minutes)
    trigger_bars = df[(df["time"] >= release) & (df["time"] < trigger_end)]
    side = None
    trigger_time = None

    for _, bar in trigger_bars.iterrows():
        hit_buy = float(bar.high) >= buy_entry_raw
        hit_sell = float(bar.low) <= sell_entry_raw
        if hit_buy and hit_sell:
            if config.same_bar_policy == "skip":
                return {"status": "both_sides_same_bar_skip", "r": 0.0, "setup_range": setup_range}
            side = "buy" if abs(float(bar.open) - buy_entry_raw) < abs(float(bar.open) - sell_entry_raw) else "sell"
            trigger_time = bar.time
            break
        if hit_buy:
            side = "buy"
            trigger_time = bar.time
            break
        if hit_sell:
            side = "sell"
            trigger_time = bar.time
            break

    if side is None:
        return {"status": "no_trigger", "r": 0.0, "setup_range": setup_range}

    if side == "buy":
        entry = buy_entry_raw + config.entry_slippage_points
        sl = buy_sl - config.exit_slippage_points
        risk = entry - sl
        tp = entry + config.tp_r * risk
        be_price = entry + config.be_at_r * risk if config.be_at_r is not None else None
    else:
        entry = sell_entry_raw - config.entry_slippage_points
        sl = sell_sl + config.exit_slippage_points
        risk = sl - entry
        tp = entry - config.tp_r * risk
        be_price = entry - config.be_at_r * risk if config.be_at_r is not None else None

    if risk <= 0:
        return {"status": "bad_trigger_risk", "r": 0.0}

    manage_end = release + pd.Timedelta(minutes=config.max_hold_minutes)
    bars = df[(df["time"] >= trigger_time) & (df["time"] <= manage_end)]
    moved_be = False

    for _, bar in bars.iterrows():
        high = float(bar.high)
        low = float(bar.low)
        if side == "buy":
            if be_price is not None and not moved_be and high >= be_price:
                moved_be = True
            effective_sl = entry if moved_be else sl
            # Conservative order: if both TP and SL hit in one M1 bar, count SL.
            if low <= effective_sl:
                r = 0.0 if moved_be else -1.0
                return {"status": "be" if moved_be else "loss", "r": r, "side": side, "setup_range": setup_range}
            if high >= tp:
                return {"status": "win", "r": config.tp_r, "side": side, "setup_range": setup_range}
        else:
            if be_price is not None and not moved_be and low <= be_price:
                moved_be = True
            effective_sl = entry if moved_be else sl
            if high >= effective_sl:
                r = 0.0 if moved_be else -1.0
                return {"status": "be" if moved_be else "loss", "r": r, "side": side, "setup_range": setup_range}
            if low <= tp:
                return {"status": "win", "r": config.tp_r, "side": side, "setup_range": setup_range}

    last = bars.iloc[-1] if len(bars) else df.iloc[-1]
    if side == "buy":
        r = (float(last.close) - entry) / risk
    else:
        r = (entry - float(last.close)) / risk
    return {"status": "timeout", "r": max(-1.0, min(config.tp_r, r)), "side": side, "setup_range": setup_range}


def summarize(event_results: list[dict], config: StrategyConfig) -> dict:
    trades = [r for r in event_results if r["status"] in {"win", "loss", "be", "timeout"}]
    rs = [float(t["r"]) for t in trades]
    wins = [r for r in rs if r > 0]
    losses = [r for r in rs if r < 0]
    equity = []
    cur = 0.0
    peak = 0.0
    max_dd = 0.0
    for r in rs:
        cur += r
        peak = max(peak, cur)
        max_dd = max(max_dd, peak - cur)
        equity.append(cur)
    gross_win = sum(wins)
    gross_loss = abs(sum(losses))
    profit_factor = gross_win / gross_loss if gross_loss else math.inf if gross_win > 0 else 0
    return {
        **asdict(config),
        "events": len(event_results),
        "trades": len(trades),
        "wins": len(wins),
        "losses": len(losses),
        "breakevens": sum(1 for t in trades if abs(float(t["r"])) < 1e-9),
        "win_rate": len(wins) / len(trades) if trades else 0.0,
        "total_r": sum(rs),
        "avg_r": sum(rs) / len(trades) if trades else 0.0,
        "profit_factor": profit_factor,
        "max_drawdown_r": max_dd,
        "skipped": len(event_results) - len(trades),
        "objective": (sum(rs) - 0.45 * max_dd + 0.2 * len(trades)),
    }


def grid_configs(symbol: str) -> Iterable[StrategyConfig]:
    for event_filter, buffer_points, sl_extra_points, tp_r, be_at_r, trigger_window, max_hold, max_setup_range, slippage in itertools.product(
        # Practical trading grid. Wider brute-force grids are possible, but news
        # straddles overfit very easily with only a few months of clean events.
        ["tier1", "tier1_pce", "inflation_jobs"],
        [5.0],
        [6.0, 8.0, 10.0],
        [2.0, 3.0, 4.0],
        [1.0],
        [1, 2, 3],
        [30, 60],
        [12.0, 20.0, 999.0],
        [1.0],
    ):
        yield StrategyConfig(
            symbol=symbol,
            event_filter=event_filter,
            buffer_points=buffer_points,
            sl_extra_points=sl_extra_points,
            tp_r=tp_r,
            be_at_r=be_at_r,
            trigger_window_minutes=trigger_window,
            max_hold_minutes=max_hold,
            max_setup_range_points=max_setup_range,
            entry_slippage_points=slippage,
            exit_slippage_points=slippage,
        )


def main() -> None:
    connect_mt5()
    symbol = "XAUUSDm"
    data: dict[NewsEvent, pd.DataFrame] = {}
    for event in NEWS_EVENTS:
        df = fetch_m1(symbol, event)
        if df is not None:
            data[event] = df

    rows = []
    details_by_key = {}
    for config in grid_configs(symbol):
        event_results = []
        for event in iter_events(config):
            df = data.get(event)
            if df is None:
                continue
            out = simulate_event(df, event, config)
            out["event"] = f"{event.date_label} {event.name}"
            out["event_type"] = event.event_type
            event_results.append(out)
        summary = summarize(event_results, config)
        if summary["trades"] >= 4 and summary["max_drawdown_r"] <= 6:
            rows.append(summary)
            details_by_key[len(rows) - 1] = event_results

    result = pd.DataFrame(rows)
    if result.empty:
        raise RuntimeError("No valid backtest results. Check MT5 history availability.")

    result = result.sort_values(["objective", "total_r", "profit_factor"], ascending=[False, False, False]).reset_index(drop=True)
    result.to_csv(ROOT / "backtest_results.csv", index=False)

    best = result.iloc[0].to_dict()
    clean_best = {k: (None if pd.isna(v) else v) for k, v in best.items() if k in StrategyConfig.__dataclass_fields__}
    with open(ROOT / "config.best.json", "w", encoding="utf-8") as f:
        json.dump(clean_best, f, indent=2)

    # Re-run best details for readable report.
    best_config = StrategyConfig(**clean_best)
    best_details = []
    for event in iter_events(best_config):
        df = data.get(event)
        if df is None:
            continue
        out = simulate_event(df, event, best_config)
        out["event"] = f"{event.date_label} {event.name}"
        out["event_type"] = event.event_type
        best_details.append(out)
    detail_df = pd.DataFrame(best_details)
    detail_df.to_csv(ROOT / "best_config_trades.csv", index=False)

    report = [
        "# News Impulse Straddle Backtest Report",
        "",
        f"Symbol: `{symbol}`",
        f"Events loaded: `{len(data)}`",
        "",
        "## Best config",
        "",
        "```json",
        json.dumps(clean_best, indent=2),
        "```",
        "",
        "## Best config stats",
        "",
        f"- Trades: `{int(best['trades'])}`",
        f"- Total R: `{best['total_r']:.2f}R`",
        f"- Average R/trade: `{best['avg_r']:.2f}R`",
        f"- Win rate: `{best['win_rate'] * 100:.1f}%`",
        f"- Profit factor: `{best['profit_factor']:.2f}`",
        f"- Max drawdown: `{best['max_drawdown_r']:.2f}R`",
        f"- Objective score: `{best['objective']:.2f}`",
        "",
        "## Trade-by-trade result",
        "",
        detail_df[["event", "event_type", "status", "side", "r", "setup_range"]].to_markdown(index=False),
        "",
        "## Important notes",
        "",
        "- This is a 1-minute OHLC simulation, not tick-perfect execution.",
        "- News slippage is modeled with adverse entry and exit slippage.",
        "- If both stop orders are touched in the same 1-minute candle, the default policy skips that event.",
        "- Demo forward testing is required before risking real money.",
    ]
    (ROOT / "BACKTEST_REPORT.md").write_text("\n".join(report), encoding="utf-8")
    print("Best config saved:", ROOT / "config.best.json")
    print("Backtest results:", ROOT / "backtest_results.csv")
    print("Report:", ROOT / "BACKTEST_REPORT.md")
    print(result.head(10)[["event_filter", "buffer_points", "sl_extra_points", "tp_r", "be_at_r", "trigger_window_minutes", "max_hold_minutes", "max_setup_range_points", "entry_slippage_points", "trades", "win_rate", "total_r", "avg_r", "profit_factor", "max_drawdown_r", "objective"]].to_string(index=False))
    mt5.shutdown()


if __name__ == "__main__":
    main()
