import asyncio
import traceback
from datetime import datetime
from sqlmodel import Session
from typing import Any, Optional

from app.core.logging import logger, orders_logger
from app.telegram.poller import TelegramPoller
from app.llm.parser import parse_signal
from app.trading.mt5_client import mt5_client
from app.trading.symbol_resolver import symbol_resolver
from app.trading.risk import RiskCalculator
from app.trading.lot_config import fixed_lot_for_signal
from app.trading.order_builder import OrderBuilder
from app.trading.trade_manager import TradeManager
from app.services.settings_service import SettingsService
from app.db.database import engine
from app.db.models import OrderAttempt, ManagedTrade, TelegramMessage
from app.db.repositories import OrderAttemptRepository, ManagedTradeRepository, SystemEventRepository, TelegramMessageRepository

class CopierService:
    def __init__(self):
        self._poller = TelegramPoller()
        self._loop_task: asyncio.Task | None = None
        self._is_running = False

    def start(self):
        """Starts the copier background orchestration loop."""
        if self._is_running:
            return
        self._is_running = True
        self._loop_task = asyncio.create_task(self._orchestration_loop())
        logger.info("Copier service background loop started.")

    async def stop(self):
        """Stops the copier background loop."""
        self._is_running = False
        if self._loop_task:
            self._loop_task.cancel()
            try:
                await self._loop_task
            except asyncio.CancelledError:
                pass
            self._loop_task = None
        logger.info("Copier service background loop stopped.")

    def is_running(self) -> bool:
        return self._is_running

    async def _orchestration_loop(self):
        """Infinite loop polling Telegram and managing trades every 10 seconds."""
        poll_interval = 10
        while self._is_running:
            try:
                # Open a new database session
                with Session(engine) as session:
                    # 1. Load latest settings
                    copier_enabled = SettingsService.get(session, "copier_enabled")
                    poll_interval = int(SettingsService.get(session, "poll_interval_seconds") or 10)
                    
                    if copier_enabled:
                        logger.debug("Copier is enabled. Processing cycle...")
                        
                        # 2. Poll and process new messages
                        new_messages = await self._poller.poll_messages(session)
                        if new_messages:
                            logger.info(f"Polled {len(new_messages)} new messages. Processing...")
                            for msg in new_messages:
                                if msg.ignored:
                                    continue
                                try:
                                    await self._process_message(session, msg)
                                except Exception as e:
                                    logger.error(f"Error processing message {msg.id}: {e}")
                                    traceback.print_exc()
                        
                        # 3. Process break-even triggers
                        try:
                            be_offset = int(SettingsService.get(session, "break_even_offset_points") or 0)
                            be_enabled = SettingsService.get(session, "move_to_break_even_enabled")
                            if be_enabled:
                                TradeManager.process_break_even(session, dynamic_offset_points=be_offset)
                        except Exception as e:
                            logger.error(f"Error in break-even trade manager: {e}")
                    else:
                        logger.debug("Copier is disabled. Skipping cycle.")
                        
            except Exception as e:
                logger.error(f"Exception in copier orchestration loop: {e}", exc_info=True)
                
            await asyncio.sleep(max(1, poll_interval))

    async def _process_message(self, session: Session, msg: TelegramMessage):
        """Pipeline processing a single Telegram message into a trade order."""
        logger.info(f"Processing message {msg.message_id} from chat {msg.chat_id}")
        
        # 1. Check max daily limit
        max_daily = int(SettingsService.get(session, "max_trades_per_day") or 0)
        if max_daily > 0:
            today_placed = OrderAttemptRepository.get_trades_count_for_day(session, datetime.utcnow().strftime("%Y-%m-%d"))
            if today_placed >= max_daily:
                logger.warning(f"Daily trade limit ({max_daily}) reached. Skipping message.")
                msg.ignored = True
                msg.ignore_reason = f"Daily trade limit of {max_daily} reached"
                msg.processed = True
                TelegramMessageRepository.save(session, msg)
                SystemEventRepository.log(session, "warning", "copier", f"Daily trade limit of {max_daily} reached. Order skipped.")
                return

        # 2. Parse using deterministic + Gemini
        min_confidence = float(SettingsService.get(session, "min_llm_confidence") or 0.80)
        gemini_key = SettingsService.get(session, "gemini_api_key")
        gemini_model = SettingsService.get(session, "gemini_model")
        
        try:
            parsed = await parse_signal(
                msg.raw_text,
                message_db_id=msg.id,
                session=session,
                dynamic_key=gemini_key,
                dynamic_model=gemini_model
            )
        except Exception as e:
            logger.error(f"Failed parsing message {msg.message_id}: {e}")
            msg.processed = True
            TelegramMessageRepository.save(session, msg)
            SystemEventRepository.log(session, "error", "llm", f"Parsing error on msg {msg.message_id}: {e}")
            return

        # Check if it was classified as non-signal
        if not parsed.is_signal:
            logger.info(f"Message {msg.message_id} classified as non-signal. Ignored.")
            msg.ignored = True
            msg.ignore_reason = parsed.ignore_reason or "Classified as non-signal"
            msg.processed = True
            TelegramMessageRepository.save(session, msg)
            return

        # Check confidence
        if parsed.confidence < min_confidence:
            logger.warning(f"Parsed signal confidence {parsed.confidence} is below threshold {min_confidence}.")
            msg.ignored = True
            msg.ignore_reason = f"Low parser confidence: {parsed.confidence:.2f} < {min_confidence:.2f}"
            msg.processed = True
            TelegramMessageRepository.save(session, msg)
            SystemEventRepository.log(session, "warning", "llm", f"Ignored signal due to low confidence: {parsed.confidence:.2f}")
            return

        # 3. Resolve Broker Symbol
        symbol_raw = parsed.symbol_raw
        if not symbol_raw:
            logger.error("Parsed signal contains no symbol raw.")
            self._save_failed_attempt(session, msg.id, parsed, "No symbol raw extracted", "validation_failed")
            msg.processed = True
            TelegramMessageRepository.save(session, msg)
            return
            
        broker_symbol, sym_conf = symbol_resolver.resolve(symbol_raw)
        if sym_conf < 0.5 or not broker_symbol:
            error_msg = f"Failed to resolve broker symbol for {symbol_raw} (confidence: {sym_conf})"
            logger.warning(error_msg)
            self._save_failed_attempt(session, msg.id, parsed, error_msg, "validation_failed")
            msg.processed = True
            TelegramMessageRepository.save(session, msg)
            SystemEventRepository.log(session, "error", "copier", error_msg)
            return

        # 4. Validate SL/TP rules
        sl = parsed.stop_loss
        tp = parsed.final_take_profit
        allow_no_sl = SettingsService.get(session, "allow_no_sl")
        
        # Verify SL exists if required
        if not sl and not allow_no_sl:
            error_msg = "Stop Loss is missing and allow_no_sl is disabled."
            self._save_failed_attempt(session, msg.id, parsed, error_msg, "validation_failed", broker_symbol)
            msg.processed = True
            TelegramMessageRepository.save(session, msg)
            SystemEventRepository.log(session, "error", "copier", f"Validation failed for {symbol_raw}: {error_msg}")
            return

        # Get current tick for validations
        tick = mt5_client.get_tick(broker_symbol)
        if not tick:
            error_msg = f"Failed to get current tick for resolved symbol {broker_symbol}."
            self._save_failed_attempt(session, msg.id, parsed, error_msg, "validation_failed", broker_symbol)
            msg.processed = True
            TelegramMessageRepository.save(session, msg)
            SystemEventRepository.log(session, "error", "mt5", error_msg)
            return

        # Determine reference entry price
        ref_price = parsed.entry_price or (tick["ask"] if parsed.side == "buy" else tick["bid"])
        
        # Validate spread limit
        max_spread = SettingsService.get(session, "max_spread_points")
        if max_spread and max_spread > 0:
            sym_info = mt5_client.get_symbol_info(broker_symbol)
            spread = tick["ask"] - tick["bid"]
            point = sym_info.get("point") if sym_info else 0.00001
            spread_points = int(round(spread / point)) if point > 0 else 0
            if spread_points > max_spread:
                error_msg = f"Spread {spread_points} points exceeds limit {max_spread} points."
                self._save_failed_attempt(session, msg.id, parsed, error_msg, "validation_failed", broker_symbol)
                msg.processed = True
                TelegramMessageRepository.save(session, msg)
                SystemEventRepository.log(session, "warning", "trading", f"Skipped trade: {error_msg}")
                return

        # Validate SL direction
        if sl:
            if parsed.side == "buy" and sl >= ref_price:
                error_msg = f"Buy SL {sl} must be below entry price {ref_price}."
                self._save_failed_attempt(session, msg.id, parsed, error_msg, "validation_failed", broker_symbol)
                msg.processed = True
                TelegramMessageRepository.save(session, msg)
                return
            elif parsed.side == "sell" and sl <= ref_price:
                error_msg = f"Sell SL {sl} must be above entry price {ref_price}."
                self._save_failed_attempt(session, msg.id, parsed, error_msg, "validation_failed", broker_symbol)
                msg.processed = True
                TelegramMessageRepository.save(session, msg)
                return

        # Validate TP direction
        if tp:
            if parsed.side == "buy" and tp <= ref_price:
                error_msg = f"Buy TP {tp} must be above entry price {ref_price}."
                self._save_failed_attempt(session, msg.id, parsed, error_msg, "validation_failed", broker_symbol)
                msg.processed = True
                TelegramMessageRepository.save(session, msg)
                return
            elif parsed.side == "sell" and tp >= ref_price:
                error_msg = f"Sell TP {tp} must be below entry price {ref_price}."
                self._save_failed_attempt(session, msg.id, parsed, error_msg, "validation_failed", broker_symbol)
                msg.processed = True
                TelegramMessageRepository.save(session, msg)
                return

        # 5. Calculate Lot Size
        risk_mode = SettingsService.get(session, "risk_mode")
        fixed_lot = float(SettingsService.get(session, "fixed_lot") or 0.01)
        lot_source = "dynamic risk sizing"
        if risk_mode == "fixed_lot":
            fixed_lot, lot_source = fixed_lot_for_signal(
                symbol_raw=symbol_raw,
                broker_symbol=broker_symbol,
                default_lot=fixed_lot,
                symbol_lots=SettingsService.get(session, "symbol_lots"),
            )
            logger.info(
                f"Fixed lot selected for {symbol_raw} -> {broker_symbol}: {fixed_lot:g} ({lot_source})."
            )
        risk_pct = float(SettingsService.get(session, "risk_percent") or 1.0)
        risk_usd = float(SettingsService.get(session, "risk_usd_cap") or 10.0)
        use_equity = SettingsService.get(session, "use_equity_instead_of_balance")
        allow_min_lot = SettingsService.get(session, "allow_min_lot_if_risk_too_small")
        max_lot = SettingsService.get(session, "max_lot")
        
        try:
            lot, lot_warning = RiskCalculator.calculate_lot(
                symbol=broker_symbol,
                side=parsed.side,
                entry_price=ref_price,
                stop_loss=sl or 0.0,
                risk_mode=risk_mode,
                fixed_lot=fixed_lot,
                risk_percent=risk_pct,
                risk_usd_cap=risk_usd,
                use_equity_instead_of_balance=use_equity,
                allow_min_lot_if_risk_too_small=allow_min_lot,
                max_lot_limit=max_lot
            )
            
            if lot <= 0:
                error_msg = "Calculated lot size is 0 (below broker limits and minimum lot execution disabled)."
                self._save_failed_attempt(session, msg.id, parsed, error_msg, "validation_failed", broker_symbol)
                msg.processed = True
                TelegramMessageRepository.save(session, msg)
                return
                
        except Exception as lot_err:
            error_msg = f"Lot calculation error: {lot_err}"
            self._save_failed_attempt(session, msg.id, parsed, error_msg, "validation_failed", broker_symbol)
            msg.processed = True
            TelegramMessageRepository.save(session, msg)
            SystemEventRepository.log(session, "error", "risk", error_msg)
            return

        # 6. Build MT5 Request
        import json
        try:
            req_dict = OrderBuilder.build_request(
                symbol=broker_symbol,
                side=parsed.side,
                order_type=parsed.order_type,
                lot=lot,
                entry_price=parsed.entry_price,
                stop_loss=sl,
                take_profit=tp,
                pending_type=parsed.pending_type,
                comment=f"TG msg {msg.message_id}"
            )
        except Exception as req_err:
            error_msg = f"Failed to build MT5 request: {req_err}"
            self._save_failed_attempt(session, msg.id, parsed, error_msg, "validation_failed", broker_symbol)
            msg.processed = True
            TelegramMessageRepository.save(session, msg)
            return

        # Create tentative OrderAttempt record
        attempt = OrderAttempt(
            telegram_message_db_id=msg.id,
            symbol_raw=symbol_raw,
            broker_symbol=broker_symbol,
            side=parsed.side,
            order_type=parsed.order_type,
            pending_type=parsed.pending_type,
            entry_price=parsed.entry_price or ref_price,
            stop_loss=sl,
            take_profits_json=json.dumps(parsed.take_profits),
            final_take_profit=tp,
            break_even_trigger_tp=parsed.break_even_trigger_tp,
            lot=lot,
            risk_mode=risk_mode,
            risk_amount=risk_usd if risk_mode == "risk_usd_cap" else (risk_pct if risk_mode == "risk_percent" else fixed_lot),
            status="pending_validation",
            mt5_request_json=json.dumps(req_dict)
        )
        OrderAttemptRepository.save(session, attempt)

        # 7. Pre-check trade margin (order_check)
        check_ok, check_result, check_err = mt5_client.check_order(req_dict)
        if not check_ok:
            attempt.status = "order_check_failed"
            attempt.error = check_err or "order_check rejected by broker"
            attempt.mt5_result_json = json.dumps(check_result) if check_result else None
            OrderAttemptRepository.save(session, attempt)
            
            msg.processed = True
            TelegramMessageRepository.save(session, msg)
            SystemEventRepository.log(session, "error", "trading", f"Order check failed for {broker_symbol}: {attempt.error}")
            return

        # 8. Submit Order to MT5 (order_send)
        send_ok, send_result, send_err = mt5_client.send_order(req_dict)
        if not send_ok:
            attempt.status = "send_failed"
            attempt.error = send_err or "order_send failed to execute"
            attempt.mt5_result_json = json.dumps(send_result) if send_result else None
            OrderAttemptRepository.save(session, attempt)
            
            msg.processed = True
            TelegramMessageRepository.save(session, msg)
            SystemEventRepository.log(session, "error", "trading", f"Order execution failed for {broker_symbol}: {attempt.error}")
            return

        # 9. Placed successfully!
        attempt.status = "placed"
        attempt.mt5_result_json = json.dumps(send_result)
        OrderAttemptRepository.save(session, attempt)

        # Get Ticket Number
        ticket = send_result.get("order") or send_result.get("position")
        if ticket:
            # Create ManagedTrade to track break-even triggers
            mt = ManagedTrade(
                order_attempt_id=attempt.id,
                mt5_ticket=ticket,
                position_identifier=ticket,
                symbol_raw=symbol_raw,
                broker_symbol=broker_symbol,
                side=parsed.side,
                lot=lot,
                entry_price=send_result.get("price") or ref_price,
                stop_loss_original=sl or 0.0,
                stop_loss_current=sl or 0.0,
                final_take_profit=tp or 0.0,
                break_even_trigger_tp=parsed.break_even_trigger_tp,
                break_even_enabled=bool(SettingsService.get(session, "move_to_break_even_enabled")),
                break_even_done=False,
                status="active"
            )
            ManagedTradeRepository.save(session, mt)
            
            msg_warn = f" (Warning: {lot_warning})" if lot_warning else ""
            success_msg = f"Successfully placed {parsed.side} trade on {broker_symbol}. Ticket: {ticket}, Volume: {lot}{msg_warn}"
            orders_logger.info(success_msg)
            SystemEventRepository.log(session, "success", "trading", success_msg)
        else:
            orders_logger.warning("Order placed successfully but ticket number could not be retrieved from MT5 result.")

        # Mark message as processed
        msg.processed = True
        TelegramMessageRepository.save(session, msg)

    def _save_failed_attempt(self, session: Session, message_db_id: int, parsed: Any, error_msg: str, status: str, broker_symbol: Optional[str] = None):
        """Helper to log validation/order failures."""
        import json
        attempt = OrderAttempt(
            telegram_message_db_id=message_db_id,
            symbol_raw=parsed.symbol_raw or "UNKNOWN",
            broker_symbol=broker_symbol,
            side=parsed.side or "UNKNOWN",
            order_type=parsed.order_type or "market",
            pending_type=parsed.pending_type,
            entry_price=parsed.entry_price,
            stop_loss=parsed.stop_loss,
            take_profits_json=json.dumps(parsed.take_profits),
            final_take_profit=parsed.final_take_profit,
            break_even_trigger_tp=parsed.break_even_trigger_tp,
            lot=0.0,
            risk_mode="unknown",
            risk_amount=0.0,
            status=status,
            error=error_msg
        )
        OrderAttemptRepository.save(session, attempt)

# Global orchestrator instance
copier_service = CopierService()
