import asyncio
import json
import traceback
from datetime import datetime
from sqlmodel import Session
from typing import Any, Optional

from app.core.logging import logger, orders_logger
from app.core.signal_hash import signal_content_hash
from app.telegram.poller import TelegramPoller
from app.telegram.browser_poller import browser_telegram_poller
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
from app.db.repositories import OrderAttemptRepository, ManagedTradeRepository, SystemEventRepository, TelegramMessageRepository, TelegramChannelRepository

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

                        daily_breaker = TradeManager.process_daily_pnl_limits(
                            session,
                            win_goal_usd=float(SettingsService.get(session, "daily_win_goal_usd") or 0.0),
                            loss_limit_usd=float(SettingsService.get(session, "daily_loss_limit_usd") or 0.0),
                        )
                        if daily_breaker.get("triggered"):
                            SettingsService.set(session, "copier_enabled", False)
                            logger.warning(
                                "Copier paused after daily P/L breaker: "
                                f"{daily_breaker.get('reason')}"
                            )
                            continue
                        
                        # 2. Poll and process new messages
                        read_mode = (SettingsService.get(session, "telegram_read_mode") or "api").strip().lower()
                        if read_mode == "browser":
                            channels = TelegramChannelRepository.list_enabled(session)
                            new_messages = []
                            for channel in channels:
                                new_messages.extend(
                                    browser_telegram_poller.poll_messages(
                                        session,
                                        chat_link_override=channel.chat_link,
                                        telegram_channel_id=channel.id,
                                    )
                                )
                        else:
                            new_messages = await self._poller.poll_messages(session)
                        if new_messages:
                            logger.info(f"Polled {len(new_messages)} new messages. Processing...")
                        pending_messages = TelegramMessageRepository.get_pending(session, limit=25)
                        messages_to_process = self._merge_message_batches(new_messages, pending_messages)
                        if pending_messages:
                            logger.info(
                                f"Found {len(pending_messages)} saved pending messages. "
                                "Processing backlog..."
                            )
                        for msg in messages_to_process:
                            if msg.ignored:
                                continue
                            try:
                                await self._process_message(session, msg)
                            except Exception as e:
                                self._mark_message_processing_error(session, msg, e)
                                traceback.print_exc()
                        
                        # 3. Process break-even triggers
                        try:
                            be_offset = int(SettingsService.get(session, "break_even_offset_points") or 0)
                            be_enabled = SettingsService.get(session, "move_to_break_even_enabled")
                            if be_enabled:
                                TradeManager.process_break_even(session, dynamic_offset_points=be_offset)
                            daily_breaker = TradeManager.process_daily_pnl_limits(
                                session,
                                win_goal_usd=float(SettingsService.get(session, "daily_win_goal_usd") or 0.0),
                                loss_limit_usd=float(SettingsService.get(session, "daily_loss_limit_usd") or 0.0),
                            )
                            if daily_breaker.get("triggered"):
                                SettingsService.set(session, "copier_enabled", False)
                                logger.warning(
                                    "Copier paused after daily P/L breaker: "
                                    f"{daily_breaker.get('reason')}"
                                )
                        except Exception as e:
                            logger.error(f"Error in break-even trade manager: {e}")
                    else:
                        logger.debug("Copier is disabled. Skipping cycle.")
                        
            except Exception as e:
                logger.error(f"Exception in copier orchestration loop: {e}", exc_info=True)
                
            await asyncio.sleep(max(1, poll_interval))

    @staticmethod
    def _merge_message_batches(*batches: list[TelegramMessage]) -> list[TelegramMessage]:
        merged: list[TelegramMessage] = []
        seen: set[int] = set()
        for batch in batches:
            for msg in batch:
                if msg.id is None or msg.id in seen:
                    continue
                seen.add(msg.id)
                merged.append(msg)
        return merged

    @staticmethod
    def _mark_message_processing_error(session: Session, msg: TelegramMessage, exc: Exception):
        error_msg = f"Processing exception: {exc}"
        logger.error(f"Error processing message {msg.id}: {exc}")
        msg.ignored = True
        msg.ignore_reason = error_msg[:500]
        msg.processed = True
        TelegramMessageRepository.save(session, msg)
        SystemEventRepository.log(
            session,
            "error",
            "copier",
            f"Message {msg.message_id} failed during processing and was marked ignored: {exc}",
        )

    async def _process_message(self, session: Session, msg: TelegramMessage, force_stale_bypass: bool = False):
        """Pipeline processing a single Telegram message into a trade order."""
        logger.info(f"Processing message {msg.message_id} from chat {msg.chat_id}")
        signal_hash = signal_content_hash(msg.raw_text)
        channel = TelegramChannelRepository.get(session, msg.telegram_channel_id) if msg.telegram_channel_id else None
        channel_attr = (channel.attr if channel else "Telegram").strip() or "Telegram"

        duplicate_attempt = OrderAttemptRepository.get_placed_by_signal_hash(session, signal_hash)
        if duplicate_attempt:
            reason = (
                f"Duplicate signal content already placed as order attempt "
                f"{duplicate_attempt.id} on {duplicate_attempt.broker_symbol or duplicate_attempt.symbol_raw}."
            )
            logger.warning(f"Skipping message {msg.message_id}: {reason}")
            msg.ignored = True
            msg.ignore_reason = reason
            msg.processed = True
            TelegramMessageRepository.save(session, msg)
            SystemEventRepository.log(
                session,
                "warning",
                "copier",
                f"Skipped duplicate Telegram signal message {msg.message_id}.",
                {"signal_hash": signal_hash, "existing_order_attempt_id": duplicate_attempt.id},
            )
            return
        
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
        effective_take_profits = list(parsed.take_profits or [])
        effective_break_even_tp = parsed.break_even_trigger_tp
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

        sym_info = mt5_client.get_symbol_info(broker_symbol)
        stale_error = self._validate_stale_signal(
            session,
            msg,
            parsed,
            tick,
            sym_info,
            force_bypass=force_stale_bypass,
        )
        if stale_error:
            self._save_failed_attempt(session, msg.id, parsed, stale_error, "validation_failed", broker_symbol)
            msg.ignored = True
            msg.ignore_reason = stale_error
            msg.processed = True
            TelegramMessageRepository.save(session, msg)
            SystemEventRepository.log(session, "warning", "copier", f"Skipped stale signal: {stale_error}")
            return

        # Determine reference entry price
        ref_price = parsed.entry_price or (tick["ask"] if parsed.side == "buy" else tick["bid"])

        rr_override_enabled = bool(SettingsService.get(session, "rr_override_enabled"))
        target_rr = float(SettingsService.get(session, "target_rr") or 1.0)
        if rr_override_enabled:
            if not sl:
                error_msg = "RR override is enabled, but signal has no Stop Loss to calculate risk distance."
                self._save_failed_attempt(session, msg.id, parsed, error_msg, "validation_failed", broker_symbol)
                msg.processed = True
                TelegramMessageRepository.save(session, msg)
                SystemEventRepository.log(session, "error", "copier", f"Validation failed for {symbol_raw}: {error_msg}")
                return
            effective_take_profits = self._build_rr_take_profit_ladder(
                side=parsed.side,
                entry_price=ref_price,
                stop_loss=sl,
                target_rr=target_rr,
                symbol_info=sym_info,
            )
            tp = effective_take_profits[-1] if effective_take_profits else None
            effective_break_even_tp = effective_take_profits[0] if effective_take_profits else None
            parsed.parser_notes.append(
                f"Signal TPs overridden by user RR target 1:{target_rr:g}; effective TPs: {effective_take_profits}."
            )
            logger.info(
                f"RR override active for {symbol_raw}: entry={ref_price}, SL={sl}, "
                f"target_rr={target_rr:g}, effective_tps={effective_take_profits}"
            )
        
        # Validate spread limit
        max_spread = SettingsService.get(session, "max_spread_points")
        if max_spread and max_spread > 0:
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

        split_enabled = bool(SettingsService.get(session, "split_legs_enabled"))
        split_max_count = int(SettingsService.get(session, "split_legs_max_count") or 0)
        be_trigger_level = int(SettingsService.get(session, "break_even_trigger_tp_level") or 1)
        if effective_take_profits:
            effective_break_even_tp = self._break_even_trigger_from_level(
                effective_take_profits,
                be_trigger_level,
                effective_break_even_tp,
            )

        if split_enabled:
            leg_take_profits = self._split_leg_targets(effective_take_profits, split_max_count)
            if not leg_take_profits:
                error_msg = "Split legs are enabled, but the signal has no usable take-profit targets."
                self._save_failed_attempt(session, msg.id, parsed, error_msg, "validation_failed", broker_symbol)
                msg.processed = True
                TelegramMessageRepository.save(session, msg)
                return
        else:
            leg_take_profits = [tp]

        # 5. Calculate per-leg lot/risk settings
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

        leg_count = len(leg_take_profits)
        leg_fixed_lot, leg_risk_pct, leg_risk_usd = self._risk_inputs_for_leg(
            risk_mode,
            fixed_lot,
            risk_pct,
            risk_usd,
            leg_count if split_enabled else 1,
        )
        placed_count = 0

        for leg_index, leg_tp in enumerate(leg_take_profits, start=1):
            try:
                lot, lot_warning = RiskCalculator.calculate_lot(
                    symbol=broker_symbol,
                    side=parsed.side,
                    entry_price=ref_price,
                    stop_loss=sl or 0.0,
                    risk_mode=risk_mode,
                    fixed_lot=leg_fixed_lot,
                    risk_percent=leg_risk_pct,
                    risk_usd_cap=leg_risk_usd,
                    use_equity_instead_of_balance=use_equity,
                    allow_min_lot_if_risk_too_small=allow_min_lot,
                    max_lot_limit=max_lot
                )

                if lot <= 0:
                    error_msg = lot_warning or "Calculated lot size is 0 (below broker limits and minimum lot execution disabled)."
                    self._save_failed_attempt(session, msg.id, parsed, error_msg, "validation_failed", broker_symbol)
                    if not split_enabled:
                        msg.processed = True
                        TelegramMessageRepository.save(session, msg)
                        return
                    continue

                leg_risk_cap = None
                if risk_mode == "risk_usd_cap":
                    leg_risk_cap = leg_risk_usd
                elif risk_mode == "risk_percent":
                    account_info = mt5_client.get_account_info() or {}
                    account_value = (
                        account_info.get("equity")
                        if use_equity
                        else account_info.get("balance")
                    ) or 0.0
                    leg_risk_cap = float(account_value) * (leg_risk_pct / 100.0)

                actual_leg_risk = None
                if risk_mode in {"risk_percent", "risk_usd_cap"} and sl:
                    actual_leg_risk = RiskCalculator.estimate_loss(
                        symbol=broker_symbol,
                        side=parsed.side,
                        entry_price=ref_price,
                        stop_loss=sl,
                        lot=lot,
                    )
                    if (
                        leg_risk_cap is not None
                        and actual_leg_risk is not None
                        and actual_leg_risk > leg_risk_cap + 0.01
                    ):
                        error_msg = (
                            f"Calculated lot {lot:g} would risk {actual_leg_risk:.2f}, "
                            f"above per-leg cap {leg_risk_cap:.2f}; skipped."
                        )
                        self._save_failed_attempt(session, msg.id, parsed, error_msg, "validation_failed", broker_symbol)
                        SystemEventRepository.log(session, "error", "risk", error_msg)
                        if not split_enabled:
                            msg.processed = True
                            TelegramMessageRepository.save(session, msg)
                            return
                        continue

            except Exception as lot_err:
                error_msg = f"Lot calculation error: {lot_err}"
                self._save_failed_attempt(session, msg.id, parsed, error_msg, "validation_failed", broker_symbol)
                SystemEventRepository.log(session, "error", "risk", error_msg)
                if not split_enabled:
                    msg.processed = True
                    TelegramMessageRepository.save(session, msg)
                    return
                continue

            leg_suffix = f" L{leg_index}/{leg_count}" if split_enabled else ""
            try:
                req_dict = OrderBuilder.build_request(
                    symbol=broker_symbol,
                    side=parsed.side,
                    order_type=parsed.order_type,
                    lot=lot,
                    entry_price=parsed.entry_price,
                    stop_loss=sl,
                    take_profit=leg_tp,
                    pending_type=parsed.pending_type,
                    comment=f"Trade {channel_attr}{leg_suffix}"[:31]
                )
            except Exception as req_err:
                error_msg = f"Failed to build MT5 request: {req_err}"
                self._save_failed_attempt(session, msg.id, parsed, error_msg, "validation_failed", broker_symbol)
                if not split_enabled:
                    msg.processed = True
                    TelegramMessageRepository.save(session, msg)
                    return
                continue

            leg_tp_ladder = effective_take_profits[:leg_index] if split_enabled else effective_take_profits
            attempt = OrderAttempt(
                telegram_message_db_id=msg.id,
                signal_hash=signal_hash,
                symbol_raw=symbol_raw,
                broker_symbol=broker_symbol,
                side=parsed.side,
                order_type=parsed.order_type,
                pending_type=parsed.pending_type,
                entry_price=parsed.entry_price or ref_price,
                stop_loss=sl,
                take_profits_json=json.dumps(leg_tp_ladder),
                final_take_profit=leg_tp,
                break_even_trigger_tp=effective_break_even_tp,
                lot=lot,
                risk_mode=risk_mode,
                risk_amount=(
                    actual_leg_risk
                    if actual_leg_risk is not None
                    else (leg_risk_usd if risk_mode == "risk_usd_cap" else (leg_risk_pct if risk_mode == "risk_percent" else leg_fixed_lot))
                ),
                status="pending_validation",
                mt5_request_json=json.dumps(req_dict)
            )
            OrderAttemptRepository.save(session, attempt)

            check_ok, check_result, check_err = mt5_client.check_order(req_dict)
            if not check_ok:
                attempt.status = "order_check_failed"
                attempt.error = check_err or "order_check rejected by broker"
                attempt.mt5_result_json = json.dumps(check_result) if check_result else None
                OrderAttemptRepository.save(session, attempt)
                SystemEventRepository.log(session, "error", "trading", f"Order check failed for {broker_symbol} leg {leg_index}: {attempt.error}")
                if not split_enabled:
                    msg.processed = True
                    TelegramMessageRepository.save(session, msg)
                    return
                continue

            send_ok, send_result, send_err = mt5_client.send_order(req_dict)
            if not send_ok:
                attempt.status = "send_failed"
                attempt.error = send_err or "order_send failed to execute"
                attempt.mt5_result_json = json.dumps(send_result) if send_result else None
                OrderAttemptRepository.save(session, attempt)
                SystemEventRepository.log(session, "error", "trading", f"Order execution failed for {broker_symbol} leg {leg_index}: {attempt.error}")
                if not split_enabled:
                    msg.processed = True
                    TelegramMessageRepository.save(session, msg)
                    return
                continue

            attempt.status = "placed"
            attempt.mt5_result_json = json.dumps(send_result)
            OrderAttemptRepository.save(session, attempt)
            placed_count += 1

            ticket = send_result.get("order") or send_result.get("position")
            if ticket:
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
                    take_profits_json=json.dumps(leg_tp_ladder),
                    final_take_profit=leg_tp or 0.0,
                    break_even_trigger_tp=effective_break_even_tp,
                    break_even_enabled=bool(SettingsService.get(session, "move_to_break_even_enabled")),
                    break_even_done=False,
                    tp2_partial_done=False,
                    status="active"
                )
                ManagedTradeRepository.save(session, mt)

                msg_warn = f" (Warning: {lot_warning})" if lot_warning else ""
                success_msg = (
                    f"Successfully placed {parsed.side} trade on {broker_symbol} "
                    f"leg {leg_index}/{leg_count}. Ticket: {ticket}, TP: {leg_tp}, Volume: {lot}{msg_warn}"
                )
                orders_logger.info(success_msg)
                SystemEventRepository.log(session, "success", "trading", success_msg)
            else:
                orders_logger.warning("Order placed successfully but ticket number could not be retrieved from MT5 result.")

        if split_enabled:
            orders_logger.info(
                f"Split legs complete for message {msg.message_id}: placed {placed_count}/{leg_count} legs."
            )

        # Mark message as processed
        msg.processed = True
        TelegramMessageRepository.save(session, msg)

    @staticmethod
    def _split_leg_targets(take_profits: list[float], max_count: int | None = 0) -> list[float]:
        targets = [float(tp) for tp in (take_profits or []) if tp is not None]
        limit = max(int(max_count or 0), 0)
        if limit > 0:
            return targets[:limit]
        return targets

    @staticmethod
    def _break_even_trigger_from_level(
        take_profits: list[float],
        level: int | None,
        fallback: Optional[float] = None,
    ) -> Optional[float]:
        targets = [float(tp) for tp in (take_profits or []) if tp is not None]
        if not targets:
            return fallback
        target_index = max(int(level or 1), 1) - 1
        target_index = min(target_index, len(targets) - 1)
        return targets[target_index]

    @staticmethod
    def _risk_inputs_for_leg(
        risk_mode: str,
        fixed_lot: float,
        risk_percent: float,
        risk_usd_cap: float,
        leg_count: int,
    ) -> tuple[float, float, float]:
        divisor = max(int(leg_count or 1), 1)
        if risk_mode == "fixed_lot":
            return fixed_lot / divisor, risk_percent, risk_usd_cap
        if risk_mode == "risk_percent":
            return fixed_lot, risk_percent / divisor, risk_usd_cap
        if risk_mode == "risk_usd_cap":
            return fixed_lot, risk_percent, risk_usd_cap / divisor
        return fixed_lot, risk_percent, risk_usd_cap

    @staticmethod
    def _build_rr_take_profit_ladder(
        side: str,
        entry_price: float,
        stop_loss: float,
        target_rr: float,
        symbol_info: Optional[dict] = None,
    ) -> list[float]:
        target_rr = max(float(target_rr or 0), 0.1)
        risk_distance = abs(float(entry_price) - float(stop_loss))
        if risk_distance <= 0:
            raise ValueError("Entry price and Stop Loss cannot be equal for RR override.")

        digits = int((symbol_info or {}).get("digits") or 5)
        rr_steps: list[float] = []
        whole_steps = int(target_rr)
        rr_steps.extend(float(step) for step in range(1, whole_steps + 1))
        if not rr_steps or abs(target_rr - rr_steps[-1]) > 1e-9:
            rr_steps.append(target_rr)

        tps: list[float] = []
        for rr in rr_steps:
            if side == "buy":
                tp = float(entry_price) + (risk_distance * rr)
            else:
                tp = float(entry_price) - (risk_distance * rr)
            rounded_tp = round(tp, digits)
            if rounded_tp not in tps:
                tps.append(rounded_tp)
        return tps

    def _save_failed_attempt(self, session: Session, message_db_id: int, parsed: Any, error_msg: str, status: str, broker_symbol: Optional[str] = None):
        """Helper to log validation/order failures."""
        import json
        message = session.get(TelegramMessage, message_db_id)
        attempt = OrderAttempt(
            telegram_message_db_id=message_db_id,
            signal_hash=signal_content_hash(message.raw_text if message else None),
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

    def _validate_stale_signal(
        self,
        session: Session,
        msg: TelegramMessage,
        parsed: Any,
        tick: dict,
        sym_info: Optional[dict],
        force_bypass: bool = False,
    ) -> Optional[str]:
        if force_bypass:
            return None

        if self._is_explicit_pending_order(parsed):
            return None

        max_age_minutes = int(SettingsService.get(session, "stale_signal_max_age_minutes") or 0)
        if max_age_minutes <= 0:
            return None

        age_minutes = self._message_age_minutes(msg.message_date)
        if age_minutes <= max_age_minutes:
            return None

        if not parsed.entry_price:
            return (
                f"Signal is {age_minutes:.1f} minutes old and has no explicit entry price; "
                "skipping to avoid chasing an old NOW trade."
            )

        point = float((sym_info or {}).get("point") or 0.00001)
        max_distance_points = int(SettingsService.get(session, "stale_signal_max_entry_distance_points") or 50)
        configured_distance = max_distance_points * point
        risk_distance = abs(float(parsed.entry_price) - float(parsed.stop_loss or parsed.entry_price))
        allowed_distance = max(configured_distance, risk_distance * 0.15)
        current_price = float(tick["ask"] if parsed.side == "buy" else tick["bid"])
        distance = abs(current_price - float(parsed.entry_price))

        if distance > allowed_distance:
            distance_points = distance / point if point > 0 else distance
            allowed_points = allowed_distance / point if point > 0 else allowed_distance
            return (
                f"Signal is {age_minutes:.1f} minutes old and current price {current_price:g} "
                f"is {distance_points:.1f} points from entry {float(parsed.entry_price):g}; "
                f"allowed {allowed_points:.1f} points."
            )

        return None

    @staticmethod
    def _is_explicit_pending_order(parsed: Any) -> bool:
        order_type = str(getattr(parsed, "order_type", "") or "").lower()
        pending_type = str(getattr(parsed, "pending_type", "") or "").lower()
        return (
            order_type == "pending"
            and pending_type in {"buy_limit", "sell_limit", "buy_stop", "sell_stop"}
            and bool(getattr(parsed, "entry_price", None))
        )

    @staticmethod
    def _message_age_minutes(message_date: datetime) -> float:
        if message_date.tzinfo is not None:
            now = datetime.now(message_date.tzinfo)
        else:
            now = datetime.utcnow()
        age_seconds = max(0.0, (now - message_date).total_seconds())
        return age_seconds / 60.0

# Global orchestrator instance
copier_service = CopierService()
