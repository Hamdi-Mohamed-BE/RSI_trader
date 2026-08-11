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
    TradeAction,
)
from ..domain.messages import ExecutionAck, FollowerCommand, SourceTradeMessage
from ..models import (
    Account,
    CopyJob,
    ExecutionAcknowledgement,
    SourceTradeEvent,
    SymbolMapping,
)
from ..transport.base import FollowerTransport
from .accounts import ensure_system_state
from .audit import record_audit
from .events import EventHub, event_hub
from .risk import RiskCalculator, RiskRejectedError
from .risk_profiles import ensure_default_risk_profile
from .snapshots import DatabaseSnapshotProvider, SnapshotUnavailableError

ENTRY_ACTIONS = {TradeAction.MARKET_OPEN, TradeAction.PENDING_CREATE, TradeAction.REVERSE}


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

            if message.action in ENTRY_ACTIONS and state.global_pause:
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
                    volume = message.volume
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
                action=message.action,
                side=message.side,
                symbol=symbol,
                volume=volume,
                entry_price=entry,
                stop_loss=stop,
                take_profit=target,
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
            self._record_ack(session, job, ack, elapsed_ms)

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

    @staticmethod
    def _record_ack(
        session: Session,
        job: CopyJob,
        ack: ExecutionAck,
        local_latency_ms: Decimal,
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
        session.commit()
