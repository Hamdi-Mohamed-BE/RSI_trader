from __future__ import annotations

import argparse
from datetime import datetime, timedelta, timezone
import json
import logging
from pathlib import Path

import pandas as pd

from .config import load_config
from .engine import backtest, calculate_metrics
from .live import run_live
from .mt5_data import (
    discover_symbols,
    ensure_account,
    load_or_fetch_m1,
    mt5_connection,
    symbol_metadata,
)
from .optimizer import optimize_symbol, universal_config_summary
from .observability import log_event, setup_logging
from .portfolio import simulate_portfolio


ROOT = Path(__file__).resolve().parents[2]
LOGGER = logging.getLogger("asia_breakout.cli")


def _utc_date(text: str) -> datetime:
    return datetime.strptime(text, "%Y-%m-%d").replace(tzinfo=timezone.utc)


def _dates(args: argparse.Namespace) -> tuple[datetime, datetime, datetime]:
    end = _utc_date(args.end) if args.end else datetime.now(timezone.utc)
    start = _utc_date(args.start) if args.start else end - timedelta(days=60)
    warmup = start - timedelta(days=30)
    return warmup, start, end


def _write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, default=str), encoding="utf-8")


def _strategy_record(row: dict[str, object]) -> dict[str, object]:
    keys = (
        "entry_mode",
        "stop_mode",
        "rr",
        "exit_mode",
        "trail_start_r",
        "trail_distance_r",
        "buffer_range_fraction",
        "min_range_adr_fraction",
        "max_range_adr_fraction",
        "retest_bars",
    )
    return {key: row[key] for key in keys}


def _basket_metrics(
    trades_by_symbol: dict[str, pd.DataFrame],
    starting_balance: float,
    risk_pct: float,
) -> dict[str, object]:
    frames = [frame for frame in trades_by_symbol.values() if not frame.empty]
    if not frames:
        return {}
    trades = pd.concat(frames, ignore_index=True)
    trades["entry_time"] = pd.to_datetime(trades["entry_time"], utc=True)
    trades["exit_time"] = pd.to_datetime(trades["exit_time"], utc=True)
    pnl = trades["pnl_r"].astype(float)
    gross_profit = float(pnl.clip(lower=0).sum())
    gross_loss = float(abs(pnl.clip(upper=0).sum()))

    events: list[tuple[pd.Timestamp, int, int]] = []
    for index, row in trades.iterrows():
        events.append((row["entry_time"], 1, index))
        events.append((row["exit_time"], -1, index))
    # Process exits before new entries at exactly the same timestamp.
    events.sort(key=lambda event: (event[0], event[1]))
    balance = starting_balance
    peak = balance
    max_realized_dd = 0.0
    active_risk: dict[int, float] = {}
    active = 0
    max_active = 0
    for _, event_type, index in events:
        if event_type == 1:
            active_risk[index] = balance * risk_pct / 100.0
            active += 1
            max_active = max(max_active, active)
        else:
            risk_cash = active_risk.pop(index, 0.0)
            balance += risk_cash * float(trades.loc[index, "pnl_r"])
            active = max(0, active - 1)
            peak = max(peak, balance)
            if peak > 0:
                max_realized_dd = max(
                    max_realized_dd,
                    (peak - balance) / peak * 100.0,
                )
    wins = int((pnl > 1e-9).sum())
    losses = int((pnl < -1e-9).sum())
    return {
        "symbols": sorted(trades["symbol"].unique().tolist()),
        "trades": int(len(trades)),
        "wins": wins,
        "losses": losses,
        "breakeven": int(len(trades) - wins - losses),
        "win_rate_pct": wins / len(trades) * 100.0,
        "profit_factor": gross_profit / gross_loss if gross_loss else float("inf"),
        "net_r": float(pnl.sum()),
        "starting_balance": starting_balance,
        "ending_balance": balance,
        "return_pct": (balance / starting_balance - 1.0) * 100.0,
        "max_realized_drawdown_pct": max_realized_dd,
        "max_concurrent_trades": max_active,
        "max_planned_risk_pct": max_active * risk_pct,
    }


def command_optimize(args: argparse.Namespace) -> None:
    config = load_config(args.env)
    setup_logging(config.log_dir, config.log_level)
    instruments = tuple(args.symbols.split(",")) if args.symbols else config.symbols
    warmup, start, end = _dates(args)
    cache = ROOT / "data"
    reports = ROOT / "reports"
    reports.mkdir(parents=True, exist_ok=True)
    summary: list[dict[str, object]] = []
    grids: list[pd.DataFrame] = []
    best_trades_by_symbol: dict[str, pd.DataFrame] = {}
    exit_comparison: list[dict[str, object]] = []
    with mt5_connection(config):
        symbol_map = discover_symbols(instruments)
        for instrument, symbol in symbol_map.items():
            ensure_account(config)
            print(f"Downloading/testing {instrument} -> {symbol}...")
            metadata = symbol_metadata(symbol)
            frame = load_or_fetch_m1(symbol, warmup, end, cache, args.refresh)
            results, trades = optimize_symbol(
                frame,
                symbol,
                float(metadata["point"]),
                config.strategy,
                start,
                end,
            )
            results["canonical_symbol"] = instrument
            results.to_csv(reports / f"{symbol.replace('.', '_')}_grid.csv", index=False)
            grids.append(results)
            trades.to_csv(reports / f"{symbol.replace('.', '_')}_best_trades.csv", index=False)
            best_trades_by_symbol[instrument] = trades
            best_by_rr = (
                results.sort_values("score", ascending=False)
                .groupby("rr", as_index=False)
                .first()
                .sort_values("rr")
            )
            best_by_rr.to_csv(
                reports / f"{symbol.replace('.', '_')}_rr_summary.csv",
                index=False,
            )
            for exit_mode in ("fixed", "trailing"):
                choices = results[results["exit_mode"] == exit_mode]
                if not choices.empty:
                    exit_comparison.append(
                        {"comparison": exit_mode, **choices.iloc[0].to_dict()}
                    )
            best = results.iloc[0].to_dict()
            best["canonical_symbol"] = instrument
            summary.append(best)
            print(
                f"{symbol}: {best['entry_mode']} {best['stop_mode']} "
                f"RR {best['rr']} | PF {best['profit_factor']:.2f} | "
                f"WR {best['win_rate_pct']:.1f}% | DD {best['max_drawdown_pct']:.1f}% | "
                f"ending ${best['ending_balance']:.2f}"
            )
            log_event(
                LOGGER,
                logging.INFO,
                "optimization_symbol_complete",
                f"Optimization completed for {instrument}",
                instrument=instrument,
                broker_symbol=symbol,
                entry_mode=best["entry_mode"],
                stop_mode=best["stop_mode"],
                rr=best["rr"],
                exit_mode=best["exit_mode"],
                profit_factor=best["profit_factor"],
                win_rate_pct=best["win_rate_pct"],
                max_drawdown_pct=best["max_drawdown_pct"],
                ending_balance=best["ending_balance"],
            )
    summary_frame = pd.DataFrame(summary).sort_values("score", ascending=False)
    summary_frame.to_csv(reports / "optimization_summary.csv", index=False)
    pd.DataFrame(exit_comparison).to_csv(
        reports / "exit_comparison.csv",
        index=False,
    )
    universal = universal_config_summary(pd.concat(grids, ignore_index=True))
    universal.to_csv(reports / "universal_config_summary.csv", index=False)
    configs = {
        row["canonical_symbol"]: {
            "strategy": _strategy_record(row),
            "metrics": {
                key: row[key]
                for key in (
                    "trades",
                    "win_rate_pct",
                    "profit_factor",
                    "net_r",
                    "max_drawdown_pct",
                    "ending_balance",
                    "first_half_net_r",
                    "second_half_net_r",
                )
            },
        }
        for row in summary
    }
    config_dir = ROOT / "configs"
    _write_json(config_dir / "best_symbols.json", configs)
    pf3_symbols = {
        str(row["canonical_symbol"])
        for row in summary
        if float(row["profit_factor"]) >= 3.0
    }
    pf3_configs = {
        symbol: configs[symbol] for symbol in sorted(pf3_symbols)
    }
    _write_json(config_dir / "pf3_basket.json", pf3_configs)
    pf3_trades = {
        symbol: frame
        for symbol, frame in best_trades_by_symbol.items()
        if symbol in pf3_symbols
    }
    _write_json(
        reports / "pf3_basket_metrics.json",
        _basket_metrics(
            pf3_trades,
            config.strategy.starting_balance,
            config.strategy.risk_pct,
        ),
    )
    _write_json(
        reports / "run_metadata.json",
        {
            "warmup_start": warmup,
            "test_start": start,
            "test_end": end,
            "starting_balance": config.strategy.starting_balance,
            "risk_pct": config.strategy.risk_pct,
            "symbols": symbol_map,
        },
    )
    print(f"\nSaved: {reports / 'optimization_summary.csv'}")
    print(f"Universal winner saved: {reports / 'universal_config_summary.csv'}")


def command_backtest(args: argparse.Namespace) -> None:
    config = load_config(args.env)
    setup_logging(config.log_dir, config.log_level)
    instruments = tuple(args.symbols.split(",")) if args.symbols else config.symbols
    warmup, start, end = _dates(args)
    cache = ROOT / "data"
    rows: list[dict[str, object]] = []
    with mt5_connection(config):
        symbol_map = discover_symbols(instruments)
        for instrument, symbol in symbol_map.items():
            ensure_account(config)
            metadata = symbol_metadata(symbol)
            frame = load_or_fetch_m1(symbol, warmup, end, cache, args.refresh)
            strategy = config.strategy_for(instrument)
            trades = backtest(
                frame,
                symbol,
                float(metadata["point"]),
                strategy,
                start,
                end,
            )
            metrics = calculate_metrics(
                trades,
                symbol,
                strategy.starting_balance,
                strategy.risk_pct,
            )
            rows.append(metrics.to_dict())
            rows[-1]["instrument"] = instrument
            log_event(
                LOGGER,
                logging.INFO,
                "backtest_symbol_complete",
                f"Backtest completed for {instrument}",
                instrument=instrument,
                broker_symbol=symbol,
                **metrics.to_dict(),
            )
    print(pd.DataFrame(rows).to_string(index=False))


def _parse_scenarios(text: str) -> list[tuple[float, float]]:
    scenarios: list[tuple[float, float]] = []
    for item in text.split(","):
        try:
            risk_text, cap_text = item.strip().split(":", maxsplit=1)
            risk_pct = float(risk_text)
            cap_pct = float(cap_text)
        except ValueError as error:
            raise ValueError(
                f"Invalid scenario {item!r}; use risk:cap, e.g. 3:9,1:6,1:9"
            ) from error
        if risk_pct <= 0 or cap_pct <= 0 or risk_pct > cap_pct:
            raise ValueError(
                f"Invalid scenario {item!r}; require 0 < risk <= exposure cap"
            )
        scenarios.append((risk_pct, cap_pct))
    return scenarios


def _write_portfolio_detail_reports(
    reports: Path,
    label: str,
    audit: pd.DataFrame,
    starting_balance: float,
) -> tuple[Path, Path, Path]:
    accepted = audit[audit["portfolio_status"] == "accepted"].copy()
    accepted["entry_time"] = pd.to_datetime(accepted["entry_time"], utc=True)
    accepted["exit_time"] = pd.to_datetime(accepted["exit_time"], utc=True)
    accepted = accepted.sort_values("portfolio_exit_sequence")

    monthly_rows: list[dict[str, object]] = []
    accepted["month"] = accepted["exit_time"].dt.strftime("%Y-%m")
    for month, group in accepted.groupby("month", sort=True):
        group = group.sort_values("portfolio_exit_sequence")
        pnl_r = group["pnl_r"].astype(float)
        pnl_cash = group["portfolio_pnl_cash"].astype(float)
        gross_profit = float(pnl_r.clip(lower=0).sum())
        gross_loss = float(abs(pnl_r.clip(upper=0).sum()))
        first = group.iloc[0]
        month_start_balance = float(
            first["portfolio_balance_after_exit"] - first["portfolio_pnl_cash"]
        )
        month_end_balance = float(group.iloc[-1]["portfolio_balance_after_exit"])
        peak = month_start_balance
        month_dd = 0.0
        for value in group["portfolio_balance_after_exit"].astype(float):
            peak = max(peak, value)
            if peak > 0:
                month_dd = max(month_dd, (peak - value) / peak * 100.0)
        wins = int((pnl_r > 1e-9).sum())
        losses = int((pnl_r < -1e-9).sum())
        monthly_rows.append(
            {
                "month": month,
                "trades": int(len(group)),
                "wins": wins,
                "losses": losses,
                "win_rate_pct": wins / len(group) * 100.0,
                "profit_factor": (
                    gross_profit / gross_loss
                    if gross_loss
                    else float("inf") if gross_profit else 0.0
                ),
                "net_r": float(pnl_r.sum()),
                "net_profit": float(pnl_cash.sum()),
                "starting_balance": month_start_balance,
                "ending_balance": month_end_balance,
                "return_pct": (
                    (month_end_balance / month_start_balance - 1.0) * 100.0
                    if month_start_balance
                    else 0.0
                ),
                "max_realized_drawdown_pct": month_dd,
                "symbols_traded": ",".join(sorted(group["instrument"].unique())),
            }
        )
    monthly_path = reports / f"{label}_monthly.csv"
    pd.DataFrame(monthly_rows).to_csv(monthly_path, index=False)

    symbol_rows: list[dict[str, object]] = []
    journals = reports / "journals" / label
    journals.mkdir(parents=True, exist_ok=True)
    journal_columns = [
        "instrument",
        "symbol",
        "session_date",
        "direction",
        "entry_mode",
        "stop_mode",
        "exit_mode",
        "rr_target",
        "entry_time",
        "exit_time",
        "entry",
        "stop",
        "target",
        "exit_price",
        "pnl_r",
        "outcome",
        "portfolio_risk_cash",
        "portfolio_pnl_cash",
        "portfolio_balance_after_exit",
        "asian_high",
        "asian_low",
        "asian_range",
        "adr",
        "range_adr_fraction",
        "mae_r",
        "ambiguous_bar",
    ]
    for instrument, group in accepted.groupby("instrument", sort=True):
        group = group.sort_values("entry_time")
        available_columns = [
            column for column in journal_columns if column in group.columns
        ]
        group[available_columns].to_csv(
            journals / f"{instrument}_journal.csv",
            index=False,
        )
        pnl_r = group["pnl_r"].astype(float)
        pnl_cash = group["portfolio_pnl_cash"].astype(float)
        gross_profit = float(pnl_r.clip(lower=0).sum())
        gross_loss = float(abs(pnl_r.clip(upper=0).sum()))
        wins = int((pnl_r > 1e-9).sum())
        symbol_rows.append(
            {
                "instrument": instrument,
                "trades": int(len(group)),
                "wins": wins,
                "losses": int((pnl_r < -1e-9).sum()),
                "win_rate_pct": wins / len(group) * 100.0,
                "profit_factor": (
                    gross_profit / gross_loss
                    if gross_loss
                    else float("inf") if gross_profit else 0.0
                ),
                "net_r": float(pnl_r.sum()),
                "net_profit": float(pnl_cash.sum()),
                "average_r": float(pnl_r.mean()),
                "worst_mae_r": (
                    float(group["mae_r"].astype(float).min())
                    if "mae_r" in group
                    else float("nan")
                ),
            }
        )
    symbol_summary_path = reports / f"{label}_by_symbol.csv"
    pd.DataFrame(symbol_rows).to_csv(symbol_summary_path, index=False)

    journal_path = reports / f"{label}_trade_journal.csv"
    available_columns = [
        column for column in journal_columns if column in accepted.columns
    ]
    accepted[available_columns].to_csv(journal_path, index=False)
    return monthly_path, symbol_summary_path, journal_path


def command_portfolio(args: argparse.Namespace) -> None:
    """Backtest frozen symbol strategies through a shared exposure-capped account."""
    config = load_config(args.env)
    setup_logging(config.log_dir, config.log_level)
    instruments = tuple(args.symbols.split(",")) if args.symbols else config.symbols
    scenarios = _parse_scenarios(args.scenarios)
    warmup, start, end = _dates(args)
    cache = ROOT / "data"
    reports = ROOT / "reports"
    reports.mkdir(parents=True, exist_ok=True)
    trades_by_instrument: dict[str, pd.DataFrame] = {}

    with mt5_connection(config):
        symbol_map = discover_symbols(instruments)
        for instrument, symbol in symbol_map.items():
            ensure_account(config)
            metadata = symbol_metadata(symbol)
            frame = load_or_fetch_m1(symbol, warmup, end, cache, args.refresh)
            strategy = config.strategy_for(instrument)
            trades = backtest(
                frame,
                symbol,
                float(metadata["point"]),
                strategy,
                start,
                end,
            )
            trades_by_instrument[instrument] = pd.DataFrame(
                trade.to_dict() for trade in trades
            )
            print(f"Prepared {instrument}: {len(trades)} signals")

    rows: list[dict[str, object]] = []
    for risk_pct, cap_pct in scenarios:
        result, audit = simulate_portfolio(
            trades_by_instrument,
            starting_balance=config.strategy.starting_balance,
            risk_pct=risk_pct,
            exposure_cap_pct=cap_pct,
            priority=instruments,
        )
        record = result.to_dict()
        record["scenario"] = f"{risk_pct:g}% risk / {cap_pct:g}% cap"
        record["test_start"] = start.date().isoformat()
        record["test_end"] = end.date().isoformat()
        rows.append(record)
        risk_label = f"{risk_pct:g}".replace(".", "_")
        cap_label = f"{cap_pct:g}".replace(".", "_")
        filename = f"portfolio_{risk_label}pct_cap{cap_label}pct_audit.csv"
        audit.to_csv(reports / filename, index=False)
        label = f"portfolio_{risk_label}pct_cap{cap_label}pct"
        monthly_path, symbol_summary_path, journal_path = (
            _write_portfolio_detail_reports(
                reports,
                label,
                audit,
                config.strategy.starting_balance,
            )
        )
        record["monthly_report"] = str(monthly_path)
        record["symbol_report"] = str(symbol_summary_path)
        record["trade_journal"] = str(journal_path)
        log_event(
            LOGGER,
            logging.INFO,
            "portfolio_backtest_complete",
            f"Portfolio backtest completed at {risk_pct:g}% risk / {cap_pct:g}% cap",
            **record,
        )

    summary = pd.DataFrame(rows)
    columns = [
        "scenario",
        "signals",
        "accepted_trades",
        "skipped_signals",
        "win_rate_pct",
        "profit_factor",
        "net_r",
        "ending_balance",
        "return_pct",
        "max_realized_drawdown_pct",
        "max_committed_risk_drawdown_pct",
        "max_concurrent_trades",
        "max_planned_exposure_pct",
    ]
    summary.to_csv(reports / "exposure_scenarios.csv", index=False)
    print("\n" + summary[columns].to_string(index=False))
    print(f"\nSaved: {reports / 'exposure_scenarios.csv'}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Asian-session breakout research bot")
    subparsers = parser.add_subparsers(dest="command", required=True)
    for name in ("optimize", "backtest", "portfolio"):
        item = subparsers.add_parser(name)
        item.add_argument("--start", help="UTC start date YYYY-MM-DD")
        item.add_argument("--end", help="UTC end date YYYY-MM-DD")
        item.add_argument("--env", default=".env")
        item.add_argument("--refresh", action="store_true")
        item.add_argument(
            "--symbols",
            help="Optional comma-separated canonical instruments, e.g. XAUUSD,BTCUSD",
        )
        if name == "portfolio":
            item.add_argument(
                "--scenarios",
                default="3:9,1:6,1:9",
                help="Comma-separated risk:cap percentages",
            )
    live = subparsers.add_parser("live")
    live.add_argument("--env", default=".env")
    live.add_argument("--once", action="store_true")
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    if args.command == "optimize":
        command_optimize(args)
    elif args.command == "backtest":
        command_backtest(args)
    elif args.command == "portfolio":
        command_portfolio(args)
    else:
        config = load_config(args.env)
        setup_logging(config.log_dir, config.log_level)
        run_live(config, once=args.once)


if __name__ == "__main__":
    main()
