import importlib
import os
from contextlib import suppress
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session, sessionmaker

from ..domain.enums import AuditSeverity, JobStatus, OrderType, Side, TradeAction
from ..domain.messages import ExecutionAck, FollowerCommand
from ..models import Account
from .audit import record_audit
from .credentials import CredentialVault

COPIER_MAGIC = 99_001_001


class Mt5FollowerExecutor:
    """Executes one lifecycle command against the follower's dedicated MT5."""

    def __init__(
        self,
        *,
        vault: CredentialVault,
        allow_live: bool = False,
        mt5_module: Any | None = None,
        platform_name: str = os.name,
    ) -> None:
        self.vault = vault
        self.allow_live = allow_live
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
    def _last_error(connector: Any) -> str:
        with suppress(AttributeError, RuntimeError, TypeError, ValueError):
            return str(connector.last_error())
        return "unknown MT5 error"

    def _initialize(self, connector: Any, account: Account) -> None:
        if self.platform_name != "nt":
            raise RuntimeError("MT5 copying is available only on Windows.")
        if not account.terminal_path:
            raise ValueError("The follower has no assigned MT5 terminal.")
        executable = Path(account.terminal_path).expanduser().resolve(strict=True)
        if executable.name.lower() not in {"terminal.exe", "terminal64.exe"}:
            raise ValueError("The configured follower MT5 executable is invalid.")
        portable = (executable.parent / ".aaa-instance.json").is_file()
        if not connector.initialize(str(executable), timeout=60_000, portable=portable):
            raise ValueError(f"MT5 could not start: {self._last_error(connector)}")
        if account.credential_ref:
            password = self.vault.retrieve(account.credential_ref)
            if not connector.login(
                int(account.login),
                password=password,
                server=account.broker_server,
                timeout=60_000,
            ):
                raise ValueError(f"MT5 login was rejected: {self._last_error(connector)}")
        account_info = connector.account_info()
        terminal_info = connector.terminal_info()
        if account_info is None or terminal_info is None:
            raise ValueError("MT5 did not return account and terminal state.")
        if str(account_info.login) != account.login:
            raise ValueError("The follower MT5 is logged into a different account.")
        demo_mode = getattr(connector, "ACCOUNT_TRADE_MODE_DEMO", 0)
        if account_info.trade_mode != demo_mode and not self.allow_live:
            raise ValueError("Live-account copying is blocked by the environment safety gates.")
        if not bool(getattr(terminal_info, "connected", False)):
            raise ValueError("The follower MT5 is disconnected from its broker.")
        if bool(getattr(terminal_info, "tradeapi_disabled", False)):
            raise ValueError("MT5 has disabled trading through the external Python API.")
        if account.position_mode != "hedging":
            raise ValueError("Continuous execution currently requires a hedging follower account.")

    @staticmethod
    def _success_retcodes(connector: Any) -> set[int]:
        return {
            int(getattr(connector, "TRADE_RETCODE_PLACED", 10008)),
            int(getattr(connector, "TRADE_RETCODE_DONE", 10009)),
            int(getattr(connector, "TRADE_RETCODE_DONE_PARTIAL", 10010)),
            int(getattr(connector, "TRADE_RETCODE_NO_CHANGES", 10025)),
        }

    @staticmethod
    def _result_error(result: Any) -> str:
        if result is None:
            return "MT5 returned no broker result."
        return (
            f"Broker retcode {getattr(result, 'retcode', 'unknown')}: "
            f"{getattr(result, 'comment', 'request rejected')}"
        )

    @staticmethod
    def _round_price(value: Decimal | None, digits: int) -> float:
        if value is None:
            return 0.0
        quantum = Decimal(1).scaleb(-digits)
        return float(value.quantize(quantum))

    @staticmethod
    def _order_type(connector: Any, side: Side, order_type: OrderType) -> int:
        names = {
            (Side.BUY, OrderType.MARKET): "ORDER_TYPE_BUY",
            (Side.SELL, OrderType.MARKET): "ORDER_TYPE_SELL",
            (Side.BUY, OrderType.LIMIT): "ORDER_TYPE_BUY_LIMIT",
            (Side.SELL, OrderType.LIMIT): "ORDER_TYPE_SELL_LIMIT",
            (Side.BUY, OrderType.STOP): "ORDER_TYPE_BUY_STOP",
            (Side.SELL, OrderType.STOP): "ORDER_TYPE_SELL_STOP",
        }
        return int(getattr(connector, names[(side, order_type)]))

    @staticmethod
    def _filling_modes(connector: Any, *, pending: bool) -> list[int]:
        values = (
            [getattr(connector, "ORDER_FILLING_RETURN", 2)]
            if pending
            else [
                getattr(connector, "ORDER_FILLING_IOC", 1),
                getattr(connector, "ORDER_FILLING_FOK", 0),
                getattr(connector, "ORDER_FILLING_RETURN", 2),
            ]
        )
        return list(dict.fromkeys(int(value) for value in values))

    def _send(self, connector: Any, request: dict[str, object], *, deal: bool) -> Any:
        candidates = (
            [
                {**request, "type_filling": mode}
                for mode in self._filling_modes(connector, pending=False)
            ]
            if deal
            else [request]
        )
        last_result: Any = None
        for candidate in candidates:
            result = connector.order_send(candidate)
            last_result = result
            if result is not None and int(getattr(result, "retcode", -1)) in self._success_retcodes(
                connector
            ):
                return result
            invalid_fill = int(getattr(connector, "TRADE_RETCODE_INVALID_FILL", 10030))
            if not deal or result is None or int(getattr(result, "retcode", -1)) != invalid_fill:
                break
        raise ValueError(self._result_error(last_result))

    @staticmethod
    def _position_ticket(connector: Any, symbol: str, result: Any, tag: str) -> str:
        positions = connector.positions_get(symbol=symbol) or ()
        order_ticket = int(getattr(result, "order", 0) or 0)
        matching = [
            position
            for position in positions
            if (
                str(getattr(position, "comment", "")) == tag
                or int(getattr(position, "identifier", 0) or 0) == order_ticket
                or int(getattr(position, "ticket", 0) or 0) == order_ticket
            )
        ]
        if not matching:
            return str(order_ticket) if order_ticket else ""
        selected = max(
            matching,
            key=lambda position: (
                int(getattr(position, "time_msc", 0) or 0),
                int(getattr(position, "ticket", 0) or 0),
            ),
        )
        return str(getattr(selected, "ticket", "") or "")

    @staticmethod
    def _position_from_order(connector: Any, order_ticket: str) -> Any | None:
        if not order_ticket:
            return None
        expected = int(order_ticket)
        for position in connector.positions_get() or ():
            if int(getattr(position, "identifier", 0) or 0) == expected:
                return position
            if int(getattr(position, "ticket", 0) or 0) == expected:
                return position
        return None

    def _request(
        self,
        connector: Any,
        command: FollowerCommand,
        *,
        digits: int,
        tick: Any,
        tag: str,
    ) -> tuple[dict[str, object], bool]:
        if command.action is TradeAction.MARKET_OPEN:
            current = Decimal(str(tick.ask if command.side is Side.BUY else tick.bid))
            stop = command.stop_loss
            target = command.take_profit
            if command.stop_loss is not None:
                distance = abs(command.entry_price - command.stop_loss)
                stop = current - distance if command.side is Side.BUY else current + distance
            if command.take_profit is not None:
                distance = abs(command.take_profit - command.entry_price)
                target = current + distance if command.side is Side.BUY else current - distance
            return (
                {
                    "action": int(connector.TRADE_ACTION_DEAL),
                    "symbol": command.symbol,
                    "volume": float(command.volume),
                    "type": self._order_type(connector, command.side, OrderType.MARKET),
                    "price": self._round_price(current, digits),
                    "sl": self._round_price(stop, digits),
                    "tp": self._round_price(target, digits),
                    "deviation": command.max_slippage_points,
                    "magic": COPIER_MAGIC,
                    "comment": tag,
                },
                True,
            )
        if command.action is TradeAction.PENDING_CREATE:
            return (
                {
                    "action": int(connector.TRADE_ACTION_PENDING),
                    "symbol": command.symbol,
                    "volume": float(command.volume),
                    "type": self._order_type(connector, command.side, command.order_type),
                    "price": self._round_price(command.entry_price, digits),
                    "sl": self._round_price(command.stop_loss, digits),
                    "tp": self._round_price(command.take_profit, digits),
                    "magic": COPIER_MAGIC,
                    "comment": tag,
                    "type_time": int(
                        getattr(
                            connector,
                            "ORDER_TIME_SPECIFIED" if command.expiration_at else "ORDER_TIME_GTC",
                            0,
                        )
                    ),
                    "expiration": (
                        int(command.expiration_at.timestamp()) if command.expiration_at else 0
                    ),
                    "type_filling": int(getattr(connector, "ORDER_FILLING_RETURN", 2)),
                },
                False,
            )
        if command.action is TradeAction.MODIFY and command.target_position_id:
            return (
                {
                    "action": int(connector.TRADE_ACTION_SLTP),
                    "symbol": command.symbol,
                    "position": int(command.target_position_id),
                    "sl": self._round_price(command.stop_loss, digits),
                    "tp": self._round_price(command.take_profit, digits),
                },
                False,
            )
        if command.action is TradeAction.MODIFY and command.target_order_id:
            return (
                {
                    "action": int(connector.TRADE_ACTION_MODIFY),
                    "order": int(command.target_order_id),
                    "price": self._round_price(command.entry_price, digits),
                    "sl": self._round_price(command.stop_loss, digits),
                    "tp": self._round_price(command.take_profit, digits),
                    "type_time": int(
                        getattr(
                            connector,
                            "ORDER_TIME_SPECIFIED" if command.expiration_at else "ORDER_TIME_GTC",
                            0,
                        )
                    ),
                    "expiration": (
                        int(command.expiration_at.timestamp()) if command.expiration_at else 0
                    ),
                },
                False,
            )
        if command.action is TradeAction.CANCEL and command.target_order_id:
            return (
                {
                    "action": int(connector.TRADE_ACTION_REMOVE),
                    "order": int(command.target_order_id),
                },
                False,
            )
        if command.action in {TradeAction.PARTIAL_CLOSE, TradeAction.CLOSE}:
            if not command.target_position_id:
                if command.action is TradeAction.CLOSE and command.target_order_id:
                    return (
                        {
                            "action": int(connector.TRADE_ACTION_REMOVE),
                            "order": int(command.target_order_id),
                        },
                        False,
                    )
                raise ValueError("The close command has no mapped follower position ticket.")
            close_side = Side.SELL if command.side is Side.BUY else Side.BUY
            current = Decimal(str(tick.bid if close_side is Side.SELL else tick.ask))
            return (
                {
                    "action": int(connector.TRADE_ACTION_DEAL),
                    "symbol": command.symbol,
                    "position": int(command.target_position_id),
                    "volume": float(command.volume),
                    "type": self._order_type(connector, close_side, OrderType.MARKET),
                    "price": self._round_price(current, digits),
                    "deviation": command.max_slippage_points,
                    "magic": COPIER_MAGIC,
                    "comment": tag,
                },
                True,
            )
        raise ValueError(f"Unsupported or incomplete copier action: {command.action.value}.")

    def execute(
        self,
        session: Session,
        account: Account,
        command: FollowerCommand,
    ) -> ExecutionAck:
        connector = self._connector()
        result: Any = None
        try:
            self._initialize(connector, account)
            if not connector.symbol_select(command.symbol, True):
                raise ValueError(f"Could not enable {command.symbol} in Market Watch.")
            symbol_info = connector.symbol_info(command.symbol)
            tick = connector.symbol_info_tick(command.symbol)
            if symbol_info is None or tick is None:
                raise ValueError(f"No current broker price is available for {command.symbol}.")
            digits = max(0, int(getattr(symbol_info, "digits", 5)))
            if command.target_order_id and not command.target_position_id:
                linked_position = self._position_from_order(
                    connector,
                    command.target_order_id,
                )
                if linked_position is not None:
                    action = command.action
                    volume = command.volume
                    if action is TradeAction.CANCEL:
                        action = TradeAction.CLOSE
                        volume = Decimal(str(linked_position.volume))
                    command = command.model_copy(
                        update={
                            "action": action,
                            "volume": volume,
                            "target_position_id": str(linked_position.ticket),
                        }
                    )
            tag = f"AAA:{command.job_uid.hex[:12]}"
            request, is_deal = self._request(
                connector,
                command,
                digits=digits,
                tick=tick,
                tag=tag,
            )
            result = self._send(connector, request, deal=is_deal)
            broker_order = str(getattr(result, "order", "") or command.target_order_id or "")
            broker_position = command.target_position_id or ""
            if command.action is TradeAction.MARKET_OPEN:
                broker_position = self._position_ticket(connector, command.symbol, result, tag)
                if not broker_position:
                    raise ValueError(
                        "The broker filled the order but its follower position "
                        "ticket was not found."
                    )
            record_audit(
                session,
                actor="continuous-copier",
                action=f"follower.{command.action.value}",
                target_type="account",
                target_id=account.id,
                message=f"{command.action.value} completed on {account.display_name}.",
                details={
                    "job_uid": str(command.job_uid),
                    "symbol": command.symbol,
                    "order": broker_order,
                    "position": broker_position,
                    "retcode": int(getattr(result, "retcode", 0)),
                },
            )
            session.commit()
            return ExecutionAck(
                job_uid=command.job_uid,
                follower_account_id=command.follower_account_id,
                status=JobStatus.FILLED,
                broker_order_id=broker_order or None,
                broker_position_id=broker_position or None,
                requested_price=command.entry_price,
                filled_price=Decimal(str(getattr(result, "price", 0) or 0)) or None,
                filled_volume=command.volume,
                broker_result_code=int(getattr(result, "retcode", 0)),
                received_at=datetime.now(UTC),
            )
        except (ArithmeticError, OSError, RuntimeError, TypeError, ValueError) as exc:
            message = str(exc) or "Unknown follower execution error."
            record_audit(
                session,
                actor="continuous-copier",
                action=f"follower.{command.action.value}.failed",
                target_type="account",
                target_id=account.id,
                severity=AuditSeverity.WARNING,
                message=message,
                details={"job_uid": str(command.job_uid)},
            )
            session.commit()
            return ExecutionAck(
                job_uid=command.job_uid,
                follower_account_id=command.follower_account_id,
                status=JobStatus.FAILED,
                broker_order_id=str(getattr(result, "order", "") or "") or None,
                broker_result_code=getattr(result, "retcode", None),
                error=message,
                received_at=datetime.now(UTC),
            )
        finally:
            with suppress(AttributeError, RuntimeError):
                connector.shutdown()


class PythonMt5Transport:
    """Copier transport backed by the account's isolated MT5 Python session."""

    def __init__(
        self,
        *,
        session_factory: sessionmaker[Session],
        executor: Mt5FollowerExecutor,
    ) -> None:
        self.session_factory = session_factory
        self.executor = executor

    async def send(self, command: FollowerCommand) -> ExecutionAck:
        with self.session_factory() as session:
            account = session.get(Account, str(command.follower_account_id))
            if account is None:
                return ExecutionAck(
                    job_uid=command.job_uid,
                    follower_account_id=command.follower_account_id,
                    status=JobStatus.REJECTED,
                    error="The follower account no longer exists.",
                )
            return self.executor.execute(session, account, command)
