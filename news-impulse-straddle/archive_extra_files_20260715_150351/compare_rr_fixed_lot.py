from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import MetaTrader5 as mt5
import pandas as pd

from backtest_news_straddle import StrategyConfig, connect_mt5, fetch_m1, iter_events, simulate_event
from news_events import NEWS_EVENTS


ROOT = Path(__file__).resolve().parent


def money_for_r(symbol: str, side: str, volume: float, entry: float, sl: float, r_value: float) -> float:
    info_type = mt5.ORDER_TYPE_BUY if side == "buy" else mt5.ORDER_TYPE_SELL
    risk_distance = abs(entry - sl)
    if side == "buy":
        exit_price = entry + r_value * risk_distance
    else:
        exit_price = entry - r_value * risk_distance
    profit = mt5.order_calc_profit(info_type, symbol, volume, entry, exit_price)
    return float(profit or 0.0)


def simulate_event_with_money(df: pd.DataFrame, event, config: StrategyConfig, volume: float) -> dict:
    out = simulate_event(df, event, config)
    out["event"] = f"{event.date_label} {event.name}"
    out["event_type"] = event.event_type
    out["usd"] = 0.0
    # Reconstruct planned entry/sl from setup candle for fixed-lot USD estimate.
    side = out.get("side")
    if side in {"buy", "sell"}:
        release = pd.Timestamp(event.release_utc)
        setup_start = release - pd.Timedelta(minutes=config.setup_candle_minutes_before + 1)
        setup_end = release - pd.Timedelta(minutes=config.setup_candle_minutes_before)
        setup = df[(df["time"] >= setup_start) & (df["time"] < setup_end)]
        if not setup.empty:
            candle = setup.iloc[-1]
            high = float(candle.high)
            low = float(candle.low)
            if side == "buy":
                entry = high + config.buffer_points + config.entry_slippage_points
                sl = low - config.sl_extra_points - config.exit_slippage_points
            else:
                entry = low - config.buffer_points - config.entry_slippage_points
                sl = high + config.sl_extra_points + config.exit_slippage_points
            out["usd"] = money_for_r(config.symbol, side, volume, entry, sl, float(out.get("r", 0.0)))
            out["risk_usd"] = abs(money_for_r(config.symbol, side, volume, entry, sl, -1.0))
    return out


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
        tp_r=3.0,
        be_at_r=1.0,
        trigger_window_minutes=1,
        max_hold_minutes=30,
        max_setup_range_points=12.0,
        entry_slippage_points=1.0,
        exit_slippage_points=1.0,
        same_bar_policy="skip",
    )
    data = {event: fetch_m1(symbol, event) for event in NEWS_EVENTS}
    data = {k: v for k, v in data.items() if v is not None}

    rows = []
    all_details = []
    for tp_r in [2, 3, 4, 5, 6, 7, 8, 10]:
        for max_hold in [15, 30, 60, 90, 120]:
            config = replace(base, tp_r=float(tp_r), max_hold_minutes=max_hold)
            details = []
            for event in iter_events(config):
                df = data.get(event)
                if df is None:
                    continue
                details.append(simulate_event_with_money(df, event, config, volume))
            trades = [d for d in details if d["status"] in {"win", "loss", "be", "timeout"}]
            total_usd = sum(float(t.get("usd", 0.0)) for t in trades)
            total_r = sum(float(t.get("r", 0.0)) for t in trades)
            risks = [float(t.get("risk_usd", 0.0)) for t in trades if t.get("risk_usd")]
            wins = [t for t in trades if float(t.get("r", 0.0)) > 0]
            losses = [t for t in trades if float(t.get("r", 0.0)) < 0]
            equity = 0.0
            peak = 0.0
            max_dd = 0.0
            for t in trades:
                equity += float(t.get("usd", 0.0))
                peak = max(peak, equity)
                max_dd = max(max_dd, peak - equity)
            rows.append(
                {
                    "tp_r": tp_r,
                    "max_hold_minutes": max_hold,
                    "trades": len(trades),
                    "wins": len(wins),
                    "losses": len(losses),
                    "win_rate": len(wins) / len(trades) if trades else 0,
                    "total_r": total_r,
                    "total_usd_0_20_lot": total_usd,
                    "avg_usd_per_trade": total_usd / len(trades) if trades else 0,
                    "avg_risk_usd": sum(risks) / len(risks) if risks else 0,
                    "max_drawdown_usd": max_dd,
                }
            )
            for d in details:
                d["tp_r"] = tp_r
                d["max_hold_minutes"] = max_hold
                all_details.append(d)

    result = pd.DataFrame(rows).sort_values(
        ["total_usd_0_20_lot", "total_r", "max_drawdown_usd"], ascending=[False, False, True]
    )
    details_df = pd.DataFrame(all_details)
    result.to_csv(ROOT / "rr_fixed_0_20_comparison.csv", index=False)
    details_df.to_csv(ROOT / "rr_fixed_0_20_trade_details.csv", index=False)
    report = [
        "# Fixed 0.20 Lot RR Comparison",
        "",
        "Assumptions:",
        "",
        "- Symbol: `XAUUSDm`",
        "- Fixed lot: `0.20`",
        "- Buffer: `$5` beyond last closed M1 high/low",
        "- SL room: opposite side + `$10` extra",
        "- Event set: CPI / NFP / FOMC / PCE",
        "- Same-bar two-sided trigger: skipped",
        "- Slippage model: `$1` adverse entry and `$1` adverse exit",
        "",
        "## Ranked results",
        "",
        result.head(20).to_markdown(index=False),
    ]
    (ROOT / "RR_FIXED_0_20_REPORT.md").write_text("\n".join(report), encoding="utf-8")
    print(result.head(20).to_string(index=False))
    print("Saved:", ROOT / "RR_FIXED_0_20_REPORT.md")
    mt5.shutdown()


if __name__ == "__main__":
    main()

