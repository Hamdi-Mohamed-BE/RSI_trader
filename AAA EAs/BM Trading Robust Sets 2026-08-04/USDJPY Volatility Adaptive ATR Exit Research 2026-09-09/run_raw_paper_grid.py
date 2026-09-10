"""Raw Exness-data reproduction of Kang (2026), USDJPY MACD + ATR exits.

The paper evaluates daily MACD models (15..20, 20..27, 16..25) and all
ATR(14) stop/target multipliers from 1.0 to 3.5 in 0.5 increments.  It omits
costs.  This audit reports both that paper-style result and an Exness cost
overlay, while keeping the paper's two-year in-sample/out-of-sample split.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
import csv
import json
import math

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parent
DATA = ROOT / "Data" / "USDJPY-D1.npz"
METADATA = ROOT / "Data" / "metadata.json"
GRID_RESULTS = ROOT / "paper-grid-results.csv"
SUMMARY = ROOT / "raw-paper-summary.json"
REPORT = ROOT / "RAW RESULTS.md"
SELECTED_TRADES = ROOT / "selected-is-atr-oos-trades.csv"

MACD_FAST = range(15, 21)
MACD_SLOW = range(20, 28)
MACD_SIGNAL = range(16, 26)
MULTIPLIERS = (1.0, 1.5, 2.0, 2.5, 3.0, 3.5)
ATR_LENGTH = 14
ROUND_TRIP_COMMISSION_FRACTION = 0.00007  # USD 7/lot at 1x USD notional ~= 0.7 bp.


@dataclass
class Metrics:
    log_return: float
    return_pct: float
    profit_factor: float
    win_rate_pct: float
    max_drawdown_pct: float
    trades: int
    sharpe: float
    expected_trade_pct: float
    average_win_pct: float
    average_loss_pct: float
    max_win_streak: int
    max_loss_streak: int
    long_win_rate_pct: float
    short_win_rate_pct: float


def load_data() -> tuple[pd.DataFrame, dict]:
    with np.load(DATA) as archive:
        rates = archive["rates"]
    frame = pd.DataFrame({name: rates[name] for name in rates.dtype.names})
    frame["time"] = pd.to_datetime(frame["time"], unit="s", utc=True)
    frame = frame.set_index("time").sort_index()
    metadata = json.loads(METADATA.read_text(encoding="utf-8"))

    # Exness stores a short Sunday D1 bar. Merge it into Monday so the input
    # matches the conventional five-session daily FX series used by the paper.
    rows: list[dict] = []
    pending_sunday: pd.Series | None = None
    for timestamp, row in frame.iterrows():
        if timestamp.dayofweek == 6:
            pending_sunday = row
            continue
        values = row.to_dict()
        if timestamp.dayofweek == 0 and pending_sunday is not None:
            values["open"] = float(pending_sunday["open"])
            values["high"] = max(float(pending_sunday["high"]), float(row["high"]))
            values["low"] = min(float(pending_sunday["low"]), float(row["low"]))
            values["tick_volume"] = float(pending_sunday["tick_volume"]) + float(row["tick_volume"])
            values["real_volume"] = float(pending_sunday["real_volume"]) + float(row["real_volume"])
        pending_sunday = None
        values["time"] = timestamp
        rows.append(values)
    daily = pd.DataFrame(rows).set_index("time").sort_index()
    return daily, metadata


def wilder_atr(frame: pd.DataFrame, length: int = ATR_LENGTH) -> pd.Series:
    previous_close = frame["close"].shift(1)
    true_range = pd.concat(
        [
            frame["high"] - frame["low"],
            (frame["high"] - previous_close).abs(),
            (frame["low"] - previous_close).abs(),
        ],
        axis=1,
    ).max(axis=1)
    return true_range.ewm(alpha=1.0 / length, adjust=False).mean()


def macd_signal(close: pd.Series, fast: int, slow: int, signal_length: int) -> np.ndarray:
    fast_ema = close.ewm(span=fast, adjust=False).mean()
    slow_ema = close.ewm(span=slow, adjust=False).mean()
    macd = fast_ema - slow_ema
    signal = macd.ewm(span=signal_length, adjust=False).mean()
    previous_difference = (macd - signal).shift(1)
    difference = macd - signal
    values = np.zeros(len(close), dtype=np.int8)
    values[(difference > 0.0) & (previous_difference <= 0.0)] = 1
    values[(difference < 0.0) & (previous_difference >= 0.0)] = -1
    return values


def streaks(values: list[float]) -> tuple[int, int]:
    best_win = best_loss = current_win = current_loss = 0
    for value in values:
        if value > 0.0:
            current_win += 1
            current_loss = 0
            best_win = max(best_win, current_win)
        elif value < 0.0:
            current_loss += 1
            current_win = 0
            best_loss = max(best_loss, current_loss)
        else:
            current_win = current_loss = 0
    return best_win, best_loss


def metrics(trades: list[dict], use_costs: bool, years: float) -> Metrics:
    key = "net_log_return" if use_costs else "gross_log_return"
    values = [float(trade[key]) for trade in trades]
    simple = [math.expm1(value) for value in values]
    total_log = float(sum(values))
    wins = [value for value in simple if value > 0.0]
    losses = [value for value in simple if value < 0.0]
    gross_profit = sum(wins)
    gross_loss = -sum(losses)
    pf = gross_profit / gross_loss if gross_loss > 0 else (999.0 if gross_profit > 0 else 0.0)
    equity = np.exp(np.cumsum(np.asarray(values, dtype=float))) if values else np.asarray([1.0])
    equity = np.concatenate(([1.0], equity))
    peaks = np.maximum.accumulate(equity)
    max_dd = float(np.max((peaks - equity) / peaks) * 100.0)
    win_streak, loss_streak = streaks(simple)
    annual_trades = len(values) / max(years, 1e-9)
    if len(simple) > 1 and np.std(simple, ddof=1) > 0:
        sharpe = float(np.mean(simple) / np.std(simple, ddof=1) * math.sqrt(annual_trades))
    else:
        sharpe = 0.0
    long_values = [math.expm1(float(t[key])) for t in trades if t["direction"] == "long"]
    short_values = [math.expm1(float(t[key])) for t in trades if t["direction"] == "short"]
    return Metrics(
        log_return=total_log,
        return_pct=math.expm1(total_log) * 100.0,
        profit_factor=pf,
        win_rate_pct=(100.0 * len(wins) / len(simple)) if simple else 0.0,
        max_drawdown_pct=max_dd,
        trades=len(simple),
        sharpe=sharpe,
        expected_trade_pct=(100.0 * float(np.mean(simple))) if simple else 0.0,
        average_win_pct=(100.0 * float(np.mean(wins))) if wins else 0.0,
        average_loss_pct=(100.0 * float(np.mean(losses))) if losses else 0.0,
        max_win_streak=win_streak,
        max_loss_streak=loss_streak,
        long_win_rate_pct=(100.0 * sum(v > 0 for v in long_values) / len(long_values)) if long_values else 0.0,
        short_win_rate_pct=(100.0 * sum(v > 0 for v in short_values) / len(short_values)) if short_values else 0.0,
    )


def simulate(
    frame: pd.DataFrame,
    signals: np.ndarray,
    atr: np.ndarray,
    start: str,
    end: str,
    sl_multiplier: float | None,
    tp_multiplier: float | None,
    point: float,
    tie_policy: str = "stop_first",
) -> list[dict]:
    eligible = (frame.index >= pd.Timestamp(start, tz="UTC")) & (frame.index <= pd.Timestamp(end, tz="UTC"))
    indices = np.flatnonzero(eligible)
    if not len(indices):
        return []

    position = 0
    pending_direction = 0
    entry_price = entry_atr = entry_spread = 0.0
    entry_time: pd.Timestamp | None = None
    trades: list[dict] = []

    def close_trade(exit_price: float, exit_spread: float, exit_time: pd.Timestamp, reason: str) -> None:
        nonlocal position, entry_price, entry_atr, entry_spread, entry_time
        if position == 1:
            gross_log = math.log(exit_price / entry_price)
            net_log = math.log(exit_price / (entry_price + entry_spread)) - ROUND_TRIP_COMMISSION_FRACTION
            direction = "long"
        else:
            gross_log = math.log(entry_price / exit_price)
            net_log = math.log(entry_price / (exit_price + exit_spread)) - ROUND_TRIP_COMMISSION_FRACTION
            direction = "short"
        trades.append(
            {
                "entry_time": entry_time.isoformat() if entry_time is not None else "",
                "exit_time": exit_time.isoformat(),
                "direction": direction,
                "entry_price": entry_price,
                "exit_price": exit_price,
                "entry_atr": entry_atr,
                "exit_reason": reason,
                "gross_log_return": gross_log,
                "net_log_return": net_log,
            }
        )
        position = 0
        entry_price = entry_atr = entry_spread = 0.0
        entry_time = None

    for index in indices:
        timestamp = frame.index[index]
        row = frame.iloc[index]
        spread_price = max(0.0, float(row["spread"]) * point)

        if position != 0 and sl_multiplier is not None and tp_multiplier is not None:
            if position == 1:
                stop = entry_price - sl_multiplier * entry_atr
                target = entry_price + tp_multiplier * entry_atr
                stop_hit = float(row["low"]) <= stop
                target_hit = float(row["high"]) >= target
            else:
                stop = entry_price + sl_multiplier * entry_atr
                target = entry_price - tp_multiplier * entry_atr
                stop_hit = float(row["high"]) >= stop
                target_hit = float(row["low"]) <= target

            if stop_hit and target_hit:
                chosen = target if tie_policy == "target_first" else stop
                close_trade(chosen, spread_price, timestamp, f"ambiguous_{tie_policy}")
            elif stop_hit:
                close_trade(stop, spread_price, timestamp, "atr_stop")
            elif target_hit:
                close_trade(target, spread_price, timestamp, "atr_target")

        if pending_direction != 0:
            if position != 0 and position != pending_direction:
                close_trade(float(row["close"]), spread_price, timestamp, "macd_reverse")
            if position == 0:
                position = pending_direction
                entry_price = float(row["close"])
                entry_atr = float(atr[index])
                entry_spread = spread_price
                entry_time = timestamp
            pending_direction = 0

        today_signal = int(signals[index])
        if today_signal != 0 and today_signal != position:
            pending_direction = today_signal

    if position != 0:
        final_index = int(indices[-1])
        final_row = frame.iloc[final_index]
        final_spread = max(0.0, float(final_row["spread"]) * point)
        close_trade(float(final_row["close"]), final_spread, frame.index[final_index], "sample_end")
    return trades


def record(prefix: str, result: Metrics, destination: dict) -> None:
    for key, value in asdict(result).items():
        destination[f"{prefix}_{key}"] = value


def evaluate_periods(
    frame: pd.DataFrame,
    signals: np.ndarray,
    atr: np.ndarray,
    sl: float | None,
    tp: float | None,
    point: float,
    tie_policy: str = "stop_first",
) -> tuple[dict, dict, list[dict], list[dict]]:
    is_trades = simulate(frame, signals, atr, "2022-01-01", "2023-12-31", sl, tp, point, tie_policy)
    oos_trades = simulate(frame, signals, atr, "2024-01-01", "2025-12-31", sl, tp, point, tie_policy)
    is_result = {
        "gross": metrics(is_trades, False, 2.0),
        "net": metrics(is_trades, True, 2.0),
    }
    oos_result = {
        "gross": metrics(oos_trades, False, 2.0),
        "net": metrics(oos_trades, True, 2.0),
    }
    return is_result, oos_result, is_trades, oos_trades


def config_label(row: dict) -> str:
    if row["kind"] == "baseline":
        return f"MACD({row['fast']},{row['slow']},{row['signal']}) no ATR exits"
    return f"MACD({row['fast']},{row['slow']},{row['signal']}) ATR14 SL {row['sl']:.1f} / TP {row['tp']:.1f}"


def main() -> None:
    frame, metadata = load_data()
    point = float(metadata["point"])
    atr = wilder_atr(frame).to_numpy(dtype=float)
    model_signals: dict[tuple[int, int, int], np.ndarray] = {}
    models = [
        (fast, slow, signal_length)
        for fast in MACD_FAST
        for slow in MACD_SLOW
        for signal_length in MACD_SIGNAL
        if fast < slow
    ]
    assert len(models) == 470

    rows: list[dict] = []
    baseline_by_model: dict[tuple[int, int, int], dict] = {}
    for model_index, (fast, slow, signal_length) in enumerate(models, 1):
        signals = macd_signal(frame["close"], fast, slow, signal_length)
        model_signals[(fast, slow, signal_length)] = signals
        is_result, oos_result, is_trades, oos_trades = evaluate_periods(frame, signals, atr, None, None, point)
        row = {"kind": "baseline", "fast": fast, "slow": slow, "signal": signal_length, "sl": None, "tp": None}
        record("is_gross", is_result["gross"], row)
        record("is_net", is_result["net"], row)
        record("oos_gross", oos_result["gross"], row)
        record("oos_net", oos_result["net"], row)
        rows.append(row)
        baseline_by_model[(fast, slow, signal_length)] = row
        if model_index % 100 == 0:
            print(f"BASELINE {model_index}/470", flush=True)

    for model_index, (fast, slow, signal_length) in enumerate(models, 1):
        signals = model_signals[(fast, slow, signal_length)]
        for sl in MULTIPLIERS:
            for tp in MULTIPLIERS:
                is_result, oos_result, is_trades, oos_trades = evaluate_periods(frame, signals, atr, sl, tp, point)
                row = {"kind": "atr", "fast": fast, "slow": slow, "signal": signal_length, "sl": sl, "tp": tp}
                record("is_gross", is_result["gross"], row)
                record("is_net", is_result["net"], row)
                record("oos_gross", oos_result["gross"], row)
                record("oos_net", oos_result["net"], row)
                rows.append(row)
        if model_index % 50 == 0:
            print(f"ATR GRID {model_index}/470", flush=True)

    result_frame = pd.DataFrame(rows)
    result_frame.to_csv(GRID_RESULTS, index=False)
    baselines = result_frame[result_frame["kind"] == "baseline"].copy()
    exits = result_frame[result_frame["kind"] == "atr"].copy()

    best_baseline = baselines.loc[baselines["is_gross_log_return"].idxmax()].to_dict()
    best_atr = exits.loc[exits["is_gross_log_return"].idxmax()].to_dict()
    best_atr_model = (int(best_atr["fast"]), int(best_atr["slow"]), int(best_atr["signal"]))
    matching_baseline = baseline_by_model[best_atr_model]

    pattern_counts = {}
    for prefix in ("is", "oos"):
        merged = exits.merge(
            baselines[["fast", "slow", "signal", f"{prefix}_gross_log_return"]],
            on=["fast", "slow", "signal"],
            suffixes=("_atr", "_baseline"),
        )
        atr_return = merged[f"{prefix}_gross_log_return_atr"]
        baseline_return = merged[f"{prefix}_gross_log_return_baseline"]
        pattern_counts[prefix] = {
            "A_loss_to_profit": int(((baseline_return < 0) & (atr_return > 0)).sum()),
            "B_profit_enhancement": int(((baseline_return > 0) & (atr_return > baseline_return)).sum()),
            "C_loss_reduction": int(((baseline_return < 0) & (atr_return < 0) & (atr_return > baseline_return)).sum()),
            "D_profit_reduction": int(((baseline_return > 0) & (atr_return > 0) & (atr_return < baseline_return)).sum()),
            "E_loss_increase": int(((baseline_return < 0) & (atr_return < baseline_return)).sum()),
            "F_profit_to_loss": int(((baseline_return > 0) & (atr_return < 0)).sum()),
        }

    stability = exits.merge(
        baselines[["fast", "slow", "signal", "is_gross_log_return", "oos_gross_log_return"]],
        on=["fast", "slow", "signal"],
        suffixes=("_atr", "_baseline"),
    )
    is_enhancement = (
        (stability["is_gross_log_return_baseline"] > 0)
        & (stability["is_gross_log_return_atr"] > stability["is_gross_log_return_baseline"])
    )
    oos_enhancement = (
        (stability["oos_gross_log_return_baseline"] > 0)
        & (stability["oos_gross_log_return_atr"] > stability["oos_gross_log_return_baseline"])
    )
    stable_enhancement_cases = int((is_enhancement & oos_enhancement).sum())

    standard_signals = macd_signal(frame["close"], 12, 26, 9)
    standard_rows = []
    for sl in MULTIPLIERS:
        for tp in MULTIPLIERS:
            is_result, oos_result, _, _ = evaluate_periods(frame, standard_signals, atr, sl, tp, point)
            standard_rows.append(
                {
                    "sl": sl,
                    "tp": tp,
                    "is_gross_log_return": is_result["gross"].log_return,
                    "is_net_log_return": is_result["net"].log_return,
                    "oos_gross_log_return": oos_result["gross"].log_return,
                    "oos_net_log_return": oos_result["net"].log_return,
                }
            )

    _, _, _, selected_oos_trades = evaluate_periods(
        frame,
        model_signals[best_atr_model],
        atr,
        float(best_atr["sl"]),
        float(best_atr["tp"]),
        point,
    )
    pd.DataFrame(selected_oos_trades).to_csv(SELECTED_TRADES, index=False)
    _, optimistic_oos, _, optimistic_trades = evaluate_periods(
        frame,
        model_signals[best_atr_model],
        atr,
        float(best_atr["sl"]),
        float(best_atr["tp"]),
        point,
        tie_policy="target_first",
    )

    summary = {
        "paper": "Kang (2026), Conditional Effectiveness of Volatility-Adaptive Exit Rules in Algorithmic Trading Systems",
        "paper_url": "https://doi.org/10.3390/jrfm19080554",
        "data": {
            **metadata,
            "normalization": "Exness short Sunday D1 bar merged into the following Monday",
            "sample": "2022-01-01 through 2025-12-31",
            "in_sample": "2022-01-01 through 2023-12-31",
            "out_of_sample": "2024-01-01 through 2025-12-31",
        },
        "rules": {
            "models": 470,
            "atr_combinations_per_model": 36,
            "atr_cases": 16920,
            "macd_ranges": {"fast": [15, 20], "slow": [20, 27], "signal": [16, 25]},
            "atr_length": 14,
            "sl_tp_multipliers": list(MULTIPLIERS),
            "execution": "signal at daily close; enter/reverse at following trading-day close; ATR first-hit exits; stop-first on unresolved same-day ties",
            "paper_costs": "none",
            "broker_overlay": "Exness D1 spread proxy plus 0.7 bp round-trip commission at 1x notional",
        },
        "paper_reported": {
            "baseline_mean_log_return_is": 0.1820,
            "baseline_mean_log_return_oos": 0.0720,
            "atr_mean_log_return_is": 0.0524,
            "atr_mean_log_return_oos": 0.0127,
            "pattern_b_is": 107,
            "pattern_b_oos": 801,
        },
        "exness_reproduction": {
            "baseline_mean_log_return_is": float(baselines["is_gross_log_return"].mean()),
            "baseline_mean_log_return_oos": float(baselines["oos_gross_log_return"].mean()),
            "atr_mean_log_return_is": float(exits["is_gross_log_return"].mean()),
            "atr_mean_log_return_oos": float(exits["oos_gross_log_return"].mean()),
            "atr_mean_net_log_return_is": float(exits["is_net_log_return"].mean()),
            "atr_mean_net_log_return_oos": float(exits["oos_net_log_return"].mean()),
            "patterns": pattern_counts,
            "is_profit_enhancement_cases_remaining_enhancements_oos": stable_enhancement_cases,
        },
        "chronological_selection": {
            "best_is_baseline": best_baseline,
            "best_is_atr": best_atr,
            "same_macd_without_atr": matching_baseline,
            "selected_atr_optimistic_tie_oos": asdict(optimistic_oos["net"]),
            "selected_atr_ambiguous_trade_count_oos": int(sum("ambiguous" in t["exit_reason"] for t in optimistic_trades)),
        },
        "standard_macd_12_26_9": {
            "mean_is_gross_log_return": float(np.mean([row["is_gross_log_return"] for row in standard_rows])),
            "mean_oos_gross_log_return": float(np.mean([row["oos_gross_log_return"] for row in standard_rows])),
            "best_is_gross_log_return": float(max(row["is_gross_log_return"] for row in standard_rows)),
            "best_oos_gross_log_return": float(max(row["oos_gross_log_return"] for row in standard_rows)),
        },
        "limitations": [
            "The paper uses Investing.com daily prices; this audit uses deployable Exness broker prices.",
            "The paper omits transaction costs even though ATR exits change trade frequency; the broker overlay is an explicit Calyx addition.",
            "Daily OHLC cannot reveal which threshold hit first when both SL and TP lie inside one bar. The primary audit uses stop-first and reports target-first sensitivity for the chronologically selected case.",
            "The paper reports a distribution study, not one pre-registered recommended parameter set. The selected candidate is chosen only from 2022-2023 and then evaluated untouched on 2024-2025.",
        ],
    }
    SUMMARY.write_text(json.dumps(summary, indent=2, default=str), encoding="utf-8")

    def table_row(name: str, row: dict) -> str:
        return (
            f"| {name} | {config_label(row)} | {row['is_net_return_pct']:+.2f}% | {row['is_net_profit_factor']:.2f} | "
            f"{row['is_net_win_rate_pct']:.2f}% | {row['is_net_max_drawdown_pct']:.2f}% | {int(row['is_net_trades'])} | "
            f"{row['oos_net_return_pct']:+.2f}% | {row['oos_net_profit_factor']:.2f} | {row['oos_net_win_rate_pct']:.2f}% | "
            f"{row['oos_net_max_drawdown_pct']:.2f}% | {int(row['oos_net_trades'])} |"
        )

    atr_improves_oos_return = float(best_atr["oos_net_return_pct"]) > float(matching_baseline["oos_net_return_pct"])
    atr_improves_oos_pf = float(best_atr["oos_net_profit_factor"]) > float(matching_baseline["oos_net_profit_factor"])
    if atr_improves_oos_return and atr_improves_oos_pf and stable_enhancement_cases > 0:
        verdict = "RAW PASS: the ATR rule improves both return and profit factor out of sample and the enhancement survives across at least one chronologically stable configuration. It is eligible for user-reviewed pipeline work, but is not deployment-ready."
    elif float(best_atr["oos_net_return_pct"]) > 0:
        verdict = "RAW REJECT AS A NEW EDGE: the selected ATR version stays profitable, but it does not improve out-of-sample return or profit factor versus the identical MACD without ATR exits. Its only useful result is lower drawdown, so keep it as a possible risk-control experiment rather than add it to Calyx."
    else:
        verdict = "RAW FAIL: the in-sample-selected ATR configuration does not survive the untouched 2024-2025 Exness out-of-sample test after costs. Do not optimize or install it."

    report_lines = [
        "# USDJPY Volatility-Adaptive ATR Exits - raw paper-grid results",
        "",
        "This is a raw reproduction of the paper's daily MACD/ATR framework on Exness USDJPY data. No Calyx session, direction, regime, trailing, breakeven or risk filters were added.",
        "",
        "## Chronological selection",
        "",
        "The candidate is selected using only 2022-2023. Its 2024-2025 statistics are untouched out-of-sample results. Returns below include the Exness spread proxy and 0.7 bp round-trip commission at 1x notional.",
        "",
        "| Selection | Configuration | IS return | IS PF | IS win | IS DD | IS trades | OOS return | OOS PF | OOS win | OOS DD | OOS trades |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
        table_row("Best baseline chosen IS", best_baseline),
        table_row("Best ATR chosen IS", best_atr),
        table_row("Same MACD without ATR", matching_baseline),
        "",
        f"The ATR version cuts matched-model OOS drawdown from {matching_baseline['oos_net_max_drawdown_pct']:.2f}% to {best_atr['oos_net_max_drawdown_pct']:.2f}%, but return falls from {matching_baseline['oos_net_return_pct']:.2f}% to {best_atr['oos_net_return_pct']:.2f}% and PF falls from {matching_baseline['oos_net_profit_factor']:.2f} to {best_atr['oos_net_profit_factor']:.2f}.",
        f"Only {pattern_counts['is']['B_profit_enhancement']} of 16,920 ATR cases improved profit in-sample, and {stable_enhancement_cases} of those remained profit enhancements out of sample.",
        "",
        "## Verdict",
        "",
        verdict,
        "",
        "## Aggregate reproduction versus the paper",
        "",
        "| Measure | Paper 2022-23 | Exness 2022-23 | Paper 2024-25 | Exness 2024-25 |",
        "|---|---:|---:|---:|---:|",
        f"| Mean baseline log return | 0.1820 | {baselines['is_gross_log_return'].mean():.4f} | 0.0720 | {baselines['oos_gross_log_return'].mean():.4f} |",
        f"| Mean ATR log return | 0.0524 | {exits['is_gross_log_return'].mean():.4f} | 0.0127 | {exits['oos_gross_log_return'].mean():.4f} |",
        f"| Profit-enhancement cases | 107 | {pattern_counts['is']['B_profit_enhancement']} | 801 | {pattern_counts['oos']['B_profit_enhancement']} |",
        "",
        "## Raw rules",
        "",
        "- Daily USDJPY closes; MACD fast 15-20, slow 20-27 and signal 16-25, requiring fast < slow.",
        "- Long on bullish MACD crossover and short on bearish crossover; execute at the next trading-day close.",
        "- ATR(14) is fixed at entry. Stop and target grids both use 1.0-3.5 ATR in 0.5 steps.",
        "- Exit at the first ATR threshold, or reverse at the next close after an opposite MACD crossover.",
        "- After an ATR exit, remain flat until a new MACD crossover.",
        "- Primary same-day ambiguity assumption is stop-first; target-first sensitivity is stored in the JSON audit.",
        "",
        "## Important paper limitations",
        "",
        "- The paper does not include transaction costs and does not publish one recommended configuration.",
        "- The 470-model parameter range was itself derived from 2022-2023, so only the 2024-2025 test is genuinely out of sample.",
        "- Daily bars cannot identify first-hit ordering when both stop and target are crossed in one session.",
        "- Exness short Sunday bars were merged into Monday to create conventional five-session FX daily bars.",
        "",
        "No website, installer, BAT, recommended system, live EA or active terminal was changed.",
    ]
    REPORT.write_text("\n".join(report_lines) + "\n", encoding="utf-8")
    print(f"SAVED {REPORT}", flush=True)


if __name__ == "__main__":
    main()
