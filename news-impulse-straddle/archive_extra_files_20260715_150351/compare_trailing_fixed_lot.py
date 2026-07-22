from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import MetaTrader5 as mt5
import pandas as pd

from backtest_news_straddle import StrategyConfig, connect_mt5, fetch_m1, iter_events
from compare_rr_fixed_lot import money_for_r
from news_events import NEWS_EVENTS


ROOT = Path(__file__).resolve().parent


def setup_levels(df: pd.DataFrame, event, config: StrategyConfig):
    release = pd.Timestamp(event.release_utc)
    setup_start = release - pd.Timedelta(minutes=config.setup_candle_minutes_before + 1)
    setup_end = release - pd.Timedelta(minutes=config.setup_candle_minutes_before)
    setup = df[(df["time"] >= setup_start) & (df["time"] < setup_end)]
    if setup.empty:
        return None
    candle = setup.iloc[-1]
    high = float(candle.high)
    low = float(candle.low)
    setup_range = high - low
    if setup_range <= 0 or setup_range > config.max_setup_range_points:
        return None
    return high, low, setup_range


def simulate_trailing_event(df: pd.DataFrame, event, config: StrategyConfig, trail_start_r: float, trail_distance_r: float, max_hold_minutes: int) -> dict:
    levels = setup_levels(df, event, config)
    if levels is None:
        return {"status": "filtered", "r": 0.0}
    high, low, setup_range = levels
    release = pd.Timestamp(event.release_utc)

    buy_entry_raw = high + config.buffer_points
    sell_entry_raw = low - config.buffer_points
    buy_sl_raw = low - config.sl_extra_points
    sell_sl_raw = high + config.sl_extra_points

    trigger_end = release + pd.Timedelta(minutes=config.trigger_window_minutes)
    trigger_bars = df[(df["time"] >= release) & (df["time"] < trigger_end)]
    side = None
    trigger_time = None
    for _, bar in trigger_bars.iterrows():
        hit_buy = float(bar.high) >= buy_entry_raw
        hit_sell = float(bar.low) <= sell_entry_raw
        if hit_buy and hit_sell:
            return {"status": "both_sides_same_bar_skip", "r": 0.0, "setup_range": setup_range}
        if hit_buy:
            side = "buy"; trigger_time = bar.time; break
        if hit_sell:
            side = "sell"; trigger_time = bar.time; break
    if side is None:
        return {"status": "no_trigger", "r": 0.0, "setup_range": setup_range}

    if side == "buy":
        entry = buy_entry_raw + config.entry_slippage_points
        sl = buy_sl_raw - config.exit_slippage_points
        risk = entry - sl
    else:
        entry = sell_entry_raw - config.entry_slippage_points
        sl = sell_sl_raw + config.exit_slippage_points
        risk = sl - entry
    if risk <= 0:
        return {"status": "bad_risk", "r": 0.0, "setup_range": setup_range}

    manage_end = release + pd.Timedelta(minutes=max_hold_minutes)
    bars = df[(df["time"] >= trigger_time) & (df["time"] <= manage_end)]
    best_r = 0.0
    stop = sl
    trailing_active = False

    for _, bar in bars.iterrows():
        h = float(bar.high)
        l = float(bar.low)
        close = float(bar.close)
        if side == "buy":
            best_r = max(best_r, (h - entry) / risk)
            if best_r >= trail_start_r:
                trailing_active = True
                stop = max(stop, entry, h - trail_distance_r * risk)
            if l <= stop:
                r = (stop - entry) / risk
                return {"status": "trail_exit" if trailing_active else "loss", "r": max(-1.0, r), "side": side, "setup_range": setup_range, "best_r": best_r}
        else:
            best_r = max(best_r, (entry - l) / risk)
            if best_r >= trail_start_r:
                trailing_active = True
                stop = min(stop, entry, l + trail_distance_r * risk)
            if h >= stop:
                r = (entry - stop) / risk
                return {"status": "trail_exit" if trailing_active else "loss", "r": max(-1.0, r), "side": side, "setup_range": setup_range, "best_r": best_r}

    if len(bars):
        last = float(bars.iloc[-1].close)
        r = (last - entry) / risk if side == "buy" else (entry - last) / risk
        return {"status": "timeout", "r": max(-1.0, r), "side": side, "setup_range": setup_range, "best_r": best_r}
    return {"status": "no_manage_bars", "r": 0.0, "setup_range": setup_range}


def main() -> None:
    connect_mt5()
    symbol = "XAUUSDm"
    volume = 0.20
    base = StrategyConfig(
        symbol=symbol,
        event_filter="tier1_pce",
        setup_candle_minutes_before=1,
        buffer_points=5.0,
        sl_extra_points=10.0,
        tp_r=999.0,
        be_at_r=1.0,
        trigger_window_minutes=1,
        max_hold_minutes=120,
        max_setup_range_points=12.0,
        entry_slippage_points=1.0,
        exit_slippage_points=1.0,
        same_bar_policy="skip",
    )
    data = {event: fetch_m1(symbol, event) for event in NEWS_EVENTS}
    data = {k: v for k, v in data.items() if v is not None}

    rows = []
    details = []
    for trail_start_r in [1.0, 1.5, 2.0, 3.0]:
        for trail_distance_r in [0.5, 0.75, 1.0, 1.5, 2.0, 3.0]:
            for max_hold in [60, 120, 180, 240]:
                event_rows = []
                for event in iter_events(base):
                    df = data.get(event)
                    if df is None:
                        continue
                    out = simulate_trailing_event(df, event, base, trail_start_r, trail_distance_r, max_hold)
                    out["event"] = f"{event.date_label} {event.name}"
                    out["event_type"] = event.event_type
                    out["trail_start_r"] = trail_start_r
                    out["trail_distance_r"] = trail_distance_r
                    out["max_hold_minutes"] = max_hold
                    if out.get("side") in {"buy", "sell"}:
                        levels = setup_levels(df, event, base)
                        high, low, _ = levels
                        if out["side"] == "buy":
                            entry = high + base.buffer_points + base.entry_slippage_points
                            sl = low - base.sl_extra_points - base.exit_slippage_points
                        else:
                            entry = low - base.buffer_points - base.entry_slippage_points
                            sl = high + base.sl_extra_points + base.exit_slippage_points
                        out["usd"] = money_for_r(symbol, out["side"], volume, entry, sl, float(out["r"]))
                        out["risk_usd"] = abs(money_for_r(symbol, out["side"], volume, entry, sl, -1.0))
                    else:
                        out["usd"] = 0.0
                    event_rows.append(out)
                    details.append(out)
                trades = [r for r in event_rows if r["status"] in {"trail_exit", "loss", "timeout"}]
                total_usd = sum(float(t["usd"]) for t in trades)
                total_r = sum(float(t["r"]) for t in trades)
                wins = [t for t in trades if float(t["r"]) > 0]
                losses = [t for t in trades if float(t["r"]) < 0]
                equity = 0.0; peak = 0.0; max_dd = 0.0
                for t in trades:
                    equity += float(t["usd"])
                    peak = max(peak, equity)
                    max_dd = max(max_dd, peak - equity)
                rows.append({
                    "trail_start_r": trail_start_r,
                    "trail_distance_r": trail_distance_r,
                    "max_hold_minutes": max_hold,
                    "trades": len(trades),
                    "wins": len(wins),
                    "losses": len(losses),
                    "win_rate": len(wins)/len(trades) if trades else 0,
                    "total_r": total_r,
                    "total_usd_0_20_lot": total_usd,
                    "avg_usd_per_trade": total_usd/len(trades) if trades else 0,
                    "max_drawdown_usd": max_dd,
                })

    result = pd.DataFrame(rows).sort_values(["total_usd_0_20_lot", "max_drawdown_usd"], ascending=[False, True])
    detail_df = pd.DataFrame(details)
    result.to_csv(ROOT / "trailing_fixed_0_20_comparison.csv", index=False)
    detail_df.to_csv(ROOT / "trailing_fixed_0_20_trade_details.csv", index=False)
    report = [
        "# Trailing Stop Fixed 0.20 Lot Comparison",
        "",
        "Assumptions:",
        "",
        "- Symbol: `XAUUSDm`",
        "- Fixed lot: `0.20`",
        "- Buffer: `$5` beyond last closed M1 high/low",
        "- SL room: opposite side + `$10` extra",
        "- No fixed TP; runner exits by trailing stop or max hold",
        "- Event set: CPI / NFP / FOMC / PCE",
        "",
        "## Ranked results",
        "",
        result.head(25).to_markdown(index=False),
    ]
    (ROOT / "TRAILING_FIXED_0_20_REPORT.md").write_text("\n".join(report), encoding="utf-8")
    print(result.head(25).to_string(index=False))
    print("Saved:", ROOT / "TRAILING_FIXED_0_20_REPORT.md")
    mt5.shutdown()


if __name__ == "__main__":
    main()

