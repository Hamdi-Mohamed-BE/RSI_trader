from __future__ import annotations

from datetime import datetime, timedelta, timezone
from math import floor

import MetaTrader5 as mt5
import pandas as pd
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..engine.strategy import SignalDecision
from ..models import OrderRecord
from ..schemas import RuntimeConfig, SymbolConfig


class MT5ExecutionError(RuntimeError):
    pass


class MT5Bridge:
    def __enter__(self) -> "MT5Bridge":
        if not mt5.initialize():
            raise MT5ExecutionError(f"MT5 initialization failed: {mt5.last_error()}")
        return self

    def __exit__(self, *_args) -> None:
        mt5.shutdown()

    @staticmethod
    def bars(symbol: str, count: int = 10_000) -> pd.DataFrame:
        if not mt5.symbol_select(symbol, True):
            raise MT5ExecutionError(f"MT5 symbol is unavailable: {symbol}")
        rates = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_M1, 0, count)
        if rates is None or not len(rates):
            raise MT5ExecutionError(f"MT5 returned no M1 bars for {symbol}: {mt5.last_error()}")
        frame = pd.DataFrame(rates)
        frame.index = pd.to_datetime(frame.pop("time"), unit="s", utc=True)
        frame = frame.rename(columns={"tick_volume": "volume"})
        return frame[["open", "high", "low", "close", "volume"]].sort_index()

    @staticmethod
    def mid_price(symbol: str) -> float:
        tick = mt5.symbol_info_tick(symbol)
        if tick is None:
            raise MT5ExecutionError(f"No live MT5 tick for {symbol}.")
        return (float(tick.bid) + float(tick.ask)) / 2.0

    def place(
        self,
        db: Session,
        decision: SignalDecision,
        config: RuntimeConfig,
        symbol_config: SymbolConfig,
        basis: float,
    ) -> OrderRecord | None:
        if (
            not config.mt5_live_orders_enabled
            or decision.status != "A_PLUS"
            or decision.entry is None
            or decision.stop_loss is None
            or decision.take_profit is None
        ):
            return None
        if self._daily_order_count(db) >= config.max_trades_per_day:
            return None
        symbol = symbol_config.mt5_symbol
        info = mt5.symbol_info(symbol)
        tick = mt5.symbol_info_tick(symbol)
        account = mt5.account_info()
        if info is None or tick is None or account is None:
            raise MT5ExecutionError(f"MT5 account or symbol state is unavailable for {symbol}.")
        if not account.trade_allowed:
            raise MT5ExecutionError("The connected MT5 account does not allow trading.")
        side_type = mt5.POSITION_TYPE_BUY if decision.direction == "BUY" else mt5.POSITION_TYPE_SELL
        if any(
            position.magic == config.mt5_magic_number and position.type == side_type
            for position in (mt5.positions_get(symbol=symbol) or [])
        ):
            return None
        if any(
            order.magic == config.mt5_magic_number
            and self._order_side(order.type) == decision.direction
            for order in (mt5.orders_get(symbol=symbol) or [])
        ):
            return None

        market = decision.order_type == "MARKET"
        entry = float(tick.ask if decision.direction == "BUY" else tick.bid) if market else float(decision.entry)
        stop = float(decision.stop_loss)
        target = float(decision.take_profit)
        entry, stop, target = self._valid_levels(info, decision.direction, entry, stop, target)
        order_type = self._order_type(decision.direction, market, entry, tick)
        risk_amount = float(account.balance) * config.risk_percent / 100.0
        volume, actual_risk, minimum_forced = self._risk_volume(
            symbol, order_type, entry, stop, risk_amount, info
        )
        request = {
            "action": mt5.TRADE_ACTION_DEAL if market else mt5.TRADE_ACTION_PENDING,
            "symbol": symbol,
            "volume": volume,
            "type": order_type,
            "price": round(entry, info.digits),
            "sl": round(stop, info.digits),
            "tp": round(target, info.digits),
            "deviation": 30,
            "magic": config.mt5_magic_number,
            "comment": f"NAW LTA S{decision.score:.0f}",
            "type_time": mt5.ORDER_TIME_GTC,
        }
        result = self._send(request, market)
        accepted = {mt5.TRADE_RETCODE_DONE, mt5.TRADE_RETCODE_PLACED, mt5.TRADE_RETCODE_DONE_PARTIAL}
        if result is None or result.retcode not in accepted:
            message = mt5.last_error() if result is None else f"{result.retcode} {result.comment}"
            raise MT5ExecutionError(f"MT5 rejected {decision.direction} {symbol}: {message}")
        ticket = int(result.order or result.deal)
        record = OrderRecord(
            symbol=decision.symbol,
            side=decision.direction,
            order_type=decision.order_type or "LIMIT",
            status="OPEN" if market else "PENDING",
            entry=entry,
            stop_loss=stop,
            take_profit=target,
            quantity=volume,
            risk_amount=actual_risk,
            score=decision.score,
            external_id=str(ticket),
            metadata_json={
                "initial_stop": stop,
                "reward_risk": decision.reward_risk,
                "mt5_symbol": symbol,
                "basis": basis,
                "minimum_lot_forced": minimum_forced,
                "requested_risk": risk_amount,
                "paper": False,
            },
        )
        db.add(record)
        db.commit()
        return record

    def reconcile(self, db: Session, config: RuntimeConfig, symbol_config: SymbolConfig) -> None:
        records = db.scalars(
            select(OrderRecord).where(
                OrderRecord.symbol == "XAUUSD", OrderRecord.status.in_(("OPEN", "PENDING"))
            )
        ).all()
        symbol = symbol_config.mt5_symbol
        positions = [
            item for item in (mt5.positions_get(symbol=symbol) or [])
            if item.magic == config.mt5_magic_number
        ]
        orders = [
            item for item in (mt5.orders_get(symbol=symbol) or [])
            if item.magic == config.mt5_magic_number
        ]
        tick = mt5.symbol_info_tick(symbol)
        for record in records:
            ticket = int(record.external_id or 0)
            if record.status == "PENDING":
                if any(item.ticket == ticket for item in orders):
                    continue
                same_side = [
                    item for item in positions
                    if (record.side == "BUY" and item.type == mt5.POSITION_TYPE_BUY)
                    or (record.side == "SELL" and item.type == mt5.POSITION_TYPE_SELL)
                ]
                if same_side:
                    record.status = "OPEN"
                    record.external_id = str(same_side[0].ticket)
                    record.entry = float(same_side[0].price_open)
                else:
                    record.status = "CANCELLED"
                continue
            position = next((item for item in positions if item.ticket == ticket), None)
            if position is None:
                deals = mt5.history_deals_get(
                    record.opened_at - timedelta(hours=1), datetime.now(timezone.utc) + timedelta(minutes=1)
                ) or []
                related = [deal for deal in deals if deal.position_id == ticket]
                record.status = "CLOSED"
                record.closed_at = datetime.now(timezone.utc)
                record.pnl = sum(float(deal.profit + deal.commission + deal.swap) for deal in related)
                continue
            if not config.trail_enabled or tick is None:
                continue
            initial_stop = float(record.metadata_json.get("initial_stop", record.stop_loss))
            risk = abs(record.entry - initial_stop)
            if not risk:
                continue
            price = float(tick.bid if record.side == "BUY" else tick.ask)
            favorable_r = (
                (price - record.entry) / risk
                if record.side == "BUY"
                else (record.entry - price) / risk
            )
            if favorable_r < config.trail_step_r:
                continue
            steps = int(favorable_r // config.trail_step_r)
            locked_r = max(0.0, (steps - 1) * config.trail_step_r)
            candidate = record.entry + (risk * locked_r if record.side == "BUY" else -risk * locked_r)
            improves = candidate > position.sl if record.side == "BUY" else candidate < position.sl
            if improves:
                result = mt5.order_send(
                    {
                        "action": mt5.TRADE_ACTION_SLTP,
                        "position": position.ticket,
                        "symbol": symbol,
                        "sl": candidate,
                        "tp": position.tp,
                        "magic": config.mt5_magic_number,
                    }
                )
                if result and result.retcode == mt5.TRADE_RETCODE_DONE:
                    record.stop_loss = candidate
        db.commit()

    @staticmethod
    def _daily_order_count(db: Session) -> int:
        start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
        return int(
            db.scalar(
                select(func.count(OrderRecord.id)).where(
                    OrderRecord.opened_at >= start,
                    OrderRecord.metadata_json["paper"].as_boolean() == False,  # noqa: E712
                )
            )
            or 0
        )

    @staticmethod
    def _risk_volume(symbol, order_type, entry, stop, risk_amount, info) -> tuple[float, float, bool]:
        market_type = mt5.ORDER_TYPE_BUY if order_type in {
            mt5.ORDER_TYPE_BUY, mt5.ORDER_TYPE_BUY_LIMIT, mt5.ORDER_TYPE_BUY_STOP
        } else mt5.ORDER_TYPE_SELL
        loss_per_lot = abs(float(mt5.order_calc_profit(market_type, symbol, 1.0, entry, stop) or 0.0))
        if not loss_per_lot:
            raise MT5ExecutionError(f"Cannot calculate MT5 risk for {symbol}.")
        raw = risk_amount / loss_per_lot
        minimum_forced = raw < info.volume_min
        stepped = floor(raw / info.volume_step) * info.volume_step
        volume = max(info.volume_min, min(info.volume_max, stepped))
        volume = round(volume, 8)
        return volume, loss_per_lot * volume, minimum_forced

    @staticmethod
    def _valid_levels(info, side: str, entry: float, stop: float, target: float) -> tuple[float, float, float]:
        minimum = max(float(info.trade_stops_level * info.point), float(info.point))
        if side == "BUY":
            stop = min(stop, entry - minimum)
            target = max(target, entry + minimum)
        else:
            stop = max(stop, entry + minimum)
            target = min(target, entry - minimum)
        return entry, stop, target

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
            mt5.ORDER_TYPE_BUY, mt5.ORDER_TYPE_BUY_LIMIT, mt5.ORDER_TYPE_BUY_STOP,
            mt5.ORDER_TYPE_BUY_STOP_LIMIT,
        } else "SELL"

    @staticmethod
    def _send(request: dict, market: bool):
        filling_modes = [mt5.ORDER_FILLING_IOC, mt5.ORDER_FILLING_FOK] if market else [mt5.ORDER_FILLING_RETURN]
        last_result = None
        for filling in filling_modes:
            request["type_filling"] = filling
            result = mt5.order_send(request)
            last_result = result
            if result and result.retcode in {
                mt5.TRADE_RETCODE_DONE, mt5.TRADE_RETCODE_PLACED, mt5.TRADE_RETCODE_DONE_PARTIAL
            }:
                return result
        return last_result
