from __future__ import annotations

from collections import defaultdict
from dataclasses import replace
from datetime import date, datetime, time, timedelta
import argparse
import json
import math
from pathlib import Path
from typing import Any

import pandas as pd

from .config import REPORTS_DIR, load_config
from .mt5_client import MT5Client
from .relvol_orb_strategy import build_opening_setups, settings_from_env, simulate_setup


REPORT_DIR = REPORTS_DIR / "relvol_orb_backtest"
CACHE_DIR = REPORT_DIR / "cache"
PAPER_TOP_SYMBOLS = (
    "NVDA",
    "AMD",
    "TSLA",
    "FSLR",
    "RCL",
    "W",
    "OKTA",
    "ADBE",
    "WDC",
    "NFLX",
    "ASML",
    "CDNS",
    "LRCX",
    "META",
    "AMZN",
    "AAPL",
    "MSFT",
)


def _parse_csv(value: str | None, cast, defaults: tuple) -> tuple:
    if not value:
        return defaults
    result = []
    for item in value.split(","):
        try:
            result.append(cast(item.strip()))
        except ValueError:
            continue
    return tuple(result) or defaults


def _normalize_volume(raw: float, minimum: float, maximum: float, step: float) -> float:
    if raw < minimum or minimum <= 0 or step <= 0:
        return 0.0
    clipped = min(raw, maximum)
    steps = math.floor((clipped - minimum + 1e-12) / step)
    return round(minimum + steps * step, 8)


def _cache_path(symbol: str, start: date, end: date) -> Path:
    return CACHE_DIR / f"{symbol}_{start.isoformat()}_{end.isoformat()}_M5.pkl"


def fetch_history(
    client: MT5Client,
    symbol: str,
    start: date,
    end: date,
    refresh: bool = False,
) -> tuple[pd.DataFrame | None, dict[str, Any]]:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    path = _cache_path(symbol, start, end)
    resolved = client.resolve_symbol(symbol)
    info = client.symbol_info(symbol) if resolved else None
    metadata = {
        "symbol": symbol,
        "broker_symbol": resolved,
        "point": float((info or {}).get("point") or 0.01),
        "contract_size": float((info or {}).get("trade_contract_size") or 1.0),
        "volume_min": float((info or {}).get("volume_min") or 1.0),
        "volume_max": float((info or {}).get("volume_max") or 100000.0),
        "volume_step": float((info or {}).get("volume_step") or 1.0),
    }
    if not resolved:
        return None, {**metadata, "status": "symbol_unavailable"}
    if path.exists() and not refresh:
        frame = pd.read_pickle(path)
        return frame, {**metadata, "status": "cache", "bars": len(frame)}

    start_dt = datetime.combine(start, time.min)
    end_dt = datetime.combine(end + timedelta(days=1), time.min)
    frame = client.fetch_candles(symbol, "M5", start_dt, end_dt, max_bars=100000)
    if frame is None or frame.empty:
        return None, {**metadata, "status": "no_history"}
    frame.to_pickle(path)
    return frame, {
        **metadata,
        "status": "mt5",
        "bars": len(frame),
        "first": str(frame.iloc[0]["time"]),
        "last": str(frame.iloc[-1]["time"]),
        "volume_source": str(frame.iloc[-1].get("volume_source") or "unknown"),
    }


def _daily_groups(setups: list[dict[str, Any]], start: date, end: date) -> dict[date, list[dict[str, Any]]]:
    grouped: dict[date, list[dict[str, Any]]] = defaultdict(list)
    for setup in setups:
        session_day = setup["session_date"]
        if start <= session_day <= end and setup.get("eligible"):
            grouped[session_day].append(setup)
    return dict(grouped)


def simulate_portfolio(
    setups: list[dict[str, Any]],
    metadata: dict[str, dict[str, Any]],
    start: date,
    end: date,
    starting_balance: float,
    stop_fraction: float,
    relative_volume_min: float,
    top_n: int,
    risk_percent: float,
    max_leverage: float,
    spread_multiplier: float,
    commission_per_unit: float,
    use_minimum_lot: bool = True,
    symbol_profiles: dict[str, dict[str, float]] | None = None,
) -> dict[str, Any]:
    balance = float(starting_balance)
    peak = balance
    max_drawdown = 0.0
    trades: list[dict[str, Any]] = []
    equity_curve = [{"date": str(start), "balance": balance}]
    skipped_below_minimum = 0
    minimum_lot_fallbacks = 0
    profiles = symbol_profiles or {}

    for session_day, candidates in sorted(_daily_groups(setups, start, end).items()):
        selected = [
            item
            for item in candidates
            if float(item["relative_volume"])
            >= float(profiles.get(str(item["symbol"]), {}).get("relative_volume_min", relative_volume_min))
        ]
        selected.sort(key=lambda item: float(item["relative_volume"]), reverse=True)
        selected = selected[:top_n]
        day_start_balance = balance
        leverage_remaining = max(0.0, day_start_balance * max_leverage)
        day_trades: list[dict[str, Any]] = []
        for setup in selected:
            symbol_meta = metadata[setup["symbol"]]
            simulated = simulate_setup(
                setup,
                atr_stop_fraction=float(
                    profiles.get(str(setup["symbol"]), {}).get("atr_stop_fraction", stop_fraction)
                ),
                point=float(symbol_meta["point"]),
                spread_multiplier=spread_multiplier,
                commission_per_unit_per_side=commission_per_unit,
            )
            if simulated is None:
                continue
            contract_size = max(1e-12, float(symbol_meta["contract_size"]))
            risk_budget = day_start_balance * (risk_percent / 100.0)
            risk_per_volume = float(simulated["stop_distance"]) * contract_size
            notional_per_volume = float(simulated["entry"]) * contract_size
            risk_volume = risk_budget / risk_per_volume if risk_per_volume > 0 else 0.0
            leverage_volume = leverage_remaining / notional_per_volume if notional_per_volume > 0 else 0.0
            minimum_volume = float(symbol_meta["volume_min"])
            volume = _normalize_volume(
                min(risk_volume, leverage_volume),
                minimum_volume,
                float(symbol_meta["volume_max"]),
                float(symbol_meta["volume_step"]),
            )
            if volume <= 0 and use_minimum_lot and risk_volume < minimum_volume <= leverage_volume:
                volume = minimum_volume
                minimum_lot_fallbacks += 1
            if volume <= 0:
                skipped_below_minimum += 1
                continue
            notional = notional_per_volume * volume
            leverage_remaining = max(0.0, leverage_remaining - notional)
            pnl = float(simulated["net_per_unit"]) * contract_size * volume
            day_trades.append(
                {
                    **simulated,
                    "volume": volume,
                    "notional": notional,
                    "risk_budget": risk_budget,
                    "pnl": pnl,
                    "balance_before": day_start_balance,
                }
            )

        balance += sum(float(item["pnl"]) for item in day_trades)
        for item in day_trades:
            item["balance_after_day"] = balance
            trades.append(item)
        peak = max(peak, balance)
        drawdown = (peak - balance) / peak * 100.0 if peak > 0 else 0.0
        max_drawdown = max(max_drawdown, drawdown)
        equity_curve.append({"date": str(session_day), "balance": balance})

    wins = [item for item in trades if float(item["pnl"]) > 0]
    losses = [item for item in trades if float(item["pnl"]) < 0]
    gross_profit = sum(float(item["pnl"]) for item in wins)
    gross_loss = abs(sum(float(item["pnl"]) for item in losses))
    daily_returns = pd.Series([item["balance"] for item in equity_curve], dtype=float).pct_change().dropna()
    sharpe = 0.0
    if len(daily_returns) > 1 and float(daily_returns.std(ddof=1)) > 0:
        sharpe = float(daily_returns.mean() / daily_returns.std(ddof=1) * math.sqrt(252))
    return {
        "start": str(start),
        "end": str(end),
        "starting_balance": starting_balance,
        "ending_balance": balance,
        "net_profit": balance - starting_balance,
        "return_percent": (balance / starting_balance - 1.0) * 100.0,
        "max_drawdown_percent": max_drawdown,
        "trades": len(trades),
        "wins": len(wins),
        "losses": len(losses),
        "win_rate_percent": len(wins) / len(trades) * 100.0 if trades else 0.0,
        "profit_factor": gross_profit / gross_loss if gross_loss > 0 else (float("inf") if gross_profit > 0 else 0.0),
        "total_r": sum(float(item["r_multiple"]) for item in trades),
        "average_r": sum(float(item["r_multiple"]) for item in trades) / len(trades) if trades else 0.0,
        "sharpe": sharpe,
        "skipped_below_broker_minimum": skipped_below_minimum,
        "minimum_lot_fallbacks": minimum_lot_fallbacks,
        "equity_curve": equity_curve,
        "trade_rows": trades,
    }


def _summary(result: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in result.items() if key not in {"trade_rows", "equity_curve"}}


def _robust_score(train: dict[str, Any], validation: dict[str, Any]) -> float:
    if train["trades"] < 4 or validation["trades"] < 2:
        return -1e9
    if train["return_percent"] <= 0 or validation["return_percent"] <= 0:
        return -1e6 + validation["return_percent"]
    return (
        validation["return_percent"] * 1.5
        + train["return_percent"] * 0.35
        + min(train["return_percent"], validation["return_percent"])
        - 0.20 * (train["max_drawdown_percent"] + validation["max_drawdown_percent"])
    )


def _training_symbol_score(result: dict[str, Any]) -> float:
    """Rank symbols using training data only; validation never influences selection."""
    if result["trades"] < 2 or result["return_percent"] <= 0 or result["profit_factor"] <= 1.0:
        return -1e9
    return (
        float(result["return_percent"])
        - 0.35 * float(result["max_drawdown_percent"])
        + min(3.0, max(0.0, float(result["profit_factor"]) - 1.0))
    )


def _configuration_passed(row: dict[str, Any]) -> bool:
    return (
        int(row["train_trades"]) >= 4
        and int(row["validation_trades"]) >= 2
        and float(row["train_return_percent"]) > 0
        and float(row["validation_return_percent"]) > 0
    )


def _markdown_report(report: dict[str, Any]) -> str:
    best = report["best_config"]
    result = report["best_full_result"]
    raw = report["raw_full_period_best_config"]
    status = "PASSED" if report["robust_selection_passed"] else "FAILED"
    lines = [
        "# Relative-Volume ORB: 60-Day Research Report",
        "",
        f"Period: {report['requested_period']['start']} to {report['requested_period']['end']}",
        f"Starting balance: ${report['starting_balance']:.2f}",
        f"Chronological train/validation screen: **{status}**",
        "",
        "## Walk-Forward Selection",
        "",
        f"- Symbols: {best['selected_symbols']}",
        f"- Opening range: {best['range_minutes']} minutes",
        f"- Stop: {float(best['atr_stop_fraction']) * 100:g}% of prior 14-session ATR",
        f"- Minimum relative volume: {best['relative_volume_min']}",
        f"- Daily rank limit: {best['top_n']}",
        f"- Training: {best['train_return_percent']:.2f}% over {best['train_trades']} trades",
        f"- Validation: {best['validation_return_percent']:.2f}% over {best['validation_trades']} trades",
        f"- Full period: ${result['ending_balance']:.2f} ({result['return_percent']:.2f}%), "
        f"{result['trades']} trades, {result['max_drawdown_percent']:.2f}% max drawdown",
        "",
        "The later segment is used to rank the optimization grid. It is chronological out-of-sample data "
        "for each individual configuration, but it is not an untouched final test after model selection.",
        "",
        "## Full-Period Winner (In-Sample)",
        "",
        f"- Symbols: {raw['selected_symbols']}",
        f"- Configuration: {raw['range_minutes']}m range, {float(raw['atr_stop_fraction']) * 100:g}% "
        f"ATR stop, RVOL >= {raw['relative_volume_min']}, top {raw['top_n']}",
        f"- Full return: {raw['full_return_percent']:.2f}% over {raw['full_trades']} trades",
        f"- Validation: {raw['validation_return_percent']:.2f}% over {raw['validation_trades']} trades",
        "",
        "This winner is reported for transparency, not promoted to a live default, because it did not pass "
        "the chronological validation gate.",
        "",
        "## Data Limitation",
        "",
        "The paper uses consolidated U.S. share volume. This broker supplies MT5 tick volume for its stock "
        "CFDs, so relative volume is only an activity proxy and the one-million-share eligibility filter "
        "cannot be reproduced faithfully.",
        "",
    ]
    return "\n".join(lines)


def run_optimization(
    symbols: tuple[str, ...],
    start: date,
    end: date,
    starting_balance: float = 300.0,
    range_values: tuple[int, ...] = (5, 15, 30, 60),
    stop_values: tuple[float, ...] = (0.05, 0.075, 0.10, 0.15, 0.20),
    relative_volume_values: tuple[float, ...] = (0.75, 1.0, 1.25, 1.5, 2.0),
    top_n_values: tuple[int, ...] = (1, 3, 5, 10, 20),
    refresh: bool = False,
) -> dict[str, Any]:
    load_config()
    base = settings_from_env()
    history_start = start - timedelta(days=55)
    client = MT5Client()
    histories: dict[str, pd.DataFrame] = {}
    metadata: dict[str, dict[str, Any]] = {}
    availability: list[dict[str, Any]] = []
    for symbol in symbols:
        frame, meta = fetch_history(client, symbol, history_start, end, refresh=refresh)
        availability.append(meta)
        if frame is not None and len(frame) >= 1000:
            histories[symbol] = frame
            metadata[symbol] = meta
    client.shutdown()
    if not histories:
        raise RuntimeError("No MT5 M5 history was available for the requested symbols.")

    setups_by_range: dict[int, list[dict[str, Any]]] = {}
    for range_minutes in range_values:
        settings = replace(
            base,
            range_minutes=range_minutes,
            relative_volume_min=0.0,
            symbols=tuple(histories),
        )
        setups: list[dict[str, Any]] = []
        for symbol, frame in histories.items():
            setups.extend(build_opening_setups(frame, symbol, settings, require_complete_session=True))
        setups_by_range[range_minutes] = setups

    session_days = sorted(
        {
            item["session_date"]
            for setups in setups_by_range.values()
            for item in setups
            if start <= item["session_date"] <= end
        }
    )
    if len(session_days) < 10:
        raise RuntimeError(f"Only {len(session_days)} complete sessions were available; optimization requires 10.")
    split_index = max(1, min(len(session_days) - 1, int(len(session_days) * 0.70)))
    validation_start = session_days[split_index]
    training_end = session_days[split_index - 1]

    rows: list[dict[str, Any]] = []
    per_symbol_rows: list[dict[str, Any]] = []
    subset_sizes = tuple(sorted({min(5, value) for value in top_n_values if value > 0})) or (1, 3, 5)
    for range_minutes in range_values:
        setups = setups_by_range[range_minutes]
        for stop_fraction in stop_values:
            for relative_volume_min in relative_volume_values:
                for top_n in top_n_values:
                    kwargs = {
                        "setups": setups,
                        "metadata": metadata,
                        "starting_balance": starting_balance,
                        "stop_fraction": stop_fraction,
                        "relative_volume_min": relative_volume_min,
                        "top_n": top_n,
                        "risk_percent": base.risk_percent,
                        "max_leverage": base.max_leverage,
                        "spread_multiplier": base.spread_multiplier,
                        "commission_per_unit": base.commission_per_unit_per_side,
                        "use_minimum_lot": base.use_minimum_lot,
                    }
                    train = simulate_portfolio(start=start, end=training_end, **kwargs)
                    validation = simulate_portfolio(start=validation_start, end=end, **kwargs)
                    full = simulate_portfolio(start=start, end=end, **kwargs)
                    rows.append(
                        {
                            "selection_method": "all_symbols",
                            "selected_symbols": ",".join(histories),
                            "range_minutes": range_minutes,
                            "atr_stop_fraction": stop_fraction,
                            "relative_volume_min": relative_volume_min,
                            "top_n": top_n,
                            "robust_score": _robust_score(train, validation),
                            **{f"train_{key}": value for key, value in _summary(train).items()},
                            **{f"validation_{key}": value for key, value in _summary(validation).items()},
                            **{f"full_{key}": value for key, value in _summary(full).items()},
                        }
                    )

                training_rank: list[tuple[float, str]] = []
                symbol_results: dict[str, tuple[dict[str, Any], dict[str, Any], dict[str, Any]]] = {}
                for symbol in histories:
                    symbol_setups = [item for item in setups if item["symbol"] == symbol]
                    symbol_kwargs = {
                        "setups": symbol_setups,
                        "metadata": metadata,
                        "starting_balance": starting_balance,
                        "stop_fraction": stop_fraction,
                        "relative_volume_min": relative_volume_min,
                        "top_n": 1,
                        "risk_percent": base.risk_percent,
                        "max_leverage": base.max_leverage,
                        "spread_multiplier": base.spread_multiplier,
                        "commission_per_unit": base.commission_per_unit_per_side,
                        "use_minimum_lot": base.use_minimum_lot,
                    }
                    train = simulate_portfolio(start=start, end=training_end, **symbol_kwargs)
                    validation = simulate_portfolio(start=validation_start, end=end, **symbol_kwargs)
                    full = simulate_portfolio(start=start, end=end, **symbol_kwargs)
                    symbol_results[symbol] = (train, validation, full)
                    training_score = _training_symbol_score(train)
                    training_rank.append((training_score, symbol))
                    per_symbol_rows.append(
                        {
                            "symbol": symbol,
                            "range_minutes": range_minutes,
                            "atr_stop_fraction": stop_fraction,
                            "relative_volume_min": relative_volume_min,
                            "training_selection_score": training_score,
                            "robust_score": _robust_score(train, validation),
                            **{f"train_{key}": value for key, value in _summary(train).items()},
                            **{f"validation_{key}": value for key, value in _summary(validation).items()},
                            **{f"full_{key}": value for key, value in _summary(full).items()},
                        }
                    )

                ranked_symbols = [
                    symbol
                    for score, symbol in sorted(training_rank, reverse=True)
                    if score > -1e8
                ]
                for subset_size in subset_sizes:
                    selected_symbols = ranked_symbols[:subset_size]
                    if not selected_symbols:
                        continue
                    selected_setups = [item for item in setups if item["symbol"] in selected_symbols]
                    subset_kwargs = {
                        "setups": selected_setups,
                        "metadata": metadata,
                        "starting_balance": starting_balance,
                        "stop_fraction": stop_fraction,
                        "relative_volume_min": relative_volume_min,
                        "top_n": subset_size,
                        "risk_percent": base.risk_percent,
                        "max_leverage": base.max_leverage,
                        "spread_multiplier": base.spread_multiplier,
                        "commission_per_unit": base.commission_per_unit_per_side,
                        "use_minimum_lot": base.use_minimum_lot,
                    }
                    train = simulate_portfolio(start=start, end=training_end, **subset_kwargs)
                    validation = simulate_portfolio(start=validation_start, end=end, **subset_kwargs)
                    full = simulate_portfolio(start=start, end=end, **subset_kwargs)
                    rows.append(
                        {
                            "selection_method": "training_positive_symbols",
                            "selected_symbols": ",".join(selected_symbols),
                            "range_minutes": range_minutes,
                            "atr_stop_fraction": stop_fraction,
                            "relative_volume_min": relative_volume_min,
                            "top_n": subset_size,
                            "robust_score": _robust_score(train, validation),
                            **{f"train_{key}": value for key, value in _summary(train).items()},
                            **{f"validation_{key}": value for key, value in _summary(validation).items()},
                            **{f"full_{key}": value for key, value in _summary(full).items()},
                        }
                    )
    rows.sort(key=lambda item: (float(item["robust_score"]), float(item["full_return_percent"])), reverse=True)
    best_config = rows[0]
    raw_best_config = max(rows, key=lambda item: float(item["full_return_percent"]))
    best_setups = setups_by_range[int(best_config["range_minutes"])]
    selected_symbols = tuple(item for item in str(best_config["selected_symbols"]).split(",") if item)
    best_setups = [item for item in best_setups if item["symbol"] in selected_symbols]
    best_full = simulate_portfolio(
        best_setups,
        metadata,
        start,
        end,
        starting_balance,
        float(best_config["atr_stop_fraction"]),
        float(best_config["relative_volume_min"]),
        int(best_config["top_n"]),
        base.risk_percent,
        base.max_leverage,
        base.spread_multiplier,
        base.commission_per_unit_per_side,
        base.use_minimum_lot,
    )

    symbol_rows: list[dict[str, Any]] = []
    for symbol in histories:
        symbol_setups = [item for item in best_setups if item["symbol"] == symbol]
        result = simulate_portfolio(
            symbol_setups,
            metadata,
            start,
            end,
            starting_balance,
            float(best_config["atr_stop_fraction"]),
            float(best_config["relative_volume_min"]),
            1,
            base.risk_percent,
            base.max_leverage,
            base.spread_multiplier,
            base.commission_per_unit_per_side,
            base.use_minimum_lot,
        )
        symbol_rows.append({"symbol": symbol, **_summary(result)})
    symbol_rows.sort(key=lambda item: float(item["return_percent"]), reverse=True)

    per_symbol_rows.sort(
        key=lambda item: (float(item["robust_score"]), float(item["full_return_percent"])),
        reverse=True,
    )
    per_symbol_best: list[dict[str, Any]] = []
    for symbol in histories:
        candidates = [item for item in per_symbol_rows if item["symbol"] == symbol]
        if candidates:
            per_symbol_best.append(candidates[0])
    per_symbol_best.sort(key=lambda item: float(item["robust_score"]), reverse=True)

    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    out_dir = REPORT_DIR / stamp
    out_dir.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_csv(out_dir / "optimization_grid.csv", index=False)
    pd.DataFrame(per_symbol_rows).to_csv(out_dir / "per_symbol_optimization.csv", index=False)
    pd.DataFrame(per_symbol_best).to_csv(out_dir / "per_symbol_best_configs.csv", index=False)
    pd.DataFrame(symbol_rows).to_csv(out_dir / "best_config_by_symbol.csv", index=False)
    pd.DataFrame(best_full["trade_rows"]).to_csv(out_dir / "best_config_trades.csv", index=False)
    pd.DataFrame(best_full["equity_curve"]).to_csv(out_dir / "best_config_equity.csv", index=False)
    report = {
        "paper": "A Profitable Day Trading Strategy For The U.S. Equity Market",
        "paper_rules": {
            "direction": "direction of first opening-range candle",
            "entry": "stop order at opening-range high/low",
            "relative_volume": "opening-range volume divided by prior 14-session average",
            "stop": "fraction of prior 14-session daily ATR",
            "exit": "stop loss or end of regular session",
        },
        "adaptations": [
            "MT5 provides tick-volume proxy rather than consolidated share volume.",
            "The paper's 1,000,000-share daily-volume filter is disabled because tick volume is not shares.",
            "Spread and round-trip per-unit commission are included.",
        ],
        "requested_period": {"start": str(start), "end": str(end), "calendar_days": (end - start).days},
        "walk_forward": {"training_end": str(training_end), "validation_start": str(validation_start)},
        "starting_balance": starting_balance,
        "risk_percent_per_trade": base.risk_percent,
        "max_portfolio_leverage": base.max_leverage,
        "symbols_requested": list(symbols),
        "symbols_tested": list(histories),
        "availability": availability,
        "best_config": best_config,
        "robust_selection_passed": _configuration_passed(best_config),
        "raw_full_period_best_config": raw_best_config,
        "best_full_result": _summary(best_full),
        "best_symbols": symbol_rows,
        "per_symbol_best_configs": per_symbol_best,
        "top_configs": rows[:20],
        "output_directory": str(out_dir),
    }
    (out_dir / "report.json").write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
    (out_dir / "summary.md").write_text(_markdown_report(report), encoding="utf-8")
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description="Optimize the paper's relative-volume ORB on MT5 stocks.")
    parser.add_argument("--days", type=int, default=60)
    parser.add_argument("--balance", type=float, default=300.0)
    parser.add_argument("--symbols", default=",".join(PAPER_TOP_SYMBOLS))
    parser.add_argument("--ranges", default="5,15,30,60")
    parser.add_argument("--stops", default="0.05,0.075,0.10,0.15,0.20")
    parser.add_argument("--relative-volumes", default="0.75,1.0,1.25,1.5,2.0")
    parser.add_argument("--top-n", default="1,3,5,10,20")
    parser.add_argument("--refresh", action="store_true")
    args = parser.parse_args()
    end = date.today() - timedelta(days=1)
    start = end - timedelta(days=max(1, args.days))
    report = run_optimization(
        symbols=tuple(item.strip().upper() for item in args.symbols.split(",") if item.strip()),
        start=start,
        end=end,
        starting_balance=args.balance,
        range_values=_parse_csv(args.ranges, int, (5, 15, 30, 60)),
        stop_values=_parse_csv(args.stops, float, (0.05, 0.075, 0.10, 0.15, 0.20)),
        relative_volume_values=_parse_csv(args.relative_volumes, float, (0.75, 1.0, 1.25, 1.5, 2.0)),
        top_n_values=_parse_csv(args.top_n, int, (1, 3, 5, 10, 20)),
        refresh=args.refresh,
    )
    print(json.dumps(report, indent=2, default=str))


if __name__ == "__main__":
    main()
