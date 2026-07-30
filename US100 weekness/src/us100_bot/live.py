from __future__ import annotations

from datetime import datetime, timedelta, timezone
import json
import logging
from pathlib import Path
import time as sleep_time
from typing import Any

import MetaTrader5 as mt5
import pandas as pd

from .config import Config
from .mt5_data import fetch_m1
from .normalization import PriceNormalizer
from .risk import position_volume
from .sessions import NY, is_trading_day

LOG = logging.getLogger("us100.live")


def _state_path(cfg: Config) -> Path:
    cfg.state_dir.mkdir(parents=True, exist_ok=True)
    return cfg.state_dir / "daily_state.json"


def load_state(cfg: Config) -> dict[str, Any]:
    path = _state_path(cfg)
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


def save_state(cfg: Config, state: dict[str, Any]) -> None:
    path = _state_path(cfg)
    temp = path.with_suffix(".tmp")
    temp.write_text(json.dumps(state, indent=2), encoding="utf-8")
    temp.replace(path)


def _filling_modes(spec_mode: int) -> tuple[int, ...]:
    modes = []
    if spec_mode & 1:
        modes.append(mt5.ORDER_FILLING_FOK)
    if spec_mode & 2:
        modes.append(mt5.ORDER_FILLING_IOC)
    modes.append(mt5.ORDER_FILLING_RETURN)
    return tuple(dict.fromkeys(modes))


def _send(cfg: Config, request: dict[str, Any], filling_mode: int) -> Any:
    if not cfg.enable_trading or cfg.dry_run:
        LOG.warning("DRY RUN signal: %s", request)
        return {"dry_run": True, "request": request}
    last = None
    for mode in _filling_modes(filling_mode):
        candidate = {**request, "type_filling": mode}
        check = mt5.order_check(candidate)
        if check is None:
            last = f"order_check None: {mt5.last_error()}"
            continue
        if int(check.retcode) not in {0, int(mt5.TRADE_RETCODE_DONE)}:
            last = check
            continue
        result = mt5.order_send(candidate)
        if result is not None and int(result.retcode) in {
            int(mt5.TRADE_RETCODE_DONE),
            int(mt5.TRADE_RETCODE_PLACED),
        }:
            return result
        last = result or mt5.last_error()
    raise RuntimeError(f"All broker filling modes failed: {last}")


def _base_request(
    cfg: Config,
    symbol: str,
    volume: float,
    order_type: int,
    price: float,
    sl: float,
    tp: float,
    comment: str,
) -> dict[str, Any]:
    return {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": symbol,
        "volume": volume,
        "type": order_type,
        "price": price,
        "sl": sl,
        "tp": tp,
        "deviation": 20,
        "magic": cfg.magic,
        "comment": comment[:31],
        "type_time": mt5.ORDER_TIME_GTC,
    }


def _today_history(symbol: str, now_utc: datetime) -> pd.DataFrame:
    ny_now = now_utc.astimezone(NY)
    ny_start = ny_now.replace(hour=0, minute=0, second=0, microsecond=0)
    return fetch_m1(symbol, ny_start.astimezone(timezone.utc), now_utc)


def _daily_realized_loss(cfg: Config, now: datetime) -> float:
    ny_now = now.astimezone(NY)
    start = ny_now.replace(hour=0, minute=0, second=0, microsecond=0).astimezone(timezone.utc)
    deals = mt5.history_deals_get(start, now) or ()
    return abs(
        sum(
            min(0.0, float(d.profit) + float(d.commission) + float(d.swap))
            for d in deals
            if int(d.magic) == cfg.magic
        )
    )


def _risk_gate(
    cfg: Config, equity: float, now: datetime, norm: PriceNormalizer
) -> None:
    if _daily_realized_loss(cfg, now) >= equity * cfg.max_daily_loss_pct / 100:
        raise RuntimeError("Maximum daily loss reached")
    positions = mt5.positions_get() or ()
    own = [p for p in positions if int(p.magic) == cfg.magic]
    open_risk = 0.0
    for position in own:
        if float(position.sl) <= 0:
            open_risk = float("inf")
            break
        distance = abs(float(position.price_open) - float(position.sl))
        open_risk += norm.money_for_move(float(position.volume), distance)
    if open_risk >= equity * cfg.max_combined_risk_pct / 100:
        raise RuntimeError(
            f"Maximum combined open risk reached ({open_risk:.2f})"
        )


def _modify_stop(cfg: Config, position: Any, new_stop: float) -> None:
    if not cfg.enable_trading or cfg.dry_run:
        LOG.warning(
            "DRY RUN stop update: ticket=%s old=%.2f new=%.2f",
            position.ticket, position.sl, new_stop,
        )
        return
    result = mt5.order_send(
        {
            "action": mt5.TRADE_ACTION_SLTP,
            "position": int(position.ticket),
            "symbol": position.symbol,
            "sl": new_stop,
            "tp": float(position.tp),
            "magic": int(position.magic),
        }
    )
    if result is None or int(result.retcode) != int(mt5.TRADE_RETCODE_DONE):
        raise RuntimeError(f"Stop modification failed for {position.ticket}: {result}")


def _close_position(cfg: Config, position: Any, spec: Any) -> None:
    tick = mt5.symbol_info_tick(position.symbol)
    if tick is None:
        raise RuntimeError(f"No tick to close {position.ticket}")
    order_type = mt5.ORDER_TYPE_BUY if int(position.type) == int(mt5.POSITION_TYPE_SELL) else mt5.ORDER_TYPE_SELL
    price = tick.ask if order_type == mt5.ORDER_TYPE_BUY else tick.bid
    request = {
        "action": mt5.TRADE_ACTION_DEAL,
        "position": int(position.ticket),
        "symbol": position.symbol,
        "volume": float(position.volume),
        "type": order_type,
        "price": price,
        "deviation": 20,
        "magic": cfg.magic,
        "comment": f"{cfg.order_comment}_EXIT"[:31],
        "type_time": mt5.ORDER_TIME_GTC,
    }
    _send(cfg, request, spec.filling_mode)


def manage_open_positions(cfg: Config, spec: Any, norm: PriceNormalizer, now: datetime) -> None:
    positions = [
        p for p in (mt5.positions_get(symbol=spec.name) or ())
        if int(p.magic) == cfg.magic
    ]
    if not positions:
        return
    ny_now = now.astimezone(NY)
    force_clock = cfg.a_force_exit.strftime("%H:%M")
    for position in positions:
        if ny_now.strftime("%H:%M") >= force_clock:
            _close_position(cfg, position, spec)
            continue
        if "A_RUNNER" not in str(position.comment):
            continue
        rates = mt5.copy_rates_from_pos(spec.name, mt5.TIMEFRAME_M15, 0, 4)
        tick = mt5.symbol_info_tick(spec.name)
        if rates is None or len(rates) < 3 or tick is None:
            continue
        # Last element is the current unfinished bar; previous elements are closed.
        closed = rates[:-1]
        if cfg.a_runner_method == "previous_two_m15":
            high = max(float(closed[-1]["high"]), float(closed[-2]["high"]))
        elif cfg.a_runner_method == "atr":
            ranges = [float(x["high"] - x["low"]) for x in closed[-2:]]
            high = float(tick.ask) + 1.5 * sum(ranges) / len(ranges)
        else:
            high = float(closed[-1]["high"])
        candidate = norm.round_price(
            high + norm.pips_to_price(cfg.a_trail_buffer_pips)
        )
        minimum = float(tick.ask) + max(
            norm.minimum_stop_price,
            norm.spec.freeze_level_points * norm.spec.point,
        )
        old = float(position.sl)
        if candidate > minimum and (old <= 0 or candidate < old):
            _modify_stop(cfg, position, candidate)
            LOG.info(
                "Runner %s stop tightened from %.2f to %.2f using closed M15",
                position.ticket, old, candidate,
            )


def run_once(cfg: Config, spec: Any, norm: PriceNormalizer) -> list[dict[str, Any]]:
    now = datetime.now(timezone.utc)
    ny_now = now.astimezone(NY)
    valid, reason = is_trading_day(ny_now.date())
    if not valid:
        LOG.info("No trading: %s", reason)
        return []
    account = mt5.account_info()
    tick = mt5.symbol_info_tick(spec.name)
    if account is None or tick is None or tick.bid <= 0 or tick.ask <= 0:
        raise RuntimeError("No valid account/tick")
    manage_open_positions(cfg, spec, norm, now)
    spread_pips = (tick.ask - tick.bid) / cfg.pip_size
    if spread_pips > cfg.max_spread_pips:
        LOG.warning("Spread filter: %.2f pips", spread_pips)
        return []
    _risk_gate(cfg, float(account.equity), now, norm)
    if cfg.news_filter_enabled:
        raise RuntimeError(
            "NEWS_FILTER_ENABLED=true but no trusted MT5 calendar adapter is "
            "configured; refusing new entries safely"
        )
    state = load_state(cfg)
    day_key = str(ny_now.date())
    daily = state.setdefault(day_key, {})
    receipts: list[dict[str, Any]] = []
    clock = ny_now.strftime("%H:%M:%S")

    # Strategy A: only the first 60 seconds after 09:30. Restart-safe via state.
    if cfg.strategy_a_enabled and "09:30:00" <= clock < "09:31:00" and not daily.get("A"):
        volume, _ = position_volume(cfg, norm, float(account.equity), cfg.a_stop_pips, 0.5)
        entry = float(tick.bid)
        stop = norm.round_price(entry + norm.pips_to_price(cfg.a_stop_pips))
        fixed_tp = norm.round_price(entry - norm.pips_to_price(cfg.a_target_pips))
        for label, tp in (("A_FIXED", fixed_tp), ("A_RUNNER", 0.0)):
            request = _base_request(
                cfg, spec.name, volume, mt5.ORDER_TYPE_SELL, entry, stop, tp,
                f"{cfg.order_comment}_{label}",
            )
            receipts.append({"strategy": label, "receipt": str(_send(cfg, request, spec.filling_mode))})
        daily["A"] = {"time": now.isoformat(), "dry_run": cfg.dry_run}

    # Strategy B uses only fully closed M1 data to build 09:45-10:00.
    if cfg.strategy_b_enabled and "10:00:00" <= clock < "10:01:00" and not daily.get("B"):
        bars = _today_history(spec.name, now)
        bars["ny"] = bars["time"].dt.tz_convert(NY)
        bars["clock"] = bars["ny"].dt.strftime("%H:%M")
        second = bars[(bars["clock"] >= "09:45") & (bars["clock"] < "10:00")]
        if len(second) >= 10:
            o, c = float(second.iloc[0].open), float(second.iloc[-1].close)
            body = abs(c - o) / cfg.pip_size
            if body >= cfg.doji_body_pips and c > o and cfg.b1_enabled:
                london = bars[(bars["clock"] >= cfg.london_start.strftime("%H:%M")) & (bars["clock"] < "10:00")]
                stop = float(london.high.max()) + norm.pips_to_price(cfg.b1_stop_buffer_pips)
                stop_pips = (stop - tick.bid) / cfg.pip_size
                if cfg.min_stop_pips <= stop_pips <= cfg.max_stop_pips:
                    volume, _ = position_volume(cfg, norm, float(account.equity), stop_pips)
                    tp = tick.bid - (stop - tick.bid) * cfg.b1_rr
                    req = _base_request(
                        cfg, spec.name, volume, mt5.ORDER_TYPE_SELL, tick.bid,
                        norm.round_price(stop), norm.round_price(tp),
                        f"{cfg.order_comment}_B1",
                    )
                    receipts.append({"strategy": "B1", "receipt": str(_send(cfg, req, spec.filling_mode))})
            elif body >= cfg.doji_body_pips and c < o and cfg.b2_enabled:
                entry = norm.round_price(c + norm.pips_to_price(cfg.b2_entry_pips))
                stop = norm.round_price(entry + norm.pips_to_price(cfg.b2_stop_pips))
                tp = norm.round_price(entry - norm.pips_to_price(cfg.b2_stop_pips * cfg.b2_rr))
                volume, _ = position_volume(cfg, norm, float(account.equity), cfg.b2_stop_pips)
                expiration = ny_now.replace(
                    hour=cfg.b2_expiry.hour, minute=cfg.b2_expiry.minute, second=0, microsecond=0
                ).astimezone(timezone.utc)
                req = {
                    **_base_request(
                        cfg, spec.name, volume, mt5.ORDER_TYPE_SELL_LIMIT, entry, stop, tp,
                        f"{cfg.order_comment}_B2",
                    ),
                    "action": mt5.TRADE_ACTION_PENDING,
                    "type_time": mt5.ORDER_TIME_SPECIFIED,
                    "expiration": int(expiration.timestamp()),
                }
                receipts.append({"strategy": "B2", "receipt": str(_send(cfg, req, spec.filling_mode))})
            daily["B"] = {"time": now.isoformat(), "dry_run": cfg.dry_run}
    save_state(cfg, state)
    return receipts


def run_loop(cfg: Config, spec: Any, norm: PriceNormalizer, once: bool = False) -> None:
    if cfg.enable_trading and cfg.dry_run:
        LOG.warning("ENABLE_TRADING=true but DRY_RUN=true: no orders will be sent")
    while True:
        try:
            receipts = run_once(cfg, spec, norm)
            for receipt in receipts:
                LOG.info("Execution receipt: %s", receipt)
        except Exception:
            LOG.exception("Live scan failed")
        if once:
            return
        sleep_time.sleep(1)
