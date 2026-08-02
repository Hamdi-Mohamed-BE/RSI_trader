from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
import itertools
import json
import math
import os
from pathlib import Path
from typing import Iterable

import MetaTrader5 as mt5
import pandas as pd
from dotenv import load_dotenv

from .backtest import canonical, completed_h4_rates, discover_symbol, pivot_signals


UTC = timezone.utc


@dataclass(frozen=True, slots=True)
class ExitConfig:
    mode: str
    target_r: float | None = None
    trail_start_r: float | None = None
    trail_distance_r: float | None = None
    target_cap_r: float | None = None

    @property
    def name(self) -> str:
        if self.mode == "fixed":
            return f"fixed_{self.target_r:g}R"
        cap = (
            f"_cap_{self.target_cap_r:g}R"
            if self.target_cap_r is not None
            else ""
        )
        return (
            f"trail_start_{self.trail_start_r:g}R_"
            f"distance_{self.trail_distance_r:g}R{cap}"
        )


@dataclass(slots=True)
class RTrade:
    symbol: str
    config: str
    side: str
    pivot_time: str
    entry_time: str
    exit_time: str
    entry: float
    initial_stop: float
    exit: float
    exit_reason: str
    bars_held: int
    result_r: float


def env_list(name: str, default: str) -> list[str]:
    return [part.strip() for part in os.getenv(name, default).split(",") if part.strip()]


def env_floats(name: str, default: str) -> list[float]:
    return [float(value) for value in env_list(name, default)]


def spread(frame: pd.DataFrame, idx: int, point: float) -> float:
    return max(float(frame.at[idx, "spread"]) * point, 0.0)


def bid_ohlc(frame: pd.DataFrame, idx: int) -> tuple[float, float, float, float]:
    return tuple(float(frame.at[idx, field]) for field in ("open", "high", "low", "close"))


def side_ohlc(
    frame: pd.DataFrame, idx: int, side: str, point: float
) -> tuple[float, float, float, float]:
    values = bid_ohlc(frame, idx)
    if side == "buy":
        return values
    spr = spread(frame, idx, point)
    return tuple(value + spr for value in values)


def entry_price(frame: pd.DataFrame, idx: int, side: str, point: float) -> float:
    open_price = float(frame.at[idx, "open"])
    return open_price + spread(frame, idx, point) if side == "buy" else open_price


def exit_open(frame: pd.DataFrame, idx: int, side: str, point: float) -> float:
    open_price = float(frame.at[idx, "open"])
    return open_price if side == "buy" else open_price + spread(frame, idx, point)


def exit_close(frame: pd.DataFrame, idx: int, side: str, point: float) -> float:
    close_price = float(frame.at[idx, "close"])
    return close_price if side == "buy" else close_price + spread(frame, idx, point)


def result_r(side: str, entry: float, exit_price: float, risk_distance: float) -> float:
    movement = exit_price - entry if side == "buy" else entry - exit_price
    return movement / risk_distance


def filtered_pivot_signals(
    frame: pd.DataFrame,
    distance: int,
    signal_filter: str = "none",
    ema_slope_bars: int = 6,
) -> list[dict[str, object]]:
    signals = pivot_signals(frame, distance)
    if signal_filter == "none":
        return signals
    if signal_filter != "ema200_slope":
        raise ValueError(f"Unsupported signal filter: {signal_filter}")
    if ema_slope_bars < 1:
        raise ValueError("ema_slope_bars must be positive")
    ema200 = frame["close"].ewm(span=200, adjust=False, min_periods=200).mean()
    accepted: list[dict[str, object]] = []
    for signal in signals:
        confirmed_idx = int(signal["confirmed_idx"])
        earlier_idx = confirmed_idx - ema_slope_bars
        if earlier_idx < 0 or pd.isna(ema200.iat[confirmed_idx]) or pd.isna(
            ema200.iat[earlier_idx]
        ):
            continue
        rising = float(ema200.iat[confirmed_idx]) > float(ema200.iat[earlier_idx])
        falling = float(ema200.iat[confirmed_idx]) < float(ema200.iat[earlier_idx])
        if (signal["side"] == "buy" and rising) or (
            signal["side"] == "sell" and falling
        ):
            accepted.append(signal)
    return accepted


def simulate(
    frame: pd.DataFrame,
    symbol: str,
    point: float,
    distance: int,
    start: datetime,
    end: datetime,
    config: ExitConfig,
    max_same_direction_legs: int = 2,
    signal_filter: str = "none",
    ema_slope_bars: int = 6,
    prepared_signals: list[dict[str, object]] | None = None,
) -> list[RTrade]:
    by_index: dict[int, list[dict[str, object]]] = {}
    signals = prepared_signals
    if signals is None:
        signals = filtered_pivot_signals(
            frame, distance, signal_filter, ema_slope_bars
        )
    for signal in signals:
        idx = int(signal["execute_idx"])
        timestamp = frame.at[idx, "time"].to_pydatetime()
        if start <= timestamp < end:
            by_index.setdefault(idx, []).append(signal)

    active: list[dict[str, object]] = []
    trades: list[RTrade] = []
    period_indexes = frame.index[(frame["time"] >= start) & (frame["time"] < end)]
    if len(period_indexes) == 0:
        return trades

    def close_trade(
        leg: dict[str, object], idx: int, price: float, reason: str
    ) -> None:
        side = str(leg["side"])
        risk_distance = float(leg["risk_distance"])
        trades.append(
            RTrade(
                symbol=symbol,
                config=config.name,
                side=side,
                pivot_time=frame.at[int(leg["pivot_idx"]), "time"].isoformat(),
                entry_time=frame.at[int(leg["entry_idx"]), "time"].isoformat(),
                exit_time=frame.at[idx, "time"].isoformat(),
                entry=float(leg["entry"]),
                initial_stop=float(leg["initial_stop"]),
                exit=price,
                exit_reason=reason,
                bars_held=idx - int(leg["entry_idx"]),
                result_r=result_r(side, float(leg["entry"]), price, risk_distance),
            )
        )
        active.remove(leg)

    for idx in period_indexes:
        signals = by_index.get(int(idx), [])
        signal_sides = {str(signal["side"]) for signal in signals}
        signal = signals[0] if len(signal_sides) == 1 and signals else None

        if signal is not None:
            new_side = str(signal["side"])
            if active and str(active[0]["side"]) != new_side:
                old_side = str(active[0]["side"])
                price = exit_open(frame, int(idx), old_side, point)
                for leg in list(active):
                    close_trade(leg, int(idx), price, "opposite_signal")
            if len(active) < max_same_direction_legs:
                entry = entry_price(frame, int(idx), new_side, point)
                pivot_idx = int(signal["pivot_idx"])
                initial_stop = (
                    float(frame.at[pivot_idx, "low"])
                    if new_side == "buy"
                    else float(frame.at[pivot_idx, "high"]) + spread(frame, int(idx), point)
                )
                risk_distance = (
                    entry - initial_stop
                    if new_side == "buy"
                    else initial_stop - entry
                )
                if risk_distance > point:
                    active.append(
                        {
                            "side": new_side,
                            "pivot_idx": pivot_idx,
                            "entry_idx": int(idx),
                            "entry": entry,
                            "initial_stop": initial_stop,
                            "stop": initial_stop,
                            "risk_distance": risk_distance,
                        }
                    )

        if not active:
            continue

        for leg in list(active):
            side = str(leg["side"])
            entry = float(leg["entry"])
            stop = float(leg["stop"])
            risk_distance = float(leg["risk_distance"])
            open_price, high, low, close = side_ohlc(frame, int(idx), side, point)
            target = (
                entry + float(config.target_r) * risk_distance
                if side == "buy" and config.mode == "fixed"
                else entry - float(config.target_r) * risk_distance
                if side == "sell" and config.mode == "fixed"
                else entry + float(config.target_cap_r) * risk_distance
                if side == "buy" and config.mode == "trail" and config.target_cap_r is not None
                else entry - float(config.target_cap_r) * risk_distance
                if side == "sell" and config.mode == "trail" and config.target_cap_r is not None
                else None
            )

            stop_gap = (side == "buy" and open_price <= stop) or (
                side == "sell" and open_price >= stop
            )
            stop_hit = (side == "buy" and low <= stop) or (
                side == "sell" and high >= stop
            )
            target_hit = target is not None and (
                (side == "buy" and high >= target)
                or (side == "sell" and low <= target)
            )
            if stop_gap:
                close_trade(leg, int(idx), open_price, "stop_gap")
                continue
            if stop_hit:
                close_trade(leg, int(idx), stop, "stop")
                continue
            if target_hit and target is not None:
                close_trade(leg, int(idx), target, "target")
                continue

            if config.mode == "trail":
                activation = (
                    entry + float(config.trail_start_r) * risk_distance
                    if side == "buy"
                    else entry - float(config.trail_start_r) * risk_distance
                )
                confirmed = (side == "buy" and close >= activation) or (
                    side == "sell" and close <= activation
                )
                if confirmed:
                    candidate = (
                        close - float(config.trail_distance_r) * risk_distance
                        if side == "buy"
                        else close + float(config.trail_distance_r) * risk_distance
                    )
                    leg["stop"] = (
                        max(stop, candidate) if side == "buy" else min(stop, candidate)
                    )

    if active:
        idx = int(period_indexes[-1])
        side = str(active[0]["side"])
        price = exit_close(frame, idx, side, point)
        for leg in list(active):
            close_trade(leg, idx, price, "end_of_period")
    return trades


def metrics(
    trades: Iterable[RTrade],
    risk_pct: float = 1.0,
    starting_balance: float = 1_000.0,
    progression_enabled: bool = False,
    progression_multiplier: float = 1.6,
    max_risk_pct: float | None = None,
) -> dict[str, float | int | bool]:
    records = list(trades)
    balance = starting_balance
    peak = balance
    max_dd = 0.0
    results: list[float] = []
    cash_results: list[float] = []
    ruined = False
    loss_streak = 0
    maximum_applied_risk_pct = 0.0
    for trade in records:
        value = trade.result_r
        results.append(value)
        applied_risk_pct = (
            risk_pct * progression_multiplier**loss_streak
            if progression_enabled
            else risk_pct
        )
        if max_risk_pct is not None:
            applied_risk_pct = min(applied_risk_pct, max_risk_pct)
        maximum_applied_risk_pct = max(maximum_applied_risk_pct, applied_risk_pct)
        risk_cash = balance * applied_risk_pct / 100.0
        # A historical gap can lose more than the intended 1R. Once equity is
        # exhausted, the account cannot keep trading or recover from a negative
        # balance. The legacy fixed-lot report allowed exactly that and produced
        # the misleading 400% drawdown result.
        previous_balance = balance
        balance = max(0.0, balance + risk_cash * value)
        cash_results.append(balance - previous_balance)
        peak = max(peak, balance)
        if peak > 0:
            max_dd = max(max_dd, (peak - balance) / peak * 100.0)
        if balance <= 0:
            ruined = True
            break
        if value < 0:
            loss_streak += 1
        elif value > 0:
            loss_streak = 0
    wins = [value for value in results if value > 0]
    losses = [value for value in results if value < 0]
    gross_profit = sum(wins)
    gross_loss = abs(sum(losses))
    cash_wins = [value for value in cash_results if value > 0]
    cash_losses = [value for value in cash_results if value < 0]
    cash_gross_profit = sum(cash_wins)
    cash_gross_loss = abs(sum(cash_losses))
    return {
        "trades": len(results),
        "wins": len(wins),
        "losses": len(losses),
        "win_rate_pct": len(wins) / len(results) * 100.0 if results else 0.0,
        "net_r": sum(results),
        "profit_factor": gross_profit / gross_loss if gross_loss else math.inf,
        "cash_profit_factor": (
            cash_gross_profit / cash_gross_loss if cash_gross_loss else math.inf
        ),
        "cash_gross_profit": cash_gross_profit,
        "cash_gross_loss": cash_gross_loss,
        "expectancy_r": sum(results) / len(results) if results else 0.0,
        "risk_pct": risk_pct,
        "progression_enabled": progression_enabled,
        "progression_multiplier": progression_multiplier,
        "max_risk_pct": max_risk_pct,
        "maximum_applied_risk_pct": maximum_applied_risk_pct,
        "final_loss_streak": loss_streak,
        "processed_trades": len(results),
        "ruined": ruined,
        "max_drawdown_pct": max_dd,
        "ending_balance": balance,
        # Kept for compatibility with the existing optimizer reports.
        "max_dd_pct_at_1pct": max_dd,
        "ending_balance_at_1pct": balance,
    }


def compounded_journal(
    trades: Iterable[RTrade],
    risk_pct: float = 1.0,
    starting_balance: float = 1_000.0,
    progression_enabled: bool = False,
    progression_multiplier: float = 1.6,
    max_risk_pct: float | None = None,
) -> pd.DataFrame:
    """Create a realizable risk-sized cash journal without negative-equity recovery."""
    balance = starting_balance
    peak = starting_balance
    rows: list[dict[str, object]] = []
    loss_streak = 0
    for trade in trades:
        if balance <= 0:
            break
        applied_risk_pct = (
            risk_pct * progression_multiplier**loss_streak
            if progression_enabled
            else risk_pct
        )
        if max_risk_pct is not None:
            applied_risk_pct = min(applied_risk_pct, max_risk_pct)
        risk_cash = balance * applied_risk_pct / 100.0
        pnl_cash = risk_cash * trade.result_r
        balance = max(0.0, balance + pnl_cash)
        peak = max(peak, balance)
        row = asdict(trade)
        row.update(
            {
                "risk_pct": risk_pct,
                "applied_risk_pct": applied_risk_pct,
                "loss_streak_before": loss_streak,
                "risk_cash": risk_cash,
                "pnl_cash": pnl_cash,
                "balance": balance,
                "drawdown_pct": (
                    (peak - balance) / peak * 100.0 if peak > 0 else 100.0
                ),
            }
        )
        rows.append(row)
        if trade.result_r < 0:
            loss_streak += 1
        elif trade.result_r > 0:
            loss_streak = 0
    return pd.DataFrame(rows)


def portfolio_metrics(
    trades: list[RTrade],
    starting_balance: float,
    risk_pct: float,
    cap_pct: float,
) -> tuple[dict[str, float | int], pd.DataFrame]:
    events: list[tuple[pd.Timestamp, int, str, RTrade]] = []
    for trade in trades:
        entry_time = pd.Timestamp(trade.entry_time)
        exit_time = pd.Timestamp(trade.exit_time)
        events.append((entry_time, 1, "entry", trade))
        # Existing positions close before new entries at the same timestamp.
        # A position stopped inside its entry candle must enter before its own
        # same-timestamp exit, otherwise it would remain falsely active.
        exit_priority = 2 if exit_time == entry_time else 0
        events.append((exit_time, exit_priority, "exit", trade))
    events.sort(key=lambda item: (item[0], item[1], item[3].symbol))
    active: dict[int, tuple[RTrade, float]] = {}
    accepted_ids: set[int] = set()
    skipped = 0
    balance = starting_balance
    peak = balance
    max_dd = 0.0
    journal: list[dict[str, object]] = []
    for _, _, event, trade in events:
        trade_id = id(trade)
        if event == "entry":
            if (len(active) + 1) * risk_pct > cap_pct + 1e-9:
                skipped += 1
                continue
            risk_cash = balance * risk_pct / 100.0
            active[trade_id] = (trade, risk_cash)
            accepted_ids.add(trade_id)
            continue
        if trade_id not in accepted_ids or trade_id not in active:
            continue
        _, risk_cash = active.pop(trade_id)
        pnl = risk_cash * trade.result_r
        balance += pnl
        peak = max(peak, balance)
        if peak > 0:
            max_dd = max(max_dd, (peak - balance) / peak * 100.0)
        row = asdict(trade)
        row.update({"risk_cash": risk_cash, "pnl_cash": pnl, "balance": balance})
        journal.append(row)
    accepted_trades = [
        RTrade(
            **{key: row[key] for key in RTrade.__dataclass_fields__}
        )
        for row in journal
    ]
    summary = metrics(accepted_trades, risk_pct=risk_pct, starting_balance=starting_balance)
    summary.update(
        {
            "accepted": len(journal),
            "skipped_exposure": skipped,
            "ending_balance": balance,
            "return_pct": (balance / starting_balance - 1.0) * 100.0,
            "max_realized_dd_pct": max_dd,
        }
    )
    return summary, pd.DataFrame(journal)


def config_grid() -> list[ExitConfig]:
    target_cap_r = min(float(os.getenv("MAX_TARGET_R", "1.7")), 1.7)
    fixed = [
        ExitConfig(mode="fixed", target_r=min(rr, target_cap_r))
        for rr in env_floats("FIXED_RRS", "1,1.5,2,2.5,3,4,5")
    ]
    # De-duplicate values that collapse to the target ceiling.
    fixed = list({config.name: config for config in fixed}.values())
    trailing = [
        ExitConfig(
            mode="trail",
            trail_start_r=start,
            trail_distance_r=distance,
            target_cap_r=target_cap_r,
        )
        for start, distance in itertools.product(
            env_floats("TRAIL_START_RS", "1,1.5,2,3"),
            env_floats("TRAIL_DISTANCE_RS", "0.5,1,1.5,2"),
        )
    ]
    return fixed + trailing


def selection_score(record: dict[str, object]) -> float:
    trades = int(record["trades"])
    expectancy = float(record["expectancy_r"])
    dd = float(record["max_dd_pct_at_1pct"])
    pf = float(record["profit_factor"])
    pf_component = min(pf, 6.0) if math.isfinite(pf) else 6.0
    return expectancy * math.sqrt(max(trades, 1)) + 0.15 * pf_component - 0.04 * dd


def main() -> None:
    load_dotenv()
    requested = env_list(
        "SYMBOLS",
        "XAUUSD,XAGUSD,BTCUSD,ETHUSD,EURJPY,AUDCAD,AUDCHF,GBPJPY,GBPUSD,US30",
    )
    history_days = int(os.getenv("HISTORY_DAYS", "365"))
    train_fraction = float(os.getenv("TRAIN_FRACTION", "0.75"))
    distance = int(os.getenv("PIVOT_DISTANCE", "6"))
    signal_filter = os.getenv("SIGNAL_FILTER", "none").strip().lower()
    ema_slope_bars = int(os.getenv("EMA_SLOPE_BARS", "6"))
    max_same_direction_legs = int(os.getenv("MAX_SAME_DIRECTION_LEGS", "2"))
    minimum_train = int(os.getenv("MIN_TRAIN_TRADES", "12"))
    minimum_train_pf = float(os.getenv("MIN_TRAIN_PROFIT_FACTOR", "1.05"))
    minimum_validation = int(os.getenv("MIN_VALIDATION_TRADES", "4"))
    starting_balance = float(os.getenv("STARTING_BALANCE", "1000"))
    risk_pct = float(os.getenv("RISK_PCT", "1"))
    cap_pct = float(os.getenv("MAX_PORTFOLIO_RISK_PCT", "3"))
    report_dir = Path(os.getenv("REPORT_DIR", r"reports\optimization"))
    report_dir.mkdir(parents=True, exist_ok=True)

    if not mt5.initialize():
        raise SystemExit(f"MT5 initialize failed: {mt5.last_error()}")
    try:
        end = datetime.now(UTC)
        start = end - timedelta(days=history_days)
        split = start + (end - start) * train_fraction
        all_rows: list[dict[str, object]] = []
        best_rows: list[dict[str, object]] = []
        validation_trades: list[RTrade] = []
        errors: list[dict[str, str]] = []
        for requested_symbol in requested:
            try:
                symbol = discover_symbol(requested_symbol)
                info = mt5.symbol_info(symbol)
                if info is None:
                    raise RuntimeError("symbol_info unavailable")
                warmup_bars = (
                    250 + ema_slope_bars if signal_filter != "none" else 0
                )
                frame = completed_h4_rates(
                    symbol, start, end, distance, warmup_bars=warmup_bars
                )
                candidates: list[tuple[ExitConfig, dict[str, object]]] = []
                for config in config_grid():
                    train_trades = simulate(
                        frame,
                        requested_symbol,
                        float(info.point),
                        distance,
                        start,
                        split,
                        config,
                        max_same_direction_legs,
                        signal_filter,
                        ema_slope_bars,
                    )
                    train_stats = metrics(train_trades)
                    row = {
                        "instrument": requested_symbol,
                        "broker_symbol": symbol,
                        "config": config.name,
                        "sample": "train",
                        **train_stats,
                    }
                    row["selection_score"] = selection_score(row)
                    all_rows.append(row)
                    if (
                        int(train_stats["trades"]) >= minimum_train
                        and float(train_stats["net_r"]) > 0
                        and float(train_stats["profit_factor"]) >= minimum_train_pf
                    ):
                        candidates.append((config, row))
                if not candidates:
                    raise RuntimeError(
                        f"no configuration reached {minimum_train} training trades "
                        f"with PF >= {minimum_train_pf:.2f} and positive net R"
                    )
                selected, selected_train = max(
                    candidates, key=lambda item: float(item[1]["selection_score"])
                )
                valid_trades = simulate(
                    frame,
                    requested_symbol,
                    float(info.point),
                    distance,
                    split,
                    end,
                    selected,
                    max_same_direction_legs,
                    signal_filter,
                    ema_slope_bars,
                )
                valid_stats = metrics(valid_trades)
                full_trades = simulate(
                    frame,
                    requested_symbol,
                    float(info.point),
                    distance,
                    start,
                    end,
                    selected,
                    max_same_direction_legs,
                    signal_filter,
                    ema_slope_bars,
                )
                full_stats = metrics(full_trades)
                last_month_trades = simulate(
                    frame,
                    requested_symbol,
                    float(info.point),
                    distance,
                    end - timedelta(days=30),
                    end,
                    selected,
                    max_same_direction_legs,
                    signal_filter,
                    ema_slope_bars,
                )
                month_stats = metrics(last_month_trades)
                valid_row = {
                    "instrument": requested_symbol,
                    "broker_symbol": symbol,
                    "config": selected.name,
                    "sample": "validation",
                    **valid_stats,
                    "selection_score": None,
                }
                month_row = {
                    "instrument": requested_symbol,
                    "broker_symbol": symbol,
                    "config": selected.name,
                    "sample": "last_30_days",
                    **month_stats,
                    "selection_score": None,
                }
                all_rows.extend([valid_row, month_row])
                best_rows.append(
                    {
                        "instrument": requested_symbol,
                        "broker_symbol": symbol,
                        "selected_config": selected.name,
                        **{
                            f"train_{key}": value
                            for key, value in selected_train.items()
                            if key
                            not in {
                                "instrument",
                                "broker_symbol",
                                "config",
                                "sample",
                                "selection_score",
                            }
                        },
                        **{f"validation_{key}": value for key, value in valid_stats.items()},
                        **{f"full_{key}": value for key, value in full_stats.items()},
                        **{f"month_{key}": value for key, value in month_stats.items()},
                    }
                )
                if (
                    int(valid_stats["trades"]) >= minimum_validation
                    and float(valid_stats["net_r"]) > 0
                    and float(valid_stats["profit_factor"]) >= 1.2
                ):
                    validation_trades.extend(valid_trades)
            except Exception as exc:
                errors.append({"instrument": requested_symbol, "error": str(exc)})
    finally:
        mt5.shutdown()

    all_frame = pd.DataFrame(all_rows)
    best_frame = pd.DataFrame(best_rows)
    all_frame.to_csv(report_dir / "all_config_results.csv", index=False)
    best_frame.to_csv(report_dir / "best_by_symbol.csv", index=False)
    pd.DataFrame(asdict(trade) for trade in validation_trades).to_csv(
        report_dir / "selected_validation_trades.csv", index=False
    )
    pd.DataFrame(errors).to_csv(report_dir / "errors.csv", index=False)
    portfolio, journal = portfolio_metrics(
        validation_trades, starting_balance, risk_pct, cap_pct
    )
    journal.to_csv(report_dir / "portfolio_journal.csv", index=False)
    payload = {
        "period_start_utc": start.isoformat(),
        "training_end_utc": split.isoformat(),
        "validation_end_utc": end.isoformat(),
        "history_days": history_days,
        "train_fraction": train_fraction,
        "tested_configurations": len(config_grid()),
        "max_same_direction_legs": max_same_direction_legs,
        "pivot_distance": distance,
        "signal_filter": signal_filter,
        "ema_slope_bars": ema_slope_bars,
        "risk_pct": risk_pct,
        "portfolio_cap_pct": cap_pct,
        "portfolio": portfolio,
        "errors": errors,
    }
    (report_dir / "summary.json").write_text(
        json.dumps(payload, indent=2, allow_nan=True), encoding="utf-8"
    )

    ranked = best_frame.sort_values(
        ["validation_profit_factor", "validation_net_r"],
        ascending=[False, False],
    )
    lines = [
        "# EMA3 Exit Optimization",
        "",
        f"Period: {start.isoformat()} to {end.isoformat()}",
        f"Training ends: {split.isoformat()}; everything after it is unseen validation.",
        f"Configurations tested per symbol: {len(config_grid())}",
        f"Signal definition: pivot {distance}; filter {signal_filter} "
        f"({ema_slope_bars} H4 slope bars)",
        "",
        "## Best training-selected exit per symbol",
        "",
        "| Symbol | Exit | Train trades | Train PF | Validation trades | Validation WR | Validation PF | Validation net R | Validation DD | Last-30d PF |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for _, row in ranked.iterrows():
        def fmt_pf(value: object) -> str:
            number = float(value)
            return "inf" if math.isinf(number) else f"{number:.2f}"

        lines.append(
            f"| {row['instrument']} | {row['selected_config']} | "
            f"{int(row['train_trades'])} | {fmt_pf(row['train_profit_factor'])} | "
            f"{int(row['validation_trades'])} | {row['validation_win_rate_pct']:.1f}% | "
            f"{fmt_pf(row['validation_profit_factor'])} | {row['validation_net_r']:.2f} | "
            f"{row['validation_max_dd_pct_at_1pct']:.2f}% | "
            f"{fmt_pf(row['month_profit_factor'])} |"
        )
    lines.extend(
        [
            "",
            "## Validation portfolio",
            "",
            f"- Accepted trades: **{portfolio['accepted']}**",
            f"- Exposure skips: **{portfolio['skipped_exposure']}**",
            f"- Win rate: **{portfolio['win_rate_pct']:.2f}%**",
            f"- Profit factor: **{portfolio['profit_factor']:.2f}**",
            f"- Net R: **{portfolio['net_r']:.2f}R**",
            f"- Ending balance: **${portfolio['ending_balance']:,.2f}**",
            f"- Return: **{portfolio['return_pct']:.2f}%**",
            f"- Max realized DD: **{portfolio['max_realized_dd_pct']:.2f}%**",
            "",
            "Only symbols with at least the configured validation trade count,",
            "positive validation net R, and validation PF >= 1.20 enter the mix.",
            "",
        ]
    )
    (report_dir / "REPORT.md").write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
