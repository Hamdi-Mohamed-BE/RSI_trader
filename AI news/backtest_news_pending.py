from __future__ import annotations

import csv
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from news_pending_strategy import (
    ROOT,
    Instrument,
    StrategyConfig,
    load_events,
    load_predictions,
    performance,
    simulate_event,
)


START = datetime(2024, 7, 31, tzinfo=timezone.utc)
HOLDOUT_START = datetime(2026, 1, 31, tzinfo=timezone.utc)
END = datetime(2026, 7, 31, tzinfo=timezone.utc)
OUTPUT_JSON = ROOT / "news_pending_2y_results.json"
OUTPUT_CSV = ROOT / "news_pending_2y_trades.csv"
OUTPUT_MD = ROOT / "NEWS_PENDING_2Y_RESULTS.md"

INSTRUMENTS = {
    "eurusd": Instrument("eurusd", pip_size=0.0001),
    "xauusd": Instrument("xauusd", pip_size=0.1),
}
EVENTS = ("NFP", "CPI", "PPI", "GDP", "FOMC")


def _parameter_grid(symbol: str):
    reward_risks = [3.0] if symbol == "eurusd" else [4.0, 5.0, 7.0]
    for mode in ("forecast", "oco"):
        for reward_risk in reward_risks:
            for spread_multiplier in (1.0, 1.5, 2.0):
                for allow_reentry in (False, True):
                    yield StrategyConfig(
                        mode=mode,
                        reward_risk=reward_risk,
                        spread_buffer_multiplier=spread_multiplier,
                        allow_reentry=allow_reentry,
                    )


def _key(config: StrategyConfig) -> str:
    return (
        f"{config.mode}|rr={config.reward_risk:g}|"
        f"spread={config.spread_buffer_multiplier:g}|"
        f"reentry={str(config.allow_reentry).lower()}"
    )


def _run_config(
    symbol: str,
    config: StrategyConfig,
    events: list[dict],
    predictions: dict[str, str],
    *,
    instrument: Instrument | None = None,
    allowed_events: list[str] | None = None,
) -> dict:
    trades = []
    statuses = Counter()
    collisions = 0
    for event in events:
        if allowed_events is not None and event["event"] not in allowed_events:
            statuses["event_filter"] += 1
            continue
        result = simulate_event(
            instrument or INSTRUMENTS[symbol],
            event,
            config,
            predictions.get(event["released"].isoformat()),
        )
        statuses[result["status"]] += 1
        collisions += int(bool(result.get("collision")))
        trades.extend(result["trades"])
    return {
        "symbol": symbol.upper(),
        "config": {
            "mode": config.mode,
            "reward_risk": config.reward_risk,
            "spread_buffer_multiplier": config.spread_buffer_multiplier,
            "min_buffer_pips": config.min_buffer_pips,
            "pending_minutes": config.pending_minutes,
            "max_hold_minutes": config.max_hold_minutes,
            "allow_reentry": config.allow_reentry,
            "reentry_rr": INSTRUMENTS[symbol].reentry_rr,
        },
        "performance": performance(trades),
        "statuses": dict(statuses),
        "same_minute_oco_collisions": collisions,
        "trades_detail": trades,
    }


def _stable_events(
    symbol: str,
    config: StrategyConfig,
    development: list[dict],
    predictions: dict[str, str],
) -> list[str]:
    stable = []
    for event_name in EVENTS:
        result = _run_config(
            symbol,
            config,
            [event for event in development if event["event"] == event_name],
            predictions,
        )
        stats = result["performance"]
        if (
            stats["trades"] >= 8
            and (stats["profit_factor"] or 0.0) >= 1.30
            and stats["net_r"] > 0
        ):
            stable.append(event_name)
    return stable


def _selection_score(result: dict) -> tuple[float, float, int]:
    stats = result["performance"]
    if stats["trades"] < 8:
        return (-10_000.0, -10_000.0, stats["trades"])
    profit_factor = stats["profit_factor"] or 0.0
    return (
        stats["net_r"] - 0.5 * stats["max_drawdown_r"],
        profit_factor,
        stats["trades"],
    )


def _summary_row(result: dict, period: str) -> dict:
    return {
        "symbol": result["symbol"],
        "period": period,
        **result["config"],
        **result["performance"],
        "usable_events": result["statuses"].get("traded", 0)
        + result["statuses"].get("expired", 0),
        "missing_events": result["statuses"].get("missing_bid_ask", 0)
        + result["statuses"].get("missing_pre_range", 0),
        "expired_events": result["statuses"].get("expired", 0),
        "same_minute_oco_collisions": result["same_minute_oco_collisions"],
    }


def _fmt_pf(value: float | None) -> str:
    return "n/a" if value is None else f"{value:.2f}"


def run() -> dict:
    events = load_events(START, END)
    development = [event for event in events if event["released"] < HOLDOUT_START]
    holdout = [event for event in events if event["released"] >= HOLDOUT_START]
    predictions = load_predictions()
    payload = {
        "methodology": {
            "start": START.isoformat(),
            "holdout_start": HOLDOUT_START.isoformat(),
            "end": END.isoformat(),
            "calendar_events": len(events),
            "development_events": len(development),
            "holdout_events": len(holdout),
            "risk_per_leg_pct": 1.0,
            "start_balance": 10_000.0,
            "same_bar_policy": "SL first; an entry-bar TP is not credited",
            "gold_pip_size": 0.1,
            "gold_literal_stress_pip_size": 0.01,
            "eurusd_pip_size": 0.0001,
            "event_filter_rule": "Development only: >=8 trades, PF >=1.30, and positive net R.",
        },
        "symbols": {},
    }
    csv_rows = []
    all_best_trades = []
    all_development_trades = []
    all_holdout_trades = []

    for symbol in INSTRUMENTS:
        development_runs = []
        for config in _parameter_grid(symbol):
            allowed_events = _stable_events(symbol, config, development, predictions)
            candidate = _run_config(
                symbol,
                config,
                development,
                predictions,
                allowed_events=allowed_events,
            )
            candidate["allowed_events"] = allowed_events
            development_runs.append(candidate)
        best_development = max(development_runs, key=_selection_score)
        config = StrategyConfig(
            mode=best_development["config"]["mode"],
            reward_risk=best_development["config"]["reward_risk"],
            spread_buffer_multiplier=best_development["config"]["spread_buffer_multiplier"],
            allow_reentry=best_development["config"]["allow_reentry"],
        )
        allowed_events = best_development["allowed_events"]
        holdout_run = _run_config(
            symbol,
            config,
            holdout,
            predictions,
            allowed_events=allowed_events,
        )
        full_run = _run_config(
            symbol,
            config,
            events,
            predictions,
            allowed_events=allowed_events,
        )
        all_development_trades.extend(best_development["trades_detail"])
        all_holdout_trades.extend(holdout_run["trades_detail"])
        unfiltered_full = _run_config(symbol, config, events, predictions)
        all_best_trades.extend(full_run["trades_detail"])

        leaderboard = []
        for candidate in development_runs:
            candidate_config = StrategyConfig(
                mode=candidate["config"]["mode"],
                reward_risk=candidate["config"]["reward_risk"],
                spread_buffer_multiplier=candidate["config"]["spread_buffer_multiplier"],
                allow_reentry=candidate["config"]["allow_reentry"],
            )
            candidate_full = _run_config(
                symbol,
                candidate_config,
                events,
                predictions,
                allowed_events=candidate["allowed_events"],
            )
            leaderboard.append(
                {
                    "key": _key(candidate_config),
                    "allowed_events": candidate["allowed_events"],
                    "development": candidate["performance"],
                    "full": candidate_full["performance"],
                }
            )
        leaderboard.sort(
            key=lambda row: (
                row["development"]["net_r"] - 0.5 * row["development"]["max_drawdown_r"],
                row["development"]["profit_factor"] or 0.0,
            ),
            reverse=True,
        )
        payload["symbols"][symbol.upper()] = {
            "selected_config": full_run["config"],
            "allowed_events": allowed_events,
            "development": {
                key: value
                for key, value in best_development.items()
                if key not in {"trades_detail", "allowed_events"}
            },
            "holdout": {
                key: value
                for key, value in holdout_run.items()
                if key != "trades_detail"
            },
            "full": {
                key: value
                for key, value in full_run.items()
                if key != "trades_detail"
            },
            "unfiltered_full": {
                key: value
                for key, value in unfiltered_full.items()
                if key != "trades_detail"
            },
            "leaderboard": leaderboard,
        }
        if symbol == "xauusd":
            literal_stress = _run_config(
                symbol,
                config,
                events,
                predictions,
                instrument=Instrument("xauusd", pip_size=0.01),
                allowed_events=allowed_events,
            )
            payload["symbols"][symbol.upper()]["literal_0_01_pip_stress"] = {
                key: value
                for key, value in literal_stress.items()
                if key != "trades_detail"
            }
        csv_rows.extend(full_run["trades_detail"])

    payload["combined_development"] = performance(all_development_trades)
    payload["combined_holdout"] = performance(all_holdout_trades)
    payload["combined_full"] = performance(all_best_trades)
    OUTPUT_JSON.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    if csv_rows:
        with OUTPUT_CSV.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(csv_rows[0]))
            writer.writeheader()
            writer.writerows(sorted(csv_rows, key=lambda row: row["entry_time"]))

    lines = [
        "# USD News Pending-Order Backtest",
        "",
        "## Honest test design",
        "",
        f"- Window: {START.date()} through {END.date()} ({len(events)} scheduled events).",
        f"- Development/selection: {START.date()} through {(HOLDOUT_START.date())}.",
        f"- Locked holdout: {HOLDOUT_START.date()} through {END.date()}.",
        "- Event set: NFP, CPI, PPI, advance GDP, and FOMC statements.",
        "- The range is the completed T-60 to T-31 window; orders are placed at T-30.",
        "- Forecast BUY uses a buy-stop above the range; forecast SELL uses a broker-valid sell-stop at/below the 50% range level.",
        "- OCO mode uses buy-stop above the range and sell-stop below the range; the first fill cancels the other side.",
        "- Pending orders expire at T+15. Filled trades can run for at most 180 minutes.",
        "- Bid/ask candles drive triggers and exits. Spread buffers move only farther from price before release.",
        "- Same-minute ambiguity is pessimistic: SL wins ties and entry-bar TP is not credited.",
        "- Metrics assume 1% compounded risk per filled leg from a normalized $10,000 account.",
        "- EURUSD uses 1 pip = 0.0001. XAUUSD uses the common 0.10 quote convention, so 90 pips is a $9 stop.",
        "- A literal XAU 0.01-pip/$0.90-stop stress test is retained separately; it is not used to select the strategy.",
        "- Event families are retained using development data only: at least 8 trades, PF >= 1.30, and positive net R.",
        "",
        "## Selected results",
        "",
        "| Symbol | Period | Mode | RR | Re-entry | Trades | Win rate | PF | Net R | Max DD | Return |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for symbol, result in payload["symbols"].items():
        lines.append(
            f"| {symbol} filter | all | {','.join(result['allowed_events'])} | - | - | - | - | - | - | - | - |"
        )
        for period in ("development", "holdout", "full"):
            row = _summary_row(result[period], period)
            lines.append(
                f"| {symbol} | {period} | {row['mode']} | {row['reward_risk']:.0f} | "
                f"{'yes' if row['allow_reentry'] else 'no'} | {row['trades']} | "
                f"{row['win_rate_pct']:.1f}% | {_fmt_pf(row['profit_factor'])} | "
                f"{row['net_r']:.2f} | {row['max_drawdown_pct']:.2f}% | "
                f"{row['return_pct']:.2f}% |"
            )
        unfiltered = result["unfiltered_full"]["performance"]
        lines.append(
            f"| {symbol} | unfiltered full | {result['selected_config']['mode']} | "
            f"{result['selected_config']['reward_risk']:.0f} | "
            f"{'yes' if result['selected_config']['allow_reentry'] else 'no'} | "
            f"{unfiltered['trades']} | {unfiltered['win_rate_pct']:.1f}% | "
            f"{_fmt_pf(unfiltered['profit_factor'])} | {unfiltered['net_r']:.2f} | "
            f"{unfiltered['max_drawdown_pct']:.2f}% | {unfiltered['return_pct']:.2f}% |"
        )
    literal = payload["symbols"]["XAUUSD"]["literal_0_01_pip_stress"]["performance"]
    lines.extend(
        [
            "",
            "## Gold pip-size stress test",
            "",
            f"The same selected XAUUSD rules with a literal 0.01 pip ($0.90 stop) produced "
            f"{literal['trades']} trades, {_fmt_pf(literal['profit_factor'])} PF, "
            f"{literal['net_r']:.2f}R, and {literal['max_drawdown_pct']:.2f}% maximum drawdown. "
            "That interpretation is rejected because news gaps and spread are too large relative to the stop.",
        ]
    )
    combined = payload["combined_full"]
    combined_holdout = payload["combined_holdout"]
    lines.extend(
        [
            "",
            "## Combined selected configurations",
            "",
            f"- Trades: {combined['trades']}",
            f"- Win rate: {combined['win_rate_pct']:.2f}%",
            f"- Profit factor: {_fmt_pf(combined['profit_factor'])}",
            f"- Net: {combined['net_r']:.2f}R",
            f"- Maximum drawdown: {combined['max_drawdown_pct']:.2f}%",
            f"- Normalized balance: ${combined['start_balance']:,.2f} -> ${combined['ending_balance']:,.2f}",
            f"- Locked holdout: {combined_holdout['trades']} trades, "
            f"{combined_holdout['win_rate_pct']:.2f}% win rate, "
            f"{_fmt_pf(combined_holdout['profit_factor'])} PF, "
            f"{combined_holdout['net_r']:.2f}R, "
            f"{combined_holdout['max_drawdown_pct']:.2f}% max DD.",
            "",
            "This is a historical execution simulation, not a guarantee. One-minute candles cannot reconstruct tick order inside a candle, so ambiguous fills are handled against the strategy.",
        ]
    )
    OUTPUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return payload


if __name__ == "__main__":
    result = run()
    print(OUTPUT_MD)
    for symbol, row in result["symbols"].items():
        stats = row["full"]["performance"]
        print(
            symbol,
            row["selected_config"],
            {
                "trades": stats["trades"],
                "win_rate_pct": round(stats["win_rate_pct"], 2),
                "profit_factor": None
                if stats["profit_factor"] is None
                else round(stats["profit_factor"], 2),
                "net_r": round(stats["net_r"], 2),
                "max_drawdown_pct": round(stats["max_drawdown_pct"], 2),
            },
        )
