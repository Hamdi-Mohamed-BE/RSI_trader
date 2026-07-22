from __future__ import annotations

from pathlib import Path

import MetaTrader5 as mt5
import pandas as pd

from backtest_news_straddle import StrategyConfig, connect_mt5, fetch_m1, iter_events
from compare_trailing_fixed_lot import simulate_trailing_event, setup_levels
from compare_rr_fixed_lot import money_for_r
from news_events import NEWS_EVENTS


ROOT = Path(__file__).resolve().parent


def main() -> None:
    connect_mt5()
    symbol = "XAUUSDm"
    starting_balance = 500.0
    volume = 0.10
    margin_call_floor = 0.0

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
    trail_start_r = 3.0
    trail_distance_r = 1.0

    data = {event: fetch_m1(symbol, event) for event in NEWS_EVENTS}
    data = {k: v for k, v in data.items() if v is not None}

    balance = starting_balance
    peak = starting_balance
    max_dd = 0.0
    rows = []
    ruined = False

    for event in iter_events(config):
        df = data.get(event)
        if df is None:
            continue
        out = simulate_trailing_event(df, event, config, trail_start_r, trail_distance_r, config.max_hold_minutes)
        usd = 0.0
        risk_usd = 0.0
        if out.get("side") in {"buy", "sell"}:
            levels = setup_levels(df, event, config)
            high, low, _ = levels
            if out["side"] == "buy":
                entry = high + config.buffer_points + config.entry_slippage_points
                sl = low - config.sl_extra_points - config.exit_slippage_points
            else:
                entry = low - config.buffer_points - config.entry_slippage_points
                sl = high + config.sl_extra_points + config.exit_slippage_points
            usd = money_for_r(symbol, out["side"], volume, entry, sl, float(out.get("r", 0.0)))
            risk_usd = abs(money_for_r(symbol, out["side"], volume, entry, sl, -1.0))
        balance_before = balance
        balance += usd
        peak = max(peak, balance)
        max_dd = max(max_dd, peak - balance)
        if balance <= margin_call_floor:
            ruined = True
        rows.append({
            "event": f"{event.date_label} {event.name}",
            "type": event.event_type,
            "status": out.get("status"),
            "side": out.get("side", ""),
            "r": float(out.get("r", 0.0)),
            "risk_usd_0_10": risk_usd,
            "pnl_usd_0_10": usd,
            "balance_before": balance_before,
            "balance_after": balance,
            "drawdown_from_peak": peak - balance,
        })

    df = pd.DataFrame(rows)
    df.to_csv(ROOT / "account_sim_500_0_10.csv", index=False)

    report = [
        "# Account Simulation: $500 Start, 0.10 Lot",
        "",
        "Strategy:",
        "",
        "- XAUUSDm only",
        "- Buffer: `$5` beyond last closed M1 high/low",
        "- SL room: opposite side + `$10` extra",
        "- Trailing starts at `+3R`",
        "- Trail distance: `1R`",
        "- Max hold: `120 minutes`",
        "- Events: CPI / NFP / FOMC / PCE",
        "",
        "## Result",
        "",
        f"- Starting balance: `${starting_balance:,.2f}`",
        f"- Final balance: `${balance:,.2f}`",
        f"- Net profit: `${balance - starting_balance:,.2f}`",
        f"- Return: `{(balance / starting_balance - 1) * 100:.1f}%`",
        f"- Max drawdown: `${max_dd:,.2f}`",
        f"- Ruined / balance <= 0: `{ruined}`",
        "",
        "## Trade path",
        "",
        df.to_markdown(index=False),
    ]
    (ROOT / "ACCOUNT_SIM_500_0_10_REPORT.md").write_text("\n".join(report), encoding="utf-8")
    print("\n".join(report[:22]))
    print(df[["event", "status", "side", "r", "risk_usd_0_10", "pnl_usd_0_10", "balance_after"]].to_string(index=False))
    print("Saved:", ROOT / "ACCOUNT_SIM_500_0_10_REPORT.md")
    mt5.shutdown()


if __name__ == "__main__":
    main()

