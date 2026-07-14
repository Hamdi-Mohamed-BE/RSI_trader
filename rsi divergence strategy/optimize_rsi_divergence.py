from __future__ import annotations

import argparse
import csv
import json
from dataclasses import asdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

import MetaTrader5 as mt5

from rsi_divergence_bot import (
    DEFAULT_CONFIGS,
    OPTIMIZED_CONFIG_PATH,
    TIMEFRAMES,
    SymbolConfig,
    TradeIdea,
    build_signals,
    combined_equity,
    rates_to_arrays,
    resolve_symbol,
    save_report,
    simulate_signal,
)


MAX_TRADES_GRID = [1, 2, 3]


def timeframe_grid(symbol: str) -> list[str]:
    default_tf = DEFAULT_CONFIGS.get(symbol, SymbolConfig(symbol, "M5", 3, 2.0, "EMA", (1.0, 1.5, 2.0))).timeframe
    return [default_tf]


def local_grid(symbol: str) -> tuple[list[int], list[float], list[str], list[tuple[float, float, float]], list[str]]:
    default = DEFAULT_CONFIGS.get(symbol, SymbolConfig(symbol, "M5", 3, 2.0, "EMA", (1.0, 1.5, 2.0), "ALL"))
    pivots = [default.pivot_len]
    stops = sorted({default.atr_sl_mult, 1.2 if default.atr_sl_mult >= 1.5 else 1.5, 2.0})
    confirmations = [default.confirmation]
    rr_values = list(dict.fromkeys([default.rr, (1.0, 1.5, 2.0), (1.0, 2.0, 3.0)]))
    sessions = list(dict.fromkeys([default.session, "ALL", "LONDON", "NY_OPEN"]))
    return pivots, stops, confirmations, rr_values, sessions


def config_to_dict(config: SymbolConfig, max_trades_per_day: int) -> dict:
    return {
        "symbol": config.symbol,
        "timeframe": config.timeframe,
        "pivot_len": config.pivot_len,
        "atr_sl_mult": config.atr_sl_mult,
        "confirmation": config.confirmation,
        "rr": list(config.rr),
        "session": config.session,
        "max_trades_per_symbol_day": max_trades_per_day,
    }


def evaluate_data_config(
    display_symbol: str,
    broker_symbol: str,
    data: dict,
    config: SymbolConfig,
    cutoff,
    start_balance: float,
    risk_percent: float,
    max_trades_per_day: int,
) -> tuple[list[TradeIdea], dict]:
    signals = [s for s in build_signals(data, config) if s["entry_time"] >= cutoff]
    balance = start_balance
    peak = balance
    max_dd = 0.0
    trades: list[TradeIdea] = []
    next_free_index = -1
    day_counts: dict[str, int] = {}

    for signal in sorted(signals, key=lambda item: item["entry_index"]):
        if signal["entry_index"] <= next_free_index:
            continue
        day_key = signal["entry_time"].date().isoformat()
        if max_trades_per_day > 0 and day_counts.get(day_key, 0) >= max_trades_per_day:
            continue
        result = simulate_signal(data, signal)
        risk_money = balance * risk_percent / 100.0
        pnl = risk_money * result["r_multiple"]
        balance += pnl
        peak = max(peak, balance)
        if peak > 0:
            max_dd = max(max_dd, (peak - balance) / peak * 100.0)
        next_free_index = int(result["exit_index"])
        day_counts[day_key] = day_counts.get(day_key, 0) + 1
        trades.append(
            TradeIdea(
                symbol=display_symbol,
                broker_symbol=broker_symbol,
                timeframe=config.timeframe,
                side=signal["side"],
                signal_time=signal["signal_time"].isoformat(),
                entry_time=signal["entry_time"].isoformat(),
                exit_time=result["exit_time"].isoformat(),
                entry=round(signal["entry"], 6),
                stop=round(signal["stop"], 6),
                tp1=round(signal["tp1"], 6),
                tp2=round(signal["tp2"], 6),
                tp3=round(signal["tp3"], 6),
                r_multiple=round(result["r_multiple"], 4),
                pnl=round(pnl, 2),
                balance_after=round(balance, 2),
                exit_reason=result["exit_reason"],
                bars_held=int(result["exit_index"] - signal["entry_index"]),
                pivot_rsi=round(signal["pivot_rsi"], 2),
                previous_rsi=round(signal["previous_rsi"], 2),
                risk_points=round(result["risk_points"], 6),
            )
        )

    wins = [t for t in trades if t.pnl > 0]
    losses = [t for t in trades if t.pnl < 0]
    gross_win = sum(t.pnl for t in wins)
    gross_loss = -sum(t.pnl for t in losses)
    stats = {
        "symbol": display_symbol,
        "broker_symbol": broker_symbol,
        "timeframe": config.timeframe,
        "confirmation": config.confirmation,
        "pivot_len": config.pivot_len,
        "atr_sl_mult": config.atr_sl_mult,
        "rr": "/".join(str(x) for x in config.rr),
        "session": config.session,
        "max_trades_per_day": max_trades_per_day,
        "trades": len(trades),
        "wins": len(wins),
        "losses": len(losses),
        "win_rate": round(len(wins) / len(trades) * 100.0, 2) if trades else 0.0,
        "start_balance": round(start_balance, 2),
        "final_balance": round(balance, 2),
        "profit": round(balance - start_balance, 2),
        "return_pct": round((balance - start_balance) / start_balance * 100.0, 2) if start_balance else 0.0,
        "max_drawdown_pct": round(max_dd, 2),
        "profit_factor": round(gross_win / gross_loss, 2) if gross_loss > 0 else (999.0 if gross_win > 0 else 0.0),
        "avg_r": round(sum(t.r_multiple for t in trades) / len(trades), 3) if trades else 0.0,
    }
    return trades, stats


def objective(stats: dict, min_trades: int) -> float:
    if stats["trades"] < min_trades:
        return -999999.0
    trade_bonus = min(stats["trades"], 60) * 0.05
    win_bonus = max(0.0, stats["win_rate"] - 50.0) * 0.20
    return stats["return_pct"] - stats["max_drawdown_pct"] * 0.35 + trade_bonus + win_bonus


def run_optimizer(args: argparse.Namespace) -> int:
    if not mt5.initialize():
        raise RuntimeError(f"MT5 initialize failed: {mt5.last_error()}")

    symbols = [s.strip().upper() for s in args.symbols.split(",") if s.strip()]
    end = datetime.now(timezone.utc)
    start = end - timedelta(days=args.days + 10)
    cutoff = end - timedelta(days=args.days)
    all_best_trades: list[TradeIdea] = []
    best_rows: list[dict] = []
    skipped: list[dict] = []
    optimized_payload = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "days": args.days,
        "balance": args.balance,
        "risk_percent": args.risk,
        "objective": "return_pct - 0.35*max_drawdown_pct + trade/win bonuses",
        "configs": {},
    }

    try:
        for symbol in symbols:
            broker_symbol = resolve_symbol(symbol)
            if not broker_symbol:
                skipped.append({"symbol": symbol, "reason": "symbol not found in MT5"})
                continue

            data_by_tf: dict[str, dict] = {}
            for tf in timeframe_grid(symbol):
                rates = mt5.copy_rates_range(broker_symbol, TIMEFRAMES[tf], start, end)
                if rates is not None and len(rates) >= 250:
                    data_by_tf[tf] = rates_to_arrays(rates)
            if not data_by_tf:
                skipped.append({"symbol": symbol, "reason": "not enough candles"})
                continue

            best: tuple[float, SymbolConfig, int, list[TradeIdea], dict] | None = None
            checked = 0
            pivot_grid, sl_grid, confirmation_grid, rr_grid, session_grid = local_grid(symbol)
            for tf, data in data_by_tf.items():
                for pivot in pivot_grid:
                    for sl_mult in sl_grid:
                        for confirmation in confirmation_grid:
                            for rr in rr_grid:
                                for session in session_grid:
                                    config = SymbolConfig(symbol, tf, pivot, sl_mult, confirmation, rr, session)
                                    for max_trades in MAX_TRADES_GRID:
                                        trades, stats = evaluate_data_config(
                                            symbol,
                                            broker_symbol,
                                            data,
                                            config,
                                            cutoff,
                                            args.balance,
                                            args.risk,
                                            max_trades,
                                        )
                                        checked += 1
                                        score = objective(stats, args.min_trades)
                                        if best is None or score > best[0]:
                                            best = (score, config, max_trades, trades, stats)

            if best is None:
                skipped.append({"symbol": symbol, "reason": "no candidate produced enough trades"})
                continue
            score, config, max_trades, trades, stats = best
            best_rows.append({**stats, "objective": round(score, 2)})
            if stats["return_pct"] > args.min_return_pct and stats["trades"] >= args.min_trades:
                all_best_trades.extend(trades)
                optimized_payload["configs"][symbol] = config_to_dict(config, max_trades)
            print(
                f"{symbol:7s} checked={checked:4d} best={config.timeframe}/{config.confirmation}/p{config.pivot_len}/"
                f"sl{config.atr_sl_mult}/rr{stats['rr']}/{config.session}/max{max_trades} "
                f"trades={stats['trades']:3d} win={stats['win_rate']:5.1f}% "
                f"return={stats['return_pct']:7.2f}% DD={stats['max_drawdown_pct']:5.1f}% obj={score:7.2f}"
                ,
                flush=True,
            )

        optimized_payload["enabled_symbols"] = list(optimized_payload["configs"].keys())
        OPTIMIZED_CONFIG_PATH.write_text(json.dumps(optimized_payload, indent=2), encoding="utf-8")

        combined = combined_equity(all_best_trades, args.balance, args.risk)
        summary = {
            "days": args.days,
            "start_balance": args.balance,
            "risk_percent": args.risk,
            "max_trades_per_symbol_day": "optimized per symbol",
            "symbols": symbols,
            "enabled_symbols": optimized_payload["enabled_symbols"],
            "combined": combined,
        }
        report_dir = save_report(Path(__file__).resolve().parent, summary, best_rows, all_best_trades, skipped)
        with (report_dir / "optimized_configs.json").open("w", encoding="utf-8") as handle:
            json.dump(optimized_payload, handle, indent=2)
        with (report_dir / "optimized_symbol_stats.csv").open("w", newline="", encoding="utf-8") as handle:
            fields = list(best_rows[0].keys()) if best_rows else ["symbol"]
            writer = csv.DictWriter(handle, fieldnames=fields)
            writer.writeheader()
            writer.writerows(best_rows)

        print("")
        print(f"Saved optimized configs: {OPTIMIZED_CONFIG_PATH}")
        print(
            f"OPTIMIZED PORTFOLIO: ${args.balance:.2f} -> ${combined['final_balance']:.2f} "
            f"({combined['return_pct']:.2f}%), trades={combined['trades']}, "
            f"win={combined['win_rate']:.2f}%, DD={combined['max_drawdown_pct']:.2f}%"
        )
        print(f"Report: {report_dir}")
        return 0
    finally:
        mt5.shutdown()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Optimize RSI divergence configs on MT5 history")
    parser.add_argument("--days", type=int, default=60)
    parser.add_argument("--balance", type=float, default=300.0)
    parser.add_argument("--risk", type=float, default=4.0)
    parser.add_argument("--min-trades", type=int, default=8)
    parser.add_argument("--min-return-pct", type=float, default=0.0)
    parser.add_argument(
        "--symbols",
        default="XAUUSD,XAGUSD,BTCUSD,ETHUSD,EURUSD,GBPUSD,USDJPY,AUDUSD,USDCAD,EURGBP,AUDCAD,GBPCHF,US30,US100",
    )
    return parser.parse_args()


if __name__ == "__main__":
    raise SystemExit(run_optimizer(parse_args()))
