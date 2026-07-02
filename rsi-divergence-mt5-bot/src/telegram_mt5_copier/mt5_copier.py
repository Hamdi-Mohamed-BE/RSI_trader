from __future__ import annotations

from dataclasses import asdict, dataclass
from math import floor

import MetaTrader5 as mt5

from .models import TradeSignal
from .settings import Settings
from .state import StateStore


class MT5CopyError(RuntimeError):
    pass


@dataclass(frozen=True)
class Placement:
    ticket: int
    symbol: str
    side: str
    order_type: str
    entry: float
    stop_loss: float
    tp1: float
    final_tp: float
    volume: float
    requested_risk: float
    actual_risk: float
    minimum_lot_forced: bool

    def to_dict(self) -> dict:
        return asdict(self)


class MT5Copier:
    def __init__(self, settings: Settings, state: StateStore):
        self.settings = settings
        self.state = state

    def place(self, signal: TradeSignal, message_key: str) -> Placement:
        self._initialize()
        try:
            account = mt5.account_info()
            if account is None or not account.trade_allowed:
                raise MT5CopyError("The connected MT5 account does not allow trading.")
            symbol = self.resolve_symbol(signal.symbol)
            info = mt5.symbol_info(symbol)
            tick = mt5.symbol_info_tick(symbol)
            if info is None or tick is None:
                raise MT5CopyError(f"No MT5 symbol/tick data for {symbol}.")
            direction_type = mt5.POSITION_TYPE_BUY if signal.side == "BUY" else mt5.POSITION_TYPE_SELL
            if any(position.type == direction_type for position in (mt5.positions_get(symbol=symbol) or [])):
                raise MT5CopyError(f"A {signal.side} position is already open on {symbol}.")
            if any(self._order_side(order.type) == signal.side for order in (mt5.orders_get(symbol=symbol) or [])):
                raise MT5CopyError(f"A {signal.side} pending order already exists on {symbol}.")

            market, entry = self._entry(signal, tick)
            self._validate_live_geometry(signal, entry)
            order_type = self._order_type(signal.side, market, entry, tick)
            entry, stop, target = self._broker_levels(
                info, signal.side, entry, signal.stop_loss, signal.final_tp
            )
            requested_risk = float(account.balance) * self.settings.risk_percent / 100.0
            volume, actual_risk, forced = self._risk_volume(
                symbol, order_type, entry, stop, requested_risk, info
            )
            request = {
                "action": mt5.TRADE_ACTION_DEAL if market else mt5.TRADE_ACTION_PENDING,
                "symbol": symbol,
                "volume": volume,
                "type": order_type,
                "price": round(entry, info.digits),
                "sl": round(stop, info.digits),
                "tp": round(target, info.digits),
                "deviation": self.settings.mt5_deviation_points,
                "magic": self.settings.mt5_magic_number,
                "comment": "TG API COPY",
                "type_time": mt5.ORDER_TIME_GTC,
            }
            result = self._send(request, market)
            accepted = {
                mt5.TRADE_RETCODE_DONE,
                mt5.TRADE_RETCODE_PLACED,
                mt5.TRADE_RETCODE_DONE_PARTIAL,
            }
            if result is None or result.retcode not in accepted:
                detail = mt5.last_error() if result is None else f"{result.retcode} {result.comment}"
                raise MT5CopyError(f"MT5 rejected {signal.side} {symbol}: {detail}")
            placement = Placement(
                ticket=int(result.order or result.deal),
                symbol=symbol,
                side=signal.side,
                order_type="MARKET" if market else "PENDING",
                entry=entry,
                stop_loss=stop,
                tp1=signal.tp1,
                final_tp=target,
                volume=volume,
                requested_risk=requested_risk,
                actual_risk=actual_risk,
                minimum_lot_forced=forced,
            )
            self.state.record_trade(
                message_key=message_key,
                ticket=placement.ticket,
                symbol=symbol,
                side=signal.side,
                entry=entry,
                stop_loss=stop,
                tp1=signal.tp1,
                final_tp=target,
                volume=volume,
                status="OPEN" if market else "PENDING",
                detail=placement.to_dict(),
            )
            return placement
        finally:
            mt5.shutdown()

    def protect_trades(self) -> list[str]:
        active = self.state.active_trades()
        if not active:
            return []
        self._initialize()
        actions: list[str] = []
        try:
            for trade in active:
                pending_orders = [
                    order for order in (mt5.orders_get(symbol=trade["symbol"]) or [])
                    if order.magic == self.settings.mt5_magic_number
                    and self._order_side(order.type) == trade["side"]
                ]
                positions = [
                    position for position in (mt5.positions_get(symbol=trade["symbol"]) or [])
                    if position.magic == self.settings.mt5_magic_number
                    and self._position_side(position.type) == trade["side"]
                ]
                if not positions:
                    if trade["status"] == "PENDING" and not pending_orders:
                        self.state.update_trade(trade["id"], "CANCELLED")
                    elif trade["status"] != "PENDING":
                        self.state.update_trade(trade["id"], "CLOSED")
                    continue
                position = positions[0]
                if trade["status"] == "PENDING":
                    self.state.update_trade(trade["id"], "OPEN")
                tick = mt5.symbol_info_tick(trade["symbol"])
                if tick is None:
                    continue
                price = float(tick.bid if trade["side"] == "BUY" else tick.ask)
                reached = price >= trade["tp1"] if trade["side"] == "BUY" else price <= trade["tp1"]
                improved = (
                    position.sl < trade["entry"] if trade["side"] == "BUY"
                    else position.sl > trade["entry"] or position.sl == 0
                )
                if not reached or not improved:
                    continue
                result = mt5.order_send(
                    {
                        "action": mt5.TRADE_ACTION_SLTP,
                        "position": position.ticket,
                        "symbol": trade["symbol"],
                        "sl": trade["entry"],
                        "tp": position.tp,
                        "magic": self.settings.mt5_magic_number,
                    }
                )
                if result and result.retcode == mt5.TRADE_RETCODE_DONE:
                    self.state.update_trade(trade["id"], "PROTECTED", trade["entry"])
                    actions.append(f"{trade['symbol']} moved to break-even after TP1")
            return actions
        finally:
            mt5.shutdown()

    def resolve_symbol(self, requested: str) -> str:
        canonical = self.settings.aliases.get(requested.upper(), requested.upper())
        symbols = mt5.symbols_get() or []
        candidates = []
        for item in symbols:
            normalized = _normalize_symbol(item.name)
            if normalized == canonical:
                candidates.append((0, len(item.name), item.name))
            elif normalized.startswith(canonical):
                candidates.append((1, len(item.name), item.name))
            elif canonical in normalized:
                candidates.append((2, len(item.name), item.name))
        if not candidates:
            raise MT5CopyError(f"No broker symbol matches Telegram symbol {requested}.")
        symbol = min(candidates)[2]
        if not mt5.symbol_select(symbol, True):
            raise MT5CopyError(f"MT5 could not select {symbol}.")
        return symbol

    @staticmethod
    def _entry(signal: TradeSignal, tick) -> tuple[bool, float]:
        market_price = float(tick.ask if signal.side == "BUY" else tick.bid)
        if signal.market or signal.entry_low is None or signal.entry_high is None:
            return True, market_price
        if signal.entry_low <= market_price <= signal.entry_high:
            return True, market_price
        return False, (signal.entry_low + signal.entry_high) / 2.0

    @staticmethod
    def _validate_live_geometry(signal: TradeSignal, entry: float) -> None:
        if signal.side == "BUY":
            valid = signal.stop_loss < entry < signal.final_tp
        else:
            valid = signal.final_tp < entry < signal.stop_loss
        if not valid:
            raise MT5CopyError(
                f"Signal is no longer valid at {entry}: SL={signal.stop_loss}, TP={signal.final_tp}."
            )

    @staticmethod
    def _broker_levels(info, side, entry, stop, target) -> tuple[float, float, float]:
        minimum = max(float(info.trade_stops_level * info.point), float(info.point))
        if side == "BUY":
            stop = min(stop, entry - minimum)
            target = max(target, entry + minimum)
        else:
            stop = max(stop, entry + minimum)
            target = min(target, entry - minimum)
        return entry, stop, target

    @staticmethod
    def _risk_volume(symbol, order_type, entry, stop, risk_amount, info) -> tuple[float, float, bool]:
        market_type = (
            mt5.ORDER_TYPE_BUY
            if order_type in {mt5.ORDER_TYPE_BUY, mt5.ORDER_TYPE_BUY_LIMIT, mt5.ORDER_TYPE_BUY_STOP}
            else mt5.ORDER_TYPE_SELL
        )
        loss_per_lot = abs(float(mt5.order_calc_profit(market_type, symbol, 1.0, entry, stop) or 0.0))
        if loss_per_lot <= 0:
            raise MT5CopyError(f"MT5 could not calculate risk for {symbol}.")
        raw = risk_amount / loss_per_lot
        minimum_forced = raw < info.volume_min
        stepped = floor(raw / info.volume_step) * info.volume_step
        volume = round(max(info.volume_min, min(info.volume_max, stepped)), 8)
        return volume, loss_per_lot * volume, minimum_forced

    @staticmethod
    def _order_type(side: str, market: bool, entry: float, tick) -> int:
        if market:
            return mt5.ORDER_TYPE_BUY if side == "BUY" else mt5.ORDER_TYPE_SELL
        if side == "BUY":
            return mt5.ORDER_TYPE_BUY_LIMIT if entry < tick.ask else mt5.ORDER_TYPE_BUY_STOP
        return mt5.ORDER_TYPE_SELL_LIMIT if entry > tick.bid else mt5.ORDER_TYPE_SELL_STOP

    @staticmethod
    def _order_side(order_type: int) -> str:
        return "BUY" if order_type in {
            mt5.ORDER_TYPE_BUY,
            mt5.ORDER_TYPE_BUY_LIMIT,
            mt5.ORDER_TYPE_BUY_STOP,
            mt5.ORDER_TYPE_BUY_STOP_LIMIT,
        } else "SELL"

    @staticmethod
    def _position_side(position_type: int) -> str:
        return "BUY" if position_type == mt5.POSITION_TYPE_BUY else "SELL"

    @staticmethod
    def _send(request: dict, market: bool):
        modes = [mt5.ORDER_FILLING_IOC, mt5.ORDER_FILLING_FOK] if market else [mt5.ORDER_FILLING_RETURN]
        result = None
        for mode in modes:
            request["type_filling"] = mode
            result = mt5.order_send(request)
            if result and result.retcode in {
                mt5.TRADE_RETCODE_DONE,
                mt5.TRADE_RETCODE_PLACED,
                mt5.TRADE_RETCODE_DONE_PARTIAL,
            }:
                return result
        return result

    @staticmethod
    def _initialize() -> None:
        if not mt5.initialize():
            raise MT5CopyError(f"MT5 initialization failed: {mt5.last_error()}")


def _normalize_symbol(value: str) -> str:
    return "".join(character for character in value.upper() if character.isalnum())
