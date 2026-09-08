"""Full no-lookahead pipeline for the SNB intraday FX session-effect paper."""
from __future__ import annotations

from dataclasses import asdict, dataclass, replace
from datetime import datetime, timezone
from pathlib import Path
import itertools
import json
import math

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import MetaTrader5 as mt5
import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parent
DATA = ROOT / "Data"
CHARTS = ROOT / "Charts"
TERMINAL = Path(r"C:\Program Files\JustMarkets MetaTrader 5\terminal64.exe")
SYMBOLS = ("EURUSD", "GBPUSD", "USDJPY", "USDCHF", "AUDUSD", "EURJPY")
TIMEFRAMES = {"M15": "15min", "M30": "30min", "H1": "1h"}
TRAIN = (pd.Timestamp("2023-09-01", tz="UTC"), pd.Timestamp("2024-09-01", tz="UTC"))
VALIDATION = (pd.Timestamp("2024-09-01", tz="UTC"), pd.Timestamp("2025-09-01", tz="UTC"))
LOCKED = (pd.Timestamp("2025-09-01", tz="UTC"), pd.Timestamp("2026-09-01", tz="UTC"))
FULL = (TRAIN[0], LOCKED[1])
RISK = 0.01
COMMISSION_SLIPPAGE_PIPS = 0.40
SPREAD_FLOOR_PIPS = 0.60
SEED = 8092026

# session name -> ((leg, local start hour, duration hours), ...)
SESSIONS = {
    "eu-06-12": (("eu", 6, 6),),
    "eu-07-13": (("eu", 7, 6),),
    "eu-07-15-paper": (("eu", 7, 8),),
    "eu-08-14": (("eu", 8, 6),),
    "ny-07-13": (("ny", 7, 6),),
    "ny-08-14": (("ny", 8, 6),),
    "ny-08-16-paper": (("ny", 8, 8),),
    "ny-09-15": (("ny", 9, 6),),
    "paper-combined": (("eu", 7, 8), ("ny", 8, 8)),
}
FILTERS = ("none", "momentum", "reversal", "ema50", "low-vol", "high-vol", "rel-volume")
DIRECTIONS = ("paper", "inverse", "long-only", "short-only")
STOPS = tuple(("atr", value) for value in (0.50, 0.75, 1.00, 1.25, 1.50, 2.00, 3.00, 4.00)) + (
    ("swing", 8.0), ("swing", 16.0), ("prior-day", 0.0),
)
TARGETS = tuple(("fixed", value) for value in (0.50, 0.75, 1.00, 1.50, 2.00, 3.00, 4.00)) + (
    ("timed", 0.0), ("adaptive", 0.0),
)
MANAGEMENTS = ("none", "breakeven", "atr-trail", "dynamic-50-20")
WEEKDAYS = ("all", "no-monday", "no-friday", "tue-thu")
_EVENT_CACHE: dict[tuple[int, str], list[tuple[int, int, str]]] = {}


@dataclass(frozen=True)
class Config:
    timeframe: str = "M15"
    session: str = "paper-combined"
    direction: str = "paper"
    confirmation: str = "none"
    stop_mode: str = "atr"
    stop_value: float = 1.50
    target_mode: str = "timed"
    rr: float = 0.0
    management: str = "none"
    weekdays: str = "all"


def dump(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, allow_nan=False), encoding="utf-8")


def broker_symbol(canonical: str, names: list[str]) -> str:
    exact = [name for name in names if name.upper() == canonical]
    if exact:
        return exact[0]
    prefixed = [name for name in names if name.upper().startswith(canonical)]
    if not prefixed:
        raise RuntimeError(f"No broker symbol found for {canonical}")
    return min(prefixed, key=len)


def download() -> dict:
    DATA.mkdir(parents=True, exist_ok=True)
    metadata_path = DATA / "metadata.json"
    if metadata_path.exists() and all((DATA / f"{symbol}-M15.npz").exists() for symbol in SYMBOLS):
        return json.loads(metadata_path.read_text(encoding="utf-8"))
    if not mt5.initialize(path=str(TERMINAL)):
        raise RuntimeError(f"MT5 initialization failed: {mt5.last_error()}")
    try:
        names = [s.name for s in (mt5.symbols_get() or ())]
        metadata = {"terminal": str(TERMINAL), "downloaded_at": datetime.now(timezone.utc).isoformat(), "symbols": {}}
        for canonical in SYMBOLS:
            actual = broker_symbol(canonical, names)
            if not mt5.symbol_select(actual, True):
                raise RuntimeError(f"Cannot select {actual}: {mt5.last_error()}")
            rates = mt5.copy_rates_from_pos(actual, mt5.TIMEFRAME_M15, 0, 99_999)
            if rates is None or len(rates) < 50_000:
                raise RuntimeError(f"Insufficient M15 data for {actual}: {0 if rates is None else len(rates)}")
            info = mt5.symbol_info(actual)
            np.savez_compressed(DATA / f"{canonical}-M15.npz", rates=rates)
            metadata["symbols"][canonical] = {
                "broker_symbol": actual, "bars": int(len(rates)), "point": float(info.point),
                "digits": int(info.digits), "from": datetime.fromtimestamp(int(rates[0]["time"]), timezone.utc).isoformat(),
                "to": datetime.fromtimestamp(int(rates[-1]["time"]), timezone.utc).isoformat(),
            }
        dump(DATA / "metadata.json", metadata)
        return metadata
    finally:
        mt5.shutdown()


def load(canonical: str, metadata: dict) -> tuple[pd.DataFrame, dict]:
    rates = np.load(DATA / f"{canonical}-M15.npz")["rates"]
    idx = pd.to_datetime(rates["time"], unit="s", utc=True)
    frame = pd.DataFrame({key: rates[key].astype(float) for key in ("open", "high", "low", "close", "tick_volume", "spread")}, index=idx)
    frame = frame[~frame.index.duplicated(keep="last")].sort_index()
    meta = metadata["symbols"][canonical]
    point = float(meta["point"])
    pip = point * 10.0
    recorded = frame.spread * point
    frame["spread_price"] = np.maximum(recorded, SPREAD_FLOOR_PIPS * pip)
    return frame, meta | {"pip": pip}


def true_range(frame: pd.DataFrame) -> pd.Series:
    previous = frame.close.shift(1)
    return pd.concat(((frame.high-frame.low), (frame.high-previous).abs(), (frame.low-previous).abs()), axis=1).max(axis=1)


def bars_for(base: pd.DataFrame, timeframe: str) -> pd.DataFrame:
    if timeframe == "M15":
        bars = base.copy()
        bars["volume"] = bars.tick_volume
    else:
        bars = base.resample(TIMEFRAMES[timeframe], label="left", closed="left").agg(
            open=("open", "first"), high=("high", "max"), low=("low", "min"), close=("close", "last"),
            volume=("tick_volume", "sum"), spread_price=("spread_price", "last"),
        ).dropna()
    bars["atr"] = true_range(bars).ewm(alpha=1/14, adjust=False, min_periods=14).mean()
    bars["ema50"] = bars.close.ewm(span=50, adjust=False, min_periods=50).mean()
    bars["atr_ratio"] = bars.atr / bars.atr.rolling(20, min_periods=10).median()
    bars["volume_ratio"] = bars.volume / bars.volume.rolling(20, min_periods=10).median().replace(0, np.nan)
    bars["swing_low_8"] = bars.low.rolling(8, min_periods=8).min().shift(1)
    bars["swing_high_8"] = bars.high.rolling(8, min_periods=8).max().shift(1)
    bars["swing_low_16"] = bars.low.rolling(16, min_periods=16).min().shift(1)
    bars["swing_high_16"] = bars.high.rolling(16, min_periods=16).max().shift(1)
    daily = base.resample("1D", label="left", closed="left").agg(high=("high", "max"), low=("low", "min")).shift(1)
    bars["prior_day_high"] = daily.high.reindex(bars.index, method="ffill")
    bars["prior_day_low"] = daily.low.reindex(bars.index, method="ffill")
    return bars.dropna(subset=["atr", "ema50"])


def weekday_ok(day: int, mode: str) -> bool:
    if mode == "no-monday": return day != 0
    if mode == "no-friday": return day != 4
    if mode == "tue-thu": return 1 <= day <= 3
    return day < 5


def session_events(bars: pd.DataFrame, session: str) -> list[tuple[int, int, str]]:
    cache_key = (id(bars), session)
    cached = _EVENT_CACHE.get(cache_key)
    if cached is not None:
        return cached
    events: list[tuple[int, int, str]] = []
    for leg, start_hour, duration in SESSIONS[session]:
        zone = "Europe/London" if leg == "eu" else "America/New_York"
        local = bars.index.tz_convert(zone)
        starts = np.flatnonzero((local.hour == start_hour) & (local.minute == 0) & (local.weekday < 5))
        for start in starts:
            end_utc = (local[start] + pd.Timedelta(hours=duration)).tz_convert("UTC")
            end = int(bars.index.searchsorted(end_utc, side="left"))
            if end < len(bars) and end > start:
                events.append((int(start), end, leg))
    result = sorted(events)
    _EVENT_CACHE[cache_key] = result
    return result


def desired_side(leg: str, mode: str) -> int:
    side = -1 if leg == "eu" else 1
    if mode == "inverse": side *= -1
    if mode == "long-only" and side < 0: return 0
    if mode == "short-only" and side > 0: return 0
    return side


def confirmed(bars: pd.DataFrame, index: int, side: int, mode: str) -> bool:
    previous = index - 1
    if previous < 1: return False
    change = float(bars.close.iloc[previous] - bars.open.iloc[previous])
    if mode == "momentum": return side * change > 0
    if mode == "reversal": return side * change < 0
    if mode == "ema50": return side * (float(bars.close.iloc[previous]) - float(bars.ema50.iloc[previous])) > 0
    if mode == "low-vol": return float(bars.atr_ratio.iloc[previous]) <= 1.0
    if mode == "high-vol": return float(bars.atr_ratio.iloc[previous]) > 1.0
    if mode == "rel-volume": return float(bars.volume_ratio.iloc[previous]) >= 1.0
    return True


def stop_distance(bars: pd.DataFrame, index: int, side: int, config: Config, entry: float) -> float:
    previous = index - 1
    atr = float(bars.atr.iloc[previous])
    if config.stop_mode == "atr":
        return config.stop_value * atr
    if config.stop_mode == "swing":
        window = int(config.stop_value)
        level = float(bars[f"swing_low_{window}"].iloc[previous] if side > 0 else bars[f"swing_high_{window}"].iloc[previous])
    else:
        level = float(bars.prior_day_low.iloc[previous] if side > 0 else bars.prior_day_high.iloc[previous])
    raw = entry-level if side > 0 else level-entry
    return max(0.50*atr, min(4.0*atr, raw+0.10*atr))


def simulate(bars: pd.DataFrame, meta: dict, config: Config, period: tuple[pd.Timestamp, pd.Timestamp], collect: bool = False, extra_cost_pips: float = 0.0) -> dict:
    rows = []
    pip = float(meta["pip"])
    for start, end, leg in session_events(bars, config.session):
        opened_at = bars.index[start]
        if opened_at < period[0] or opened_at >= period[1] or not weekday_ok(opened_at.weekday(), config.weekdays):
            continue
        side = desired_side(leg, config.direction)
        if side == 0 or not confirmed(bars, start, side, config.confirmation):
            continue
        spread = float(bars.spread_price.iloc[start])
        entry = float(bars.open.iloc[start]) + (spread if side > 0 else 0.0)
        distance = stop_distance(bars, start, side, config, entry)
        if not math.isfinite(distance) or distance <= 2.0*spread:
            continue
        stop = entry-side*distance
        atr_ratio = float(bars.atr_ratio.iloc[start-1])
        rr = config.rr
        if config.target_mode == "adaptive": rr = 2.0 if atr_ratio <= 1.0 else 0.75
        target = entry+side*rr*distance if config.target_mode != "timed" else math.nan
        exit_index = end
        exit_price = float(bars.close.iloc[end]) + (float(bars.spread_price.iloc[end]) if side < 0 else 0.0)
        reason = "session-close"
        for i in range(start, end+1):
            bar_spread = float(bars.spread_price.iloc[i])
            if side > 0:
                stop_hit = float(bars.low.iloc[i]) <= stop
                target_hit = config.target_mode != "timed" and float(bars.high.iloc[i]) >= target
            else:
                stop_hit = float(bars.high.iloc[i])+bar_spread >= stop
                target_hit = config.target_mode != "timed" and float(bars.low.iloc[i])+bar_spread <= target
            if stop_hit:
                exit_index, exit_price, reason = i, stop, "stop"
                break
            if target_hit:
                exit_index, exit_price, reason = i, target, "target"
                break
            progress = side*(float(bars.close.iloc[i])+(bar_spread if side < 0 else 0.0)-entry)/distance
            if config.management == "breakeven" and progress >= 1.0:
                stop = max(stop, entry) if side > 0 else min(stop, entry)
            elif config.management == "atr-trail" and progress >= 1.0:
                candidate = float(bars.close.iloc[i])-1.5*float(bars.atr.iloc[i]) if side > 0 else float(bars.close.iloc[i])+bar_spread+1.5*float(bars.atr.iloc[i])
                stop = max(stop, candidate) if side > 0 else min(stop, candidate)
            elif config.management == "dynamic-50-20" and progress >= 0.50:
                candidate = entry+side*0.20*distance
                stop = max(stop, candidate) if side > 0 else min(stop, candidate)
        cost_r = (COMMISSION_SLIPPAGE_PIPS+extra_cost_pips)*pip/distance
        result_r = side*(exit_price-entry)/distance-cost_r
        rows.append({
            "entry": opened_at.isoformat(), "exit": bars.index[exit_index].isoformat(), "side": "long" if side > 0 else "short",
            "leg": leg, "r": float(result_r), "stop_pips": float(distance/pip), "reason": reason,
        })
    return metrics(rows, collect)


def metrics(trades: list[dict], collect: bool = False) -> dict:
    if not trades:
        return {"return_pct": 0.0, "profit_factor": 0.0, "win_rate": 0.0, "max_dd_pct": 0.0, "trades": 0, "sharpe": 0.0, "recovery": 0.0, "expectancy_r": 0.0, "average_rr": 0.0, "max_win_streak": 0, "max_loss_streak": 0}
    ordered = sorted(trades, key=lambda x: x["exit"])
    rs = np.array([x["r"] for x in ordered], float)
    equity = np.r_[1.0, np.cumprod(np.maximum(0.01, 1.0+RISK*rs))]
    pnl = np.diff(equity)
    gains, losses = pnl[pnl > 0].sum(), -pnl[pnl < 0].sum()
    peaks = np.maximum.accumulate(equity)
    drawdown = float(np.max(1.0-equity/peaks)*100.0)
    exits = pd.to_datetime([x["exit"] for x in ordered], utc=True)
    daily = pd.Series(RISK*rs, index=exits).groupby(level=0).sum().resample("1D").sum()
    sharpe = float(daily.mean()/daily.std(ddof=1)*math.sqrt(252.0)) if daily.std(ddof=1) > 0 else 0.0
    win_streak = loss_streak = max_win = max_loss = 0
    for value in rs:
        if value > 0: win_streak, loss_streak = win_streak+1, 0
        elif value < 0: loss_streak, win_streak = loss_streak+1, 0
        else: win_streak = loss_streak = 0
        max_win, max_loss = max(max_win, win_streak), max(max_loss, loss_streak)
    result = {
        "return_pct": float((equity[-1]-1.0)*100.0), "profit_factor": float(min(99.0, gains/losses if losses else 99.0)),
        "win_rate": float(np.mean(rs > 0)*100.0), "max_dd_pct": drawdown, "trades": int(len(rs)), "sharpe": sharpe,
        "recovery": float(((equity[-1]-1.0)*100.0)/drawdown if drawdown else 0.0), "expectancy_r": float(rs.mean()),
        "average_rr": float(rs[rs > 0].mean() if np.any(rs > 0) else 0.0), "max_win_streak": max_win, "max_loss_streak": max_loss,
    }
    if collect: result["trades_data"] = ordered
    return result


def raw_paper(bars: pd.DataFrame, meta: dict, period: tuple[pd.Timestamp, pd.Timestamp]) -> dict:
    trades = []
    pip = float(meta["pip"])
    for start, end, leg in session_events(bars, "paper-combined"):
        opened_at = bars.index[start]
        if opened_at < period[0] or opened_at >= period[1]: continue
        side = -1 if leg == "eu" else 1
        spread = float(bars.spread_price.iloc[start])
        entry = float(bars.open.iloc[start])+(spread if side > 0 else 0.0)
        exit_price = float(bars.close.iloc[end])+(float(bars.spread_price.iloc[end]) if side < 0 else 0.0)
        net = side*(exit_price-entry)/entry-(COMMISSION_SLIPPAGE_PIPS*pip/entry)
        trades.append({"entry": opened_at.isoformat(), "exit": bars.index[end].isoformat(), "r": net/0.01, "side": "long" if side > 0 else "short", "leg": leg, "stop_pips": 0.0, "reason": "paper-session-close"})
    result = metrics(trades)
    result["return_pct"] = float((np.prod(1.0+np.array([x["r"] for x in trades])*0.01)-1.0)*100.0) if trades else 0.0
    return result


def robust_score(train: dict, validation: dict) -> float:
    if train["trades"] < 50 or validation["trades"] < 50: return -10_000.0+train["trades"]+validation["trades"]
    minimum_return = min(train["return_pct"], validation["return_pct"])
    minimum_pf = min(train["profit_factor"], validation["profit_factor"])
    minimum_sharpe = min(train["sharpe"], validation["sharpe"])
    maximum_dd = max(train["max_dd_pct"], validation["max_dd_pct"])
    score = 0.40*minimum_return+12.0*math.log(max(0.05, min(3.0, minimum_pf)))+2.0*minimum_sharpe+min(train["recovery"], validation["recovery"])-0.30*maximum_dd
    if minimum_return <= 0: score -= 35.0+abs(minimum_return)
    if minimum_pf < 1.0: score -= 30.0*(1.0-minimum_pf)
    return float(score)


def evaluate(bars: dict[str, pd.DataFrame], meta: dict, config: Config) -> tuple[dict, dict, float]:
    train = simulate(bars[config.timeframe], meta, config, TRAIN)
    validation = simulate(bars[config.timeframe], meta, config, VALIDATION)
    return train, validation, robust_score(train, validation)


def key(config: Config) -> tuple:
    return tuple(asdict(config).values())


def beam_stage(bars: dict[str, pd.DataFrame], meta: dict, configs: list[Config], width: int = 20) -> tuple[list[Config], list[dict]]:
    seen = set(); scored = []; audit = []
    for config in configs:
        if key(config) in seen: continue
        seen.add(key(config))
        train, validation, score = evaluate(bars, meta, config)
        scored.append((score, config))
        audit.append({"config": asdict(config), "score": score, "train": train, "validation": validation})
    scored.sort(key=lambda item: item[0], reverse=True)
    return [config for _, config in scored[:width]], audit


def select(canonical: str, base: pd.DataFrame, meta: dict) -> dict:
    _EVENT_CACHE.clear()
    bars = {name: bars_for(base, name) for name in TIMEFRAMES}
    all_audit = []
    initial = [Config(timeframe=tf, session=session, confirmation=confirmation) for tf, session, confirmation in itertools.product(TIMEFRAMES, SESSIONS, FILTERS)]
    print(f"  {canonical}: signal/session/timeframe stage ({len(initial)} configs)", flush=True)
    beam, audit = beam_stage(bars, meta, initial); all_audit += [{"stage": "signal", **x} for x in audit]
    print(f"  {canonical}: direction stage", flush=True)
    beam, audit = beam_stage(bars, meta, [replace(c, direction=value) for c in beam for value in DIRECTIONS]); all_audit += [{"stage": "direction", **x} for x in audit]
    print(f"  {canonical}: dynamic-stop stage", flush=True)
    beam, audit = beam_stage(bars, meta, [replace(c, stop_mode=mode, stop_value=value) for c in beam for mode, value in STOPS]); all_audit += [{"stage": "stop", **x} for x in audit]
    print(f"  {canonical}: RR/adaptive-RR stage", flush=True)
    beam, audit = beam_stage(bars, meta, [replace(c, target_mode=mode, rr=value) for c in beam for mode, value in TARGETS]); all_audit += [{"stage": "target", **x} for x in audit]
    print(f"  {canonical}: breakeven/trailing stage", flush=True)
    beam, audit = beam_stage(bars, meta, [replace(c, management=value) for c in beam for value in MANAGEMENTS]); all_audit += [{"stage": "management", **x} for x in audit]
    print(f"  {canonical}: weekday robustness stage", flush=True)
    beam, audit = beam_stage(bars, meta, [replace(c, weekdays=value) for c in beam for value in WEEKDAYS]); all_audit += [{"stage": "weekday", **x} for x in audit]
    selected = beam[0]
    train, validation, score = evaluate(bars, meta, selected)
    locked = simulate(bars[selected.timeframe], meta, selected, LOCKED, collect=True)
    full = simulate(bars[selected.timeframe], meta, selected, FULL, collect=True)
    stressed = simulate(bars[selected.timeframe], meta, selected, LOCKED, extra_cost_pips=1.0)
    raw = raw_paper(bars["M15"], meta, LOCKED)
    return {"symbol": canonical, "selected": asdict(selected), "selection_score": score, "raw_locked": raw, "train": train, "validation": validation, "locked": locked, "locked_double_cost": stressed, "full": full, "audit": all_audit}


def monte_carlo(trades: list[dict], paths: int = 5000, block: int = 5) -> dict:
    rs = np.array([x["r"] for x in trades], float)
    if not len(rs): return {"paths": paths, "return_p5": -100.0, "return_median": -100.0, "return_p95": -100.0, "dd_median": 100.0, "dd_p95": 100.0, "profit_probability": 0.0}
    rng = np.random.default_rng(SEED+len(rs)); returns = []; drawdowns = []
    for _ in range(paths):
        sample = []
        while len(sample) < len(rs):
            start = int(rng.integers(0, max(1, len(rs)-block+1))); sample.extend(rs[start:start+block])
        equity = np.cumprod(np.maximum(0.01, 1.0+RISK*np.array(sample[:len(rs)])))
        peak = np.maximum.accumulate(np.r_[1.0, equity])[1:]
        returns.append((equity[-1]-1.0)*100.0); drawdowns.append(np.max(1.0-equity/peak)*100.0)
    return {"paths": paths, "return_p5": float(np.percentile(returns, 5)), "return_median": float(np.median(returns)), "return_p95": float(np.percentile(returns, 95)), "dd_median": float(np.median(drawdowns)), "dd_p95": float(np.percentile(drawdowns, 95)), "profit_probability": float(np.mean(np.array(returns) > 0)*100.0)}


def promotion(row: dict) -> tuple[bool, list[str]]:
    failures = []
    for phase in ("train", "validation", "locked", "locked_double_cost"):
        if row[phase]["return_pct"] <= 0: failures.append(f"{phase} return <= 0")
    if row["locked"]["profit_factor"] < 1.20: failures.append("locked PF < 1.20")
    if row["locked"]["trades"] < 80: failures.append("locked trades < 80")
    if row["locked"]["max_dd_pct"] > 15.0: failures.append("locked DD > 15%")
    if row["monte_carlo"]["return_p5"] <= 0: failures.append("Monte Carlo P5 <= 0")
    return not failures, failures


def chart(row: dict) -> None:
    trades = row["full"]["trades_data"]
    equity = 10_000.0; xs = [FULL[0]]; ys = [equity]
    for trade in sorted(trades, key=lambda x: x["exit"]):
        equity *= max(0.01, 1.0+RISK*trade["r"]); xs.append(pd.Timestamp(trade["exit"])); ys.append(equity)
    CHARTS.mkdir(parents=True, exist_ok=True)
    fig, ax = plt.subplots(figsize=(12, 5)); fig.patch.set_facecolor("#07110f"); ax.set_facecolor("#07110f")
    ax.plot(xs, ys, color="#74f5ca", linewidth=1.5); ax.axvline(VALIDATION[0], color="#55b6ff", linestyle="--"); ax.axvline(LOCKED[0], color="#f2c14e", linestyle="--")
    ax.set_title(f"{row['symbol']} — selected session effect", color="white"); ax.tick_params(colors="#a9c8bf"); ax.grid(alpha=.15); fig.tight_layout()
    fig.savefig(CHARTS / f"{row['symbol'].lower()}-equity.png", dpi=150); plt.close(fig)


def report(payload: dict) -> str:
    lines = [
        "# Intraday FX Session Effect — Full Pipeline Report", "", "Research only. No EA/BAT/website/portfolio deployment was performed.", "",
        "## Source and test design", "", "The source is the Swiss National Bank paper by Breedon and Ranaldo. The paper reports local-currency depreciation during local trading hours and found its simple EURUSD session rules profitable after interdealer costs. Calyx retests that hypothesis on recent retail MT5 data with a frozen train/validation/locked-year protocol.", "",
        "## Selected results", "", "| Pair | Locked WR | Locked PF | Locked return | Locked DD | Sharpe | Recovery | Trades | Avg win R | Stress PF | MC P5 | Gate |", "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|",
    ]
    for row in payload["results"]:
        locked, stress, mc = row["locked"], row["locked_double_cost"], row["monte_carlo"]
        lines.append(f"| {row['symbol']} | {locked['win_rate']:.2f}% | {locked['profit_factor']:.2f} | {locked['return_pct']:+.2f}% | {locked['max_dd_pct']:.2f}% | {locked['sharpe']:.2f} | {locked['recovery']:.2f} | {locked['trades']} | {locked['average_rr']:.2f}R | {stress['profit_factor']:.2f} | {mc['return_p5']:+.2f}% | {'PASS' if row['promoted'] else 'FAIL'} |")
    lines += ["", "## Paper-rule comparison", "", "| Pair | Raw locked WR | Raw locked PF | Raw locked return | Optimized locked PF |", "|---|---:|---:|---:|---:|"]
    for row in payload["results"]:
        raw, locked = row["raw_locked"], row["locked"]
        lines.append(f"| {row['symbol']} | {raw['win_rate']:.2f}% | {raw['profit_factor']:.2f} | {raw['return_pct']:+.2f}% | {locked['profit_factor']:.2f} |")
    lines += ["", "## Configurations and decisions", ""]
    for row in payload["results"]:
        lines += [f"### {row['symbol']}", "", f"- Selected without looking at locked year: `{json.dumps(row['selected'], sort_keys=True)}`", f"- Decision: **{'PASS' if row['promoted'] else 'FAIL'}**", f"- Reasons: {', '.join(row['gate_failures']) if row['gate_failures'] else 'all quantitative gates passed; native MT5 confirmation remains required'}", ""]
    lines += ["## Final decision", "", "Only rows marked PASS are candidates for a native MT5 Every Tick EA confirmation. This report does not authorize live deployment or portfolio inclusion.", ""]
    return "\n".join(lines)


def main() -> int:
    metadata = download()
    results = []
    for canonical in SYMBOLS:
        print(f"Researching {canonical}...", flush=True)
        base, meta = load(canonical, metadata)
        row = select(canonical, base, meta)
        row["monte_carlo"] = monte_carlo(row["locked"]["trades_data"])
        row["promoted"], row["gate_failures"] = promotion(row)
        chart(row)
        results.append(row)
        dump(ROOT / "partial-results.json", {"results": results})
    payload = {
        "strategy": "SNB intraday FX session effect", "source": "https://www.snb.ch/en/publications/research/working-papers/2011/working_paper_2011_04",
        "generated_at": datetime.now(timezone.utc).isoformat(), "broker": metadata, "risk_per_trade_pct": 1.0,
        "cost_model": {"spread_floor_pips": SPREAD_FLOOR_PIPS, "commission_slippage_pips": COMMISSION_SLIPPAGE_PIPS, "stress_extra_pips": 1.0}, "results": results,
    }
    dump(ROOT / "results.json", payload)
    (ROOT / "FULL REPORT.md").write_text(report(payload), encoding="utf-8")
    print(report(payload))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
