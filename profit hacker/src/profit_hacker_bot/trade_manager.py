from __future__ import annotations

import logging
import math
from datetime import datetime, timezone

from .config import Settings
from .models import (
    BrokerOrderResult,
    Direction,
    EntryType,
    OrderPlan,
    Signal,
    TradeRecord,
    VolumeConstraints,
)
from .mt5_client import BrokerError, MT5Client
from .storage import Storage

logger = logging.getLogger(__name__)


class TradeManager:
    def __init__(self, settings: Settings, storage: Storage, broker: MT5Client) -> None:
        self.settings = settings
        self.storage = storage
        self.broker = broker

    def handle_signal(self, signal: Signal) -> None:
        if self.storage.has_message(signal.source_id, signal.message_id):
            logger.info("Message %s already handled.", signal.key)
            return

        self.storage.record_message(
            signal.source_id,
            signal.message_id,
            status="accepted",
            raw_text=signal.raw_text,
        )

        age_limit = (
            self.settings.rescan_max_age_seconds
            if signal.recovered
            else self.settings.max_signal_age_seconds
        )
        if age_limit > 0 and signal.age_seconds() > age_limit:
            self.storage.record_message(
                signal.source_id,
                signal.message_id,
                status="ignored",
                reason=f"stale before order placement ({age_limit}s limit)",
                raw_text=signal.raw_text,
            )
            return

        comment_prefix = self._comment_prefix(signal)

        if self.settings.dry_run and not self.broker.connected:
            broker_symbol = self.settings.resolve_symbol(signal.symbol)
            logger.info(
                "[DRY RUN] %s%s %s %s SL=%s TP=%s",
                signal.symbol,
                f" -> {broker_symbol}" if broker_symbol != signal.symbol else "",
                signal.direction.value,
                signal.entry_type.value,
                signal.stop_loss,
                ", ".join(str(tp) for tp in signal.take_profits),
            )
            return

        try:
            broker_symbol = self.broker.resolve_broker_symbol(signal.symbol)
            entry_type, entry_price = self.broker.resolve_entry(
                symbol=broker_symbol,
                direction=signal.direction,
                entry_type=signal.entry_type,
                entry_price=signal.entry_price,
            )
            self._validate_active_geometry(signal, entry_price)
            self._reject_late_market_entry(
                signal=signal,
                broker_symbol=broker_symbol,
                entry_price=entry_price,
            )
            self.broker.validate_pending_entry(
                symbol=broker_symbol,
                direction=signal.direction,
                entry_type=entry_type,
                entry_price=entry_price,
            )
            volume = self.broker.calculate_volume(
                symbol=broker_symbol,
                entry_price=entry_price,
                stop_loss=signal.stop_loss,
            )
            constraints = self.broker.volume_constraints(broker_symbol)
            plans = self._build_order_plans(
                signal=signal,
                broker_symbol=broker_symbol,
                entry_type=entry_type,
                entry_price=entry_price,
                total_volume=volume.total_volume,
                constraints=constraints,
                comment_prefix=comment_prefix,
            )

            logger.info(
                "Signal %s risk %.2f%%: raw lots %.4f, sending %.4f lots%s.",
                signal.key,
                self.settings.risk_percent,
                volume.raw_volume,
                volume.total_volume,
                " (broker minimum)" if volume.used_minimum_lot else "",
            )

            if self.settings.dry_run:
                for plan in plans:
                    logger.info(
                        "[DRY RUN] Would place %s %s %.4f lots on %s, entry=%s, SL=%s, TP=%s",
                        plan.direction.value,
                        plan.entry_type.value,
                        plan.volume,
                        plan.symbol,
                        plan.entry_price or "market",
                        plan.stop_loss,
                        plan.take_profit,
                    )
                return

            results = [self.broker.place_order(plan) for plan in plans]
            status = "active" if entry_type is EntryType.MARKET else "pending"
            self.storage.record_trade(
                signal,
                broker_symbol=broker_symbol,
                entry_price=entry_price,
                take_profit=signal.final_tp,
                break_even_trigger=signal.first_tp,
                comment_prefix=comment_prefix,
                order_results=results,
                status=status,
            )
            logger.info("Placed %s MT5 order(s) for signal %s.", len(results), signal.key)

        except BrokerError as exc:
            logger.warning("Ignored signal %s: %s", signal.key, exc)
            self.storage.record_message(
                signal.source_id,
                signal.message_id,
                status="ignored",
                reason=str(exc),
                raw_text=signal.raw_text,
            )

    def _validate_active_geometry(self, signal: Signal, entry_price: float) -> None:
        stop = float(signal.stop_loss)
        first_tp = float(signal.first_tp)
        if signal.direction.is_buy:
            if entry_price <= stop:
                raise BrokerError(
                    f"Signal is no longer active: BUY price {entry_price:g} reached/passed SL {stop:g}."
                )
            if entry_price >= first_tp:
                raise BrokerError(
                    f"Signal is no longer active: BUY price {entry_price:g} reached/passed TP1 {first_tp:g}."
                )
            invalid_targets = [value for value in signal.take_profits if value <= entry_price]
        else:
            if entry_price >= stop:
                raise BrokerError(
                    f"Signal is no longer active: SELL price {entry_price:g} reached/passed SL {stop:g}."
                )
            if entry_price <= first_tp:
                raise BrokerError(
                    f"Signal is no longer active: SELL price {entry_price:g} reached/passed TP1 {first_tp:g}."
                )
            invalid_targets = [value for value in signal.take_profits if value >= entry_price]
        if invalid_targets:
            raise BrokerError(
                "Signal contains TP level(s) on the wrong side of current/entry price: "
                + ", ".join(f"{value:g}" for value in invalid_targets)
            )

    def _build_order_plans(
        self,
        *,
        signal: Signal,
        broker_symbol: str,
        entry_type: EntryType,
        entry_price: float,
        total_volume: float,
        constraints: VolumeConstraints,
        comment_prefix: str,
    ) -> list[OrderPlan]:
        tp_levels = list(signal.take_profits)
        if self.settings.order_mode == "split" and len(tp_levels) > 1:
            parts = self._split_volume(total_volume, len(tp_levels), constraints)
            if parts:
                return [
                    OrderPlan(
                        symbol=broker_symbol,
                        direction=signal.direction,
                        entry_type=entry_type,
                        volume=part,
                        stop_loss=signal.stop_loss,
                        take_profit=tp,
                        break_even_trigger=signal.first_tp,
                        entry_price=None if entry_type is EntryType.MARKET else entry_price,
                        comment=f"{comment_prefix}:{index}",
                    )
                    for index, (part, tp) in enumerate(zip(parts, tp_levels), start=1)
                ]
            logger.info(
                "Total volume %.4f cannot be split across %s TP levels with min lot %.4f. Using single order.",
                total_volume,
                len(tp_levels),
                constraints.minimum,
            )

        return [
            OrderPlan(
                symbol=broker_symbol,
                direction=signal.direction,
                entry_type=entry_type,
                volume=total_volume,
                stop_loss=signal.stop_loss,
                take_profit=signal.final_tp,
                break_even_trigger=signal.first_tp,
                entry_price=None if entry_type is EntryType.MARKET else entry_price,
                comment=f"{comment_prefix}:1",
            )
        ]

    def _split_volume(
        self,
        total_volume: float,
        count: int,
        constraints: VolumeConstraints,
    ) -> list[float]:
        minimum_needed = constraints.minimum * count
        if total_volume + 1e-12 < minimum_needed:
            return []

        base = self._floor_to_step(total_volume / count, constraints.step)
        if base + 1e-12 < constraints.minimum:
            return []

        parts = [base for _ in range(count)]
        used = sum(parts)
        remaining = self._floor_to_step(total_volume - used, constraints.step)
        index = 0
        while remaining + 1e-12 >= constraints.step and index < count:
            parts[index] = self._round_volume(parts[index] + constraints.step, constraints.step)
            remaining = self._round_volume(remaining - constraints.step, constraints.step)
            index += 1
        return [self._round_volume(part, constraints.step) for part in parts]

    def _reject_late_market_entry(
        self,
        *,
        signal: Signal,
        broker_symbol: str,
        entry_price: float,
    ) -> None:
        if signal.entry_type is not EntryType.MARKET:
            return
        if signal.entry_price is None or self.settings.max_entry_drift_points <= 0:
            return

        info = self.broker.ensure_symbol(broker_symbol)
        max_drift = self.settings.max_entry_drift_points * float(info.point)
        if abs(entry_price - signal.entry_price) > max_drift:
            raise BrokerError("Market price drift is above MAX_ENTRY_DRIFT_POINTS.")

    def _comment_prefix(self, signal: Signal) -> str:
        return f"{self.settings.trade_comment_prefix}:{signal.message_id}"

    def _floor_to_step(self, value: float, step: float) -> float:
        if step <= 0:
            return value
        return math.floor(value / step) * step

    def _round_volume(self, value: float, step: float) -> float:
        if step <= 0:
            return value
        decimals = max(0, min(8, len(f"{step:.8f}".rstrip("0").split(".")[-1])))
        return round(value, decimals)


class PositionWatcher:
    def __init__(self, settings: Settings, storage: Storage, broker: MT5Client) -> None:
        self.settings = settings
        self.storage = storage
        self.broker = broker

    async def run_forever(self) -> None:
        import asyncio

        while True:
            try:
                await asyncio.to_thread(self.tick)
            except BrokerError as exc:
                logger.warning("Watcher broker error: %s", exc)
            except Exception:
                logger.exception("Watcher failed.")
            await asyncio.sleep(self.settings.watch_interval_seconds)

    def tick(self) -> None:
        if not self.broker.connected:
            return

        for trade in self.storage.iter_active_trades():
            positions = self.broker.find_positions(
                symbol=trade.symbol,
                comment_prefix=trade.comment_prefix,
            )
            orders = self.broker.find_orders(
                symbol=trade.symbol,
                comment_prefix=trade.comment_prefix,
            )

            if orders and not positions and self._pending_order_expired(trade):
                for order in orders:
                    self.broker.cancel_order(order)
                self.storage.mark_trade_status(trade.id, "expired")
                logger.info("Expired pending order(s) for %s.", trade.signal_key)
                continue

            if positions:
                if trade.status == "pending":
                    self.storage.mark_trade_status(trade.id, "active")
                self._maybe_move_break_even(trade, positions)
                continue

            if not positions and not orders:
                self.storage.mark_trade_status(trade.id, "closed")
                logger.info("Trade %s is closed.", trade.signal_key)

    def _maybe_move_break_even(self, trade: TradeRecord, positions: list[object]) -> None:
        if not self.settings.break_even_enabled:
            return
        if trade.break_even_done:
            return

        watch_price = self.broker.current_break_even_watch_price(trade.symbol, trade.direction)
        reached = (
            watch_price >= trade.break_even_trigger
            if trade.direction is Direction.BUY
            else watch_price <= trade.break_even_trigger
        )
        if not reached:
            return

        for position in positions:
            self.broker.move_position_sl_to_break_even(
                position,
                direction=trade.direction,
                offset_points=self.settings.break_even_offset_points,
            )
        self.storage.mark_break_even_done(trade.id)
        logger.info("Moved SL to break-even for %s.", trade.signal_key)

    def _pending_order_expired(self, trade: TradeRecord) -> bool:
        age = (datetime.now(timezone.utc) - trade.created_at).total_seconds()
        return age > self.settings.pending_order_ttl_seconds
