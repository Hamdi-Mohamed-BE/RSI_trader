from __future__ import annotations

import csv
import json
import math
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Iterable

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


HERE = Path(__file__).resolve().parent
STORE = HERE.parents[2] / "EA store"
CACHE = STORE / "data" / "evidence-cache" / "v1"
MANIFEST = CACHE / "manifest.json"

START = pd.Timestamp("2023-09-07 00:00:00")
DEV_END = pd.Timestamp("2025-09-06 23:59:59")
LOCKED_START = pd.Timestamp("2025-09-07 00:00:00")
END = pd.Timestamp("2026-09-07 23:59:59")
INITIAL_BALANCE = 10_000.0
MC_PATHS = 10_000
MC_BLOCK_DAYS = 5
MC_SEED = 20260907


@dataclass(frozen=True)
class Policy:
    name: str
    total_cap: float | None
    symbol_cap: float | None = None
    family_cap: float | None = None
    news_family_cap: float | None = None


POLICIES = [
    Policy("Uncapped", None, None, None),
    Policy("8% total", 8.0, None, None),
    Policy("6% total", 6.0, None, None),
    Policy("5% total", 5.0, None, None),
    Policy("4% total", 4.0, None, None),
    Policy("3% total", 3.0, None, None),
    Policy("2% total", 2.0, None, None),
    Policy("6% total / 3% symbol", 6.0, 3.0, None),
    Policy("5% total / 3% symbol", 5.0, 3.0, None),
    Policy("4% total / 3% symbol", 4.0, 3.0, None),
    Policy("4% total / 2% symbol", 4.0, 2.0, None),
    Policy("3% total / 2% symbol", 3.0, 2.0, None),
    Policy("6% total / 3% symbol / 2% ORB family", 6.0, 3.0, 2.0, 4.5),
    Policy("5% total / 3% symbol / 2% ORB family", 5.0, 3.0, 2.0, 4.5),
    Policy("4% total / 3% symbol / 2% ORB family", 4.0, 3.0, 2.0, 4.5),
]


def risk_family(slug: str) -> str:
    if slug.startswith("news-pulse-"):
        return "NEWS_PULSE"
    if slug.startswith("orb-volume-profile") or slug.startswith("xau-orb-"):
        return "XAU_ORB"
    if slug.startswith("us100-") and "orb" in slug:
        return "US100_ORB"
    return slug


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def finite(value: Any, default: float = 0.0) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return default
    return number if math.isfinite(number) else default


def load_recommended_trades() -> tuple[pd.DataFrame, list[dict[str, Any]]]:
    manifest = read_json(MANIFEST)
    recommended = manifest["recommended_eas"]
    frames: list[pd.DataFrame] = []
    inventory: list[dict[str, Any]] = []

    for priority, item in enumerate(recommended):
        slug = item["slug"]
        mode = item["mode"]
        path = CACHE / "products" / slug / mode / "3y.trades.json"
        payload_path = CACHE / "products" / slug / mode / "3y.json"
        if not path.is_file():
            inventory.append({**item, "status": "missing trade cache", "path": str(path)})
            continue

        rows = read_json(path)
        payload = read_json(payload_path) if payload_path.is_file() else {}
        frame = pd.DataFrame(rows)
        if frame.empty:
            inventory.append({**item, "status": "empty trade cache", "path": str(path)})
            continue

        frame["slug"] = slug
        frame["label"] = item["label"]
        frame["selected_mode"] = mode
        frame["priority"] = priority
        frame["open_time"] = pd.to_datetime(frame["open_time"], errors="coerce")
        frame["close_time"] = pd.to_datetime(frame["close_time"], errors="coerce")
        frame["net_profit"] = pd.to_numeric(frame["net_profit"], errors="coerce").fillna(0.0)
        frame["configured_risk_pct"] = pd.to_numeric(
            frame.get("configured_risk_pct", pd.Series(index=frame.index, dtype=float)), errors="coerce"
        )
        default_risk = 0.75 if slug.startswith("news-pulse-") else 1.0
        frame["configured_risk_pct"] = frame["configured_risk_pct"].fillna(default_risk)
        frame["estimated_risk_cash"] = pd.to_numeric(
            frame.get("estimated_risk_cash", pd.Series(index=frame.index, dtype=float)), errors="coerce"
        )
        fallback_r = pd.to_numeric(
            frame.get("estimated_r", pd.Series(index=frame.index, dtype=float)), errors="coerce"
        )
        exact_r = frame["net_profit"] / frame["estimated_risk_cash"].replace(0.0, np.nan)
        frame["r_multiple"] = exact_r.fillna(fallback_r)
        frame["reserved_risk_pct"] = frame["configured_risk_pct"]
        # News Pulse can have both 0.75% pending directions live. Reserve the whole
        # 1.50% event budget even though only the triggered leg appears in the ledger.
        frame.loc[frame["slug"].str.startswith("news-pulse-"), "reserved_risk_pct"] = 1.5
        frame["risk_family"] = frame["slug"].map(risk_family)
        frames.append(frame)
        inventory.append(
            {
                **item,
                "status": "loaded",
                "cached_trades": int(len(frame)),
                "cache_from": payload.get("available_from"),
                "cache_to": payload.get("available_to"),
                "path": str(path),
            }
        )

    if not frames:
        raise RuntimeError("No recommended cached trade ledgers were found.")
    trades = pd.concat(frames, ignore_index=True)
    trades = trades.dropna(subset=["open_time", "close_time", "r_multiple"])
    trades = trades[(trades["close_time"] >= trades["open_time"]) & np.isfinite(trades["r_multiple"])]
    trades = trades[(trades["open_time"] >= START) & (trades["close_time"] <= END)].copy()
    trades["trade_id"] = np.arange(len(trades), dtype=int)
    trades["symbol"] = trades["symbol"].astype(str).str.upper()
    trades["side"] = trades["side"].astype(str)
    return trades, inventory


def select_window(trades: pd.DataFrame, start: pd.Timestamp, end: pd.Timestamp) -> pd.DataFrame:
    return trades[(trades["open_time"] >= start) & (trades["close_time"] <= end)].copy()


def simulate(
    trades: pd.DataFrame,
    policy: Policy,
    start: pd.Timestamp,
    end: pd.Timestamp,
    *,
    extra_cost_pct: float = 0.0,
) -> dict[str, Any]:
    if trades.empty:
        raise ValueError("Cannot simulate an empty trade set")

    opens: dict[pd.Timestamp, list[dict[str, Any]]] = defaultdict(list)
    closes: dict[pd.Timestamp, list[int]] = defaultdict(list)
    records = trades.to_dict("records")
    for row in records:
        opens[row["open_time"]].append(row)
        closes[row["close_time"]].append(int(row["trade_id"]))

    times = sorted(set(opens) | set(closes))
    active: dict[int, dict[str, Any]] = {}
    accepted: list[dict[str, Any]] = []
    rejected: list[dict[str, Any]] = []
    equity = INITIAL_BALANCE
    fixed_equity = INITIAL_BALANCE
    peak = equity
    fixed_peak = fixed_equity
    max_drawdown_pct = 0.0
    max_drawdown_cash = 0.0
    fixed_max_drawdown_pct = 0.0
    fixed_max_drawdown_cash = 0.0
    equity_series = [
        {
            "time": start.isoformat(),
            "balance": equity,
            "fixed_balance": fixed_equity,
            "drawdown_pct": 0.0,
            "fixed_drawdown_pct": 0.0,
        }
    ]
    exposure_series: list[dict[str, Any]] = []
    max_total_risk = 0.0
    max_active = 0
    max_symbol_risk: Counter[str] = Counter()
    opportunities_by_slug: Counter[str] = Counter()
    accepted_by_slug: Counter[str] = Counter()

    def snapshot(timestamp: pd.Timestamp) -> None:
        nonlocal max_total_risk, max_active
        total = sum(float(item["reserved_risk_pct"]) for item in active.values())
        symbol_risk: Counter[str] = Counter()
        for item in active.values():
            symbol_risk[str(item["symbol"])] += float(item["reserved_risk_pct"])
        max_total_risk = max(max_total_risk, total)
        max_active = max(max_active, len(active))
        for symbol, risk in symbol_risk.items():
            max_symbol_risk[symbol] = max(max_symbol_risk[symbol], risk)
        exposure_series.append(
            {
                "time": timestamp.isoformat(),
                "active_trades": len(active),
                "total_risk_pct": total,
                "symbol_risk_pct": dict(symbol_risk),
            }
        )

    for timestamp in times:
        # Realized exits free their original risk before entries at the same timestamp.
        for trade_id in sorted(closes.get(timestamp, [])):
            position = active.pop(trade_id, None)
            if position is None:
                continue
            pnl = float(position["simulated_pnl"])
            fixed_pnl = float(position["fixed_risk_pnl"])
            equity += pnl
            fixed_equity += fixed_pnl
            peak = max(peak, equity)
            fixed_peak = max(fixed_peak, fixed_equity)
            drawdown_cash = peak - equity
            drawdown_pct = drawdown_cash / peak * 100.0 if peak else 0.0
            fixed_drawdown_cash = fixed_peak - fixed_equity
            fixed_drawdown_pct = fixed_drawdown_cash / fixed_peak * 100.0 if fixed_peak else 0.0
            max_drawdown_pct = max(max_drawdown_pct, drawdown_pct)
            max_drawdown_cash = max(max_drawdown_cash, drawdown_cash)
            fixed_max_drawdown_pct = max(fixed_max_drawdown_pct, fixed_drawdown_pct)
            fixed_max_drawdown_cash = max(fixed_max_drawdown_cash, fixed_drawdown_cash)
            position["simulated_close_equity"] = equity
            position["fixed_close_equity"] = fixed_equity
            position["drawdown_pct_after_close"] = drawdown_pct
            position["fixed_drawdown_pct_after_close"] = fixed_drawdown_pct
            equity_series.append(
                {
                    "time": timestamp.isoformat(),
                    "balance": equity,
                    "fixed_balance": fixed_equity,
                    "drawdown_pct": -drawdown_pct,
                    "fixed_drawdown_pct": -fixed_drawdown_pct,
                }
            )

        raw_candidates = opens.get(timestamp, [])
        for row in raw_candidates:
            opportunities_by_slug[str(row["slug"])] += 1
        # Fair deterministic arbitration prevents a permanently earlier chart in
        # the manifest from starving a correlated sibling whose entries share the
        # same timestamp. The least-served EA is evaluated first; frozen manifest
        # order only breaks exact ties.
        candidates = sorted(
            raw_candidates,
            key=lambda row: (
                accepted_by_slug[str(row["slug"])] / opportunities_by_slug[str(row["slug"])],
                str(row["symbol"]),
                int(row["priority"]),
                str(row["slug"]),
                int(row["trade_id"]),
            ),
        )
        for row in candidates:
            current_total = sum(float(item["reserved_risk_pct"]) for item in active.values())
            current_symbol = sum(
                float(item["reserved_risk_pct"])
                for item in active.values()
                if str(item["symbol"]) == str(row["symbol"])
            )
            current_family = sum(
                float(item["reserved_risk_pct"])
                for item in active.values()
                if str(item["risk_family"]) == str(row["risk_family"])
            )
            reserve = float(row["reserved_risk_pct"])
            total_ok = policy.total_cap is None or current_total + reserve <= policy.total_cap + 1e-9
            symbol_ok = policy.symbol_cap is None or current_symbol + reserve <= policy.symbol_cap + 1e-9
            family_limit = policy.news_family_cap if str(row["risk_family"]) == "NEWS_PULSE" else policy.family_cap
            family_ok = family_limit is None or current_family + reserve <= family_limit + 1e-9
            output = {
                "trade_id": int(row["trade_id"]),
                "slug": str(row["slug"]),
                "label": str(row["label"]),
                "symbol": str(row["symbol"]),
                "side": str(row["side"]),
                "open_time": row["open_time"].isoformat(),
                "close_time": row["close_time"].isoformat(),
                "r_multiple": float(row["r_multiple"]),
                "trade_risk_pct": float(row["configured_risk_pct"]),
                "reserved_risk_pct": reserve,
                "risk_family": str(row["risk_family"]),
                "equity_at_entry": equity,
                "fixed_equity_at_entry": fixed_equity,
                "active_risk_before_pct": current_total,
                "symbol_risk_before_pct": current_symbol,
                "family_risk_before_pct": current_family,
            }
            if not total_ok or not symbol_ok or not family_ok:
                output["reason"] = "total cap" if not total_ok else "symbol cap" if not symbol_ok else "family cap"
                rejected.append(output)
                continue

            trade_risk_cash = equity * float(row["configured_risk_pct"]) / 100.0
            fixed_risk_cash = INITIAL_BALANCE * float(row["configured_risk_pct"]) / 100.0
            extra_cost_cash = equity * extra_cost_pct / 100.0
            fixed_extra_cost_cash = INITIAL_BALANCE * extra_cost_pct / 100.0
            output["risk_cash"] = trade_risk_cash
            output["fixed_risk_cash"] = fixed_risk_cash
            output["extra_cost_cash"] = extra_cost_cash
            output["fixed_extra_cost_cash"] = fixed_extra_cost_cash
            output["simulated_pnl"] = float(row["r_multiple"]) * trade_risk_cash - extra_cost_cash
            output["fixed_risk_pnl"] = float(row["r_multiple"]) * fixed_risk_cash - fixed_extra_cost_cash
            output["active_risk_after_pct"] = current_total + reserve
            accepted.append(output)
            accepted_by_slug[str(row["slug"])] += 1
            active[int(row["trade_id"])] = output
        snapshot(timestamp)

    # There should be no active positions because the window includes only trades
    # whose closes fall inside it. Keep the guard explicit for data-quality reporting.
    unclosed_count = len(active)
    equity_series.append(
        {
            "time": end.isoformat(),
            "balance": equity,
            "fixed_balance": fixed_equity,
            "drawdown_pct": -(peak - equity) / peak * 100.0,
            "fixed_drawdown_pct": -(fixed_peak - fixed_equity) / fixed_peak * 100.0,
        }
    )

    pnl = np.asarray([float(row["simulated_pnl"]) for row in accepted], dtype=float)
    gross_profit = float(pnl[pnl > 0].sum()) if len(pnl) else 0.0
    gross_loss = float(-pnl[pnl < 0].sum()) if len(pnl) else 0.0
    pf = gross_profit / gross_loss if gross_loss else None
    win_rate = float((pnl > 0).mean() * 100.0) if len(pnl) else None
    elapsed_years = max((end - start).total_seconds() / (365.25 * 86400.0), 1 / 365.25)
    cagr = ((equity / INITIAL_BALANCE) ** (1.0 / elapsed_years) - 1.0) * 100.0 if equity > 0 else -100.0

    daily = daily_returns(equity_series, start, end)
    daily_std = float(daily["return"].std(ddof=1)) if len(daily) > 1 else 0.0
    sharpe = float(daily["return"].mean() / daily_std * math.sqrt(365.0)) if daily_std > 0 else None
    fixed_daily_std = float(daily["fixed_return_on_initial"].std(ddof=1)) if len(daily) > 1 else 0.0
    fixed_sharpe = (
        float(daily["fixed_return_on_initial"].mean() / fixed_daily_std * math.sqrt(365.0))
        if fixed_daily_std > 0
        else None
    )
    accepted_ids = {int(row["trade_id"]) for row in accepted}
    by_ea: list[dict[str, Any]] = []
    for slug, group in trades.groupby("slug", sort=False):
        ids = set(int(value) for value in group["trade_id"])
        kept = [row for row in accepted if int(row["trade_id"]) in ids]
        ea_pnl = sum(float(row["fixed_risk_pnl"]) for row in kept)
        by_ea.append(
            {
                "slug": slug,
                "label": str(group.iloc[0]["label"]),
                "symbol": str(group.iloc[0]["symbol"]),
                "mode": str(group.iloc[0]["selected_mode"]),
                "available_trades": int(len(group)),
                "accepted_trades": int(len(kept)),
                "skipped_trades": int(len(ids - accepted_ids)),
                "acceptance_pct": float(len(kept) / len(group) * 100.0),
                "fixed_risk_pnl": float(ea_pnl),
                "win_rate_pct": float(sum(float(row["fixed_risk_pnl"]) > 0 for row in kept) / len(kept) * 100.0)
                if kept
                else None,
            }
        )

    stats = {
        "policy": policy.name,
        "total_cap_pct": policy.total_cap,
        "symbol_cap_pct": policy.symbol_cap,
        "family_cap_pct": policy.family_cap,
        "news_family_cap_pct": policy.news_family_cap,
        "from": start.isoformat(),
        "to": end.isoformat(),
        "initial_balance": INITIAL_BALANCE,
        "final_balance": equity,
        "net_profit": equity - INITIAL_BALANCE,
        "return_pct": (equity / INITIAL_BALANCE - 1.0) * 100.0,
        "cagr_pct": cagr,
        "profit_factor": pf,
        "win_rate_pct": win_rate,
        "max_drawdown_pct": max_drawdown_pct,
        "max_drawdown_cash": max_drawdown_cash,
        "recovery_factor": (equity - INITIAL_BALANCE) / max_drawdown_cash if max_drawdown_cash else None,
        "daily_sharpe": sharpe,
        "fixed_final_balance": fixed_equity,
        "fixed_net_profit": fixed_equity - INITIAL_BALANCE,
        "fixed_return_pct": (fixed_equity / INITIAL_BALANCE - 1.0) * 100.0,
        "fixed_profit_factor": (
            sum(max(float(row["fixed_risk_pnl"]), 0.0) for row in accepted)
            / abs(sum(min(float(row["fixed_risk_pnl"]), 0.0) for row in accepted))
            if any(float(row["fixed_risk_pnl"]) < 0 for row in accepted)
            else None
        ),
        "fixed_max_drawdown_pct": fixed_max_drawdown_pct,
        "fixed_max_drawdown_cash": fixed_max_drawdown_cash,
        "fixed_recovery_factor": (fixed_equity - INITIAL_BALANCE) / fixed_max_drawdown_cash
        if fixed_max_drawdown_cash
        else None,
        "fixed_daily_sharpe": fixed_sharpe,
        "available_trades": int(len(trades)),
        "accepted_trades": int(len(accepted)),
        "skipped_trades": int(len(rejected)),
        "acceptance_pct": float(len(accepted) / len(trades) * 100.0),
        "max_concurrent_trades": max_active,
        "max_reserved_risk_pct": max_total_risk,
        "max_symbol_risk_pct": dict(max_symbol_risk),
        "unclosed_count": unclosed_count,
        "extra_cost_pct_per_trade": extra_cost_pct,
    }
    return {
        "stats": stats,
        "accepted": accepted,
        "rejected": rejected,
        "equity_series": equity_series,
        "exposure_series": exposure_series,
        "daily_returns": daily,
        "by_ea": by_ea,
    }


def daily_returns(series: list[dict[str, Any]], start: pd.Timestamp, end: pd.Timestamp) -> pd.DataFrame:
    frame = pd.DataFrame(series)
    frame["time"] = pd.to_datetime(frame["time"])
    frame = frame.sort_values("time").drop_duplicates("time", keep="last").set_index("time")
    index = pd.date_range(start.normalize(), end.normalize(), freq="D")
    balances = frame["balance"].resample("D").last().reindex(index).ffill().fillna(INITIAL_BALANCE)
    returns = balances.pct_change().fillna(0.0)
    fixed_balances = frame["fixed_balance"].resample("D").last().reindex(index).ffill().fillna(INITIAL_BALANCE)
    fixed_pnl = fixed_balances.diff().fillna(0.0)
    return pd.DataFrame(
        {
            "date": index,
            "balance": balances.values,
            "return": returns.values,
            "fixed_balance": fixed_balances.values,
            "fixed_return_on_initial": (fixed_pnl / INITIAL_BALANCE).values,
        }
    )


def duration_weighted_exposure(exposure_series: list[dict[str, Any]], end: pd.Timestamp) -> dict[str, Any]:
    if not exposure_series:
        return {}
    rows = sorted(exposure_series, key=lambda row: row["time"])
    weighted: list[tuple[float, float, int, dict[str, float]]] = []
    total_seconds = 0.0
    for index, row in enumerate(rows):
        at = pd.Timestamp(row["time"])
        next_at = pd.Timestamp(rows[index + 1]["time"]) if index + 1 < len(rows) else end
        seconds = max((next_at - at).total_seconds(), 0.0)
        if seconds <= 0:
            continue
        total_seconds += seconds
        weighted.append(
            (
                seconds,
                float(row["total_risk_pct"]),
                int(row["active_trades"]),
                {str(k): float(v) for k, v in row["symbol_risk_pct"].items()},
            )
        )

    def weighted_quantile(values: Iterable[tuple[float, float]], q: float) -> float:
        ordered = sorted(values, key=lambda item: item[1])
        target = sum(weight for weight, _ in ordered) * q
        cumulative = 0.0
        for weight, value in ordered:
            cumulative += weight
            if cumulative >= target:
                return value
        return ordered[-1][1] if ordered else 0.0

    total_values = [(seconds, risk) for seconds, risk, _, _ in weighted]
    active_values = [(seconds, float(count)) for seconds, _, count, _ in weighted]
    symbol_names = sorted({symbol for _, _, _, symbols in weighted for symbol in symbols})
    symbols: dict[str, dict[str, float]] = {}
    for symbol in symbol_names:
        values = [(seconds, risks.get(symbol, 0.0)) for seconds, _, _, risks in weighted]
        symbols[symbol] = {
            "mean_pct": sum(weight * value for weight, value in values) / total_seconds if total_seconds else 0.0,
            "p95_pct": weighted_quantile(values, 0.95),
            "max_pct": max((value for _, value in values), default=0.0),
        }
    return {
        "mean_total_risk_pct": sum(seconds * risk for seconds, risk, _, _ in weighted) / total_seconds
        if total_seconds
        else 0.0,
        "p50_total_risk_pct": weighted_quantile(total_values, 0.50),
        "p90_total_risk_pct": weighted_quantile(total_values, 0.90),
        "p95_total_risk_pct": weighted_quantile(total_values, 0.95),
        "p99_total_risk_pct": weighted_quantile(total_values, 0.99),
        "max_total_risk_pct": max((risk for _, risk, _, _ in weighted), default=0.0),
        "mean_active_trades": sum(seconds * count for seconds, _, count, _ in weighted) / total_seconds
        if total_seconds
        else 0.0,
        "p95_active_trades": weighted_quantile(active_values, 0.95),
        "max_active_trades": max((count for _, _, count, _ in weighted), default=0),
        "symbols": symbols,
    }


def correlation_analysis(trades: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    frame = trades.copy()
    frame["close_date"] = frame["close_time"].dt.normalize()
    # R-normalized daily outcomes prevent one EA's compounding cash scale from
    # dominating another EA in the correlation matrix.
    daily = frame.pivot_table(index="close_date", columns="slug", values="r_multiple", aggfunc="sum", fill_value=0.0)
    daily = daily.reindex(pd.date_range(START.normalize(), END.normalize(), freq="D"), fill_value=0.0)
    matrix = daily.corr().fillna(0.0)
    pairs: list[dict[str, Any]] = []
    columns = list(matrix.columns)
    symbol_by_slug = frame.groupby("slug")["symbol"].first().to_dict()
    label_by_slug = frame.groupby("slug")["label"].first().to_dict()
    for left_index, left in enumerate(columns):
        for right in columns[left_index + 1 :]:
            pairs.append(
                {
                    "ea_1": left,
                    "label_1": label_by_slug.get(left, left),
                    "symbol_1": symbol_by_slug.get(left, ""),
                    "ea_2": right,
                    "label_2": label_by_slug.get(right, right),
                    "symbol_2": symbol_by_slug.get(right, ""),
                    "daily_r_correlation": float(matrix.loc[left, right]),
                }
            )
    pairs_frame = pd.DataFrame(pairs).sort_values("daily_r_correlation", ascending=False)
    return matrix, pairs_frame


def monte_carlo(daily: pd.DataFrame, paths: int = MC_PATHS, block_days: int = MC_BLOCK_DAYS) -> dict[str, Any]:
    # Fixed-risk daily P/L as a fraction of the original account avoids turning a
    # high-frequency multi-EA backtest into an implausible exponential projection.
    values = daily["fixed_return_on_initial"].to_numpy(dtype=float)
    n = len(values)
    if n == 0:
        return {}
    blocks = np.asarray([np.take(values, np.arange(start, start + block_days) % n) for start in range(n)])
    needed = math.ceil(n / block_days)
    rng = np.random.default_rng(MC_SEED)
    batch_size = 250
    final_returns: list[np.ndarray] = []
    max_drawdowns: list[np.ndarray] = []
    ruin_count = 0
    for offset in range(0, paths, batch_size):
        size = min(batch_size, paths - offset)
        indices = rng.integers(0, n, size=(size, needed))
        sampled = blocks[indices].reshape(size, needed * block_days)[:, :n]
        equity = 1.0 + np.cumsum(sampled, axis=1)
        peaks = np.maximum.accumulate(equity, axis=1)
        drawdowns = 1.0 - equity / peaks
        final = (equity[:, -1] - 1.0) * 100.0
        dd = drawdowns.max(axis=1) * 100.0
        final_returns.append(final)
        max_drawdowns.append(dd)
        ruin_count += int(np.sum(np.min(equity, axis=1) <= 0.5))
    returns = np.concatenate(final_returns)
    drawdowns = np.concatenate(max_drawdowns)
    return {
        "paths": paths,
        "block_days": block_days,
        "seed": MC_SEED,
        "model": "fixed 1% initial-balance risk per regular trade; additive daily P/L",
        "return_p5_pct": float(np.percentile(returns, 5)),
        "return_median_pct": float(np.percentile(returns, 50)),
        "return_p95_pct": float(np.percentile(returns, 95)),
        "drawdown_median_pct": float(np.percentile(drawdowns, 50)),
        "drawdown_p95_pct": float(np.percentile(drawdowns, 95)),
        "profitable_paths_pct": float(np.mean(returns > 0.0) * 100.0),
        "loss_50pct_or_more_pct": float(ruin_count / paths * 100.0),
    }


def jsonable(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): jsonable(item) for key, item in value.items()}
    if isinstance(value, list):
        return [jsonable(item) for item in value]
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating,)):
        return None if not math.isfinite(float(value)) else float(value)
    if isinstance(value, (pd.Timestamp, datetime)):
        return value.isoformat()
    if isinstance(value, float) and not math.isfinite(value):
        return None
    return value


def round_stats(stats: dict[str, Any]) -> dict[str, Any]:
    rounded: dict[str, Any] = {}
    for key, value in stats.items():
        if isinstance(value, float):
            rounded[key] = round(value, 4)
        elif isinstance(value, dict):
            rounded[key] = round_stats(value)
        else:
            rounded[key] = value
    return rounded


def save_table(path: Path, rows: list[dict[str, Any]]) -> None:
    frame = pd.DataFrame(rows)
    if not frame.empty:
        for column in frame.select_dtypes(include=["float"]).columns:
            frame[column] = frame[column].round(4)
    frame.to_csv(path, index=False, encoding="utf-8-sig", quoting=csv.QUOTE_MINIMAL)


def plot_results(
    full_results: dict[str, dict[str, Any]],
    selected_name: str,
    corr: pd.DataFrame,
    raw_exposure: dict[str, Any],
) -> None:
    charts = HERE / "Charts"
    charts.mkdir(parents=True, exist_ok=True)
    plt.style.use("dark_background")
    mint = "#65f5c5"
    blue = "#59c9ff"
    red = "#ff6577"
    gold = "#f7c948"
    grid = "#203633"

    # Cap frontier.
    ordered = [policy.name for policy in POLICIES]
    returns = [full_results[name]["stats"]["fixed_return_pct"] for name in ordered]
    dds = [full_results[name]["stats"]["fixed_max_drawdown_pct"] for name in ordered]
    acceptance = [full_results[name]["stats"]["acceptance_pct"] for name in ordered]
    labels = [name.replace(" total", "").replace(" / ", "/") for name in ordered]
    fig, axes = plt.subplots(2, 1, figsize=(14, 9), constrained_layout=True)
    axes[0].bar(np.arange(len(labels)) - 0.18, returns, width=0.36, color=mint, label="Return %")
    axes[0].bar(np.arange(len(labels)) + 0.18, dds, width=0.36, color=red, label="Max closed-balance DD %")
    axes[0].set_xticks(np.arange(len(labels)), labels, rotation=28, ha="right")
    axes[0].grid(axis="y", color=grid, alpha=0.7)
    axes[0].legend(frameon=False)
    axes[0].set_title("Three-year shared-equity cap comparison", loc="left", fontweight="bold")
    axes[1].bar(np.arange(len(labels)), acceptance, color=blue)
    axes[1].axhline(90, color=gold, linestyle="--", linewidth=1, label="90% accepted")
    axes[1].set_ylim(0, 105)
    axes[1].set_ylabel("Accepted trades (%)")
    axes[1].set_xticks(np.arange(len(labels)), labels, rotation=28, ha="right")
    axes[1].grid(axis="y", color=grid, alpha=0.7)
    axes[1].legend(frameon=False)
    fig.savefig(charts / "cap-frontier.png", dpi=170, facecolor="#07110f")
    plt.close(fig)

    # Equity and drawdown comparison.
    fig, axes = plt.subplots(2, 1, figsize=(14, 9), sharex=True, constrained_layout=True)
    for name, color in [("Uncapped", red), (selected_name, mint)]:
        daily = full_results[name]["daily_returns"]
        axes[0].plot(daily["date"], daily["fixed_balance"], color=color, linewidth=1.5, label=name)
        peak = daily["fixed_balance"].cummax()
        dd = (daily["fixed_balance"] / peak - 1.0) * 100.0
        axes[1].plot(daily["date"], dd, color=color, linewidth=1.3, label=name)
    axes[0].set_title("Fixed-risk shared portfolio reconstruction", loc="left", fontweight="bold")
    axes[0].set_ylabel("Balance (USD)")
    axes[0].grid(color=grid, alpha=0.7)
    axes[0].legend(frameon=False)
    axes[1].set_title("Closed-balance drawdown", loc="left", fontweight="bold")
    axes[1].set_ylabel("Drawdown (%)")
    axes[1].grid(color=grid, alpha=0.7)
    axes[1].xaxis.set_major_locator(mdates.MonthLocator(interval=4))
    axes[1].xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m"))
    axes[1].tick_params(axis="x", rotation=30)
    fig.savefig(charts / "selected-equity-and-drawdown.png", dpi=170, facecolor="#07110f")
    plt.close(fig)

    # Correlation heatmap.
    fig, ax = plt.subplots(figsize=(16, 13), constrained_layout=True)
    image = ax.imshow(corr.to_numpy(), vmin=-0.35, vmax=0.70, cmap="RdYlGn_r", aspect="auto")
    ax.set_xticks(np.arange(len(corr.columns)), corr.columns, rotation=75, ha="right", fontsize=7)
    ax.set_yticks(np.arange(len(corr.index)), corr.index, fontsize=7)
    ax.set_title("Daily R correlation — selected 28 EAs", loc="left", fontweight="bold")
    fig.colorbar(image, ax=ax, shrink=0.7, label="Pearson correlation")
    fig.savefig(charts / "daily-r-correlation.png", dpi=170, facecolor="#07110f")
    plt.close(fig)

    # Raw duration-weighted exposure by symbol.
    symbols = raw_exposure.get("symbols", {})
    labels = list(symbols)
    means = [symbols[symbol]["mean_pct"] for symbol in labels]
    p95s = [symbols[symbol]["p95_pct"] for symbol in labels]
    maximums = [symbols[symbol]["max_pct"] for symbol in labels]
    positions = np.arange(len(labels))
    fig, ax = plt.subplots(figsize=(12, 7), constrained_layout=True)
    ax.bar(positions - 0.25, means, width=0.25, color=blue, label="Time-weighted mean")
    ax.bar(positions, p95s, width=0.25, color=gold, label="Time-weighted P95")
    ax.bar(positions + 0.25, maximums, width=0.25, color=red, label="Maximum")
    ax.set_xticks(positions, labels)
    ax.set_ylabel("Reserved risk (%)")
    ax.set_title("Uncapped simultaneous risk by symbol", loc="left", fontweight="bold")
    ax.grid(axis="y", color=grid, alpha=0.7)
    ax.legend(frameon=False)
    fig.savefig(charts / "uncapped-symbol-exposure.png", dpi=170, facecolor="#07110f")
    plt.close(fig)


def choose_policy(dev_rows: list[dict[str, Any]]) -> str:
    # Pre-declared guardrails: keep most signals, cap both same-symbol and strongly
    # correlated strategy-family exposure, and avoid a development drawdown blowout.
    eligible = [
        row
        for row in dev_rows
        if row["symbol_cap_pct"] is not None
        and row["family_cap_pct"] is not None
        and row["acceptance_pct"] >= 60.0
        and row["fixed_max_drawdown_pct"] <= 25.0
        and row["fixed_final_balance"] > 0
    ]
    if not eligible:
        eligible = [
            row
            for row in dev_rows
            if row["symbol_cap_pct"] is not None
            and row["family_cap_pct"] is not None
            and row["fixed_final_balance"] > 0
        ]
    # Rank on normalized development return / drawdown, with a small acceptance penalty. The
    # locked year is deliberately not used for selection.
    for row in eligible:
        row["selection_score"] = (
            row["fixed_return_pct"] / max(row["fixed_max_drawdown_pct"], 0.25)
        ) * math.sqrt(max(row["acceptance_pct"], 1.0) / 100.0)
    return max(eligible, key=lambda row: row["selection_score"])["policy"]


def main() -> int:
    HERE.mkdir(parents=True, exist_ok=True)
    trades, inventory = load_recommended_trades()
    full_trades = select_window(trades, START, END)
    dev_trades = select_window(trades, START, DEV_END)
    locked_trades = select_window(trades, LOCKED_START, END)

    invalid_inventory = [row for row in inventory if row["status"] != "loaded"]
    if invalid_inventory:
        raise RuntimeError(f"Missing or empty recommended ledgers: {invalid_inventory}")

    quality = {
        "manifest_recommended_eas": len(inventory),
        "loaded_eas": int(full_trades["slug"].nunique()),
        "loaded_trades": int(len(full_trades)),
        "development_trades": int(len(dev_trades)),
        "locked_year_trades": int(len(locked_trades)),
        "cached_rows_outside_common_3y_window_or_invalid": int(
            sum(int(row.get("cached_trades", 0)) for row in inventory) - len(full_trades)
        ),
        "r_min": float(full_trades["r_multiple"].min()),
        "r_median": float(full_trades["r_multiple"].median()),
        "r_max": float(full_trades["r_multiple"].max()),
        "abs_r_over_10": int((full_trades["r_multiple"].abs() > 10.0).sum()),
        "news_trade_count": int(full_trades["slug"].str.startswith("news-pulse-").sum()),
        "regular_trade_risk_pct": 1.0,
        "news_triggered_leg_risk_pct": 0.75,
        "news_reserved_event_risk_pct": 1.5,
    }

    windows = {
        "development": (dev_trades, START, DEV_END),
        "locked_year": (locked_trades, LOCKED_START, END),
        "full_3y": (full_trades, START, END),
    }
    results: dict[str, dict[str, dict[str, Any]]] = {}
    comparison_rows: list[dict[str, Any]] = []
    for window_name, (window_trades, start, end) in windows.items():
        results[window_name] = {}
        for policy in POLICIES:
            outcome = simulate(window_trades, policy, start, end)
            results[window_name][policy.name] = outcome
            comparison_rows.append({"window": window_name, **outcome["stats"]})

    dev_stats = [results["development"][policy.name]["stats"] for policy in POLICIES]
    selected_name = choose_policy(dev_stats)
    selected_policy = next(policy for policy in POLICIES if policy.name == selected_name)

    raw_exposure = duration_weighted_exposure(results["full_3y"]["Uncapped"]["exposure_series"], END)
    selected_exposure = duration_weighted_exposure(
        results["full_3y"][selected_name]["exposure_series"], END
    )
    corr, pairs = correlation_analysis(full_trades)

    selected_full = results["full_3y"][selected_name]
    selected_locked = results["locked_year"][selected_name]
    monte_carlo_results = {
        "full_3y": monte_carlo(selected_full["daily_returns"]),
        "locked_year": monte_carlo(selected_locked["daily_returns"]),
    }

    stress_rows: list[dict[str, Any]] = []
    for extra_cost in [0.0, 0.02, 0.05, 0.10]:
        for window_name, (window_trades, start, end) in windows.items():
            outcome = simulate(window_trades, selected_policy, start, end, extra_cost_pct=extra_cost)
            stress_rows.append({"window": window_name, **outcome["stats"]})

    # Two anti-fragility checks: remove News Pulse entirely, then retain it but cap
    # every realized winner at +5R. Seven XAG news trades exceed +10R, so the main
    # decision must not depend on those unusually favorable fills.
    core_trades = full_trades[~full_trades["slug"].str.startswith("news-pulse-")].copy()
    core_dev = select_window(core_trades, START, DEV_END)
    core_locked = select_window(core_trades, LOCKED_START, END)
    core_policy_rows: list[dict[str, Any]] = []
    core_results: dict[str, dict[str, Any]] = {}
    for policy in POLICIES:
        core_dev_outcome = simulate(core_dev, policy, START, DEV_END)
        core_results[policy.name] = {
            "development": core_dev_outcome,
            "locked_year": simulate(core_locked, policy, LOCKED_START, END),
            "full_3y": simulate(core_trades, policy, START, END),
        }
        core_policy_rows.append(core_dev_outcome["stats"])
    core_selected_name = choose_policy(core_policy_rows)

    capped_r_trades = full_trades.copy()
    capped_r_trades["r_multiple"] = capped_r_trades["r_multiple"].clip(lower=-5.0, upper=5.0)
    capped_r_results = {
        "development": simulate(select_window(capped_r_trades, START, DEV_END), selected_policy, START, DEV_END),
        "locked_year": simulate(
            select_window(capped_r_trades, LOCKED_START, END), selected_policy, LOCKED_START, END
        ),
        "full_3y": simulate(capped_r_trades, selected_policy, START, END),
    }

    selected_by_ea = sorted(selected_full["by_ea"], key=lambda row: row["fixed_risk_pnl"], reverse=True)
    rejected_by_reason = Counter(row["reason"] for row in selected_full["rejected"])
    rejected_by_symbol = Counter(row["symbol"] for row in selected_full["rejected"])
    rejected_by_ea = Counter(row["slug"] for row in selected_full["rejected"])

    audit = {
        "step": 12,
        "title": "Portfolio-wide recombination and shared-risk audit",
        "generated_at": datetime.now().astimezone().isoformat(),
        "method": {
            "description": "Chronological shared-account reconstruction from the 28 recommended native MT5 cached trade ledgers.",
            "sizing": "The decision view holds regular risk at $100 per trade (1% of the original $10,000) and News Pulse at $75 per triggered leg, preventing exponential compounding from distorting cap selection. A dynamic 1% current-equity projection is retained as a non-deployable mathematical stress view.",
            "cap_logic": "Full initial risk remains reserved until the cached close time. Exits are processed before entries at equal timestamps. Simultaneous entries use deterministic least-served arbitration, with frozen manifest order only breaking ties. ORB siblings share a 2% family cap. The three News Pulse EAs share a separate 4.5% family allowance because each reserves its hard 1.5% event budget.",
            "drawdown": "Closed-balance drawdown only; intratrade mark-to-market paths are unavailable in the cached deal ledgers.",
            "selection": "The policy was selected using only the first two years. The final year was held out and reported afterward.",
        },
        "quality": quality,
        "inventory": inventory,
        "selected_policy": selected_name,
        "selected_policy_definition": {
            "total_cap_pct": selected_policy.total_cap,
            "symbol_cap_pct": selected_policy.symbol_cap,
            "family_cap_pct": selected_policy.family_cap,
            "news_family_cap_pct": selected_policy.news_family_cap,
        },
        "selected_results": {
            window: round_stats(results[window][selected_name]["stats"])
            for window in ["development", "locked_year", "full_3y"]
        },
        "uncapped_results": {
            window: round_stats(results[window]["Uncapped"]["stats"])
            for window in ["development", "locked_year", "full_3y"]
        },
        "uncapped_exposure": round_stats(raw_exposure),
        "selected_exposure": round_stats(selected_exposure),
        "monte_carlo": round_stats(monte_carlo_results),
        "anti_fragility": {
            "core_25_eas_excluding_news": {
                "development_selected_policy": core_selected_name,
                "selected_policy_matches_full_portfolio": core_selected_name == selected_name,
                "using_full_portfolio_policy": {
                    window: round_stats(core_results[selected_name][window]["stats"])
                    for window in ["development", "locked_year", "full_3y"]
                },
                "using_core_selected_policy": {
                    window: round_stats(core_results[core_selected_name][window]["stats"])
                    for window in ["development", "locked_year", "full_3y"]
                },
            },
            "all_28_with_r_wins_capped_at_plus_5r": {
                window: round_stats(capped_r_results[window]["stats"])
                for window in ["development", "locked_year", "full_3y"]
            },
        },
        "selected_rejections": {
            "by_reason": dict(rejected_by_reason),
            "by_symbol": dict(rejected_by_symbol),
            "top_eas": dict(rejected_by_ea.most_common(10)),
        },
        "top_positive_correlations": pairs.head(15).round(4).to_dict("records"),
        "top_negative_correlations": pairs.tail(15).sort_values("daily_r_correlation").round(4).to_dict("records"),
        "selected_ea_contributions": selected_by_ea,
        "limitations": [
            "The source EAs were tested separately, so this reconstruction cannot model shared margin, intratrade floating equity, stop-gap slippage, or broker liquidation.",
            "Estimated R is reconstructed from native net P/L and each test's estimated equity risk at entry; it is not an exchange-provided field.",
            "Keeping initial risk reserved until close is conservative when an EA moves its stop to break-even or trails it.",
            "A centralized portfolio risk gate still needs implementation and demo verification before this cap can be enforced live.",
        ],
    }

    write_json(HERE / "portfolio-risk-audit.json", jsonable(audit))
    save_table(HERE / "cap-comparison.csv", comparison_rows)
    save_table(HERE / "cost-stress.csv", stress_rows)
    save_table(
        HERE / "core-25-cap-comparison.csv",
        [
            {"window": window, **core_results[policy.name][window]["stats"]}
            for window in ["development", "locked_year", "full_3y"]
            for policy in POLICIES
        ],
    )
    save_table(HERE / "selected-ea-contribution.csv", selected_by_ea)
    save_table(HERE / "selected-accepted-trades.csv", selected_full["accepted"])
    save_table(HERE / "selected-skipped-trades.csv", selected_full["rejected"])
    corr.round(5).to_csv(HERE / "daily-r-correlation-matrix.csv", encoding="utf-8-sig")
    pairs.round(5).to_csv(HERE / "ea-correlation-pairs.csv", index=False, encoding="utf-8-sig")
    save_table(HERE / "inventory.csv", inventory)
    save_table(
        HERE / "r-outliers-over-10.csv",
        full_trades.loc[
            full_trades["r_multiple"].abs() > 10.0,
            [
                "slug",
                "label",
                "symbol",
                "side",
                "open_time",
                "close_time",
                "net_profit",
                "estimated_risk_cash",
                "r_multiple",
                "entry_comment",
                "exit_comment",
            ],
        ].to_dict("records"),
    )
    write_json(HERE / "monte-carlo-results.json", jsonable(round_stats(monte_carlo_results)))
    plot_results(results["full_3y"], selected_name, corr, raw_exposure)

    compact = {
        "selected_policy": selected_name,
        "quality": quality,
        "selected_results": audit["selected_results"],
        "uncapped_results": audit["uncapped_results"],
        "uncapped_exposure": audit["uncapped_exposure"],
        "selected_exposure": audit["selected_exposure"],
        "monte_carlo": audit["monte_carlo"],
        "anti_fragility": audit["anti_fragility"],
        "top_positive_correlations": audit["top_positive_correlations"][:8],
        "selected_rejections": audit["selected_rejections"],
    }
    print(json.dumps(compact, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
