"""Causal Markov regime overlay on frozen native-MT5 strategy ledgers."""
from __future__ import annotations

from dataclasses import dataclass, asdict
from pathlib import Path
import itertools
import json
import math

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parent
PACKAGE = ROOT.parent
DATA = PACKAGE / "Volatility Compression Expansion Research 2026-09-06" / "Data"
TREND = PACKAGE / "Slow Multi Asset Trend Research 2026-09-06" / "Native"
SNAPBACK = PACKAGE / "Session VWAP Snapback Research 2026-09-06" / "Native"
CHARTS = ROOT / "Charts"
SYMBOLS = ("XAUUSD", "XAGUSD", "BTCUSD", "USTEC")
TRAIN = (pd.Timestamp("2023-09-01", tz="UTC"), pd.Timestamp("2024-09-01", tz="UTC"))
VALIDATION = (pd.Timestamp("2024-09-01", tz="UTC"), pd.Timestamp("2025-09-01", tz="UTC"))
LOCKED = (pd.Timestamp("2025-09-01", tz="UTC"), pd.Timestamp("2026-09-01", tz="UTC"))
FULL = (TRAIN[0], LOCKED[1])


@dataclass(frozen=True)
class Config:
    mode: str
    window: int
    threshold: float
    history: int
    signal_gate: float
    sideways_probability: float


def dump(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, allow_nan=False), encoding="utf-8")


def load_prices(symbol: str) -> pd.Series:
    rates = np.load(DATA / f"{symbol}-M5.npz")["rates"]
    index = pd.to_datetime(rates["time"], unit="s", utc=True)
    close = pd.Series(rates["close"].astype(float), index=index)
    close = close[~close.index.duplicated(keep="last")].sort_index()
    return close.resample("1D").last().dropna()


def export_daily_csv(symbol: str, close: pd.Series) -> None:
    frame = pd.DataFrame({"date": close.index.strftime("%Y-%m-%d"), "close": close.values})
    path = ROOT / "Data" / f"{symbol}-D1.csv"
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(path, index=False)


def load_ledger(path: Path, leg: str) -> list[dict]:
    if not path.exists():
        return []
    out = []
    for raw in json.loads(path.read_text(encoding="utf-8")):
        row = dict(raw)
        row["entry"] = pd.Timestamp(row["entry_time"], tz="UTC")
        row["exit"] = pd.Timestamp(row["exit_time"], tz="UTC")
        row["side_sign"] = 1 if row["side"].lower() in ("buy", "long") else -1
        row["leg"] = leg
        out.append(row)
    return out


def ledgers(symbol: str, stage: str) -> tuple[list[dict], list[dict]]:
    lower = symbol.lower()
    if stage == "full":
        momentum = TREND / f"{lower}-selected-full-model1" / "trades.json"
        snapback = SNAPBACK / f"{lower}-frozen-full-model1" / "trades.json"
    else:
        momentum = TREND / f"{lower}-selected-test-model0" / "trades.json"
        snapback = SNAPBACK / f"{lower}-frozen-locked-model0" / "trades.json"
    return load_ledger(momentum, "momentum"), load_ledger(snapback, "mean-reversion")


def labels(close: pd.Series, window: int, threshold: float) -> pd.Series:
    change = close / close.shift(window) - 1.0
    state = pd.Series(np.where(change > threshold, 2, np.where(change < -threshold, 0, 1)), index=close.index)
    return state.where(change.notna()).dropna().astype(int)


def forecasts(close: pd.Series, config: Config) -> pd.DataFrame:
    state = labels(close, config.window, config.threshold)
    rows = []
    values = state.to_numpy(dtype=int)
    dates = state.index
    minimum = max(60, min(config.history, 126))
    for i in range(minimum, len(values)):
        start = max(0, i - config.history) if config.history < 9999 else 0
        history = values[start:i + 1]
        # The last known state is the forecast origin. Deliberately exclude the
        # transition into it, matching the production SafeRegimeFilter.
        counts = np.ones((3, 3), dtype=float)
        for j in range(len(history) - 2):
            counts[history[j], history[j + 1]] += 1.0
        matrix = counts / counts.sum(axis=1, keepdims=True)
        current = int(history[-1])
        probability = matrix[current]
        rows.append((dates[i], current, probability[0], probability[1], probability[2], probability[2] - probability[0]))
    return pd.DataFrame(rows, columns=("date", "state", "p_bear", "p_sideways", "p_bull", "signal")).set_index("date")


def attach_forecast(trades: list[dict], forecast: pd.DataFrame) -> list[dict]:
    if forecast.empty:
        return []
    dates = forecast.index.values
    out = []
    for trade in trades:
        # Previous completed daily bar only: an entry on D uses forecast from D-1.
        cutoff = (trade["entry"].normalize() - pd.Timedelta(days=1)).to_datetime64()
        i = int(np.searchsorted(dates, cutoff, side="right") - 1)
        if i < 0:
            continue
        f = forecast.iloc[i]
        out.append(trade | {"state": int(f.state), "p_bear": float(f.p_bear), "p_sideways": float(f.p_sideways), "p_bull": float(f.p_bull), "signal": float(f.signal)})
    return out


def gate(trade: dict, config: Config) -> bool:
    side = trade["side_sign"]
    if config.mode == "baseline":
        return trade["leg"] == "momentum"
    if config.mode == "directional-signal":
        return trade["leg"] == "momentum" and side * trade["signal"] > config.signal_gate
    if config.mode == "directional-state":
        return trade["leg"] == "momentum" and ((side > 0 and trade["state"] == 2) or (side < 0 and trade["state"] == 0))
    if config.mode == "flat-sideways":
        directional = trade["state"] != 1 and side * trade["signal"] > config.signal_gate
        return trade["leg"] == "momentum" and directional
    if trade["leg"] == "momentum":
        return trade["state"] != 1 and side * trade["signal"] > config.signal_gate
    return trade["state"] == 1 and trade["p_sideways"] >= config.sideways_probability


def select_non_overlapping(trades: list[dict], config: Config, period: tuple[pd.Timestamp, pd.Timestamp]) -> list[dict]:
    candidates = [x for x in trades if period[0] <= x["entry"] < period[1] and gate(x, config)]
    candidates.sort(key=lambda x: (x["entry"], 0 if x["leg"] == "momentum" else 1))
    selected = []
    available = period[0]
    for trade in candidates:
        if trade["entry"] < available:
            continue
        selected.append(trade)
        available = trade["exit"]
    return selected


def metrics(trades: list[dict]) -> dict:
    if not trades:
        return dict(return_pct=0.0, profit_factor=0.0, win_rate=0.0, max_dd_pct=0.0, trades=0, sharpe=0.0, recovery=0.0, avg_win_r=0.0, avg_loss_r=0.0, momentum_trades=0, mean_reversion_trades=0)
    fractions = np.array([float(x["return_fraction"]) for x in trades], dtype=float)
    equity = np.r_[1.0, np.cumprod(1.0 + fractions)]
    pnl = np.diff(equity)
    gains, losses = pnl[pnl > 0].sum(), -pnl[pnl < 0].sum()
    dd = float(np.max(1.0 - equity / np.maximum.accumulate(equity)) * 100.0)
    ret = float((equity[-1] - 1.0) * 100.0)
    daily = pd.Series(fractions, index=pd.DatetimeIndex([x["exit"] for x in trades])).groupby(level=0).sum().resample("1D").sum()
    std = float(daily.std(ddof=1))
    sharpe = float(daily.mean() / std * math.sqrt(252.0)) if std > 0 else 0.0
    risk_r = fractions / 0.01
    return dict(
        return_pct=ret,
        profit_factor=float(gains / losses) if losses > 0 else 99.0,
        win_rate=float(np.mean(fractions > 0) * 100.0),
        max_dd_pct=dd,
        trades=len(trades),
        sharpe=sharpe,
        recovery=float(ret / dd) if dd else 0.0,
        avg_win_r=float(risk_r[risk_r > 0].mean()) if np.any(risk_r > 0) else 0.0,
        avg_loss_r=float(risk_r[risk_r < 0].mean()) if np.any(risk_r < 0) else 0.0,
        momentum_trades=sum(x["leg"] == "momentum" for x in trades),
        mean_reversion_trades=sum(x["leg"] == "mean-reversion" for x in trades),
    )


def score(train: dict, validation: dict) -> float:
    minimum_trades = min(train["trades"], validation["trades"])
    if minimum_trades < 8:
        return -1000.0 + minimum_trades
    minimum_return = min(train["return_pct"], validation["return_pct"])
    minimum_pf = min(train["profit_factor"], validation["profit_factor"])
    value = 0.45 * minimum_return + 8.0 * math.log(max(0.05, min(3.0, minimum_pf)))
    value += 1.5 * min(train["sharpe"], validation["sharpe"])
    value += min(train["recovery"], validation["recovery"])
    value -= 0.25 * max(train["max_dd_pct"], validation["max_dd_pct"])
    value -= max(0, 15 - minimum_trades) * 0.75
    if minimum_return <= 0:
        value -= 20.0 + abs(minimum_return)
    if minimum_pf < 1.0:
        value -= 20.0 * (1.0 - minimum_pf)
    return float(value)


def monte_carlo(trades: list[dict], paths: int = 10000, seed: int = 6092026) -> dict:
    values = np.array([float(x["return_fraction"]) for x in trades], dtype=float)
    if len(values) == 0:
        return dict(paths=paths, profitable_probability=0.0, return_p5=0.0, return_median=0.0, return_p95=0.0, dd_median=0.0, dd_p95=0.0)
    rng = np.random.default_rng(seed)
    returns, dds = np.empty(paths), np.empty(paths)
    # Very small samples cannot support a five-trade block bootstrap: the only
    # possible block would be the original ledger itself and would falsely
    # report 100% certainty. Fall back to iid resampling below ten trades.
    block = 1 if len(values) < 10 else 5
    for i in range(paths):
        starts = rng.integers(0, max(1, len(values) - block + 1), size=math.ceil(len(values) / block))
        sample = np.concatenate([values[s:s + block] for s in starts])[:len(values)]
        curve = np.r_[1.0, np.cumprod(1.0 + sample)]
        returns[i] = (curve[-1] - 1.0) * 100.0
        dds[i] = np.max(1.0 - curve / np.maximum.accumulate(curve)) * 100.0
    return dict(paths=paths, profitable_probability=float(np.mean(returns > 0) * 100.0), return_p5=float(np.percentile(returns, 5)), return_median=float(np.median(returns)), return_p95=float(np.percentile(returns, 95)), dd_median=float(np.median(dds)), dd_p95=float(np.percentile(dds, 95)))


def public_trade(trade: dict) -> dict:
    return {key: (value.isoformat() if isinstance(value, pd.Timestamp) else value) for key, value in trade.items() if key not in ("entry", "exit")}


def configurations(has_snapback: bool):
    yield Config("baseline", 20, 0.05, 252, 0.05, 0.40)
    modes = ("directional-signal", "directional-state", "flat-sideways") + (("regime-switch",) if has_snapback else ())
    for mode, window, threshold, history, signal_gate, sideways in itertools.product(
        modes, (10, 20, 40, 60), (0.02, 0.03, 0.05, 0.08), (126, 252, 504, 9999), (0.0, 0.03, 0.05, 0.10), (0.34, 0.40, 0.50)
    ):
        if mode != "regime-switch" and sideways != 0.34:
            continue
        yield Config(mode, window, threshold, history, signal_gate, sideways)


def analyse_symbol(symbol: str) -> tuple[dict, list[dict]]:
    close = load_prices(symbol)
    export_daily_csv(symbol, close)
    momentum_full, snapback_full = ledgers(symbol, "full")
    rows, cached = [], {}
    best = None
    best_by_mode = {}
    for config in configurations(bool(snapback_full)):
        key = (config.window, config.threshold, config.history)
        if key not in cached:
            cached[key] = forecasts(close, config)
        forecast = cached[key]
        attached = attach_forecast(momentum_full + snapback_full, forecast)
        train_trades = select_non_overlapping(attached, config, TRAIN)
        validation_trades = select_non_overlapping(attached, config, VALIDATION)
        train_result, validation_result = metrics(train_trades), metrics(validation_trades)
        value = score(train_result, validation_result)
        row = dict(symbol=symbol, config=json.dumps(asdict(config), sort_keys=True), score=value, **{f"train_{k}": v for k, v in train_result.items()}, **{f"validation_{k}": v for k, v in validation_result.items()})
        rows.append(row)
        current = best_by_mode.get(config.mode)
        if current is None or value > current[0]:
            best_by_mode[config.mode] = (value, config, train_result, validation_result)
        if config.mode != "baseline" and (best is None or value > best[0]):
            best = (value, config)
    baseline = next(config for config in configurations(bool(snapback_full)) if config.mode == "baseline")
    selected = best[1]
    # Locked trade data comes from the higher-fidelity MT5 Every Tick/random-delay run.
    momentum_locked, snapback_locked = ledgers(symbol, "locked")
    locked_forecast = forecasts(close, selected)
    baseline_locked_forecast = forecasts(close, baseline)
    selected_locked = select_non_overlapping(attach_forecast(momentum_locked + snapback_locked, locked_forecast), selected, LOCKED)
    baseline_locked = select_non_overlapping(attach_forecast(momentum_locked, baseline_locked_forecast), baseline, LOCKED)
    full_selected = select_non_overlapping(attach_forecast(momentum_full + snapback_full, locked_forecast), selected, FULL)
    mode_comparison = {}
    for mode, (value, mode_config, train_result, validation_result) in best_by_mode.items():
        mode_forecast = forecasts(close, mode_config)
        mode_locked = select_non_overlapping(attach_forecast(momentum_locked + snapback_locked, mode_forecast), mode_config, LOCKED)
        mode_comparison[mode] = dict(config=asdict(mode_config), score=value, train=train_result, validation=validation_result, locked=metrics(mode_locked))
    result = dict(
        selected=asdict(selected),
        baseline_locked=metrics(baseline_locked),
        selected_locked=metrics(selected_locked),
        selected_full=metrics(full_selected),
        monte_carlo=monte_carlo(selected_locked),
        best_by_mode=mode_comparison,
        has_validated_mean_reversion_leg=bool(snapback_full),
        selected_locked_trades=[public_trade(x) for x in selected_locked],
        promotion_pass=False,
    )
    b, s = result["baseline_locked"], result["selected_locked"]
    result["promotion_pass"] = bool(s["return_pct"] > 0 and s["profit_factor"] >= 1.20 and s["trades"] >= 20 and s["max_dd_pct"] <= b["max_dd_pct"] and result["monte_carlo"]["return_p5"] > 0)
    return result, rows


def plot(results: dict) -> None:
    CHARTS.mkdir(parents=True, exist_ok=True)
    symbols = list(results)
    base = [results[x]["baseline_locked"] for x in symbols]
    selected = [results[x]["selected_locked"] for x in symbols]
    fig, axes = plt.subplots(2, 2, figsize=(15, 9))
    x = np.arange(len(symbols)); width = 0.36
    for ax, field, title in (
        (axes[0, 0], "return_pct", "Locked return (%)"),
        (axes[0, 1], "profit_factor", "Locked profit factor"),
        (axes[1, 0], "win_rate", "Locked win rate (%)"),
        (axes[1, 1], "max_dd_pct", "Locked max drawdown (%)"),
    ):
        ax.bar(x - width / 2, [r[field] for r in base], width, label="Frozen baseline", color="#64748b")
        ax.bar(x + width / 2, [r[field] for r in selected], width, label="Selected regime overlay", color="#34d399")
        ax.set_xticks(x, symbols); ax.set_title(title); ax.grid(axis="y", alpha=.2)
    axes[0, 0].legend()
    fig.suptitle("Volatility-Regime Switch — untouched 2025-09 to 2026-09 evidence")
    fig.tight_layout(); fig.savefig(CHARTS / "locked-comparison.png", dpi=180); plt.close(fig)

    fig, ax = plt.subplots(figsize=(13, 7))
    for symbol, result in results.items():
        trades = result["selected_locked_trades"]
        if not trades:
            continue
        times = [pd.Timestamp(x["exit_time"]) for x in trades]
        curve = 10000 * np.cumprod(1.0 + np.array([x["return_fraction"] for x in trades]))
        ax.plot(times, curve, lw=1.6, label=symbol)
    ax.axhline(10000, color="#64748b", ls="--", lw=.8)
    ax.set_title("Selected locked-year equity — 1% risk per accepted trade")
    ax.set_ylabel("USD"); ax.grid(alpha=.2); ax.legend(); fig.tight_layout()
    fig.savefig(CHARTS / "locked-equity.png", dpi=180); plt.close(fig)


def main() -> int:
    results, rows = {}, []
    for symbol in SYMBOLS:
        print("REGIME SCREEN", symbol, flush=True)
        result, symbol_rows = analyse_symbol(symbol)
        results[symbol] = result; rows.extend(symbol_rows)
        dump(ROOT / "selection-lock.json", {key: value["selected"] for key, value in results.items()})
        print("LOCKED", symbol, result["selected"], result["selected_locked"], "PROMOTE", result["promotion_pass"], flush=True)
    dump(ROOT / "results.json", results)
    pd.DataFrame(rows).to_csv(ROOT / "all-screen-results.csv", index=False)
    plot(results)
    progress = dict(step=1, title="Volatility-Regime Switch", status="complete", fixed_risk_percent=1.0, symbols=list(SYMBOLS), xag_mandatory=True, configurations=len(rows), locked_first_read_after_selection=True, monte_carlo_paths=10000, production_changed=False, promoted=[s for s in SYMBOLS if results[s]["promotion_pass"]])
    dump(ROOT / "progress.json", progress)
    print("COMPLETE", progress, flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
