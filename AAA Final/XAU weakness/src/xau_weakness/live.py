from __future__ import annotations

from datetime import datetime, timedelta, timezone
import json
import logging
from pathlib import Path
import time

import MetaTrader5 as mt5

from .config import LiveConfig, ROOT
from .engine import prepare, setup_at
from .mt5_data import MT5Error, account_snapshot, connected, discover_xau, fetch_m15, round_price, symbol_spec, volume_for_risk


LOGGER = logging.getLogger("xau_weakness.live")


def _logging() -> None:
    (ROOT / "logs").mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)sZ | %(levelname)-7s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=[logging.StreamHandler(), logging.FileHandler(ROOT / "logs" / "xau-weakness.log", encoding="utf-8")],
        force=True,
    )
    logging.Formatter.converter = time.gmtime


def _own_orders(symbol: str, magic: int):
    return [value for value in (mt5.orders_get(symbol=symbol) or ()) if int(value.magic) == magic]


def _own_positions(symbol: str, magic: int):
    return [value for value in (mt5.positions_get(symbol=symbol) or ()) if int(value.magic) == magic]


def _cancel(ticket: int) -> None:
    result = mt5.order_send({"action": mt5.TRADE_ACTION_REMOVE, "order": ticket})
    if result is None or result.retcode != mt5.TRADE_RETCODE_DONE:
        LOGGER.error("Could not cancel pending order %s: %s", ticket, result)


def _active_xau_risk(config: LiveConfig) -> float:
    mapping = {}
    for item in config.selected_xau_magic_risks.split(","):
        if ":" in item:
            magic, risk = item.split(":", 1)
            mapping[int(magic.strip())] = float(risk.strip())
    tickets = list(mt5.orders_get() or ()) + list(mt5.positions_get() or ())
    active = {int(item.magic) for item in tickets if int(getattr(item, "magic", 0)) in mapping}
    return sum(mapping[value] for value in active)


def _send_pending(request: dict):
    last = None
    for filling in (mt5.ORDER_FILLING_RETURN, mt5.ORDER_FILLING_IOC, mt5.ORDER_FILLING_FOK):
        candidate = {**request, "type_filling": filling}
        check = mt5.order_check(candidate)
        last = check
        if check is None or check.retcode not in (0, mt5.TRADE_RETCODE_DONE):
            continue
        result = mt5.order_send(candidate)
        last = result
        if result is not None and result.retcode in (mt5.TRADE_RETCODE_DONE, mt5.TRADE_RETCODE_PLACED):
            return result
    raise MT5Error(f"Buy-stop rejected by all filling modes: {last}")


def _state(path: Path) -> dict[str, object]:
    if not path.exists():
        return {"last_signal": "", "day": "", "day_start_balance": 0.0, "peak_equity": 0.0}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {"last_signal": "", "day": "", "day_start_balance": 0.0, "peak_equity": 0.0}


def _save(path: Path, value: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2), encoding="utf-8")


def run_live(config: LiveConfig, *, once: bool = False) -> None:
    _logging()
    state_path = ROOT / "runtime" / "state.json"
    LOGGER.info("XAU WEAKNESS | M15 bearish impulse -> two high tests -> BUY STOP | %.2f%% risk", config.strategy.risk_pct)
    with connected():
        symbol = discover_xau(config.canonical_symbol)
        spec = symbol_spec(symbol)
        snapshot = account_snapshot()
        LOGGER.info(
            "Account %s | %s | balance %.2f %s | equity %.2f | leverage 1:%s | XAU alias %s | trading %s",
            snapshot["login"], snapshot["server"], snapshot["balance"], snapshot["currency"],
            snapshot["equity"], snapshot["leverage"], symbol, "LIVE" if config.unlocked else "MONITOR ONLY",
        )
        state = _state(state_path)
        while True:
            try:
                now = datetime.now(timezone.utc)
                snapshot = account_snapshot()
                day = now.date().isoformat()
                if state.get("day") != day:
                    state.update(day=day, day_start_balance=snapshot["balance"], peak_equity=snapshot["equity"])
                state["peak_equity"] = max(float(state.get("peak_equity", snapshot["equity"])), float(snapshot["equity"]))
                daily_loss = max(0.0, (float(state["day_start_balance"]) - float(snapshot["equity"])) / max(float(state["day_start_balance"]), 1) * 100)
                equity_dd = max(0.0, (float(state["peak_equity"]) - float(snapshot["equity"])) / max(float(state["peak_equity"]), 1) * 100)
                frame = prepare(fetch_m15(symbol, now - timedelta(days=12), now))
                closed = frame.iloc[:-1]
                latest_time = closed.index[-1]
                setup = setup_at(closed, len(closed) - 1, config.strategy)
                for order in _own_orders(symbol, config.magic):
                    age = now - datetime.fromtimestamp(order.time_setup, tz=timezone.utc)
                    tick = mt5.symbol_info_tick(symbol)
                    if age >= timedelta(minutes=15 * config.strategy.pending_expiry_bars) or (tick and tick.bid <= order.sl):
                        LOGGER.info("Canceling expired/invalidated order %s", order.ticket)
                        _cancel(order.ticket)
                if setup and str(latest_time) != state.get("last_signal") and not _own_orders(symbol, config.magic) and not _own_positions(symbol, config.magic):
                    state["last_signal"] = str(latest_time)
                    shared = _active_xau_risk(config)
                    safe = (
                        daily_loss < config.strategy.max_daily_loss_pct
                        and equity_dd < config.max_equity_dd_pct
                        and (float(snapshot["margin_level"]) == 0 or float(snapshot["margin_level"]) >= config.min_margin_level_pct)
                        and shared + config.strategy.risk_pct <= config.shared_xau_risk_cap_pct + 1e-9
                    )
                    entry, stop, target = (round_price(value, spec) for value in (setup.entry, setup.stop, setup.target))
                    risk_cash = float(snapshot["equity"]) * config.strategy.risk_pct / 100
                    volume, actual_risk = volume_for_risk(symbol, entry, stop, risk_cash, spec)
                    LOGGER.info(
                        "A setup | tests %s and %s | BUY STOP %.2f | SL %.2f | TP %.2f | %.2fR | %.2f lots | risk $%.2f | %s",
                        setup.first_test_time, setup.signal_time, entry, stop, target, config.strategy.target_rr,
                        volume, actual_risk, "READY" if safe else "BLOCKED",
                    )
                    if safe and config.unlocked:
                        receipt = _send_pending({
                            "action": mt5.TRADE_ACTION_PENDING, "symbol": symbol, "volume": volume,
                            "type": mt5.ORDER_TYPE_BUY_STOP, "price": entry, "sl": stop, "tp": target,
                            "deviation": 30, "magic": config.magic, "type_time": mt5.ORDER_TIME_GTC,
                            "comment": "XAUWeak A dbl high",
                        })
                        LOGGER.info("Placed order %s", receipt.order)
                LOGGER.info(
                    "Heartbeat | M15 %s | equity %.2f | daily loss %.2f%% | equity DD %.2f%% | orders %s | positions %s",
                    latest_time, snapshot["equity"], daily_loss, equity_dd,
                    len(_own_orders(symbol, config.magic)), len(_own_positions(symbol, config.magic)),
                )
                _save(state_path, state)
            except Exception:
                LOGGER.exception("Live cycle failed")
            if once:
                return
            time.sleep(config.poll_seconds)
