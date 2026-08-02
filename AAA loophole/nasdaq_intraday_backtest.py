from __future__ import annotations

import itertools
import json
import math
from dataclasses import asdict, dataclass
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import yfinance as yf
from numba import njit


ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data"
OUT = ROOT / "results_intraday"
RISK_PER_TRADE = 0.005
TEST_START = pd.Timestamp("2026-01-01", tz="UTC")


@dataclass(frozen=True)
class IntradayCandidate:
    family: str
    direction: str
    fast_ema: int
    slow_ema: int
    atr_stop: float
    target_r: float
    entry_start_hour: int
    entry_end_hour: int
    max_hold: int = 5
    rsi_period: int = 0
    rsi_threshold: int = 0
    breakout_lookback: int = 0
    opening_move_atr: float = 0.0

    @property
    def candidate_id(self) -> str:
        core = (
            f"{self.family}_{self.direction}_E{self.fast_ema}-{self.slow_ema}_"
            f"S{self.atr_stop:g}_T{self.target_r:g}_"
            f"HR{self.entry_start_hour}-{self.entry_end_hour}"
        )
        if self.family == "trend_pullback":
            return f"{core}_RSI{self.rsi_period}-{self.rsi_threshold}"
        if self.family == "trend_breakout":
            return f"{core}_BO{self.breakout_lookback}"
        return f"{core}_MOVE{self.opening_move_atr:g}"


def download_hourly() -> pd.DataFrame:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    frame = yf.download(
        "NQ=F",
        period="730d",
        interval="60m",
        auto_adjust=False,
        actions=False,
        progress=False,
        threads=False,
    )
    if frame.empty:
        raise RuntimeError("No NQ hourly data returned")
    if isinstance(frame.columns, pd.MultiIndex):
        frame.columns = frame.columns.get_level_values(0)
    frame = frame.rename(columns=str.lower).dropna(subset=["open", "high", "low", "close"])
    if frame.index.tz is None:
        frame.index = frame.index.tz_localize("UTC")
    else:
        frame.index = frame.index.tz_convert("UTC")
    frame = frame[~frame.index.duplicated(keep="last")].sort_index()
    frame.to_csv(DATA_DIR / "NQ_F_hourly.csv", index_label="datetime_utc")
    return frame


def rsi(series: pd.Series, period: int) -> pd.Series:
    delta = series.diff()
    gain = delta.clip(lower=0.0)
    loss = -delta.clip(upper=0.0)
    avg_gain = gain.ewm(alpha=1.0 / period, adjust=False, min_periods=period).mean()
    avg_loss = loss.ewm(alpha=1.0 / period, adjust=False, min_periods=period).mean()
    value = 100.0 - 100.0 / (1.0 + avg_gain / avg_loss.replace(0.0, np.nan))
    return value.fillna(100.0).where(avg_gain.notna())


def prepare(frame: pd.DataFrame) -> pd.DataFrame:
    result = frame.copy()
    previous = result["close"].shift(1)
    tr = pd.concat(
        [
            result["high"] - result["low"],
            (result["high"] - previous).abs(),
            (result["low"] - previous).abs(),
        ],
        axis=1,
    ).max(axis=1)
    result["atr20"] = tr.ewm(alpha=1.0 / 20.0, adjust=False, min_periods=20).mean()
    for length in (8, 12, 20, 32, 48, 60):
        result[f"ema_{length}"] = result["close"].ewm(span=length, adjust=False).mean()
    for period in (2, 3):
        result[f"rsi_{period}"] = rsi(result["close"], period)
    for lookback in (3, 6, 12):
        result[f"prior_high_{lookback}"] = result["high"].rolling(lookback).max().shift(1)
        result[f"prior_low_{lookback}"] = result["low"].rolling(lookback).min().shift(1)

    local = result.index.tz_convert("America/New_York")
    result["et_hour"] = local.hour.astype(np.int16)
    local_midnight = local.tz_localize(None).normalize()
    # Convert explicitly to calendar-day resolution. Pandas may store downloaded
    # timestamps at second rather than nanosecond resolution, so dividing the raw
    # integer representation by nanoseconds can silently collapse many dates.
    result["day_code"] = local_midnight.to_numpy(dtype="datetime64[D]").astype(np.int64)
    first_rth_open = result["open"].where(result["et_hour"] == 9)
    result["session_open"] = first_rth_open.groupby(result["day_code"]).transform("max")
    result["opening_move_atr"] = (result["close"] - result["session_open"]) / result["atr20"]
    return result


def candidates() -> list[IntradayCandidate]:
    output: list[IntradayCandidate] = []
    ema_pairs = ((8, 32), (12, 48), (20, 60))
    for direction, (fast, slow), lookback, stop, target, start_hour in itertools.product(
        ("long", "both"), ema_pairs, (3, 6, 12), (1.0, 1.5, 2.0), (1.0, 1.5, 2.0), (10, 11)
    ):
        output.append(
            IntradayCandidate(
                family="trend_breakout",
                direction=direction,
                fast_ema=fast,
                slow_ema=slow,
                atr_stop=stop,
                target_r=target,
                entry_start_hour=start_hour,
                entry_end_hour=14,
                breakout_lookback=lookback,
            )
        )
    for direction, (fast, slow), period, threshold, stop, target, start_hour in itertools.product(
        ("long", "both"),
        ema_pairs,
        (2, 3),
        (10, 20, 30),
        (1.0, 1.5, 2.0),
        (1.0, 1.5, 2.0),
        (10, 11),
    ):
        output.append(
            IntradayCandidate(
                family="trend_pullback",
                direction=direction,
                fast_ema=fast,
                slow_ema=slow,
                atr_stop=stop,
                target_r=target,
                entry_start_hour=start_hour,
                entry_end_hour=14,
                rsi_period=period,
                rsi_threshold=threshold,
            )
        )
    for family, direction, (fast, slow), move, stop, target, hour in itertools.product(
        ("opening_momentum", "opening_reversal"),
        ("long", "both"),
        ema_pairs,
        (0.25, 0.5, 0.75),
        (1.0, 1.5),
        (1.0, 1.5, 2.0),
        (11, 12),
    ):
        output.append(
            IntradayCandidate(
                family=family,
                direction=direction,
                fast_ema=fast,
                slow_ema=slow,
                atr_stop=stop,
                target_r=target,
                entry_start_hour=hour,
                entry_end_hour=hour,
                opening_move_atr=move,
            )
        )
    return output


def signals(frame: pd.DataFrame, candidate: IntradayCandidate) -> tuple[np.ndarray, ...]:
    close = frame["close"]
    fast = frame[f"ema_{candidate.fast_ema}"]
    slow = frame[f"ema_{candidate.slow_ema}"]
    bull, bear = fast > slow, fast < slow
    if candidate.family == "trend_breakout":
        long_entry = bull & (close > frame[f"prior_high_{candidate.breakout_lookback}"])
        short_entry = bear & (close < frame[f"prior_low_{candidate.breakout_lookback}"])
    elif candidate.family == "trend_pullback":
        oscillator = frame[f"rsi_{candidate.rsi_period}"]
        long_entry = bull & (oscillator < candidate.rsi_threshold)
        short_entry = bear & (oscillator > 100 - candidate.rsi_threshold)
    else:
        move = frame["opening_move_atr"]
        if candidate.family == "opening_momentum":
            long_entry = bull & (move > candidate.opening_move_atr)
            short_entry = bear & (move < -candidate.opening_move_atr)
        else:
            long_entry = bull & (move < -candidate.opening_move_atr)
            short_entry = bear & (move > candidate.opening_move_atr)
    if candidate.direction == "long":
        short_entry = pd.Series(False, index=frame.index)
    return long_entry.fillna(False).to_numpy(bool), short_entry.fillna(False).to_numpy(bool)


@njit(cache=True)
def fast_replay(
    opens: np.ndarray,
    highs: np.ndarray,
    lows: np.ndarray,
    closes: np.ndarray,
    atrs: np.ndarray,
    day_codes: np.ndarray,
    hours: np.ndarray,
    long_signal: np.ndarray,
    short_signal: np.ndarray,
    start_index: int,
    end_index: int,
    atr_stop: float,
    target_r: float,
    entry_start: int,
    entry_end: int,
    max_hold: int,
    slippage: float,
    commission: float,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    capacity = end_index - start_index + 2
    r_values = np.empty(capacity, np.float64)
    entries = np.empty(capacity, np.int64)
    exits = np.empty(capacity, np.int64)
    count = 0
    direction = 0
    traded_day = -10_000_000
    active_day = -10_000_000
    entry_price = risk_points = stop_price = target_price = 0.0
    bars_held = 0
    entry_index = -1

    for i in range(max(1, start_index), end_index + 1):
        if direction != 0 and day_codes[i] != active_day:
            exit_price = opens[i] - direction * slippage
            pnl = direction * (exit_price - entry_price) - commission
            r_values[count], entries[count], exits[count] = pnl / risk_points, entry_index, i
            count += 1
            direction = 0

        eligible_hour = entry_start <= hours[i] <= entry_end
        same_day_signal = day_codes[i - 1] == day_codes[i]
        if direction == 0 and traded_day != day_codes[i] and eligible_hour and same_day_signal:
            new_direction = 1 if long_signal[i - 1] else (-1 if short_signal[i - 1] else 0)
            if new_direction != 0 and not np.isnan(atrs[i - 1]):
                direction = new_direction
                traded_day = day_codes[i]
                active_day = day_codes[i]
                entry_index = i
                entry_price = opens[i] + direction * slippage
                risk_points = atrs[i - 1] * atr_stop
                stop_price = entry_price - direction * risk_points
                target_price = entry_price + direction * risk_points * target_r
                bars_held = 0

        if direction == 0:
            continue
        bars_held += 1
        stop_hit = lows[i] <= stop_price if direction == 1 else highs[i] >= stop_price
        target_hit = highs[i] >= target_price if direction == 1 else lows[i] <= target_price
        if stop_hit:
            exit_price = min(opens[i], stop_price) if direction == 1 else max(opens[i], stop_price)
            pnl = direction * (exit_price - entry_price) - commission
            r_values[count], entries[count], exits[count] = pnl / risk_points, entry_index, i
            count += 1
            direction = 0
        elif target_hit:
            pnl = direction * (target_price - entry_price) - commission
            r_values[count], entries[count], exits[count] = pnl / risk_points, entry_index, i
            count += 1
            direction = 0
        elif hours[i] >= 15 or bars_held >= max_hold:
            exit_price = closes[i] - direction * slippage
            pnl = direction * (exit_price - entry_price) - commission
            r_values[count], entries[count], exits[count] = pnl / risk_points, entry_index, i
            count += 1
            direction = 0

    if direction != 0:
        exit_price = closes[end_index] - direction * slippage
        pnl = direction * (exit_price - entry_price) - commission
        r_values[count], entries[count], exits[count] = pnl / risk_points, entry_index, end_index
        count += 1
    return r_values[:count], entries[:count], exits[:count]


def replay(frame: pd.DataFrame, candidate: IntradayCandidate, start: pd.Timestamp, end: pd.Timestamp,
           slippage: float = 1.0, commission: float = 0.62) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    long_signal, short_signal = signals(frame, candidate)
    start_i = int(frame.index.searchsorted(start, side="left"))
    end_i = int(frame.index.searchsorted(end, side="right") - 1)
    return fast_replay(
        frame["open"].to_numpy(float), frame["high"].to_numpy(float),
        frame["low"].to_numpy(float), frame["close"].to_numpy(float),
        frame["atr20"].to_numpy(float), frame["day_code"].to_numpy(np.int64),
        frame["et_hour"].to_numpy(np.int16), long_signal, short_signal,
        start_i, end_i, candidate.atr_stop, candidate.target_r,
        candidate.entry_start_hour, candidate.entry_end_hour, candidate.max_hold,
        slippage, commission,
    )


def stats(r_values: np.ndarray, session_days: int | None = None) -> dict:
    if len(r_values) == 0:
        return {"trades": 0, "profit_factor": 0.0, "win_rate_pct": 0.0,
                "max_drawdown_pct": 0.0, "total_return_pct": 0.0,
                "net_r": 0.0, "avg_r": 0.0, "active_days_pct": 0.0,
                "profitable_all_days_pct": 0.0}
    gains = r_values[r_values > 0].sum()
    losses = -r_values[r_values < 0].sum()
    pf = gains / losses if losses else float("inf")
    equity = np.insert(np.cumprod(1.0 + r_values * RISK_PER_TRADE), 0, 1.0)
    drawdown = equity / np.maximum.accumulate(equity) - 1.0
    sessions = int(session_days or len(r_values))
    return {
        "trades": int(len(r_values)),
        "profit_factor": float(pf),
        "win_rate_pct": float((r_values > 0).mean() * 100),
        "max_drawdown_pct": float(-drawdown.min() * 100),
        "total_return_pct": float((equity[-1] - 1.0) * 100),
        "net_r": float(r_values.sum()),
        "avg_r": float(r_values.mean()),
        "active_days_pct": float(len(r_values) / sessions * 100),
        "profitable_all_days_pct": float((r_values > 0).sum() / sessions * 100),
    }


def session_count(frame: pd.DataFrame, start: pd.Timestamp, end: pd.Timestamp) -> int:
    sample = frame.loc[start:end]
    return int(sample.loc[sample["et_hour"] == 9, "day_code"].nunique())


def development_search(frame: pd.DataFrame, universe: list[IntradayCandidate]) -> pd.DataFrame:
    folds = (
        (pd.Timestamp("2024-04-01", tz="UTC"), pd.Timestamp("2024-08-31 23:59", tz="UTC")),
        (pd.Timestamp("2024-09-01", tz="UTC"), pd.Timestamp("2025-01-31 23:59", tz="UTC")),
        (pd.Timestamp("2025-02-01", tz="UTC"), pd.Timestamp("2025-06-30 23:59", tz="UTC")),
    )
    dev_start, dev_end = folds[0][0], folds[-1][1]
    records = []
    for candidate in universe:
        r_values, entries, _ = replay(frame, candidate, dev_start, dev_end)
        entry_dates = frame.index[entries]
        fold_stats = []
        for start, end in folds:
            fold_stats.append(stats(r_values[(entry_dates >= start) & (entry_dates <= end)]))
        aggregate = stats(r_values, session_count(frame, dev_start, dev_end))
        pfs = np.array([item["profit_factor"] for item in fold_stats], float)
        counts = [item["trades"] for item in fold_stats]
        valid = (
            aggregate["trades"] >= 75 and min(counts) >= 15 and
            np.min(pfs) >= 0.80 and int(np.sum(pfs > 1.0)) >= 2
        )
        capped = np.minimum(pfs, 3.5)
        score = (
            float(np.median(capped) - np.std(capped)) +
            1.5 * aggregate["avg_r"] +
            0.08 * math.log1p(aggregate["trades"]) -
            0.02 * aggregate["max_drawdown_pct"] +
            0.001 * min(aggregate["trades"], 200)
        )
        record = {"candidate_id": candidate.candidate_id, **asdict(candidate), "valid": valid,
                  "development_score": score, **{f"development_{k}": v for k, v in aggregate.items()}}
        for number, item in enumerate(fold_stats, 1):
            record[f"fold{number}_pf"] = item["profit_factor"]
            record[f"fold{number}_trades"] = item["trades"]
        records.append(record)
    return pd.DataFrame(records).sort_values(
        ["valid", "development_score"], ascending=[False, False]
    ).reset_index(drop=True)


def from_row(row: pd.Series) -> IntradayCandidate:
    return IntradayCandidate(
        family=str(row["family"]), direction=str(row["direction"]),
        fast_ema=int(row["fast_ema"]), slow_ema=int(row["slow_ema"]),
        atr_stop=float(row["atr_stop"]), target_r=float(row["target_r"]),
        entry_start_hour=int(row["entry_start_hour"]), entry_end_hour=int(row["entry_end_hour"]),
        max_hold=int(row["max_hold"]), rsi_period=int(row["rsi_period"]),
        rsi_threshold=int(row["rsi_threshold"]), breakout_lookback=int(row["breakout_lookback"]),
        opening_move_atr=float(row["opening_move_atr"]),
    )


def select_with_validation(frame: pd.DataFrame, leaderboard: pd.DataFrame) -> tuple[IntradayCandidate, pd.DataFrame]:
    validation_start = pd.Timestamp("2025-07-01", tz="UTC")
    validation_end = pd.Timestamp("2025-12-31 23:59", tz="UTC")
    rows = []
    for _, row in leaderboard[leaderboard["valid"]].head(40).iterrows():
        candidate = from_row(row)
        values, _, _ = replay(frame, candidate, validation_start, validation_end)
        result = stats(values, session_count(frame, validation_start, validation_end))
        validation_ok = result["trades"] >= 25 and result["profit_factor"] >= 0.90
        selection_score = (
            float(row["development_score"]) +
            0.75 * min(result["profit_factor"], 3.5) +
            1.5 * result["avg_r"] -
            0.03 * result["max_drawdown_pct"] +
            0.001 * min(result["trades"], 100)
        )
        rows.append({**row.to_dict(), **{f"validation_{k}": v for k, v in result.items()},
                     "validation_ok": validation_ok, "selection_score": selection_score})
    validation = pd.DataFrame(rows).sort_values(
        ["validation_ok", "selection_score"], ascending=[False, False]
    ).reset_index(drop=True)
    if validation.empty or not bool(validation.iloc[0]["validation_ok"]):
        raise RuntimeError("No intraday rule passed the predeclared validation gate")
    return from_row(validation.iloc[0]), validation


def trade_ledger(frame: pd.DataFrame, candidate: IntradayCandidate, start: pd.Timestamp,
                 end: pd.Timestamp, slippage: float = 1.0, commission: float = 0.62) -> pd.DataFrame:
    values, entries, exits = replay(frame, candidate, start, end, slippage, commission)
    rows = []
    for r_value, entry_i, exit_i in zip(values, entries, exits):
        direction = 1 if signals(frame, candidate)[0][entry_i - 1] else -1
        entry_price = float(frame.iloc[entry_i]["open"]) + direction * slippage
        risk_points = float(frame.iloc[entry_i - 1]["atr20"]) * candidate.atr_stop
        pnl_points = float(r_value) * risk_points
        exit_price = entry_price + direction * (pnl_points + commission)
        rows.append({
            "entry_utc": frame.index[entry_i], "exit_utc": frame.index[exit_i],
            "entry_et": frame.index[entry_i].tz_convert("America/New_York"),
            "exit_et": frame.index[exit_i].tz_convert("America/New_York"),
            "direction": "long" if direction == 1 else "short", "entry_price": entry_price,
            "exit_price": exit_price, "risk_points": risk_points,
            "pnl_points": pnl_points, "r_multiple": float(r_value),
        })
    return pd.DataFrame(rows)


def bootstrap(values: np.ndarray, simulations: int = 5_000) -> dict:
    rng = np.random.default_rng(42)
    samples = rng.choice(values, size=(simulations, len(values)), replace=True)
    gains = np.where(samples > 0, samples, 0).sum(axis=1)
    losses = -np.where(samples < 0, samples, 0).sum(axis=1)
    pf = np.divide(gains, losses, out=np.full_like(gains, np.inf), where=losses > 0)
    return {"pf_ci_low": float(np.quantile(pf, 0.025)), "pf_ci_high": float(np.quantile(pf, 0.975)),
            "probability_pf_above_1_pct": float((pf > 1).mean() * 100)}


def plot_equity(ledger: pd.DataFrame) -> None:
    returns = ledger["r_multiple"].to_numpy(float) * RISK_PER_TRADE
    equity = np.cumprod(1 + returns) * 100
    peak = np.maximum.accumulate(equity)
    dd = (equity / peak - 1) * 100
    dates = pd.to_datetime(ledger["exit_utc"], utc=True)
    plt.style.use("seaborn-v0_8-darkgrid")
    fig, axes = plt.subplots(2, 1, figsize=(12, 8), sharex=True, height_ratios=[2, 1])
    axes[0].plot(dates, equity, color="#007c91", linewidth=2)
    axes[0].set_title("Intraday NQ — sealed 2026 test")
    axes[0].set_ylabel("Equity (start = 100)")
    axes[1].fill_between(dates, dd, 0, color="#d35454", alpha=0.7)
    axes[1].set_ylabel("Drawdown (%)")
    axes[1].set_xlabel("Exit date")
    fig.tight_layout()
    fig.savefig(OUT / "intraday_test_equity.png", dpi=170, bbox_inches="tight")
    plt.close(fig)


def fmt(value: float) -> str:
    return "∞" if math.isinf(value) else f"{value:.2f}"


def write_report(candidate: IntradayCandidate, universe_size: int, data: pd.DataFrame,
                 dev: dict, val: dict, test: dict, boot: dict, stress: dict) -> None:
    report = f"""# Intraday Nasdaq Research — Sealed Test

## Result that matters: January 2026 through {data.index.max().date()}

| Metric | Result |
|---|---:|
| Profit factor | {fmt(test['profit_factor'])} |
| Win rate on active days | {fmt(test['win_rate_pct'])}% |
| Maximum daily-close drawdown | {fmt(test['max_drawdown_pct'])}% |
| Trades | {test['trades']} |
| Active session days | {fmt(test['active_days_pct'])}% |
| Profitable days out of all sessions | {fmt(test['profitable_all_days_pct'])}% |
| Return at 0.5% risk/trade | {fmt(test['total_return_pct'])}% |
| Average trade | {test['avg_r']:.3f}R |

## Locked rule

`{candidate.candidate_id}`

{json.dumps(asdict(candidate), indent=2)}

Only one trade is allowed per New York session. All positions are closed by the end of the regular U.S. session. Signals use a completed hourly bar and enter at the next hourly open.

## Experiment design

- {universe_size} predeclared intraday candidates.
- Development folds: April 2024–June 2025.
- Validation and final selection: July–December 2025.
- Sealed test: January 2026 onward.
- Costs: 1 NQ point of slippage per side plus 0.62 point round-trip commission equivalent.
- Same-bar stop/target ambiguity is resolved against the strategy: stop first.
- Risk normalization: 0.5% of current equity per initial stop.

| Segment | Trades | PF | Win rate | Max DD | Return |
|---|---:|---:|---:|---:|---:|
| Development | {dev['trades']} | {fmt(dev['profit_factor'])} | {fmt(dev['win_rate_pct'])}% | {fmt(dev['max_drawdown_pct'])}% | {fmt(dev['total_return_pct'])}% |
| Validation | {val['trades']} | {fmt(val['profit_factor'])} | {fmt(val['win_rate_pct'])}% | {fmt(val['max_drawdown_pct'])}% | {fmt(val['total_return_pct'])}% |
| Sealed test | {test['trades']} | {fmt(test['profit_factor'])} | {fmt(test['win_rate_pct'])}% | {fmt(test['max_drawdown_pct'])}% | {fmt(test['total_return_pct'])}% |

At five times the modeled execution costs, sealed-test PF is {fmt(stress['profit_factor'])}.

The 5,000-sample trade bootstrap gives a 95% PF interval of {fmt(boot['pf_ci_low'])}–{fmt(boot['pf_ci_high'])}; estimated probability PF > 1 is {fmt(boot['probability_pf_above_1_pct'])}%.

## Interpretation

“Profitable every day” is not a valid promise. The useful figure is profitable days out of all available sessions, which includes no-trade days. Hourly Yahoo continuous futures data is suitable for a prototype, not live deployment: it cannot reproduce your broker's US100 spread, tick sequence, latency, financing, or order rejection. Paper-test the frozen rule on the exact execution feed before risking capital.
"""
    (OUT / "intraday_report.md").write_text(report, encoding="utf-8")


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    frame = prepare(download_hourly())
    universe = candidates()
    leaderboard = development_search(frame, universe)
    leaderboard.to_csv(OUT / "development_leaderboard.csv", index=False)
    selected, validation = select_with_validation(frame, leaderboard)
    validation.to_csv(OUT / "validation_shortlist.csv", index=False)

    dev_start = pd.Timestamp("2024-04-01", tz="UTC")
    dev_end = pd.Timestamp("2025-06-30 23:59", tz="UTC")
    val_start = pd.Timestamp("2025-07-01", tz="UTC")
    val_end = pd.Timestamp("2025-12-31 23:59", tz="UTC")
    test_end = frame.index.max()
    dev_values, _, _ = replay(frame, selected, dev_start, dev_end)
    val_values, _, _ = replay(frame, selected, val_start, val_end)
    test_values, _, _ = replay(frame, selected, TEST_START, test_end)
    dev_stats = stats(dev_values, session_count(frame, dev_start, dev_end))
    val_stats = stats(val_values, session_count(frame, val_start, val_end))
    test_stats = stats(test_values, session_count(frame, TEST_START, test_end))
    stressed_values, _, _ = replay(frame, selected, TEST_START, test_end, slippage=5.0, commission=3.10)
    stress_stats = stats(stressed_values, session_count(frame, TEST_START, test_end))
    boot = bootstrap(test_values)
    ledger = trade_ledger(frame, selected, TEST_START, test_end)
    ledger.to_csv(OUT / "intraday_unseen_trades.csv", index=False)
    plot_equity(ledger)
    write_report(selected, len(universe), frame, dev_stats, val_stats, test_stats, boot, stress_stats)
    summary = {
        "generated_through": str(test_end), "candidate_count": len(universe),
        "selected_candidate_id": selected.candidate_id, "selected_candidate": asdict(selected),
        "development": dev_stats, "validation": val_stats, "sealed_2026_test": test_stats,
        "five_x_cost_stress": stress_stats, "bootstrap": boot,
        "risk_per_trade": RISK_PER_TRADE,
    }
    (OUT / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
