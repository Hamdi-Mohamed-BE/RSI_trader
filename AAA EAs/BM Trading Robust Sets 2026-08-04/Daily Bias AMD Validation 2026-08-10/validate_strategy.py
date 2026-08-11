from __future__ import annotations

import itertools
import json
import math
from dataclasses import asdict, dataclass
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parent
OUTPUT = ROOT / "Results"
APEX_ROOT = ROOT.parent / "Apex Pulse and IVB Research 2026-08-10"
APEX_DATA = APEX_ROOT / "Data"
LOCAL_DATA = ROOT / "Data"
INITIAL_BALANCE = 10_000.0
RISK_FRACTION = 0.01
TZ = "Europe/London"

MARKETS = {
    "XAU": {"pattern": APEX_DATA / "MEXAtlantic-XAU-XAUUSD..-M1-{year}.csv.gz", "manifest": "apex"},
    "BTC": {"pattern": LOCAL_DATA / "MEXAtlantic-BTC-BTCUSD-M1-{year}.csv.gz", "manifest": "local"},
    "EURUSD": {"pattern": APEX_DATA / "MEXAtlantic-EURUSD-EURUSD..-M1-{year}.csv.gz", "manifest": "apex"},
    "GBPJPY": {"pattern": LOCAL_DATA / "MEXAtlantic-GBPJPY-GBPJPY..-M1-{year}.csv.gz", "manifest": "local"},
    "US30": {"pattern": APEX_DATA / "MEXAtlantic-US30-US30-M1-{year}.csv.gz", "manifest": "apex"},
    "US100": {"pattern": APEX_DATA / "MEXAtlantic-US100-UT100-M1-{year}.csv.gz", "manifest": "apex"},
}


@dataclass(frozen=True)
class Config:
    bias_mode: str
    skip_third_directional_day: bool
    confirmation_minutes: int
    confirmation_mode: str
    entry_mode: str
    asia_sweep_buffer_fraction: float
    reward_risk: float
    management: str


@dataclass
class DayContext:
    date: object
    year: int
    bias: dict[tuple[str, bool], int]
    asia_high: float
    asia_low: float
    asia_range: float
    bar_time: np.ndarray
    bar_open: np.ndarray
    bar_high: np.ndarray
    bar_low: np.ndarray
    bar_close: np.ndarray
    bar_spread: np.ndarray
    m1_time: np.ndarray
    m1_open: np.ndarray
    m1_high: np.ndarray
    m1_low: np.ndarray
    m1_close: np.ndarray
    m1_spread: np.ndarray


def load_manifests() -> dict[str, dict]:
    apex = json.loads((APEX_DATA / "manifest.json").read_text(encoding="utf-8"))["instruments"]
    local = json.loads((LOCAL_DATA / "manifest.json").read_text(encoding="utf-8"))["instruments"]
    return {**apex, **local}


def load_market(label: str, point: float) -> pd.DataFrame:
    frames = []
    pattern: Path = MARKETS[label]["pattern"]
    for year in range(2022, 2027):
        path = Path(str(pattern).format(year=year))
        if not path.exists():
            raise FileNotFoundError(path)
        frame = pd.read_csv(
            path,
            compression="gzip",
            usecols=["time", "open", "high", "low", "close", "tick_volume", "spread"],
            parse_dates=["time"],
        )
        frame["time"] = pd.to_datetime(frame.time, utc=True)
        frames.append(frame)
    data = pd.concat(frames, ignore_index=True)
    data = data.drop_duplicates("time", keep="last").sort_values("time")
    data["spread_price"] = data.spread.astype(float) * point
    data = data.set_index("time").tz_convert(TZ)
    return data


def direction(row: pd.Series) -> int:
    if row.close > row.open:
        return 1
    if row.close < row.open:
        return -1
    return 0


def body_engulfs(latest: pd.Series, previous: pd.Series, side: int) -> bool:
    if side > 0:
        return (
            latest.close > latest.open
            and latest.open <= min(previous.open, previous.close)
            and latest.close >= max(previous.open, previous.close)
        )
    return (
        latest.close < latest.open
        and latest.open >= max(previous.open, previous.close)
        and latest.close <= min(previous.open, previous.close)
    )


def build_daily_bias(data: pd.DataFrame) -> tuple[pd.DataFrame, dict[object, dict[tuple[str, bool], int]]]:
    daily = data.resample("1D", label="left", closed="left").agg(
        open=("open", "first"), high=("high", "max"), low=("low", "min"), close=("close", "last"), count=("close", "count")
    )
    daily = daily.loc[daily["count"] >= 120].dropna().copy()
    result: dict[object, dict[tuple[str, bool], int]] = {}
    for i in range(3, len(daily)):
        today = daily.iloc[i]
        latest, previous, third = daily.iloc[i - 1], daily.iloc[i - 2], daily.iloc[i - 3]
        latest_dir, previous_dir, third_dir = direction(latest), direction(previous), direction(third)
        latest_range = max(float(latest.high - latest.low), 1e-12)
        body_quality = abs(float(latest.close - latest.open)) / latest_range >= 0.30
        engulf = body_engulfs(latest, previous, latest_dir) if latest_dir else False
        stacked = latest_dir != 0 and latest_dir == previous_dir
        continuation = latest_dir if body_quality and (stacked or engulf) else 0
        reversal = 0
        if body_quality and latest_dir > 0 and previous_dir < 0 and engulf and latest.low < previous.low:
            reversal = 1
        elif body_quality and latest_dir < 0 and previous_dir > 0 and engulf and latest.high > previous.high:
            reversal = -1
        values: dict[tuple[str, bool], int] = {}
        for skip in (False, True):
            adjusted = continuation
            if skip and adjusted and latest_dir == previous_dir == third_dir:
                adjusted = 0
            values[("continuation", skip)] = adjusted
            values[("reversal", skip)] = reversal
            values[("both", skip)] = reversal if reversal else adjusted
        result[daily.index[i].date()] = values
    return daily, result


def resample_bars(data: pd.DataFrame, minutes: int) -> pd.DataFrame:
    bars = data.resample(f"{minutes}min", label="left", closed="left").agg(
        open=("open", "first"),
        high=("high", "max"),
        low=("low", "min"),
        close=("close", "last"),
        spread=("spread_price", "last"),
        count=("close", "count"),
    )
    return bars.loc[bars["count"] >= max(2, minutes // 2)].dropna()


def make_contexts(data: pd.DataFrame, biases: dict, minutes: int) -> list[DayContext]:
    bars = resample_bars(data, minutes)
    result = []
    for day, values in biases.items():
        if day.weekday() >= 5:
            continue
        day_start = pd.Timestamp(day, tz=TZ)
        asia_end = day_start + pd.Timedelta(hours=8)
        finish = day_start + pd.Timedelta(hours=16)
        asia = bars.loc[(bars.index >= day_start) & (bars.index < asia_end)]
        session = bars.loc[(bars.index >= asia_end) & (bars.index < finish)]
        m1 = data.loc[(data.index >= asia_end) & (data.index < finish)]
        if len(asia) < int(0.60 * 480 / minutes) or len(session) < int(0.60 * 480 / minutes) or len(m1) < 240:
            continue
        asia_high, asia_low = float(asia.high.max()), float(asia.low.min())
        asia_range = asia_high - asia_low
        if not asia_range > 0:
            continue
        result.append(
            DayContext(
                date=day,
                year=day.year,
                bias=values,
                asia_high=asia_high,
                asia_low=asia_low,
                asia_range=asia_range,
                bar_time=session.index.to_numpy(dtype="datetime64[ns]"),
                bar_open=session.open.to_numpy(dtype=float),
                bar_high=session.high.to_numpy(dtype=float),
                bar_low=session.low.to_numpy(dtype=float),
                bar_close=session.close.to_numpy(dtype=float),
                bar_spread=session.spread.to_numpy(dtype=float),
                m1_time=m1.index.to_numpy(dtype="datetime64[ns]"),
                m1_open=m1.open.to_numpy(dtype=float),
                m1_high=m1.high.to_numpy(dtype=float),
                m1_low=m1.low.to_numpy(dtype=float),
                m1_close=m1.close.to_numpy(dtype=float),
                m1_spread=m1.spread_price.to_numpy(dtype=float),
            )
        )
    return result


def confirmation(context: DayContext, i: int, side: int, mode: str) -> bool:
    if i < 1:
        return False
    op, hi, lo, cl = context.bar_open[i], context.bar_high[i], context.bar_low[i], context.bar_close[i]
    pop, phi, plo, pcl = context.bar_open[i - 1], context.bar_high[i - 1], context.bar_low[i - 1], context.bar_close[i - 1]
    if side > 0:
        body = cl > op and op <= pcl and cl >= pop and cl > context.asia_low
        return body and (mode == "body" or cl > phi)
    body = cl < op and op >= pcl and cl <= pop and cl < context.asia_high
    return body and (mode == "body" or cl < plo)


def locate_setup(context: DayContext, config: Config) -> dict | None:
    side = context.bias.get((config.bias_mode, config.skip_third_directional_day), 0)
    if side == 0:
        return None
    required = config.asia_sweep_buffer_fraction * context.asia_range
    swept = False
    extreme = math.inf if side > 0 else -math.inf
    for i in range(len(context.bar_open)):
        if side > 0:
            extreme = min(extreme, context.bar_low[i])
            swept = swept or context.bar_low[i] <= context.asia_low - required
        else:
            extreme = max(extreme, context.bar_high[i])
            swept = swept or context.bar_high[i] >= context.asia_high + required
        if not swept or not confirmation(context, i, side, config.confirmation_mode):
            continue
        signal_end = context.bar_time[i] + np.timedelta64(config.confirmation_minutes, "m")
        first = int(np.searchsorted(context.m1_time, signal_end, side="left"))
        if first >= len(context.m1_time):
            return None
        fill = -1
        entry = 0.0
        if config.entry_mode == "market":
            fill = first
            entry = context.m1_open[fill] + context.m1_spread[fill] if side > 0 else context.m1_open[fill]
        else:
            if side > 0:
                impulse_high = max(context.bar_high[i], context.bar_close[i])
                level = impulse_high - 0.618 * (impulse_high - extreme)
            else:
                impulse_low = min(context.bar_low[i], context.bar_close[i])
                level = impulse_low + 0.618 * (extreme - impulse_low)
            deadline = signal_end + np.timedelta64(4 * config.confirmation_minutes, "m")
            last = min(len(context.m1_time), int(np.searchsorted(context.m1_time, deadline, side="right")))
            for j in range(first, last):
                if side > 0 and context.m1_low[j] + context.m1_spread[j] <= level:
                    fill, entry = j, level
                    break
                if side < 0 and context.m1_high[j] >= level:
                    fill, entry = j, level
                    break
            if fill < 0:
                return None
        buffer = 0.05 * context.asia_range
        if side > 0:
            stop = extreme - buffer
            risk = entry - stop
        else:
            stop = extreme + buffer + context.m1_spread[fill]
            risk = stop - entry
        if risk <= max(2.0 * context.m1_spread[fill], 1e-12) or risk > 3.0 * context.asia_range:
            return None
        return {
            "side": side,
            "fill": fill,
            "entry": float(entry),
            "stop": float(stop),
            "risk": float(risk),
            "signal_time": pd.Timestamp(signal_end),
            "entry_time": pd.Timestamp(context.m1_time[fill]),
            "asia_high": context.asia_high,
            "asia_low": context.asia_low,
        }
    return None


def simulate(context: DayContext, setup: dict, reward_risk: float, management: str) -> dict:
    side, first = setup["side"], setup["fill"]
    entry, original_stop, risk = setup["entry"], setup["stop"], setup["risk"]
    stop = original_stop
    target = entry + side * reward_risk * risk
    exit_price = entry
    exit_reason = "session_close"
    exit_index = len(context.m1_time) - 1
    for i in range(first, len(context.m1_time)):
        if side > 0:
            high, low = context.m1_high[i], context.m1_low[i]
            if low <= stop:
                exit_price, exit_reason, exit_index = stop, "stop", i
                break
            if high >= target:
                exit_price, exit_reason, exit_index = target, "target", i
                break
            if management == "be1" and stop < entry and high >= entry + risk:
                if low <= entry:
                    exit_price, exit_reason, exit_index = entry, "break_even_same_minute", i
                    break
                stop = entry
        else:
            high = context.m1_high[i] + context.m1_spread[i]
            low = context.m1_low[i] + context.m1_spread[i]
            if high >= stop:
                exit_price, exit_reason, exit_index = stop, "stop", i
                break
            if low <= target:
                exit_price, exit_reason, exit_index = target, "target", i
                break
            if management == "be1" and stop > entry and low <= entry - risk:
                if high >= entry:
                    exit_price, exit_reason, exit_index = entry, "break_even_same_minute", i
                    break
                stop = entry
    else:
        if side > 0:
            exit_price = context.m1_close[exit_index]
        else:
            exit_price = context.m1_close[exit_index] + context.m1_spread[exit_index]
    result_r = side * (exit_price - entry) / risk
    result_r = float(max(-1.0, min(reward_risk, result_r)))
    return {
        "date": str(context.date),
        "year": context.year,
        "direction": "LONG" if side > 0 else "SHORT",
        "signal_time": setup["signal_time"].isoformat(),
        "entry_time": setup["entry_time"].isoformat(),
        "exit_time": pd.Timestamp(context.m1_time[exit_index]).isoformat(),
        "entry": entry,
        "stop": original_stop,
        "target": target,
        "exit": float(exit_price),
        "exit_reason": exit_reason,
        "result_r": result_r,
        "asia_high": setup["asia_high"],
        "asia_low": setup["asia_low"],
    }


def trades_for_config(contexts: list[DayContext], config: Config, years: set[int] | None = None) -> list[dict]:
    trades = []
    for context in contexts:
        if years is not None and context.year not in years:
            continue
        setup = locate_setup(context, config)
        if setup is not None:
            trades.append(simulate(context, setup, config.reward_risk, config.management))
    return trades


def metrics(trades: list[dict]) -> dict:
    if not trades:
        return {
            "trades": 0, "wins": 0, "losses": 0, "win_rate_pct": 0.0, "profit_factor": 0.0,
            "mean_r": 0.0, "net_r": 0.0, "return_pct": 0.0, "max_closed_balance_dd_pct": 0.0,
            "final_balance": INITIAL_BALANCE, "gross_profit": 0.0, "gross_loss": 0.0,
        }
    balance = INITIAL_BALANCE
    peak = balance
    max_dd = 0.0
    gross_profit = 0.0
    gross_loss = 0.0
    positive_r = 0.0
    negative_r = 0.0
    wins = losses = 0
    for trade in sorted(trades, key=lambda x: (x["entry_time"], x.get("market", ""))):
        r = float(trade["result_r"])
        pnl = balance * RISK_FRACTION * r
        balance += pnl
        if pnl > 0:
            gross_profit += pnl; positive_r += r; wins += 1
        elif pnl < 0:
            gross_loss += pnl; negative_r += r; losses += 1
        peak = max(peak, balance)
        if peak > 0:
            max_dd = max(max_dd, (peak - balance) / peak * 100.0)
    count = len(trades)
    return {
        "trades": count,
        "wins": wins,
        "losses": losses,
        "win_rate_pct": wins / count * 100.0,
        "profit_factor": positive_r / abs(negative_r) if negative_r < 0 else (999.0 if positive_r > 0 else 0.0),
        "mean_r": sum(float(t["result_r"]) for t in trades) / count,
        "net_r": sum(float(t["result_r"]) for t in trades),
        "return_pct": (balance / INITIAL_BALANCE - 1.0) * 100.0,
        "max_closed_balance_dd_pct": max_dd,
        "final_balance": balance,
        "gross_profit": gross_profit,
        "gross_loss": gross_loss,
    }


def score(train: dict, validation: dict) -> float:
    if train["trades"] < 20 or validation["trades"] < 8:
        return -999.0
    if train["profit_factor"] <= 1.0 or validation["profit_factor"] <= 1.0:
        return -100.0 + min(train["mean_r"], validation["mean_r"])
    stability = abs(train["mean_r"] - validation["mean_r"])
    drawdown = max(train["max_closed_balance_dd_pct"], validation["max_closed_balance_dd_pct"])
    return min(train["mean_r"], validation["mean_r"]) - 0.20 * stability - 0.002 * drawdown + 0.0001 * validation["trades"]


def all_configs() -> list[Config]:
    return [
        Config(*values)
        for values in itertools.product(
            ("continuation", "reversal", "both"),
            (False, True),
            (5, 15),
            ("body", "close_break"),
            ("market", "fib618"),
            (0.0, 0.05),
            (2.0, 3.0),
            ("none", "be1"),
        )
    ]


def evaluate_market(label: str, contexts: dict[int, list[DayContext]], configs: list[Config]) -> tuple[pd.DataFrame, dict[Config, dict]]:
    rows = []
    details: dict[Config, dict] = {}
    for number, config in enumerate(configs, 1):
        relevant = contexts[config.confirmation_minutes]
        train_trades = trades_for_config(relevant, config, {2022, 2023})
        validation_trades = trades_for_config(relevant, config, {2024})
        train = metrics(train_trades)
        validation = metrics(validation_trades)
        value = score(train, validation)
        details[config] = {"train": train, "validation": validation, "score": value}
        rows.append({
            **asdict(config), "score": value,
            "train_trades": train["trades"], "train_return": train["return_pct"], "train_pf": train["profit_factor"], "train_mean_r": train["mean_r"], "train_dd": train["max_closed_balance_dd_pct"],
            "validation_trades": validation["trades"], "validation_return": validation["return_pct"], "validation_pf": validation["profit_factor"], "validation_mean_r": validation["mean_r"], "validation_dd": validation["max_closed_balance_dd_pct"],
        })
        if number % 64 == 0:
            print(f"  {label}: {number}/{len(configs)} configurations", flush=True)
    ranking = pd.DataFrame(rows).sort_values(["score", "validation_trades"], ascending=[False, False])
    return ranking, details


def period_metrics(trades: list[dict]) -> dict:
    return {
        "train_2022_2023": metrics([t for t in trades if t["year"] in (2022, 2023)]),
        "validation_2024": metrics([t for t in trades if t["year"] == 2024]),
        "holdout_2025_2026": metrics([t for t in trades if t["year"] >= 2025]),
        "full_2022_2026": metrics(trades),
    }


def daily_accuracy(daily: pd.DataFrame, biases: dict, label: str) -> list[dict]:
    by_date = {stamp.date(): row for stamp, row in daily.iterrows()}
    rows = []
    for mode in ("continuation", "reversal", "both"):
        for period, years in (("train_2022_2023", {2022, 2023}), ("validation_2024", {2024}), ("holdout_2025_2026", {2025, 2026}), ("full", {2022, 2023, 2024, 2025, 2026})):
            outcomes = []
            for day, values in biases.items():
                if day.year not in years or day not in by_date:
                    continue
                side = values[(mode, False)]
                if side == 0:
                    continue
                actual = direction(by_date[day])
                if actual:
                    outcomes.append(1 if actual == side else 0)
            rows.append({"market": label, "bias_mode": mode, "period": period, "signals": len(outcomes), "direction_accuracy_pct": 100.0 * sum(outcomes) / len(outcomes) if outcomes else 0.0})
    return rows


def save_equity(trades: list[dict], path: Path, title: str) -> None:
    balance = INITIAL_BALANCE
    dates = []
    values = []
    for trade in sorted(trades, key=lambda x: (x["entry_time"], x.get("market", ""))):
        balance *= 1.0 + RISK_FRACTION * float(trade["result_r"])
        dates.append(pd.Timestamp(trade["entry_time"]))
        values.append(balance)
    fig, ax = plt.subplots(figsize=(12, 5.5))
    if dates:
        ax.step(dates, values, where="post", linewidth=1.4)
    ax.axhline(INITIAL_BALANCE, color="#777", linewidth=0.8)
    ax.grid(alpha=0.25)
    ax.set(title=title, xlabel="Trade date", ylabel="Closed balance (USD)")
    fig.tight_layout()
    fig.savefig(path, dpi=170)
    plt.close(fig)


def json_safe(value):
    if isinstance(value, dict):
        return {str(k): json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [json_safe(v) for v in value]
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating,)):
        return float(value)
    if isinstance(value, (pd.Timestamp,)):
        return value.isoformat()
    return value


def main() -> int:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    manifests = load_manifests()
    configs = all_configs()
    all_details: dict[str, dict[Config, dict]] = {}
    selected: dict[str, Config] = {}
    prepared: dict[str, tuple[dict[int, list[DayContext]], pd.DataFrame, dict]] = {}
    accuracy_rows = []
    print(f"Testing {len(configs)} configurations without reading the 2025-2026 holdout during selection.", flush=True)
    for label in MARKETS:
        print(f"Loading {label}...", flush=True)
        data = load_market(label, float(manifests[label]["point"]))
        daily, biases = build_daily_bias(data)
        accuracy_rows.extend(daily_accuracy(daily, biases, label))
        contexts = {minutes: make_contexts(data, biases, minutes) for minutes in (5, 15)}
        prepared[label] = (contexts, daily, biases)
        print(f"  contexts: M5={len(contexts[5])}, M15={len(contexts[15])}", flush=True)
        ranking, details = evaluate_market(label, contexts, configs)
        ranking.to_csv(OUTPUT / f"configuration-ranking-{label}.csv", index=False)
        chosen = configs[int(ranking.index[0])]
        selected[label] = chosen
        all_details[label] = details
        print(f"  selected {label}: {chosen}", flush=True)

    # Select one universal configuration using training and 2024 validation only.
    pooled_rows = []
    for config in configs:
        train_trades = sum(all_details[label][config]["train"]["trades"] for label in MARKETS)
        val_trades = sum(all_details[label][config]["validation"]["trades"] for label in MARKETS)
        train_net = sum(all_details[label][config]["train"]["net_r"] for label in MARKETS)
        val_net = sum(all_details[label][config]["validation"]["net_r"] for label in MARKETS)
        train_pos = sum(all_details[label][config]["train"]["profit_factor"] > 1.0 for label in MARKETS)
        val_pos = sum(all_details[label][config]["validation"]["profit_factor"] > 1.0 for label in MARKETS)
        worst_dd = max(all_details[label][config]["validation"]["max_closed_balance_dd_pct"] for label in MARKETS)
        mean_train = train_net / train_trades if train_trades else -10.0
        mean_val = val_net / val_trades if val_trades else -10.0
        universal_score = min(mean_train, mean_val) - 0.03 * (6 - val_pos) - 0.01 * (6 - train_pos) - 0.002 * worst_dd
        if train_trades < 120 or val_trades < 40:
            universal_score = -999.0
        pooled_rows.append({**asdict(config), "score": universal_score, "train_trades": train_trades, "validation_trades": val_trades, "train_mean_r": mean_train, "validation_mean_r": mean_val, "positive_train_markets": train_pos, "positive_validation_markets": val_pos, "worst_validation_dd": worst_dd})
    pooled_ranking = pd.DataFrame(pooled_rows).sort_values(["score", "validation_trades"], ascending=[False, False])
    pooled_ranking.to_csv(OUTPUT / "configuration-ranking-UNIVERSAL.csv", index=False)
    universal = configs[int(pooled_ranking.index[0])]
    print(f"Universal configuration locked: {universal}", flush=True)

    # Only now evaluate selected configurations on the untouched years.
    summary_rows = []
    result_json = {"methodology": {"initial_balance": INITIAL_BALANCE, "risk_fraction": RISK_FRACTION, "selection": "2022-2023 training plus 2024 validation", "untouched_holdout": "2025-01-01 through 2026-08-09", "costs": "Observed M1 broker spread included; no commission or swap; same-minute ambiguity resolved stop-first."}, "markets": {}, "universal": {"config": asdict(universal)}}
    universal_trades = []
    for label in MARKETS:
        contexts = prepared[label][0]
        config = selected[label]
        trades = trades_for_config(contexts[config.confirmation_minutes], config)
        for trade in trades:
            trade["market"] = label
        pd.DataFrame(trades).to_csv(OUTPUT / f"selected-trades-{label}.csv", index=False)
        periods = period_metrics(trades)
        result_json["markets"][label] = {"config": asdict(config), "period_metrics": periods}
        train, validation = periods["train_2022_2023"], periods["validation_2024"]
        full, holdout = periods["full_2022_2026"], periods["holdout_2025_2026"]
        passed = (
            train["trades"] >= 20 and train["profit_factor"] > 1.0 and train["return_pct"] > 0
            and validation["trades"] >= 8 and validation["profit_factor"] > 1.0 and validation["return_pct"] > 0
            and holdout["trades"] >= 8 and holdout["profit_factor"] > 1.0 and holdout["return_pct"] > 0
            and full["profit_factor"] >= 1.15 and full["max_closed_balance_dd_pct"] <= 15.0
        )
        summary_rows.append({"market": label, **asdict(config), "full_trades": full["trades"], "full_return_pct": full["return_pct"], "full_pf": full["profit_factor"], "full_win_rate_pct": full["win_rate_pct"], "full_max_dd_pct": full["max_closed_balance_dd_pct"], "holdout_trades": holdout["trades"], "holdout_return_pct": holdout["return_pct"], "holdout_pf": holdout["profit_factor"], "holdout_win_rate_pct": holdout["win_rate_pct"], "holdout_max_dd_pct": holdout["max_closed_balance_dd_pct"], "pass": passed})
        save_equity(trades, OUTPUT / f"equity-{label}.png", f"Daily Bias AMD — {label} — individually selected rule")

        common = trades_for_config(contexts[universal.confirmation_minutes], universal)
        for trade in common:
            trade["market"] = label
        universal_trades.extend(common)

    universal_periods = period_metrics(universal_trades)
    result_json["universal"]["period_metrics"] = universal_periods
    pd.DataFrame(universal_trades).sort_values(["entry_time", "market"]).to_csv(OUTPUT / "selected-trades-UNIVERSAL.csv", index=False)
    save_equity(universal_trades, OUTPUT / "equity-UNIVERSAL.png", "Daily Bias AMD — one locked rule across all six markets")
    pd.DataFrame(summary_rows).to_csv(OUTPUT / "summary.csv", index=False)
    pd.DataFrame(accuracy_rows).to_csv(OUTPUT / "daily-bias-direction-accuracy.csv", index=False)
    (OUTPUT / "results.json").write_text(json.dumps(json_safe(result_json), indent=2), encoding="utf-8")
    print(json.dumps(json_safe({"summary": summary_rows, "universal_config": asdict(universal), "universal_periods": universal_periods}), indent=2), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
