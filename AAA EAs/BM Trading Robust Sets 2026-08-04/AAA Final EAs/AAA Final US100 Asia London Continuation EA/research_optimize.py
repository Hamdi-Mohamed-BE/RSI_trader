from __future__ import annotations

import argparse
import hashlib
import json
import math
from dataclasses import asdict, dataclass
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path
from typing import Iterable
from zoneinfo import ZoneInfo

import matplotlib.pyplot as plt
import MetaTrader5 as mt5
import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parent
RESEARCH = ROOT / "Research"
DATA = RESEARCH / "data"
REPORTS = RESEARCH / "reports"
TERMINAL = Path(
    r"C:\Users\hama101\Desktop\geek\ai trader\AAA EAs\BM Trading Robust Sets 2026-08-04"
    r"\_Backtests\MT5-Isolated-20260805\terminal64.exe"
)
SYMBOL = "USTEC"
START = datetime(2019, 7, 16, tzinfo=timezone.utc)
END = datetime(2026, 8, 10, tzinfo=timezone.utc)
POINT = 0.01
INITIAL_BALANCE = 10_000.0
RISK_FRACTION = 0.01
NY = ZoneInfo("America/New_York")


@dataclass(frozen=True)
class DayContext:
    session_date: date
    direction: int
    asia_open: float
    asia_high: float
    asia_low: float
    london_open: float
    ny_open: float
    or_high: float
    or_low: float
    or_range: float
    trend_points: float
    london_agrees: bool
    proximity_points: float
    minutes: np.ndarray
    bid_open: np.ndarray
    bid_high: np.ndarray
    bid_low: np.ndarray
    bid_close: np.ndarray
    spread_points: np.ndarray
    timestamps: np.ndarray


@dataclass(frozen=True)
class SignalParam:
    proximity_threshold: float
    minimum_trend: float
    require_london_agreement: bool
    direction_mode: str
    maximum_opening_range: float


@dataclass(frozen=True)
class OutcomeParam:
    stop_range_multiple: float
    minimum_stop_points: float
    reward_risk: float
    trailing_mode: str
    exit_minute: int


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def ensure_dirs() -> None:
    DATA.mkdir(parents=True, exist_ok=True)
    REPORTS.mkdir(parents=True, exist_ok=True)


def cache_path(year: int) -> Path:
    return DATA / f"Exness-{SYMBOL}-M1-{year}.csv.gz"


def download_history(force: bool = False) -> tuple[pd.DataFrame, dict]:
    ensure_dirs()
    if not mt5.initialize(path=str(TERMINAL), timeout=60_000):
        raise RuntimeError(f"MT5 initialization failed: {mt5.last_error()}")
    try:
        if not mt5.symbol_select(SYMBOL, True):
            raise RuntimeError(f"Cannot select {SYMBOL}: {mt5.last_error()}")
        info = mt5.symbol_info(SYMBOL)
        if info is None:
            raise RuntimeError(f"No symbol specification for {SYMBOL}")
        specification = {
            "symbol": SYMBOL,
            "server": mt5.account_info().server if mt5.account_info() else "unknown",
            "digits": int(info.digits),
            "point": float(info.point),
            "trade_tick_size": float(info.trade_tick_size),
            "trade_tick_value": float(info.trade_tick_value),
            "contract_size": float(info.trade_contract_size),
            "volume_min": float(info.volume_min),
            "volume_step": float(info.volume_step),
        }
        if not math.isclose(specification["trade_tick_size"], POINT, abs_tol=1e-12):
            raise RuntimeError(f"Unexpected {SYMBOL} tick size: {specification['trade_tick_size']}")

        manifest_files: list[dict] = []
        frames: list[pd.DataFrame] = []
        for year in range(START.year, END.year + 1):
            path = cache_path(year)
            period_start = max(START, datetime(year, 1, 1, tzinfo=timezone.utc))
            period_end = min(END, datetime(year + 1, 1, 1, tzinfo=timezone.utc))
            if force or not path.exists():
                print(f"Downloading {SYMBOL} M1 {period_start.date()} to {period_end.date()}...", flush=True)
                rates = mt5.copy_rates_range(SYMBOL, mt5.TIMEFRAME_M1, period_start, period_end)
                if rates is None or len(rates) == 0:
                    raise RuntimeError(f"No M1 rates for {year}: {mt5.last_error()}")
                frame = pd.DataFrame(rates)
                frame["time"] = pd.to_datetime(frame["time"], unit="s", utc=True)
                frame.to_csv(path, index=False, compression={"method": "gzip", "compresslevel": 6})
            frame = pd.read_csv(path, compression="gzip", parse_dates=["time"])
            frame["time"] = pd.to_datetime(frame["time"], utc=True)
            frames.append(frame)
            manifest_files.append(
                {
                    "file": path.name,
                    "rows": int(len(frame)),
                    "first_utc": frame["time"].iloc[0].isoformat(),
                    "last_utc": frame["time"].iloc[-1].isoformat(),
                    "bytes": path.stat().st_size,
                    "sha256": sha256_file(path),
                }
            )
        combined = pd.concat(frames, ignore_index=True)
        before = len(combined)
        combined = combined.drop_duplicates(subset=["time"], keep="last").sort_values("time")
        combined = combined[(combined["time"] >= START) & (combined["time"] < END)].reset_index(drop=True)
        positive_spreads = combined.loc[combined["spread"] > 0, "spread"]
        median_spread_points = float(positive_spreads.median()) if len(positive_spreads) else 0.0
        manifest = {
            "created_utc": datetime.now(timezone.utc).isoformat(),
            "terminal": str(TERMINAL),
            "specification": specification,
            "requested_start_utc": START.isoformat(),
            "requested_end_utc_exclusive": END.isoformat(),
            "rows_before_deduplication": before,
            "rows": int(len(combined)),
            "duplicate_rows_removed": int(before - len(combined)),
            "median_positive_spread_points": median_spread_points,
            "median_positive_spread_index_points": median_spread_points * POINT,
            "zero_spread_rows": int((combined["spread"] <= 0).sum()),
            "files": manifest_files,
        }
        (DATA / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        return combined, manifest
    finally:
        mt5.shutdown()


def ny_timestamp(day: date, hour: int, minute: int = 0) -> pd.Timestamp:
    return pd.Timestamp(datetime.combine(day, time(hour, minute)), tz=NY).tz_convert("UTC")


def index_slice(frame: pd.DataFrame, start: pd.Timestamp, end: pd.Timestamp) -> pd.DataFrame:
    left = int(frame.index.searchsorted(start, side="left"))
    right = int(frame.index.searchsorted(end, side="left"))
    return frame.iloc[left:right]


def build_day_contexts(raw: pd.DataFrame, fallback_spread_points: float) -> tuple[list[DayContext], dict]:
    frame = raw.copy()
    frame = frame.set_index("time").sort_index()
    local_first = frame.index[0].tz_convert(NY).date()
    local_last = frame.index[-1].tz_convert(NY).date()
    contexts: list[DayContext] = []
    skipped: dict[str, int] = {}

    def skip(reason: str) -> None:
        skipped[reason] = skipped.get(reason, 0) + 1

    for stamp in pd.date_range(local_first + timedelta(days=1), local_last, freq="D"):
        session_date = stamp.date()
        if session_date.weekday() >= 5:
            continue
        asia_start = ny_timestamp(session_date - timedelta(days=1), 18, 0)
        asia_end = ny_timestamp(session_date, 3, 0)
        london_start = asia_end
        london_end = ny_timestamp(session_date, 9, 30)
        or_start = london_end
        or_end = ny_timestamp(session_date, 9, 45)
        trade_end = ny_timestamp(session_date, 16, 0)
        asia = index_slice(frame, asia_start, asia_end)
        london = index_slice(frame, london_start, london_end)
        opening_range = index_slice(frame, or_start, or_end)
        trade = index_slice(frame, or_end, trade_end)
        if len(asia) < 180:
            skip("insufficient_asia_bars")
            continue
        if len(london) < 180:
            skip("insufficient_london_bars")
            continue
        if len(opening_range) < 12:
            skip("incomplete_new_york_opening_range")
            continue
        if len(trade) < 60:
            skip("insufficient_trade_path")
            continue

        asia_open = float(asia.iloc[0]["open"])
        asia_high = float(asia["high"].max())
        asia_low = float(asia["low"].min())
        london_open = float(london.iloc[0]["open"])
        ny_open = float(opening_range.iloc[0]["open"])
        or_high = float(opening_range["high"].max())
        or_low = float(opening_range["low"].min())
        trend = ny_open - asia_open
        if math.isclose(trend, 0.0, abs_tol=1e-12):
            skip("flat_asia_to_new_york")
            continue
        direction = 1 if trend > 0 else -1
        london_move = ny_open - london_open
        london_agrees = (london_move > 0 and direction > 0) or (london_move < 0 and direction < 0)
        proximity = abs(or_high - asia_high) if direction > 0 else abs(or_low - asia_low)
        local_index = trade.index.tz_convert(NY)
        minutes = (local_index.hour * 60 + local_index.minute).to_numpy(dtype=np.int16)
        spreads = trade["spread"].to_numpy(dtype=float)
        spreads = np.where(spreads > 0, spreads, fallback_spread_points)
        contexts.append(
            DayContext(
                session_date=session_date,
                direction=direction,
                asia_open=asia_open,
                asia_high=asia_high,
                asia_low=asia_low,
                london_open=london_open,
                ny_open=ny_open,
                or_high=or_high,
                or_low=or_low,
                or_range=max(or_high - or_low, POINT),
                trend_points=abs(trend),
                london_agrees=london_agrees,
                proximity_points=proximity,
                minutes=minutes,
                bid_open=trade["open"].to_numpy(dtype=float),
                bid_high=trade["high"].to_numpy(dtype=float),
                bid_low=trade["low"].to_numpy(dtype=float),
                bid_close=trade["close"].to_numpy(dtype=float),
                spread_points=spreads,
                timestamps=trade.index.to_numpy(),
            )
        )
    quality = {
        "candidate_weekdays": int(sum(1 for d in pd.date_range(local_first + timedelta(days=1), local_last, freq="D") if d.weekday() < 5)),
        "valid_sessions": len(contexts),
        "skipped": skipped,
        "first_session": contexts[0].session_date.isoformat() if contexts else None,
        "last_session": contexts[-1].session_date.isoformat() if contexts else None,
    }
    return contexts, quality


def trailing_start_r(mode: str) -> float:
    return {"none": math.inf, "be_1r": 1.0, "m15_1r": 1.0, "m15_1_5r": 1.5, "m15_2r": 2.0}[mode]


def simulate_day(day: DayContext, param: OutcomeParam, detail: bool = False) -> float | dict:
    direction = day.direction
    stop_distance = max(day.or_range * param.stop_range_multiple, param.minimum_stop_points)
    opening_spread = day.spread_points[0] * POINT
    entry = float(day.bid_open[0] + opening_spread) if direction > 0 else float(day.bid_open[0])
    initial_stop = entry - stop_distance if direction > 0 else entry + stop_distance
    stop = initial_stop
    target = entry + param.reward_risk * stop_distance if direction > 0 else entry - param.reward_risk * stop_distance
    activated = False
    mode = param.trailing_mode
    start_r = trailing_start_r(mode)
    bucket_high = -math.inf
    bucket_low = math.inf
    exit_price = float(day.bid_close[-1]) if direction > 0 else float(day.bid_close[-1] + day.spread_points[-1] * POINT)
    exit_reason = "time"
    exit_timestamp = day.timestamps[-1]

    for i in range(len(day.minutes)):
        if int(day.minutes[i]) >= param.exit_minute:
            break
        spread = day.spread_points[i] * POINT
        if direction > 0:
            bar_open = float(day.bid_open[i])
            bar_high = float(day.bid_high[i])
            bar_low = float(day.bid_low[i])
            bar_close = float(day.bid_close[i])
        else:
            bar_open = float(day.bid_open[i] + spread)
            bar_high = float(day.bid_high[i] + spread)
            bar_low = float(day.bid_low[i] + spread)
            bar_close = float(day.bid_close[i] + spread)

        bucket_high = max(bucket_high, bar_high)
        bucket_low = min(bucket_low, bar_low)
        stop_hit = bar_low <= stop if direction > 0 else bar_high >= stop
        target_hit = bar_high >= target if direction > 0 else bar_low <= target

        # M1 OHLC does not reveal the order when both levels occur. Stop-first is conservative.
        if stop_hit:
            if direction > 0:
                exit_price = min(stop, bar_open) if bar_open < stop else stop
            else:
                exit_price = max(stop, bar_open) if bar_open > stop else stop
            exit_reason = "stop"
            exit_timestamp = day.timestamps[i]
            break
        if target_hit:
            exit_price = target
            exit_reason = "target"
            exit_timestamp = day.timestamps[i]
            break

        favorable = (bar_high - entry) / stop_distance if direction > 0 else (entry - bar_low) / stop_distance
        if favorable >= start_r:
            activated = True

        if activated and mode == "be_1r":
            stop = max(stop, entry) if direction > 0 else min(stop, entry)

        closes_m15 = int(day.minutes[i]) % 15 == 14
        if closes_m15:
            if activated and mode.startswith("m15_"):
                candidate = bucket_low if direction > 0 else bucket_high
                if direction > 0 and candidate < bar_close:
                    stop = max(stop, candidate)
                elif direction < 0 and candidate > bar_close:
                    stop = min(stop, candidate)
            bucket_high = -math.inf
            bucket_low = math.inf
        exit_price = bar_close
        exit_timestamp = day.timestamps[i]

    pnl_points = (exit_price - entry) * direction
    result_r = pnl_points / stop_distance
    if not detail:
        return float(result_r)
    return {
        "date": day.session_date.isoformat(),
        "side": "LONG" if direction > 0 else "SHORT",
        "asia_open": day.asia_open,
        "asia_high": day.asia_high,
        "asia_low": day.asia_low,
        "london_open": day.london_open,
        "ny_open": day.ny_open,
        "or_high": day.or_high,
        "or_low": day.or_low,
        "or_range": day.or_range,
        "trend_points": day.trend_points,
        "london_agrees": day.london_agrees,
        "proximity_points": day.proximity_points,
        "entry": entry,
        "initial_stop": initial_stop,
        "target": target,
        "exit": exit_price,
        "exit_time_utc": pd.Timestamp(exit_timestamp).isoformat(),
        "exit_reason": exit_reason,
        "result_r": float(result_r),
    }


def signal_params() -> list[SignalParam]:
    return [
        SignalParam(threshold, trend, agreement, direction, maximum_range)
        for threshold in (20.0, 40.0, 60.0, 100.0, 150.0, 200.0)
        for trend in (0.0, 50.0, 100.0)
        for agreement in (False, True)
        for direction in ("both", "long", "short")
        for maximum_range in (100.0, 200.0, 400.0)
    ]


def outcome_params() -> list[OutcomeParam]:
    return [
        OutcomeParam(stop_mult, minimum_stop, reward_risk, trailing, exit_minute)
        for stop_mult in (0.75, 1.0, 1.25)
        for minimum_stop in (20.0, 40.0)
        for reward_risk in (1.0, 1.5, 2.0, 3.0, 4.0)
        for trailing in ("none", "be_1r", "m15_1r", "m15_1_5r", "m15_2r")
        for exit_minute in (12 * 60, 14 * 60, 16 * 60)
    ]


def signal_mask(contexts: list[DayContext], param: SignalParam) -> np.ndarray:
    mask = np.ones(len(contexts), dtype=bool)
    proximity = np.fromiter((d.proximity_points for d in contexts), dtype=float)
    trend = np.fromiter((d.trend_points for d in contexts), dtype=float)
    agreement = np.fromiter((d.london_agrees for d in contexts), dtype=bool)
    directions = np.fromiter((d.direction for d in contexts), dtype=np.int8)
    opening_ranges = np.fromiter((d.or_range for d in contexts), dtype=float)
    mask &= proximity <= param.proximity_threshold
    mask &= trend >= param.minimum_trend
    mask &= opening_ranges <= param.maximum_opening_range
    if param.require_london_agreement:
        mask &= agreement
    if param.direction_mode == "long":
        mask &= directions > 0
    elif param.direction_mode == "short":
        mask &= directions < 0
    return mask


def vector_metrics(values: np.ndarray) -> dict[str, np.ndarray]:
    count = values.shape[0]
    if count == 0:
        zeros = np.zeros(values.shape[1], dtype=float)
        return {"count": zeros, "mean": zeros, "std": zeros, "lcb": zeros, "pf": zeros, "win_rate": zeros}
    mean = values.mean(axis=0)
    std = values.std(axis=0, ddof=1) if count > 1 else np.zeros(values.shape[1])
    positive = np.where(values > 0, values, 0.0).sum(axis=0)
    negative = -np.where(values < 0, values, 0.0).sum(axis=0)
    pf = np.divide(positive, negative, out=np.full_like(positive, np.inf), where=negative > 0)
    lcb = mean - 1.2816 * std / math.sqrt(max(count, 1))
    return {
        "count": np.full(values.shape[1], count, dtype=float),
        "mean": mean,
        "std": std,
        "lcb": lcb,
        "pf": pf,
        "win_rate": (values > 0).mean(axis=0) * 100.0,
    }


def scalar_metrics(values: Iterable[float], risk_fraction: float = RISK_FRACTION) -> dict:
    r = np.asarray(list(values), dtype=float)
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
            "max_closed_balance_dd_pct": 0.0,
            "final_balance": INITIAL_BALANCE,
        }
    gross_profit = float(r[r > 0].sum())
    gross_loss = float(-r[r < 0].sum())
    multipliers = np.maximum(1.0 + risk_fraction * r, 0.000001)
    equity = INITIAL_BALANCE * np.cumprod(multipliers)
    equity_with_start = np.concatenate(([INITIAL_BALANCE], equity))
    peaks = np.maximum.accumulate(equity_with_start)
    drawdown = (peaks - equity_with_start) / peaks
    return {
        "trades": int(len(r)),
        "wins": int((r > 0).sum()),
        "losses": int((r <= 0).sum()),
        "win_rate_pct": float((r > 0).mean() * 100.0),
        "profit_factor": float(gross_profit / gross_loss) if gross_loss > 0 else float("inf"),
        "mean_r": float(r.mean()),
        "median_r": float(np.median(r)),
        "net_r": float(r.sum()),
        "gross_profit_r": gross_profit,
        "gross_loss_r": -gross_loss,
        "return_pct": float((equity[-1] / INITIAL_BALANCE - 1.0) * 100.0),
        "max_closed_balance_dd_pct": float(drawdown.max() * 100.0),
        "final_balance": float(equity[-1]),
        "largest_win_r": float(r.max()),
        "largest_loss_r": float(r.min()),
        "average_win_r": float(r[r > 0].mean()) if (r > 0).any() else 0.0,
        "average_loss_r": float(r[r <= 0].mean()) if (r <= 0).any() else 0.0,
    }


def optimize(contexts: list[DayContext]) -> tuple[SignalParam, OutcomeParam, pd.DataFrame, np.ndarray]:
    outcomes = outcome_params()
    print(f"Precomputing {len(contexts):,} sessions x {len(outcomes):,} exits...", flush=True)
    matrix = np.empty((len(contexts), len(outcomes)), dtype=np.float32)
    for row, day in enumerate(contexts):
        for col, param in enumerate(outcomes):
            matrix[row, col] = simulate_day(day, param)
        if (row + 1) % 250 == 0:
            print(f"  simulated {row + 1:,}/{len(contexts):,} sessions", flush=True)

    dates = np.asarray([np.datetime64(d.session_date) for d in contexts])
    train_dates = dates < np.datetime64("2024-01-01")
    validation_dates = (dates >= np.datetime64("2024-01-01")) & (dates < np.datetime64("2025-01-01"))
    candidates: list[dict] = []
    for signal in signal_params():
        base = signal_mask(contexts, signal)
        train_mask = base & train_dates
        validation_mask = base & validation_dates
        if int(train_mask.sum()) < 60 or int(validation_mask.sum()) < 15:
            continue
        train = vector_metrics(matrix[train_mask])
        validation = vector_metrics(matrix[validation_mask])
        score = np.minimum(train["lcb"], validation["lcb"])
        qualified = (
            (train["pf"] >= 1.05)
            & (validation["pf"] >= 1.05)
            & (train["mean"] > 0)
            & (validation["mean"] > 0)
        )
        for col in np.flatnonzero(qualified):
            candidates.append(
                {
                    **asdict(signal),
                    **asdict(outcomes[col]),
                    "outcome_index": int(col),
                    "robust_lcb_score": float(score[col]),
                    "train_trades": int(train["count"][col]),
                    "train_pf": float(train["pf"][col]),
                    "train_mean_r": float(train["mean"][col]),
                    "train_win_rate": float(train["win_rate"][col]),
                    "validation_trades": int(validation["count"][col]),
                    "validation_pf": float(validation["pf"][col]),
                    "validation_mean_r": float(validation["mean"][col]),
                    "validation_win_rate": float(validation["win_rate"][col]),
                }
            )
    if not candidates:
        raise RuntimeError("No configuration passed the minimum train/validation criteria.")
    table = pd.DataFrame(candidates).sort_values(
        ["robust_lcb_score", "validation_pf", "train_pf"], ascending=False
    )

    # Penalize unstable candidates by inspecting every pre-holdout calendar year.
    audited: list[dict] = []
    for _, row in table.head(500).iterrows():
        signal = SignalParam(
            row.proximity_threshold,
            row.minimum_trend,
            bool(row.require_london_agreement),
            row.direction_mode,
            row.maximum_opening_range,
        )
        col = int(row.outcome_index)
        mask = signal_mask(contexts, signal)
        yearly_returns: dict[str, float] = {}
        positive_years = 0
        tested_years = 0
        for year in range(2020, 2025):
            year_mask = mask & (dates >= np.datetime64(f"{year}-01-01")) & (dates < np.datetime64(f"{year + 1}-01-01"))
            metrics = scalar_metrics(matrix[year_mask, col])
            yearly_returns[str(year)] = metrics["return_pct"]
            if metrics["trades"] >= 8:
                tested_years += 1
                positive_years += int(metrics["return_pct"] > 0)
        combined_mask = mask & (dates < np.datetime64("2025-01-01"))
        combined = scalar_metrics(matrix[combined_mask, col])
        stability_score = float(row.robust_lcb_score) + 0.01 * positive_years - 0.002 * combined["max_closed_balance_dd_pct"]
        audited.append(
            {
                **row.to_dict(),
                "positive_preholdout_years": positive_years,
                "tested_preholdout_years": tested_years,
                "preholdout_return_pct": combined["return_pct"],
                "preholdout_pf": combined["profit_factor"],
                "preholdout_dd_pct": combined["max_closed_balance_dd_pct"],
                "stability_score": stability_score,
                "yearly_returns_json": json.dumps(yearly_returns, sort_keys=True),
            }
        )
    audited_table = pd.DataFrame(audited)
    stable = audited_table[
        (audited_table["tested_preholdout_years"] >= 5)
        & (audited_table["positive_preholdout_years"] >= 4)
        & (audited_table["preholdout_pf"] >= 1.10)
        & (audited_table["preholdout_dd_pct"] <= 15.0)
    ]
    if stable.empty:
        stable = audited_table
    stable = stable.sort_values(["stability_score", "robust_lcb_score"], ascending=False)
    winner = stable.iloc[0]
    selected_signal = SignalParam(
        float(winner.proximity_threshold),
        float(winner.minimum_trend),
        bool(winner.require_london_agreement),
        str(winner.direction_mode),
        float(winner.maximum_opening_range),
    )
    selected_outcome = OutcomeParam(
        float(winner.stop_range_multiple),
        float(winner.minimum_stop_points),
        float(winner.reward_risk),
        str(winner.trailing_mode),
        int(winner.exit_minute),
    )
    return selected_signal, selected_outcome, stable, matrix


def selected_trades(
    contexts: list[DayContext], signal: SignalParam, outcome: OutcomeParam
) -> pd.DataFrame:
    mask = signal_mask(contexts, signal)
    rows = [simulate_day(day, outcome, detail=True) for day, include in zip(contexts, mask) if include]
    return pd.DataFrame(rows)


def stress_metrics(trades: pd.DataFrame, slippage_each_side_points: float) -> dict:
    if trades.empty:
        return scalar_metrics([])
    stop_distance = (trades["entry"] - trades["initial_stop"]).abs().to_numpy()
    stressed_r = trades["result_r"].to_numpy() - (2.0 * slippage_each_side_points / stop_distance)
    return scalar_metrics(stressed_r)


def plot_equity(trades: pd.DataFrame, destination: Path) -> None:
    r = trades["result_r"].to_numpy(dtype=float)
    equity = INITIAL_BALANCE * np.cumprod(np.maximum(1.0 + RISK_FRACTION * r, 0.000001))
    x = pd.to_datetime(trades["date"])
    plt.figure(figsize=(12, 5.5))
    plt.plot(x, equity, color="#1677ff", linewidth=1.8, label="Closed balance")
    plt.axvline(pd.Timestamp("2024-01-01"), color="#888888", linestyle="--", linewidth=1, label="Validation starts")
    plt.axvline(pd.Timestamp("2025-01-01"), color="#d65f5f", linestyle="--", linewidth=1, label="Untouched holdout starts")
    plt.title("US100 Asia–London continuation: selected configuration")
    plt.xlabel("Session date")
    plt.ylabel("Balance (USD), 1% risk per trade")
    plt.grid(alpha=0.25)
    plt.legend()
    plt.tight_layout()
    plt.savefig(destination, dpi=170)
    plt.close()


def json_safe(value):
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating,)):
        return float(value)
    if isinstance(value, float) and not math.isfinite(value):
        return "Infinity" if value > 0 else "-Infinity"
    if isinstance(value, dict):
        return {key: json_safe(item) for key, item in value.items()}
    if isinstance(value, list):
        return [json_safe(item) for item in value]
    return value


def write_report(
    manifest: dict,
    quality: dict,
    signal: SignalParam,
    outcome: OutcomeParam,
    top: pd.DataFrame,
    trades: pd.DataFrame,
) -> dict:
    dates = pd.to_datetime(trades["date"])
    periods = {
        "training_2019_2023": dates < pd.Timestamp("2024-01-01"),
        "validation_2024": (dates >= pd.Timestamp("2024-01-01")) & (dates < pd.Timestamp("2025-01-01")),
        "holdout_2025_2026": dates >= pd.Timestamp("2025-01-01"),
        "full_2019_2026": np.ones(len(trades), dtype=bool),
    }
    metrics = {name: scalar_metrics(trades.loc[mask, "result_r"]) for name, mask in periods.items()}
    stress = {
        f"{points:g}_points_each_side": stress_metrics(trades, points)
        for points in (0.5, 1.0, 2.0)
    }
    side_metrics = {
        side.lower(): scalar_metrics(group["result_r"])
        for side, group in trades.groupby("side")
    }
    yearly = {
        str(year): scalar_metrics(group["result_r"])
        for year, group in trades.groupby(dates.dt.year)
    }
    result = {
        "methodology": {
            "symbol": SYMBOL,
            "broker": manifest["specification"]["server"],
            "history_start": manifest["requested_start_utc"],
            "history_end_exclusive": manifest["requested_end_utc_exclusive"],
            "data_model": "Broker M1 bid OHLC plus recorded M1 spread; stop-first when SL and TP share one M1 bar",
            "asia_session_new_york": "18:00 previous day to 03:00",
            "london_session_new_york": "03:00 to 09:30",
            "opening_range_new_york": "09:30 to 09:45",
            "entry": "Market at 09:45 New York in the Asia-open to New-York-open trend direction",
            "risk_fraction": RISK_FRACTION,
            "initial_balance": INITIAL_BALANCE,
            "selection": "2019-2023 training, 2024 validation, 2025-2026 untouched holdout",
        },
        "pip_tick_definition": {
            "broker_tick_size_index_points": manifest["specification"]["trade_tick_size"],
            "two_thousand_broker_ticks_index_points": 2000 * manifest["specification"]["trade_tick_size"],
            "original_threshold_used_index_points": 20.0,
        },
        "quality": quality,
        "selected_signal": asdict(signal),
        "selected_outcome": asdict(outcome),
        "metrics": metrics,
        "side_metrics": side_metrics,
        "yearly_metrics": yearly,
        "slippage_stress_full_period": stress,
        "top_configuration_count": int(len(top)),
    }
    (REPORTS / "results.json").write_text(json.dumps(json_safe(result), indent=2), encoding="utf-8")
    top.head(200).to_csv(REPORTS / "top-configurations.csv", index=False)
    trades.to_csv(REPORTS / "selected-trades.csv", index=False)
    plot_equity(trades, REPORTS / "equity-curve.png")

    selected = metrics["full_2019_2026"]
    holdout = metrics["holdout_2025_2026"]
    lines = [
        "# US100 Asia–London Continuation Research Report",
        "",
        "## Locked interpretation",
        "",
        "- Asia: 18:00 previous day–03:00 New York.",
        "- London: 03:00–09:30 New York.",
        "- First New York range: 09:30–09:45 New York.",
        "- Direction: sign of the move from the Asia open to the 09:30 New York open.",
        "- Bullish sessions compare the New York range high to the Asia high; bearish sessions use the symmetric low-to-low comparison.",
        "- Entry: market at 09:45 in the continuation direction.",
        "- M1 same-bar ambiguity is resolved against the strategy: stop before target.",
        "",
        "## Broker units",
        "",
        f"- `{SYMBOL}` tick size: `{manifest['specification']['trade_tick_size']:.2f}` index point.",
        f"- 2,000 broker ticks: `{2000 * manifest['specification']['trade_tick_size']:.2f}` index points.",
        "- The original user threshold is therefore 20.00 index points.",
        "",
        "## Selected configuration",
        "",
    ]
    for key, value in {**asdict(signal), **asdict(outcome)}.items():
        lines.append(f"- {key}: `{value}`")
    lines.extend(
        [
            "",
            "## Full-period result",
            "",
            f"- Trades: {selected['trades']}",
            f"- Return at 1% risk: {selected['return_pct']:.2f}%",
            f"- Profit factor: {selected['profit_factor']:.2f}",
            f"- Win rate: {selected['win_rate_pct']:.2f}%",
            f"- Closed-balance maximum drawdown: {selected['max_closed_balance_dd_pct']:.2f}%",
            f"- Mean trade: {selected['mean_r']:.3f}R",
            "",
            "## Untouched 2025–2026 holdout",
            "",
            f"- Trades: {holdout['trades']}",
            f"- Return at 1% risk: {holdout['return_pct']:.2f}%",
            f"- Profit factor: {holdout['profit_factor']:.2f}",
            f"- Win rate: {holdout['win_rate_pct']:.2f}%",
            f"- Closed-balance maximum drawdown: {holdout['max_closed_balance_dd_pct']:.2f}%",
            "",
            "## Limitations",
            "",
            "- This is an M1 broker-history research test, not an exchange-tick reconstruction.",
            "- The drawdown is based on closed trade balance; MT5 tick replay is required for exact floating-equity drawdown.",
            "- The 2025–2026 holdout was not used to choose the configuration.",
            "- A final EA preset should only be deployed after an independent MT5 tester run and cross-broker check.",
            "",
        ]
    )
    (REPORTS / "REPORT.md").write_text("\n".join(lines), encoding="utf-8")
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--force-download", action="store_true")
    parser.add_argument("--download-only", action="store_true")
    args = parser.parse_args()
    raw, manifest = download_history(force=args.force_download)
    print(
        f"Loaded {len(raw):,} M1 bars; median spread "
        f"{manifest['median_positive_spread_index_points']:.2f} index points.",
        flush=True,
    )
    if args.download_only:
        return 0
    fallback_spread = manifest["median_positive_spread_points"]
    contexts, quality = build_day_contexts(raw, fallback_spread)
    print(f"Built {len(contexts):,} valid New York sessions; skipped={quality['skipped']}", flush=True)
    signal, outcome, top, _ = optimize(contexts)
    print(f"Selected signal={signal}", flush=True)
    print(f"Selected outcome={outcome}", flush=True)
    trades = selected_trades(contexts, signal, outcome)
    result = write_report(manifest, quality, signal, outcome, top, trades)
    print(json.dumps(json_safe(result["metrics"]), indent=2), flush=True)
    print(f"Reports written to {REPORTS}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
