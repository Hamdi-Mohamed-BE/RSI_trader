from datetime import datetime
from sqlmodel import Session
from app.trading.mt5_client import mt5_client
from app.db.models import ManagedTrade
from app.db.repositories import ManagedTradeRepository, SystemEventRepository
from app.core.logging import logger, orders_logger

class TradeManager:
    @staticmethod
    def process_break_even(session: Session, dynamic_offset_points: int | None = None) -> int:
        """
        Protects active copier trades:
        - TP1 reached: move SL to break-even.
        - TP2 reached: close 50% once and leave the rest running to TP3/final TP.
        Returns: number of successful trade-management actions.
        """
        active_db_trades = ManagedTradeRepository.get_active(session)
        if not active_db_trades:
            return 0

        # Poll all active positions from MT5
        mt5_positions = mt5_client.get_positions()
        # Create mapping of ticket -> position dict for fast lookup
        mt5_pos_map = {pos["ticket"]: pos for pos in mt5_positions}

        modified_count = 0

        for trade in active_db_trades:
            ticket = trade.mt5_ticket
            
            # If trade is no longer active in MT5, mark it as closed in DB
            if ticket not in mt5_pos_map:
                logger.info(f"Managed trade {ticket} is no longer active in MT5. Marking as closed.")
                trade.status = "closed"
                trade.updated_at = datetime.utcnow()
                ManagedTradeRepository.save(session, trade)
                continue
                
            pos = mt5_pos_map[ticket]
            current_price = pos["price_current"]
            entry_price = trade.entry_price
            side = trade.side.lower()

            if (
                not trade.break_even_done
                and trade.break_even_enabled
                and trade.break_even_trigger_tp
                and TradeManager._price_reached(side, current_price, trade.break_even_trigger_tp)
            ):
                modified_count += TradeManager._move_to_break_even(
                    session=session,
                    trade=trade,
                    pos=pos,
                    dynamic_offset_points=dynamic_offset_points,
                )

            take_profits = trade.take_profits
            tp2 = take_profits[1] if len(take_profits) >= 3 else None
            if (
                tp2
                and not trade.tp2_partial_done
                and TradeManager._price_reached(side, current_price, tp2)
            ):
                modified_count += TradeManager._close_half_at_tp2(session, trade, pos, tp2)
                    
        return modified_count

    @staticmethod
    def _price_reached(side: str, current_price: float, target: float) -> bool:
        if side == "buy":
            return current_price >= target
        if side == "sell":
            return current_price <= target
        return False

    @staticmethod
    def _move_to_break_even(
        session: Session,
        trade: ManagedTrade,
        pos: dict,
        dynamic_offset_points: int | None = None,
    ) -> int:
        ticket = trade.mt5_ticket
        orders_logger.info(
            f"Trade {ticket} ({trade.symbol_raw}) hit TP1 trigger {trade.break_even_trigger_tp}. Triggering break-even."
        )

        sym_info = mt5_client.get_symbol_info(trade.broker_symbol)
        point = sym_info.get("point") if sym_info else 0.00001
        digits = sym_info.get("digits") if sym_info else 5
        offset_pts = dynamic_offset_points if dynamic_offset_points is not None else 0
        offset_price = offset_pts * point

        if trade.side.lower() == "buy":
            new_sl = trade.entry_price + offset_price
        else:
            new_sl = trade.entry_price - offset_price
        new_sl = round(new_sl, digits)

        orders_logger.info(f"Moving SL for trade {ticket} from current {pos['sl']} to break-even {new_sl}")

        success, error = mt5_client.modify_position(ticket, stop_loss=new_sl, take_profit=trade.final_take_profit)

        if success:
            trade.stop_loss_current = new_sl
            trade.break_even_done = True
            trade.break_even_done_at = datetime.utcnow()
            trade.updated_at = datetime.utcnow()
            ManagedTradeRepository.save(session, trade)

            SystemEventRepository.log(
                session,
                level="success",
                source="trading",
                message=f"Moved trade {ticket} ({trade.symbol_raw}) to break-even at {new_sl}"
            )
            return 1

        orders_logger.error(f"Failed to move trade {ticket} to break-even. Error: {error}")
        SystemEventRepository.log(
            session,
            level="error",
            source="trading",
            message=f"Failed to move trade {ticket} to break-even: {error}"
        )
        return 0

    @staticmethod
    def _close_half_at_tp2(session: Session, trade: ManagedTrade, pos: dict, tp2: float) -> int:
        ticket = trade.mt5_ticket
        current_volume = float(pos.get("volume") or trade.lot)
        half_volume = current_volume / 2

        orders_logger.info(
            f"Trade {ticket} ({trade.symbol_raw}) hit TP2 {tp2}. Closing 50% ({half_volume:g}) and leaving the rest to TP3/final TP."
        )
        success, result, error = mt5_client.close_partial_position(
            ticket,
            volume=half_volume,
            comment=f"TG TP2 half {ticket}",
        )

        if success:
            trade.tp2_partial_done = True
            trade.tp2_partial_done_at = datetime.utcnow()
            trade.tp2_partial_volume = half_volume
            trade.updated_at = datetime.utcnow()
            ManagedTradeRepository.save(session, trade)

            SystemEventRepository.log(
                session,
                level="success",
                source="trading",
                message=f"Closed 50% of trade {ticket} ({trade.symbol_raw}) at TP2 {tp2}; remainder is running to TP3/final TP.",
                details={"mt5_result": result},
            )
            return 1

        orders_logger.error(f"Failed to close 50% of trade {ticket} at TP2. Error: {error}")
        SystemEventRepository.log(
            session,
            level="error",
            source="trading",
            message=f"Failed TP2 partial close for trade {ticket}: {error}",
            details={"mt5_result": result},
        )
        return 0
