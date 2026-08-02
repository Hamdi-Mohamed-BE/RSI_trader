from __future__ import annotations

import csv
import json
import math
import statistics
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path

from news_pending_strategy import ROOT, load_day, load_events, load_predictions


START = datetime(2021, 8, 1, tzinfo=timezone.utc)
HOLDOUT_START = datetime(2025, 8, 1, tzinfo=timezone.utc)
END = datetime(2026, 8, 1, tzinfo=timezone.utc)
EVENT_NAMES = ("NFP", "CPI", "PPI", "GDP", "FOMC")
OFFSETS_PIPS = (0.0, 2.0, 5.0, 8.0, 10.0, 12.0, 15.0, 20.0, 25.0, 30.0, 40.0, 50.0, 60.0, 75.0, 100.0)
SPREAD_MULTIPLIERS = (1.0, 1.5, 2.0, 3.0)

PIP_SIZE = 0.1
STOP_PIPS = 90.0
REWARD_RISK = 3.0
EXPIRY_MINUTES = 3
HOLD_MINUTES = 60

OUTPUT_JSON = ROOT / "news_pulse_offset_5y.json"
OUTPUT_CSV = ROOT / "news_pulse_offset_5y_trades.csv"
OUTPUT_MD = ROOT / "NEWS_PULSE_OFFSET_5Y.md"


@dataclass(frozen=True)
class OffsetConfig:
    fixed_offset_pips: float
    spread_multiplier: float


@dataclass
class PulseTrade:
    event: str
    release_utc: str
    side: str
    entry_time: str
    exit_time: str
    entry: float
    stop_loss: float
    take_profit: float
    exit_price: float
    fixed_offset_pips: float
    spread_pips: float
    effective_offset_pips: float
    slippage_pips: float
    result_r: float
    outcome: str
    reached_1r: bool
    post_fill_mfe_r: float
    post_fill_mae_r: float
    snapback: bool


def _stamp(value: datetime) -> int:
    return int(value.timestamp() * 1000)


def _iso(stamp: int) -> str:
    return datetime.fromtimestamp(stamp / 1000, timezone.utc).isoformat()


def _performance(
    trades: list[dict],
    *,
    risk_pct: float = 1.0,
    start_balance: float = 10_000.0,
) -> dict:
    gross_profit = sum(max(0.0, float(row["result_r"])) for row in trades)
    gross_loss = -sum(min(0.0, float(row["result_r"])) for row in trades)
    wins = sum(float(row["result_r"]) > 0 for row in trades)
    equity = start_balance
    peak = equity
    max_drawdown_pct = 0.0
    running_r = 0.0
    peak_r = 0.0
    max_drawdown_r = 0.0
    for row in sorted(trades, key=lambda item: item["entry_time"]):
        result_r = float(row["result_r"])
        equity += equity * risk_pct / 100.0 * result_r
        peak = max(peak, equity)
        if peak > 0:
            max_drawdown_pct = max(max_drawdown_pct, 100.0 * (peak - equity) / peak)
        running_r += result_r
        peak_r = max(peak_r, running_r)
        max_drawdown_r = max(max_drawdown_r, peak_r - running_r)
    return {
        "trades": len(trades),
        "wins": wins,
        "losses": len(trades) - wins,
        "win_rate_pct": 100.0 * wins / len(trades) if trades else 0.0,
        "profit_factor": gross_profit / gross_loss if gross_loss else None,
        "net_r": gross_profit - gross_loss,
        "max_drawdown_r": max_drawdown_r,
        "stopout_rate_pct": 100.0
        * sum(row["outcome"] == "SL" for row in trades)
        / len(trades)
        if trades
        else 0.0,
        "one_r_continuation_pct": 100.0
        * sum(bool(row["reached_1r"]) for row in trades)
        / len(trades)
        if trades
        else 0.0,
        "snapback_rate_pct": 100.0
        * sum(bool(row["snapback"]) for row in trades)
        / len(trades)
        if trades
        else 0.0,
        "ending_balance": equity,
        "return_pct": 100.0 * (equity / start_balance - 1.0),
        "max_drawdown_pct": max_drawdown_pct,
    }


def _exit_trade(
    *,
    event: dict,
    side: str,
    trigger_stamp: int,
    intended_entry: float,
    fill: float,
    stop: float,
    target: float,
    bid: dict[int, dict[str, float]],
    ask: dict[int, dict[str, float]],
    config: OffsetConfig,
    spread_pips: float,
    effective_offset_pips: float,
) -> PulseTrade:
    release_stamp = _stamp(event["released"])
    max_exit = release_stamp + HOLD_MINUTES * 60_000
    exit_price = fill
    exit_stamp = trigger_stamp
    outcome = "TIME"
    reached_1r = False
    post_fill_mfe_r = 0.0
    post_fill_mae_r = 0.0

    stamps = [
        stamp
        for stamp in sorted(set(bid) & set(ask))
        if trigger_stamp <= stamp <= max_exit
    ]
    for stamp in stamps:
        bar = bid[stamp] if side == "buy" else ask[stamp]
        if stamp > trigger_stamp:
            favorable = bar["high"] - fill if side == "buy" else fill - bar["low"]
            adverse = fill - bar["low"] if side == "buy" else bar["high"] - fill
            post_fill_mfe_r = max(post_fill_mfe_r, favorable / (STOP_PIPS * PIP_SIZE))
            post_fill_mae_r = max(post_fill_mae_r, adverse / (STOP_PIPS * PIP_SIZE))

        stop_hit = bar["low"] <= stop if side == "buy" else bar["high"] >= stop
        one_r_price = fill + STOP_PIPS * PIP_SIZE if side == "buy" else fill - STOP_PIPS * PIP_SIZE
        one_r_hit = bar["high"] >= one_r_price if side == "buy" else bar["low"] <= one_r_price
        target_hit = bar["high"] >= target if side == "buy" else bar["low"] <= target

        # M1 cannot recover tick order. Stops win same-bar ties, and an
        # entry-bar target is not credited.
        if stop_hit:
            exit_price = min(stop, bar["open"]) if side == "buy" else max(stop, bar["open"])
            exit_stamp = stamp
            outcome = "SL"
            break
        if one_r_hit:
            reached_1r = True
        if target_hit and stamp > trigger_stamp:
            exit_price = max(target, bar["open"]) if side == "buy" else min(target, bar["open"])
            exit_stamp = stamp
            outcome = "TP"
            break
    else:
        if stamps:
            exit_stamp = stamps[-1]
            exit_price = bid[exit_stamp]["close"] if side == "buy" else ask[exit_stamp]["close"]

    result = exit_price - fill if side == "buy" else fill - exit_price
    result_r = result / (STOP_PIPS * PIP_SIZE)
    snapback = post_fill_mfe_r >= 0.5 and result_r <= 0.0
    slippage = abs(fill - intended_entry) / PIP_SIZE
    return PulseTrade(
        event=event["event"],
        release_utc=event["released"].isoformat(),
        side=side,
        entry_time=_iso(trigger_stamp),
        exit_time=_iso(exit_stamp),
        entry=fill,
        stop_loss=stop,
        take_profit=target,
        exit_price=exit_price,
        fixed_offset_pips=config.fixed_offset_pips,
        spread_pips=spread_pips,
        effective_offset_pips=effective_offset_pips,
        slippage_pips=slippage,
        result_r=result_r,
        outcome=outcome,
        reached_1r=reached_1r,
        post_fill_mfe_r=post_fill_mfe_r,
        post_fill_mae_r=post_fill_mae_r,
        snapback=snapback,
    )


def _simulate_event(
    event: dict,
    config: OffsetConfig,
    forecast_side: str | None,
    market_data: tuple[dict[int, dict[str, float]], dict[int, dict[str, float]]],
) -> dict:
    if forecast_side not in {"buy", "sell"}:
        return {"status": "missing_forecast"}
    bid, ask = market_data
    if not bid or not ask:
        return {"status": "missing_bid_ask"}

    release_stamp = _stamp(event["released"])
    snapshot_stamp = release_stamp - 2 * 60_000
    if snapshot_stamp not in bid or snapshot_stamp not in ask:
        return {"status": "missing_snapshot"}

    spread_pips = max(
        0.0,
        (ask[snapshot_stamp]["close"] - bid[snapshot_stamp]["close"]) / PIP_SIZE,
    )
    effective_offset_pips = max(
        config.fixed_offset_pips,
        spread_pips * config.spread_multiplier,
    )
    offset = effective_offset_pips * PIP_SIZE
    intended = (
        ask[snapshot_stamp]["close"] + offset
        if forecast_side == "buy"
        else bid[snapshot_stamp]["close"] - offset
    )

    # The order is armed one minute before the release. Including the T-1 bar
    # is deliberately conservative because M1 cannot identify a last-second
    # placement inside that candle.
    first_stamp = release_stamp - 60_000
    last_stamp = release_stamp + EXPIRY_MINUTES * 60_000
    for stamp in range(first_stamp, last_stamp + 1, 60_000):
        if stamp not in bid or stamp not in ask:
            continue
        if forecast_side == "buy":
            triggered = ask[stamp]["high"] >= intended
            fill = max(intended, ask[stamp]["open"])
            stop = intended - STOP_PIPS * PIP_SIZE
            target = intended + REWARD_RISK * STOP_PIPS * PIP_SIZE
        else:
            triggered = bid[stamp]["low"] <= intended
            fill = min(intended, bid[stamp]["open"])
            stop = intended + STOP_PIPS * PIP_SIZE
            target = intended - REWARD_RISK * STOP_PIPS * PIP_SIZE
        if not triggered:
            continue
        trade = _exit_trade(
            event=event,
            side=forecast_side,
            trigger_stamp=stamp,
            intended_entry=intended,
            fill=fill,
            stop=stop,
            target=target,
            bid=bid,
            ask=ask,
            config=config,
            spread_pips=spread_pips,
            effective_offset_pips=effective_offset_pips,
        )
        return {"status": "traded", "trade": asdict(trade)}
    return {
        "status": "expired",
        "spread_pips": spread_pips,
        "effective_offset_pips": effective_offset_pips,
    }


def _run_config(
    events: list[dict],
    config: OffsetConfig,
    predictions: dict[str, str],
    data: dict[str, tuple[dict, dict]],
) -> dict:
    trades = []
    statuses: dict[str, int] = {}
    offsets = []
    for event in events:
        release = event["released"].isoformat()
        result = _simulate_event(event, config, predictions.get(release), data[release])
        status = result["status"]
        statuses[status] = statuses.get(status, 0) + 1
        if status == "traded":
            trades.append(result["trade"])
            offsets.append(float(result["trade"]["effective_offset_pips"]))
        elif "effective_offset_pips" in result:
            offsets.append(float(result["effective_offset_pips"]))
    usable = len(events) - statuses.get("missing_bid_ask", 0) - statuses.get("missing_snapshot", 0) - statuses.get("missing_forecast", 0)
    performance = _performance(trades)
    performance.update(
        {
            "events": len(events),
            "usable_events": usable,
            "fill_rate_pct": 100.0 * len(trades) / usable if usable else 0.0,
            "median_effective_offset_pips": statistics.median(offsets) if offsets else None,
            "mean_effective_offset_pips": statistics.fmean(offsets) if offsets else None,
        }
    )
    return {
        "config": asdict(config),
        "performance": performance,
        "statuses": statuses,
        "trades": trades,
    }


def _selection_score(run: dict) -> tuple[float, float, int]:
    stats = run["performance"]
    if stats["trades"] < 50:
        return (-math.inf, -math.inf, stats["trades"])
    return (
        stats["net_r"] - 0.5 * stats["max_drawdown_r"],
        stats["profit_factor"] or 0.0,
        stats["trades"],
    )


def _event_breakdown(trades: list[dict]) -> dict[str, dict]:
    return {
        event: _performance([row for row in trades if row["event"] == event])
        for event in EVENT_NAMES
    }


def _fmt(value: float | None, digits: int = 2) -> str:
    return "n/a" if value is None else f"{value:.{digits}f}"


def run() -> dict:
    events = [
        event
        for event in load_events(START, END)
        if event["event"] in EVENT_NAMES
    ]
    development = [event for event in events if event["released"] < HOLDOUT_START]
    holdout = [event for event in events if event["released"] >= HOLDOUT_START]
    predictions = load_predictions()
    data = {}
    for event in events:
        release = event["released"].isoformat()
        day = event["released"].date().isoformat()
        data[release] = (
            load_day("xauusd", day, "bid"),
            load_day("xauusd", day, "ask"),
        )

    development_runs = [
        _run_config(development, OffsetConfig(offset, multiplier), predictions, data)
        for multiplier in SPREAD_MULTIPLIERS
        for offset in OFFSETS_PIPS
    ]
    development_runs.sort(key=_selection_score, reverse=True)
    selected = OffsetConfig(**development_runs[0]["config"])
    selected_development = development_runs[0]
    selected_holdout = _run_config(holdout, selected, predictions, data)
    selected_full = _run_config(events, selected, predictions, data)
    development_by_config = {
        (
            run["config"]["fixed_offset_pips"],
            run["config"]["spread_multiplier"],
        ): run
        for run in development_runs
    }
    robustness_offsets = (0.0, 5.0, 8.0, 10.0, 12.0, 15.0, 20.0, 30.0, 40.0)
    offset_robustness = []
    for offset in robustness_offsets:
        config = OffsetConfig(offset, selected.spread_multiplier)
        development_run = development_by_config[(offset, selected.spread_multiplier)]
        holdout_run = _run_config(holdout, config, predictions, data)
        offset_robustness.append(
            {
                "fixed_offset_pips": offset,
                "development": development_run["performance"],
                "holdout": holdout_run["performance"],
            }
        )
    account_800 = _performance(
        selected_full["trades"],
        risk_pct=3.0,
        start_balance=800.0,
    )
    payload = {
        "methodology": {
            "symbol": "XAUUSD",
            "start": START.isoformat(),
            "holdout_start": HOLDOUT_START.isoformat(),
            "end": END.isoformat(),
            "event_names": EVENT_NAMES,
            "pip_size": PIP_SIZE,
            "stop_pips": STOP_PIPS,
            "reward_risk": REWARD_RISK,
            "order_armed": "T-1 minute",
            "entry_expiry": f"T+{EXPIRY_MINUTES} minutes",
            "max_hold_minutes": HOLD_MINUTES,
            "entry_anchor": "T-2 completed M1 bid/ask close",
            "effective_offset": "max(fixed offset, T-2 spread x multiplier)",
            "same_bar_policy": "Stop first; entry-bar TP not credited",
            "selection": "First four years only; maximize net R minus 0.5 x max drawdown R with at least 50 fills",
        },
        "selected_config": asdict(selected),
        "development": {key: value for key, value in selected_development.items() if key != "trades"},
        "holdout": {key: value for key, value in selected_holdout.items() if key != "trades"},
        "full": {key: value for key, value in selected_full.items() if key != "trades"},
        "account_800_risk_3pct": account_800,
        "event_breakdown_full": _event_breakdown(selected_full["trades"]),
        "offset_robustness": offset_robustness,
        "leaderboard_development": [
            {key: value for key, value in candidate.items() if key != "trades"}
            for candidate in development_runs[:15]
        ],
        "trades": selected_full["trades"],
    }
    OUTPUT_JSON.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    if selected_full["trades"]:
        with OUTPUT_CSV.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(selected_full["trades"][0]))
            writer.writeheader()
            writer.writerows(selected_full["trades"])

    dev = selected_development["performance"]
    test = selected_holdout["performance"]
    full = selected_full["performance"]
    lines = [
        "# XAUUSD News-Pulse Offset Study",
        "",
        "## Test design",
        "",
        f"- Window: {START.date()} through {END.date()} ({len(events)} scheduled USD events).",
        f"- Development: {START.date()} through {HOLDOUT_START.date()} ({len(development)} events).",
        f"- Locked holdout: {HOLDOUT_START.date()} through {END.date()} ({len(holdout)} events).",
        "- Events: NFP, CPI, PPI, advance GDP, and FOMC statements.",
        "- Direction comes from the frozen T-30 gold-impact prediction archive.",
        "- Entry is a stop in the predicted direction, anchored to the T-2 completed M1 close.",
        f"- Orders are armed at T-1, expire at T+{EXPIRY_MINUTES}, use a {STOP_PIPS:g}-pip stop and {REWARD_RISK:g}R target, and close by T+{HOLD_MINUTES}.",
        "- Bid/ask candles model spread, gaps, fills, stops, and exits.",
        "- Same-bar uncertainty is pessimistic: the stop wins and entry-bar TP is not credited.",
        "",
        "## Selected offset",
        "",
        f"**Use max({_fmt(selected.fixed_offset_pips, 0)} gold pips, live spread x {_fmt(selected.spread_multiplier, 1)}).**",
        f"With 1 gold pip = $0.10, the fixed floor is ${selected.fixed_offset_pips * PIP_SIZE:.2f}.",
        f"The actual median effective offset was {_fmt(full['median_effective_offset_pips'], 1)} pips (${(full['median_effective_offset_pips'] or 0) * PIP_SIZE:.2f}).",
        "",
        "## Results",
        "",
        "| Period | Trades | Fill rate | Win rate | PF | Net R | Max DD | 1R continuation | Snapback |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|",
        f"| Development | {dev['trades']} | {dev['fill_rate_pct']:.1f}% | {dev['win_rate_pct']:.1f}% | {_fmt(dev['profit_factor'])} | {dev['net_r']:.2f} | {dev['max_drawdown_r']:.2f}R | {dev['one_r_continuation_pct']:.1f}% | {dev['snapback_rate_pct']:.1f}% |",
        f"| Locked holdout | {test['trades']} | {test['fill_rate_pct']:.1f}% | {test['win_rate_pct']:.1f}% | {_fmt(test['profit_factor'])} | {test['net_r']:.2f} | {test['max_drawdown_r']:.2f}R | {test['one_r_continuation_pct']:.1f}% | {test['snapback_rate_pct']:.1f}% |",
        f"| Full five years | {full['trades']} | {full['fill_rate_pct']:.1f}% | {full['win_rate_pct']:.1f}% | {_fmt(full['profit_factor'])} | {full['net_r']:.2f} | {full['max_drawdown_r']:.2f}R | {full['one_r_continuation_pct']:.1f}% | {full['snapback_rate_pct']:.1f}% |",
        "",
        "## $800 account at 3% risk",
        "",
        f"- Ending balance: ${account_800['ending_balance']:.2f}",
        f"- Return: {account_800['return_pct']:.2f}%",
        f"- Maximum compounded drawdown: {account_800['max_drawdown_pct']:.2f}%",
        "",
        "## Event breakdown",
        "",
        "| Event | Trades | Win rate | PF | Net R | Max DD |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for event, stats in payload["event_breakdown_full"].items():
        lines.append(
            f"| {event} | {stats['trades']} | {stats['win_rate_pct']:.1f}% | {_fmt(stats['profit_factor'])} | {stats['net_r']:.2f} | {stats['max_drawdown_r']:.2f}R |"
        )
    lines.extend(
        [
            "",
            "## Neighboring offsets",
            "",
            "| Fixed offset | Development PF | Development net R | Holdout PF | Holdout net R | Holdout snapback |",
            "|---:|---:|---:|---:|---:|---:|",
        ]
    )
    for row in offset_robustness:
        development_stats = row["development"]
        holdout_stats = row["holdout"]
        lines.append(
            f"| {row['fixed_offset_pips']:.0f} pips | {_fmt(development_stats['profit_factor'])} | {development_stats['net_r']:.2f} | {_fmt(holdout_stats['profit_factor'])} | {holdout_stats['net_r']:.2f} | {holdout_stats['snapback_rate_pct']:.1f}% |"
        )
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "Offsets around 5-10 pips formed the best development-period plateau. Larger fixed offsets reduced some snapbacks, but they entered after more of the impulse was already spent and lost money in development. Eight pips is the selected compromise, not a guarantee against reversal.",
            "",
            "This remains an M1 historical simulation, not a guarantee. Tick data is required to know the exact order of prices inside the release candle.",
        ]
    )
    OUTPUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return payload


if __name__ == "__main__":
    result = run()
    print(OUTPUT_MD.read_text(encoding="utf-8"))
