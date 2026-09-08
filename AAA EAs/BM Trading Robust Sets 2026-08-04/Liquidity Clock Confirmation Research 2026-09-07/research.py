"""Liquidity-clock veto screen over existing native MT5 trade ledgers."""
from __future__ import annotations

from dataclasses import dataclass
import html
import json
import math
from pathlib import Path
import re

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parent
PACKAGE = ROOT.parent
STORE = PACKAGE.parent / "EA store"
CACHE = STORE / "data" / "evidence-cache" / "v1" / "products"
LVN = PACKAGE / "LVN Volume Profile Research 2026-09-04"
DEV = (pd.Timestamp("2023-09-01", tz="UTC"), pd.Timestamp("2025-09-01", tz="UTC"))
LOCKED = (pd.Timestamp("2025-09-01", tz="UTC"), pd.Timestamp("2026-09-01", tz="UTC"))
THRESHOLDS = (0.50, 0.65, 0.80, 0.90, 1.00, 1.10, 1.25, 1.50)
LOOKBACKS = (10, 20, 40)
TAG_RE = re.compile(r"<[^>]+>")


@dataclass(frozen=True)
class Strategy:
    family: str
    name: str
    symbol: str
    source: str
    trades: tuple[dict, ...]


def dump(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, allow_nan=False), encoding="utf-8")


def clean(value: str) -> str:
    return html.unescape(TAG_RE.sub("", value)).replace("\xa0", " ").strip()


def number(value: str) -> float:
    match = re.search(r"[-+]?\d[\d ]*(?:\.\d+)?", value.replace("%", ""))
    return float(match.group(0).replace(" ", "")) if match else 0.0


def read_report(path: Path) -> str:
    for encoding in ("utf-16", "utf-8-sig", "utf-8"):
        try:
            text = path.read_text(encoding=encoding)
        except UnicodeError:
            continue
        if "Initial Deposit" in text:
            return text
    return path.read_text(encoding="utf-8", errors="ignore")


def native_trades(path: Path, label: str) -> list[dict]:
    text = read_report(path)
    marker = text.lower().find("<b>deals</b>")
    if marker < 0:
        return []
    row_re = re.compile(r"<tr\b[^>]*>(.*?)</tr>", re.I | re.S)
    cell_re = re.compile(r"<td\b[^>]*>(.*?)</td>", re.I | re.S)
    entries: dict[str, list[dict]] = {}
    trades: list[dict] = []
    for row_html in row_re.findall(text[marker:]):
        cells = [clean(cell) for cell in cell_re.findall(row_html)]
        if len(cells) < 13 or not re.fullmatch(r"\d{4}\.\d{2}\.\d{2} \d{2}:\d{2}:\d{2}", cells[0]):
            continue
        symbol, deal_type, direction = cells[2], cells[3].lower(), cells[4].lower()
        if not symbol or deal_type not in {"buy", "sell"}:
            continue
        volume = number(cells[5])
        timestamp = cells[0].replace(".", "-", 2).replace(" ", "T", 1)
        costs = number(cells[8]) + number(cells[9]) + number(cells[10])
        if direction in {"in", "in/out"}:
            entries.setdefault(symbol, []).append(
                {"time": timestamp, "type": deal_type, "volume": volume, "remaining": volume, "costs": costs}
            )
            if direction == "in":
                continue
        if direction not in {"out", "out by", "in/out"}:
            continue
        remaining = volume
        queue = entries.get(symbol, [])
        while remaining > 1e-9 and queue:
            entry = queue[0]
            matched = min(remaining, float(entry["remaining"]))
            share = matched / volume if volume else 1.0
            entry_share = matched / float(entry["volume"]) if float(entry["volume"]) else 1.0
            net = costs * share + float(entry["costs"]) * entry_share
            trades.append(
                {
                    "number": len(trades) + 1,
                    "ea": label,
                    "symbol": symbol.upper(),
                    "side": "Long" if entry["type"] == "buy" else "Short",
                    "open_time": entry["time"],
                    "close_time": timestamp,
                    "net_profit": round(net, 2),
                }
            )
            entry["remaining"] = float(entry["remaining"]) - matched
            remaining -= matched
            if float(entry["remaining"]) <= 1e-9:
                queue.pop(0)
    return trades


def cached_trades(path: Path) -> list[dict]:
    return json.loads(path.read_text(encoding="utf-8"))


def discover_strategies() -> list[Strategy]:
    strategies: list[Strategy] = []
    lta = CACHE / "lta-volume-profile" / "standard" / "3y.trades.json"
    if lta.is_file():
        trades = cached_trades(lta)
        strategies.append(Strategy("LTA", "LTA XAU current", "XAUUSD", str(lta), tuple(trades)))

    for product in sorted(CACHE.iterdir()):
        if "orb" not in product.name:
            continue
        files = sorted(product.glob("*/3y.trades.json"))
        # Prefer standard; otherwise use the first available mode.
        files.sort(key=lambda path: (path.parent.name != "standard", str(path)))
        if not files:
            continue
        trades = cached_trades(files[0])
        if not trades:
            continue
        symbol = str(trades[0].get("symbol", "")).upper()
        strategies.append(Strategy("ORB", product.name, symbol, str(files[0]), tuple(trades)))

    audit = json.loads((LVN / "FINAL AUDIT.json").read_text(encoding="utf-8"))
    for symbol, payload in audit["symbols"].items():
        relative = payload["optimized_full"]["path"]
        report = LVN / Path(relative)
        trades = native_trades(report, f"LVN {symbol.upper()} optimized")
        if trades:
            strategies.append(Strategy("LVN", f"LVN {symbol.upper()} optimized", symbol.upper(), str(report), tuple(trades)))
    return strategies


def data_path(symbol: str) -> Path:
    roots = [
        PACKAGE / "Relative Value Pairs Research 2026-09-06" / "Data",
        PACKAGE / "Session VWAP Snapback Research 2026-09-06" / "Data",
        PACKAGE / "Volatility Compression Expansion Research 2026-09-06" / "Data",
    ]
    for folder in roots:
        path = folder / f"{symbol}-M5.npz"
        if path.is_file():
            return path
    raise FileNotFoundError(f"No M5 broker series for {symbol}")


def volume_series(symbol: str) -> pd.Series:
    rates = np.load(data_path(symbol))["rates"]
    index = pd.to_datetime(rates["time"], unit="s", utc=True)
    return pd.Series(rates["tick_volume"].astype(float), index=index, name=symbol).sort_index()


def add_clock_features(strategy: Strategy) -> pd.DataFrame:
    frame = pd.DataFrame(list(strategy.trades))
    frame["open_dt"] = pd.to_datetime(frame.open_time, utc=True)
    frame["close_dt"] = pd.to_datetime(frame.close_time, utc=True)
    volume = volume_series(strategy.symbol)
    index = volume.index
    values = volume.to_numpy()
    slots = index.hour * 60 + index.minute
    rows = []
    for timestamp in frame.open_dt:
        cutoff = timestamp - pd.Timedelta(minutes=5)
        location = int(index.searchsorted(cutoff, side="right") - 1)
        if location < 0:
            rows.append((np.nan, np.nan, np.nan, np.nan))
            continue
        current = float(values[location])
        slot = int(slots[location])
        prior_locations = np.flatnonzero((slots[:location] == slot))
        ratios = []
        for lookback in LOOKBACKS:
            history = values[prior_locations[-lookback:]]
            median = float(np.median(history)) if len(history) >= max(5, lookback // 2) else np.nan
            ratios.append(current / median if median and np.isfinite(median) else np.nan)
        rolling = values[max(0, location - 20):location]
        rolling_median = float(np.median(rolling)) if len(rolling) >= 10 else np.nan
        rows.append((*ratios, current / rolling_median if rolling_median else np.nan))
    frame[["clock10", "clock20", "clock40", "rolling20"]] = rows
    frame["family"] = strategy.family
    frame["strategy"] = strategy.name
    frame["symbol"] = strategy.symbol
    return frame


def metrics(frame: pd.DataFrame) -> dict:
    if frame.empty:
        return {"return_pct": 0.0, "profit_factor": 0.0, "win_rate": 0.0, "max_dd_pct": 0.0, "trades": 0, "sharpe": 0.0, "recovery": 0.0}
    pnl = frame.sort_values("close_dt").net_profit.to_numpy(float)
    curve = np.r_[10000.0, 10000.0 + np.cumsum(pnl)]
    gains = float(pnl[pnl > 0].sum())
    losses = -float(pnl[pnl < 0].sum())
    pf = gains / losses if losses else 99.0
    drawdown = float(np.max(1.0 - curve / np.maximum.accumulate(curve)) * 100.0)
    ret = float(pnl.sum() / 10000.0 * 100.0)
    daily = frame.assign(day=frame.close_dt.dt.floor("D")).groupby("day").net_profit.sum().sort_index()
    daily = (daily / 10000.0).resample("1D").sum()
    std = float(daily.std(ddof=1))
    sharpe = float(daily.mean() / std * math.sqrt(252)) if std > 0 else 0.0
    return {
        "return_pct": ret,
        "profit_factor": float(min(99.0, pf)),
        "win_rate": float(np.mean(pnl > 0) * 100.0),
        "max_dd_pct": drawdown,
        "trades": int(len(pnl)),
        "sharpe": sharpe,
        "recovery": ret / drawdown if drawdown > 0 else 0.0,
    }


def score(result: dict, baseline_trades: int) -> float:
    minimum = max(15, int(math.ceil(baseline_trades * 0.30)))
    if result["trades"] < minimum:
        return -10000.0 + result["trades"]
    if result["return_pct"] <= 0 or result["profit_factor"] < 1.0:
        return -1000.0 - result["max_dd_pct"]
    return (
        5.0 * math.log1p(result["return_pct"])
        + 5.0 * math.log(min(3.0, result["profit_factor"]))
        + 2.0 * max(-3.0, min(3.0, result["sharpe"]))
        + 2.0 * max(-3.0, min(8.0, result["recovery"]))
        + 0.01 * result["win_rate"]
        - 0.5 * result["max_dd_pct"]
    )


def select_filter(frame: pd.DataFrame):
    dev = frame[(frame.open_dt >= DEV[0]) & (frame.open_dt < DEV[1])].copy()
    baseline = metrics(dev)
    rows = [{"lookback": 0, "threshold": 0.0, "name": "baseline", **baseline, "score": score(baseline, baseline["trades"])}]
    for lookback in LOOKBACKS:
        column = f"clock{lookback}"
        for threshold in THRESHOLDS:
            selected = dev[dev[column] >= threshold]
            result = metrics(selected)
            rows.append(
                {"lookback": lookback, "threshold": threshold, "name": f"clock{lookback}>={threshold:.2f}", **result, "score": score(result, baseline["trades"])}
            )
    chosen = max(rows, key=lambda row: row["score"])
    return chosen, rows


def apply_filter(frame: pd.DataFrame, chosen: dict, period: tuple[pd.Timestamp, pd.Timestamp]) -> pd.DataFrame:
    sample = frame[(frame.open_dt >= period[0]) & (frame.open_dt < period[1])].copy()
    if chosen["lookback"] == 0:
        return sample
    return sample[sample[f"clock{int(chosen['lookback'])}"] >= float(chosen["threshold"])]


def monte_carlo(frame: pd.DataFrame, paths: int = 5000, seed: int = 20260907) -> dict:
    pnl = frame.sort_values("close_dt").net_profit.to_numpy(float) / 10000.0
    if len(pnl) == 0:
        return {"paths": paths, "return_p5": 0.0, "return_median": 0.0, "dd_p95": 0.0, "profit_probability": 0.0}
    rng = np.random.default_rng(seed)
    block = min(5, len(pnl))
    blocks = int(math.ceil(len(pnl) / block))
    starts = rng.integers(0, len(pnl), size=(paths, blocks))
    indices = (starts[:, :, None] + np.arange(block)) % len(pnl)
    samples = pnl[indices.reshape(paths, -1)[:, :len(pnl)]]
    curves = 1.0 + np.cumsum(samples, axis=1)
    curves = np.c_[np.ones(paths), curves]
    returns = (curves[:, -1] - 1.0) * 100.0
    drawdowns = np.max(1.0 - curves / np.maximum.accumulate(curves, axis=1), axis=1) * 100.0
    return {
        "paths": paths,
        "return_p5": float(np.percentile(returns, 5)),
        "return_median": float(np.median(returns)),
        "return_p95": float(np.percentile(returns, 95)),
        "dd_p95": float(np.percentile(drawdowns, 95)),
        "profit_probability": float(np.mean(returns > 0) * 100.0),
    }


def make_charts(results: list[dict], screens: list[dict]) -> None:
    charts = ROOT / "Charts"
    charts.mkdir(exist_ok=True)
    count = len(results)
    fig, axes = plt.subplots(count, 2, figsize=(14, max(4, count * 3.0)), constrained_layout=True)
    if count == 1:
        axes = np.array([axes])
    for i, result in enumerate(results):
        frame = pd.DataFrame(result["locked_equity"])
        if not frame.empty:
            axes[i, 0].plot(pd.to_datetime(frame.date), frame.baseline, label="baseline", color="#5794e6")
            axes[i, 0].plot(pd.to_datetime(frame.date), frame.selected, label="clock filter", color="#25b887")
        axes[i, 0].set_title(result["name"] + " — locked equity")
        axes[i, 0].legend(loc="best")
        screen = pd.DataFrame([row for row in screens if row["strategy"] == result["name"] and row["lookback"] > 0])
        for lookback, group in screen.groupby("lookback"):
            axes[i, 1].plot(group.threshold, group.profit_factor, marker="o", label=f"{int(lookback)} slots")
        axes[i, 1].axhline(1.0, color="#d85b67", linewidth=0.8)
        axes[i, 1].set_title(result["name"] + " — development PF screen")
        axes[i, 1].legend(loc="best")
        for axis in axes[i]:
            axis.grid(alpha=0.2)
    fig.savefig(charts / "all-strategies.png", dpi=150)
    plt.close(fig)

    summary = pd.DataFrame(results)
    x = np.arange(len(summary))
    fig, axes = plt.subplots(2, 2, figsize=(16, 10), constrained_layout=True)
    for axis, key, title in (
        (axes[0, 0], "baseline_locked_return", "Locked return: baseline vs clock"),
        (axes[0, 1], "baseline_locked_pf", "Locked PF: baseline vs clock"),
        (axes[1, 0], "baseline_locked_dd", "Locked DD: baseline vs clock"),
        (axes[1, 1], "baseline_locked_trades", "Locked trades: baseline vs clock"),
    ):
        selected_key = key.replace("baseline_", "selected_")
        axis.bar(x - 0.2, summary[key], width=0.4, label="baseline", color="#5794e6")
        axis.bar(x + 0.2, summary[selected_key], width=0.4, label="clock", color="#25b887")
        axis.set_title(title)
        axis.set_xticks(x, summary.name, rotation=65, ha="right")
        axis.legend()
        axis.grid(axis="y", alpha=0.2)
    fig.savefig(charts / "locked-comparison.png", dpi=150)
    plt.close(fig)


def equity_comparison(baseline: pd.DataFrame, selected: pd.DataFrame) -> list[dict]:
    dates = sorted(set(baseline.close_dt.dt.floor("D")) | set(selected.close_dt.dt.floor("D")))
    if not dates:
        return []
    baseline_daily = baseline.groupby(baseline.close_dt.dt.floor("D")).net_profit.sum()
    selected_daily = selected.groupby(selected.close_dt.dt.floor("D")).net_profit.sum()
    b = 10000.0
    s = 10000.0
    rows = []
    for date in dates:
        b += float(baseline_daily.get(date, 0.0))
        s += float(selected_daily.get(date, 0.0))
        rows.append({"date": date.isoformat(), "baseline": b, "selected": s})
    return rows


def main() -> None:
    strategies = discover_strategies()
    results = []
    screens = []
    enriched_folder = ROOT / "Enriched Ledgers"
    enriched_folder.mkdir(exist_ok=True)
    print(f"Discovered {len(strategies)} native strategy ledgers", flush=True)
    for number_, strategy in enumerate(strategies, 1):
        frame = add_clock_features(strategy)
        safe_name = re.sub(r"[^a-z0-9]+", "-", strategy.name.lower()).strip("-")
        frame.to_csv(enriched_folder / f"{safe_name}.csv", index=False)
        chosen, rows = select_filter(frame)
        for row in rows:
            screens.append({"family": strategy.family, "strategy": strategy.name, "symbol": strategy.symbol, **row})
        locked_baseline_frame = apply_filter(frame, {"lookback": 0}, LOCKED)
        locked_selected_frame = apply_filter(frame, chosen, LOCKED)
        baseline_locked = metrics(locked_baseline_frame)
        selected_locked = metrics(locked_selected_frame)
        mc = monte_carlo(locked_selected_frame)
        retention = selected_locked["trades"] / baseline_locked["trades"] * 100.0 if baseline_locked["trades"] else 0.0
        passes = (
            int(chosen["lookback"]) > 0
            and selected_locked["trades"] >= 20
            and retention >= 30.0
            and selected_locked["return_pct"] >= baseline_locked["return_pct"]
            and selected_locked["profit_factor"] > baseline_locked["profit_factor"]
            and selected_locked["max_dd_pct"] <= baseline_locked["max_dd_pct"]
            and selected_locked["profit_factor"] >= 1.20
            and mc["return_p5"] > 0
        )
        result = {
            "family": strategy.family,
            "name": strategy.name,
            "symbol": strategy.symbol,
            "source": strategy.source,
            "selected_filter": chosen["name"],
            "development_baseline": metrics(frame[(frame.open_dt >= DEV[0]) & (frame.open_dt < DEV[1])]),
            "development_selected": {key: chosen[key] for key in ("return_pct", "profit_factor", "win_rate", "max_dd_pct", "trades", "sharpe", "recovery")},
            "baseline_locked": baseline_locked,
            "selected_locked": selected_locked,
            "retention_pct": retention,
            "monte_carlo": mc,
            "passes_preliminary_gate": passes,
            "locked_equity": equity_comparison(locked_baseline_frame, locked_selected_frame),
        }
        results.append(result)
        print(f"{number_}/{len(strategies)} {strategy.name}: {chosen['name']} locked PF {selected_locked['profit_factor']:.2f} gate {passes}", flush=True)

    pd.DataFrame(screens).to_csv(ROOT / "all-development-screens.csv", index=False)
    summary_rows = []
    for result in results:
        summary_rows.append(
            {
                "family": result["family"],
                "name": result["name"],
                "symbol": result["symbol"],
                "filter": result["selected_filter"],
                "baseline_locked_return": result["baseline_locked"]["return_pct"],
                "selected_locked_return": result["selected_locked"]["return_pct"],
                "baseline_locked_pf": result["baseline_locked"]["profit_factor"],
                "selected_locked_pf": result["selected_locked"]["profit_factor"],
                "baseline_locked_win_rate": result["baseline_locked"]["win_rate"],
                "selected_locked_win_rate": result["selected_locked"]["win_rate"],
                "baseline_locked_dd": result["baseline_locked"]["max_dd_pct"],
                "selected_locked_dd": result["selected_locked"]["max_dd_pct"],
                "baseline_locked_trades": result["baseline_locked"]["trades"],
                "selected_locked_trades": result["selected_locked"]["trades"],
                "selected_locked_sharpe": result["selected_locked"]["sharpe"],
                "selected_locked_recovery": result["selected_locked"]["recovery"],
                "mc_return_p5": result["monte_carlo"]["return_p5"],
                "passes": result["passes_preliminary_gate"],
                "locked_equity": result["locked_equity"],
            }
        )
    pd.DataFrame(summary_rows).to_csv(ROOT / "locked-summary.csv", index=False)
    dump(ROOT / "results.json", {"results": results, "production_changed": False})
    make_charts(summary_rows, screens)

    passing = [row for row in summary_rows if row["passes"]]
    lines = [
        "# Step 3 — Liquidity-Clock Confirmation",
        "",
        f"**Decision: {'NATIVE CONFIRMATION REQUIRED' if passing else 'REJECT / DO NOT ADD'}. No production file was changed.**",
        "",
        f"The screen evaluated {len(strategies)} existing native strategy ledgers. Each filter was selected on development data only, then opened once on the locked last year.",
        "",
        "| Family / setup | Clock filter | Locked return base → filter | PF base → filter | Win rate base → filter | DD base → filter | Trades base → filter | Sharpe | Recovery | MC P5 | Gate |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---|",
    ]
    for row in summary_rows:
        lines.append(
            f"| {row['family']} / {row['name']} | {row['filter']} | {row['baseline_locked_return']:+.2f}% → {row['selected_locked_return']:+.2f}% | "
            f"{row['baseline_locked_pf']:.2f} → {row['selected_locked_pf']:.2f} | {row['baseline_locked_win_rate']:.2f}% → {row['selected_locked_win_rate']:.2f}% | "
            f"{row['baseline_locked_dd']:.2f}% → {row['selected_locked_dd']:.2f}% | {row['baseline_locked_trades']} → {row['selected_locked_trades']} | "
            f"{row['selected_locked_sharpe']:.2f} | {row['selected_locked_recovery']:.2f} | {row['mc_return_p5']:+.2f}% | {'PASS' if row['passes'] else 'FAIL'} |"
        )
    lines += [
        "",
        "![Locked comparison](Charts/locked-comparison.png)",
        "",
        "## Interpretation",
        "",
        f"{len(passing)} of {len(strategies)} configurations passed the deliberately strict preliminary gate.",
        "A pass is not permission to deploy: the filter must next be implemented in a copied EA and rerun natively because a ledger veto cannot reconstruct additional signals that may occur after a skipped position.",
        "Broker tick count is a quote-activity proxy, not centralized exchange volume.",
        "",
        "![Every strategy and setting](Charts/all-strategies.png)",
    ]
    (ROOT / "REPORT.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    checks = [
        (len(strategies) >= 3, "LTA, LVN and ORB ledgers discovered"),
        (all(row["baseline_locked_trades"] >= row["selected_locked_trades"] for row in summary_rows), "filters are veto-only"),
        (all(row["mc_return_p5"] is not None for row in summary_rows), "Monte Carlo calculated"),
        ((ROOT / "Charts" / "locked-comparison.png").is_file(), "comparison graph generated"),
        (not any(path.suffix.lower() in (".mq5", ".ex5", ".set", ".bat") for path in ROOT.rglob("*")), "no deployment artifacts created"),
    ]
    (ROOT / "VERIFICATION.txt").write_text(
        "\n".join([f"{'PASS' if ok else 'FAIL'} {label}" for ok, label in checks] + [f"SUMMARY {sum(ok for ok, _ in checks)}/{len(checks)} checks passed"]) + "\n",
        encoding="utf-8",
    )
    dump(ROOT / "progress.json", {"step": 3, "title": "Liquidity-Clock Confirmation", "status": "awaiting-review", "passing_candidates": len(passing), "production_changed": False})
    print(f"COMPLETE passing={len(passing)} total={len(strategies)}", flush=True)


if __name__ == "__main__":
    main()
