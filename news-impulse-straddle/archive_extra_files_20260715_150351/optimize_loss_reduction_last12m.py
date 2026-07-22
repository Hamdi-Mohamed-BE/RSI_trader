from __future__ import annotations

import itertools
from pathlib import Path

import MetaTrader5 as mt5
import pandas as pd

from account_sim_last_12m_500_0_10 import LAST_12M_EVENTS, fetch_event_m1
from backtest_news_straddle import StrategyConfig, connect_mt5
from compare_rr_fixed_lot import money_for_r
from compare_trailing_fixed_lot import setup_levels, simulate_trailing_event


ROOT = Path(__file__).resolve().parent


EVENT_GROUPS: dict[str, set[str]] = {
    "cpi_nfp_fomc_pce": {"CPI", "NFP", "FOMC", "PCE"},
    "cpi_nfp_fomc": {"CPI", "NFP", "FOMC"},
    "cpi_nfp": {"CPI", "NFP"},
    "cpi_fomc": {"CPI", "FOMC"},
    "nfp_fomc": {"NFP", "FOMC"},
    "cpi_only": {"CPI"},
    "nfp_only": {"NFP"},
    "fomc_only": {"FOMC"},
}


def levels_and_risk_usd(df: pd.DataFrame, event, config: StrategyConfig, side: str, volume: float) -> tuple[float, float, float] | None:
    levels = setup_levels(df, event, config)
    if levels is None:
        return None
    high, low, setup_range = levels
    if side == "buy":
        entry = high + config.buffer_points + config.entry_slippage_points
        sl = low - config.sl_extra_points - config.exit_slippage_points
    else:
        entry = low - config.buffer_points - config.entry_slippage_points
        sl = high + config.sl_extra_points + config.exit_slippage_points
    risk_usd = abs(money_for_r(config.symbol, side, volume, entry, sl, -1.0))
    return entry, sl, risk_usd


def run_combo(
    data: dict,
    event_group_name: str,
    allowed_types: set[str],
    skip_fomc_minutes: bool,
    buffer_points: float,
    sl_extra_points: float,
    max_setup_range_points: float,
    max_risk_usd: float,
    trail_start_r: float,
    trail_distance_r: float,
    max_hold_minutes: int,
    volume: float,
    start_balance: float,
) -> tuple[dict, list[dict]]:
    config = StrategyConfig(
        symbol="XAUUSDm",
        event_filter="tier1_pce",
        setup_candle_minutes_before=1,
        buffer_points=buffer_points,
        sl_extra_points=sl_extra_points,
        tp_r=999.0,
        be_at_r=None,
        trigger_window_minutes=1,
        max_hold_minutes=max_hold_minutes,
        max_setup_range_points=max_setup_range_points,
        entry_slippage_points=1.0,
        exit_slippage_points=1.0,
        same_bar_policy="skip",
    )

    balance = start_balance
    peak = start_balance
    max_dd = 0.0
    min_balance = start_balance
    rows: list[dict] = []

    for event, df in data.items():
        if event.event_type not in allowed_types:
            continue
        if skip_fomc_minutes and event.event_type == "FOMC" and "minutes" in event.name.lower():
            continue

        event_label = f"{event.date_label} {event.name}"
        if df is None:
            rows.append({"event": event_label, "type": event.event_type, "status": "no_data", "balance_after": balance})
            continue

        out = simulate_trailing_event(df, event, config, trail_start_r, trail_distance_r, max_hold_minutes)
        usd = 0.0
        risk_usd = 0.0
        entry = ""
        sl = ""

        if out.get("side") in {"buy", "sell"}:
            risk_pack = levels_and_risk_usd(df, event, config, out["side"], volume)
            if risk_pack is not None:
                entry, sl, risk_usd = risk_pack
                if risk_usd > max_risk_usd:
                    out = {
                        "status": "filtered_risk_too_large",
                        "side": out["side"],
                        "r": 0.0,
                        "best_r": out.get("best_r", ""),
                    }
                else:
                    usd = money_for_r(config.symbol, out["side"], volume, float(entry), float(sl), float(out.get("r", 0.0)))

        balance += usd
        peak = max(peak, balance)
        min_balance = min(min_balance, balance)
        max_dd = max(max_dd, peak - balance)
        rows.append(
            {
                "event": event_label,
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
                "drawdown_from_peak": peak - balance,
            }
        )

    result = pd.DataFrame(rows)
    trade_rows = result[result["status"].isin(["trail_exit", "loss", "timeout"])]
    wins = trade_rows[trade_rows["pnl_usd_0_10"] > 0]
    losses = trade_rows[trade_rows["pnl_usd_0_10"] < 0]
    loss_rows = trade_rows[trade_rows["status"].eq("loss")]
    summary = {
        "event_group": event_group_name,
        "skip_fomc_minutes": skip_fomc_minutes,
        "buffer_points": buffer_points,
        "sl_extra_points": sl_extra_points,
        "max_setup_range_points": max_setup_range_points,
        "max_risk_usd": max_risk_usd,
        "trail_start_r": trail_start_r,
        "trail_distance_r": trail_distance_r,
        "max_hold_minutes": max_hold_minutes,
        "trades": len(trade_rows),
        "wins": len(wins),
        "losses": len(losses),
        "loss_stops": len(loss_rows),
        "win_rate": len(wins) / len(trade_rows) if len(trade_rows) else 0.0,
        "total_r": float(trade_rows["r"].sum()) if len(trade_rows) else 0.0,
        "final_balance": balance,
        "net_usd": balance - start_balance,
        "return_pct": (balance / start_balance - 1) * 100,
        "max_drawdown_usd": max_dd,
        "min_balance": min_balance,
        "below_zero": bool((result["balance_after"] <= 0).any()) if len(result) else False,
        "filtered_risk": int(result["status"].eq("filtered_risk_too_large").sum()) if len(result) else 0,
        "skipped_no_trigger": int(result["status"].eq("no_trigger").sum()) if len(result) else 0,
    }
    # Profit with some penalty for drawdown and tiny samples. This ranks for usable settings, not curve-fit moonshots.
    summary["robust_score"] = summary["net_usd"] - 0.8 * summary["max_drawdown_usd"] + 35.0 * min(summary["trades"], 18)
    return summary, rows


def main() -> None:
    connect_mt5()
    symbol = "XAUUSDm"
    volume = 0.10
    start_balance = 500.0

    data = {}
    for event in LAST_12M_EVENTS:
        if event.event_type in {"CPI", "NFP", "FOMC", "PCE"}:
            data[event] = fetch_event_m1(symbol, event)

    summaries = []
    detail_sets: dict[int, list[dict]] = {}
    combo_i = 0

    for (
        event_group_name,
        buffer_points,
        sl_extra_points,
        max_setup_range_points,
        max_risk_usd,
        trail_start_r,
        trail_distance_r,
        max_hold_minutes,
        skip_fomc_minutes,
    ) in itertools.product(
        ["cpi_nfp_fomc_pce", "cpi_nfp_fomc", "cpi_nfp"],
        [5.0, 8.0, 10.0, 12.0, 15.0],
        [10.0, 15.0, 20.0],
        [8.0, 12.0, 16.0],
        [200.0, 225.0, 9999.0],
        [7.0, 10.0],
        [1.0, 1.5],
        [120],
        [False, True],
    ):
        summary, rows = run_combo(
            data=data,
            event_group_name=event_group_name,
            allowed_types=EVENT_GROUPS[event_group_name],
            skip_fomc_minutes=skip_fomc_minutes,
            buffer_points=buffer_points,
            sl_extra_points=sl_extra_points,
            max_setup_range_points=max_setup_range_points,
            max_risk_usd=max_risk_usd,
            trail_start_r=trail_start_r,
            trail_distance_r=trail_distance_r,
            max_hold_minutes=max_hold_minutes,
            volume=volume,
            start_balance=start_balance,
        )
        if summary["trades"] >= 8 and not summary["below_zero"]:
            summary["combo_id"] = combo_i
            summaries.append(summary)
            detail_sets[combo_i] = rows
            combo_i += 1

    summary_df = pd.DataFrame(summaries)
    summary_df = summary_df.sort_values(["robust_score", "net_usd", "max_drawdown_usd"], ascending=[False, False, True]).reset_index(drop=True)
    summary_df.to_csv(ROOT / "loss_reduction_last12m_optimization.csv", index=False)

    best = summary_df.iloc[0]
    best_rows = detail_sets[int(best["combo_id"])]
    best_df = pd.DataFrame(best_rows)
    best_df.to_csv(ROOT / "loss_reduction_last12m_best_trades.csv", index=False)

    # Baseline loss review using the previous known best runner: buffer 5 / SL extra 10 / trail 7R / dist 1R / 120m.
    baseline_summary, baseline_rows = run_combo(
        data=data,
        event_group_name="cpi_nfp_fomc_pce",
        allowed_types=EVENT_GROUPS["cpi_nfp_fomc_pce"],
        skip_fomc_minutes=False,
        buffer_points=5.0,
        sl_extra_points=10.0,
        max_setup_range_points=12.0,
        max_risk_usd=9999.0,
        trail_start_r=7.0,
        trail_distance_r=1.0,
        max_hold_minutes=120,
        volume=volume,
        start_balance=start_balance,
    )
    baseline_df = pd.DataFrame(baseline_rows)
    baseline_losses = baseline_df[baseline_df["status"].eq("loss")].copy()
    if len(baseline_losses):
        baseline_losses["best_r"] = pd.to_numeric(baseline_losses["best_r"], errors="coerce")
        baseline_losses = baseline_losses.sort_values("pnl_usd_0_10")
    baseline_losses.to_csv(ROOT / "loss_reduction_baseline_losses.csv", index=False)

    report = [
        "# Last 12M Loss Reduction Optimization",
        "",
        "Goal: reduce drawdown and false-break losses for XAU news straddle.",
        "",
        "Baseline:",
        "",
        pd.DataFrame([baseline_summary]).to_markdown(index=False),
        "",
        "Best robust configuration:",
        "",
        best.to_frame().T.to_markdown(index=False),
        "",
        "Top 25 robust configurations:",
        "",
        summary_df.head(25).to_markdown(index=False),
        "",
        "Baseline stopped losses, sorted worst first:",
        "",
        baseline_losses[["event", "type", "side", "best_r", "risk_usd_0_10", "pnl_usd_0_10", "balance_after"]].to_markdown(index=False),
        "",
        "Best configuration trade path:",
        "",
        best_df[["event", "type", "status", "side", "r", "best_r", "risk_usd_0_10", "pnl_usd_0_10", "balance_after", "drawdown_from_peak"]].to_markdown(index=False),
    ]
    (ROOT / "LOSS_REDUCTION_LAST12M_REPORT.md").write_text("\n".join(report), encoding="utf-8")

    print("BASELINE")
    print(pd.DataFrame([baseline_summary]).to_string(index=False))
    print()
    print("BEST ROBUST")
    print(best.to_string())
    print()
    print("TOP 15")
    print(summary_df.head(15).to_string(index=False))
    print("Saved:", ROOT / "LOSS_REDUCTION_LAST12M_REPORT.md")
    mt5.shutdown()


if __name__ == "__main__":
    main()
