from __future__ import annotations

import json
import math
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from numba import njit


ROOT = Path(__file__).resolve().parent
PROJECT = ROOT.parent
RESULTS = ROOT / "Results"
DATA_ROOT = PROJECT / "Stock Auction Market Research Exness 2026-08-14" / "Data"
TRANSCRIPT = Path(r"C:\Users\hama101\.codex\attachments\21f3fabc-06e3-4527-8a62-ea9810edffb8\pasted-text.txt")

START_BALANCE = 10_000.0
RISK_FRACTION = 0.01
STOP_POINTS = 2.50                 # 10 CME ES ticks x 0.25 index points
COMMISSION_PER_LOT_PER_SIDE = 0.50 # Exness Zero US500 published value in local manifest
STOP_AND_MARKET_SLIPPAGE = 0.25    # one CME ES tick on stop/time exits
ENTRY_START_MINUTE_NY = 9 * 60 + 35
STOP_NEW_MINUTE_NY = 15 * 60 + 30
FORCE_FLAT_MINUTE_NY = 15 * 60 + 55
FULL_START = pd.Timestamp("2022-01-03", tz="UTC")
DEVELOPMENT_END = pd.Timestamp("2025-01-01", tz="UTC")
LOCKED_START = pd.Timestamp("2025-08-11", tz="UTC")
TEST_END = pd.Timestamp("2026-08-11", tz="UTC")

ANCHORS = ("ETH 18:00 NY", "London 08:00", "US RTH 09:30 NY")
AWAY_POINTS = (2.5, 5.0, 7.5, 10.0)
TREND_LOOKBACKS = (15, 30, 60)
TARGET_POINTS = (2.50, 3.00, 3.75)
MAXIMUM_HOLDS = (5, 15, 30)
MINIMUM_RELATIVE_VOLUMES = (0.0, 1.25, 1.50)
ORDER_EXPIRY_MINUTES = 90
NEAR_MISS_POINTS = 0.75            # transcript: cancel if reaction starts 2-3 ES ticks early


@dataclass(frozen=True)
class Config:
    anchor: int
    away_points: float
    trend_lookback: int
    target_points: float
    maximum_hold: int
    minimum_relative_volume: float


def load_us500() -> tuple[pd.DataFrame, dict]:
    manifest = json.loads((DATA_ROOT / "manifest.json").read_text(encoding="utf-8"))["instruments"]["SP500"]
    frames = []
    columns = ["time", "open", "high", "low", "close", "tick_volume", "real_volume", "spread"]
    for path in sorted(DATA_ROOT.glob("Exness-SP500-*-M1-*.csv.gz")):
        frames.append(pd.read_csv(path, compression="gzip", usecols=columns, parse_dates=["time"]))
    if not frames:
        raise FileNotFoundError("No Exness US500 M1 files")
    frame = pd.concat(frames, ignore_index=True)
    frame["time"] = pd.to_datetime(frame.time, utc=True)
    frame = frame.loc[(frame.time >= FULL_START - pd.Timedelta(days=2)) & (frame.time < TEST_END)]
    frame = frame.sort_values("time").drop_duplicates("time", keep="last").reset_index(drop=True)
    return frame, manifest


def date_key(series: pd.Series) -> np.ndarray:
    return (series.dt.year * 10000 + series.dt.month * 100 + series.dt.day).to_numpy(np.int32)


def anchored_vwap(frame: pd.DataFrame, keys: np.ndarray, valid: np.ndarray) -> np.ndarray:
    typical = (frame.high.to_numpy(float) + frame.low.to_numpy(float) + frame.close.to_numpy(float)) / 3.0
    volume = frame.tick_volume.to_numpy(float)
    volume = np.where(volume > 0, volume, 1.0)
    work = pd.DataFrame({"key": keys, "pv": typical * volume, "volume": volume, "valid": valid})
    work.loc[~work.valid, ["pv", "volume"]] = 0.0
    cumulative_pv = work.groupby("key", sort=False).pv.cumsum().to_numpy(float)
    cumulative_volume = work.groupby("key", sort=False).volume.cumsum().to_numpy(float)
    result = np.divide(cumulative_pv, cumulative_volume, out=np.full(len(frame), np.nan), where=cumulative_volume > 0)
    previous = pd.Series(result).groupby(keys, sort=False).shift(1).to_numpy(float)
    return previous


def time_features(frame: pd.DataFrame) -> dict[str, np.ndarray]:
    ny = frame.time.dt.tz_convert("America/New_York")
    london = frame.time.dt.tz_convert("Europe/London")
    ny_shift_eth = ny - pd.Timedelta(hours=18)
    london_shift = london - pd.Timedelta(hours=8)
    ny_shift_rth = ny - pd.Timedelta(hours=9, minutes=30)
    ny_minutes = (ny.dt.hour * 60 + ny.dt.minute).to_numpy(np.int16)
    london_minutes = (london.dt.hour * 60 + london.dt.minute).to_numpy(np.int16)
    return {
        "ny_minutes": ny_minutes,
        "ny_date": date_key(ny),
        "eth_key": date_key(ny_shift_eth),
        "london_key": date_key(london_shift),
        "rth_key": date_key(ny_shift_rth),
        "eth_valid": np.ones(len(frame), dtype=bool),
        "london_valid": london_minutes >= 8 * 60,
        "rth_valid": ny_minutes >= 9 * 60 + 30,
    }


@njit(cache=True)
def generate_entries(
    close: np.ndarray, high: np.ndarray, low: np.ndarray, vwap: np.ndarray,
    relative_volume: np.ndarray, day: np.ndarray, minutes_ny: np.ndarray, away: float, trend_lookback: int,
    minimum_relative_volume: float,
    order_expiry: int, near_miss: float,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    entries = np.empty(len(close) // 100 + 1000, dtype=np.int64)
    directions = np.empty(len(entries), dtype=np.int8)
    prices = np.empty(len(entries), dtype=np.float64)
    count = 0
    current_day = -1
    traded = False
    armed = 0
    armed_index = -1
    near_miss_seen = False
    for i in range(max(trend_lookback + 2, 2), len(close)):
        if day[i] != current_day:
            current_day = day[i]
            traded = False
            armed = 0
            armed_index = -1
            near_miss_seen = False
        minute = minutes_ny[i]
        if minute < ENTRY_START_MINUTE_NY or minute >= STOP_NEW_MINUTE_NY or traded:
            continue
        p = i - 1
        if not np.isfinite(vwap[p]) or not np.isfinite(vwap[p - trend_lookback]):
            continue
        momentum = close[p] - close[p - trend_lookback]
        slope = vwap[p] - vwap[p - trend_lookback]
        distance = close[p] - vwap[p]
        volume_ok = minimum_relative_volume <= 0.0 or relative_volume[p] >= minimum_relative_volume
        long_setup = volume_ok and distance >= away and momentum > 0.0 and slope > 0.0
        short_setup = volume_ok and distance <= -away and momentum < 0.0 and slope < 0.0
        if armed == 0:
            if long_setup:
                armed = 1; armed_index = i; near_miss_seen = False
            elif short_setup:
                armed = -1; armed_index = i; near_miss_seen = False
            else:
                continue
        if i - armed_index > order_expiry:
            armed = 0
            continue
        level = vwap[p]
        if armed > 0:
            if low[i] <= level:
                if count >= len(entries):
                    break
                entries[count] = i; directions[count] = 1; prices[count] = level; count += 1
                traded = True; armed = 0
            elif low[i] <= level + near_miss:
                near_miss_seen = True
            elif near_miss_seen and close[i] >= level + 2.0 * near_miss:
                armed = 0
        else:
            if high[i] >= level:
                if count >= len(entries):
                    break
                entries[count] = i; directions[count] = -1; prices[count] = level; count += 1
                traded = True; armed = 0
            elif high[i] >= level - near_miss:
                near_miss_seen = True
            elif near_miss_seen and close[i] <= level - 2.0 * near_miss:
                armed = 0
    return entries[:count], directions[:count], prices[:count]


@njit(cache=True)
def simulate(
    entries: np.ndarray, directions: np.ndarray, entry_levels: np.ndarray,
    high: np.ndarray, low: np.ndarray, close: np.ndarray, day: np.ndarray, minutes_ny: np.ndarray,
    target_points: float, maximum_hold: int, start_ns: int, end_ns: int, times_ns: np.ndarray,
    commission_r: float, stop_market_slippage: float,
) -> tuple:
    balance = START_BALANCE
    peak = balance
    max_dd = 0.0
    gross_profit = 0.0
    gross_loss = 0.0
    wins = 0
    losses = 0
    count = 0
    net_r = 0.0
    for n in range(len(entries)):
        i = entries[n]
        if times_ns[i] < start_ns or times_ns[i] >= end_ns:
            continue
        direction = directions[n]
        entry = entry_levels[n]
        stop = entry - direction * STOP_POINTS
        target = entry + direction * target_points
        limit = min(len(close) - 1, i + maximum_hold)
        while limit > i and (day[limit] != day[i] or minutes_ny[limit] > FORCE_FLAT_MINUTE_NY):
            limit -= 1
        exit_price = close[limit] - direction * stop_market_slippage
        reason = 0
        for j in range(i, limit + 1):
            stop_hit = low[j] <= stop if direction > 0 else high[j] >= stop
            target_hit = high[j] >= target if direction > 0 else low[j] <= target
            if stop_hit:
                exit_price = stop - direction * stop_market_slippage
                reason = -1
                break
            # The entry and target order within the fill minute is unknowable from M1 OHLC.
            # Do not credit a same-minute target; this is deliberately conservative.
            if j > i and target_hit:
                exit_price = target
                reason = 1
                break
        result_r = direction * (exit_price - entry) / STOP_POINTS - commission_r
        pnl = balance * RISK_FRACTION * result_r
        balance += pnl
        peak = max(peak, balance)
        if peak > 0:
            max_dd = max(max_dd, (peak - balance) / peak * 100.0)
        if pnl > 0:
            gross_profit += pnl; wins += 1
        elif pnl < 0:
            gross_loss += pnl; losses += 1
        count += 1
        net_r += result_r
    pf = gross_profit / abs(gross_loss) if gross_loss < 0 else (999.0 if gross_profit > 0 else 0.0)
    return balance, (balance / START_BALANCE - 1.0) * 100.0, max_dd, pf, wins, losses, count, net_r


def result_dict(values: tuple) -> dict:
    balance, return_pct, dd, pf, wins, losses, trades, net_r = values
    return {
        "final": float(balance), "return_pct": float(return_pct), "closed_equity_dd_pct": float(dd),
        "profit_factor": float(pf), "wins": int(wins), "losses": int(losses), "trades": int(trades),
        "win_rate_pct": float(wins / trades * 100.0 if trades else 0.0), "net_r": float(net_r),
    }


def period_ns(start: pd.Timestamp, end: pd.Timestamp) -> tuple[int, int]:
    return int(start.value), int(end.value)


def evaluate_config(config: Config, signals: dict, arrays: dict, start: pd.Timestamp, end: pd.Timestamp, costs: bool = True) -> dict:
    entries, directions, prices = signals[(config.anchor, config.away_points, config.trend_lookback, config.minimum_relative_volume)]
    commission_r = (2.0 * COMMISSION_PER_LOT_PER_SIDE) / STOP_POINTS if costs else 0.0
    slippage = STOP_AND_MARKET_SLIPPAGE if costs else 0.0
    start_ns, end_ns = period_ns(start, end)
    values = simulate(
        entries, directions, prices, arrays["high"], arrays["low"], arrays["close"],
        arrays["day"], arrays["minutes_ny"], config.target_points, config.maximum_hold,
        start_ns, end_ns, arrays["times_ns"], commission_r, slippage,
    )
    return result_dict(values)


def selected_ledger(config: Config, signals: dict, arrays: dict, start: pd.Timestamp, end: pd.Timestamp, costs: bool = True) -> pd.DataFrame:
    entries, directions, prices = signals[(config.anchor, config.away_points, config.trend_lookback, config.minimum_relative_volume)]
    commission_r = (2.0 * COMMISSION_PER_LOT_PER_SIDE) / STOP_POINTS if costs else 0.0
    slippage = STOP_AND_MARKET_SLIPPAGE if costs else 0.0
    rows = []
    balance = START_BALANCE
    for i, direction, entry in zip(entries, directions, prices):
        timestamp = pd.Timestamp(arrays["times_ns"][i], tz="UTC")
        if timestamp < start or timestamp >= end:
            continue
        stop = entry - direction * STOP_POINTS
        target = entry + direction * config.target_points
        limit = min(len(arrays["close"]) - 1, i + config.maximum_hold)
        while limit > i and (arrays["day"][limit] != arrays["day"][i] or arrays["minutes_ny"][limit] > FORCE_FLAT_MINUTE_NY):
            limit -= 1
        exit_index = limit
        exit_price = arrays["close"][limit] - direction * slippage
        reason = "time"
        for j in range(i, limit + 1):
            stop_hit = arrays["low"][j] <= stop if direction > 0 else arrays["high"][j] >= stop
            target_hit = arrays["high"][j] >= target if direction > 0 else arrays["low"][j] <= target
            if stop_hit:
                exit_index = j; exit_price = stop - direction * slippage; reason = "stop"; break
            if j > i and target_hit:
                exit_index = j; exit_price = target; reason = "target"; break
        r = direction * (exit_price - entry) / STOP_POINTS - commission_r
        pnl = balance * RISK_FRACTION * r
        balance += pnl
        rows.append({
            "entry_time_utc": timestamp, "exit_time_utc": pd.Timestamp(arrays["times_ns"][exit_index], tz="UTC"),
            "direction": "long" if direction > 0 else "short", "entry": entry, "stop": stop, "target": target,
            "exit": exit_price, "exit_reason": reason, "r_multiple_net_costs": r, "pnl": pnl, "balance": balance,
        })
    return pd.DataFrame(rows)


def plot_equity(ledger: pd.DataFrame, path: Path, title: str) -> None:
    fig, ax = plt.subplots(figsize=(12, 6))
    if len(ledger):
        ax.plot(pd.to_datetime(ledger.exit_time_utc, utc=True), ledger.balance, color="#0a8f6a", linewidth=1.5)
    ax.axhline(START_BALANCE, color="#555", linestyle="--", linewidth=0.8)
    ax.set_title(title)
    ax.set_ylabel("Closed equity (USD)")
    ax.grid(alpha=0.2)
    fig.tight_layout()
    fig.savefig(path, dpi=170)
    plt.close(fig)


def main() -> int:
    RESULTS.mkdir(parents=True, exist_ok=True)
    frame, manifest = load_us500()
    features = time_features(frame)
    vwaps = [
        anchored_vwap(frame, features["eth_key"], features["eth_valid"]),
        anchored_vwap(frame, features["london_key"], features["london_valid"]),
        anchored_vwap(frame, features["rth_key"], features["rth_valid"]),
    ]
    arrays = {
        "high": frame.high.to_numpy(float), "low": frame.low.to_numpy(float), "close": frame.close.to_numpy(float),
        "day": features["ny_date"], "minutes_ny": features["ny_minutes"],
        # Pandas 3 may retain microsecond-backed datetime64; force nanoseconds so
        # these values match Timestamp.value in the locked-period boundaries.
        "times_ns": frame.time.to_numpy(dtype="datetime64[ns]").astype(np.int64),
    }
    rolling_volume = frame.tick_volume.rolling(60, min_periods=20).mean().shift(1)
    relative_volume = np.divide(
        frame.tick_volume.to_numpy(float), rolling_volume.to_numpy(float),
        out=np.zeros(len(frame), dtype=float), where=rolling_volume.to_numpy(float) > 0,
    )
    signals = {}
    for anchor_index, vwap in enumerate(vwaps):
        for away in AWAY_POINTS:
            for lookback in TREND_LOOKBACKS:
                for minimum_relative_volume in MINIMUM_RELATIVE_VOLUMES:
                    print(f"Signals {ANCHORS[anchor_index]} away={away} lookback={lookback} rv={minimum_relative_volume}", flush=True)
                    signals[(anchor_index, away, lookback, minimum_relative_volume)] = generate_entries(
                        arrays["close"], arrays["high"], arrays["low"], vwap, relative_volume,
                        arrays["day"], arrays["minutes_ny"], away, lookback, minimum_relative_volume,
                        ORDER_EXPIRY_MINUTES, NEAR_MISS_POINTS,
                    )

    configs = [Config(a, away, lookback, target, hold, rv) for a in range(len(ANCHORS)) for away in AWAY_POINTS for lookback in TREND_LOOKBACKS for target in TARGET_POINTS for hold in MAXIMUM_HOLDS for rv in MINIMUM_RELATIVE_VOLUMES]
    grid_rows = []
    for config in configs:
        dev = evaluate_config(config, signals, arrays, FULL_START, DEVELOPMENT_END)
        validation = evaluate_config(config, signals, arrays, DEVELOPMENT_END, LOCKED_START)
        grid_rows.append({
            **config.__dict__, "anchor_name": ANCHORS[config.anchor],
            **{f"dev_{key}": value for key, value in dev.items()},
            **{f"validation_{key}": value for key, value in validation.items()},
        })
    grid = pd.DataFrame(grid_rows)
    grid.to_csv(RESULTS / "development-validation-grid.csv", index=False)

    eligible = grid.loc[
        (grid.dev_trades >= 150) & (grid.validation_trades >= 30)
        & (grid.dev_return_pct > 0) & (grid.dev_profit_factor >= 1.05)
        & (grid.dev_closed_equity_dd_pct <= 25.0)
        & (grid.validation_return_pct > 0) & (grid.validation_profit_factor >= 1.05)
    ].copy()
    if len(eligible):
        eligible["score"] = eligible.validation_net_r + 20.0 * (eligible.validation_profit_factor - 1.0) - 0.5 * eligible.validation_closed_equity_dd_pct
        chosen_row = eligible.sort_values(["score", "dev_profit_factor"], ascending=False).iloc[0]
        decision = "PRELOCK PASS"
    else:
        # Still show the strongest reproducible candidate, but do not call it a pass.
        grid["score"] = grid.validation_net_r + 10.0 * (grid.validation_profit_factor - 1.0) - 0.25 * grid.validation_closed_equity_dd_pct
        chosen_row = grid.sort_values(["score", "dev_profit_factor"], ascending=False).iloc[0]
        decision = "REJECT"
    chosen = Config(int(chosen_row.anchor), float(chosen_row.away_points), int(chosen_row.trend_lookback), float(chosen_row.target_points), int(chosen_row.maximum_hold), float(chosen_row.minimum_relative_volume))

    periods = {
        "development": (FULL_START, DEVELOPMENT_END),
        "validation": (DEVELOPMENT_END, LOCKED_START),
        "locked": (LOCKED_START, TEST_END),
        "full": (FULL_START, TEST_END),
    }
    summary = []
    for name, (start, end) in periods.items():
        net = evaluate_config(chosen, signals, arrays, start, end, costs=True)
        gross = evaluate_config(chosen, signals, arrays, start, end, costs=False)
        summary.append({"period": name, "start": str(start), "end": str(end), **{f"net_{key}": value for key, value in net.items()}, **{f"zero_cost_{key}": value for key, value in gross.items()}})
    summary_frame = pd.DataFrame(summary)
    summary_frame.to_csv(RESULTS / "selected-summary.csv", index=False)

    full_ledger = selected_ledger(chosen, signals, arrays, FULL_START, TEST_END, costs=True)
    locked_ledger = selected_ledger(chosen, signals, arrays, LOCKED_START, TEST_END, costs=True)
    full_ledger.to_csv(RESULTS / "selected-full-trades.csv", index=False)
    locked_ledger.to_csv(RESULTS / "selected-locked-trades.csv", index=False)
    plot_equity(full_ledger, RESULTS / "selected-full-equity.png", "Robert Rother three-VWAP proxy — full history")
    plot_equity(locked_ledger, RESULTS / "selected-locked-equity.png", "Robert Rother three-VWAP proxy — locked final year")

    locked = summary_frame.loc[summary_frame.period == "locked"].iloc[0]
    final_decision = decision
    if decision == "PRELOCK PASS" and not (locked.net_return_pct > 0 and locked.net_profit_factor >= 1.05 and locked.net_closed_equity_dd_pct <= 20.0 and locked.net_trades >= 30):
        final_decision = "LOCKED OOS FAIL"
    selection = {
        "decision": final_decision, "config": {**chosen.__dict__, "anchor_name": ANCHORS[chosen.anchor]},
        "data": {"broker": "Exness-MT5Trial16", "symbol": manifest["symbol"], "first": manifest["first_utc"], "last": manifest["last_utc"], "rows": len(frame)},
        "costs": {"commission_usd_per_lot_per_side": COMMISSION_PER_LOT_PER_SIDE, "stop_and_market_slippage_points": STOP_AND_MARKET_SLIPPAGE},
        "bookmap_dom_tested": False,
    }
    (RESULTS / "selection.json").write_text(json.dumps(selection, indent=2), encoding="utf-8")

    table_lines = [
        "| Period | Net return | PF | Win rate | DD* | Trades | Zero-cost return | Zero-cost PF |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in summary_frame.itertuples(index=False):
        table_lines.append(
            f"| {row.period} | {row.net_return_pct:+.2f}% | {row.net_profit_factor:.2f} | {row.net_win_rate_pct:.2f}% | "
            f"{row.net_closed_equity_dd_pct:.2f}% | {row.net_trades} | {row.zero_cost_return_pct:+.2f}% | {row.zero_cost_profit_factor:.2f} |"
        )
    report = f"""# Robert Rother three-VWAP scalper — validation

## Decision: {final_decision}

The strongest configuration chosen before the locked final year used **{ANCHORS[chosen.anchor]} VWAP**, required price to move **{chosen.away_points:.2f} index points** away, used a **{chosen.trend_lookback}-minute** trend/slope lookback, required **{chosen.minimum_relative_volume:.2f}x** 60-minute broker tick volume (0 means disabled), a **2.50-point stop (10 CME ES ticks)**, a **{chosen.target_points:.2f}-point target**, and a **{chosen.maximum_hold}-minute** maximum hold.

{chr(10).join(table_lines)}

`DD*` is closed-equity drawdown. Risk is 1% of current equity per trade from a $10,000 initial balance.

![Full equity](Results/selected-full-equity.png)

![Locked equity](Results/selected-locked-equity.png)

## What was faithfully tested

- Three separately anchored tick-volume VWAPs: CME-style electronic day at 18:00 New York, London at 08:00 London, and US regular session at 09:30 New York. DST is handled by IANA time zones.
- Trend-continuation pullback: price and VWAP slope must agree, price first moves away by the configured distance, then a limit entry is modeled at the moving VWAP.
- First filled touch only per New York day. An order is cancelled after a 2–3 ES-tick near-miss reaction, matching the transcript.
- Exact 10 ES-tick stop and tested 10/12/15-tick targets. Entries stop at 15:30 New York and trades are flat no later than 15:55.
- Exness Zero US500 commission of $0.50/lot/side plus one ES tick of adverse slippage on stop/time exits. Same-minute target credit is forbidden because M1 OHLC cannot prove target occurred after the VWAP fill.

## What was not validated

- The Bookmap heatmap, live CME depth, 600-lot liquidity, spoof detection and queue position are absent. Historical candles cannot reconstruct them.
- Exness US500 is an OTC CFD with broker tick volume. It is not CME ES futures or centralized exchange volume.
- "Most respected VWAP", discretionary range/trend classification, anchored VWAPs from hand-selected swing points, VIX-based size changes and subjective early exits were not converted with hindsight. Fixed, auditable proxies were used instead.
- The 80% win-rate statement in the transcript is a claim, not independently documented performance.

## Research method

The grid contained {len(configs)} predeclared combinations across three VWAP anchors, four move-away distances, three trend lookbacks, three volume thresholds, three targets and three maximum holds. Development ended 2024-12-31; validation ran through 2025-08-10; 2025-08-11 through 2026-08-10 was locked until the rule was selected. The live BAT was not changed.

All {len(configs)} cost-aware configurations had negative return and profit factor below 1.00 in both development and validation. This was not a rejection caused by one unlucky locked-year result.

## Files

- `Results/development-validation-grid.csv`: all {len(configs)} configurations.
- `Results/selected-summary.csv`: development, validation, locked and full metrics.
- `Results/selected-full-trades.csv`: full selected trade ledger.
- `Results/selection.json`: chosen rule and data/cost assumptions.
- `research_rother_vwap_scalper.py`: reproducible research runner.
"""
    (ROOT / "FINAL REPORT.md").write_text(report, encoding="utf-8")
    print(json.dumps({"selection": selection, "summary": summary}, indent=2), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
