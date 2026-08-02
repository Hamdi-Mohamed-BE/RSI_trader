from __future__ import annotations

from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import time

import MetaTrader5 as mt5
import pandas as pd

from .config import Config
from .mt5_adapter import (
    MT5Error,
    account_summary,
    cancel_order,
    close_position,
    connection,
    discover_symbol,
    fetch_m1,
    modify_position_stop,
    send_sell_order,
    strategy_orders,
    strategy_positions,
    symbol_metadata,
    volume_for_cash_risk,
)
from .strategy import NY, build_day_plan, resample_bars


def _state(path: Path) -> dict[str, object]:
    if not path.exists():
        return {"submitted": []}
    return json.loads(path.read_text(encoding="utf-8"))


def _save_state(path: Path, state: dict[str, object]) -> None:
    path.write_text(json.dumps(state, indent=2), encoding="utf-8")


def _current_plan(frame, symbol: str, config: Config, now: datetime):
    local_date = now.astimezone(NY).date()
    return build_day_plan(
        frame, symbol, local_date, config, as_of=now
    )


def _manage(
    frame: pd.DataFrame,
    symbol: str,
    config: Config,
    plan,
    now: datetime,
) -> None:
    orders = strategy_orders(symbol, config.magic)
    positions = strategy_positions(symbol, config.magic)
    expiry = (
        pd.Timestamp(plan.orders[0].expiry_time)
        if plan.orders
        else pd.Timestamp(
            datetime.combine(
                now.astimezone(NY).date(),
                datetime.min.time(),
                tzinfo=NY,
            )
        )
    )
    local_now = now.astimezone(NY)
    exit_clock = config.session_exit_ny
    past_exit = (local_now.hour, local_now.minute) >= exit_clock
    if past_exit:
        for item in orders:
            cancel_order(int(item.ticket))
        for item in positions:
            close_position(symbol, item, "NW session exit")
        return
    if now >= expiry.to_pydatetime():
        for item in orders:
            cancel_order(int(item.ticket))
    if positions and config.pending_mode == "OCO":
        for item in strategy_orders(symbol, config.magic):
            cancel_order(int(item.ticket))
    if not positions or not plan.orders:
        return
    completed = resample_bars(frame, "15min")
    completed = completed.loc[
        completed["time"] + pd.Timedelta(minutes=15)
        <= pd.Timestamp(now)
    ]
    if completed.empty:
        return
    invalidation = max(item.invalidation_high for item in plan.orders)
    latest = completed.iloc[-1]
    if float(latest["close"]) > invalidation:
        for item in positions:
            close_position(symbol, item, "NW body invalidation")
        for item in strategy_orders(symbol, config.magic):
            cancel_order(int(item.ticket))
        return
    tick = mt5.symbol_info_tick(symbol)
    if tick is None:
        return
    metadata = symbol_metadata(symbol)
    spread = float(tick.ask - tick.bid)
    lookback = config.runner_trail_bars
    if len(completed) < lookback:
        return
    candidate = (
        float(completed.iloc[-lookback]["high"])
        + config.runner_buffer_points * config.note_point_to_price
        + spread
    )
    for item in positions:
        if "RUN" not in str(item.comment).upper():
            continue
        current_stop = float(item.sl)
        if candidate <= float(tick.ask):
            close_position(symbol, item, "NW trail crossed")
        elif current_stop == 0 or candidate < current_stop:
            modify_position_stop(
                symbol,
                int(item.ticket),
                candidate,
                float(item.tp),
            )


def run_live(config: Config, cycles: int = 0) -> None:
    if not config.live_allowed:
        raise RuntimeError(
            "Live execution is locked. Run optimization and forward testing "
            "first. Unlocking requires ENABLE_TRADING=true, DRY_RUN=false, "
            "and the explicit LIVE_UNLOCK acknowledgement."
        )
    # The CLI account/backtest commands already open an MT5 connection, but
    # the live worker is invoked directly by run_live.bat.  It must own the
    # MT5 lifecycle as well; otherwise symbols_get() is empty and automatic
    # broker-symbol discovery cannot work.
    with connection():
        _run_live_connected(config, cycles)


def _run_live_connected(config: Config, cycles: int = 0) -> None:
    account = account_summary()
    symbol = discover_symbol(config.canonical_symbol)
    print(
        "CONNECTED MT5 | "
        f"server={account['server']} | login={account['login']} | "
        f"balance={account['balance']:.2f} {account['currency']} | "
        f"Nasdaq-100={symbol}"
    )
    state_path = config.logs_dir / "live_state.json"
    completed_cycles = 0
    while cycles <= 0 or completed_cycles < cycles:
        now = datetime.now(timezone.utc)
        frame = fetch_m1(symbol, now - timedelta(days=14), now)
        plan = _current_plan(frame, symbol, config, now)
        _manage(frame, symbol, config, plan, now)
        if plan.orders:
            account = account_summary()
            state = _state(state_path)
            submitted = set(state.get("submitted", []))
            key = f"{plan.ny_date}:{plan.setup}"
            signal_time = min(item.signal_time for item in plan.orders)
            lateness = (now - signal_time).total_seconds()
            if 0 <= lateness <= 90 and key not in submitted:
                receipts = []
                for index, order in enumerate(plan.orders, start=1):
                    cash = (
                        float(account["balance"])
                        * config.risk_pct
                        / 100
                        * order.risk_share
                    )
                    volume = volume_for_cash_risk(
                        symbol, order.entry, order.stop, cash
                    )
                    label = (
                        f"US100Weak A+ {plan.setup} "
                        f"{'RUN' if order.runner else f'leg{index}'}"
                    )[:31]
                    receipt = send_sell_order(
                        symbol=symbol,
                        kind=order.kind,
                        volume=volume,
                        entry=order.entry,
                        stop=order.stop,
                        target=order.target,
                        magic=config.magic,
                        comment=label,
                    )
                    receipts.append(int(receipt.order or receipt.deal))
                submitted.add(key)
                state["submitted"] = sorted(submitted)
                _save_state(state_path, state)
                print(f"SUBMITTED {key}: {receipts}")
        completed_cycles += 1
        if cycles <= 0 or completed_cycles < cycles:
            time.sleep(config.poll_seconds)
