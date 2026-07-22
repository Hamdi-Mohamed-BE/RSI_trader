from __future__ import annotations

from pathlib import Path

import MetaTrader5 as mt5
import pandas as pd

from account_sim_last_12m_500_0_10 import LAST_12M_EVENTS, fetch_event_m1
from backtest_news_straddle import StrategyConfig, connect_mt5
from compare_trailing_fixed_lot import setup_levels
from compare_rr_fixed_lot import money_for_r


ROOT = Path(__file__).resolve().parent


def simulate_be_then_trail_event(
    df: pd.DataFrame,
    event,
    config: StrategyConfig,
    be_at_r: float,
    trail_start_r: float,
    trail_distance_r: float,
    max_hold_minutes: int,
) -> dict:
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
        original_stop = low - config.sl_extra_points - config.exit_slippage_points
        risk = entry - original_stop
    else:
        entry = sell_entry_raw - config.entry_slippage_points
        original_stop = high + config.sl_extra_points + config.exit_slippage_points
        risk = original_stop - entry

    if risk <= 0:
        return {"status": "bad_risk", "r": 0.0, "setup_range": setup_range}

    manage_end = release + pd.Timedelta(minutes=max_hold_minutes)
    bars = df[(df["time"] >= trigger_time) & (df["time"] <= manage_end)]

    stop = original_stop
    best_r = 0.0
    be_active = False
    trailing_active = False

    for _, bar in bars.iterrows():
        h = float(bar.high)
        l = float(bar.low)

        if side == "buy":
            best_r = max(best_r, (h - entry) / risk)
            if best_r >= be_at_r:
                be_active = True
                stop = max(stop, entry)
            if best_r >= trail_start_r:
                trailing_active = True
                stop = max(stop, h - trail_distance_r * risk)
            if l <= stop:
                r = (stop - entry) / risk
                status = "trail_exit" if trailing_active else "breakeven" if be_active else "loss"
                return {
                    "status": status,
                    "r": max(-1.0, r),
                    "side": side,
                    "setup_range": setup_range,
                    "best_r": best_r,
                }
        else:
            best_r = max(best_r, (entry - l) / risk)
            if best_r >= be_at_r:
                be_active = True
                stop = min(stop, entry)
            if best_r >= trail_start_r:
                trailing_active = True
                stop = min(stop, l + trail_distance_r * risk)
            if h >= stop:
                r = (entry - stop) / risk
                status = "trail_exit" if trailing_active else "breakeven" if be_active else "loss"
                return {
                    "status": status,
                    "r": max(-1.0, r),
                    "side": side,
                    "setup_range": setup_range,
                    "best_r": best_r,
                }

    if len(bars):
        last = float(bars.iloc[-1].close)
        r = (last - entry) / risk if side == "buy" else (entry - last) / risk
        return {"status": "timeout", "r": max(-1.0, r), "side": side, "setup_range": setup_range, "best_r": best_r}

    return {"status": "no_manage_bars", "r": 0.0, "setup_range": setup_range}


def main() -> None:
    connect_mt5()
    symbol = "XAUUSDm"
    volume = 0.10
    start_balance = 500.0

    config = StrategyConfig(
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

    data = {}
    for event in LAST_12M_EVENTS:
        if event.event_type not in {"CPI", "NFP", "FOMC", "PCE"}:
            continue
        data[event] = fetch_event_m1(symbol, event)

    summary_rows = []
    all_details = []

    for trail_start_r in [2.0, 3.0, 4.0, 5.0, 7.0, 10.0]:
        for trail_distance_r in [0.75, 1.0, 1.5, 2.0, 3.0, 4.0]:
            for max_hold_minutes in [120, 240, 360, 720]:
                balance = start_balance
                peak = start_balance
                max_dd = 0.0
                min_balance = start_balance
                rows = []

                for event, df in data.items():
                    event_name = f"{event.date_label} {event.name}"
                    if df is None:
                        rows.append({"event": event_name, "type": event.event_type, "status": "no_data", "balance_after": balance})
                        continue

                    out = simulate_be_then_trail_event(
                        df,
                        event,
                        config,
                        be_at_r=1.0,
                        trail_start_r=trail_start_r,
                        trail_distance_r=trail_distance_r,
                        max_hold_minutes=max_hold_minutes,
                    )

                    usd = 0.0
                    risk_usd = 0.0
                    entry = ""
                    sl = ""
                    if out.get("side") in {"buy", "sell"}:
                        levels = setup_levels(df, event, config)
                        if levels is not None:
                            high, low, _ = levels
                            if out["side"] == "buy":
                                entry = high + config.buffer_points + config.entry_slippage_points
                                sl = low - config.sl_extra_points - config.exit_slippage_points
                            else:
                                entry = low - config.buffer_points - config.entry_slippage_points
                                sl = high + config.sl_extra_points + config.exit_slippage_points
                            usd = money_for_r(symbol, out["side"], volume, entry, sl, float(out.get("r", 0.0)))
                            risk_usd = abs(money_for_r(symbol, out["side"], volume, entry, sl, -1.0))

                    balance += usd
                    peak = max(peak, balance)
                    min_balance = min(min_balance, balance)
                    max_dd = max(max_dd, peak - balance)
                    rows.append(
                        {
                            "event": event_name,
                            "type": event.event_type,
                            "status": out.get("status"),
                            "side": out.get("side", ""),
                            "r": float(out.get("r", 0.0)),
                            "best_r": out.get("best_r", ""),
                            "entry": entry,
                            "sl": sl,
                            "risk_usd_0_10": risk_usd,
                            "pnl_usd_0_10": usd,
                            "balance_after": balance,
                        }
                    )

                result = pd.DataFrame(rows)
                trade_rows = result[result["status"].isin(["trail_exit", "loss", "timeout", "breakeven"])]
                wins = trade_rows[trade_rows["pnl_usd_0_10"] > 0]
                losses = trade_rows[trade_rows["pnl_usd_0_10"] < 0]
                be = trade_rows[trade_rows["status"].eq("breakeven")]
                summary_rows.append(
                    {
                        "trail_start_r": trail_start_r,
                        "trail_distance_r": trail_distance_r,
                        "max_hold_minutes": max_hold_minutes,
                        "trades": len(trade_rows),
                        "wins": len(wins),
                        "losses": len(losses),
                        "breakevens": len(be),
                        "win_rate": len(wins) / len(trade_rows) if len(trade_rows) else 0.0,
                        "total_r": float(trade_rows["r"].sum()) if len(trade_rows) else 0.0,
                        "final_balance": balance,
                        "net_usd": balance - start_balance,
                        "return_pct": (balance / start_balance - 1) * 100,
                        "max_drawdown_usd": max_dd,
                        "min_balance": min_balance,
                        "below_zero": bool((result["balance_after"] <= 0).any()),
                    }
                )

                for row in rows:
                    row["trail_start_r"] = trail_start_r
                    row["trail_distance_r"] = trail_distance_r
                    row["max_hold_minutes"] = max_hold_minutes
                    all_details.append(row)

    summary = pd.DataFrame(summary_rows)
    summary = summary.sort_values(["below_zero", "final_balance", "max_drawdown_usd"], ascending=[True, False, True])
    details = pd.DataFrame(all_details)

    summary.to_csv(ROOT / "last12m_trailing_rr_500_0_10_comparison.csv", index=False)
    details.to_csv(ROOT / "last12m_trailing_rr_500_0_10_details.csv", index=False)

    best = summary.iloc[0]
    best_details = details[
        (details["trail_start_r"] == best["trail_start_r"])
        & (details["trail_distance_r"] == best["trail_distance_r"])
        & (details["max_hold_minutes"] == best["max_hold_minutes"])
    ]
    best_details.to_csv(ROOT / "last12m_trailing_rr_500_0_10_best_trades.csv", index=False)

    report = [
        "# Last 12 Months Bigger Runner / Trailing Stop Optimization",
        "",
        "Strategy: XAU news straddle, fixed 0.10 lot, $500 starting account.",
        "",
        "Common settings:",
        "",
        "- Buffer: `$5` beyond last closed M1 high/low",
        "- Stop: opposite side of setup candle + `$10` extra room",
        "- Move stop to breakeven after `+1R`",
        "- Then activate trailing stop only after the tested runner R threshold",
        "- Event set: CPI / NFP / FOMC / PCE",
        "",
        "## Best result",
        "",
        best.to_frame().T.to_markdown(index=False),
        "",
        "## Top 25 combinations",
        "",
        summary.head(25).to_markdown(index=False),
        "",
        "## Best-combo trade path",
        "",
        best_details[["event", "status", "side", "r", "best_r", "pnl_usd_0_10", "balance_after"]].to_markdown(index=False),
    ]
    (ROOT / "LAST12M_TRAILING_RR_500_0_10_REPORT.md").write_text("\n".join(report), encoding="utf-8")

    print("BEST")
    print(best.to_string())
    print()
    print("TOP 15")
    print(summary.head(15).to_string(index=False))
    print("Saved:", ROOT / "LAST12M_TRAILING_RR_500_0_10_REPORT.md")
    mt5.shutdown()


if __name__ == "__main__":
    main()
