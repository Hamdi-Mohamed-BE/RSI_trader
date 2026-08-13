from __future__ import annotations

import argparse
import itertools
import json
import math
import random
from dataclasses import asdict, dataclass
from pathlib import Path

import duckdb
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parent
DATA = ROOT / "Data"
RESULTS = ROOT / "Results"
STARTING_BALANCE = 10_000.0
RISK_PER_TRADE = 0.01
TAKER_FEE = 0.0005
SLIPPAGE_PER_SIDE = 0.0001
MAX_NOTIONAL_LEVERAGE = 3.0
TRAIN_START = pd.Timestamp("2024-08-11", tz="UTC")
TRAIN_END = pd.Timestamp("2026-02-10 23:59:59", tz="UTC")
FINAL_START = pd.Timestamp("2026-02-11", tz="UTC")
FINAL_END = pd.Timestamp("2026-08-10 23:59:59", tz="UTC")


@dataclass(frozen=True)
class Params:
    timeframe: int
    lookback: int
    delta_bars: int
    delta_threshold: float
    book_bars: int
    book_threshold: float
    book5_threshold: float
    replenishment_threshold: float
    close_location: float
    relative_volume: float
    max_sweep_atr: float
    stop_atr: float
    reward_risk: float
    max_hold: int
    break_even_r: float
    direction: str
    signal_model: str


def data_path() -> Path:
    candidates = sorted(DATA.glob("btcusdt-orderflow-2024-08-11_2026-08-10.parquet"))
    if not candidates:
        raise SystemExit("The normalized two-year dataset does not exist yet.")
    return candidates[0]


def load_minutes() -> pd.DataFrame:
    path = data_path()
    con = duckdb.connect()
    frame = con.execute(f"SELECT * FROM read_parquet('{path.as_posix()}') ORDER BY time").fetchdf()
    con.close()
    frame["time"] = pd.to_datetime(frame["time"], utc=True)
    return frame.set_index("time").sort_index()


def load_funding() -> dict[str, np.ndarray]:
    path = DATA / "btcusdt-funding-2024-08-11_2026-08-10.parquet"
    if not path.exists():
        raise SystemExit("Run download_funding.py before the backtest.")
    con = duckdb.connect()
    frame = con.execute(f"SELECT * FROM read_parquet('{path.as_posix()}') ORDER BY time").fetchdf()
    con.close()
    frame["time"] = pd.to_datetime(frame["time"], utc=True)
    return {
        "time_ns": frame["time"].astype("int64").to_numpy(),
        "rate": frame["rate"].to_numpy(float),
        "mark_price": frame["mark_price"].to_numpy(float),
    }


def prepare(minutes: pd.DataFrame, timeframe: int) -> pd.DataFrame:
    rule = f"{timeframe}min"
    agg = minutes.resample(rule, label="left", closed="left").agg(
        open=("open", "first"), high=("high", "max"), low=("low", "min"), close=("close", "last"),
        volume=("volume", "sum"), quote_volume=("quote_volume", "sum"), count=("count", "sum"),
        signed_volume=("signed_volume", "sum"), imb_1=("imb_1", "mean"), imb_5=("imb_5", "mean"),
        replenishment_edge=("replenishment_edge", "median"), depth_snapshots=("depth_snapshots", "sum"),
        minute_count=("close", "count"),
    )
    agg = agg.dropna(subset=["open", "high", "low", "close"])
    agg["complete"] = agg["minute_count"] >= max(1, timeframe - 1)
    agg["delta_ratio"] = agg["signed_volume"] / agg["volume"].replace(0, np.nan)
    agg["close_location"] = (agg["close"] - agg["low"]) / (agg["high"] - agg["low"]).replace(0, np.nan)
    prior_close = agg["close"].shift(1)
    true_range = pd.concat(
        [(agg["high"] - agg["low"]), (agg["high"] - prior_close).abs(), (agg["low"] - prior_close).abs()],
        axis=1,
    ).max(axis=1)
    agg["atr"] = true_range.rolling(14, min_periods=14).mean()
    agg["volume_median"] = agg["volume"].rolling(48, min_periods=32).median().shift(1)
    agg["relative_volume"] = agg["volume"] / agg["volume_median"].replace(0, np.nan)
    return agg.replace([np.inf, -np.inf], np.nan)


def make_signals(frame: pd.DataFrame, p: Params, mode: str = "full") -> tuple[np.ndarray, np.ndarray]:
    prior_low = frame["low"].rolling(p.lookback, min_periods=p.lookback).min().shift(1)
    prior_high = frame["high"].rolling(p.lookback, min_periods=p.lookback).max().shift(1)
    delta = frame["signed_volume"].rolling(p.delta_bars, min_periods=p.delta_bars).sum() / frame["volume"].rolling(
        p.delta_bars, min_periods=p.delta_bars
    ).sum().replace(0, np.nan)
    book = frame["imb_1"].rolling(p.book_bars, min_periods=p.book_bars).mean()
    book5 = frame["imb_5"].rolling(p.book_bars, min_periods=p.book_bars).mean()
    replenishment = frame["replenishment_edge"].rolling(p.book_bars, min_periods=p.book_bars).median()
    long_sweep = (prior_low - frame["low"]) / frame["atr"]
    short_sweep = (frame["high"] - prior_high) / frame["atr"]
    if p.signal_model == "continuation":
        core_long = (
            (frame["close"] > prior_high) & (frame["close"].shift(1) <= prior_high.shift(1)) &
            (frame["close_location"] >= p.close_location) & (frame["relative_volume"] >= p.relative_volume)
        )
        core_short = (
            (frame["close"] < prior_low) & (frame["close"].shift(1) >= prior_low.shift(1)) &
            (frame["close_location"] <= 1.0 - p.close_location) & (frame["relative_volume"] >= p.relative_volume)
        )
        long_delta, short_delta = delta >= p.delta_threshold, delta <= -p.delta_threshold
    else:
        core_long = (
            (frame["low"] < prior_low) & (frame["close"] > prior_low) &
            (long_sweep >= 0) & (long_sweep <= p.max_sweep_atr) &
            (frame["close_location"] >= p.close_location) &
            (frame["relative_volume"] >= p.relative_volume)
        )
        core_short = (
            (frame["high"] > prior_high) & (frame["close"] < prior_high) &
            (short_sweep >= 0) & (short_sweep <= p.max_sweep_atr) &
            (frame["close_location"] <= 1.0 - p.close_location) &
            (frame["relative_volume"] >= p.relative_volume)
        )
        long_delta, short_delta = delta <= -p.delta_threshold, delta >= p.delta_threshold
    if mode == "price_only":
        long_signal, short_signal = core_long, core_short
    elif mode == "cvd_only":
        long_signal = core_long & long_delta
        short_signal = core_short & short_delta
    else:
        long_signal = core_long & long_delta & (book >= p.book_threshold) & (
            book5 >= p.book5_threshold
        ) & (replenishment >= p.replenishment_threshold)
        short_signal = core_short & short_delta & (book <= -p.book_threshold) & (
            book5 <= -p.book5_threshold
        ) & (replenishment <= -p.replenishment_threshold)
    valid = frame["complete"].rolling(max(2, p.delta_bars), min_periods=max(2, p.delta_bars)).min().fillna(False).astype(bool)
    long_signal = (long_signal & valid).fillna(False)
    short_signal = (short_signal & valid).fillna(False)
    if p.direction == "long":
        short_signal[:] = False
    elif p.direction == "short":
        long_signal[:] = False
    return long_signal.to_numpy(dtype=bool), short_signal.to_numpy(dtype=bool)


def run_backtest(
    frame: pd.DataFrame, p: Params, start: pd.Timestamp, end: pd.Timestamp,
    funding: dict[str, np.ndarray], mode: str = "full",
) -> dict:
    sample = frame.loc[(frame.index >= start) & (frame.index <= end)].copy()
    if len(sample) < 100:
        return empty_result()
    long_signal, short_signal = make_signals(sample, p, mode)
    opens = sample["open"].to_numpy(float)
    highs = sample["high"].to_numpy(float)
    lows = sample["low"].to_numpy(float)
    closes = sample["close"].to_numpy(float)
    atr = sample["atr"].to_numpy(float)
    complete = sample["complete"].to_numpy(bool)
    times = sample.index
    balance = STARTING_BALANCE
    curve = [{"time": start.isoformat(), "equity": balance}]
    trades = []
    signal_indexes = np.flatnonzero(long_signal | short_signal)
    next_available = 0
    for i in signal_indexes:
        if i < next_available or i >= len(sample) - 1:
            continue
        direction = 1 if long_signal[i] else (-1 if short_signal[i] else 0)
        if direction == 0 or not np.isfinite(atr[i]) or atr[i] <= 0 or not complete[i + 1]:
            continue
        entry_i = i + 1
        raw_entry = opens[entry_i]
        entry = raw_entry * (1.0 + direction * SLIPPAGE_PER_SIDE)
        stop_distance = max(float(atr[i]) * p.stop_atr, entry * 0.0020)
        risk_cash = balance * RISK_PER_TRADE
        quantity = risk_cash / stop_distance
        quantity = min(quantity, balance * MAX_NOTIONAL_LEVERAGE / entry)
        if quantity <= 0:
            continue
        stop = entry - direction * stop_distance
        target = entry + direction * stop_distance * p.reward_risk
        active_stop = stop
        exit_i = min(len(sample) - 1, entry_i + p.max_hold - 1)
        exit_reason = "time"
        raw_exit = closes[exit_i]
        be_armed = False
        for j in range(entry_i, exit_i + 1):
            if not complete[j]:
                raw_exit = closes[j]
                exit_i = j
                exit_reason = "data_gap"
                break
            if direction > 0:
                stop_hit = lows[j] <= active_stop
                target_hit = highs[j] >= target
            else:
                stop_hit = highs[j] >= active_stop
                target_hit = lows[j] <= target
            # Conservative rule: if both are touched in one bar, the stop wins.
            if stop_hit:
                raw_exit = active_stop
                exit_i = j
                exit_reason = "break_even" if be_armed and abs(active_stop - entry) < entry * 0.0002 else "stop"
                break
            if target_hit:
                raw_exit = target
                exit_i = j
                exit_reason = "target"
                break
            if p.break_even_r > 0:
                trigger = entry + direction * stop_distance * p.break_even_r
                reached = highs[j] >= trigger if direction > 0 else lows[j] <= trigger
                if reached:
                    active_stop = entry
                    be_armed = True
        exit_price = raw_exit * (1.0 - direction * SLIPPAGE_PER_SIDE)
        entry_fee = quantity * entry * TAKER_FEE
        exit_fee = quantity * exit_price * TAKER_FEE
        entry_ns = times[entry_i].value
        exit_ns = times[exit_i].value
        funding_from = int(np.searchsorted(funding["time_ns"], entry_ns, side="right"))
        funding_to = int(np.searchsorted(funding["time_ns"], exit_ns, side="right"))
        funding_pnl = 0.0
        if funding_to > funding_from:
            rates = funding["rate"][funding_from:funding_to]
            marks = funding["mark_price"][funding_from:funding_to]
            funding_pnl = float((-direction * quantity * marks * rates).sum())
        pnl = direction * quantity * (exit_price - entry) - entry_fee - exit_fee + funding_pnl
        before = balance
        balance += pnl
        trades.append({
            "signal_time": times[i].isoformat(), "entry_time": times[entry_i].isoformat(),
            "exit_time": times[exit_i].isoformat(), "side": "long" if direction > 0 else "short",
            "entry": entry, "exit": exit_price, "stop_distance": stop_distance, "quantity": quantity,
            "notional": quantity * entry, "fees": entry_fee + exit_fee, "funding_pnl": funding_pnl, "pnl": pnl,
            "return_on_equity_pct": pnl / before * 100.0, "balance": balance, "reason": exit_reason,
        })
        curve.append({"time": times[exit_i].isoformat(), "equity": balance})
        next_available = exit_i + 1
    curve.append({"time": end.isoformat(), "equity": balance})
    return metrics(trades, curve, start, end)


def empty_result() -> dict:
    return {
        "initial": STARTING_BALANCE, "final": STARTING_BALANCE, "net": 0.0, "return_pct": 0.0,
        "profit_factor": 0.0, "win_rate_pct": 0.0, "trades": 0, "wins": 0, "losses": 0,
        "max_drawdown_pct": 0.0, "max_drawdown_amount": 0.0, "average_trade": 0.0,
        "total_fees": 0.0, "total_funding_pnl": 0.0, "largest_win": 0.0, "largest_loss": 0.0,
        "trades_data": [], "curve": [],
    }


def metrics(trades: list[dict], curve: list[dict], start: pd.Timestamp, end: pd.Timestamp) -> dict:
    if not trades:
        result = empty_result()
        result["curve"] = curve
        return result
    pnls = np.array([trade["pnl"] for trade in trades], dtype=float)
    equities = np.array([point["equity"] for point in curve], dtype=float)
    peaks = np.maximum.accumulate(equities)
    drawdowns = peaks - equities
    drawdown_pct = np.divide(drawdowns, peaks, out=np.zeros_like(drawdowns), where=peaks != 0) * 100.0
    gross_profit = float(pnls[pnls > 0].sum())
    gross_loss = float(-pnls[pnls < 0].sum())
    wins = int((pnls > 0).sum())
    losses = int((pnls < 0).sum())
    years = max((end - start).total_seconds() / (365.25 * 86400), 1 / 365.25)
    return {
        "initial": STARTING_BALANCE, "final": float(equities[-1]), "net": float(equities[-1] - STARTING_BALANCE),
        "return_pct": float((equities[-1] / STARTING_BALANCE - 1.0) * 100.0),
        "annualized_return_pct": float(((equities[-1] / STARTING_BALANCE) ** (1.0 / years) - 1.0) * 100.0) if equities[-1] > 0 else -100.0,
        "profit_factor": gross_profit / gross_loss if gross_loss > 0 else (999.0 if gross_profit > 0 else 0.0),
        "win_rate_pct": wins / len(trades) * 100.0, "trades": len(trades), "wins": wins, "losses": losses,
        "max_drawdown_pct": float(drawdown_pct.max()), "max_drawdown_amount": float(drawdowns.max()),
        "average_trade": float(pnls.mean()), "total_fees": float(sum(trade["fees"] for trade in trades)),
        "total_funding_pnl": float(sum(trade["funding_pnl"] for trade in trades)),
        "largest_win": float(pnls.max()), "largest_loss": float(pnls.min()),
        "trades_data": trades, "curve": curve,
    }


def candidates(limit: int = 600) -> list[Params]:
    rng = random.Random(20260813)
    selected = []
    # Add transparent anchors before the randomized coverage.
    anchors = [
        Params(5, 24, 2, 0.15, 2, 0.05, -0.05, 0.0, 0.60, 1.0, 2.0, 1.5, 2.0, 24, 1.0, "both", "reversal"),
        Params(15, 24, 2, 0.15, 2, 0.05, -0.05, 0.0, 0.60, 1.0, 2.0, 1.5, 2.0, 12, 1.0, "both", "reversal"),
        Params(5, 24, 2, 0.15, 2, 0.05, -0.05, 0.0, 0.60, 1.0, 2.0, 1.5, 2.0, 24, 1.0, "both", "continuation"),
    ]
    selected.extend(anchors)
    choices = [
        [5, 15], [12, 24, 48, 72], [1, 2, 3], [0.05, 0.15, 0.25], [1, 2, 3],
        [0.0, 0.05, 0.10], [-0.10, -0.05, 0.0], [-0.03, 0.0, 0.03], [0.55, 0.65],
        [0.8, 1.0, 1.2], [1.0, 2.0], [1.0, 1.5, 2.0], [1.5, 2.0, 2.5, 3.0],
        [12, 24, 48], [0.0, 1.0, 1.5], ["both", "long", "short"], ["reversal", "continuation"],
    ]
    while len(selected) < limit:
        p = Params(*(rng.choice(values) for values in choices))
        if p not in selected:
            selected.append(p)
    return selected


def public_row(result: dict) -> dict:
    return {key: value for key, value in result.items() if key not in {"trades_data", "curve"}}


def params_from_row(row) -> Params:
    return Params(
        timeframe=int(row["timeframe"]), lookback=int(row["lookback"]), delta_bars=int(row["delta_bars"]),
        delta_threshold=float(row["delta_threshold"]), book_bars=int(row["book_bars"]),
        book_threshold=float(row["book_threshold"]), book5_threshold=float(row["book5_threshold"]),
        replenishment_threshold=float(row["replenishment_threshold"]), close_location=float(row["close_location"]),
        relative_volume=float(row["relative_volume"]), max_sweep_atr=float(row["max_sweep_atr"]),
        stop_atr=float(row["stop_atr"]), reward_risk=float(row["reward_risk"]), max_hold=int(row["max_hold"]),
        break_even_r=float(row["break_even_r"]), direction=str(row["direction"]),
        signal_model=str(row["signal_model"]),
    )


def optimize() -> None:
    RESULTS.mkdir(parents=True, exist_ok=True)
    minutes = load_minutes()
    funding = load_funding()
    prepared = {tf: prepare(minutes, tf) for tf in (5, 15)}
    segments = [
        (pd.Timestamp("2024-08-11", tz="UTC"), pd.Timestamp("2025-02-10 23:59:59", tz="UTC")),
        (pd.Timestamp("2025-02-11", tz="UTC"), pd.Timestamp("2025-08-10 23:59:59", tz="UTC")),
        (pd.Timestamp("2025-08-11", tz="UTC"), TRAIN_END),
    ]
    rows = []
    for index, p in enumerate(candidates(), 1):
        segment_results = [run_backtest(prepared[p.timeframe], p, start, end, funding) for start, end in segments]
        full = run_backtest(prepared[p.timeframe], p, TRAIN_START, TRAIN_END, funding)
        returns = [result["return_pct"] for result in segment_results]
        pfs = [result["profit_factor"] for result in segment_results]
        segment_trades = [result["trades"] for result in segment_results]
        stable = all(value > 0 for value in returns) and all(value > 1 for value in pfs) and min(segment_trades) >= 8
        score = (
            min(returns) * 2.0 + sum(returns) / 3.0 + min(min(value, 3.0) for value in pfs) * 4.0 +
            full["return_pct"] - full["max_drawdown_pct"] * 0.75 + math.log1p(full["trades"])
        )
        rows.append({
            "candidate": index, **asdict(p), "stable": stable, "score": score,
            **{f"segment_{n + 1}_return": returns[n] for n in range(3)},
            **{f"segment_{n + 1}_pf": pfs[n] for n in range(3)},
            **{f"segment_{n + 1}_trades": segment_trades[n] for n in range(3)},
            **{f"training_{key}": value for key, value in public_row(full).items()},
        })
        if index % 40 == 0:
            print(f"screened {index} candidates", flush=True)
    table = pd.DataFrame(rows).sort_values(["stable", "score"], ascending=[False, False])
    table.to_csv(RESULTS / "training-screen.csv", index=False)
    eligible = table[(table["stable"]) & (table["training_trades"] >= 50) & (table["training_profit_factor"] >= 1.10)]
    if eligible.empty:
        eligible = table.head(1)
        selection_status = "NO ROBUST TRAINING CANDIDATE; least-bad setting retained only for final falsification"
    else:
        selection_status = "Passed predeclared training stability gate"
    best = eligible.iloc[0]
    p = params_from_row(best)
    selection = {
        "status": selection_status, "parameters": asdict(p),
        "training": {key.removeprefix("training_"): best[key] for key in table.columns if key.startswith("training_")},
        "segments": [
            {"return_pct": best[f"segment_{n}_return"], "profit_factor": best[f"segment_{n}_pf"], "trades": int(best[f"segment_{n}_trades"])}
            for n in range(1, 4)
        ],
        "cost_model": {
            "taker_fee_each_side": TAKER_FEE, "slippage_each_side": SLIPPAGE_PER_SIDE,
            "funding": "actual Binance historical funding rates and mark prices",
        },
        "final_window_not_opened": [FINAL_START.isoformat(), FINAL_END.isoformat()],
    }
    (RESULTS / "selected-training-config.json").write_text(json.dumps(selection, indent=2, default=float), encoding="utf-8")
    print(json.dumps(selection, indent=2, default=float))


def final() -> None:
    selection_path = RESULTS / "selected-training-config.json"
    if not selection_path.exists():
        raise SystemExit("Run --stage optimize first.")
    selection = json.loads(selection_path.read_text(encoding="utf-8"))
    p = Params(**selection["parameters"])
    minutes = load_minutes()
    funding = load_funding()
    frame = prepare(minutes, p.timeframe)
    tests = {
        "full_order_flow": run_backtest(frame, p, FINAL_START, FINAL_END, funding, "full"),
        "cvd_without_book": run_backtest(frame, p, FINAL_START, FINAL_END, funding, "cvd_only"),
        "price_sweep_only": run_backtest(frame, p, FINAL_START, FINAL_END, funding, "price_only"),
    }
    result = tests["full_order_flow"]
    for name, test in tests.items():
        pd.DataFrame(test["trades_data"]).to_csv(RESULTS / f"{name}-trades.csv", index=False)
        pd.DataFrame(test["curve"]).to_csv(RESULTS / f"{name}-equity.csv", index=False)
    summary = {name: public_row(test) for name, test in tests.items()}
    payload = {"selection": selection, "final_window": [FINAL_START.isoformat(), FINAL_END.isoformat()], "tests": summary}
    (RESULTS / "final-results.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
    pd.DataFrame([{"model": name, **values} for name, values in summary.items()]).to_csv(RESULTS / "final-summary.csv", index=False)

    fig, ax = plt.subplots(figsize=(12, 6.5))
    for name, test in tests.items():
        curve = pd.DataFrame(test["curve"])
        if curve.empty:
            continue
        curve["time"] = pd.to_datetime(curve["time"], utc=True)
        label = f"{name.replace('_', ' ')}: {test['return_pct']:+.2f}% | PF {test['profit_factor']:.2f} | DD {test['max_drawdown_pct']:.2f}%"
        ax.step(curve["time"], curve["equity"], where="post", label=label, linewidth=1.8)
    ax.axhline(STARTING_BALANCE, color="gray", linestyle="--", linewidth=1)
    ax.set_title("BTCUSDT untouched holdout — closed equity after fees and slippage")
    ax.set_ylabel("Equity (USD)")
    ax.set_xlabel("Date (UTC)")
    ax.grid(alpha=0.25)
    ax.legend(loc="best")
    fig.tight_layout()
    fig.savefig(RESULTS / "final-equity-comparison.png", dpi=170)
    plt.close(fig)
    print(json.dumps(payload, indent=2))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--stage", choices=["optimize", "final"], required=True)
    args = parser.parse_args()
    optimize() if args.stage == "optimize" else final()


if __name__ == "__main__":
    main()
