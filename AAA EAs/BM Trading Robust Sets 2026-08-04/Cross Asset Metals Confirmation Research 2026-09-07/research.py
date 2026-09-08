from __future__ import annotations

import json
import math
import shutil
from dataclasses import dataclass
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


HERE = Path(__file__).resolve().parent
PACKAGE = HERE.parent
STORE = PACKAGE.parent / "EA store"
CACHE = STORE / "data" / "evidence-cache" / "v1" / "products"
REGIME_DATA = PACKAGE / "Regime Switch Overlay Research 2026-09-06" / "Data"
DATA = HERE / "Data"
CHARTS = HERE / "Charts"

START = pd.Timestamp("2023-09-01")
LOCK = pd.Timestamp("2025-09-01")
END = pd.Timestamp("2026-09-01")
RISK = 0.01
MAX_OPEN = 4
SEED = 290907

LEDGERS = {
    "lta-volume-profile": "LTA Volume Profile",
    "engineered-liquidity-xau": "Engineered Liquidity XAU",
    "orb-volume-profile": "ORB Volume Profile",
    "orb-volume-profile-high-win-0-75r": "ORB High-Win 0.75R",
    "orb-volume-profile-volume-confirmed": "ORB Volume-Confirmed",
    "xau-orb-new-york-m30": "XAU ORB New York M30",
    "xau-orb-london-ny-overlap-m30": "XAU ORB London–NY M30",
    "asia-breakout": "Asia Breakout",
    "ema3": "EMA3",
    "xau-weakness": "XAU Weakness",
    "xau-rsi-vwap": "XAU RSI VWAP",
    "xau-trend-progression": "XAU Trend Progression",
    "xau-elliott-wave-1-2-3": "XAU Elliott Wave 1-2-3",
    "xau-slow-trend": "XAU Slow Trend",
    "xag-session-vwap-snapback": "XAG Session VWAP Snapback",
}


@dataclass(frozen=True)
class Rule:
    name: str
    family: str
    a: float = 0
    b: float = 0


def read_ledger(slug: str, label: str) -> pd.DataFrame:
    paths = [
        CACHE / slug / "standard" / "5y.trades.json",
        CACHE / slug / "safe" / "5y.trades.json",
    ]
    path = next((p for p in paths if p.exists()), None)
    if path is None:
        raise FileNotFoundError(f"No 5y native ledger for {slug}")
    rows = json.loads(path.read_text(encoding="utf-8"))
    df = pd.DataFrame(rows)
    if df.empty:
        raise ValueError(f"Empty ledger for {slug}")
    df["open_time"] = pd.to_datetime(df["open_time"], errors="coerce")
    df["close_time"] = pd.to_datetime(df["close_time"], errors="coerce")
    df["r"] = pd.to_numeric(df.get("estimated_r"), errors="coerce")
    fallback = pd.to_numeric(df.get("net_profit"), errors="coerce") / pd.to_numeric(
        df.get("estimated_risk_cash"), errors="coerce"
    ).replace(0, np.nan)
    df["r"] = df["r"].fillna(fallback)
    df["side_sign"] = df["side"].astype(str).str.lower().map({"long": 1, "buy": 1, "short": -1, "sell": -1})
    df["slug"] = slug
    df["strategy"] = label
    cols = ["slug", "strategy", "symbol", "side", "side_sign", "open_time", "close_time", "r", "net_profit"]
    df = df[cols].dropna(subset=["open_time", "close_time", "r", "side_sign"])
    return df[(df.open_time >= START) & (df.open_time < END)].copy()


def load_prices() -> pd.DataFrame:
    DATA.mkdir(parents=True, exist_ok=True)
    parts = []
    for symbol in ("XAUUSD", "XAGUSD"):
        src = REGIME_DATA / f"{symbol}-D1.csv"
        dst = DATA / src.name
        shutil.copy2(src, dst)
        x = pd.read_csv(dst)
        x["date"] = pd.to_datetime(x["date"]).astype("datetime64[ns]")
        x = x[["date", "close"]].rename(columns={"close": symbol.lower()})
        parts.append(x)
    px = parts[0].merge(parts[1], on="date", how="inner").sort_values("date").reset_index(drop=True)
    for s in ("xauusd", "xagusd"):
        px[f"{s}_r1"] = np.log(px[s]).diff()
        for n in (1, 3, 5, 10, 20, 40, 60):
            px[f"{s}_ret{n}"] = np.log(px[s]).diff(n)
            vol = px[f"{s}_r1"].rolling(60, min_periods=20).std() * math.sqrt(n)
            px[f"{s}_imp{n}"] = px[f"{s}_ret{n}"] / vol.replace(0, np.nan)
    for n in (20, 40, 60):
        px[f"corr{n}"] = px["xauusd_r1"].rolling(n, min_periods=max(10, n // 2)).corr(px["xagusd_r1"])
        ratio = np.log(px["xauusd"] / px["xagusd"])
        mu = ratio.rolling(n, min_periods=max(10, n // 2)).mean()
        sd = ratio.rolling(n, min_periods=max(10, n // 2)).std()
        px[f"ratio_z{n}"] = (ratio - mu) / sd.replace(0, np.nan)
    return px


def attach_features(trades: pd.DataFrame, px: pd.DataFrame) -> pd.DataFrame:
    left = trades.sort_values("open_time").copy()
    left["lookup"] = (left["open_time"].dt.normalize() - pd.Timedelta(nanoseconds=1)).astype("datetime64[ns]")
    right = px.rename(columns={"date": "feature_date"}).sort_values("feature_date")
    right["feature_date"] = right["feature_date"].astype("datetime64[ns]")
    out = pd.merge_asof(left, right, left_on="lookup", right_on="feature_date", direction="backward")
    xau = out.symbol.eq("XAUUSD")
    for n in (1, 3, 5, 10, 20, 40, 60):
        out[f"own_ret{n}"] = np.where(xau, out[f"xauusd_ret{n}"], out[f"xagusd_ret{n}"])
        out[f"peer_ret{n}"] = np.where(xau, out[f"xagusd_ret{n}"], out[f"xauusd_ret{n}"])
        out[f"peer_imp{n}"] = np.where(xau, out[f"xagusd_imp{n}"], out[f"xauusd_imp{n}"])
    # Positive convergence score means the stated trade direction closes an XAU/XAG dislocation.
    for n in (20, 40, 60):
        out[f"conv{n}"] = np.where(xau, -out[f"ratio_z{n}"], out[f"ratio_z{n}"])
    return out


def rules() -> list[Rule]:
    rs = [Rule("baseline", "baseline")]
    for n in (1, 3, 5, 10, 20, 40):
        rs.append(Rule(f"peer-direction-{n}d", "peer", n))
    for n in (3, 5, 10, 20, 40):
        rs.append(Rule(f"both-metals-direction-{n}d", "both", n))
        rs.append(Rule(f"metals-agree-{n}d", "agree", n))
    for n in (3, 5, 10, 20):
        for threshold in (0.25, 0.50, 0.75, 1.00):
            rs.append(Rule(f"peer-impulse-{n}d-{threshold:.2f}", "impulse", n, threshold))
    for n in (20, 40, 60):
        for threshold in (0.0, 0.25, 0.50):
            rs.append(Rule(f"corr-peer-{n}d-{threshold:.2f}", "corr", n, threshold))
        for threshold in (0.25, 0.50, 0.75, 1.00, 1.50):
            rs.append(Rule(f"ratio-convergence-{n}d-{threshold:.2f}", "convergence", n, threshold))
            rs.append(Rule(f"ratio-continuation-{n}d-{threshold:.2f}", "continuation", n, threshold))
    return rs


def eligible(df: pd.DataFrame, rule: Rule) -> pd.Series:
    if rule.family == "baseline":
        return pd.Series(True, index=df.index)
    n = int(rule.a)
    side = df.side_sign.astype(float)
    if rule.family == "peer":
        return side * df[f"peer_ret{n}"] > 0
    if rule.family == "both":
        return (side * df[f"peer_ret{n}"] > 0) & (side * df[f"own_ret{n}"] > 0)
    if rule.family == "agree":
        return df[f"peer_ret{n}"] * df[f"own_ret{n}"] > 0
    if rule.family == "impulse":
        return side * df[f"peer_imp{n}"] >= rule.b
    if rule.family == "corr":
        return (side * df[f"peer_ret{n}"] > 0) & (df[f"corr{n}"] >= rule.b)
    if rule.family == "convergence":
        return side * df[f"conv{n}"] >= rule.b
    if rule.family == "continuation":
        return side * (-df[f"conv{n}"]) >= rule.b
    raise ValueError(rule)


def strategy_priorities(df: pd.DataFrame) -> dict[str, float]:
    out = {}
    for slug, x in df.groupby("slug"):
        gp = x.loc[x.r > 0, "r"].sum()
        gl = -x.loc[x.r < 0, "r"].sum()
        out[slug] = float(gp / gl) if gl else 99.0
    return out


def concurrency_cap(df: pd.DataFrame, priority: dict[str, float], max_open: int = MAX_OPEN) -> pd.DataFrame:
    if df.empty:
        return df.copy()
    x = df.copy()
    x["priority"] = x.slug.map(priority).fillna(0.0)
    x = x.sort_values(["open_time", "priority", "slug"], ascending=[True, False, True])
    active: list[pd.Timestamp] = []
    keep = []
    for idx, row in x.iterrows():
        active = [t for t in active if t > row.open_time]
        if len(active) < max_open:
            keep.append(idx)
            active.append(row.close_time)
    return x.loc[keep].drop(columns="priority").sort_values("close_time")


def period(df: pd.DataFrame, start: pd.Timestamp, end: pd.Timestamp) -> pd.DataFrame:
    return df[(df.open_time >= start) & (df.open_time < end) & (df.close_time < end)].copy()


def metrics(df: pd.DataFrame, cost_r: float = 0.0) -> dict:
    if df.empty:
        return {k: 0.0 for k in ("return_pct", "pf", "win_rate", "dd_pct", "trades", "sharpe", "recovery")}
    x = df.sort_values("close_time").copy()
    equity = 10000.0
    eq = []
    pnls = []
    daily = {}
    for row in x.itertuples():
        rr = float(row.r) - cost_r
        pnl = equity * RISK * rr
        equity += pnl
        pnls.append(pnl)
        eq.append(equity)
        day = pd.Timestamp(row.close_time).normalize()
        daily[day] = daily.get(day, 0.0) + pnl
    arr = np.asarray(eq, float)
    peak = np.maximum.accumulate(np.r_[10000.0, arr])
    dd = (peak[1:] - arr) / peak[1:] * 100
    gp = sum(p for p in pnls if p > 0)
    gl = -sum(p for p in pnls if p < 0)
    ret = (equity / 10000.0 - 1) * 100
    dr = pd.Series(daily).sort_index() / 10000.0
    sharpe = float(math.sqrt(252) * dr.mean() / dr.std(ddof=1)) if len(dr) > 1 and dr.std(ddof=1) > 0 else 0.0
    maxdd = float(np.max(dd)) if len(dd) else 0.0
    return {
        "return_pct": round(ret, 4),
        "pf": round(gp / gl, 4) if gl else 99.0,
        "win_rate": round(100 * sum(p > 0 for p in pnls) / len(pnls), 4),
        "dd_pct": round(maxdd, 4),
        "trades": int(len(pnls)),
        "sharpe": round(sharpe, 4),
        "recovery": round(ret / maxdd, 4) if maxdd else 0.0,
        "final_equity": round(equity, 2),
    }


def equity_curve(df: pd.DataFrame, cost_r: float = 0.0, start_date: pd.Timestamp = START) -> pd.DataFrame:
    equity = 10000.0
    rows = [(start_date, equity)]
    for row in df.sort_values("close_time").itertuples():
        equity *= 1 + RISK * (float(row.r) - cost_r)
        rows.append((pd.Timestamp(row.close_time), equity))
    return pd.DataFrame(rows, columns=["date", "equity"])


def monte_carlo(rs: np.ndarray, paths: int = 5000, block: int = 5) -> dict:
    if len(rs) == 0:
        return {"return_p5": 0.0, "return_median": 0.0, "return_p95": 0.0, "dd_median": 0.0, "dd_p95": 0.0, "profit_probability": 0.0}
    rng = np.random.default_rng(SEED)
    n = len(rs)
    rets, dds = [], []
    for _ in range(paths):
        sample = []
        while len(sample) < n:
            start = int(rng.integers(0, max(1, n - block + 1)))
            sample.extend(rs[start : start + block])
        sample = np.asarray(sample[:n])
        eq = 10000.0 * np.cumprod(1 + RISK * sample)
        peak = np.maximum.accumulate(np.r_[10000.0, eq])
        dd = np.max((peak[1:] - eq) / peak[1:] * 100)
        rets.append((eq[-1] / 10000.0 - 1) * 100)
        dds.append(dd)
    return {
        "return_p5": round(float(np.percentile(rets, 5)), 4),
        "return_median": round(float(np.median(rets)), 4),
        "return_p95": round(float(np.percentile(rets, 95)), 4),
        "dd_median": round(float(np.median(dds)), 4),
        "dd_p95": round(float(np.percentile(dds, 95)), 4),
        "profit_probability": round(float(np.mean(np.asarray(rets) > 0) * 100), 4),
    }


def fmt(v: float, kind: str = "n") -> str:
    if kind == "pct":
        return f"{v:+.2f}%"
    return f"{v:.2f}"


def md_table(headers: list[str], rows: list[list[object]]) -> str:
    lines = ["| " + " | ".join(headers) + " |", "|" + "|".join(["---"] * len(headers)) + "|"]
    lines.extend("| " + " | ".join(map(str, row)) + " |" for row in rows)
    return "\n".join(lines)


def main() -> None:
    HERE.mkdir(parents=True, exist_ok=True)
    CHARTS.mkdir(parents=True, exist_ok=True)
    px = load_prices()
    ledgers = [read_ledger(slug, label) for slug, label in LEDGERS.items()]
    raw = pd.concat(ledgers, ignore_index=True)
    trades = attach_features(raw, px)
    dev_all = period(trades, START, LOCK)
    priority = strategy_priorities(dev_all)
    candidates = rules()

    screen_rows = []
    selected_frames: dict[str, pd.DataFrame] = {}
    for rule in candidates:
        gated = dev_all[eligible(dev_all, rule).fillna(False)]
        capped = concurrency_cap(gated, priority)
        m = metrics(capped)
        selected_frames[rule.name] = capped
        screen_rows.append({"rule": rule.name, "family": rule.family, **m})
    screen = pd.DataFrame(screen_rows)
    base_dev = screen.loc[screen.rule.eq("baseline")].iloc[0]
    viable = screen[
        (screen.rule != "baseline")
        & (screen.trades >= max(100, int(base_dev.trades * 0.40)))
        & (screen.return_pct >= base_dev.return_pct * 0.85)
        & (screen.pf >= base_dev.pf)
        & (screen.dd_pct <= base_dev.dd_pct * 1.05)
        & (screen.sharpe >= base_dev.sharpe)
    ].copy()
    if viable.empty:
        chosen_name = "baseline"
    else:
        viable["score"] = viable.sharpe + 0.20 * np.log(viable.pf.clip(lower=0.01)) + 0.02 * viable.recovery
        chosen_name = str(viable.sort_values(["score", "return_pct"], ascending=False).iloc[0].rule)
    chosen = next(r for r in candidates if r.name == chosen_name)

    def apply(rule: Rule, start: pd.Timestamp, end: pd.Timestamp) -> pd.DataFrame:
        x = period(trades, start, end)
        x = x[eligible(x, rule).fillna(False)]
        return concurrency_cap(x, priority)

    baseline_dev = apply(candidates[0], START, LOCK)
    selected_dev = apply(chosen, START, LOCK)
    baseline_locked = apply(candidates[0], LOCK, END)
    selected_locked = apply(chosen, LOCK, END)
    baseline_full = apply(candidates[0], START, END)
    selected_full = apply(chosen, START, END)

    summaries = {
        "development": {"baseline": metrics(baseline_dev), "selected": metrics(selected_dev)},
        "locked": {"baseline": metrics(baseline_locked), "selected": metrics(selected_locked)},
        "three_year": {"baseline": metrics(baseline_full), "selected": metrics(selected_full)},
        "cost_stress_locked": metrics(selected_locked, cost_r=0.05),
    }
    mc = monte_carlo(selected_locked.sort_values("close_time").r.to_numpy())

    per_ea = []
    for slug, label in LEDGERS.items():
        b = period(trades[trades.slug.eq(slug)], LOCK, END)
        s = b[eligible(b, chosen).fillna(False)]
        bm, sm = metrics(b), metrics(s)
        per_ea.append({"slug": slug, "strategy": label, "symbol": str(b.symbol.iloc[0]) if len(b) else "—", "baseline": bm, "selected": sm})

    stability = []
    for start in pd.date_range(START, END, freq="6MS", inclusive="left"):
        end = min(start + pd.DateOffset(months=6), END)
        x = apply(chosen, start, end)
        stability.append({"from": start.date().isoformat(), "to": end.date().isoformat(), **metrics(x)})

    locked_base = summaries["locked"]["baseline"]
    locked_sel = summaries["locked"]["selected"]
    retention = locked_sel["trades"] / locked_base["trades"] if locked_base["trades"] else 0
    positives = sum(row["return_pct"] > 0 for row in stability)
    gate_checks = {
        "non_baseline": chosen.name != "baseline",
        "locked_min_trades": locked_sel["trades"] >= 80,
        "locked_retention_40pct": retention >= 0.40,
        "locked_return_improves": locked_sel["return_pct"] > locked_base["return_pct"],
        "locked_pf_improves": locked_sel["pf"] > locked_base["pf"],
        "locked_dd_not_worse": locked_sel["dd_pct"] <= locked_base["dd_pct"],
        "cost_stress_positive": summaries["cost_stress_locked"]["return_pct"] > 0,
        "monte_carlo_p5_positive": mc["return_p5"] > 0,
        "four_of_six_positive_halves": positives >= 4,
    }
    passed = all(gate_checks.values())

    screen.to_csv(HERE / "development-screen.csv", index=False)
    pd.DataFrame(stability).to_csv(HERE / "six-month-stability.csv", index=False)
    selected_locked.to_csv(HERE / "selected-locked-trades.csv", index=False)
    result = {
        "step": 4,
        "title": "XAU/XAG Cross-Asset Confirmation",
        "decision": "PASS_NATIVE_CONFIRMATION_REQUIRED" if passed else "REJECT_DO_NOT_ADD",
        "selected_rule": chosen.name,
        "risk_per_trade_pct": 1.0,
        "max_concurrent_metals_positions": MAX_OPEN,
        "summaries": summaries,
        "monte_carlo": mc,
        "gate_checks": gate_checks,
        "per_ea_locked": per_ea,
        "six_month_stability": stability,
        "limitations": [
            "The cross-asset condition is a veto on existing native MT5 trades; it cannot create replacement entries after a skipped trade.",
            "Daily XAU/XAG closes are broker CFD data, not centralized futures settlement data.",
            "A passing veto screen still requires copied-EA native MT5 replay before deployment.",
        ],
    }
    (HERE / "results.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    (HERE / "progress.json").write_text(json.dumps({"step": 4, "title": result["title"], "status": "complete", "decision": result["decision"]}, indent=2), encoding="utf-8")

    plt.style.use("dark_background")
    base_eq = equity_curve(baseline_locked, start_date=LOCK)
    sel_eq = equity_curve(selected_locked, start_date=LOCK)
    fig, axes = plt.subplots(2, 2, figsize=(15, 9))
    fig.patch.set_facecolor("#071512")
    for ax in axes.flat:
        ax.set_facecolor("#0b1d19")
        ax.grid(alpha=0.16)
    axes[0, 0].plot(base_eq.date, base_eq.equity, color="#63c6ff", label="Current baseline")
    axes[0, 0].plot(sel_eq.date, sel_eq.equity, color="#72f5c1", label=chosen.name)
    axes[0, 0].set_title("Untouched locked-year equity")
    axes[0, 0].legend()
    names = ["Return", "PF", "Win rate", "DD"]
    bv = [locked_base["return_pct"], locked_base["pf"], locked_base["win_rate"], locked_base["dd_pct"]]
    sv = [locked_sel["return_pct"], locked_sel["pf"], locked_sel["win_rate"], locked_sel["dd_pct"]]
    xx = np.arange(len(names))
    bars_b = axes[0, 1].bar(xx - 0.18, bv, 0.36, color="#63c6ff", label="Baseline")
    bars_s = axes[0, 1].bar(xx + 0.18, sv, 0.36, color="#72f5c1", label="Selected")
    axes[0, 1].set_xticks(xx, names)
    axes[0, 1].set_yscale("log")
    axes[0, 1].bar_label(bars_b, fmt="%.2f", padding=2, fontsize=8)
    axes[0, 1].bar_label(bars_s, fmt="%.2f", padding=2, fontsize=8)
    axes[0, 1].set_title("Locked metrics")
    axes[0, 1].legend()
    stab = pd.DataFrame(stability)
    colors = ["#72f5c1" if v >= 0 else "#ff6b78" for v in stab.return_pct]
    axes[1, 0].bar(stab["from"], stab.return_pct, color=colors)
    axes[1, 0].axhline(0, color="white", lw=0.8)
    axes[1, 0].tick_params(axis="x", rotation=30)
    axes[1, 0].set_title("Selected rule: consecutive six-month return")
    top = screen.sort_values("sharpe", ascending=False).head(12).sort_values("sharpe")
    axes[1, 1].barh(top.rule, top.sharpe, color="#b794f4")
    axes[1, 1].axvline(base_dev.sharpe, color="#63c6ff", ls="--", label="Baseline")
    axes[1, 1].set_title("Development screen: highest Sharpe")
    axes[1, 1].legend()
    fig.suptitle("Calyx Step 4 — XAU/XAG Cross-Asset Confirmation", fontsize=16, fontweight="bold")
    fig.tight_layout()
    fig.savefig(CHARTS / "step4-summary.png", dpi=170, bbox_inches="tight")
    plt.close(fig)

    per_rows = []
    for row in per_ea:
        b, s = row["baseline"], row["selected"]
        per_rows.append([
            row["strategy"], row["symbol"],
            f"{b['return_pct']:+.2f}→{s['return_pct']:+.2f}%",
            f"{b['pf']:.2f}→{s['pf']:.2f}",
            f"{b['win_rate']:.2f}→{s['win_rate']:.2f}%",
            f"{b['dd_pct']:.2f}→{s['dd_pct']:.2f}%",
            f"{b['trades']}→{s['trades']}",
            f"{s['sharpe']:.2f}", f"{s['recovery']:.2f}",
        ])
    sample_rows = []
    for name, block in summaries.items():
        if name == "cost_stress_locked":
            continue
        b, s = block["baseline"], block["selected"]
        sample_rows.append([
            name.replace("_", " ").title(),
            f"{b['return_pct']:+.2f}→{s['return_pct']:+.2f}%",
            f"{b['pf']:.2f}→{s['pf']:.2f}",
            f"{b['win_rate']:.2f}→{s['win_rate']:.2f}%",
            f"{b['dd_pct']:.2f}→{s['dd_pct']:.2f}%",
            f"{b['trades']}→{s['trades']}", f"{s['sharpe']:.2f}", f"{s['recovery']:.2f}",
        ])
    checks = "\n".join(f"- {'PASS' if ok else 'FAIL'} — {name.replace('_', ' ')}" for name, ok in gate_checks.items())
    report = f"""# Step 4 — XAU/XAG Cross-Asset Confirmation

**Decision: {'PASS — native confirmation required before any deployment' if passed else 'REJECT / DO NOT ADD. No EA, BAT, SET, website, cache, or portfolio file was changed.'}**

## Frozen rule

`{chosen.name}` was selected using the combined development portfolio only. Each source trade retained its native 1% risk configuration, entry, stop, target, trailing/breakeven behavior and session. The overlay can only veto a trade after the source EA triggers. Maximum simultaneous initial metals risk is 4%.

## Portfolio evidence

{md_table(['Sample', 'Return base→gate', 'PF base→gate', 'Win base→gate', 'DD base→gate', 'Trades base→gate', 'Gate Sharpe', 'Gate recovery'], sample_rows)}

Extra locked cost stress (0.05R per accepted trade): **{summaries['cost_stress_locked']['return_pct']:+.2f}%**, PF **{summaries['cost_stress_locked']['pf']:.2f}**. Monte Carlo: P5 **{mc['return_p5']:+.2f}%**, median **{mc['return_median']:+.2f}%**, P95 **{mc['return_p95']:+.2f}%**, profitable paths **{mc['profit_probability']:.2f}%**, DD P95 **{mc['dd_p95']:.2f}%**.

![Step 4 summary](Charts/step4-summary.png)

## Locked-year breakdown by EA

{md_table(['EA', 'Asset', 'Return base→gate', 'PF base→gate', 'Win base→gate', 'DD base→gate', 'Trades base→gate', 'Gate Sharpe', 'Gate recovery'], per_rows)}

## Promotion checks

{checks}

## Interpretation

The locked year was never used to select the rule. If the baseline wins development selection or any locked requirement fails, the correct action is to retain the existing EAs unchanged. A higher PF from a much smaller trade sample is not sufficient.

This is a ledger-veto reconstruction using native MT5 trade outcomes and causal prior-day broker data. A skipped trade can change later EA state, so any passing result would still require a copied-EA implementation and native MT5 Every Tick replay. Broker CFD daily data are also not centralized COMEX futures settlement data.

## Files

- `development-screen.csv`: every tested cross-metal rule.
- `selected-locked-trades.csv`: accepted locked-year trades.
- `six-month-stability.csv`: consecutive half-year results.
- `results.json`: complete machine-readable evidence and gate decisions.
- `Charts/step4-summary.png`: locked comparison, stability, and development screen.
"""
    (HERE / "REPORT.md").write_text(report, encoding="utf-8")
    verification = [
        ("all ledgers found", len(ledgers) == len(LEDGERS)),
        ("development and locked separated", START < LOCK < END),
        ("risk fixed at one percent", RISK == 0.01),
        ("cross-metal features use prior day", trades.feature_date.lt(trades.open_time.dt.normalize()).all()),
        ("monte carlo completed", mc["return_p95"] != mc["return_p5"]),
        ("summary chart generated", (CHARTS / "step4-summary.png").exists()),
    ]
    text = "\n".join(f"{'PASS' if ok else 'FAIL'} — {name}" for name, ok in verification)
    text += f"\nSUMMARY {sum(ok for _, ok in verification)}/{len(verification)}\n"
    (HERE / "VERIFICATION.txt").write_text(text, encoding="utf-8")
    print(f"COMPLETE decision={result['decision']} selected={chosen.name} locked_trades={locked_sel['trades']}")


if __name__ == "__main__":
    main()
