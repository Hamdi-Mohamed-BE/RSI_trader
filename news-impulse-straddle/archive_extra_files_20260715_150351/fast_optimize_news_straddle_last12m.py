from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import MetaTrader5 as mt5
import pandas as pd

from account_sim_last_12m_500_0_10 import LAST_12M_EVENTS, fetch_event_m1
from backtest_news_straddle import connect_mt5


ROOT = Path(__file__).resolve().parent


EVENT_GROUPS: dict[str, set[str]] = {
    "cpi_nfp_fomc_pce": {"CPI", "NFP", "FOMC", "PCE"},
    "cpi_nfp_fomc": {"CPI", "NFP", "FOMC"},
    "cpi_nfp": {"CPI", "NFP"},
    "cpi_only": {"CPI"},
    "nfp_only": {"NFP"},
    "fomc_only": {"FOMC"},
}


@dataclass(frozen=True)
class PreparedEvent:
    label: str
    event_type: str
    is_fomc_minutes: bool
    setup_high: float
    setup_low: float
    setup_range: float
    trigger_high: float
    trigger_low: float
    highs: tuple[float, ...]
    lows: tuple[float, ...]
    closes: tuple[float, ...]


def prepare_events() -> list[PreparedEvent]:
    out: list[PreparedEvent] = []
    for event in LAST_12M_EVENTS:
        if event.event_type not in {"CPI", "NFP", "FOMC", "PCE"}:
            continue
        df = fetch_event_m1("XAUUSDm", event)
        if df is None:
            continue
        release = pd.Timestamp(event.release_utc)
        setup = df[(df["time"] >= release - pd.Timedelta(minutes=2)) & (df["time"] < release - pd.Timedelta(minutes=1))]
        trigger = df[(df["time"] >= release) & (df["time"] < release + pd.Timedelta(minutes=1))]
        manage = df[(df["time"] >= release) & (df["time"] <= release + pd.Timedelta(minutes=720))]
        if setup.empty or trigger.empty or manage.empty:
            continue
        candle = setup.iloc[-1]
        setup_high = float(candle.high)
        setup_low = float(candle.low)
        setup_range = setup_high - setup_low
        if setup_range <= 0:
            continue
        out.append(
            PreparedEvent(
                label=f"{event.date_label} {event.name}",
                event_type=event.event_type,
                is_fomc_minutes=event.event_type == "FOMC" and "minutes" in event.name.lower(),
                setup_high=setup_high,
                setup_low=setup_low,
                setup_range=setup_range,
                trigger_high=float(trigger.iloc[0].high),
                trigger_low=float(trigger.iloc[0].low),
                highs=tuple(float(x) for x in manage["high"]),
                lows=tuple(float(x) for x in manage["low"]),
                closes=tuple(float(x) for x in manage["close"]),
            )
        )
    return out


def simulate_event(
    event: PreparedEvent,
    buffer_points: float,
    sl_extra_points: float,
    max_setup_range_points: float,
    max_risk_usd: float,
    trail_start_r: float,
    trail_distance_r: float,
    max_hold_minutes: int,
) -> dict:
    if event.setup_range > max_setup_range_points:
        return {"status": "filtered_big_setup", "r": 0.0}

    buy_raw = event.setup_high + buffer_points
    sell_raw = event.setup_low - buffer_points
    buy_hit = event.trigger_high >= buy_raw
    sell_hit = event.trigger_low <= sell_raw

    if buy_hit and sell_hit:
        return {"status": "both_sides_same_bar_skip", "r": 0.0}
    if not buy_hit and not sell_hit:
        return {"status": "no_trigger", "r": 0.0}

    side = "buy" if buy_hit else "sell"
    if side == "buy":
        entry = buy_raw + 1.0
        stop = event.setup_low - sl_extra_points - 1.0
        risk = entry - stop
    else:
        entry = sell_raw - 1.0
        stop = event.setup_high + sl_extra_points + 1.0
        risk = stop - entry

    if risk <= 0:
        return {"status": "bad_risk", "r": 0.0}

    # XAU standard CFD: 0.10 lot is normally $10 per $1 move. This matches MT5 order_calc_profit
    # closely for the existing XAUUSDm test data and avoids thousands of slow broker calls.
    risk_usd = risk * 10.0
    if risk_usd > max_risk_usd:
        return {"status": "filtered_risk_too_large", "r": 0.0, "side": side, "risk_usd": risk_usd}

    best_r = 0.0
    trailing_active = False
    stop_now = stop
    limit = min(max_hold_minutes + 1, len(event.highs))

    for i in range(limit):
        high = event.highs[i]
        low = event.lows[i]
        if side == "buy":
            best_r = max(best_r, (high - entry) / risk)
            if best_r >= trail_start_r:
                trailing_active = True
                stop_now = max(stop_now, entry, high - trail_distance_r * risk)
            if low <= stop_now:
                r = max(-1.0, (stop_now - entry) / risk)
                return {"status": "trail_exit" if trailing_active else "loss", "r": r, "side": side, "best_r": best_r, "risk_usd": risk_usd}
        else:
            best_r = max(best_r, (entry - low) / risk)
            if best_r >= trail_start_r:
                trailing_active = True
                stop_now = min(stop_now, entry, low + trail_distance_r * risk)
            if high >= stop_now:
                r = max(-1.0, (entry - stop_now) / risk)
                return {"status": "trail_exit" if trailing_active else "loss", "r": r, "side": side, "best_r": best_r, "risk_usd": risk_usd}

    close = event.closes[limit - 1]
    r = (close - entry) / risk if side == "buy" else (entry - close) / risk
    return {"status": "timeout", "r": max(-1.0, r), "side": side, "best_r": best_r, "risk_usd": risk_usd}


def run_combo(events: list[PreparedEvent], params: dict) -> tuple[dict, list[dict]]:
    balance = 500.0
    peak = 500.0
    max_dd = 0.0
    min_balance = 500.0
    rows = []

    for event in events:
        if event.event_type not in EVENT_GROUPS[params["event_group"]]:
            continue
        if params["skip_fomc_minutes"] and event.is_fomc_minutes:
            continue
        result = simulate_event(
            event,
            params["buffer_points"],
            params["sl_extra_points"],
            params["max_setup_range_points"],
            params["max_risk_usd"],
            params["trail_start_r"],
            params["trail_distance_r"],
            params["max_hold_minutes"],
        )
        pnl = float(result.get("r", 0.0)) * float(result.get("risk_usd", 0.0))
        balance += pnl
        peak = max(peak, balance)
        min_balance = min(min_balance, balance)
        max_dd = max(max_dd, peak - balance)
        rows.append(
            {
                "event": event.label,
                "type": event.event_type,
                "status": result["status"],
                "side": result.get("side", ""),
                "r": result.get("r", 0.0),
                "best_r": result.get("best_r", ""),
                "risk_usd_0_10": result.get("risk_usd", 0.0),
                "pnl_usd_0_10": pnl,
                "balance_after": balance,
                "drawdown_from_peak": peak - balance,
            }
        )

    df = pd.DataFrame(rows)
    trades = df[df["status"].isin(["trail_exit", "loss", "timeout"])] if len(df) else df
    wins = trades[trades["pnl_usd_0_10"] > 0] if len(trades) else trades
    losses = trades[trades["pnl_usd_0_10"] < 0] if len(trades) else trades
    summary = {
        **params,
        "trades": len(trades),
        "wins": len(wins),
        "losses": len(losses),
        "win_rate": len(wins) / len(trades) if len(trades) else 0.0,
        "total_r": float(trades["r"].sum()) if len(trades) else 0.0,
        "final_balance": balance,
        "net_usd": balance - 500.0,
        "return_pct": (balance / 500.0 - 1) * 100,
        "max_drawdown_usd": max_dd,
        "min_balance": min_balance,
        "below_zero": bool((df["balance_after"] <= 0).any()) if len(df) else False,
        "filtered_risk": int(df["status"].eq("filtered_risk_too_large").sum()) if len(df) else 0,
        "no_trigger": int(df["status"].eq("no_trigger").sum()) if len(df) else 0,
    }
    summary["robust_score"] = summary["net_usd"] - 1.0 * summary["max_drawdown_usd"] + 40.0 * min(summary["trades"], 18)
    return summary, rows


def main() -> None:
    connect_mt5()
    events = prepare_events()
    mt5.shutdown()

    param_rows = []
    for event_group in ["cpi_nfp_fomc_pce", "cpi_nfp_fomc", "cpi_nfp", "cpi_only"]:
        for skip_fomc_minutes in [False, True]:
            for buffer_points in [5.0, 8.0, 12.0, 20.0]:
                for sl_extra_points in [10.0, 20.0]:
                    for max_setup_range_points in [8.0, 12.0, 25.0]:
                        for max_risk_usd in [200.0, 250.0, 9999.0]:
                            for trail_start_r in [7.0, 10.0]:
                                for trail_distance_r in [1.0, 2.0]:
                                    for max_hold_minutes in [120]:
                                        param_rows.append(
                                            {
                                                "event_group": event_group,
                                                "skip_fomc_minutes": skip_fomc_minutes,
                                                "buffer_points": buffer_points,
                                                "sl_extra_points": sl_extra_points,
                                                "max_setup_range_points": max_setup_range_points,
                                                "max_risk_usd": max_risk_usd,
                                                "trail_start_r": trail_start_r,
                                                "trail_distance_r": trail_distance_r,
                                                "max_hold_minutes": max_hold_minutes,
                                            }
                                        )

    summaries = []
    best_rows_by_id = {}
    for i, params in enumerate(param_rows):
        summary, rows = run_combo(events, params)
        if summary["trades"] >= 4 and not summary["below_zero"]:
            summary["combo_id"] = i
            summaries.append(summary)
            best_rows_by_id[i] = rows

    summary_df = pd.DataFrame(summaries)
    summary_df = summary_df.sort_values(["robust_score", "net_usd", "max_drawdown_usd"], ascending=[False, False, True]).reset_index(drop=True)
    summary_df.to_csv(ROOT / "fast_loss_reduction_optimization.csv", index=False)

    best = summary_df.iloc[0]
    best_rows = pd.DataFrame(best_rows_by_id[int(best["combo_id"])])
    best_rows.to_csv(ROOT / "fast_loss_reduction_best_trades.csv", index=False)

    baseline_params = {
        "event_group": "cpi_nfp_fomc_pce",
        "skip_fomc_minutes": False,
        "buffer_points": 5.0,
        "sl_extra_points": 10.0,
        "max_setup_range_points": 12.0,
        "max_risk_usd": 9999.0,
        "trail_start_r": 7.0,
        "trail_distance_r": 1.0,
        "max_hold_minutes": 120,
    }
    baseline, baseline_rows = run_combo(events, baseline_params)
    baseline_df = pd.DataFrame(baseline_rows)
    baseline_losses = baseline_df[baseline_df["status"].eq("loss")].copy()
    baseline_losses.to_csv(ROOT / "fast_baseline_losses.csv", index=False)

    report = [
        "# Fast Last 12M News Straddle Loss Reduction Optimization",
        "",
        "Baseline:",
        "",
        pd.DataFrame([baseline]).to_markdown(index=False),
        "",
        "Best robust setting:",
        "",
        best.to_frame().T.to_markdown(index=False),
        "",
        "Top 30:",
        "",
        summary_df.head(30).to_markdown(index=False),
        "",
        "Baseline losses:",
        "",
        baseline_losses[["event", "type", "side", "best_r", "risk_usd_0_10", "pnl_usd_0_10", "balance_after"]].to_markdown(index=False),
        "",
        "Best setting trade path:",
        "",
        best_rows[["event", "type", "status", "side", "r", "best_r", "risk_usd_0_10", "pnl_usd_0_10", "balance_after", "drawdown_from_peak"]].to_markdown(index=False),
    ]
    (ROOT / "FAST_LOSS_REDUCTION_REPORT.md").write_text("\n".join(report), encoding="utf-8")

    print("BASELINE")
    print(pd.DataFrame([baseline]).to_string(index=False))
    print()
    print("BEST")
    print(best.to_string())
    print()
    print("TOP 20")
    print(summary_df.head(20).to_string(index=False))
    print("Saved:", ROOT / "FAST_LOSS_REDUCTION_REPORT.md")


if __name__ == "__main__":
    main()
