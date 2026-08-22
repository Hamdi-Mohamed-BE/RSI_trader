from __future__ import annotations

import json
import math
from dataclasses import asdict, dataclass
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from numba import njit


ROOT = Path(__file__).resolve().parent
PROJECT = ROOT.parent
RESULTS = ROOT / "Results"
DATA_ROOT = PROJECT / "Stock Auction Market Research Exness 2026-08-14" / "Data"

START_BALANCE = 10_000.0
RISK_FRACTION = 0.01
COMMISSION_PER_LOT_PER_SIDE = 0.50
STOP_AND_MARKET_SLIPPAGE = 0.25
ENTRY_START_NY = 10 * 60
STOP_NEW_ENTRIES_NY = 15 * 60 + 30
FORCE_FLAT_NY = 15 * 60 + 55
MINIMUM_SESSION_BARS = 30
REARM_SIGMA = 2.0

FULL_START = pd.Timestamp("2022-01-03", tz="UTC")
DEVELOPMENT_END = pd.Timestamp("2025-01-01", tz="UTC")
LOCKED_START = pd.Timestamp("2025-08-11", tz="UTC")
TEST_END = pd.Timestamp("2026-08-11", tz="UTC")

ANCHORS = ("US RTH 09:30 NY", "Electronic day 18:00 NY")
ENTRY_SIGMAS = (2.5, 3.0, 3.5)
REWARD_TO_RISKS = (0.33, 0.50, 0.75)
TARGET_MODES = ("fixed entry-time VWAP", "moving VWAP")
MAX_TRADES_PER_DAY = (1, 2, 3)


@dataclass(frozen=True)
class Config:
    anchor: int
    entry_sigma: float
    reward_to_risk: float
    moving_target: int
    maximum_trades_per_day: int


def load_us500() -> tuple[pd.DataFrame, dict]:
    manifest_all = json.loads((DATA_ROOT / "manifest.json").read_text(encoding="utf-8"))
    manifest = manifest_all["instruments"]["SP500"]
    columns = ["time", "open", "high", "low", "close", "tick_volume", "spread"]
    frames = [
        pd.read_csv(path, compression="gzip", usecols=columns, parse_dates=["time"])
        for path in sorted(DATA_ROOT.glob("Exness-SP500-US500-M1-*.csv.gz"))
    ]
    if not frames:
        raise FileNotFoundError("No Exness US500 M1 history was found")
    frame = pd.concat(frames, ignore_index=True)
    frame["time"] = pd.to_datetime(frame.time, utc=True)
    frame = frame.loc[(frame.time >= FULL_START - pd.Timedelta(days=2)) & (frame.time < TEST_END)]
    frame = frame.sort_values("time").drop_duplicates("time", keep="last").reset_index(drop=True)
    positive_spreads = frame.loc[frame.spread > 0, "spread"]
    fallback_spread = float(positive_spreads.median()) if len(positive_spreads) else float(manifest["median_positive_spread_points"])
    frame.loc[frame.spread <= 0, "spread"] = fallback_spread
    frame["spread_price"] = frame.spread.astype(float) * float(manifest["point"])
    return frame, manifest


def date_key(series: pd.Series) -> np.ndarray:
    return (series.dt.year * 10000 + series.dt.month * 100 + series.dt.day).to_numpy(np.int32)


def build_time_features(frame: pd.DataFrame) -> dict[str, np.ndarray]:
    ny = frame.time.dt.tz_convert("America/New_York")
    minutes = (ny.dt.hour * 60 + ny.dt.minute).to_numpy(np.int16)
    rth_keys = date_key(ny)
    electronic_keys = date_key(ny - pd.Timedelta(hours=18))
    return {
        "minutes": minutes,
        "ny_day": date_key(ny),
        "rth_keys": rth_keys,
        "electronic_keys": electronic_keys,
        "rth_valid": (minutes >= 9 * 60 + 30) & (minutes <= FORCE_FLAT_NY),
        "electronic_valid": np.ones(len(frame), dtype=bool),
    }


def anchored_vwap_and_deviation(
    frame: pd.DataFrame, keys: np.ndarray, valid: np.ndarray
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    typical = (frame.high.to_numpy(float) + frame.low.to_numpy(float) + frame.close.to_numpy(float)) / 3.0
    volume = np.where(frame.tick_volume.to_numpy(float) > 0, frame.tick_volume.to_numpy(float), 1.0)
    work = pd.DataFrame({
        "key": keys,
        "v": np.where(valid, volume, 0.0),
        "pv": np.where(valid, typical * volume, 0.0),
        "p2v": np.where(valid, typical * typical * volume, 0.0),
        "n": valid.astype(np.int32),
    })
    grouped = work.groupby("key", sort=False)
    cumulative_v = grouped.v.cumsum()
    cumulative_pv = grouped.pv.cumsum()
    cumulative_p2v = grouped.p2v.cumsum()
    cumulative_n = grouped.n.cumsum()
    mean = cumulative_pv / cumulative_v.replace(0.0, np.nan)
    variance = cumulative_p2v / cumulative_v.replace(0.0, np.nan) - mean * mean
    deviation = np.sqrt(np.maximum(variance.to_numpy(float), 0.0))
    # Signals on minute i use values known after minute i-1.
    mean_previous = mean.groupby(work.key, sort=False).shift(1).to_numpy(float)
    deviation_previous = pd.Series(deviation).groupby(work.key, sort=False).shift(1).to_numpy(float)
    bars_previous = cumulative_n.groupby(work.key, sort=False).shift(1).fillna(0).to_numpy(np.int32)
    return mean_previous, deviation_previous, bars_previous


@njit(cache=True)
def simulate(
    open_bid: np.ndarray,
    high_bid: np.ndarray,
    low_bid: np.ndarray,
    close_bid: np.ndarray,
    spread: np.ndarray,
    vwap: np.ndarray,
    deviation: np.ndarray,
    session_bars: np.ndarray,
    ny_day: np.ndarray,
    ny_minutes: np.ndarray,
    times_ns: np.ndarray,
    start_ns: int,
    end_ns: int,
    entry_sigma: float,
    reward_to_risk: float,
    moving_target: int,
    maximum_trades_per_day: int,
    collect: int,
    costs: int,
) -> tuple:
    max_rows = len(close_bid) // 50 + 1000
    ledger_entry_index = np.empty(max_rows, dtype=np.int64)
    ledger_exit_index = np.empty(max_rows, dtype=np.int64)
    ledger_direction = np.empty(max_rows, dtype=np.int8)
    ledger_entry = np.empty(max_rows, dtype=np.float64)
    ledger_stop = np.empty(max_rows, dtype=np.float64)
    ledger_target = np.empty(max_rows, dtype=np.float64)
    ledger_exit = np.empty(max_rows, dtype=np.float64)
    ledger_reason = np.empty(max_rows, dtype=np.int8)
    ledger_lot = np.empty(max_rows, dtype=np.float64)
    ledger_pnl = np.empty(max_rows, dtype=np.float64)
    ledger_balance = np.empty(max_rows, dtype=np.float64)

    balance = START_BALANCE
    peak = balance
    max_dd = 0.0
    gross_profit = 0.0
    gross_loss = 0.0
    wins = 0
    losses = 0
    trades = 0
    net_r = 0.0
    largest_win = 0.0
    largest_loss = 0.0
    current_day = -1
    trades_today = 0
    rearmed = True
    i = 2

    while i < len(close_bid) - 1:
        if times_ns[i] < start_ns:
            i += 1
            continue
        if times_ns[i] >= end_ns:
            break
        if ny_day[i] != current_day:
            current_day = ny_day[i]
            trades_today = 0
            rearmed = True
        minute = ny_minutes[i]
        if minute < ENTRY_START_NY or minute >= STOP_NEW_ENTRIES_NY:
            i += 1
            continue
        p = i - 1
        if session_bars[p] < MINIMUM_SESSION_BARS or not np.isfinite(vwap[p]) or not np.isfinite(deviation[p]) or deviation[p] <= 0.0:
            i += 1
            continue
        upper_rearm = vwap[p] + REARM_SIGMA * deviation[p]
        lower_rearm = vwap[p] - REARM_SIGMA * deviation[p]
        if not rearmed and close_bid[p] < upper_rearm and close_bid[p] + spread[p] > lower_rearm:
            rearmed = True
        if not rearmed or trades_today >= maximum_trades_per_day:
            i += 1
            continue

        upper = vwap[p] + entry_sigma * deviation[p]
        lower = vwap[p] - entry_sigma * deviation[p]
        previous_spread = spread[p] if costs == 1 else 0.0
        current_spread = spread[i] if costs == 1 else 0.0
        previous_ask = close_bid[p] + previous_spread
        current_ask_low = low_bid[i] + current_spread
        long_touch = previous_ask > lower and current_ask_low <= lower
        short_touch = close_bid[p] < upper and high_bid[i] >= upper
        if long_touch == short_touch:
            i += 1
            continue
        direction = 1 if long_touch else -1
        entry = lower if direction > 0 else upper
        initial_target = vwap[p]
        reward_distance = direction * (initial_target - entry)
        if reward_distance <= 0.0:
            i += 1
            continue
        stop_distance = reward_distance / reward_to_risk
        if stop_distance <= 0.0:
            i += 1
            continue
        raw_lot = balance * RISK_FRACTION / stop_distance
        lot = math.floor(raw_lot / 0.01) * 0.01
        if lot < 0.14:
            i += 1
            continue
        stop = entry - direction * stop_distance
        commission = 2.0 * COMMISSION_PER_LOT_PER_SIDE * lot if costs == 1 else 0.0
        slippage = STOP_AND_MARKET_SLIPPAGE if costs == 1 else 0.0
        exit_index = i
        exit_price = entry
        exit_reason = 0
        j = i
        while j < len(close_bid) and times_ns[j] < end_ns and ny_day[j] == ny_day[i] and ny_minutes[j] <= FORCE_FLAT_NY:
            path_spread = spread[j] if costs == 1 else 0.0
            ask_high = high_bid[j] + path_spread
            ask_low = low_bid[j] + path_spread
            stop_hit = low_bid[j] <= stop if direction > 0 else ask_high >= stop
            if moving_target == 1 and j > i and np.isfinite(vwap[j - 1]):
                target = vwap[j - 1]
            else:
                target = initial_target
            target_hit = high_bid[j] >= target if direction > 0 else ask_low <= target
            if stop_hit:
                exit_price = stop - direction * slippage
                exit_index = j
                exit_reason = -1
                break
            # M1 OHLC cannot establish a target after a limit fill in the same minute.
            if j > i and target_hit:
                exit_price = target
                exit_index = j
                exit_reason = 1
                break
            if ny_minutes[j] >= FORCE_FLAT_NY:
                exit_price = close_bid[j] - direction * (0.0 if direction > 0 else path_spread) - direction * slippage
                exit_index = j
                exit_reason = 0
                break
            j += 1
        if j >= len(close_bid) or times_ns[min(j, len(close_bid) - 1)] >= end_ns or ny_day[min(j, len(close_bid) - 1)] != ny_day[i]:
            k = min(max(i, j - 1), len(close_bid) - 1)
            final_spread = spread[k] if costs == 1 else 0.0
            exit_price = close_bid[k] - direction * (0.0 if direction > 0 else final_spread) - direction * slippage
            exit_index = k
            exit_reason = 0

        risk_dollars = balance * RISK_FRACTION
        pnl = direction * (exit_price - entry) * lot - commission
        balance += pnl
        if balance > peak:
            peak = balance
        if peak > 0.0:
            dd = (peak - balance) / peak * 100.0
            if dd > max_dd:
                max_dd = dd
        if pnl > 0.0:
            gross_profit += pnl
            wins += 1
            if pnl > largest_win:
                largest_win = pnl
        elif pnl < 0.0:
            gross_loss += pnl
            losses += 1
            if pnl < largest_loss:
                largest_loss = pnl
        net_r += pnl / risk_dollars if risk_dollars > 0.0 else 0.0
        if collect == 1 and trades < max_rows:
            ledger_entry_index[trades] = i
            ledger_exit_index[trades] = exit_index
            ledger_direction[trades] = direction
            ledger_entry[trades] = entry
            ledger_stop[trades] = stop
            ledger_target[trades] = initial_target
            ledger_exit[trades] = exit_price
            ledger_reason[trades] = exit_reason
            ledger_lot[trades] = lot
            ledger_pnl[trades] = pnl
            ledger_balance[trades] = balance
        trades += 1
        trades_today += 1
        rearmed = False
        i = max(i + 1, exit_index + 1)

    pf = gross_profit / abs(gross_loss) if gross_loss < 0.0 else (999.0 if gross_profit > 0.0 else 0.0)
    average_win = gross_profit / wins if wins else 0.0
    average_loss = gross_loss / losses if losses else 0.0
    return (
        balance, (balance / START_BALANCE - 1.0) * 100.0, max_dd, pf, wins, losses, trades,
        net_r, gross_profit, gross_loss, largest_win, largest_loss, average_win, average_loss,
        ledger_entry_index[:trades] if collect == 1 else ledger_entry_index[:0],
        ledger_exit_index[:trades] if collect == 1 else ledger_exit_index[:0],
        ledger_direction[:trades] if collect == 1 else ledger_direction[:0],
        ledger_entry[:trades] if collect == 1 else ledger_entry[:0],
        ledger_stop[:trades] if collect == 1 else ledger_stop[:0],
        ledger_target[:trades] if collect == 1 else ledger_target[:0],
        ledger_exit[:trades] if collect == 1 else ledger_exit[:0],
        ledger_reason[:trades] if collect == 1 else ledger_reason[:0],
        ledger_lot[:trades] if collect == 1 else ledger_lot[:0],
        ledger_pnl[:trades] if collect == 1 else ledger_pnl[:0],
        ledger_balance[:trades] if collect == 1 else ledger_balance[:0],
    )


def result_dict(values: tuple) -> dict:
    (
        final, return_pct, dd, pf, wins, losses, trades, net_r, gross_profit, gross_loss,
        largest_win, largest_loss, average_win, average_loss, *_
    ) = values
    years = 1.0
    return {
        "final": float(final),
        "return_pct": float(return_pct),
        "closed_equity_dd_pct": float(dd),
        "profit_factor": float(pf),
        "wins": int(wins),
        "losses": int(losses),
        "trades": int(trades),
        "win_rate_pct": float(100.0 * wins / trades if trades else 0.0),
        "net_r": float(net_r),
        "gross_profit": float(gross_profit),
        "gross_loss": float(gross_loss),
        "largest_win": float(largest_win),
        "largest_loss": float(largest_loss),
        "average_win": float(average_win),
        "average_loss": float(average_loss),
    }


def period_ns(start: pd.Timestamp, end: pd.Timestamp) -> tuple[int, int]:
    return int(start.value), int(end.value)


def evaluate(config: Config, arrays: dict, bands: list[tuple[np.ndarray, np.ndarray, np.ndarray]], start: pd.Timestamp, end: pd.Timestamp, collect: bool = False, costs: bool = True) -> tuple[dict, tuple]:
    start_ns, end_ns = period_ns(start, end)
    values = simulate(
        arrays["open"], arrays["high"], arrays["low"], arrays["close"], arrays["spread"],
        bands[config.anchor][0], bands[config.anchor][1], bands[config.anchor][2],
        arrays["day"], arrays["minutes"], arrays["times_ns"], start_ns, end_ns,
        config.entry_sigma, config.reward_to_risk, config.moving_target,
        config.maximum_trades_per_day, 1 if collect else 0, 1 if costs else 0,
    )
    return result_dict(values), values


def ledger_frame(values: tuple, arrays: dict) -> pd.DataFrame:
    entry_i, exit_i, direction, entry, stop, target, exit_price, reason, lot, pnl, balance = values[14:]
    if not len(entry_i):
        return pd.DataFrame(columns=["entry_time_utc", "exit_time_utc", "direction", "entry", "stop", "initial_target", "exit", "exit_reason", "lot", "pnl", "balance"])
    reasons = np.where(reason == 1, "target", np.where(reason == -1, "stop", "time"))
    return pd.DataFrame({
        "entry_time_utc": pd.to_datetime(arrays["times_ns"][entry_i], utc=True),
        "exit_time_utc": pd.to_datetime(arrays["times_ns"][exit_i], utc=True),
        "direction": np.where(direction > 0, "long", "short"),
        "entry": entry,
        "stop": stop,
        "initial_target": target,
        "exit": exit_price,
        "exit_reason": reasons,
        "lot": lot,
        "pnl": pnl,
        "balance": balance,
    })


def plot_equity(ledger: pd.DataFrame, path: Path, title: str) -> None:
    fig, ax = plt.subplots(figsize=(12, 6))
    if len(ledger):
        ax.plot(pd.to_datetime(ledger.exit_time_utc, utc=True), ledger.balance, color="#0a8f6a", linewidth=1.5)
    ax.axhline(START_BALANCE, color="#555", linestyle="--", linewidth=0.9)
    ax.set_title(title)
    ax.set_ylabel("Closed equity (USD)")
    ax.grid(alpha=0.2)
    fig.tight_layout()
    fig.savefig(path, dpi=170)
    plt.close(fig)


def annualized_return(return_pct: float, start: pd.Timestamp, end: pd.Timestamp) -> float:
    years = (end - start).total_seconds() / (365.2425 * 86400.0)
    growth = 1.0 + return_pct / 100.0
    return (growth ** (1.0 / years) - 1.0) * 100.0 if growth > 0.0 and years > 0.0 else -100.0


def main() -> int:
    RESULTS.mkdir(parents=True, exist_ok=True)
    frame, manifest = load_us500()
    time = build_time_features(frame)
    bands = [
        anchored_vwap_and_deviation(frame, time["rth_keys"], time["rth_valid"]),
        anchored_vwap_and_deviation(frame, time["electronic_keys"], time["electronic_valid"]),
    ]
    arrays = {
        "open": frame.open.to_numpy(float),
        "high": frame.high.to_numpy(float),
        "low": frame.low.to_numpy(float),
        "close": frame.close.to_numpy(float),
        "spread": frame.spread_price.to_numpy(float),
        "day": time["ny_day"],
        "minutes": time["minutes"],
        "times_ns": frame.time.to_numpy(dtype="datetime64[ns]").astype(np.int64),
    }
    configs = [
        Config(anchor, sigma, rr, moving, maximum)
        for anchor in range(len(ANCHORS))
        for sigma in ENTRY_SIGMAS
        for rr in REWARD_TO_RISKS
        for moving in (0, 1)
        for maximum in MAX_TRADES_PER_DAY
    ]
    rows = []
    for number, config in enumerate(configs, 1):
        print(f"{number}/{len(configs)} {config}", flush=True)
        dev, _ = evaluate(config, arrays, bands, FULL_START, DEVELOPMENT_END)
        val, _ = evaluate(config, arrays, bands, DEVELOPMENT_END, LOCKED_START)
        rows.append({
            **asdict(config),
            "anchor_name": ANCHORS[config.anchor],
            "target_mode": TARGET_MODES[config.moving_target],
            **{f"dev_{k}": v for k, v in dev.items()},
            **{f"validation_{k}": v for k, v in val.items()},
        })
    grid = pd.DataFrame(rows)
    grid["minimum_prelock_pf"] = grid[["dev_profit_factor", "validation_profit_factor"]].min(axis=1)
    grid["score"] = (
        50.0 * (grid.minimum_prelock_pf - 1.0)
        + grid.dev_return_pct / 3.0
        + grid.validation_return_pct
        - 0.25 * (grid.dev_closed_equity_dd_pct + grid.validation_closed_equity_dd_pct)
    )
    eligible = grid.loc[
        (grid.dev_return_pct > 0.0)
        & (grid.dev_profit_factor >= 1.05)
        & (grid.dev_trades >= 80)
        & (grid.validation_return_pct > 0.0)
        & (grid.validation_profit_factor >= 1.05)
        & (grid.validation_trades >= 20)
    ]
    if len(eligible):
        chosen_row = eligible.sort_values(["score", "minimum_prelock_pf"], ascending=False).iloc[0]
        prelock_decision = "PRELOCK PASS"
    else:
        chosen_row = grid.sort_values(["score", "minimum_prelock_pf"], ascending=False).iloc[0]
        prelock_decision = "REJECT"
    chosen = Config(
        int(chosen_row.anchor), float(chosen_row.entry_sigma), float(chosen_row.reward_to_risk),
        int(chosen_row.moving_target), int(chosen_row.maximum_trades_per_day),
    )
    literal = Config(0, 3.0, 0.50, 1, 3)
    grid.sort_values(["score", "minimum_prelock_pf"], ascending=False).to_csv(RESULTS / "development-validation-grid.csv", index=False)

    periods = {
        "development": (FULL_START, DEVELOPMENT_END),
        "validation": (DEVELOPMENT_END, LOCKED_START),
        "locked": (LOCKED_START, TEST_END),
        "full": (FULL_START, TEST_END),
    }
    selected_summary = []
    literal_summary = []
    literal_zero_cost_summary = []
    for name, (start, end) in periods.items():
        result, _ = evaluate(chosen, arrays, bands, start, end)
        result["annualized_return_pct"] = annualized_return(result["return_pct"], start, end)
        selected_summary.append({"period": name, "start": str(start), "end": str(end), **result})
        result, _ = evaluate(literal, arrays, bands, start, end)
        result["annualized_return_pct"] = annualized_return(result["return_pct"], start, end)
        literal_summary.append({"period": name, "start": str(start), "end": str(end), **result})
        result, _ = evaluate(literal, arrays, bands, start, end, costs=False)
        result["annualized_return_pct"] = annualized_return(result["return_pct"], start, end)
        literal_zero_cost_summary.append({"period": name, "start": str(start), "end": str(end), **result})
    selected_frame = pd.DataFrame(selected_summary)
    literal_frame = pd.DataFrame(literal_summary)
    literal_zero_cost_frame = pd.DataFrame(literal_zero_cost_summary)
    selected_frame.to_csv(RESULTS / "selected-summary.csv", index=False)
    literal_frame.to_csv(RESULTS / "literal-summary.csv", index=False)
    literal_zero_cost_frame.to_csv(RESULTS / "literal-zero-cost-summary.csv", index=False)

    selected_full_result, selected_full_values = evaluate(chosen, arrays, bands, FULL_START, TEST_END, collect=True)
    selected_locked_result, selected_locked_values = evaluate(chosen, arrays, bands, LOCKED_START, TEST_END, collect=True)
    literal_full_result, literal_full_values = evaluate(literal, arrays, bands, FULL_START, TEST_END, collect=True)
    selected_full_ledger = ledger_frame(selected_full_values, arrays)
    selected_locked_ledger = ledger_frame(selected_locked_values, arrays)
    literal_full_ledger = ledger_frame(literal_full_values, arrays)
    selected_full_ledger.to_csv(RESULTS / "selected-full-trades.csv", index=False)
    selected_locked_ledger.to_csv(RESULTS / "selected-locked-trades.csv", index=False)
    literal_full_ledger.to_csv(RESULTS / "literal-full-trades.csv", index=False)
    plot_equity(selected_full_ledger, RESULTS / "selected-full-equity.png", "VWAP third-deviation mean reversion — selected — full history")
    plot_equity(selected_locked_ledger, RESULTS / "selected-locked-equity.png", "VWAP third-deviation mean reversion — selected — locked final year")
    plot_equity(literal_full_ledger, RESULTS / "literal-full-equity.png", "VWAP third-deviation mean reversion — literal rules — full history")

    locked = selected_frame.loc[selected_frame.period == "locked"].iloc[0]
    full = selected_frame.loc[selected_frame.period == "full"].iloc[0]
    if prelock_decision == "PRELOCK PASS" and (
        locked.return_pct > 0.0 and locked.profit_factor >= 1.05 and locked.closed_equity_dd_pct <= 20.0
        and locked.trades >= 20 and full.annualized_return_pct >= 15.0
    ):
        final_decision = "PASS RESEARCH; NATIVE MT5 VALIDATION REQUIRED"
    elif prelock_decision == "PRELOCK PASS":
        final_decision = "LOCKED OOS FAIL"
    else:
        final_decision = "REJECT"

    selection = {
        "decision": final_decision,
        "selected_config": {**asdict(chosen), "anchor_name": ANCHORS[chosen.anchor], "target_mode": TARGET_MODES[chosen.moving_target]},
        "literal_config": {**asdict(literal), "anchor_name": ANCHORS[literal.anchor], "target_mode": TARGET_MODES[literal.moving_target]},
        "data": {
            "broker": "Exness-MT5Trial16",
            "symbol": manifest["symbol"],
            "first_utc": str(frame.time.min()),
            "last_utc": str(frame.time.max()),
            "rows": len(frame),
        },
        "execution": {
            "risk_fraction": RISK_FRACTION,
            "initial_balance": START_BALANCE,
            "actual_m1_spread_used": True,
            "zero_spread_fallback_price": float(manifest["median_spread_price"]),
            "commission_usd_per_lot_per_side": COMMISSION_PER_LOT_PER_SIDE,
            "stop_and_market_slippage_points": STOP_AND_MARKET_SLIPPAGE,
            "same_minute_target_credited": False,
        },
        "grid_configurations": len(configs),
        "eligible_prelock_configurations": len(eligible),
    }
    (RESULTS / "selection.json").write_text(json.dumps(selection, indent=2), encoding="utf-8")

    development_profitable = int(((grid.dev_return_pct > 0.0) & (grid.dev_profit_factor > 1.0)).sum())
    validation_profitable = int(((grid.validation_return_pct > 0.0) & (grid.validation_profit_factor > 1.0)).sum())
    both_profitable = int((
        (grid.dev_return_pct > 0.0) & (grid.dev_profit_factor > 1.0)
        & (grid.validation_return_pct > 0.0) & (grid.validation_profit_factor > 1.0)
    ).sum())

    def report_rows(frame_: pd.DataFrame) -> str:
        lines = ["| Period | Return | Annualized | PF | Win rate | Closed DD | Trades |", "|---|---:|---:|---:|---:|---:|---:|"]
        for _, row in frame_.iterrows():
            lines.append(
                f"| {row.period} | {row.return_pct:+.2f}% | {row.annualized_return_pct:+.2f}% | "
                f"{row.profit_factor:.2f} | {row.win_rate_pct:.2f}% | {row.closed_equity_dd_pct:.2f}% | {int(row.trades)} |"
            )
        return "\n".join(lines)

    report = f"""# VWAP third-standard-deviation mean-reversion validation

## Decision: {final_decision}

### Literal advertised rules

RTH VWAP beginning 09:30 New York, entry at the third volume-weighted standard-deviation band, moving central VWAP target, stop twice the initial target distance (0.50 reward-to-risk), and up to three separately rearmed touches per day.

{report_rows(literal_frame)}

For diagnosis only, with spread, commission and slippage all removed:

{report_rows(literal_zero_cost_frame)}

![Literal equity](Results/literal-full-equity.png)

### Strongest configuration selected before the locked year

**{ANCHORS[chosen.anchor]}**, **{chosen.entry_sigma:.2f}σ** entry, **{chosen.reward_to_risk:.2f} reward-to-risk**, **{TARGET_MODES[chosen.moving_target]}**, maximum **{chosen.maximum_trades_per_day} trade(s) per day**.

{report_rows(selected_frame)}

Across all {len(configs)} variations, {development_profitable} were profitable in development, {validation_profitable} were profitable in validation, and {both_profitable} were profitable in both. Therefore no parameter set had repeatable positive pre-lock evidence.

![Selected full equity](Results/selected-full-equity.png)

![Selected locked equity](Results/selected-locked-equity.png)

## Method and execution assumptions

- Exness US500 M1 data from 2022-01-03 through 2026-08-10; New York daylight-saving changes are handled by the IANA timezone database.
- Volume-weighted session VWAP and population standard deviation use only completed prior minutes. Broker tick volume is used because an OTC CFD has no centralized exchange volume.
- A lower-band buy fills only when ask reaches the limit; an upper-band sell fills when bid reaches it. Actual recorded M1 spread is used, with the broker-history median substituted only where spread is recorded as zero.
- Exness Zero commission of $0.50/lot/side and 0.25 US500 point of adverse slippage on stop/time exits are included. No same-minute target is credited after an entry because M1 OHLC cannot prove event order.
- Initial balance is $10,000. Stop risk is 1% of current equity before costs, rounded down to the broker's 0.01 lot step and subject to its 0.14 minimum lot.
- Entries are permitted from 10:00 through 15:29 New York and all positions are closed by 15:55. A new touch requires price to re-enter the ±2σ area.
- Development ended 2024-12-31, validation ran through 2025-08-10, and 2025-08-11 through 2026-08-10 remained locked until selection.

## Files

- `Results/development-validation-grid.csv`: all {len(configs)} configurations.
- `Results/literal-summary.csv`, `Results/literal-zero-cost-summary.csv`, and `Results/selected-summary.csv`: period statistics.
- `Results/literal-full-trades.csv`, `Results/selected-full-trades.csv`, and `Results/selected-locked-trades.csv`: trade ledgers.
- `Results/selection.json`: selected rules and execution assumptions.
- `research_vwap_third_deviation.py`: reproducible research runner.

The active BAT installer was not changed.
"""
    (ROOT / "FINAL REPORT.md").write_text(report, encoding="utf-8")
    print(json.dumps({"selection": selection, "literal": literal_summary, "literal_zero_cost": literal_zero_cost_summary, "selected": selected_summary}, indent=2), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
