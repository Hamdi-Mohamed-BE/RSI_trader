from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import MetaTrader5 as mt5
import pandas as pd

from backtest_news_straddle import StrategyConfig, connect_mt5, fetch_m1, iter_events
from compare_trailing_fixed_lot import simulate_trailing_event, setup_levels
from compare_rr_fixed_lot import money_for_r


ROOT = Path(__file__).resolve().parent


@dataclass(frozen=True)
class Event:
    date_label: str
    name: str
    event_type: str
    release_utc: datetime


def dt(y: int, m: int, d: int, hh: int, mm: int) -> datetime:
    return datetime(y, m, d, hh, mm, tzinfo=timezone.utc)


# Last-12-month scheduled catalyst list for XAU backtesting.
# Times are ET releases converted to UTC. Jul-Oct dates use EDT (+4h);
# Nov-Mar dates use EST (+5h); Apr-Jul dates use EDT (+4h).
LAST_12M_EVENTS = [
    # 2025 CPI / PPI / Jobs / FOMC / PCE major windows
    Event("Jul 30 2025", "FOMC Statement", "FOMC", dt(2025, 7, 30, 18, 0)),
    Event("Jul 31 2025", "PCE", "PCE", dt(2025, 7, 31, 12, 30)),
    Event("Aug 01 2025", "NFP / Jobs", "NFP", dt(2025, 8, 1, 12, 30)),
    Event("Aug 12 2025", "CPI", "CPI", dt(2025, 8, 12, 12, 30)),
    Event("Aug 14 2025", "PPI", "PPI", dt(2025, 8, 14, 12, 30)),
    Event("Aug 20 2025", "FOMC Minutes", "FOMC", dt(2025, 8, 20, 18, 0)),
    Event("Aug 29 2025", "PCE", "PCE", dt(2025, 8, 29, 12, 30)),
    Event("Sep 05 2025", "NFP / Jobs", "NFP", dt(2025, 9, 5, 12, 30)),
    Event("Sep 10 2025", "PPI", "PPI", dt(2025, 9, 10, 12, 30)),
    Event("Sep 11 2025", "CPI", "CPI", dt(2025, 9, 11, 12, 30)),
    Event("Sep 17 2025", "FOMC Statement", "FOMC", dt(2025, 9, 17, 18, 0)),
    Event("Sep 26 2025", "PCE", "PCE", dt(2025, 9, 26, 12, 30)),
    Event("Oct 03 2025", "NFP / Jobs", "NFP", dt(2025, 10, 3, 12, 30)),
    Event("Oct 08 2025", "FOMC Minutes", "FOMC", dt(2025, 10, 8, 18, 0)),
    Event("Oct 15 2025", "CPI", "CPI", dt(2025, 10, 15, 12, 30)),
    Event("Oct 16 2025", "PPI", "PPI", dt(2025, 10, 16, 12, 30)),
    Event("Oct 29 2025", "FOMC Statement", "FOMC", dt(2025, 10, 29, 18, 0)),
    Event("Oct 31 2025", "PCE", "PCE", dt(2025, 10, 31, 12, 30)),
    Event("Nov 07 2025", "NFP / Jobs", "NFP", dt(2025, 11, 7, 13, 30)),
    Event("Nov 13 2025", "CPI", "CPI", dt(2025, 11, 13, 13, 30)),
    Event("Nov 19 2025", "FOMC Minutes", "FOMC", dt(2025, 11, 19, 19, 0)),
    Event("Nov 26 2025", "PCE", "PCE", dt(2025, 11, 26, 13, 30)),
    Event("Dec 05 2025", "NFP / Jobs", "NFP", dt(2025, 12, 5, 13, 30)),
    Event("Dec 10 2025", "CPI", "CPI", dt(2025, 12, 10, 13, 30)),
    Event("Dec 10 2025", "FOMC Statement", "FOMC", dt(2025, 12, 10, 19, 0)),
    Event("Dec 11 2025", "PPI", "PPI", dt(2025, 12, 11, 13, 30)),
    Event("Dec 23 2025", "PCE", "PCE", dt(2025, 12, 23, 13, 30)),
    # 2026 windows
    Event("Jan 07 2026", "FOMC Minutes", "FOMC", dt(2026, 1, 7, 19, 0)),
    Event("Jan 09 2026", "NFP / Jobs", "NFP", dt(2026, 1, 9, 13, 30)),
    Event("Jan 13 2026", "CPI", "CPI", dt(2026, 1, 13, 13, 30)),
    Event("Jan 14 2026", "PPI", "PPI", dt(2026, 1, 14, 13, 30)),
    Event("Jan 28 2026", "FOMC Statement", "FOMC", dt(2026, 1, 28, 19, 0)),
    Event("Jan 30 2026", "PCE / PPI", "PCE", dt(2026, 1, 30, 13, 30)),
    Event("Feb 11 2026", "NFP / Jobs", "NFP", dt(2026, 2, 11, 13, 30)),
    Event("Feb 13 2026", "CPI", "CPI", dt(2026, 2, 13, 13, 30)),
    Event("Feb 18 2026", "FOMC Minutes", "FOMC", dt(2026, 2, 18, 19, 0)),
    Event("Feb 27 2026", "PPI / PCE", "PCE", dt(2026, 2, 27, 13, 30)),
    Event("Mar 11 2026", "CPI", "CPI", dt(2026, 3, 11, 12, 30)),
    Event("Mar 18 2026", "PPI / FOMC", "FOMC", dt(2026, 3, 18, 18, 0)),
    Event("Apr 03 2026", "NFP / Jobs", "NFP", dt(2026, 4, 3, 12, 30)),
    Event("Apr 10 2026", "CPI", "CPI", dt(2026, 4, 10, 12, 30)),
    Event("Apr 14 2026", "PPI", "PPI", dt(2026, 4, 14, 12, 30)),
    Event("Apr 29 2026", "FOMC Statement", "FOMC", dt(2026, 4, 29, 18, 0)),
    Event("May 08 2026", "NFP / Jobs", "NFP", dt(2026, 5, 8, 12, 30)),
    Event("May 12 2026", "CPI", "CPI", dt(2026, 5, 12, 12, 30)),
    Event("May 13 2026", "PPI", "PPI", dt(2026, 5, 13, 12, 30)),
    Event("May 20 2026", "FOMC Minutes", "FOMC", dt(2026, 5, 20, 18, 0)),
    Event("May 29 2026", "PCE", "PCE", dt(2026, 5, 29, 12, 30)),
    Event("Jun 05 2026", "NFP / Jobs", "NFP", dt(2026, 6, 5, 12, 30)),
    Event("Jun 10 2026", "CPI", "CPI", dt(2026, 6, 10, 12, 30)),
    Event("Jun 11 2026", "PPI", "PPI", dt(2026, 6, 11, 12, 30)),
    Event("Jun 17 2026", "FOMC Statement", "FOMC", dt(2026, 6, 17, 18, 0)),
    Event("Jun 25 2026", "PCE", "PCE", dt(2026, 6, 25, 12, 30)),
    Event("Jul 02 2026", "NFP / Jobs", "NFP", dt(2026, 7, 2, 12, 30)),
    Event("Jul 08 2026", "FOMC Minutes", "FOMC", dt(2026, 7, 8, 18, 0)),
    Event("Jul 14 2026", "CPI", "CPI", dt(2026, 7, 14, 12, 30)),
]


def fetch_event_m1(symbol: str, event: Event) -> pd.DataFrame | None:
    rates = mt5.copy_rates_range(
        symbol,
        mt5.TIMEFRAME_M1,
        event.release_utc - pd.Timedelta(minutes=10),
        event.release_utc + pd.Timedelta(minutes=260),
    )
    if rates is None or len(rates) < 20:
        return None
    df = pd.DataFrame(rates)
    df["time"] = pd.to_datetime(df["time"], unit="s", utc=True)
    return df


def main() -> None:
    connect_mt5()
    symbol = "XAUUSDm"
    start_balance = 500.0
    volume = 0.10
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

    rows = []
    balance = start_balance
    peak = start_balance
    max_dd = 0.0
    min_balance = start_balance
    for event in LAST_12M_EVENTS:
        if event.event_type not in {"CPI", "NFP", "FOMC", "PCE"}:
            continue
        df = fetch_event_m1(symbol, event)
        if df is None:
            rows.append({"event": f"{event.date_label} {event.name}", "type": event.event_type, "status": "no_data", "balance_after": balance})
            continue
        out = simulate_trailing_event(df, event, config, trail_start_r, trail_distance_r, config.max_hold_minutes)
        usd = 0.0
        risk_usd = 0.0
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
        before = balance
        balance += usd
        peak = max(peak, balance)
        min_balance = min(min_balance, balance)
        max_dd = max(max_dd, peak - balance)
        rows.append({
            "event": f"{event.date_label} {event.name}",
            "type": event.event_type,
            "status": out.get("status"),
            "side": out.get("side", ""),
            "r": float(out.get("r", 0.0)),
            "best_r": out.get("best_r", ""),
            "risk_usd_0_10": risk_usd,
            "pnl_usd_0_10": usd,
            "balance_before": before,
            "balance_after": balance,
            "drawdown_from_peak": peak - balance,
        })

    result = pd.DataFrame(rows)
    result.to_csv(ROOT / "account_sim_last_12m_500_0_10.csv", index=False)
    trade_rows = result[result["status"].isin(["trail_exit", "loss", "timeout"])]
    wins = trade_rows[trade_rows["pnl_usd_0_10"] > 0]
    losses = trade_rows[trade_rows["pnl_usd_0_10"] < 0]
    no_data = result[result["status"].eq("no_data")]
    report = [
        "# Last 12 Months Account Simulation: $500 Start, 0.10 Lot",
        "",
        "Strategy: XAU news straddle trailing runner.",
        "",
        f"- Events listed: `{len(LAST_12M_EVENTS)}`",
        f"- Events with no MT5 data: `{len(no_data)}`",
        f"- Trades taken: `{len(trade_rows)}`",
        f"- Wins: `{len(wins)}`",
        f"- Losses: `{len(losses)}`",
        f"- Win rate: `{(len(wins) / len(trade_rows) * 100) if len(trade_rows) else 0:.1f}%`",
        f"- Starting balance: `${start_balance:,.2f}`",
        f"- Final balance: `${balance:,.2f}`",
        f"- Net: `${balance - start_balance:,.2f}`",
        f"- Return: `{(balance / start_balance - 1) * 100:.1f}%`",
        f"- Max drawdown: `${max_dd:,.2f}`",
        f"- Min balance: `${min_balance:,.2f}`",
        f"- Account below zero: `{bool((result['balance_after'] <= 0).any())}`",
        "",
        "## Trade path",
        "",
        result.to_markdown(index=False),
    ]
    (ROOT / "ACCOUNT_SIM_LAST_12M_500_0_10_REPORT.md").write_text("\n".join(report), encoding="utf-8")
    print("\n".join(report[:18]))
    print(result[["event", "status", "side", "r", "pnl_usd_0_10", "balance_after"]].tail(25).to_string(index=False))
    print("Saved:", ROOT / "ACCOUNT_SIM_LAST_12M_500_0_10_REPORT.md")
    mt5.shutdown()


if __name__ == "__main__":
    main()

