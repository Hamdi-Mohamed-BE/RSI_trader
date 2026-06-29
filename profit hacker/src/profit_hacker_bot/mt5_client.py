from __future__ import annotations

import logging
import math
from typing import Any

from .config import Settings
from .models import (
    BrokerOrderResult,
    BrokerVolume,
    Direction,
    EntryType,
    OrderPlan,
    VolumeConstraints,
)
from .symbol_discovery import choose_best_symbol

try:
    import MetaTrader5 as mt5
except ImportError:  # pragma: no cover - depends on local Windows setup
    mt5 = None  # type: ignore[assignment]

logger = logging.getLogger(__name__)

# MetaTrader5's Python package exposes ORDER_FILLING_* but not the
# SYMBOL_FILLING_* bitmask constants returned by symbol_info().filling_mode.
SYMBOL_FILLING_FOK_FLAG = 1
SYMBOL_FILLING_IOC_FLAG = 2


class BrokerError(RuntimeError):
    pass


class MT5Client:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.connected = False
        self._symbol_cache: dict[str, str] = {}

    def connect(self, *, required: bool) -> None:
        if mt5 is None:
            message = "MetaTrader5 Python package is not installed."
            if required:
                raise BrokerError(message)
            logger.warning("%s Running without broker connection.", message)
            return

        initialized = mt5.initialize(path=self.settings.mt5_path or None)
        if not initialized:
            message = f"MT5 initialize failed: {mt5.last_error()}"
            if required:
                raise BrokerError(message)
            logger.warning(message)
            return

        if self.settings.mt5_login:
            logged_in = mt5.login(
                self.settings.mt5_login,
                password=self.settings.mt5_password or None,
                server=self.settings.mt5_server or None,
            )
            if not logged_in:
                raise BrokerError(f"MT5 login failed: {mt5.last_error()}")

        self.connected = True
        account = mt5.account_info()
        if account:
            logger.info("Connected to MT5 account %s, balance %.2f", account.login, account.balance)
        else:
            logger.info("Connected to MT5 terminal.")

    def shutdown(self) -> None:
        if mt5 is not None and self.connected:
            mt5.shutdown()
        self.connected = False

    def ensure_ready(self) -> None:
        if not self.connected or mt5 is None:
            raise BrokerError("MT5 is not connected.")

    def ensure_symbol(self, symbol: str) -> Any:
        self.ensure_ready()
        info = mt5.symbol_info(symbol)
        if info is None:
            raise BrokerError(f"MT5 symbol not found: {symbol}")
        if not info.visible and not mt5.symbol_select(symbol, True):
            raise BrokerError(f"Could not select MT5 symbol: {symbol}")
        return mt5.symbol_info(symbol)

    def resolve_broker_symbol(self, telegram_symbol: str) -> str:
        self.ensure_ready()
        requested = telegram_symbol.upper()
        if requested in self._symbol_cache:
            return self._symbol_cache[requested]

        configured = self.settings.symbol_map.get(requested)
        if configured:
            try:
                self.ensure_symbol(configured)
            except BrokerError:
                if not self.settings.auto_discover_symbols:
                    raise
                logger.warning(
                    "Configured symbol map %s -> %s is unavailable; trying broker auto-discovery.",
                    requested,
                    configured,
                )
            else:
                self._symbol_cache[requested] = configured
                if configured.upper() != requested:
                    logger.info("Using configured symbol map %s -> %s.", requested, configured)
                return configured

        exact_info = mt5.symbol_info(requested)
        if exact_info is not None:
            self.ensure_symbol(requested)
            self._symbol_cache[requested] = requested
            return requested

        if not self.settings.auto_discover_symbols:
            raise BrokerError(
                f"MT5 symbol not found: {requested}. Add it to SYMBOL_MAP or enable AUTO_DISCOVER_SYMBOLS."
            )

        broker_symbols = mt5.symbols_get()
        if not broker_symbols:
            raise BrokerError("Could not read broker symbol list from MT5.")

        match = choose_best_symbol(
            requested,
            broker_symbols,
            disabled_trade_mode=getattr(mt5, "SYMBOL_TRADE_MODE_DISABLED", None),
        )
        if match is None:
            raise BrokerError(
                f"No broker symbol match found for {requested}. Add SYMBOL_MAP={requested}=YourBrokerSymbol."
            )

        self.ensure_symbol(match.name)
        self._symbol_cache[requested] = match.name
        logger.info(
            "Auto-discovered broker symbol %s -> %s (%s, score %s).",
            requested,
            match.name,
            match.reason,
            match.score,
        )
        return match.name

    def tick(self, symbol: str) -> Any:
        self.ensure_ready()
        tick = mt5.symbol_info_tick(symbol)
        if tick is None:
            raise BrokerError(f"No tick available for {symbol}")
        return tick

    def current_entry_price(self, symbol: str, direction: Direction) -> float:
        tick = self.tick(symbol)
        return float(tick.ask if direction.is_buy else tick.bid)

    def current_break_even_watch_price(self, symbol: str, direction: Direction) -> float:
        tick = self.tick(symbol)
        return float(tick.bid if direction.is_buy else tick.ask)

    def volume_constraints(self, symbol: str) -> VolumeConstraints:
        info = self.ensure_symbol(symbol)
        return VolumeConstraints(
            minimum=float(info.volume_min),
            maximum=float(info.volume_max),
            step=float(info.volume_step),
        )

    def calculate_volume(
        self,
        *,
        symbol: str,
        entry_price: float,
        stop_loss: float,
    ) -> BrokerVolume:
        info = self.ensure_symbol(symbol)
        account = mt5.account_info()
        if account is None:
            raise BrokerError("Could not read MT5 account info.")

        tick_size = float(info.trade_tick_size or info.point)
        tick_value = float(
            getattr(info, "trade_tick_value_loss", 0.0)
            or getattr(info, "trade_tick_value", 0.0)
        )
        if tick_size <= 0 or tick_value <= 0:
            raise BrokerError(
                f"Symbol {symbol} has invalid tick_size/tick_value for risk sizing."
            )

        price_distance = abs(float(entry_price) - float(stop_loss))
        if price_distance <= 0:
            raise BrokerError("Entry price and stop loss cannot be the same.")

        risk_money = float(account.balance) * (self.settings.risk_percent / 100.0)
        loss_per_lot = (price_distance / tick_size) * tick_value
        raw_volume = risk_money / loss_per_lot
        constraints = self.volume_constraints(symbol)

        used_minimum = raw_volume < constraints.minimum
        if used_minimum:
            total_volume = constraints.minimum
        else:
            total_volume = self._floor_to_step(raw_volume, constraints.step)
            total_volume = max(constraints.minimum, total_volume)

        total_volume = min(total_volume, constraints.maximum)
        total_volume = self._round_volume(total_volume, constraints.step)
        return BrokerVolume(
            total_volume=total_volume,
            risk_money=risk_money,
            loss_per_lot=loss_per_lot,
            raw_volume=raw_volume,
            used_minimum_lot=used_minimum,
        )

    def resolve_entry(
        self,
        *,
        symbol: str,
        direction: Direction,
        entry_type: EntryType,
        entry_price: float | None,
    ) -> tuple[EntryType, float]:
        if entry_type is EntryType.MARKET:
            return EntryType.MARKET, self.current_entry_price(symbol, direction)

        if entry_price is None:
            raise BrokerError("Pending order signal is missing entry price.")

        if entry_type is EntryType.AUTO:
            tick = self.tick(symbol)
            if direction.is_buy:
                resolved = EntryType.LIMIT if entry_price < float(tick.ask) else EntryType.STOP
            else:
                resolved = EntryType.LIMIT if entry_price > float(tick.bid) else EntryType.STOP
            return resolved, float(entry_price)

        return entry_type, float(entry_price)

    def validate_pending_entry(
        self,
        *,
        symbol: str,
        direction: Direction,
        entry_type: EntryType,
        entry_price: float,
    ) -> None:
        if entry_type is EntryType.MARKET:
            return
        tick = self.tick(symbol)
        ask = float(tick.ask)
        bid = float(tick.bid)
        if direction.is_buy and entry_type is EntryType.LIMIT and entry_price >= ask:
            raise BrokerError("Buy limit entry is already at/above market.")
        if direction.is_buy and entry_type is EntryType.STOP and entry_price <= ask:
            raise BrokerError("Buy stop entry is already at/below market.")
        if not direction.is_buy and entry_type is EntryType.LIMIT and entry_price <= bid:
            raise BrokerError("Sell limit entry is already at/below market.")
        if not direction.is_buy and entry_type is EntryType.STOP and entry_price >= bid:
            raise BrokerError("Sell stop entry is already at/above market.")

    def place_order(self, plan: OrderPlan) -> BrokerOrderResult:
        self.ensure_ready()
        info = self.ensure_symbol(plan.symbol)
        resolved_type, price = self._order_type_and_price(plan)
        request: dict[str, Any] = {
            "action": mt5.TRADE_ACTION_DEAL
            if plan.entry_type is EntryType.MARKET
            else mt5.TRADE_ACTION_PENDING,
            "symbol": plan.symbol,
            "volume": float(plan.volume),
            "type": resolved_type,
            "price": round(float(price), int(info.digits)),
            "sl": round(float(plan.stop_loss), int(info.digits)),
            "tp": round(float(plan.take_profit), int(info.digits)),
            "deviation": 20,
            "magic": int(self.settings.mt5_magic),
            "comment": plan.comment,
            "type_time": mt5.ORDER_TIME_GTC,
        }
        ok_codes = {
            mt5.TRADE_RETCODE_DONE,
            mt5.TRADE_RETCODE_PLACED,
            mt5.TRADE_RETCODE_DONE_PARTIAL,
        }
        invalid_fill = getattr(mt5, "TRADE_RETCODE_INVALID_FILL", 10030)
        attempts: list[str] = []
        result = None
        filling_candidates = self._filling_candidates(
            info,
            pending=plan.entry_type is not EntryType.MARKET,
        )
        for index, filling in enumerate(filling_candidates):
            candidate_request = {**request, "type_filling": filling}
            result = mt5.order_send(candidate_request)
            filling_name = self._filling_name(filling)
            if result is None:
                raise BrokerError(
                    f"order_send returned None with {filling_name}: {mt5.last_error()}"
                )
            attempts.append(f"{filling_name}={result.retcode}:{result.comment}")
            if result.retcode in ok_codes:
                if index > 0:
                    logger.info(
                        "Placed %s using fallback filling mode %s after %s rejection(s).",
                        plan.symbol,
                        filling_name,
                        index,
                    )
                break
            if result.retcode == invalid_fill and index + 1 < len(filling_candidates):
                logger.warning(
                    "%s rejected filling mode %s; retrying with %s.",
                    plan.symbol,
                    filling_name,
                    self._filling_name(filling_candidates[index + 1]),
                )
                continue
            raise BrokerError(
                f"order_send failed: retcode={result.retcode}, comment={result.comment}, "
                f"filling_attempts={'; '.join(attempts)}"
            )

        if result is None or result.retcode not in ok_codes:
            raise BrokerError(f"order_send failed for all filling modes: {'; '.join(attempts)}")

        return BrokerOrderResult(
            ticket=int(result.order),
            deal=int(result.deal) if getattr(result, "deal", 0) else None,
            retcode=int(result.retcode),
            comment=plan.comment,
        )

    def find_positions(self, *, symbol: str, comment_prefix: str) -> list[Any]:
        self.ensure_ready()
        positions = mt5.positions_get(symbol=symbol) or []
        return [
            position
            for position in positions
            if int(getattr(position, "magic", 0)) == self.settings.mt5_magic
            and str(getattr(position, "comment", "")).startswith(comment_prefix)
        ]

    def find_orders(self, *, symbol: str, comment_prefix: str) -> list[Any]:
        self.ensure_ready()
        orders = mt5.orders_get(symbol=symbol) or []
        return [
            order
            for order in orders
            if int(getattr(order, "magic", 0)) == self.settings.mt5_magic
            and str(getattr(order, "comment", "")).startswith(comment_prefix)
        ]

    def move_position_sl_to_break_even(
        self,
        position: Any,
        *,
        direction: Direction,
        offset_points: float,
    ) -> None:
        self.ensure_ready()
        info = self.ensure_symbol(str(position.symbol))
        offset = float(offset_points) * float(info.point)
        entry = float(position.price_open)
        new_sl = entry + offset if direction.is_buy else entry - offset
        current_sl = float(position.sl or 0.0)

        if direction.is_buy and current_sl >= new_sl:
            return
        if not direction.is_buy and current_sl != 0.0 and current_sl <= new_sl:
            return

        request = {
            "action": mt5.TRADE_ACTION_SLTP,
            "position": int(position.ticket),
            "symbol": str(position.symbol),
            "sl": round(new_sl, int(info.digits)),
            "tp": round(float(position.tp or 0.0), int(info.digits)),
            "magic": int(self.settings.mt5_magic),
            "comment": f"{self.settings.trade_comment_prefix}:BE",
        }
        result = mt5.order_send(request)
        if result is None or result.retcode != mt5.TRADE_RETCODE_DONE:
            raise BrokerError(
                f"SLTP modify failed for position {position.ticket}: "
                f"{None if result is None else result.retcode}"
            )

    def cancel_order(self, order: Any) -> None:
        self.ensure_ready()
        request = {
            "action": mt5.TRADE_ACTION_REMOVE,
            "order": int(order.ticket),
            "symbol": str(order.symbol),
            "magic": int(self.settings.mt5_magic),
            "comment": f"{self.settings.trade_comment_prefix}:TTL",
        }
        result = mt5.order_send(request)
        if result is None or result.retcode != mt5.TRADE_RETCODE_DONE:
            raise BrokerError(
                f"Pending order cancel failed for {order.ticket}: "
                f"{None if result is None else result.retcode}"
            )

    def _order_type_and_price(self, plan: OrderPlan) -> tuple[int, float]:
        if plan.entry_type is EntryType.MARKET:
            tick = self.tick(plan.symbol)
            order_type = mt5.ORDER_TYPE_BUY if plan.direction.is_buy else mt5.ORDER_TYPE_SELL
            price = float(tick.ask if plan.direction.is_buy else tick.bid)
            return order_type, price

        if plan.entry_price is None:
            raise BrokerError("Pending plan is missing entry price.")

        if plan.direction.is_buy and plan.entry_type is EntryType.LIMIT:
            return mt5.ORDER_TYPE_BUY_LIMIT, plan.entry_price
        if plan.direction.is_buy and plan.entry_type is EntryType.STOP:
            return mt5.ORDER_TYPE_BUY_STOP, plan.entry_price
        if not plan.direction.is_buy and plan.entry_type is EntryType.LIMIT:
            return mt5.ORDER_TYPE_SELL_LIMIT, plan.entry_price
        if not plan.direction.is_buy and plan.entry_type is EntryType.STOP:
            return mt5.ORDER_TYPE_SELL_STOP, plan.entry_price
        raise BrokerError(f"Unsupported order plan: {plan}")

    def _filling_candidates(self, info: Any, *, pending: bool) -> tuple[int, ...]:
        filling_mode = int(getattr(info, "filling_mode", 0))
        allowed: list[int] = []
        if filling_mode & SYMBOL_FILLING_FOK_FLAG:
            allowed.append(mt5.ORDER_FILLING_FOK)
        if filling_mode & SYMBOL_FILLING_IOC_FLAG:
            allowed.append(mt5.ORDER_FILLING_IOC)

        preferred = [mt5.ORDER_FILLING_RETURN, *allowed] if pending else allowed
        # Broker metadata is not always reliable. Unsupported-fill retcode 10030
        # guarantees the rejected request was not executed, so trying the other
        # standard policies is safe and avoids silently missing a valid signal.
        fallbacks = [
            mt5.ORDER_FILLING_FOK,
            mt5.ORDER_FILLING_IOC,
            mt5.ORDER_FILLING_RETURN,
        ]
        candidates: list[int] = []
        for value in [*preferred, *fallbacks]:
            if value not in candidates:
                candidates.append(value)
        return tuple(candidates)

    def _filling_name(self, filling: int) -> str:
        names = {
            mt5.ORDER_FILLING_FOK: "FOK",
            mt5.ORDER_FILLING_IOC: "IOC",
            mt5.ORDER_FILLING_RETURN: "RETURN",
        }
        return names.get(filling, str(filling))

    def _floor_to_step(self, value: float, step: float) -> float:
        if step <= 0:
            return value
        return math.floor(value / step) * step

    def _round_volume(self, value: float, step: float) -> float:
        if step <= 0:
            return value
        decimals = max(0, min(8, len(f"{step:.8f}".rstrip("0").split(".")[-1])))
        return round(value, decimals)
