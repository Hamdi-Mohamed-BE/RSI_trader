from __future__ import annotations

import argparse
import itertools
import json
import math
from dataclasses import asdict, dataclass
from pathlib import Path

import matplotlib.pyplot as plt
import numba as nb
import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parent
DATA = ROOT.parent / "Apex Pulse and IVB Research 2026-08-10" / "Data"
RESULTS = ROOT / "Results"
INITIAL_BALANCE = 10_000.0
RISK_FRACTION = 0.01
POINT = 0.01
SLIPPAGE_PRICE = 0.50


@dataclass(frozen=True)
class Params:
    london_close: str
    candle_lookback: int
    min_net_body_points: float
    stop_points: float
    reward_risk: float
    max_hold_minutes: int
    management: str


def load_minutes() -> pd.DataFrame:
    files = sorted(DATA.glob("MEXAtlantic-US100-UT100-M1-20*.csv.gz"))
    frames = [pd.read_csv(path, compression="gzip", parse_dates=["time"]) for path in files]
    frame = pd.concat(frames, ignore_index=True)
    frame["time"] = pd.to_datetime(frame["time"], utc=True)
    frame = frame.drop_duplicates("time", keep="last").sort_values("time").set_index("time")
    positive = frame.loc[frame["spread"] > 0, "spread"]
    fallback = float(positive.median()) if len(positive) else 170.0
    frame.loc[frame["spread"] <= 0, "spread"] = fallback
    frame["spread_price"] = frame["spread"].astype(float) * POINT
    return frame


def make_m15(minutes: pd.DataFrame) -> pd.DataFrame:
    bars = minutes.resample("15min", label="left", closed="left").agg(
        open=("open", "first"),
        high=("high", "max"),
        low=("low", "min"),
        close=("close", "last"),
        tick_volume=("tick_volume", "sum"),
        count=("close", "count"),
    )
    return bars.dropna(subset=["open", "high", "low", "close"])


def build_events(minutes: pd.DataFrame, bars: pd.DataFrame, close_text: str, lookback: int, min_body: float) -> pd.DataFrame:
    hour, minute = (int(part) for part in close_text.split(":"))
    end_utc = bars.index + pd.Timedelta(minutes=15)
    end_london = end_utc.tz_convert("Europe/London")
    positions = np.flatnonzero(
        (end_london.hour == hour)
        & (end_london.minute == minute)
        & (end_london.dayofweek < 5)
        & (bars["count"].to_numpy() >= 12)
    )
    rows: list[dict] = []
    for pos in positions:
        start = pos - lookback + 1
        if start < 0:
            continue
        window = bars.iloc[start : pos + 1]
        expected = pd.date_range(window.index[0], periods=lookback, freq="15min", tz="UTC")
        if len(window) != lookback or not window.index.equals(expected) or (window["count"] < 12).any():
            continue
        local_dates = (window.index + pd.Timedelta(minutes=15)).tz_convert("Europe/London").date
        if len(set(local_dates)) != 1:
            continue
        net_body = float((window["close"] - window["open"]).sum())
        if abs(net_body) < min_body or abs(net_body) < 1e-9:
            continue
        direction = -1 if net_body > 0 else 1
        entry_time = end_utc[pos]
        # Pandas may store this index at microsecond resolution while
        # Timestamp.value is nanoseconds, so use the timezone-aware index
        # search directly instead of comparing differently scaled integers.
        entry_index = int(minutes.index.searchsorted(entry_time, side="left"))
        if entry_index >= len(minutes):
            continue
        actual_time = minutes.index[entry_index]
        if actual_time - entry_time > pd.Timedelta(minutes=2):
            continue
        rows.append(
            {
                "signal_time": entry_time,
                "entry_index": entry_index,
                "direction": direction,
                "net_body_points": net_body,
                "london_date": str(end_london[pos].date()),
            }
        )
    return pd.DataFrame(rows)


@nb.njit(cache=True)
def simulate_fast(
    entries: np.ndarray,
    directions: np.ndarray,
    opens: np.ndarray,
    highs: np.ndarray,
    lows: np.ndarray,
    closes: np.ndarray,
    spreads: np.ndarray,
    stop_distance: float,
    reward_risk: float,
    max_hold: int,
    management: int,
) -> np.ndarray:
    results = np.empty(len(entries), dtype=np.float64)
    for trade in range(len(entries)):
        idx = int(entries[trade])
        direction = int(directions[trade])
        if direction > 0:
            entry = opens[idx] + spreads[idx] + SLIPPAGE_PRICE
            stop = entry - stop_distance
            target = entry + reward_risk * stop_distance
        else:
            entry = opens[idx] - SLIPPAGE_PRICE
            stop = entry + stop_distance
            target = entry - reward_risk * stop_distance
        exit_price = entry
        pending_stop = stop
        end = min(len(opens), idx + max_hold)
        for bar in range(idx, end):
            spread = spreads[bar]
            if direction > 0:
                bar_high = highs[bar]
                bar_low = lows[bar]
                if bar_low <= stop and bar_high >= target:
                    exit_price = stop - SLIPPAGE_PRICE
                    break
                if bar_low <= stop:
                    exit_price = stop - SLIPPAGE_PRICE
                    break
                if bar_high >= target:
                    exit_price = target
                    break
                if management == 1 and bar_high >= entry + stop_distance:
                    pending_stop = max(pending_stop, entry)
                elif management == 2 and bar_high >= entry + 1.5 * stop_distance:
                    pending_stop = max(pending_stop, closes[bar] - stop_distance, entry)
                exit_price = closes[bar]
            else:
                ask_high = highs[bar] + spread
                ask_low = lows[bar] + spread
                ask_close = closes[bar] + spread
                if ask_high >= stop and ask_low <= target:
                    exit_price = stop + SLIPPAGE_PRICE
                    break
                if ask_high >= stop:
                    exit_price = stop + SLIPPAGE_PRICE
                    break
                if ask_low <= target:
                    exit_price = target
                    break
                if management == 1 and ask_low <= entry - stop_distance:
                    pending_stop = min(pending_stop, entry)
                elif management == 2 and ask_low <= entry - 1.5 * stop_distance:
                    pending_stop = min(pending_stop, ask_close + stop_distance, entry)
                exit_price = ask_close
            stop = pending_stop
        results[trade] = direction * (exit_price - entry) / stop_distance
    return results


def metrics(r_values: np.ndarray) -> dict:
    r = np.asarray(r_values, dtype=float)
    r = r[np.isfinite(r)]
    if len(r) == 0:
        return {
            "trades": 0,
            "wins": 0,
            "losses": 0,
            "win_rate_pct": 0.0,
            "profit_factor": 0.0,
            "mean_r": 0.0,
            "net_r": 0.0,
            "return_pct": 0.0,
            "max_drawdown_pct": 0.0,
            "final_balance": INITIAL_BALANCE,
        }
    gains = float(r[r > 0].sum())
    losses = float(-r[r < 0].sum())
    curve = INITIAL_BALANCE * np.cumprod(1.0 + RISK_FRACTION * r)
    full = np.concatenate(([INITIAL_BALANCE], curve))
    peaks = np.maximum.accumulate(full)
    drawdown = (peaks - full) / peaks
    return {
        "trades": int(len(r)),
        "wins": int((r > 0).sum()),
        "losses": int((r <= 0).sum()),
        "win_rate_pct": float((r > 0).mean() * 100.0),
        "profit_factor": float(gains / losses) if losses > 0 else (999.0 if gains > 0 else 0.0),
        "mean_r": float(r.mean()),
        "net_r": float(r.sum()),
        "return_pct": float((curve[-1] / INITIAL_BALANCE - 1.0) * 100.0),
        "max_drawdown_pct": float(drawdown.max() * 100.0),
        "final_balance": float(curve[-1]),
    }


def management_code(name: str) -> int:
    return {"none": 0, "breakeven_1R": 1, "trail_after_1.5R": 2}[name]


def arrays(minutes: pd.DataFrame) -> tuple[np.ndarray, ...]:
    return tuple(minutes[column].to_numpy(float) for column in ["open", "high", "low", "close", "spread_price"])


def score(train: dict, validation: dict) -> float:
    if train["trades"] < 120 or validation["trades"] < 50:
        return -999.0
    if train["profit_factor"] <= 1.0 or validation["profit_factor"] <= 1.0:
        return -500.0 + min(train["mean_r"], validation["mean_r"])
    edge = min(train["mean_r"], validation["mean_r"])
    pf_bonus = 0.03 * min(math.log(train["profit_factor"]), math.log(validation["profit_factor"]))
    dd_penalty = 0.002 * max(train["max_drawdown_pct"], validation["max_drawdown_pct"])
    return edge + pf_bonus - dd_penalty


def yearly_stability_score(year_stats: list[dict]) -> float:
    if any(item["trades"] < 30 for item in year_stats):
        return -999.0
    worst_mean = min(item["mean_r"] for item in year_stats)
    worst_pf = min(item["profit_factor"] for item in year_stats)
    worst_return = min(item["return_pct"] for item in year_stats)
    worst_dd = max(item["max_drawdown_pct"] for item in year_stats)
    if worst_pf <= 0.90 or worst_return <= -5.0:
        return -500.0 + worst_mean
    return worst_mean + 0.025 * math.log(max(worst_pf, 1e-9)) - 0.0015 * worst_dd


def optimize() -> None:
    RESULTS.mkdir(parents=True, exist_ok=True)
    minutes = load_minutes()
    bars = make_m15(minutes)
    opens, highs, lows, closes, spreads = arrays(minutes)
    event_cache: dict[tuple, pd.DataFrame] = {}
    rows: list[dict] = []
    signal_grid = itertools.product(
        ["16:00", "16:30", "17:00"],
        [1, 2, 4],
        [0.0, 10.0, 25.0, 50.0],
    )
    for close_text, lookback, min_body in signal_grid:
        events = build_events(minutes, bars, close_text, lookback, min_body)
        event_cache[(close_text, lookback, min_body)] = events
        if events.empty:
            continue
        years = pd.to_datetime(events["signal_time"], utc=True).dt.year.to_numpy()
        entries = events["entry_index"].to_numpy(np.int64)
        directions = events["direction"].to_numpy(np.int8)
        for stop_distance, reward_risk, max_hold, management in itertools.product(
            [25.0, 35.0, 50.0, 75.0, 100.0, 150.0],
            [1.0, 1.25, 1.5, 2.0, 2.5, 3.0],
            [90, 180, 360],
            ["none", "breakeven_1R", "trail_after_1.5R"],
        ):
            r = simulate_fast(
                entries,
                directions,
                opens,
                highs,
                lows,
                closes,
                spreads,
                stop_distance,
                reward_risk,
                max_hold,
                management_code(management),
            )
            train = metrics(r[(years >= 2022) & (years <= 2023)])
            validation = metrics(r[years == 2024])
            row = asdict(Params(close_text, lookback, min_body, stop_distance, reward_risk, max_hold, management))
            row.update({f"train_{key}": value for key, value in train.items()})
            row.update({f"validation_{key}": value for key, value in validation.items()})
            row["score"] = score(train, validation)
            rows.append(row)
    table = pd.DataFrame(rows).sort_values("score", ascending=False).reset_index(drop=True)
    table.to_csv(RESULTS / "training-screen.csv", index=False)
    eligible = table[
        (table["score"] > -100)
        & (table["train_return_pct"] > 0)
        & (table["validation_return_pct"] > 0)
        & (table["train_profit_factor"] >= 1.05)
        & (table["validation_profit_factor"] >= 1.05)
    ]
    if eligible.empty:
        selected = table.iloc[0]
        status = "NO CONFIGURATION PASSED THE ROBUSTNESS GATE; top-ranked setting retained only for holdout falsification"
    else:
        selected = eligible.iloc[0]
        status = "Passed training and 2024 validation gate"
    parameter_names = list(Params.__dataclass_fields__)
    params = {name: selected[name].item() if hasattr(selected[name], "item") else selected[name] for name in parameter_names}
    payload = {
        "status": status,
        "parameters": params,
        "training_2022_2023": {key.removeprefix("train_"): selected[key] for key in table.columns if key.startswith("train_")},
        "validation_2024": {key.removeprefix("validation_"): selected[key] for key in table.columns if key.startswith("validation_")},
        "holdout_locked": ["2025-01-01", "2026-08-07"],
        "execution": {
            "entry": "next available M1 bar after the selected Europe/London close",
            "spread": "recorded broker spread on each M1 bar",
            "slippage_price_each_market_fill": SLIPPAGE_PRICE,
            "same_bar_stop_target": "stop first",
            "risk_fraction": RISK_FRACTION,
        },
    }
    (RESULTS / "selected-training-config.json").write_text(json.dumps(payload, indent=2, default=float), encoding="utf-8")
    print(json.dumps(payload, indent=2, default=float))


def refine() -> None:
    """Select on 2022-2025 only; 2026 remains the confirmation slice."""
    RESULTS.mkdir(parents=True, exist_ok=True)
    minutes = load_minutes()
    bars = make_m15(minutes)
    opens, highs, lows, closes, spreads = arrays(minutes)
    rows: list[dict] = []
    for close_text, lookback, min_body in itertools.product(
        ["16:00", "16:30", "17:00"], [1, 2, 4], [0.0, 10.0, 25.0, 50.0]
    ):
        events = build_events(minutes, bars, close_text, lookback, min_body)
        if events.empty:
            continue
        years = pd.to_datetime(events["signal_time"], utc=True).dt.year.to_numpy()
        entries = events["entry_index"].to_numpy(np.int64)
        directions = events["direction"].to_numpy(np.int8)
        for stop_distance, reward_risk, max_hold, management in itertools.product(
            [25.0, 35.0, 50.0, 75.0, 100.0, 150.0],
            [1.0, 1.25, 1.5, 2.0, 2.5, 3.0],
            [90, 180, 360],
            ["none", "breakeven_1R", "trail_after_1.5R"],
        ):
            r = simulate_fast(
                entries, directions, opens, highs, lows, closes, spreads,
                stop_distance, reward_risk, max_hold, management_code(management),
            )
            stats = [metrics(r[years == year]) for year in [2022, 2023, 2024, 2025]]
            row = asdict(Params(close_text, lookback, min_body, stop_distance, reward_risk, max_hold, management))
            for year, stat in zip([2022, 2023, 2024, 2025], stats, strict=True):
                row.update({f"y{year}_{key}": value for key, value in stat.items()})
            row["score"] = yearly_stability_score(stats)
            rows.append(row)
    table = pd.DataFrame(rows).sort_values("score", ascending=False).reset_index(drop=True)
    table.to_csv(RESULTS / "walkforward-screen-2022-2025.csv", index=False)
    eligible = table[
        (table["score"] > -100)
        & (table[[f"y{year}_return_pct" for year in [2022, 2023, 2024, 2025]]] > 0).all(axis=1)
        & (table[[f"y{year}_profit_factor" for year in [2022, 2023, 2024, 2025]]] >= 1.02).all(axis=1)
    ]
    if eligible.empty:
        selected = table.iloc[0]
        status = "NO CONFIGURATION WAS PROFITABLE IN EACH OF 2022-2025; least-fragile setting retained only for 2026 confirmation"
    else:
        selected = eligible.iloc[0]
        status = "Passed positive-return and PF>=1.02 gate in every year 2022-2025"
    parameter_names = list(Params.__dataclass_fields__)
    params = {name: selected[name].item() if hasattr(selected[name], "item") else selected[name] for name in parameter_names}
    payload = {
        "status": status,
        "parameters": params,
        "development_years": {
            str(year): {key.removeprefix(f"y{year}_"): selected[key] for key in table.columns if key.startswith(f"y{year}_")}
            for year in [2022, 2023, 2024, 2025]
        },
        "confirmation_locked": ["2026-01-01", "2026-08-07"],
        "note": "The earlier selected configuration's 2026 result was already observed; this second selection uses no 2026 values but is confirmatory, not a pristine first holdout.",
    }
    (RESULTS / "selected-walkforward-config.json").write_text(json.dumps(payload, indent=2, default=float), encoding="utf-8")
    print(json.dumps(payload, indent=2, default=float))


def simulate_detailed(minutes: pd.DataFrame, events: pd.DataFrame, params: Params) -> pd.DataFrame:
    records: list[dict] = []
    for row in events.itertuples(index=False):
        idx = int(row.entry_index)
        direction = int(row.direction)
        first = minutes.iloc[idx]
        if direction > 0:
            entry = float(first.open + first.spread_price + SLIPPAGE_PRICE)
            stop = entry - params.stop_points
            target = entry + params.reward_risk * params.stop_points
        else:
            entry = float(first.open - SLIPPAGE_PRICE)
            stop = entry + params.stop_points
            target = entry - params.reward_risk * params.stop_points
        initial_stop = stop
        pending_stop = stop
        exit_price = entry
        exit_reason = "time"
        exit_idx = min(len(minutes) - 1, idx + params.max_hold_minutes - 1)
        for bar_idx in range(idx, min(len(minutes), idx + params.max_hold_minutes)):
            bar = minutes.iloc[bar_idx]
            if direction > 0:
                if bar.low <= stop and bar.high >= target:
                    exit_price, exit_reason = stop - SLIPPAGE_PRICE, "stop_same_bar"
                    exit_idx = bar_idx
                    break
                if bar.low <= stop:
                    exit_price, exit_reason = stop - SLIPPAGE_PRICE, "stop"
                    exit_idx = bar_idx
                    break
                if bar.high >= target:
                    exit_price, exit_reason = target, "target"
                    exit_idx = bar_idx
                    break
                if params.management == "breakeven_1R" and bar.high >= entry + params.stop_points:
                    pending_stop = max(pending_stop, entry)
                elif params.management == "trail_after_1.5R" and bar.high >= entry + 1.5 * params.stop_points:
                    pending_stop = max(pending_stop, float(bar.close) - params.stop_points, entry)
                exit_price = float(bar.close)
            else:
                ask_high = float(bar.high + bar.spread_price)
                ask_low = float(bar.low + bar.spread_price)
                ask_close = float(bar.close + bar.spread_price)
                if ask_high >= stop and ask_low <= target:
                    exit_price, exit_reason = stop + SLIPPAGE_PRICE, "stop_same_bar"
                    exit_idx = bar_idx
                    break
                if ask_high >= stop:
                    exit_price, exit_reason = stop + SLIPPAGE_PRICE, "stop"
                    exit_idx = bar_idx
                    break
                if ask_low <= target:
                    exit_price, exit_reason = target, "target"
                    exit_idx = bar_idx
                    break
                if params.management == "breakeven_1R" and ask_low <= entry - params.stop_points:
                    pending_stop = min(pending_stop, entry)
                elif params.management == "trail_after_1.5R" and ask_low <= entry - 1.5 * params.stop_points:
                    pending_stop = min(pending_stop, ask_close + params.stop_points, entry)
                exit_price = ask_close
            stop = pending_stop
        result_r = direction * (exit_price - entry) / params.stop_points
        records.append(
            {
                "signal_time": row.signal_time,
                "entry_time": minutes.index[idx],
                "exit_time": minutes.index[exit_idx],
                "direction": "long" if direction > 0 else "short",
                "net_body_points": row.net_body_points,
                "entry": entry,
                "initial_stop": initial_stop,
                "target": target,
                "exit": exit_price,
                "exit_reason": exit_reason,
                "result_r": result_r,
            }
        )
    return pd.DataFrame(records)


def final() -> None:
    selection = json.loads((RESULTS / "selected-training-config.json").read_text(encoding="utf-8"))
    params = Params(**selection["parameters"])
    minutes = load_minutes()
    bars = make_m15(minutes)
    events = build_events(minutes, bars, params.london_close, params.candle_lookback, params.min_net_body_points)
    trades = simulate_detailed(minutes, events, params)
    trades["year"] = pd.to_datetime(trades["signal_time"], utc=True).dt.year
    periods = {
        "training_2022_2023": trades[trades["year"].between(2022, 2023)],
        "validation_2024": trades[trades["year"] == 2024],
        "holdout_2025_2026": trades[trades["year"] >= 2025],
        "full_2022_2026": trades,
    }
    result = {name: metrics(frame["result_r"].to_numpy(float)) for name, frame in periods.items()}
    yearly = []
    for year, frame in trades.groupby("year"):
        yearly.append({"year": int(year), **metrics(frame["result_r"].to_numpy(float))})
    trades.to_csv(RESULTS / "selected-trades.csv", index=False)
    pd.DataFrame(yearly).to_csv(RESULTS / "yearly-results.csv", index=False)
    payload = {"selection": selection, "parameters": asdict(params), "periods": result, "yearly": yearly}
    (RESULTS / "final-results.json").write_text(json.dumps(payload, indent=2, default=float), encoding="utf-8")

    fig, axes = plt.subplots(2, 1, figsize=(12, 9), sharex=False)
    for ax, (label, frame) in zip(axes, [("Full 2022-2026", trades), ("Untouched 2025-2026", periods["holdout_2025_2026"])], strict=True):
        r = frame["result_r"].to_numpy(float)
        equity = INITIAL_BALANCE * np.cumprod(1.0 + RISK_FRACTION * r) if len(r) else np.array([INITIAL_BALANCE])
        times = pd.to_datetime(frame["exit_time"], utc=True) if len(frame) else pd.DatetimeIndex([pd.Timestamp("2025-01-01", tz="UTC")])
        stat = metrics(r)
        ax.step(times, equity, where="post", linewidth=1.8)
        ax.axhline(INITIAL_BALANCE, color="gray", linestyle="--", linewidth=1)
        ax.set_title(
            f"{label}: {stat['return_pct']:+.2f}% | PF {stat['profit_factor']:.2f} | "
            f"WR {stat['win_rate_pct']:.2f}% | DD {stat['max_drawdown_pct']:.2f}% | {stat['trades']} trades"
        )
        ax.set_ylabel("Closed equity (USD)")
        ax.grid(alpha=0.25)
    axes[-1].set_xlabel("Date (UTC)")
    fig.suptitle("US100 London-close M15 reversal — recorded spread, 1% risk")
    fig.tight_layout()
    fig.savefig(RESULTS / "equity-curve.png", dpi=180)
    plt.close(fig)
    print(json.dumps(payload, indent=2, default=float))


def confirm() -> None:
    selection = json.loads((RESULTS / "selected-walkforward-config.json").read_text(encoding="utf-8"))
    params = Params(**selection["parameters"])
    minutes = load_minutes()
    bars = make_m15(minutes)
    events = build_events(minutes, bars, params.london_close, params.candle_lookback, params.min_net_body_points)
    trades = simulate_detailed(minutes, events, params)
    trades["year"] = pd.to_datetime(trades["signal_time"], utc=True).dt.year
    periods = {
        "development_2022_2025": trades[trades["year"].between(2022, 2025)],
        "confirmation_2026": trades[trades["year"] == 2026],
        "full_2022_2026": trades,
    }
    result = {name: metrics(frame["result_r"].to_numpy(float)) for name, frame in periods.items()}
    payload = {"selection": selection, "parameters": asdict(params), "periods": result}
    trades.to_csv(RESULTS / "walkforward-selected-trades.csv", index=False)
    (RESULTS / "walkforward-confirmation.json").write_text(json.dumps(payload, indent=2, default=float), encoding="utf-8")

    fig, ax = plt.subplots(figsize=(12, 6.5))
    r = trades["result_r"].to_numpy(float)
    equity = INITIAL_BALANCE * np.cumprod(1.0 + RISK_FRACTION * r)
    ax.step(pd.to_datetime(trades["exit_time"], utc=True), equity, where="post", linewidth=1.8)
    ax.axvline(pd.Timestamp("2026-01-01", tz="UTC"), color="red", linestyle="--", label="2026 confirmation begins")
    ax.axhline(INITIAL_BALANCE, color="gray", linestyle="--", linewidth=1)
    dev = result["development_2022_2025"]
    conf = result["confirmation_2026"]
    ax.set_title(
        f"Walk-forward selection: development {dev['return_pct']:+.2f}% PF {dev['profit_factor']:.2f}; "
        f"2026 confirmation {conf['return_pct']:+.2f}% PF {conf['profit_factor']:.2f}"
    )
    ax.set_ylabel("Closed equity (USD)")
    ax.set_xlabel("Date (UTC)")
    ax.grid(alpha=0.25)
    ax.legend()
    fig.tight_layout()
    fig.savefig(RESULTS / "walkforward-equity.png", dpi=180)
    plt.close(fig)
    print(json.dumps(payload, indent=2, default=float))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--stage", required=True, choices=["optimize", "final", "refine", "confirm"])
    args = parser.parse_args()
    if args.stage == "optimize":
        optimize()
    elif args.stage == "final":
        final()
    elif args.stage == "refine":
        refine()
    else:
        confirm()


if __name__ == "__main__":
    main()
