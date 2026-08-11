import time
from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from ..config import Settings
from ..domain.enums import (
    AccountRole,
    AccountState,
    AuditSeverity,
    ExecutionMode,
    JobStatus,
    OrderType,
    TradeAction,
)
from ..domain.messages import ExecutionAck, FollowerCommand, SourceTradeMessage
from ..models import (
    Account,
    AccountSymbolSpec,
    CopyJob,
    ExecutionAcknowledgement,
    SourceTradeEvent,
    SymbolMapping,
    TradeLink,
)
from ..transport.base import FollowerTransport
from .accounts import ensure_system_state
from .audit import record_audit
from .events import EventHub, event_hub
from .risk import RiskCalculator, RiskRejectedError
from .risk_profiles import ensure_default_risk_profile
from .snapshots import DatabaseSnapshotProvider, SnapshotUnavailableError

ENTRY_ACTIONS = {TradeAction.MARKET_OPEN, TradeAction.PENDING_CREATE, TradeAction.REVERSE}
SUCCESS_STATUSES = {JobStatus.FILLED, JobStatus.ACKNOWLEDGED}


class CopierCore:
    def __init__(
        self,
        *,
        settings: Settings,
        transport: FollowerTransport,
        snapshot_provider: DatabaseSnapshotProvider | None = None,
        risk_calculator: RiskCalculator | None = None,
        events: EventHub | None = None,
    ) -> None:
        self.settings = settings
        self.transport = transport
        self.snapshot_provider = snapshot_provider or DatabaseSnapshotProvider()
        self.risk_calculator = risk_calculator or RiskCalculator()
        self.events = events or event_hub

    def _save_source_event(
        self, session: Session, message: SourceTradeMessage
    ) -> tuple[SourceTradeEvent, bool]:
        existing = session.scalar(
            select(SourceTradeEvent)
            .options(selectinload(SourceTradeEvent.jobs))
            .where(SourceTradeEvent.event_uid == str(message.event_uid))
        )
        if existing:
            return existing, False

        event = SourceTradeEvent(
            event_uid=str(message.event_uid),
            source_account_id=str(message.source_account_id),
            sequence=message.sequence,
            source_order_id=message.source_order_id,
            source_position_id=message.source_position_id,
            action=message.action.value,
            side=message.side.value,
            symbol=message.symbol,
            volume=message.volume,
            entry_price=message.entry_price,
            stop_loss=message.stop_loss,
            take_profit=message.take_profit,
            magic_number=message.magic_number,
            comment=message.comment,
            occurred_at=message.occurred_at,
            payload=message.model_dump(mode="json"),
        )
        session.add(event)
        session.commit()
        session.refresh(event)
        return event, True

    @staticmethod
    def _map_prices(
        message: SourceTradeMessage,
        mapping: SymbolMapping | None,
    ) -> tuple[str, Decimal, Decimal | None, Decimal | None]:
        if mapping is None:
            return message.symbol, message.entry_price, message.stop_loss, message.take_profit

        entry = message.entry_price + Decimal(mapping.price_offset)
        if not mapping.preserve_relative_stops:
            stop = (
                message.stop_loss + Decimal(mapping.price_offset)
                if message.stop_loss is not None
                else None
            )
            target = (
                message.take_profit + Decimal(mapping.price_offset)
                if message.take_profit is not None
                else None
            )
            return mapping.follower_symbol, entry, stop, target

        stop = None
        if message.stop_loss is not None:
            stop_distance = abs(message.entry_price - message.stop_loss)
            stop = entry - stop_distance if message.side.value == "buy" else entry + stop_distance
        target = None
        if message.take_profit is not None:
            target_distance = abs(message.take_profit - message.entry_price)
            target = (
                entry + target_distance if message.side.value == "buy" else entry - target_distance
            )
        return mapping.follower_symbol, entry, stop, target

    @staticmethod
    def _source_identity(message: SourceTradeMessage) -> tuple[str, str]:
        if message.action in {TradeAction.PENDING_CREATE, TradeAction.CANCEL}:
            return "pending", message.source_order_id
        if message.action is TradeAction.MODIFY and not message.source_position_id:
            return "pending", message.source_order_id
        return "position", message.source_position_id or message.source_order_id

    @classmethod
    def _find_link(
        cls,
        session: Session,
        master: Account,
        follower: Account,
        message: SourceTradeMessage,
    ) -> TradeLink | None:
        source_type, source_ticket = cls._source_identity(message)
        return session.scalar(
            select(TradeLink).where(
                TradeLink.master_account_id == master.id,
                TradeLink.follower_account_id == follower.id,
                TradeLink.source_type == source_type,
                TradeLink.source_ticket == source_ticket,
                TradeLink.status == "active",
            )
        )

    @staticmethod
    def _floor_to_step(value: Decimal, step: Decimal) -> Decimal:
        return (value // step) * step

    def _lifecycle_volume(
        self,
        session: Session,
        follower: Account,
        message: SourceTradeMessage,
        link: TradeLink,
    ) -> Decimal:
        if message.action is TradeAction.CLOSE:
            return Decimal(link.follower_volume)
        if message.action is not TradeAction.PARTIAL_CLOSE:
            return Decimal(link.follower_volume)
        previous = Decimal(str(message.metadata.get("previous_volume", link.source_volume)))
        if previous <= 0:
            raise RiskRejectedError("The master volume before partial close is unavailable.")
        raw = Decimal(link.follower_volume) * message.volume / previous
        specification = session.scalar(
            select(AccountSymbolSpec).where(
                AccountSymbolSpec.account_id == follower.id,
                AccountSymbolSpec.symbol == link.follower_symbol,
            )
        )
        if specification is None:
            raise SnapshotUnavailableError("Follower volume specification is unavailable.")
        volume = self._floor_to_step(raw, Decimal(specification.volume_step))
        if volume < Decimal(specification.volume_min):
            raise RiskRejectedError(
                "The proportional partial close is below broker minimum volume."
            )
        return min(volume, Decimal(link.follower_volume))

    @staticmethod
    def _rejected_job(
        event: SourceTradeEvent,
        follower: Account,
        *,
        symbol: str,
        reason: str,
    ) -> CopyJob:
        return CopyJob(
            source_event_id=event.id,
            follower_account_id=follower.id,
            status=JobStatus.REJECTED.value,
            follower_symbol=symbol,
            requested_volume=Decimal("0"),
            requested_price=event.entry_price,
            stop_loss=event.stop_loss,
            take_profit=event.take_profit,
            rejection_reason=reason,
        )

    async def process(self, session: Session, message: SourceTradeMessage) -> list[CopyJob]:
        ensure_default_risk_profile(session, actor="copier-core")
        state = ensure_system_state(session)
        if not state.active_master_account_id:
            raise ValueError("No active master account is configured.")
        if str(message.source_account_id) != state.active_master_account_id:
            raise ValueError("Source event did not come from the active master account.")
        master = session.get(Account, state.active_master_account_id)
        if master is None or not master.is_master:
            raise ValueError("The configured master account is unavailable.")

        source_event, created = self._save_source_event(session, message)
        if not created:
            return list(source_event.jobs)

        followers = session.scalars(
            select(Account)
            .options(selectinload(Account.risk_profile))
            .where(
                Account.role == AccountRole.FOLLOWER.value,
                Account.state == AccountState.ACTIVE.value,
                Account.is_master.is_(False),
            )
            .order_by(Account.display_name)
        ).all()
        jobs: list[CopyJob] = []

        for follower in followers:
            profile = follower.risk_profile
            mapping = session.scalar(
                select(SymbolMapping).where(
                    SymbolMapping.follower_account_id == follower.id,
                    SymbolMapping.master_symbol == message.symbol,
                    SymbolMapping.enabled.is_(True),
                )
            )
            symbol, entry, stop, target = self._map_prices(message, mapping)
            rejection = ""
            link = self._find_link(session, master, follower, message)

            if message.action in ENTRY_ACTIONS and link is not None:
                rejection = "This master trade is already linked to the follower."
            elif message.action not in ENTRY_ACTIONS and link is None:
                rejection = "No active follower ticket mapping exists for this master trade."
            elif message.action in ENTRY_ACTIONS and state.global_pause:
                rejection = f"System is paused: {state.reason}"
            elif message.action in ENTRY_ACTIONS and state.execution_mode == ExecutionMode.MONITOR:
                rejection = "System is in monitor-only mode."
            elif (
                message.action in ENTRY_ACTIONS
                and state.execution_mode == ExecutionMode.LIVE
                and not self.settings.execution_is_permitted
            ):
                rejection = "Live execution is disabled by environment safety gates."
            elif message.action in ENTRY_ACTIONS and profile is None:
                rejection = "Follower has no risk profile."

            if rejection:
                job = self._rejected_job(source_event, follower, symbol=symbol, reason=rejection)
                session.add(job)
                jobs.append(job)
                continue

            try:
                if message.action in ENTRY_ACTIONS:
                    assert profile is not None
                    snapshot = self.snapshot_provider.get(session, follower, symbol)
                    decision = self.risk_calculator.calculate_volume(
                        snapshot=snapshot,
                        profile=profile,
                        master_volume=message.volume,
                        master_equity=Decimal(master.equity),
                        entry_price=entry,
                        stop_loss=stop,
                    )
                    volume = decision.volume
                    cash_risk = decision.cash_risk
                else:
                    assert link is not None
                    symbol = link.follower_symbol
                    if message.source_position_id:
                        entry = Decimal(link.entry_price)
                        if mapping is not None and not mapping.preserve_relative_stops:
                            offset = Decimal(mapping.price_offset)
                            stop = message.stop_loss + offset if message.stop_loss else None
                            target = (
                                message.take_profit + offset if message.take_profit else None
                            )
                        else:
                            stop = None
                            if message.stop_loss is not None:
                                distance = abs(message.entry_price - message.stop_loss)
                                stop = (
                                    entry - distance
                                    if message.side.value == "buy"
                                    else entry + distance
                                )
                            target = None
                            if message.take_profit is not None:
                                distance = abs(message.take_profit - message.entry_price)
                                target = (
                                    entry + distance
                                    if message.side.value == "buy"
                                    else entry - distance
                                )
                    volume = self._lifecycle_volume(session, follower, message, link)
                    cash_risk = Decimal("0")
            except (RiskRejectedError, SnapshotUnavailableError) as exc:
                job = self._rejected_job(source_event, follower, symbol=symbol, reason=str(exc))
                session.add(job)
                jobs.append(job)
                continue

            job = CopyJob(
                source_event_id=source_event.id,
                follower_account_id=follower.id,
                status=JobStatus.QUEUED.value,
                follower_symbol=symbol,
                requested_volume=volume,
                requested_price=entry,
                stop_loss=stop,
                take_profit=target,
                risk_cash=cash_risk,
            )
            session.add(job)
            session.flush()
            jobs.append(job)

            command = FollowerCommand(
                job_uid=UUID(job.job_uid),
                source_event_uid=message.event_uid,
                follower_account_id=UUID(follower.id),
                source_order_id=message.source_order_id,
                source_position_id=message.source_position_id,
                target_order_id=link.follower_order_id if link else None,
                target_position_id=link.follower_position_id if link else None,
                action=message.action,
                side=message.side,
                order_type=OrderType(str(message.metadata.get("order_type", "market"))),
                symbol=symbol,
                volume=volume,
                entry_price=entry,
                stop_loss=stop,
                take_profit=target,
                expiration_at=message.metadata.get("expiration_at"),
                max_slippage_points=profile.max_slippage_points if profile else 30,
            )
            session.commit()
            started = time.perf_counter()
            job.status = JobStatus.DISPATCHED.value
            job.dispatched_at = datetime.now(UTC)
            ack = await self.transport.send(command)
            elapsed_ms = Decimal(str((time.perf_counter() - started) * 1000)).quantize(
                Decimal("0.001")
            )
            self._record_ack(
                session,
                job,
                ack,
                elapsed_ms,
                master=master,
                follower=follower,
                message=message,
                link=link,
            )

        record_audit(
            session,
            action="source_event.processed",
            target_type="source_trade_event",
            target_id=source_event.id,
            severity=AuditSeverity.INFO,
            message=f"Processed {message.action.value} for {len(followers)} eligible followers.",
            details={"jobs": len(jobs), "event_uid": str(message.event_uid)},
        )
        session.commit()
        self.events.publish(
            {
                "type": "source_event.processed",
                "event_uid": str(message.event_uid),
                "job_count": len(jobs),
            }
        )
        return jobs

    def _record_ack(
        self,
        session: Session,
        job: CopyJob,
        ack: ExecutionAck,
        local_latency_ms: Decimal,
        *,
        master: Account,
        follower: Account,
        message: SourceTradeMessage,
        link: TradeLink | None,
    ) -> None:
        job.status = ack.status.value
        job.acknowledged_at = ack.received_at
        job.local_latency_ms = local_latency_ms
        if ack.status in {JobStatus.REJECTED, JobStatus.FAILED}:
            job.rejection_reason = ack.error
        session.add(
            ExecutionAcknowledgement(
                copy_job_id=job.id,
                status=ack.status.value,
                broker_order_id=ack.broker_order_id or "",
                broker_position_id=ack.broker_position_id or "",
                broker_result_code=ack.broker_result_code,
                filled_price=ack.filled_price,
                filled_volume=ack.filled_volume,
                error=ack.error,
                received_at=ack.received_at,
            )
        )
        if ack.status in SUCCESS_STATUSES:
            source_type, source_ticket = self._source_identity(message)
            if link is None and message.action in ENTRY_ACTIONS:
                link = TradeLink(
                    master_account_id=master.id,
                    follower_account_id=follower.id,
                    source_type=source_type,
                    source_ticket=source_ticket,
                    source_order_id=message.source_order_id,
                    source_position_id=message.source_position_id or "",
                    follower_symbol=job.follower_symbol,
                    follower_order_id=ack.broker_order_id or "",
                    follower_position_id=ack.broker_position_id or "",
                    side=message.side.value,
                    source_volume=message.volume,
                    follower_volume=ack.filled_volume or job.requested_volume,
                    entry_price=ack.filled_price or job.requested_price,
                    stop_loss=job.stop_loss,
                    take_profit=job.take_profit,
                    status="active",
                    last_source_event_id=job.source_event_id,
                )
                session.add(link)
            elif link is not None:
                link.last_source_event_id = job.source_event_id
                link.stop_loss = job.stop_loss
                link.take_profit = job.take_profit
                link.last_error = ""
                if ack.broker_order_id:
                    link.follower_order_id = ack.broker_order_id
                if ack.broker_position_id:
                    link.follower_position_id = ack.broker_position_id
                if message.action is TradeAction.PARTIAL_CLOSE:
                    link.source_volume = max(
                        Decimal("0"), Decimal(link.source_volume) - message.volume
                    )
                    link.follower_volume = max(
                        Decimal("0"), Decimal(link.follower_volume) - job.requested_volume
                    )
                elif message.action is TradeAction.CLOSE:
                    link.source_volume = Decimal("0")
                    link.follower_volume = Decimal("0")
                    link.status = "closed"
                elif message.action is TradeAction.CANCEL:
                    link.source_volume = Decimal("0")
                    link.follower_volume = Decimal("0")
                    link.status = "cancelled"
                session.add(link)
        elif link is not None:
            link.last_error = ack.error
            session.add(link)
        session.commit()
