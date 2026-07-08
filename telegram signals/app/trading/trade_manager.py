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
        Retrieves active trades from DB, polls MT5 positions, checks if TP1 has been reached,
        and moves stop loss to entry price + offset if break-even is triggered.
        Returns: number of trades successfully moved to break-even.
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
                
            # If break-even is already done, skip
            if trade.break_even_done:
                continue

            # Check if break-even is enabled and trigger TP exists
            if not trade.break_even_enabled or not trade.break_even_trigger_tp:
                continue

            pos = mt5_pos_map[ticket]
            current_price = pos["price_current"]
            entry_price = trade.entry_price
            side = trade.side.lower()
            trigger_tp = trade.break_even_trigger_tp
            
            # Check if target TP1 trigger has been reached
            trigger_reached = False
            if side == "buy":
                trigger_reached = current_price >= trigger_tp
            elif side == "sell":
                trigger_reached = current_price <= trigger_tp

            if trigger_reached:
                orders_logger.info(f"Trade {ticket} ({trade.symbol_raw}) hit TP1 trigger {trigger_tp}. Triggering break-even.")
                
                # Fetch symbol info to get point size
                sym_info = mt5_client.get_symbol_info(trade.broker_symbol)
                point = sym_info.get("point") if sym_info else 0.00001
                
                # Calculate new SL
                offset_pts = dynamic_offset_points if dynamic_offset_points is not None else 0
                offset_price = offset_pts * point
                
                if side == "buy":
                    new_sl = entry_price + offset_price
                else:
                    new_sl = entry_price - offset_price

                # Send modification request to MT5
                # For safety, let's round the SL to symbol digits
                digits = sym_info.get("digits") if sym_info else 5
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
                    modified_count += 1
                else:
                    orders_logger.error(f"Failed to move trade {ticket} to break-even. Error: {error}")
                    SystemEventRepository.log(
                        session,
                        level="error",
                        source="trading",
                        message=f"Failed to move trade {ticket} to break-even: {error}"
                    )
                    
        return modified_count
