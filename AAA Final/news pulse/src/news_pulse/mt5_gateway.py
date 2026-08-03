from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
import logging
import math
from typing import Any

import MetaTrader5 as mt5

from .config import Config
from .core import FrozenRange, discover_gold_symbol, risk_sized_volume


LOG = logging.getLogger("news_pulse.mt5")


@dataclass(frozen=True)
class OrderReceipt:
    ticket: int
    request: dict[str, Any]
    result: dict[str, Any]


class MT5Gateway:
    def __init__(self, config: Config) -> None:
        self.config = config
        self.symbol = ""
        self.info: Any = None

    def __enter__(self) -> "MT5Gateway":
        if not mt5.initialize():
            raise RuntimeError(f"MT5 initialize failed: {mt5.last_error()}")
        self.info = discover_gold_symbol(mt5.symbols_get() or ())
        self.symbol = str(self.info.name)
        if not self.info.visible and not mt5.symbol_select(self.symbol, True):
            raise RuntimeError(f"Could not select {self.symbol}: {mt5.last_error()}")
        return self

    def __exit__(self, *_: object) -> None:
        mt5.shutdown()

    def account(self) -> Any:
        account = mt5.account_info()
        if account is None:
            raise RuntimeError(f"MT5 account unavailable: {mt5.last_error()}")
        return account

    def tick(self) -> Any:
        tick = mt5.symbol_info_tick(self.symbol)
        if tick is None:
            raise RuntimeError(f"No tick for {self.symbol}: {mt5.last_error()}")
        return tick

    def frozen_range(self, release: datetime) -> FrozenRange:
        start = release - timedelta(minutes=60)
        end = release - timedelta(minutes=30, seconds=1)
        rows = mt5.copy_rates_range(self.symbol, mt5.TIMEFRAME_M1, start, end)
        if rows is None or len(rows) != 30:
            raise RuntimeError(f"Need exactly 30 completed T-60..T-31 bars; received {0 if rows is None else len(rows)}")
        expected_last = int((release - timedelta(minutes=31)).timestamp())
        if int(rows[-1]["time"]) != expected_last:
            raise RuntimeError("Frozen range is stale or has a missing final T-31 bar")
        highs = [float(x["high"]) for x in rows]
        lows = [float(x["low"]) for x in rows]
        closes = [float(x["close"]) for x in rows]
        true_ranges = []
        for index, row in enumerate(rows):
            previous = closes[index - 1] if index else float(row["open"])
            true_ranges.append(max(float(row["high"]) - float(row["low"]), abs(float(row["high"]) - previous), abs(float(row["low"]) - previous)))
        point = float(self.info.point)
        spread = float(rows[-1]["spread"]) * point
        return FrozenRange(max(highs), min(lows), sum(true_ranges) / len(true_ranges), spread, datetime.fromtimestamp(int(rows[0]["time"]), timezone.utc).isoformat(), datetime.fromtimestamp(int(rows[-1]["time"]), timezone.utc).isoformat())

    def normalize_price(self, price: float) -> float:
        tick_size = float(getattr(self.info, "trade_tick_size", 0.0) or self.info.point)
        return round(round(price / tick_size) * tick_size, int(self.info.digits))

    def volume_for(self, side: str, entry: float, stop: float) -> float | None:
        if self.config.sizing_mode == "fixed_lot":
            raw = self.config.fixed_lot
        else:
            account = self.account()
            cash_risk = float(account.equity) * self.config.risk_pct / 100.0
            order_type = mt5.ORDER_TYPE_BUY if side == "buy" else mt5.ORDER_TYPE_SELL
            profit = mt5.order_calc_profit(order_type, self.symbol, 1.0, entry, stop)
            if profit is None:
                raise RuntimeError(f"order_calc_profit failed: {mt5.last_error()}")
            raw = risk_sized_volume(cash_risk=cash_risk, loss_per_lot=abs(float(profit)), minimum=float(self.info.volume_min), maximum=float(self.info.volume_max), step=float(self.info.volume_step))
            if raw is None:
                return None
        step = float(self.info.volume_step)
        volume = math.floor(float(raw) / step + 1e-12) * step
        return round(min(max(volume, float(self.info.volume_min)), float(self.info.volume_max)), 8)

    def _fill_modes(self) -> list[int]:
        preferred = int(getattr(self.info, "filling_mode", mt5.ORDER_FILLING_IOC))
        return list(dict.fromkeys([preferred, mt5.ORDER_FILLING_IOC, mt5.ORDER_FILLING_FOK, mt5.ORDER_FILLING_RETURN]))

    def cash_risk(self, side: str, volume: float, entry: float, stop: float) -> float:
        order_type = mt5.ORDER_TYPE_BUY if side == "buy" else mt5.ORDER_TYPE_SELL
        result = mt5.order_calc_profit(order_type, self.symbol, volume, entry, stop)
        if result is None:
            raise RuntimeError(f"order_calc_profit failed: {mt5.last_error()}")
        return abs(float(result))

    def daily_stats(self, now: datetime) -> tuple[float, int]:
        start = now.astimezone(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
        deals = mt5.history_deals_get(start, now) or ()
        owned = [deal for deal in deals if int(getattr(deal, "magic", -1)) == self.config.magic]
        realized = sum(
            float(getattr(deal, "profit", 0.0))
            + float(getattr(deal, "commission", 0.0))
            + float(getattr(deal, "swap", 0.0))
            + float(getattr(deal, "fee", 0.0))
            for deal in owned
            if int(getattr(deal, "entry", -1)) in {mt5.DEAL_ENTRY_OUT, mt5.DEAL_ENTRY_OUT_BY}
        )
        opened_orders = {
            int(getattr(deal, "order", 0))
            for deal in owned
            if int(getattr(deal, "entry", -1)) == mt5.DEAL_ENTRY_IN
        }
        return realized, len(opened_orders)

    def recent_owned_deals(self, start: datetime, end: datetime) -> list[Any]:
        return [
            deal for deal in (mt5.history_deals_get(start, end) or ())
            if int(getattr(deal, "magic", -1)) == self.config.magic
        ]

    def send_pending(self, *, side: str, entry: float, stop: float, target: float, volume: float, expiration: datetime, comment: str, order_kind: str = "stop") -> OrderReceipt | None:
        if order_kind not in {"stop", "limit"}:
            raise ValueError("order_kind must be stop or limit")
        if order_kind == "limit":
            order_type = mt5.ORDER_TYPE_BUY_LIMIT if side == "buy" else mt5.ORDER_TYPE_SELL_LIMIT
        else:
            order_type = mt5.ORDER_TYPE_BUY_STOP if side == "buy" else mt5.ORDER_TYPE_SELL_STOP
        request_base = {
            "action": mt5.TRADE_ACTION_PENDING,
            "symbol": self.symbol,
            "volume": volume,
            "type": order_type,
            "price": self.normalize_price(entry),
            "sl": self.normalize_price(stop),
            "tp": self.normalize_price(target),
            "deviation": max(1, int(round(self.config.max_slippage_usd / float(self.info.point)))),
            "magic": self.config.magic,
            "comment": comment[:31],
            "type_time": mt5.ORDER_TIME_SPECIFIED,
            "expiration": int(expiration.timestamp()),
        }
        last_check: Any = None
        for filling in self._fill_modes():
            request = {**request_base, "type_filling": filling}
            check = mt5.order_check(request)
            LOG.info("order_check request=%s response=%s", request, check)
            last_check = check
            if check is None or int(check.retcode) not in {0, mt5.TRADE_RETCODE_DONE, mt5.TRADE_RETCODE_PLACED}:
                continue
            if not self.config.execution_enabled:
                LOG.warning("PAPER order only: %s", request)
                return None
            result = mt5.order_send(request)
            LOG.info("order_send request=%s response=%s", request, result)
            if result is None or int(result.retcode) not in {mt5.TRADE_RETCODE_DONE, mt5.TRADE_RETCODE_PLACED}:
                raise RuntimeError(f"order_send failed: {result}")
            return OrderReceipt(int(result.order), request, result._asdict())
        raise RuntimeError(f"No broker-supported fill mode passed order_check: {last_check}")

    def cancel_order(self, ticket: int) -> None:
        request = {"action": mt5.TRADE_ACTION_REMOVE, "order": int(ticket), "magic": self.config.magic}
        check = mt5.order_check(request)
        LOG.info("cancel order_check request=%s response=%s", request, check)
        if not self.config.execution_enabled:
            return
        result = mt5.order_send(request)
        LOG.info("cancel order_send request=%s response=%s", request, result)

    def close_position(self, position: Any, comment: str) -> bool:
        tick = self.tick()
        is_buy = int(position.type) == mt5.POSITION_TYPE_BUY
        base = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": self.symbol,
            "position": int(position.ticket),
            "volume": float(position.volume),
            "type": mt5.ORDER_TYPE_SELL if is_buy else mt5.ORDER_TYPE_BUY,
            "price": self.normalize_price(float(tick.bid if is_buy else tick.ask)),
            "deviation": max(1, int(round(self.config.max_slippage_usd / float(self.info.point)))),
            "magic": self.config.magic,
            "comment": comment[:31],
            "type_time": mt5.ORDER_TIME_GTC,
        }
        for filling in self._fill_modes():
            request = {**base, "type_filling": filling}
            check = mt5.order_check(request)
            LOG.info("close order_check request=%s response=%s", request, check)
            if check is None or int(check.retcode) not in {0, mt5.TRADE_RETCODE_DONE}:
                continue
            if not self.config.execution_enabled:
                LOG.warning("PAPER close only: %s", request)
                return False
            result = mt5.order_send(request)
            LOG.info("close order_send request=%s response=%s", request, result)
            if result is not None and int(result.retcode) == mt5.TRADE_RETCODE_DONE:
                return True
        raise RuntimeError(f"Could not close owned position {position.ticket}")

    def owned_orders(self) -> list[Any]:
        return [x for x in (mt5.orders_get(symbol=self.symbol) or ()) if int(x.magic) == self.config.magic]

    def owned_positions(self) -> list[Any]:
        return [x for x in (mt5.positions_get(symbol=self.symbol) or ()) if int(x.magic) == self.config.magic]
