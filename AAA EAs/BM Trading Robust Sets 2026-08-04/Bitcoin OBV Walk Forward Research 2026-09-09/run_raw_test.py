"""Raw walk-forward transfer of Deprez & Froemmel (2024), OBV family only.

The published paper evaluates 2,475 OBV rules at each of four frequencies and
selects portfolios monthly using only the preceding 12 months.  This script
implements its published Best and Best-50 portfolio variants.  The paper's
FDR+ stationary-bootstrap portfolio is intentionally not approximated.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
import json
import math

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from numba import njit, prange


ROOT = Path(__file__).resolve().parent
DATA_FILE = ROOT / "Data" / "BTCUSD-M5.npz"
FREQUENCIES = {"M10": "10min", "M30": "30min", "H1": "1h", "D1": "1D"}
P_LENGTHS = np.array([2, 6, 12, 18, 24, 30, 48, 96, 144, 168], dtype=np.int64)
Q_LENGTHS = np.array([2, 6, 12, 18, 24, 30, 48, 96, 144, 168, 192], dtype=np.int64)
BANDS_PCT = np.array([0.0, 0.01, 0.05], dtype=np.float64)
DELAYS = np.array([0, 2, 3, 4, 5], dtype=np.int64)
HOLDS = np.array([6, 12, 0], dtype=np.int64)  # 0 represents the paper's infinity case.
PAPER_FEE_ONE_WAY = 0.001


@dataclass(frozen=True)
class Rule:
    rule_id: int
    frequency: str
    p: int
    q: int
    band_pct: float
    delay: int
    hold: str


def load_m5() -> pd.DataFrame:
    with np.load(DATA_FILE) as archive:
        rates = archive["rates"]
    frame = pd.DataFrame({name: rates[name] for name in rates.dtype.names})
    frame["time"] = pd.to_datetime(frame["time"], unit="s", utc=True)
    frame = frame.set_index("time").sort_index()
    return frame


def resample(frame: pd.DataFrame, rule: str) -> pd.DataFrame:
    if rule == "5min":
        return frame.copy()
    aggregated = frame.resample(rule, label="left", closed="left").agg(
        open=("open", "first"),
        high=("high", "max"),
        low=("low", "min"),
        close=("close", "last"),
        tick_volume=("tick_volume", "sum"),
        spread=("spread", "first"),
    )
    return aggregated.dropna(subset=["open", "high", "low", "close"])


def moving_averages(values: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    p_ma = np.empty((len(P_LENGTHS), len(values)), dtype=np.float64)
    q_ma = np.empty((len(Q_LENGTHS), len(values)), dtype=np.float64)
    cumulative = np.concatenate(([0.0], np.cumsum(values, dtype=np.float64)))
    for row, length in enumerate(P_LENGTHS):
        p_ma[row] = np.nan
        p_ma[row, length - 1 :] = (cumulative[length:] - cumulative[:-length]) / length
    for row, length in enumerate(Q_LENGTHS):
        q_ma[row] = np.nan
        q_ma[row, length - 1 :] = (cumulative[length:] - cumulative[:-length]) / length
    return p_ma, q_ma


def rule_parameter_arrays() -> tuple[np.ndarray, ...]:
    rows = []
    for pi, p in enumerate(P_LENGTHS):
        for qi, q in enumerate(Q_LENGTHS):
            if p >= q:
                continue
            for band in BANDS_PCT:
                for delay in DELAYS:
                    for hold in HOLDS:
                        rows.append((pi, qi, band / 100.0, delay, hold))
    values = np.asarray(rows, dtype=np.float64)
    assert len(values) == 2475
    return (
        values[:, 0].astype(np.int64),
        values[:, 1].astype(np.int64),
        values[:, 2],
        values[:, 3].astype(np.int64),
        values[:, 4].astype(np.int64),
    )


@njit(parallel=True, cache=True)
def simulate_family(
    p_ma: np.ndarray,
    q_ma: np.ndarray,
    log_return: np.ndarray,
    spread_fraction: np.ndarray,
    day_index: np.ndarray,
    is_first: np.ndarray,
    is_last: np.ndarray,
    p_index: np.ndarray,
    q_index: np.ndarray,
    band: np.ndarray,
    delay: np.ndarray,
    hold: np.ndarray,
    day_count: int,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    rule_count = len(p_index)
    broker = np.zeros((rule_count, day_count), dtype=np.float32)
    paper = np.zeros((rule_count, day_count), dtype=np.float32)
    turnover = np.zeros((rule_count, day_count), dtype=np.float32)
    first_position = np.zeros((rule_count, day_count), dtype=np.int8)
    last_position = np.zeros((rule_count, day_count), dtype=np.int8)

    for rule in prange(rule_count):
        decision = 0
        previous_position = 0
        long_run = 0
        short_run = 0
        remaining = 0
        required = delay[rule]
        if required < 1:
            required = 1

        for bar in range(len(log_return)):
            position = decision
            changed = abs(position - previous_position)
            day = day_index[bar]
            spread_cost = 0.5 * spread_fraction[bar] * changed
            gross = position * log_return[bar]
            broker[rule, day] += gross - spread_cost
            paper[rule, day] += gross - spread_cost - PAPER_FEE_ONE_WAY * changed
            turnover[rule, day] += changed
            if is_first[bar]:
                first_position[rule, day] = position
            if is_last[bar]:
                last_position[rule, day] = position
            previous_position = position

            short_value = p_ma[p_index[rule], bar]
            long_value = q_ma[q_index[rule], bar]
            signal = 0
            if not np.isnan(short_value) and not np.isnan(long_value):
                threshold = band[rule] * abs(long_value)
                difference = short_value - long_value
                if difference >= threshold:
                    signal = 1
                elif difference <= -threshold:
                    signal = -1

            if signal == 1:
                long_run += 1
                short_run = 0
            elif signal == -1:
                short_run += 1
                long_run = 0
            else:
                long_run = 0
                short_run = 0

            if hold[rule] == 0:
                if decision == 0 and long_run >= required:
                    decision = 1
                elif decision == 1 and short_run >= required:
                    decision = 0
            else:
                if decision == 1:
                    remaining -= 1
                    if remaining <= 0:
                        decision = 0
                elif long_run >= required:
                    decision = 1
                    remaining = hold[rule]

    return broker, paper, turnover, first_position, last_position


@njit(cache=True)
def simulate_single_position(
    short_ma: np.ndarray,
    long_ma: np.ndarray,
    log_return: np.ndarray,
    spread_fraction: np.ndarray,
    band: float,
    delay: int,
    hold: int,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    positions = np.zeros(len(log_return), dtype=np.int8)
    broker = np.zeros(len(log_return), dtype=np.float64)
    paper = np.zeros(len(log_return), dtype=np.float64)
    decision = 0
    previous_position = 0
    long_run = 0
    short_run = 0
    remaining = 0
    required = max(1, delay)
    for bar in range(len(log_return)):
        position = decision
        positions[bar] = position
        changed = abs(position - previous_position)
        spread_cost = 0.5 * spread_fraction[bar] * changed
        gross = position * log_return[bar]
        broker[bar] = gross - spread_cost
        paper[bar] = gross - spread_cost - PAPER_FEE_ONE_WAY * changed
        previous_position = position

        signal = 0
        if not np.isnan(short_ma[bar]) and not np.isnan(long_ma[bar]):
            threshold = band * abs(long_ma[bar])
            difference = short_ma[bar] - long_ma[bar]
            if difference >= threshold:
                signal = 1
            elif difference <= -threshold:
                signal = -1
        if signal == 1:
            long_run += 1
            short_run = 0
        elif signal == -1:
            short_run += 1
            long_run = 0
        else:
            long_run = 0
            short_run = 0
        if hold == 0:
            if decision == 0 and long_run >= required:
                decision = 1
            elif decision == 1 and short_run >= required:
                decision = 0
        else:
            if decision == 1:
                remaining -= 1
                if remaining <= 0:
                    decision = 0
            elif long_run >= required:
                decision = 1
                remaining = hold
    return positions, broker, paper


def prepare_frequency(frame: pd.DataFrame, frequency: str, master_days: pd.DatetimeIndex) -> dict:
    sampled = resample(frame, FREQUENCIES[frequency])
    close = sampled["close"].to_numpy(dtype=np.float64)
    returns = np.zeros(len(close), dtype=np.float64)
    returns[1:] = np.log(close[1:] / close[:-1])
    change = np.zeros(len(close), dtype=np.float64)
    change[1:] = close[1:] - close[:-1]
    signed_volume = np.where(change >= 0, sampled["tick_volume"].to_numpy(dtype=np.float64), -sampled["tick_volume"].to_numpy(dtype=np.float64))
    signed_volume[0] = sampled["tick_volume"].iloc[0]
    obv = np.cumsum(signed_volume)

    point = 0.01
    spread_points = sampled["spread"].to_numpy(dtype=np.float64, copy=True)
    positives = spread_points[spread_points > 0]
    replacement = float(np.median(positives)) if len(positives) else 0.0
    spread_points[spread_points <= 0] = replacement
    spread_fraction = spread_points * point / close

    dates = sampled.index.normalize()
    day_index = master_days.get_indexer(dates).astype(np.int64)
    if (day_index < 0).any():
        raise RuntimeError(f"{frequency}: a bar falls outside the master calendar")
    is_first = np.r_[True, day_index[1:] != day_index[:-1]]
    is_last = np.r_[day_index[:-1] != day_index[1:], True]
    first_spread = np.zeros(len(master_days), dtype=np.float64)
    last_spread = np.zeros(len(master_days), dtype=np.float64)
    first_spread[day_index[is_first]] = spread_fraction[is_first]
    last_spread[day_index[is_last]] = spread_fraction[is_last]
    p_ma, q_ma = moving_averages(obv)
    params = rule_parameter_arrays()
    broker, paper, turnover, first_pos, last_pos = simulate_family(
        p_ma,
        q_ma,
        returns,
        spread_fraction,
        day_index,
        is_first,
        is_last,
        *params,
        len(master_days),
    )
    return {
        "sampled": sampled,
        "obv": obv,
        "returns": returns,
        "spread_fraction": spread_fraction,
        "p_ma": p_ma,
        "q_ma": q_ma,
        "broker": broker,
        "paper": paper,
        "turnover": turnover,
        "first_pos": first_pos,
        "last_pos": last_pos,
        "first_spread": first_spread,
        "last_spread": last_spread,
        "params": params,
    }


def maximum_drawdown(log_returns: np.ndarray) -> float:
    equity = np.exp(np.cumsum(np.nan_to_num(log_returns)))
    peak = np.maximum.accumulate(np.r_[1.0, equity])
    full = np.r_[1.0, equity]
    return float(np.min(full / peak - 1.0))


def daily_metrics(log_returns: np.ndarray) -> dict:
    simple = np.expm1(log_returns)
    total = math.expm1(float(np.sum(log_returns)))
    annual = math.expm1(float(np.mean(log_returns)) * 365.25)
    std = float(np.std(simple, ddof=1)) if len(simple) > 1 else 0.0
    sharpe = float(np.mean(simple) / std * math.sqrt(365.25)) if std > 0 else 0.0
    drawdown = maximum_drawdown(log_returns)
    positive = simple[simple > 0].sum()
    negative = simple[simple < 0].sum()
    daily_pf = float(positive / abs(negative)) if negative else float("inf")
    active = simple != 0
    positive_day_rate = float((simple[active] > 0).mean()) if active.any() else 0.0
    return {
        "return_pct": total * 100.0,
        "annualized_return_pct": annual * 100.0,
        "daily_profit_factor": daily_pf,
        "positive_active_day_pct": positive_day_rate * 100.0,
        "max_drawdown_pct": abs(drawdown) * 100.0,
        "sharpe": sharpe,
        "recovery_factor": total / abs(drawdown) if drawdown < 0 else float("inf"),
    }


def build_rule_table() -> list[Rule]:
    rules = []
    global_id = 0
    for frequency in FREQUENCIES:
        for p in P_LENGTHS:
            for q in Q_LENGTHS:
                if p >= q:
                    continue
                for band in BANDS_PCT:
                    for delay in DELAYS:
                        for hold in HOLDS:
                            rules.append(Rule(global_id, frequency, int(p), int(q), float(band), int(delay), "infinity" if hold == 0 else str(int(hold))))
                            global_id += 1
    assert len(rules) == 9900
    return rules


def month_starts(master_days: pd.DatetimeIndex) -> list[pd.Timestamp]:
    first = master_days[0] + pd.DateOffset(years=1)
    first = pd.Timestamp(year=first.year, month=first.month, day=1, tz="UTC")
    if first < master_days[0] + pd.Timedelta(days=360):
        first += pd.offsets.MonthBegin(1)
    end = master_days[-1] + pd.Timedelta(days=1)
    return list(pd.date_range(first, end, freq="MS", tz="UTC", inclusive="left"))


def select_and_build(
    matrix_for_selection: np.ndarray,
    matrix_to_apply: np.ndarray,
    turnover: np.ndarray,
    first_pos: np.ndarray,
    last_pos: np.ndarray,
    frequency_index: np.ndarray,
    first_spreads: np.ndarray,
    last_spreads: np.ndarray,
    days: pd.DatetimeIndex,
    objective: str,
    top_n: int,
    cost_mode: str,
) -> tuple[np.ndarray, list[dict]]:
    result = np.zeros(len(days), dtype=np.float64)
    selections = []
    months = month_starts(days)
    for start in months:
        stop = start + pd.offsets.MonthBegin(1)
        train_start = start - pd.DateOffset(years=1)
        train = (days >= train_start) & (days < start)
        test = (days >= start) & (days < stop)
        if train.sum() < 330 or not test.any():
            continue
        sample = matrix_for_selection[:, train]
        means = sample.mean(axis=1)
        if objective == "sharpe":
            deviations = sample.std(axis=1, ddof=1)
            scores = np.divide(means, deviations, out=np.full_like(means, -np.inf), where=deviations > 0)
        else:
            scores = means
        picks = np.argpartition(scores, -top_n)[-top_n:]
        picks = picks[np.argsort(scores[picks])[::-1]]
        test_indices = np.flatnonzero(test)
        applied = matrix_to_apply[picks][:, test].mean(axis=0).astype(np.float64)

        first_day = test_indices[0]
        last_day = test_indices[-1]
        entry_cost = 0.0
        exit_cost = 0.0
        for selected in picks:
            freq = frequency_index[selected]
            if first_pos[selected, first_day] == 1:
                entry_cost += 0.5 * first_spreads[freq, first_day]
                if cost_mode == "paper":
                    entry_cost += PAPER_FEE_ONE_WAY
            if last_pos[selected, last_day] == 1:
                exit_cost += 0.5 * last_spreads[freq, last_day]
                if cost_mode == "paper":
                    exit_cost += PAPER_FEE_ONE_WAY
        applied[0] -= entry_cost / top_n
        applied[-1] -= exit_cost / top_n
        result[test] = applied

        equivalent_transactions = float(turnover[picks][:, test].sum() / top_n)
        equivalent_transactions += float(first_pos[picks, first_day].sum() / top_n)
        equivalent_transactions += float(last_pos[picks, last_day].sum() / top_n)
        selections.append({
            "month": start.date().isoformat(),
            "train_start": train_start.date().isoformat(),
            "train_end": (start - pd.Timedelta(days=1)).date().isoformat(),
            "objective": objective,
            "top_n": top_n,
            "cost_mode": cost_mode,
            "selected_rule_ids": ";".join(str(int(value)) for value in picks),
            "best_score": float(scores[picks[0]]),
            "equivalent_transactions": equivalent_transactions,
        })
    return result, selections


def trade_ledger_for_best1(
    selections: pd.DataFrame,
    rules: list[Rule],
    prepared: dict[str, dict],
    cost_mode: str,
) -> pd.DataFrame:
    trades = []
    for row in selections.itertuples(index=False):
        rule_id = int(str(row.selected_rule_ids).split(";")[0])
        rule = rules[rule_id]
        source = prepared[rule.frequency]
        p_row = int(np.flatnonzero(P_LENGTHS == rule.p)[0])
        q_row = int(np.flatnonzero(Q_LENGTHS == rule.q)[0])
        hold = 0 if rule.hold == "infinity" else int(rule.hold)
        positions, broker, paper = simulate_single_position(
            source["p_ma"][p_row],
            source["q_ma"][q_row],
            source["returns"],
            source["spread_fraction"],
            rule.band_pct / 100.0,
            rule.delay,
            hold,
        )
        returns = paper if cost_mode == "paper" else broker
        timestamps = source["sampled"].index
        start = pd.Timestamp(row.month, tz="UTC")
        stop = start + pd.offsets.MonthBegin(1)
        selected = np.flatnonzero((timestamps >= start) & (timestamps < stop))
        if not len(selected):
            continue
        active = False
        accumulated = 0.0
        entry_time = None
        first_bar = int(selected[0])
        for bar in selected:
            position = int(positions[bar])
            if not active and position == 1:
                active = True
                entry_time = timestamps[bar]
                accumulated = 0.0
                if bar == first_bar and bar > 0 and positions[bar - 1] == 1:
                    boundary = 0.5 * source["spread_fraction"][bar]
                    if cost_mode == "paper":
                        boundary += PAPER_FEE_ONE_WAY
                    accumulated -= boundary
            if active:
                accumulated += float(returns[bar])
                if position == 0:
                    trades.append({
                        "entry_utc": entry_time.isoformat(),
                        "exit_utc": timestamps[bar].isoformat(),
                        "month": row.month,
                        "objective": row.objective,
                        "cost_mode": cost_mode,
                        "rule_id": rule_id,
                        "frequency": rule.frequency,
                        "p": rule.p,
                        "q": rule.q,
                        "band_pct": rule.band_pct,
                        "delay": rule.delay,
                        "hold": rule.hold,
                        "return_pct": math.expm1(accumulated) * 100.0,
                    })
                    active = False
                    entry_time = None
                    accumulated = 0.0
        if active:
            bar = int(selected[-1])
            boundary = 0.5 * source["spread_fraction"][bar]
            if cost_mode == "paper":
                boundary += PAPER_FEE_ONE_WAY
            accumulated -= boundary
            trades.append({
                "entry_utc": entry_time.isoformat(),
                "exit_utc": timestamps[bar].isoformat(),
                "month": row.month,
                "objective": row.objective,
                "cost_mode": cost_mode,
                "rule_id": rule_id,
                "frequency": rule.frequency,
                "p": rule.p,
                "q": rule.q,
                "band_pct": rule.band_pct,
                "delay": rule.delay,
                "hold": rule.hold,
                "return_pct": math.expm1(accumulated) * 100.0,
            })
    return pd.DataFrame(trades)


def trade_metrics(trades: pd.DataFrame) -> dict:
    values = trades["return_pct"].to_numpy(dtype=float) / 100.0
    wins = values[values > 0]
    losses = values[values < 0]
    return {
        "trades": int(len(values)),
        "win_rate_pct": float((values > 0).mean() * 100.0) if len(values) else 0.0,
        "profit_factor": float(wins.sum() / abs(losses.sum())) if len(losses) else float("inf"),
        "average_trade_pct": float(values.mean() * 100.0) if len(values) else 0.0,
    }


def annual_stability(daily: pd.DataFrame, trades: pd.DataFrame, column: str) -> list[dict]:
    output = []
    series = daily[column]
    for year, group in series.groupby(series.index.year):
        year_trades = trades[pd.to_datetime(trades["exit_utc"], utc=True).dt.year == year]
        row = {"year": int(year), **daily_metrics(group.to_numpy(dtype=float)), **trade_metrics(year_trades)}
        output.append(row)
    return output


def serializable(value):
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating,)):
        value = float(value)
    if isinstance(value, float) and not math.isfinite(value):
        return None
    return value


def main() -> None:
    frame = load_m5()
    master_days = pd.date_range(frame.index.min().normalize(), frame.index.max().normalize(), freq="D", tz="UTC")
    prepared = {}
    blocks = []
    for frequency in FREQUENCIES:
        print(f"Simulating 2,475 raw OBV rules at {frequency}...", flush=True)
        prepared[frequency] = prepare_frequency(frame, frequency, master_days)
        blocks.append(prepared[frequency])

    broker = np.concatenate([block["broker"] for block in blocks], axis=0)
    paper = np.concatenate([block["paper"] for block in blocks], axis=0)
    turnover = np.concatenate([block["turnover"] for block in blocks], axis=0)
    first_pos = np.concatenate([block["first_pos"] for block in blocks], axis=0)
    last_pos = np.concatenate([block["last_pos"] for block in blocks], axis=0)
    first_spreads = np.stack([block["first_spread"] for block in blocks])
    last_spreads = np.stack([block["last_spread"] for block in blocks])
    frequency_index = np.repeat(np.arange(len(FREQUENCIES), dtype=np.int64), 2475)
    rules = build_rule_table()

    oos_start = month_starts(master_days)[0]
    oos_mask = master_days >= oos_start
    daily = pd.DataFrame(index=master_days[oos_mask])
    all_selections = []
    selection_frames = {}
    for objective in ("mean", "sharpe"):
        for top_n in (1, 50):
            for cost_mode, applied_matrix in (("broker", broker), ("paper", paper)):
                values, selections = select_and_build(
                    paper,
                    applied_matrix,
                    turnover,
                    first_pos,
                    last_pos,
                    frequency_index,
                    first_spreads,
                    last_spreads,
                    master_days,
                    objective,
                    top_n,
                    cost_mode,
                )
                name = f"best{top_n}_{objective}_{cost_mode}"
                daily[name] = values[oos_mask]
                frame_selection = pd.DataFrame(selections)
                selection_frames[name] = frame_selection
                all_selections.extend(selections)

    close_daily = resample(frame, "1D")["close"].reindex(master_days).ffill()
    buyhold = np.zeros(len(master_days), dtype=np.float64)
    prices = close_daily.to_numpy(dtype=np.float64)
    buyhold[1:] = np.log(prices[1:] / prices[:-1])
    daily["buyhold_gross"] = buyhold[oos_mask]
    buyhold_broker = buyhold[oos_mask].copy()
    buyhold_paper = buyhold[oos_mask].copy()
    median_spread = float(np.median(prepared["D1"]["spread_fraction"]))
    buyhold_broker[0] -= 0.5 * median_spread
    buyhold_broker[-1] -= 0.5 * median_spread
    buyhold_paper[0] -= 0.5 * median_spread + PAPER_FEE_ONE_WAY
    buyhold_paper[-1] -= 0.5 * median_spread + PAPER_FEE_ONE_WAY
    daily["buyhold_broker"] = buyhold_broker
    daily["buyhold_paper"] = buyhold_paper

    selection_table = pd.DataFrame(all_selections).drop_duplicates(
        subset=["month", "objective", "top_n", "cost_mode"]
    )
    selection_table.to_csv(ROOT / "monthly-selections.csv", index=False)
    pd.DataFrame([asdict(rule) for rule in rules]).to_csv(ROOT / "rule-universe.csv", index=False)
    daily.to_csv(ROOT / "portfolio-daily.csv", index_label="date_utc")

    best1_trades = []
    summaries = []
    stability = []
    for objective in ("mean", "sharpe"):
        for cost_mode in ("broker", "paper"):
            name = f"best1_{objective}_{cost_mode}"
            choices = selection_frames[name]
            ledger = trade_ledger_for_best1(choices, rules, prepared, cost_mode)
            best1_trades.append(ledger)
            metrics = {**daily_metrics(daily[name].to_numpy(dtype=float)), **trade_metrics(ledger)}
            metrics.update(strategy=f"Best 1 / {objective.title()}", cost_mode=cost_mode, win_rate_basis="closed trades")
            summaries.append(metrics)
            for row in annual_stability(daily, ledger, name):
                stability.append({"strategy": f"Best 1 / {objective.title()}", "cost_mode": cost_mode, **row})

    trades = pd.concat(best1_trades, ignore_index=True)
    trades.to_csv(ROOT / "best1-trades.csv", index=False)

    for objective in ("mean", "sharpe"):
        for top_n in (50,):
            for cost_mode in ("broker", "paper"):
                name = f"best{top_n}_{objective}_{cost_mode}"
                metrics = daily_metrics(daily[name].to_numpy(dtype=float))
                selected = selection_frames[name]
                metrics.update(
                    strategy=f"Best {top_n} / {objective.title()}",
                    cost_mode=cost_mode,
                    trades=float(selected["equivalent_transactions"].sum() / 2.0),
                    win_rate_pct=metrics["positive_active_day_pct"],
                    profit_factor=metrics["daily_profit_factor"],
                    win_rate_basis="positive active days; ensemble has no single trade ledger",
                )
                summaries.append(metrics)

    for cost_mode in ("broker", "paper"):
        metrics = daily_metrics(daily[f"buyhold_{cost_mode}"].to_numpy(dtype=float))
        metrics.update(
            strategy="Buy and hold",
            cost_mode=cost_mode,
            trades=1,
            win_rate_pct=100.0 if metrics["return_pct"] > 0 else 0.0,
            profit_factor=None,
            win_rate_basis="single holding period",
        )
        summaries.append(metrics)

    summary_frame = pd.DataFrame(summaries)
    summary_frame.to_csv(ROOT / "raw-summary.csv", index=False)
    stability_frame = pd.DataFrame(stability)
    stability_frame.to_csv(ROOT / "yearly-stability.csv", index=False)

    frequency_counts = []
    primary_choices = selection_frames["best1_sharpe_paper"]
    for value in primary_choices["selected_rule_ids"]:
        rule = rules[int(str(value).split(";")[0])]
        frequency_counts.append(rule.frequency)
    frequency_mix = pd.Series(frequency_counts).value_counts().to_dict()

    output = {
        "paper": {
            "title": "Are simple technical trading rules profitable in bitcoin markets?",
            "authors": "Niek Deprez and Michael Froemmel",
            "year": 2024,
            "doi": "10.1016/j.iref.2024.05.003",
        },
        "transfer": {
            "asset": "Exness BTCUSD CFD",
            "source_bars": int(len(frame)),
            "source_start_utc": frame.index.min().isoformat(),
            "source_end_utc": frame.index.max().isoformat(),
            "oos_start_utc": oos_start.isoformat(),
            "oos_end_utc": master_days[-1].isoformat(),
            "formation_window": "trailing 12 calendar months",
            "rebalance": "monthly",
            "rules": len(rules),
            "rules_per_frequency": 2475,
            "frequencies": list(FREQUENCIES),
            "direction": "long/flat",
            "volume": "MT5 tick-volume proxy",
            "paper_cost_stress": "0.10% fee plus half observed spread per one-way transaction",
            "broker_cost": "half observed spread per one-way transaction",
            "frequency_mix_best1_sharpe_paper": frequency_mix,
        },
        "summaries": [{key: serializable(value) for key, value in row.items()} for row in summaries],
        "yearly_stability": [{key: serializable(value) for key, value in row.items()} for row in stability],
        "production_action": "none",
    }
    (ROOT / "raw-results.json").write_text(json.dumps(output, indent=2), encoding="utf-8")

    plt.style.use("dark_background")
    fig, ax = plt.subplots(figsize=(12, 6))
    colors = {"best1_sharpe_paper": "#65f6c1", "best50_sharpe_paper": "#5ba6ff", "buyhold_paper": "#f6c65b"}
    labels = {"best1_sharpe_paper": "Best 1 OBV / paper costs", "best50_sharpe_paper": "Best 50 OBV / paper costs", "buyhold_paper": "BTC buy & hold / paper costs"}
    for column in colors:
        equity = 10_000.0 * np.exp(np.cumsum(daily[column].to_numpy(dtype=float)))
        ax.plot(daily.index, equity, label=labels[column], color=colors[column], linewidth=1.6)
    ax.set_title("Bitcoin OBV paper transfer — untouched monthly walk-forward")
    ax.set_ylabel("Growth of $10,000 (log scale)")
    ax.set_yscale("log")
    ax.grid(alpha=0.15)
    ax.legend(frameon=False)
    fig.tight_layout()
    fig.savefig(ROOT / "raw-equity.png", dpi=180)
    plt.close(fig)

    print(summary_frame.to_string(index=False), flush=True)


if __name__ == "__main__":
    main()
