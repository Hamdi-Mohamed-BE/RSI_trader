from __future__ import annotations

import itertools
import json
import math
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import yfinance as yf
from numba import njit


ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data"
RESULTS_DIR = ROOT / "results"
RANDOM_SEED = 42


@dataclass(frozen=True)
class Candidate:
    family: str
    direction: str
    regime_ma: int
    atr_stop: float
    max_hold: int
    target_r: float = 0.0
    rsi_period: int = 0
    rsi_entry: int = 0
    rsi_exit: int = 0
    breakout_lookback: int = 0
    exit_ema: int = 0

    @property
    def candidate_id(self) -> str:
        if self.family == "pullback_rsi":
            return (
                f"PB_{self.direction}_MA{self.regime_ma}_RSI{self.rsi_period}_"
                f"E{self.rsi_entry}_X{self.rsi_exit}_ATR{self.atr_stop:g}_"
                f"H{self.max_hold}_T{self.target_r:g}"
            )
        return (
            f"BO_{self.direction}_MA{self.regime_ma}_D{self.breakout_lookback}_"
            f"EMA{self.exit_ema}_ATR{self.atr_stop:g}_H{self.max_hold}"
        )


def download_symbol(symbol: str) -> pd.DataFrame:
    """Download unadjusted daily bars and cache a reproducible CSV snapshot."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    data = yf.download(
        symbol,
        period="max",
        interval="1d",
        auto_adjust=False,
        actions=False,
        progress=False,
        threads=False,
    )
    if data.empty:
        raise RuntimeError(f"No data returned for {symbol}")
    if isinstance(data.columns, pd.MultiIndex):
        data.columns = data.columns.get_level_values(0)
    data = data.rename(columns=str.lower)
    required = ["open", "high", "low", "close"]
    data = data.dropna(subset=required).copy()
    data.index = pd.to_datetime(data.index).tz_localize(None)
    data = data[~data.index.duplicated(keep="last")].sort_index()
    safe_name = symbol.replace("=", "_").replace("^", "")
    data.to_csv(DATA_DIR / f"{safe_name}_daily.csv", index_label="date")
    return data


def rsi(series: pd.Series, period: int) -> pd.Series:
    delta = series.diff()
    gain = delta.clip(lower=0.0)
    loss = -delta.clip(upper=0.0)
    avg_gain = gain.ewm(alpha=1.0 / period, adjust=False, min_periods=period).mean()
    avg_loss = loss.ewm(alpha=1.0 / period, adjust=False, min_periods=period).mean()
    rs = avg_gain / avg_loss.replace(0.0, np.nan)
    value = 100.0 - (100.0 / (1.0 + rs))
    return value.fillna(100.0).where(avg_gain.notna())


def prepare_indicators(data: pd.DataFrame) -> pd.DataFrame:
    frame = data.copy()
    prior_close = frame["close"].shift(1)
    true_range = pd.concat(
        [
            frame["high"] - frame["low"],
            (frame["high"] - prior_close).abs(),
            (frame["low"] - prior_close).abs(),
        ],
        axis=1,
    ).max(axis=1)
    frame["atr14"] = true_range.ewm(alpha=1.0 / 14.0, adjust=False, min_periods=14).mean()
    for length in (100, 200):
        frame[f"sma_{length}"] = frame["close"].rolling(length).mean()
    for length in (5, 10, 20):
        frame[f"ema_{length}"] = frame["close"].ewm(span=length, adjust=False).mean()
    for period in (2, 3):
        frame[f"rsi_{period}"] = rsi(frame["close"], period)
    for lookback in (20, 50, 100):
        frame[f"prior_high_{lookback}"] = frame["high"].rolling(lookback).max().shift(1)
        frame[f"prior_low_{lookback}"] = frame["low"].rolling(lookback).min().shift(1)
    return frame


def generate_candidates() -> list[Candidate]:
    candidates: list[Candidate] = []
    for values in itertools.product(
        ("long", "both"),
        (100, 200),
        (2, 3),
        (5, 10, 20),
        (55, 70),
        (1.5, 2.25, 3.0),
        (5, 10),
        (0.0, 2.0),
    ):
        direction, regime_ma, rp, entry, exit_level, stop, hold, target = values
        candidates.append(
            Candidate(
                family="pullback_rsi",
                direction=direction,
                regime_ma=regime_ma,
                rsi_period=rp,
                rsi_entry=entry,
                rsi_exit=exit_level,
                atr_stop=stop,
                max_hold=hold,
                target_r=target,
            )
        )
    for values in itertools.product(
        ("long", "both"),
        (100, 200),
        (20, 50, 100),
        (5, 10, 20),
        (2.0, 3.0),
        (20, 50),
    ):
        direction, regime_ma, lookback, exit_ema, stop, hold = values
        candidates.append(
            Candidate(
                family="breakout",
                direction=direction,
                regime_ma=regime_ma,
                breakout_lookback=lookback,
                exit_ema=exit_ema,
                atr_stop=stop,
                max_hold=hold,
            )
        )
    return candidates


def candidate_signals(frame: pd.DataFrame, candidate: Candidate) -> tuple[pd.Series, ...]:
    close = frame["close"]
    regime = frame[f"sma_{candidate.regime_ma}"]
    if candidate.family == "pullback_rsi":
        oscillator = frame[f"rsi_{candidate.rsi_period}"]
        long_entry = (close > regime) & (oscillator < candidate.rsi_entry)
        short_entry = (close < regime) & (oscillator > 100 - candidate.rsi_entry)
        long_exit = oscillator > candidate.rsi_exit
        short_exit = oscillator < 100 - candidate.rsi_exit
    else:
        long_entry = (close > regime) & (
            close > frame[f"prior_high_{candidate.breakout_lookback}"]
        )
        short_entry = (close < regime) & (
            close < frame[f"prior_low_{candidate.breakout_lookback}"]
        )
        exit_average = frame[f"ema_{candidate.exit_ema}"]
        long_exit = close < exit_average
        short_exit = close > exit_average
    if candidate.direction == "long":
        short_entry = pd.Series(False, index=frame.index)
    return long_entry.fillna(False), short_entry.fillna(False), long_exit.fillna(False), short_exit.fillna(False)


def backtest(
    frame: pd.DataFrame,
    candidate: Candidate,
    start: str | pd.Timestamp,
    end: str | pd.Timestamp,
    *,
    slippage_points: float = 0.5,
    slippage_bps: float = 0.0,
    commission_points: float = 0.62,
) -> pd.DataFrame:
    """Event-driven, next-open backtest. If stop and target both hit, stop wins."""
    start_ts, end_ts = pd.Timestamp(start), pd.Timestamp(end)
    long_entry, short_entry, long_exit, short_exit = candidate_signals(frame, candidate)
    rows: list[dict] = []
    position: dict | None = None
    pending_exit = False
    just_exited = False
    index = frame.index

    for i in range(1, len(frame)):
        date = index[i]
        if date < start_ts:
            continue
        if date > end_ts:
            break
        bar = frame.iloc[i]
        prior = frame.iloc[i - 1]
        just_exited = False

        if position is not None and pending_exit:
            direction = position["direction"]
            slip = slippage_points + float(bar["open"]) * slippage_bps / 10_000.0
            exit_price = float(bar["open"]) - direction * slip
            rows.append(_close_trade(position, date, exit_price, "signal", commission_points))
            position = None
            pending_exit = False
            just_exited = True

        if position is None and not just_exited:
            direction = 0
            if bool(long_entry.iloc[i - 1]):
                direction = 1
            elif bool(short_entry.iloc[i - 1]):
                direction = -1
            if direction and pd.notna(prior["atr14"]):
                slip = slippage_points + float(bar["open"]) * slippage_bps / 10_000.0
                entry_price = float(bar["open"]) + direction * slip
                risk_points = float(prior["atr14"]) * candidate.atr_stop
                stop_price = entry_price - direction * risk_points
                target_price = (
                    entry_price + direction * risk_points * candidate.target_r
                    if candidate.target_r > 0
                    else None
                )
                position = {
                    "entry_date": date,
                    "entry_price": entry_price,
                    "direction": direction,
                    "risk_points": risk_points,
                    "stop_price": stop_price,
                    "target_price": target_price,
                    "bars_held": 0,
                }

        if position is None:
            continue

        position["bars_held"] += 1
        direction = position["direction"]
        stop_hit = (
            float(bar["low"]) <= position["stop_price"]
            if direction == 1
            else float(bar["high"]) >= position["stop_price"]
        )
        target_hit = False
        if position["target_price"] is not None:
            target_hit = (
                float(bar["high"]) >= position["target_price"]
                if direction == 1
                else float(bar["low"]) <= position["target_price"]
            )

        if stop_hit:
            # Gap-through stops receive the worse opening price; same-bar stop/target ambiguity is conservative.
            if direction == 1:
                exit_price = min(float(bar["open"]), position["stop_price"])
            else:
                exit_price = max(float(bar["open"]), position["stop_price"])
            rows.append(_close_trade(position, date, exit_price, "stop", commission_points))
            position = None
            pending_exit = False
            continue
        if target_hit:
            rows.append(
                _close_trade(position, date, position["target_price"], "target", commission_points)
            )
            position = None
            pending_exit = False
            continue

        rule_exit = bool(long_exit.iloc[i]) if direction == 1 else bool(short_exit.iloc[i])
        pending_exit = rule_exit or position["bars_held"] >= candidate.max_hold

    if position is not None:
        final_date = min(end_ts, frame.index[-1])
        eligible = frame.loc[:final_date]
        if not eligible.empty:
            final_price = float(eligible.iloc[-1]["close"])
            slip = slippage_points + final_price * slippage_bps / 10_000.0
            final_price -= position["direction"] * slip
            rows.append(_close_trade(position, eligible.index[-1], final_price, "period_end", commission_points))

    columns = [
        "entry_date",
        "exit_date",
        "direction",
        "entry_price",
        "exit_price",
        "risk_points",
        "pnl_points",
        "r_multiple",
        "bars_held",
        "exit_reason",
    ]
    return pd.DataFrame(rows, columns=columns)


def _close_trade(
    position: dict,
    exit_date: pd.Timestamp,
    exit_price: float,
    reason: str,
    commission_points: float,
) -> dict:
    pnl_points = (
        position["direction"] * (float(exit_price) - position["entry_price"])
        - commission_points
    )
    return {
        "entry_date": position["entry_date"],
        "exit_date": exit_date,
        "direction": "long" if position["direction"] == 1 else "short",
        "entry_price": position["entry_price"],
        "exit_price": float(exit_price),
        "risk_points": position["risk_points"],
        "pnl_points": pnl_points,
        "r_multiple": pnl_points / position["risk_points"],
        "bars_held": position["bars_held"],
        "exit_reason": reason,
    }


@njit(cache=True)
def _fast_backtest_arrays(
    opens: np.ndarray,
    highs: np.ndarray,
    lows: np.ndarray,
    closes: np.ndarray,
    atrs: np.ndarray,
    long_entries: np.ndarray,
    short_entries: np.ndarray,
    long_exits: np.ndarray,
    short_exits: np.ndarray,
    start_index: int,
    end_index: int,
    atr_stop: float,
    target_r: float,
    max_hold: int,
    slippage_points: float,
    commission_points: float,
) -> tuple[np.ndarray, np.ndarray]:
    """Compiled equivalent used only for the development search."""
    capacity = end_index - start_index + 2
    r_values = np.empty(capacity, dtype=np.float64)
    entry_indices = np.empty(capacity, dtype=np.int64)
    trade_count = 0
    direction = 0
    entry_price = 0.0
    risk_points = 0.0
    stop_price = 0.0
    target_price = 0.0
    active_target = False
    bars_held = 0
    pending_exit = False
    active_entry_index = -1

    for i in range(max(1, start_index), end_index + 1):
        just_exited = False
        if direction != 0 and pending_exit:
            exit_price = opens[i] - direction * slippage_points
            pnl = direction * (exit_price - entry_price) - commission_points
            r_values[trade_count] = pnl / risk_points
            entry_indices[trade_count] = active_entry_index
            trade_count += 1
            direction = 0
            pending_exit = False
            just_exited = True

        if direction == 0 and not just_exited:
            new_direction = 0
            if long_entries[i - 1]:
                new_direction = 1
            elif short_entries[i - 1]:
                new_direction = -1
            if new_direction != 0 and not np.isnan(atrs[i - 1]):
                direction = new_direction
                entry_price = opens[i] + direction * slippage_points
                risk_points = atrs[i - 1] * atr_stop
                stop_price = entry_price - direction * risk_points
                active_target = target_r > 0.0
                if active_target:
                    target_price = entry_price + direction * risk_points * target_r
                bars_held = 0
                active_entry_index = i

        if direction == 0:
            continue

        bars_held += 1
        if direction == 1:
            stop_hit = lows[i] <= stop_price
            target_hit = active_target and highs[i] >= target_price
        else:
            stop_hit = highs[i] >= stop_price
            target_hit = active_target and lows[i] <= target_price

        if stop_hit:
            if direction == 1:
                exit_price = min(opens[i], stop_price)
            else:
                exit_price = max(opens[i], stop_price)
            pnl = direction * (exit_price - entry_price) - commission_points
            r_values[trade_count] = pnl / risk_points
            entry_indices[trade_count] = active_entry_index
            trade_count += 1
            direction = 0
            pending_exit = False
            continue
        if target_hit:
            pnl = direction * (target_price - entry_price) - commission_points
            r_values[trade_count] = pnl / risk_points
            entry_indices[trade_count] = active_entry_index
            trade_count += 1
            direction = 0
            pending_exit = False
            continue

        rule_exit = long_exits[i] if direction == 1 else short_exits[i]
        pending_exit = rule_exit or bars_held >= max_hold

    if direction != 0:
        exit_price = closes[end_index] - direction * slippage_points
        pnl = direction * (exit_price - entry_price) - commission_points
        r_values[trade_count] = pnl / risk_points
        entry_indices[trade_count] = active_entry_index
        trade_count += 1
    return r_values[:trade_count], entry_indices[:trade_count]


def metrics_from_r(r_values: np.ndarray, risk_fraction: float = 0.005) -> dict[str, float | int]:
    if len(r_values) == 0:
        return {
            "trades": 0,
            "profit_factor": 0.0,
            "win_rate_pct": 0.0,
            "max_drawdown_pct": 0.0,
            "total_return_pct": 0.0,
            "net_r": 0.0,
            "avg_r": 0.0,
        }
    gains = r_values[r_values > 0].sum()
    losses = -r_values[r_values < 0].sum()
    pf = gains / losses if losses > 0 else float("inf")
    equity = np.cumprod(1.0 + r_values * risk_fraction)
    equity_with_start = np.insert(equity, 0, 1.0)
    peaks = np.maximum.accumulate(equity_with_start)
    drawdowns = equity_with_start / peaks - 1.0
    return {
        "trades": int(len(r_values)),
        "profit_factor": float(pf),
        "win_rate_pct": float((r_values > 0).mean() * 100.0),
        "max_drawdown_pct": float(-drawdowns.min() * 100.0),
        "total_return_pct": float((equity[-1] - 1.0) * 100.0),
        "net_r": float(r_values.sum()),
        "avg_r": float(r_values.mean()),
    }


def metrics(trades: pd.DataFrame, risk_fraction: float = 0.005) -> dict[str, float | int]:
    if trades.empty:
        return {
            "trades": 0,
            "profit_factor": 0.0,
            "win_rate_pct": 0.0,
            "max_drawdown_pct": 0.0,
            "total_return_pct": 0.0,
            "net_r": 0.0,
            "avg_r": 0.0,
        }
    r_values = trades["r_multiple"].astype(float).to_numpy()
    gains = r_values[r_values > 0].sum()
    losses = -r_values[r_values < 0].sum()
    pf = gains / losses if losses > 0 else float("inf")
    trade_returns = r_values * risk_fraction
    equity = np.cumprod(1.0 + trade_returns)
    equity_with_start = np.insert(equity, 0, 1.0)
    peaks = np.maximum.accumulate(equity_with_start)
    drawdowns = equity_with_start / peaks - 1.0
    return {
        "trades": int(len(trades)),
        "profit_factor": float(pf),
        "win_rate_pct": float((r_values > 0).mean() * 100.0),
        "max_drawdown_pct": float(-drawdowns.min() * 100.0),
        "total_return_pct": float((equity[-1] - 1.0) * 100.0),
        "net_r": float(r_values.sum()),
        "avg_r": float(r_values.mean()),
    }


def evaluate_development(frame: pd.DataFrame, candidates: Iterable[Candidate]) -> pd.DataFrame:
    folds = (
        ("2000-01-01", "2007-12-31"),
        ("2008-01-01", "2014-12-31"),
        ("2015-01-01", "2020-12-31"),
    )
    start_index = int(frame.index.searchsorted(pd.Timestamp(folds[0][0]), side="left"))
    end_index = int(frame.index.searchsorted(pd.Timestamp(folds[-1][1]), side="right") - 1)
    opens = frame["open"].to_numpy(dtype=np.float64)
    highs = frame["high"].to_numpy(dtype=np.float64)
    lows = frame["low"].to_numpy(dtype=np.float64)
    closes = frame["close"].to_numpy(dtype=np.float64)
    atrs = frame["atr14"].to_numpy(dtype=np.float64)
    records: list[dict] = []
    for candidate in candidates:
        long_entry, short_entry, long_exit, short_exit = candidate_signals(frame, candidate)
        r_values, entry_indices = _fast_backtest_arrays(
            opens,
            highs,
            lows,
            closes,
            atrs,
            long_entry.to_numpy(dtype=np.bool_),
            short_entry.to_numpy(dtype=np.bool_),
            long_exit.to_numpy(dtype=np.bool_),
            short_exit.to_numpy(dtype=np.bool_),
            start_index,
            end_index,
            candidate.atr_stop,
            candidate.target_r,
            candidate.max_hold,
            0.5,
            0.62,
        )
        entry_dates = frame.index[entry_indices]
        fold_metrics = []
        for start, end in folds:
            mask = (entry_dates >= pd.Timestamp(start)) & (entry_dates <= pd.Timestamp(end))
            fold_metrics.append(metrics_from_r(r_values[mask]))
        aggregate = metrics_from_r(r_values)
        pfs = [float(item["profit_factor"]) for item in fold_metrics]
        counts = [int(item["trades"]) for item in fold_metrics]
        avg_rs = [float(item["avg_r"]) for item in fold_metrics]
        valid = (
            aggregate["trades"] >= 60
            and min(counts) >= 12
            and min(pfs) >= 0.85
            and sum(pf > 1.0 for pf in pfs) >= 2
            and sum(value > 0.0 for value in avg_rs) >= 2
        )
        capped_pf = np.minimum(pfs, 4.0)
        stability = float(np.median(capped_pf) - np.std(capped_pf))
        score = (
            stability
            + 0.15 * math.log1p(aggregate["trades"])
            + 2.0 * float(aggregate["avg_r"])
            - 0.02 * float(aggregate["max_drawdown_pct"])
        )
        record = {
            "candidate_id": candidate.candidate_id,
            **asdict(candidate),
            "valid": valid,
            "robust_score": score,
            "development_trades": aggregate["trades"],
            "development_pf": aggregate["profit_factor"],
            "development_win_rate_pct": aggregate["win_rate_pct"],
            "development_max_dd_pct": aggregate["max_drawdown_pct"],
        }
        for number, item in enumerate(fold_metrics, start=1):
            record[f"fold{number}_trades"] = item["trades"]
            record[f"fold{number}_pf"] = item["profit_factor"]
            record[f"fold{number}_avg_r"] = item["avg_r"]
        records.append(record)
    result = pd.DataFrame(records)
    return result.sort_values(
        ["valid", "robust_score", "development_trades"], ascending=[False, False, False]
    ).reset_index(drop=True)


def candidate_from_row(row: pd.Series) -> Candidate:
    return Candidate(
        family=str(row["family"]),
        direction=str(row["direction"]),
        regime_ma=int(row["regime_ma"]),
        atr_stop=float(row["atr_stop"]),
        max_hold=int(row["max_hold"]),
        target_r=float(row["target_r"]),
        rsi_period=int(row["rsi_period"]),
        rsi_entry=int(row["rsi_entry"]),
        rsi_exit=int(row["rsi_exit"]),
        breakout_lookback=int(row["breakout_lookback"]),
        exit_ema=int(row["exit_ema"]),
    )


def bootstrap_pf(trades: pd.DataFrame, simulations: int = 5_000) -> dict[str, float]:
    rng = np.random.default_rng(RANDOM_SEED)
    values = trades["r_multiple"].astype(float).to_numpy()
    if len(values) < 2:
        return {"pf_ci_low": 0.0, "pf_ci_high": 0.0, "probability_pf_above_1_pct": 0.0}
    samples = rng.choice(values, size=(simulations, len(values)), replace=True)
    gains = np.where(samples > 0, samples, 0.0).sum(axis=1)
    losses = -np.where(samples < 0, samples, 0.0).sum(axis=1)
    ratios = np.divide(gains, losses, out=np.full_like(gains, np.inf), where=losses > 0)
    return {
        "pf_ci_low": float(np.quantile(ratios, 0.025)),
        "pf_ci_high": float(np.quantile(ratios, 0.975)),
        "probability_pf_above_1_pct": float((ratios > 1.0).mean() * 100.0),
    }


def marked_to_market_equity(
    frame: pd.DataFrame,
    trades: pd.DataFrame,
    start_date: pd.Timestamp,
    end_date: pd.Timestamp,
    risk_fraction: float = 0.005,
) -> pd.DataFrame:
    """Daily-close equity with each trade sized by its initial stop distance."""
    sample = frame.loc[start_date:end_date]
    equity = pd.Series(1.0, index=sample.index, dtype=float)
    current = 1.0
    last_filled = -1
    for row in trades.itertuples(index=False):
        entry_date = pd.Timestamp(row.entry_date)
        exit_date = pd.Timestamp(row.exit_date)
        entry_pos = int(sample.index.searchsorted(entry_date, side="left"))
        exit_pos = int(sample.index.searchsorted(exit_date, side="left"))
        if entry_pos > last_filled + 1:
            equity.iloc[last_filled + 1 : entry_pos] = current
        direction = 1.0 if row.direction == "long" else -1.0
        point_units = current * risk_fraction / float(row.risk_points)
        for position in range(entry_pos, min(exit_pos, len(sample) - 1) + 1):
            if position == exit_pos:
                marked_pnl = float(row.pnl_points)
            else:
                marked_pnl = direction * (
                    float(sample.iloc[position]["close"]) - float(row.entry_price)
                )
            equity.iloc[position] = current + point_units * marked_pnl
        current *= 1.0 + float(row.r_multiple) * risk_fraction
        equity.iloc[exit_pos] = current
        last_filled = exit_pos
    if last_filled < len(equity) - 1:
        equity.iloc[last_filled + 1 :] = current
    peaks = equity.cummax()
    return pd.DataFrame(
        {
            "equity": equity,
            "drawdown_pct": (equity / peaks - 1.0) * 100.0,
        }
    )


def buy_hold_metrics(frame: pd.DataFrame, start: str, end: str) -> dict[str, float]:
    sample = frame.loc[pd.Timestamp(start) : pd.Timestamp(end), "close"].dropna()
    returns = sample.pct_change().fillna(0.0)
    equity = (1.0 + returns).cumprod()
    drawdown = equity / equity.cummax() - 1.0
    return {
        "total_return_pct": float((equity.iloc[-1] - 1.0) * 100.0),
        "max_drawdown_pct": float(-drawdown.min() * 100.0),
    }


def fmt(value: float, digits: int = 2) -> str:
    if math.isinf(value):
        return "∞"
    return f"{value:.{digits}f}"


def write_report(
    candidate: Candidate,
    candidate_count: int,
    nq_data: pd.DataFrame,
    qqq_data: pd.DataFrame,
    dev_trades: pd.DataFrame,
    test_trades: pd.DataFrame,
    qqq_test_trades: pd.DataFrame,
    dev_stats: dict,
    test_stats: dict,
    qqq_stats: dict,
    bootstrap: dict,
    benchmark: dict,
) -> None:
    report = f"""# Nasdaq Loophole Research — Initial Locked Backtest

Generated from data available through **{nq_data.index.max().date()}**.

## Result that matters: untouched NQ test (2021-present)

| Metric | Result |
|---|---:|
| Trades | {test_stats['trades']} |
| Profit factor | {fmt(test_stats['profit_factor'])} |
| Win rate | {fmt(test_stats['win_rate_pct'])}% |
| Maximum drawdown (daily marked-to-market) | {fmt(test_stats['max_drawdown_pct'])}% |
| Total return at 0.5% initial risk/trade | {fmt(test_stats['total_return_pct'])}% |
| Net R | {fmt(test_stats['net_r'])}R |
| Mean trade | {fmt(test_stats['avg_r'], 3)}R |

The maximum drawdown and return use fractional sizing at **0.5% of current equity per initial stop**. Drawdown is marked to each daily close (and realized exit), but does not include intraday unrealized extremes, taxes, financing, or broker margin rules.

## Locked rule

`{candidate.candidate_id}`

- Family: {candidate.family}
- Direction: {candidate.direction}
- Trend regime: {candidate.regime_ma}-day moving average
- RSI period / entry / exit: {candidate.rsi_period} / {candidate.rsi_entry} / {candidate.rsi_exit}
- Breakout lookback / exit EMA: {candidate.breakout_lookback} / {candidate.exit_ema}
- Initial stop: {candidate.atr_stop:g} × ATR(14)
- Profit target: {candidate.target_r:g}R (`0` means no fixed target)
- Maximum holding period: {candidate.max_hold} sessions
- Signal is calculated after the close; execution is at the next open.

## Honest experiment design

- {candidate_count} bounded hypotheses were evaluated.
- Selection data only: 2000–2020, divided into three non-overlapping robustness folds.
- Locked unseen test: 2021 through {nq_data.index.max().date()}.
- Independent implementation check: the locked rule was also run on QQQ during the same test dates.
- NQ cost assumption: 0.5 index points slippage per side plus 0.62 point round-trip commission equivalent (conservative MNQ-style assumption).
- If a daily bar touches both stop and target, the stop is assumed to occur first.
- Entry and indicator calculations contain no same-bar look-ahead.

## Comparison

| Dataset | Period | Trades | Profit factor | Win rate | Max DD | Return at 0.5% risk/trade |
|---|---|---:|---:|---:|---:|---:|
| NQ development | 2000–2020 | {dev_stats['trades']} | {fmt(dev_stats['profit_factor'])} | {fmt(dev_stats['win_rate_pct'])}% | {fmt(dev_stats['max_drawdown_pct'])}% | {fmt(dev_stats['total_return_pct'])}% |
| NQ untouched test | 2021–present | {test_stats['trades']} | {fmt(test_stats['profit_factor'])} | {fmt(test_stats['win_rate_pct'])}% | {fmt(test_stats['max_drawdown_pct'])}% | {fmt(test_stats['total_return_pct'])}% |
| QQQ cross-check | 2021–present | {qqq_stats['trades']} | {fmt(qqq_stats['profit_factor'])} | {fmt(qqq_stats['win_rate_pct'])}% | {fmt(qqq_stats['max_drawdown_pct'])}% | {fmt(qqq_stats['total_return_pct'])}% |

NQ buy-and-hold over the test window returned {fmt(benchmark['total_return_pct'])}% with a {fmt(benchmark['max_drawdown_pct'])}% daily-close drawdown. This is context, not a directly equivalent risk comparison.

## Uncertainty check

Bootstrapping the unseen NQ trades 5,000 times produced a 95% profit-factor interval of **{fmt(bootstrap['pf_ci_low'])}–{fmt(bootstrap['pf_ci_high'])}**. The resampled probability of PF > 1 was **{fmt(bootstrap['probability_pf_above_1_pct'])}%**. A wide interval means the sample is still too small to claim a durable edge.

## Important limitations

This is a research result, not proof of a live-trading loophole. Yahoo's `NQ=F` is a continuous daily series, not a broker's US100 tick feed. It can hide rollover details and cannot model intraday order sequence, spread expansion, rejected orders, latency, financing, or prop-firm rules. Before real money, rerun the locked rule on the exact broker feed, then perform paper and small-size forward tests.

## Reproduce

```powershell
python nasdaq_loophole_backtest.py
```
"""
    (RESULTS_DIR / "backtest_report.md").write_text(report, encoding="utf-8")


def plot_results(equity: pd.DataFrame) -> None:
    plt.style.use("seaborn-v0_8-darkgrid")
    fig, axes = plt.subplots(2, 1, figsize=(12, 8), sharex=True, height_ratios=[2, 1])
    axes[0].plot(equity.index, equity["equity"] * 100.0, color="#00a6a6", linewidth=2)
    axes[0].set_title("Untouched NQ test — risk-normalized daily equity")
    axes[0].set_ylabel("Equity (start = 100)")
    axes[1].fill_between(equity.index, equity["drawdown_pct"], 0, color="#d64b4b", alpha=0.65)
    axes[1].set_ylabel("Drawdown (%)")
    axes[1].set_xlabel("Date")
    fig.tight_layout()
    fig.savefig(RESULTS_DIR / "nq_test_equity.png", dpi=170, bbox_inches="tight")
    plt.close(fig)


def main() -> None:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    nq = prepare_indicators(download_symbol("NQ=F"))
    qqq = prepare_indicators(download_symbol("QQQ"))
    candidates = generate_candidates()
    leaderboard = evaluate_development(nq, candidates)
    leaderboard.to_csv(RESULTS_DIR / "candidate_leaderboard.csv", index=False)
    valid = leaderboard[leaderboard["valid"]]
    if valid.empty:
        raise RuntimeError("No candidate passed the predeclared development robustness gates.")
    selected = candidate_from_row(valid.iloc[0])

    dev_trades = backtest(nq, selected, "2000-01-01", "2020-12-31")
    test_start = pd.Timestamp("2021-01-01")
    test_end = nq.index.max()
    test_trades = backtest(nq, selected, test_start, test_end)
    # QQQ uses 1 bp of slippage per side and zero explicit commission.
    qqq_test_trades = backtest(
        qqq,
        selected,
        test_start,
        min(test_end, qqq.index.max()),
        slippage_points=0.0,
        slippage_bps=1.0,
        commission_points=0.0,
    )

    dev_stats = metrics(dev_trades)
    test_stats = metrics(test_trades)
    qqq_stats = metrics(qqq_test_trades)
    bootstrap = bootstrap_pf(test_trades)
    benchmark = buy_hold_metrics(nq, str(test_start.date()), str(test_end.date()))
    dev_equity = marked_to_market_equity(
        nq, dev_trades, pd.Timestamp("2000-01-01"), pd.Timestamp("2020-12-31")
    )
    equity = marked_to_market_equity(nq, test_trades, test_start, test_end)
    qqq_equity = marked_to_market_equity(
        qqq, qqq_test_trades, test_start, min(test_end, qqq.index.max())
    )
    dev_stats["max_drawdown_pct"] = float(-dev_equity["drawdown_pct"].min())
    test_stats["max_drawdown_pct"] = float(-equity["drawdown_pct"].min())
    qqq_stats["max_drawdown_pct"] = float(-qqq_equity["drawdown_pct"].min())

    dev_trades.to_csv(RESULTS_DIR / "nq_development_trades.csv", index=False)
    test_trades.to_csv(RESULTS_DIR / "nq_unseen_test_trades.csv", index=False)
    qqq_test_trades.to_csv(RESULTS_DIR / "qqq_crosscheck_trades.csv", index=False)
    equity.to_csv(RESULTS_DIR / "nq_test_equity.csv", index_label="date")
    plot_results(equity)
    write_report(
        selected,
        len(candidates),
        nq,
        qqq,
        dev_trades,
        test_trades,
        qqq_test_trades,
        dev_stats,
        test_stats,
        qqq_stats,
        bootstrap,
        benchmark,
    )
    summary = {
        "generated_through": str(test_end.date()),
        "candidate_count": len(candidates),
        "selected_candidate": asdict(selected),
        "selected_candidate_id": selected.candidate_id,
        "development": dev_stats,
        "unseen_nq_test": test_stats,
        "qqq_crosscheck": qqq_stats,
        "unseen_nq_bootstrap": bootstrap,
        "nq_buy_hold_test_period": benchmark,
        "assumptions": {
            "risk_fraction_per_trade": 0.005,
            "nq_slippage_points_per_side": 0.5,
            "nq_round_trip_commission_equivalent_points": 0.62,
            "qqq_slippage_bps_per_side": 1.0,
            "execution": "signal at close, fill at next open",
            "same_bar_stop_target": "stop first",
        },
    }
    (RESULTS_DIR / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
