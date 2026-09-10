from __future__ import annotations

import argparse
import hashlib
import json
import math
import shutil
import statistics
import sys
import time
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any


STORE_ROOT = Path(__file__).resolve().parents[1]
if str(STORE_ROOT) not in sys.path:
    sys.path.insert(0, str(STORE_ROOT))

from app.catalog import PACKAGE_ROOT, Product, get_sellable_catalog  # noqa: E402
from app.evidence_cache import (  # noqa: E402
    CACHE_ROOT,
    PERIOD_OPTIONS,
    portfolio_cache_path,
    portfolio_trades_path,
    product_cache_path,
    product_trades_path,
    write_json,
)
from app.evidence_series import parse_mt5_balance_series  # noqa: E402
from app.mt5_evidence_jobs import _native_metrics, _native_trades, mt5_evidence_jobs  # noqa: E402
from app.mt5_live import live_mt5  # noqa: E402
from app.trade_metrics import enrich_trades, outcome_streaks  # noqa: E402


PERIOD_MONTHS = {"6m": 6, "1y": 12, "3y": 36, "5y": 60}


def subtract_months(value: date, months: int) -> date:
    total = value.year * 12 + value.month - 1 - months
    year, month_zero = divmod(total, 12)
    month = month_zero + 1
    month_lengths = (31, 29 if year % 4 == 0 and (year % 100 != 0 or year % 400 == 0) else 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31)
    return date(year, month, min(value.day, month_lengths[month - 1]))


def sample_series(series: list[dict[str, Any]], maximum: int = 5_000) -> list[dict[str, Any]]:
    if len(series) <= maximum:
        return series
    step = (len(series) - 1) / (maximum - 1)
    indexes = sorted({round(index * step) for index in range(maximum)} | {0, len(series) - 1})
    return [series[index] for index in indexes]


def file_hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def source_fingerprint(product: Product, mode: str, start: date, end: date) -> dict[str, Any]:
    set_relative = (
        product.dynamic_set_source
        if mode == "dynamic"
        else product.safe_set_source
        if mode == "safe" and product.safe_set_source
        else product.set_source
    )
    expert_relative = product.dynamic_expert_source if mode == "dynamic" else product.expert_source
    if not set_relative or not expert_relative:
        raise ValueError(f"Missing source files for {product.label} {mode} mode.")
    expert = PACKAGE_ROOT / expert_relative
    settings = PACKAGE_ROOT / str(set_relative)
    fingerprint = {
        "slug": product.slug,
        "mode": mode,
        "from": start.isoformat(),
        "to": end.isoformat(),
        "canonical_symbol": product.canonical,
        "timeframe": product.timeframe,
        "expert_sha256": file_hash(expert),
        "settings_sha256": file_hash(settings),
    }
    return fingerprint


def source_paths(product: Product, mode: str, period: str) -> tuple[Path, Path]:
    folder = CACHE_ROOT / "source-runs" / product.slug / mode
    return folder / f"{period}.htm", folder / f"{period}.meta.json"


def resolve_symbol(product: Product) -> str:
    try:
        return live_mt5.resolve_symbol(product.canonical)
    except RuntimeError:
        return product.canonical


def cleanup_stale_dynamic_artifacts() -> int:
    """Remove only files created by the website's isolated dynamic-test runner."""
    tester_root = mt5_evidence_jobs.tester_terminal.parent.resolve()
    locations = (
        (tester_root / "MQL5" / "Experts" / "EA Store Dynamic", "*.ex5"),
        (tester_root / "reports" / "ea-store-dynamic", "*"),
        (tester_root / "backtest-configs" / "ea-store-dynamic", "*.ini"),
    )
    removed = 0
    for folder, pattern in locations:
        if not folder.is_dir() or tester_root not in folder.resolve().parents:
            continue
        for path in folder.glob(pattern):
            if not path.is_file():
                continue
            path.unlink(missing_ok=True)
            removed += 1
    tester_sets = tester_root / "MQL5" / "Profiles" / "Tester"
    for product in get_sellable_catalog():
        for path in tester_sets.glob(f"{product.slug}-????????.set"):
            if path.is_file():
                path.unlink(missing_ok=True)
                removed += 1
    return removed


def run_native(product: Product, mode: str, period: str, start: date, end: date, *, force: bool) -> Path:
    report_path, metadata_path = source_paths(product, mode, period)
    fingerprint = source_fingerprint(product, mode, start, end)
    if not force and report_path.is_file() and metadata_path.is_file():
        try:
            if json.loads(metadata_path.read_text(encoding="utf-8-sig")) == fingerprint:
                print(f"CACHE SOURCE {product.label} {mode} {period}", flush=True)
                return report_path
        except (OSError, json.JSONDecodeError):
            pass

    symbol = resolve_symbol(product)
    print(f"RUN {product.label} | {mode} | {period} | {symbol} {product.timeframe} | {start} to {end}", flush=True)
    try:
        job = mt5_evidence_jobs.start(product.slug, mode, start, end, symbol)
    except ValueError as exc:
        if "wait a few seconds" not in str(exc).lower():
            raise
        time.sleep(10)
        job = mt5_evidence_jobs.start(product.slug, mode, start, end, symbol)
    last_stage = ""
    while job["status"] in {"queued", "running"}:
        if job.get("stage") != last_stage:
            last_stage = str(job.get("stage"))
            print(f"  {last_stage} ({job.get('progress', 0)}%)", flush=True)
        time.sleep(1)
        job = mt5_evidence_jobs.get(str(job["id"])) or job
    if job["status"] != "completed":
        raise RuntimeError(str(job.get("error") or f"Native MT5 run failed for {product.label}"))
    latest = mt5_evidence_jobs.output_root / product.slug / "latest.htm"
    if not latest.is_file():
        raise RuntimeError(f"Native report was not retained for {product.label}.")
    report_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(latest, report_path)
    write_json(metadata_path, fingerprint)
    latest.unlink(missing_ok=True)
    (latest.parent / "latest.json").unlink(missing_ok=True)
    return report_path


def product_payload(product: Product, mode: str, period: str, start: date, end: date, report: Path) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    parse_mt5_balance_series.cache_clear()
    series = [dict(point) for point in parse_mt5_balance_series(report)]
    native = _native_metrics(report)
    trades = _native_trades(report, f"{product.label} — {mode.title()}")
    for number, trade in enumerate(trades, 1):
        trade["number"] = number
        trade["cache_slug"] = product.slug
        trade["cache_mode"] = mode
        trade["cache_period"] = period
        trade["source"] = "Precomputed native MT5 deals"
    trades = enrich_trades(trades, product.slug)
    native.update(outcome_streaks(trades))
    initial = float(native.get("initial_balance", 10_000) or 10_000)
    if not series:
        series = [{"time": f"{start.isoformat()}T00:00:00", "balance": initial}]
    if str(series[0]["time"])[:10] > start.isoformat():
        series.insert(0, {"time": f"{start.isoformat()}T00:00:00", "balance": initial})
    final = float(native.get("final_balance", initial))
    if len(series) == 1 or str(series[-1]["time"])[:10] < end.isoformat():
        series.append({"time": f"{end.isoformat()}T23:59:59", "balance": final})
    native.update({"from": start.isoformat(), "to": end.isoformat()})
    first_trade_at = min((str(trade["open_time"]) for trade in trades), default=None)
    last_trade_at = max((str(trade["close_time"]) for trade in trades), default=None)
    payload = {
        "label": product.label,
        "period": f"{start.isoformat()} to {end.isoformat()}",
        "period_key": period,
        "mode": mode,
        "currency": "USD",
        "series": sample_series(series),
        "stats": native,
        "available_from": start.isoformat(),
        "available_to": end.isoformat(),
        "cached_trade_count": len(trades),
        "trade_coverage_from": first_trade_at,
        "trade_coverage_to": last_trade_at,
        "notice": "Precomputed native MT5 Every Tick result using the exact active recommended EA and SET file.",
        "source": "precomputed-native-mt5-cache",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "history_quality": native.get("history_quality"),
    }
    return payload, trades


def portfolio_metrics(trades: list[dict[str, Any]], start: date, end: date) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    ordered = sorted(trades, key=lambda row: (str(row["close_time"]), str(row.get("ea", "")), int(row.get("number", 0))))
    balance = 10_000.0
    peak = balance
    maximum_drawdown_cash = 0.0
    maximum_drawdown_pct = 0.0
    series: list[dict[str, Any]] = [{"time": f"{start.isoformat()}T00:00:00", "balance": balance}]
    outcomes: list[float] = []
    normalized: list[dict[str, Any]] = []
    for number, row in enumerate(ordered, 1):
        outcome = float(row["net_profit"])
        outcomes.append(outcome)
        balance += outcome
        peak = max(peak, balance)
        drawdown = peak - balance
        maximum_drawdown_cash = max(maximum_drawdown_cash, drawdown)
        maximum_drawdown_pct = max(maximum_drawdown_pct, drawdown / peak * 100 if peak else 0.0)
        series.append({"time": str(row["close_time"]), "balance": round(balance, 2)})
        normalized.append({**row, "number": number})
    series.append({"time": f"{end.isoformat()}T23:59:59", "balance": round(balance, 2)})
    gross_profit = sum(value for value in outcomes if value > 0)
    gross_loss = -sum(value for value in outcomes if value < 0)
    profit_factor = gross_profit / gross_loss if gross_loss else (999.0 if gross_profit else None)
    win_rate = sum(value > 0 for value in outcomes) / len(outcomes) * 100 if outcomes else None
    sharpe = None
    if len(outcomes) > 1:
        deviation = statistics.pstdev(outcomes)
        if deviation:
            sharpe = statistics.mean(outcomes) / deviation * math.sqrt(len(outcomes))
    net = balance - 10_000.0
    stats = {
        "initial_balance": 10_000.0,
        "final_balance": round(balance, 2),
        "net_profit": round(net, 2),
        "return_pct": round(net / 10_000.0 * 100, 2),
        "profit_factor": round(profit_factor, 2) if profit_factor is not None else None,
        "win_rate_pct": round(win_rate, 2) if win_rate is not None else None,
        "max_drawdown_pct": round(maximum_drawdown_pct, 2),
        "max_drawdown_cash": round(maximum_drawdown_cash, 2),
        "trades": len(outcomes),
        "sharpe_ratio": round(sharpe, 2) if sharpe is not None else None,
        "recovery_factor": round(net / maximum_drawdown_cash, 2) if maximum_drawdown_cash else None,
        "from": start.isoformat(),
        "to": end.isoformat(),
    }
    return stats, series


def portfolio_analytics(
    trades: list[dict[str, Any]],
    series: list[dict[str, Any]],
    initial_balance: float = 10_000.0,
) -> dict[str, Any]:
    """Build deployable portfolio breakdowns from the complete cached MT5 ledger."""
    outcomes = [float(row.get("net_profit") or 0.0) for row in trades]
    wins = [value for value in outcomes if value > 0]
    losses = [value for value in outcomes if value < 0]

    assets: dict[str, dict[str, Any]] = {}
    directions: dict[str, dict[str, Any]] = {
        "Long": {"side": "Long", "trades": 0, "wins": 0, "net_profit": 0.0},
        "Short": {"side": "Short", "trades": 0, "wins": 0, "net_profit": 0.0},
    }
    monthly: dict[str, float] = {}
    for row in trades:
        net = float(row.get("net_profit") or 0.0)
        symbol = str(row.get("symbol") or "Unknown").upper()
        asset = assets.setdefault(symbol, {"symbol": symbol, "trades": 0, "wins": 0, "net_profit": 0.0})
        asset["trades"] += 1
        asset["wins"] += int(net > 0)
        asset["net_profit"] += net

        side_text = str(row.get("side") or "").lower()
        side = "Long" if "buy" in side_text or "long" in side_text else "Short"
        directions[side]["trades"] += 1
        directions[side]["wins"] += int(net > 0)
        directions[side]["net_profit"] += net

        closed = str(row.get("close_time") or "")
        month = closed[:7] if len(closed) >= 7 else "Unknown"
        monthly[month] = monthly.get(month, 0.0) + net

    asset_rows: list[dict[str, Any]] = []
    for asset in assets.values():
        trade_count = int(asset["trades"])
        net = float(asset["net_profit"])
        asset_rows.append(
            {
                **asset,
                "net_profit": round(net, 2),
                "return_contribution_pct": round(net / initial_balance * 100, 2),
                "win_rate_pct": round(float(asset["wins"]) / trade_count * 100, 2) if trade_count else None,
                "trade_share_pct": round(trade_count / len(trades) * 100, 2) if trades else 0.0,
            }
        )
    asset_rows.sort(key=lambda row: float(row["net_profit"]), reverse=True)

    direction_rows: list[dict[str, Any]] = []
    for direction in directions.values():
        trade_count = int(direction["trades"])
        net = float(direction["net_profit"])
        direction_rows.append(
            {
                **direction,
                "net_profit": round(net, 2),
                "win_rate_pct": round(float(direction["wins"]) / trade_count * 100, 2) if trade_count else None,
                "avg_pnl": round(net / trade_count, 2) if trade_count else None,
                "trade_share_pct": round(trade_count / len(trades) * 100, 2) if trades else 0.0,
            }
        )

    ordered_series = sorted(series, key=lambda point: str(point["time"]))
    peak = float(ordered_series[0]["balance"]) if ordered_series else initial_balance
    drawdown_series: list[dict[str, Any]] = []
    for point in ordered_series:
        balance = float(point["balance"])
        peak = max(peak, balance)
        drawdown = (balance - peak) / peak * 100 if peak else 0.0
        drawdown_series.append({"time": str(point["time"]), "drawdown_pct": round(drawdown, 4)})

    return {
        "trade_stats": {
            "average_win": round(statistics.mean(wins), 2) if wins else None,
            "average_loss": round(statistics.mean(losses), 2) if losses else None,
            "best_trade": round(max(outcomes), 2) if outcomes else None,
            "worst_trade": round(min(outcomes), 2) if outcomes else None,
            "payoff_ratio": round(statistics.mean(wins) / abs(statistics.mean(losses)), 2) if wins and losses else None,
        },
        "drawdown_series": sample_series(drawdown_series, maximum=2_000),
        "assets": asset_rows,
        "monthly_pnl": [
            {"month": month, "net_profit": round(net, 2)}
            for month, net in sorted(monthly.items())
            if month != "Unknown"
        ],
        "directions": direction_rows,
    }


def build_portfolio(products: list[Product], period: str, start: date, end: date) -> dict[str, Any]:
    all_trades: list[dict[str, Any]] = []
    included: list[dict[str, Any]] = []
    for product in products:
        selected_mode = (
            "dynamic"
            if product.recommended_dynamic_mode and product.dynamic_mode_supported
            else "safe"
            if product.recommended_safe_mode
            else "standard"
        )
        payload_path = product_cache_path(product.slug, selected_mode, period)
        trades_path = product_trades_path(product.slug, selected_mode, period)
        if not payload_path.is_file() or not trades_path.is_file():
            continue
        payload = json.loads(payload_path.read_text(encoding="utf-8-sig"))
        product_trades = json.loads(trades_path.read_text(encoding="utf-8-sig"))
        all_trades.extend(product_trades)
        included.append(
            {
                "slug": product.slug,
                "label": product.label,
                "symbol": product.canonical,
                "timeframe": product.timeframe,
                "mode": selected_mode,
                "net_profit": payload["stats"].get("net_profit"),
                "return_pct": payload["stats"].get("return_pct"),
                "profit_factor": payload["stats"].get("profit_factor"),
                "win_rate_pct": payload["stats"].get("win_rate_pct"),
                "max_drawdown_pct": payload["stats"].get("max_drawdown_pct"),
                "trades": payload["stats"].get("trades"),
            }
        )
    stats, series = portfolio_metrics(all_trades, start, end)
    analytics = portfolio_analytics(all_trades, series, float(stats["initial_balance"]))
    included.sort(key=lambda row: float(row.get("net_profit") or 0.0), reverse=True)
    first_trade_at = min((str(trade["open_time"]) for trade in all_trades), default=None)
    last_trade_at = max((str(trade["close_time"]) for trade in all_trades), default=None)
    payload = {
        "label": f"Recommended {len(included)}-EA portfolio",
        "period": f"{start.isoformat()} to {end.isoformat()}",
        "period_key": period,
        "mode": "recommended",
        "currency": "USD",
        "series": sample_series(series),
        "stats": stats,
        "available_from": start.isoformat(),
        "available_to": end.isoformat(),
        "cached_trade_count": len(all_trades),
        "trade_coverage_from": first_trade_at,
        "trade_coverage_to": last_trade_at,
        "included_eas": included,
        "analytics": analytics,
        "included_ea_count": len(included),
        "expected_ea_count": len(products),
        "notice": "Precomputed chronological cash-flow overlay of separate native MT5 tests using each EA's recommended Standard or Safe mode; this is not a simultaneous shared-margin MT5 run.",
        "source": "precomputed-native-mt5-cache",
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
    write_json(portfolio_cache_path("standard", period), payload)
    write_json(portfolio_trades_path("standard", period), sorted(all_trades, key=lambda row: str(row["close_time"])))
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(description="Precompute fixed-period native MT5 evidence for the active recommended portfolio.")
    parser.add_argument("--period", choices=["all", *PERIOD_MONTHS], default="all")
    parser.add_argument("--slug", action="append", help="Limit generation to one or more EA slugs.")
    parser.add_argument("--safe", action="store_true", help="Also generate Safe mode for compatible EAs.")
    parser.add_argument("--dynamic", action="store_true", help="Also generate saved Dynamic London mode when available.")
    parser.add_argument("--force", action="store_true", help="Ignore reusable native source reports.")
    parser.add_argument("--portfolio-only", action="store_true", help="Only rebuild portfolio caches from existing EA caches.")
    parser.add_argument("--end", type=date.fromisoformat, default=date.today())
    args = parser.parse_args()

    products = get_sellable_catalog()
    if args.slug:
        wanted = set(args.slug)
        products = [product for product in products if product.slug in wanted]
        missing = wanted - {product.slug for product in products}
        if missing:
            raise SystemExit(f"Unknown EA slug(s): {', '.join(sorted(missing))}")
    periods = list(PERIOD_MONTHS) if args.period == "all" else [args.period]
    failures: list[dict[str, str]] = []
    generated: list[dict[str, Any]] = []

    if not args.portfolio_only:
        removed = cleanup_stale_dynamic_artifacts()
        print(f"CLEANUP removed {removed} stale isolated-tester artifacts", flush=True)
        for product in products:
            modes = (
                ["standard"]
                + (["safe"] if args.safe and product.safe_filter_supported else [])
                + (["dynamic"] if args.dynamic and product.dynamic_mode_supported else [])
            )
            for mode in modes:
                for period in periods:
                    start = subtract_months(args.end, PERIOD_MONTHS[period])
                    try:
                        report = run_native(product, mode, period, start, args.end, force=args.force)
                        payload, trades = product_payload(product, mode, period, start, args.end, report)
                        write_json(product_cache_path(product.slug, mode, period), payload)
                        write_json(product_trades_path(product.slug, mode, period), trades)
                        generated.append({"slug": product.slug, "mode": mode, "period": period, "stats": payload["stats"]})
                        print(
                            f"DONE {product.label} {mode} {period}: "
                            f"{payload['stats'].get('return_pct')}% | PF {payload['stats'].get('profit_factor')} | "
                            f"WR {payload['stats'].get('win_rate_pct')}% | DD {payload['stats'].get('max_drawdown_pct')}% | "
                            f"{len(trades)} trades",
                            flush=True,
                        )
                    except Exception as exc:
                        failures.append({"slug": product.slug, "mode": mode, "period": period, "error": str(exc)})
                        print(f"FAILED {product.label} {mode} {period}: {exc}", flush=True)

    portfolio_rows: list[dict[str, Any]] = []
    full_catalog = get_sellable_catalog()
    for period in periods:
        start = subtract_months(args.end, PERIOD_MONTHS[period])
        portfolio_end = args.end
        if args.portfolio_only and full_catalog:
            reference_mode = (
                "dynamic"
                if full_catalog[0].recommended_dynamic_mode and full_catalog[0].dynamic_mode_supported
                else "safe"
                if full_catalog[0].recommended_safe_mode
                else "standard"
            )
            reference_path = product_cache_path(full_catalog[0].slug, reference_mode, period)
            if reference_path.is_file():
                reference = json.loads(reference_path.read_text(encoding="utf-8-sig"))
                start = date.fromisoformat(str(reference["available_from"]))
                portfolio_end = date.fromisoformat(str(reference["available_to"]))
        if all(
            product_cache_path(
                product.slug,
                "dynamic"
                if product.recommended_dynamic_mode and product.dynamic_mode_supported
                else "safe"
                if product.recommended_safe_mode
                else "standard",
                period,
            ).is_file()
            for product in full_catalog
        ):
            portfolio = build_portfolio(full_catalog, period, start, portfolio_end)
            portfolio_rows.append({"period": period, "stats": portfolio["stats"], "included_ea_count": portfolio["included_ea_count"]})
            print(f"PORTFOLIO {period}: {portfolio['stats']}", flush=True)
        else:
            print(f"PORTFOLIO {period}: waiting for all {len(full_catalog)} recommended-mode EA caches", flush=True)

    manifest = {
        "cache_version": "v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "end_date": str(portfolio_rows[-1]["stats"]["to"]) if portfolio_rows else args.end.isoformat(),
        "periods": PERIOD_OPTIONS,
        "recommended_eas": [
            {
                "slug": product.slug,
                "label": product.label,
                "symbol": product.canonical,
                "timeframe": product.timeframe,
                "mode": (
                    "dynamic"
                    if product.recommended_dynamic_mode and product.dynamic_mode_supported
                    else "safe"
                    if product.recommended_safe_mode
                    else "standard"
                ),
            }
            for product in full_catalog
        ],
        "recommended_ea_count": len(full_catalog),
        "generated_runs": generated,
        "portfolio": portfolio_rows,
        "failures": failures,
        "methodology": "Each cached EA period is an independent native MT5 Every Tick run from a USD 10,000 starting balance using its exact active recommended EA, SET and evidence-selected Standard, Safe or Dynamic mode. Portfolio curves chronologically overlay realized cash flows from those separate tests.",
    }
    write_json(CACHE_ROOT / "manifest.json", manifest)
    print(f"MANIFEST {CACHE_ROOT / 'manifest.json'}", flush=True)
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
