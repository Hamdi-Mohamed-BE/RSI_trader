from __future__ import annotations

from dataclasses import asdict
from datetime import date, datetime, time, timedelta, timezone
from itertools import product
import csv
import json
import math

from .config import StrategyConfig, load_runtime
from .engine import calculate_metrics, prepare_frame, run_backtest
from .market import (
    fetch_m5,
    initialize,
    resolve_symbol,
    shutdown,
    symbol_info,
)
from .models import Trade


def candidate_configs() -> list[StrategyConfig]:
    candidates: list[StrategyConfig] = []
    model_sets = (
        ("retest",),
        ("sweep", "rejection"),
        ("retest", "sweep", "rejection"),
        ("straight",),
    )
    for models in model_sets:
        has_retest = "retest" in models
        retest_options = product(
            (3, 6) if has_retest else (4,),
            (False, True) if has_retest else (False,),
        )
        for retest_bars, require_fvg in retest_options:
            for body, volume, rr, bias in product(
                (0.55, 0.70),
                (1.00, 1.25),
                (2.0, 3.0),
                (False, True),
            ):
                candidates.append(
                    StrategyConfig(
                        models=models,
                        breakout_body_min=body,
                        relative_volume_min=volume,
                        retest_bars=retest_bars,
                        retest_tolerance_atr=0.25,
                        rejection_body_min=0.35,
                        stop_buffer_atr=0.10,
                        sweep_excursion_atr=0.05,
                        target_rr=rr,
                        use_h1_bias=bias,
                        require_fvg=require_fvg,
                        move_to_be_at_r=1.0,
                        partial_at_r=2.0,
                        partial_fraction=0.5 if rr >= 3.0 else 0.0,
                    )
                )
    unique = {candidate.key(): candidate for candidate in candidates}
    return list(unique.values())


def _rebased_metrics(trades: list[Trade], starting_balance: float, risk_percent: float):
    balance = starting_balance
    rebased: list[Trade] = []
    for original in trades:
        risk_amount = balance * risk_percent / 100.0
        pnl = risk_amount * original.r_multiple
        clone = Trade(
            **{
                **original.to_dict(),
                "risk_amount": risk_amount,
                "pnl": pnl,
                "balance_after": balance + pnl,
            }
        )
        rebased.append(clone)
        balance = clone.balance_after
    return calculate_metrics(rebased, starting_balance)


def _profit_factor(value: float | str) -> float:
    if value == "inf":
        return 10.0
    return float(value)


def _rank_candidate(train, validation, full) -> tuple[float, bool]:
    robust = (
        train.trades >= 3
        and validation.trades >= 2
        and train.average_r > 0
        and validation.average_r > 0
        and _profit_factor(train.profit_factor) > 1.0
        and _profit_factor(validation.profit_factor) > 1.0
    )
    evidence = min(full.trades, 20) * 0.03
    edge = min(train.average_r, validation.average_r) * 6.0
    validation_weight = validation.average_r * 2.0
    drawdown_penalty = (
        train.max_drawdown_percent + validation.max_drawdown_percent
    ) * 0.08
    score = edge + validation_weight + evidence - drawdown_penalty
    if not robust:
        score -= 5.0
    return score, robust


def _portfolio_metrics(
    selected_trades: dict[str, list[Trade]],
    starting_balance: float,
    risk_percent: float,
    max_daily_losses: int,
) -> dict:
    ordered = sorted(
        (
            trade
            for trades in selected_trades.values()
            for trade in trades
        ),
        key=lambda trade: (trade.entry_time, trade.symbol),
    )
    balance = starting_balance
    curve = [balance]
    gross_profit = 0.0
    gross_loss = 0.0
    wins = 0
    losses = 0
    breakeven = 0
    skipped = 0
    accepted = 0
    open_trades: list[tuple[datetime, float, Trade]] = []
    daily_losses: dict[str, int] = {}

    def settle(until: datetime | None = None) -> None:
        nonlocal balance, gross_profit, gross_loss, wins, losses, breakeven
        ready = [
            item
            for item in open_trades
            if until is None or item[0] <= until
        ]
        ready.sort(key=lambda item: (item[0], item[2].symbol))
        for item in ready:
            open_trades.remove(item)
            _, pnl, trade = item
            balance += pnl
            curve.append(balance)
            if pnl > 1e-9:
                gross_profit += pnl
                wins += 1
            elif pnl < -1e-9:
                gross_loss += abs(pnl)
                losses += 1
                daily_losses[trade.session_date] = (
                    daily_losses.get(trade.session_date, 0) + 1
                )
            else:
                breakeven += 1

    for trade in ordered:
        entry_time = datetime.fromisoformat(trade.entry_time)
        settle(entry_time)
        if daily_losses.get(trade.session_date, 0) >= max_daily_losses:
            skipped += 1
            continue
        pnl = balance * risk_percent / 100.0 * trade.r_multiple
        open_trades.append(
            (datetime.fromisoformat(trade.exit_time), pnl, trade)
        )
        accepted += 1
    settle()
    peak = starting_balance
    max_drawdown = 0.0
    for value in curve:
        peak = max(peak, value)
        max_drawdown = max(max_drawdown, (peak - value) / peak * 100.0)
    factor = gross_profit / gross_loss if gross_loss else (
        math.inf if gross_profit else 0.0
    )
    return {
        "starting_balance": round(starting_balance, 2),
        "ending_balance": round(balance, 2),
        "net_profit": round(balance - starting_balance, 2),
        "return_percent": round(
            (balance / starting_balance - 1.0) * 100.0, 2
        ),
        "trades": accepted,
        "wins": wins,
        "losses": losses,
        "breakeven": breakeven,
        "skipped_after_daily_loss_limit": skipped,
        "win_rate": round(wins / accepted * 100.0, 2) if accepted else 0.0,
        "profit_factor": round(factor, 3) if math.isfinite(factor) else "inf",
        "max_drawdown_percent": round(max_drawdown, 2),
    }


def run() -> dict:
    runtime = load_runtime()
    end_date = datetime.now(runtime.timezone).date() - timedelta(days=1)
    start_date = end_date - timedelta(days=runtime.backtest_days)
    warmup_start = start_date - timedelta(days=20)
    start_utc = datetime.combine(warmup_start, time.min, tzinfo=timezone.utc)
    end_utc = datetime.combine(
        end_date + timedelta(days=1), time.min, tzinfo=timezone.utc
    )
    split_date = start_date + timedelta(
        days=round((end_date - start_date).days * 0.70)
    )
    candidates = candidate_configs()
    print(
        f"ORB2 optimization: {len(candidates)} candidates per symbol, "
        f"{start_date} to {end_date}, validation starts {split_date}.",
        flush=True,
    )

    initialize(runtime)
    datasets = {}
    failures = {}
    try:
        for requested in runtime.symbols:
            try:
                broker_symbol = resolve_symbol(requested)
                info = symbol_info(broker_symbol)
                print(
                    f"Downloading/caching {requested} -> {broker_symbol}...",
                    flush=True,
                )
                frame = fetch_m5(
                    runtime, broker_symbol, start_utc, end_utc
                )
                datasets[requested] = (
                    broker_symbol,
                    info,
                    prepare_frame(frame),
                )
                print(
                    f"  {len(frame):,} M5 bars "
                    f"({frame.index[0].date()} to {frame.index[-1].date()})",
                    flush=True,
                )
            except Exception as exc:
                failures[requested] = str(exc)
                print(f"  FAILED: {exc}", flush=True)
    finally:
        shutdown()

    symbol_reports = {}
    selected_configs = {}
    selected_trades = {}
    for requested, (broker_symbol, info, frame) in datasets.items():
        print(f"Optimizing {requested}...", flush=True)
        rankings = []
        trade_lookup: dict[str, list[Trade]] = {}
        for index, config in enumerate(candidates, start=1):
            trades, full_metrics, reasons = run_backtest(
                broker_symbol,
                frame,
                info.point,
                runtime,
                config,
                start_date,
                end_date,
            )
            train_trades = [
                trade
                for trade in trades
                if date.fromisoformat(trade.session_date) < split_date
            ]
            validation_trades = [
                trade
                for trade in trades
                if date.fromisoformat(trade.session_date) >= split_date
            ]
            train = _rebased_metrics(
                train_trades,
                runtime.starting_balance,
                runtime.risk_percent,
            )
            validation = _rebased_metrics(
                validation_trades,
                runtime.starting_balance,
                runtime.risk_percent,
            )
            score, robust = _rank_candidate(
                train, validation, full_metrics
            )
            rankings.append(
                {
                    "score": round(score, 6),
                    "robust": robust,
                    "config": asdict(config),
                    "config_key": config.key(),
                    "train": train.to_dict(),
                    "validation": validation.to_dict(),
                    "full": full_metrics.to_dict(),
                    "reasons": reasons,
                }
            )
            trade_lookup[config.key()] = trades
            if index % 40 == 0:
                print(
                    f"  {requested}: {index}/{len(candidates)} candidates",
                    flush=True,
                )
        rankings.sort(
            key=lambda item: (
                item["robust"],
                item["score"],
                item["validation"]["trades"],
                item["full"]["trades"],
            ),
            reverse=True,
        )
        best = rankings[0]
        full = best["full"]
        validation = best["validation"]
        enabled = bool(
            best["robust"]
            and full["trades"] >= 6
            and _profit_factor(full["profit_factor"]) >= 1.10
            and validation["trades"] >= 2
        )
        selected_configs[requested] = {
            "enabled": enabled,
            "broker_symbol": broker_symbol,
            "point": info.point,
            "volume_min": info.volume_min,
            "volume_step": info.volume_step,
            "spread_current_points": info.spread,
            "config": best["config"],
            "selection": {
                "robust": best["robust"],
                "score": best["score"],
                "train": best["train"],
                "validation": validation,
                "full": full,
            },
        }
        if enabled:
            selected_trades[requested] = trade_lookup[best["config_key"]]
        symbol_reports[requested] = {
            **selected_configs[requested],
            "top_candidates": rankings[:10],
            "selected_trades": [
                trade.to_dict()
                for trade in trade_lookup[best["config_key"]]
            ],
        }
        print(
            f"  selected {best['config_key']} | enabled={enabled} | "
            f"trades={full['trades']} PF={full['profit_factor']} "
            f"return={full['return_percent']}% validation "
            f"PF={validation['profit_factor']}",
            flush=True,
        )

    portfolio = _portfolio_metrics(
        selected_trades,
        runtime.starting_balance,
        runtime.risk_percent,
        runtime.max_daily_losses,
    )
    report = {
        "source": "The ORB Playbook - Mind Over Markets",
        "period": {
            "start": start_date.isoformat(),
            "validation_start": split_date.isoformat(),
            "end": end_date.isoformat(),
        },
        "data_source": "JustMarkets MT5 historical M5 bars",
        "starting_balance": runtime.starting_balance,
        "risk_percent": runtime.risk_percent,
        "candidate_count_per_symbol": len(candidates),
        "symbols": symbol_reports,
        "portfolio_enabled_symbols": sorted(selected_trades),
        "portfolio": portfolio,
        "data_failures": failures,
        "methodology": {
            "opening_range": "09:30-09:45 America/New_York",
            "execution_timeframe": "M5",
            "training_fraction": 0.70,
            "validation_fraction": 0.30,
            "minimum_rr": 2.0,
            "break_even_at_r": 1.0,
            "same_bar_policy": "stop_first",
            "weekends": "disabled",
            "max_trades_per_symbol_day": 1,
        },
        "warnings": [
            "Tick volume is a broker activity proxy, not centralized exchange volume.",
            "Commission and swap are not included; historical spread and configured slippage are included.",
            "Optimization cannot guarantee future performance. Validation sample size is reported for every selection.",
        ],
    }

    report_dir = runtime.root / "reports"
    report_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    report_path = report_dir / f"orb2_optimization_{stamp}.json"
    summary_path = report_dir / f"orb2_summary_{stamp}.csv"
    defaults_path = runtime.root / "optimized_configs.json"
    report["report_files"] = {
        "json": str(report_path),
        "summary_csv": str(summary_path),
        "optimized_configs": str(defaults_path),
    }
    report_path.write_text(
        json.dumps(report, indent=2, default=str), encoding="utf-8"
    )
    with summary_path.open("w", encoding="utf-8", newline="") as handle:
        fields = [
            "symbol",
            "broker_symbol",
            "enabled",
            "models",
            "target_rr",
            "trades",
            "win_rate",
            "profit_factor",
            "return_percent",
            "max_drawdown_percent",
            "validation_trades",
            "validation_profit_factor",
        ]
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for symbol, item in selected_configs.items():
            full = item["selection"]["full"]
            validation = item["selection"]["validation"]
            writer.writerow(
                {
                    "symbol": symbol,
                    "broker_symbol": item["broker_symbol"],
                    "enabled": item["enabled"],
                    "models": "+".join(item["config"]["models"]),
                    "target_rr": item["config"]["target_rr"],
                    "trades": full["trades"],
                    "win_rate": full["win_rate"],
                    "profit_factor": full["profit_factor"],
                    "return_percent": full["return_percent"],
                    "max_drawdown_percent": full["max_drawdown_percent"],
                    "validation_trades": validation["trades"],
                    "validation_profit_factor": validation["profit_factor"],
                }
            )
    defaults_path.write_text(
        json.dumps(selected_configs, indent=2, default=str),
        encoding="utf-8",
    )
    return report


def main() -> None:
    report = run()
    concise = {
        "period": report["period"],
        "enabled_symbols": report["portfolio_enabled_symbols"],
        "portfolio": report["portfolio"],
        "symbols": {
            symbol: {
                "enabled": item["enabled"],
                "broker_symbol": item["broker_symbol"],
                "config": item["config"],
                "train": item["selection"]["train"],
                "validation": item["selection"]["validation"],
                "full": item["selection"]["full"],
            }
            for symbol, item in report["symbols"].items()
        },
        "failures": report["data_failures"],
        "report_files": report["report_files"],
    }
    print(json.dumps(concise, indent=2, default=str))


if __name__ == "__main__":
    main()
