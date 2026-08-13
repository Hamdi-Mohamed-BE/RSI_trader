import importlib
import logging
import os
from contextlib import suppress
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..domain.enums import (
    AccountRole,
    AccountState,
    AuditSeverity,
    ExecutionMode,
    JobStatus,
    OrderType,
    Side,
    TradeAction,
)
from ..domain.messages import SourceTradeMessage
from ..models import Account, MasterTradeState, SourceTradeEvent, TradeLink
from .accounts import ensure_system_state
from .audit import record_audit
from .copier import CopierCore
from .credentials import CredentialVault
from .terminals import TerminalManager

logger = logging.getLogger("aaa.master_watcher")


@dataclass(frozen=True)
class ObservedMasterTrade:
    source_type: str
    source_ticket: str
    broker_ticket: str
    symbol: str
    side: Side
    order_type: OrderType
    broker_order_type: int
    volume: Decimal
    entry_price: Decimal
    stop_loss: Decimal | None
    take_profit: Decimal | None
    expiration_at: datetime | None = None

    @property
    def fingerprint(self) -> str:
        values = (
            self.broker_ticket,
            self.symbol,
            self.side.value,
            self.order_type.value,
            str(self.broker_order_type),
            str(self.volume),
            str(self.entry_price),
            str(self.stop_loss or ""),
            str(self.take_profit or ""),
            self.expiration_at.isoformat() if self.expiration_at else "",
        )
        return "|".join(values)


@dataclass(frozen=True)
class MasterPollResult:
    master_id: str
    master_name: str
    master_login: str
    position_count: int
    pending_count: int


class MasterSnapshotReader:
    """Reads all current orders and positions from the active master terminal."""

    def __init__(
        self,
        *,
        vault: CredentialVault,
        mt5_module: Any | None = None,
        platform_name: str = os.name,
    ) -> None:
        self.vault = vault
        self.mt5_module = mt5_module
        self.platform_name = platform_name

    def _connector(self) -> Any:
        if self.mt5_module is not None:
            return self.mt5_module
        try:
            return importlib.import_module("MetaTrader5")
        except ImportError as exc:
            raise RuntimeError("The MetaTrader5 Python connector is not installed.") from exc

    @staticmethod
    def _optional_price(value: Any) -> Decimal | None:
        parsed = Decimal(str(value or 0))
        return parsed if parsed > 0 else None

    def _initialize(self, connector: Any, account: Account) -> None:
        if self.platform_name != "nt":
            raise RuntimeError("Continuous MT5 copying is available only on Windows.")
        if not account.terminal_path:
            raise ValueError("The active master has no assigned MT5 terminal.")
        executable = Path(account.terminal_path).expanduser().resolve(strict=True)
        portable = (executable.parent / ".aaa-instance.json").is_file()
        if not connector.initialize(str(executable), timeout=60_000, portable=portable):
            raise ValueError(f"Could not connect to master MT5: {connector.last_error()}")
        if account.credential_ref:
            password = self.vault.retrieve(account.credential_ref)
            if not connector.login(
                int(account.login),
                password=password,
                server=account.broker_server,
                timeout=60_000,
            ):
                raise ValueError(f"Master MT5 login failed: {connector.last_error()}")
        info = connector.account_info()
        terminal = connector.terminal_info()
        if info is None or terminal is None or not bool(getattr(terminal, "connected", False)):
            raise ValueError("The active master MT5 is not connected.")
        if str(info.login) != account.login:
            raise ValueError("The selected master MT5 is logged into a different account.")

    @staticmethod
    def _pending_kind(connector: Any, value: int) -> tuple[Side, OrderType]:
        mapping = {
            int(getattr(connector, "ORDER_TYPE_BUY_LIMIT", 2)): (Side.BUY, OrderType.LIMIT),
            int(getattr(connector, "ORDER_TYPE_SELL_LIMIT", 3)): (Side.SELL, OrderType.LIMIT),
            int(getattr(connector, "ORDER_TYPE_BUY_STOP", 4)): (Side.BUY, OrderType.STOP),
            int(getattr(connector, "ORDER_TYPE_SELL_STOP", 5)): (Side.SELL, OrderType.STOP),
        }
        if value not in mapping:
            raise ValueError(f"Unsupported master pending-order type {value}.")
        return mapping[value]

    def read(self, account: Account) -> list[ObservedMasterTrade]:
        connector = self._connector()
        try:
            self._initialize(connector, account)
            observed: list[ObservedMasterTrade] = []
            buy_position = int(getattr(connector, "POSITION_TYPE_BUY", 0))
            for position in connector.positions_get() or ():
                ticket = str(getattr(position, "ticket", "") or "")
                identifier = str(getattr(position, "identifier", "") or ticket)
                observed.append(
                    ObservedMasterTrade(
                        source_type="position",
                        source_ticket=identifier,
                        broker_ticket=ticket,
                        symbol=str(position.symbol),
                        side=Side.BUY if int(position.type) == buy_position else Side.SELL,
                        order_type=OrderType.MARKET,
                        broker_order_type=int(position.type),
                        volume=Decimal(str(position.volume)),
                        entry_price=Decimal(str(position.price_open)),
                        stop_loss=self._optional_price(position.sl),
                        take_profit=self._optional_price(position.tp),
                    )
                )
            for order in connector.orders_get() or ():
                broker_type = int(order.type)
                side, order_type = self._pending_kind(connector, broker_type)
                expiration = int(getattr(order, "time_expiration", 0) or 0)
                observed.append(
                    ObservedMasterTrade(
                        source_type="pending",
                        source_ticket=str(order.ticket),
                        broker_ticket=str(order.ticket),
                        symbol=str(order.symbol),
                        side=side,
                        order_type=order_type,
                        broker_order_type=broker_type,
                        volume=Decimal(str(order.volume_current)),
                        entry_price=Decimal(str(order.price_open)),
                        stop_loss=self._optional_price(order.sl),
                        take_profit=self._optional_price(order.tp),
                        expiration_at=(
                            datetime.fromtimestamp(expiration, UTC) if expiration else None
                        ),
                    )
                )
            return observed
        finally:
            with suppress(AttributeError, RuntimeError):
                connector.shutdown()


class ContinuousTradeCopier:
    """Reconciles the complete master lifecycle into durable follower commands."""

    def __init__(
        self,
        *,
        core: CopierCore,
        reader: MasterSnapshotReader,
        terminal_manager: TerminalManager,
        retry_seconds: int = 5,
    ) -> None:
        self.core = core
        self.reader = reader
        self.terminal_manager = terminal_manager
        self.retry_seconds = retry_seconds
        self._sequence = 0

    def _next_sequence(self, session: Session) -> int:
        if self._sequence <= 0:
            self._sequence = int(session.scalar(select(func.max(SourceTradeEvent.sequence))) or 0)
        self._sequence += 1
        return self._sequence

    @staticmethod
    def _record_change(
        session: Session,
        master: Account,
        *,
        action: str,
        trade: MasterTradeState | ObservedMasterTrade,
        note: str = "",
    ) -> None:
        message = (
            f"Detected {action} on master {master.display_name}: "
            f"{trade.side} {trade.symbol} ticket {trade.source_ticket}, "
            f"volume {trade.volume}, SL {trade.stop_loss or 'none'}, "
            f"TP {trade.take_profit or 'none'}."
        )
        if note:
            message = f"{message} {note}"
        logger.info(message)
        record_audit(
            session,
            actor="master-watcher",
            action=f"master.change.{action}",
            target_type="account",
            target_id=master.id,
            message=message,
            details={
                "source_type": trade.source_type,
                "source_ticket": trade.source_ticket,
                "broker_ticket": trade.broker_ticket,
                "symbol": trade.symbol,
                "side": str(trade.side),
                "volume": str(trade.volume),
                "entry_price": str(trade.entry_price),
                "stop_loss": str(trade.stop_loss or ""),
                "take_profit": str(trade.take_profit or ""),
            },
        )
        session.commit()

    @staticmethod
    def _message(
        state_or_trade: MasterTradeState | ObservedMasterTrade,
        *,
        master: Account,
        sequence: int,
        action: TradeAction,
        volume: Decimal | None = None,
        previous_volume: Decimal | None = None,
    ) -> SourceTradeMessage:
        source_type = state_or_trade.source_type
        source_ticket = state_or_trade.source_ticket
        expiration = state_or_trade.expiration_at
        metadata: dict[str, object] = {
            "source": "continuous_mt5_reconciliation",
            "order_type": state_or_trade.order_type.value
            if isinstance(state_or_trade, ObservedMasterTrade)
            else OrderType.MARKET.value
            if source_type == "position"
            else (
                OrderType.LIMIT.value
                if state_or_trade.order_type in {2, 3}
                else OrderType.STOP.value
            ),
        }
        if expiration:
            metadata["expiration_at"] = expiration.isoformat()
        if previous_volume is not None:
            metadata["previous_volume"] = str(previous_volume)
        return SourceTradeMessage(
            event_uid=uuid4(),
            sequence=sequence,
            source_account_id=UUID(master.id),
            source_order_id=source_ticket,
            source_position_id=source_ticket if source_type == "position" else None,
            action=action,
            side=Side(state_or_trade.side),
            symbol=state_or_trade.symbol,
            volume=volume or Decimal(state_or_trade.volume),
            entry_price=Decimal(state_or_trade.entry_price),
            stop_loss=(
                Decimal(state_or_trade.stop_loss) if state_or_trade.stop_loss is not None else None
            ),
            take_profit=(
                Decimal(state_or_trade.take_profit)
                if state_or_trade.take_profit is not None
                else None
            ),
            occurred_at=datetime.now(UTC),
            metadata=metadata,
        )

    @staticmethod
    def _update_state(state: MasterTradeState, trade: ObservedMasterTrade) -> None:
        preserve_baseline = state.status == "baseline"
        state.broker_ticket = trade.broker_ticket
        state.symbol = trade.symbol
        state.side = trade.side.value
        state.order_type = trade.broker_order_type
        state.volume = trade.volume
        state.entry_price = trade.entry_price
        state.stop_loss = trade.stop_loss
        state.take_profit = trade.take_profit
        state.expiration_at = trade.expiration_at
        state.fingerprint = trade.fingerprint
        state.status = "baseline" if preserve_baseline else "active"
        state.last_seen_at = datetime.now(UTC)

    @staticmethod
    def _position_from_state(state: MasterTradeState) -> ObservedMasterTrade:
        return ObservedMasterTrade(
            source_type="position",
            source_ticket=state.source_ticket,
            broker_ticket=state.broker_ticket,
            symbol=state.symbol,
            side=Side(state.side),
            order_type=OrderType.MARKET,
            broker_order_type=state.order_type,
            volume=Decimal(state.volume),
            entry_price=Decimal(state.entry_price),
            stop_loss=(Decimal(state.stop_loss) if state.stop_loss is not None else None),
            take_profit=(
                Decimal(state.take_profit) if state.take_profit is not None else None
            ),
            expiration_at=state.expiration_at,
        )

    @staticmethod
    def _entry_copying_enabled(global_pause: bool, execution_mode: str) -> bool:
        return not global_pause and execution_mode in {
            ExecutionMode.DEMO.value,
            ExecutionMode.LIVE.value,
        }

    async def _dispatch(
        self,
        session: Session,
        master: Account,
        message: SourceTradeMessage,
        state: MasterTradeState,
    ) -> bool:
        self.terminal_manager.ensure_symbol_routing(
            session,
            message.symbol,
            actor="continuous-copier",
        )
        jobs = await self.core.process(session, message)
        state.last_dispatched_at = datetime.now(UTC)
        session.add(state)
        session.commit()
        completed = bool(jobs) and all(
            job.status in {JobStatus.FILLED.value, JobStatus.ACKNOWLEDGED.value}
            or job.rejection_reason == "This master trade is already linked to the follower."
            for job in jobs
        )
        if not jobs:
            result_message = (
                f"Master {message.action.value} ticket {message.source_order_id} produced no "
                "follower jobs because no eligible active followers were found."
            )
            logger.warning(result_message)
            record_audit(
                session,
                actor="master-watcher",
                action="copier.dispatch.no_followers",
                target_type="account",
                target_id=master.id,
                message=result_message,
            )
        for job in jobs:
            follower_id = str(getattr(job, "follower_account_id", "") or "")
            follower = session.get(Account, follower_id) if follower_id else None
            follower_name = (
                follower.display_name if follower is not None else follower_id or "unknown follower"
            )
            reason = str(getattr(job, "rejection_reason", "") or "").strip()
            job_status = str(getattr(job, "status", JobStatus.FAILED.value))
            result_message = (
                f"Copy {message.action.value} for master ticket {message.source_order_id} -> "
                f"{follower_name}: {job_status}"
            )
            if reason:
                result_message = f"{result_message}. {reason}"
            log_method = logger.info if job_status in {
                JobStatus.FILLED.value,
                JobStatus.ACKNOWLEDGED.value,
            } else logger.warning
            log_method(result_message)
            record_audit(
                session,
                actor="master-watcher",
                action=f"copier.dispatch.{job_status}",
                target_type="account",
                target_id=follower_id or master.id,
                message=result_message,
                details={
                    "source_order_id": message.source_order_id,
                    "source_position_id": message.source_position_id or "",
                    "symbol": str(getattr(job, "follower_symbol", message.symbol)),
                    "requested_volume": str(getattr(job, "requested_volume", "")),
                    "status": job_status,
                    "reason": reason,
                },
            )
        state.last_dispatch_failed = not completed
        session.add(state)
        session.commit()
        return completed

    def _retry_ready(self, state: MasterTradeState) -> bool:
        if not state.last_dispatch_failed:
            return True
        dispatched = state.last_dispatched_at
        if dispatched is None:
            return True
        if dispatched.tzinfo is None:
            dispatched = dispatched.replace(tzinfo=UTC)
        return dispatched <= datetime.now(UTC) - timedelta(seconds=self.retry_seconds)

    @staticmethod
    def _transition_pending_link(
        session: Session,
        master: Account,
        pending_state: MasterTradeState,
        position: ObservedMasterTrade,
    ) -> MasterTradeState:
        links = session.scalars(
            select(TradeLink).where(
                TradeLink.master_account_id == master.id,
                TradeLink.source_type == "pending",
                TradeLink.source_ticket == pending_state.source_ticket,
                TradeLink.status == "active",
            )
        ).all()
        removed_link_ids: list[str] = []
        for link in links:
            conflicting = session.scalar(
                select(TradeLink).where(
                    TradeLink.master_account_id == master.id,
                    TradeLink.follower_account_id == link.follower_account_id,
                    TradeLink.source_type == "position",
                    TradeLink.source_ticket == position.source_ticket,
                    TradeLink.id != link.id,
                )
            )
            if conflicting is None:
                continue
            removed_link_ids.append(conflicting.id)
            session.delete(conflicting)

        # Delete conflicting position rows before changing the pending keys. An
        # older Publisher event may already have inserted those keys.
        if removed_link_ids:
            session.flush()
        for link in links:
            link.source_type = "position"
            link.source_position_id = position.source_ticket
            link.source_volume = position.volume
            session.add(link)

        conflicting_state = session.scalar(
            select(MasterTradeState).where(
                MasterTradeState.master_account_id == master.id,
                MasterTradeState.source_type == "position",
                MasterTradeState.source_ticket == position.source_ticket,
                MasterTradeState.id != pending_state.id,
            )
        )
        removed_state_id = ""
        if conflicting_state is not None:
            removed_state_id = conflicting_state.id
            session.delete(conflicting_state)
            session.flush()

        pending_state.source_type = "position"
        ContinuousTradeCopier._update_state(pending_state, position)
        session.add(pending_state)
        if removed_link_ids or removed_state_id:
            record_audit(
                session,
                actor="master-watcher",
                action="master.pending_fill_conflict_merged",
                target_type="account",
                target_id=master.id,
                severity=AuditSeverity.WARNING,
                message=(
                    f"Merged duplicate Publisher/watcher records for filled pending ticket "
                    f"{position.source_ticket}; copying continues from the pending-order link."
                ),
                details={
                    "source_ticket": position.source_ticket,
                    "removed_trade_link_ids": removed_link_ids,
                    "removed_master_state_id": removed_state_id,
                    "review_follower_for_legacy_duplicate": bool(removed_link_ids),
                },
            )
        session.commit()
        return pending_state

    async def poll_once(self, session: Session) -> MasterPollResult | None:
        system = ensure_system_state(session)
        if not system.active_master_account_id:
            return None
        master = session.get(Account, system.active_master_account_id)
        if master is None or not master.is_master or master.state != AccountState.ACTIVE.value:
            return None
        observed = self.reader.read(master)
        poll_result = MasterPollResult(
            master_id=master.id,
            master_name=master.display_name,
            master_login=master.login,
            position_count=sum(trade.source_type == "position" for trade in observed),
            pending_count=sum(trade.source_type == "pending" for trade in observed),
        )
        observed_by_key = {(trade.source_type, trade.source_ticket): trade for trade in observed}
        states = session.scalars(
            select(MasterTradeState).where(
                MasterTradeState.master_account_id == master.id,
                MasterTradeState.status.in_(("active", "baseline")),
            )
        ).all()
        states_by_key = {(state.source_type, state.source_ticket): state for state in states}

        # A filled pending order normally keeps its ticket as the position identifier.
        # Merge even if the position closed while the core was down: the stored
        # position state is enough to repair the Publisher/watcher collision.
        pending_states = [
            state for state in states if state.source_type == "pending"
        ]
        for pending_state in pending_states:
            position_key = ("position", pending_state.source_ticket)
            position_state = states_by_key.get(position_key)
            position = observed_by_key.get(position_key)
            if position is None and position_state is not None:
                position = self._position_from_state(position_state)
            if position is None:
                continue
            self._record_change(
                session,
                master,
                action="pending_filled",
                trade=position,
            )
            canonical_state = self._transition_pending_link(
                session,
                master,
                pending_state,
                position,
            )
            states_by_key.pop(("pending", position.source_ticket))
            states_by_key.pop(position_key, None)
            states_by_key[("position", position.source_ticket)] = canonical_state

        # First obey closes and cancellations. They are processed even when new entries are paused.
        for key, state in list(states_by_key.items()):
            if key in observed_by_key:
                continue
            if state.status == "baseline":
                state.status = "closed" if state.source_type == "position" else "cancelled"
                state.last_dispatch_failed = False
                session.add(state)
                session.commit()
                continue
            if not self._retry_ready(state):
                continue
            action = TradeAction.CLOSE if state.source_type == "position" else TradeAction.CANCEL
            self._record_change(
                session,
                master,
                action=action.value,
                trade=state,
            )
            message = self._message(
                state,
                master=master,
                sequence=self._next_sequence(session),
                action=action,
            )
            await self._dispatch(session, master, message, state)
            active_link = session.scalar(
                select(TradeLink.id).where(
                    TradeLink.master_account_id == master.id,
                    TradeLink.source_type == state.source_type,
                    TradeLink.source_ticket == state.source_ticket,
                    TradeLink.status == "active",
                )
            )
            if active_link is not None:
                continue
            state.status = "closed" if action is TradeAction.CLOSE else "cancelled"
            session.add(state)
            session.commit()

        for key, trade in observed_by_key.items():
            current_state = states_by_key.get(key)
            if current_state is None:
                entry_enabled = self._entry_copying_enabled(
                    system.global_pause,
                    system.execution_mode,
                )
                current_state = MasterTradeState(
                    master_account_id=master.id,
                    source_type=trade.source_type,
                    source_ticket=trade.source_ticket,
                    broker_ticket=trade.broker_ticket,
                    symbol=trade.symbol,
                    side=trade.side.value,
                    order_type=trade.broker_order_type,
                    volume=trade.volume,
                    entry_price=trade.entry_price,
                    stop_loss=trade.stop_loss,
                    take_profit=trade.take_profit,
                    expiration_at=trade.expiration_at,
                    fingerprint=trade.fingerprint,
                    status="active" if entry_enabled else "baseline",
                    last_seen_at=datetime.now(UTC),
                )
                session.add(current_state)
                session.flush()
                if not entry_enabled:
                    self._record_change(
                        session,
                        master,
                        action="baselined",
                        trade=trade,
                        note=(
                            f"Not copied because execution mode is {system.execution_mode} "
                            f"and pause is {system.global_pause}."
                        ),
                    )
                    session.commit()
                    continue
                action = (
                    TradeAction.MARKET_OPEN
                    if trade.source_type == "position"
                    else TradeAction.PENDING_CREATE
                )
                self._record_change(
                    session,
                    master,
                    action=action.value,
                    trade=trade,
                )
                message = self._message(
                    trade,
                    master=master,
                    sequence=self._next_sequence(session),
                    action=action,
                )
                await self._dispatch(session, master, message, current_state)
                continue

            if current_state.status == "baseline":
                self._update_state(current_state, trade)
                current_state.last_dispatch_failed = False
                session.add(current_state)
                session.commit()
                continue

            previous_volume = Decimal(current_state.volume)
            if trade.fingerprint != current_state.fingerprint and not self._retry_ready(
                current_state
            ):
                current_state.last_seen_at = datetime.now(UTC)
                session.add(current_state)
                session.commit()
                continue
            if trade.source_type == "position" and trade.volume < previous_volume:
                self._record_change(
                    session,
                    master,
                    action=TradeAction.PARTIAL_CLOSE.value,
                    trade=trade,
                    note=f"Previous volume was {previous_volume}.",
                )
                message = self._message(
                    trade,
                    master=master,
                    sequence=self._next_sequence(session),
                    action=TradeAction.PARTIAL_CLOSE,
                    volume=previous_volume - trade.volume,
                    previous_volume=previous_volume,
                )
                completed = await self._dispatch(session, master, message, current_state)
            elif trade.fingerprint != current_state.fingerprint:
                self._record_change(
                    session,
                    master,
                    action=TradeAction.MODIFY.value,
                    trade=trade,
                )
                message = self._message(
                    trade,
                    master=master,
                    sequence=self._next_sequence(session),
                    action=TradeAction.MODIFY,
                )
                completed = await self._dispatch(session, master, message, current_state)
            else:
                completed = True
            if not completed:
                current_state.last_seen_at = datetime.now(UTC)
                session.add(current_state)
                session.commit()
                continue
            self._update_state(current_state, trade)
            session.add(current_state)
            session.commit()

        # Retry an active trade only when at least one enabled follower still has no link.
        if not self._entry_copying_enabled(system.global_pause, system.execution_mode):
            return poll_result
        follower_ids = set(
            session.scalars(
                select(Account.id).where(
                    Account.role == AccountRole.FOLLOWER.value,
                    Account.state == AccountState.ACTIVE.value,
                    Account.is_master.is_(False),
                )
            ).all()
        )
        if not follower_ids:
            return poll_result
        retry_before = datetime.now(UTC) - timedelta(seconds=self.retry_seconds)
        for state in session.scalars(
            select(MasterTradeState).where(
                MasterTradeState.master_account_id == master.id,
                MasterTradeState.status == "active",
            )
        ).all():
            linked = set(
                session.scalars(
                    select(TradeLink.follower_account_id).where(
                        TradeLink.master_account_id == master.id,
                        TradeLink.source_type == state.source_type,
                        TradeLink.source_ticket == state.source_ticket,
                        TradeLink.status == "active",
                    )
                ).all()
            )
            if follower_ids <= linked:
                continue
            dispatched = state.last_dispatched_at
            if dispatched is not None:
                if dispatched.tzinfo is None:
                    dispatched = dispatched.replace(tzinfo=UTC)
                if dispatched > retry_before:
                    continue
            action = (
                TradeAction.MARKET_OPEN
                if state.source_type == "position"
                else TradeAction.PENDING_CREATE
            )
            message = self._message(
                state,
                master=master,
                sequence=self._next_sequence(session),
                action=action,
            )
            await self._dispatch(session, master, message, state)
        return poll_result
