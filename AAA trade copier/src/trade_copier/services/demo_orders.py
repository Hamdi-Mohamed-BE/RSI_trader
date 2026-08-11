import importlib
import os
from contextlib import suppress
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from ..domain.enums import AuditSeverity, OrderType, Side
from ..models import Account
from .audit import record_audit
from .credentials import CredentialVault

DEMO_TEST_MAGIC = 99_001_002


@dataclass(frozen=True)
class DemoOrderRequest:
    side: Side
    order_type: OrderType
    symbol: str
    volume: Decimal
    entry_price: Decimal
    stop_loss: Decimal
    take_profit: Decimal | None
    max_slippage_points: int


@dataclass(frozen=True)
class DemoOrderOutcome:
    success: bool
    message: str
    broker_order_id: str = ""
    broker_deal_id: str = ""
    executed_price: Decimal | None = None
    cleanup_id: str = ""
    broker_retcode: int | None = None


class DemoOrderExecutor:
    """Places an explicitly requested demo-account test order and leaves it active."""

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
    def _last_error(connector: Any) -> str:
        with suppress(AttributeError, RuntimeError, TypeError, ValueError):
            return str(connector.last_error())
        return "unknown MT5 error"

    def _initialize(self, connector: Any, account: Account) -> None:
        if self.platform_name != "nt":
            raise RuntimeError("Demo MT5 execution is available only on Windows.")
        if not account.terminal_path:
            raise ValueError("The follower has no managed MT5 terminal.")
        executable = Path(account.terminal_path).expanduser().resolve(strict=True)
        if executable.name.lower() not in {"terminal.exe", "terminal64.exe"}:
            raise ValueError("The configured MT5 terminal executable is invalid.")
        if not connector.initialize(str(executable), timeout=60_000, portable=True):
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
            raise ValueError("MT5 did not return its account and terminal state.")
        if str(account_info.login) != account.login:
            raise ValueError("MT5 is logged into a different account.")
        if account_info.trade_mode != getattr(connector, "ACCOUNT_TRADE_MODE_DEMO", 0):
            raise ValueError("Actual Copy Test orders are blocked on live accounts.")
        if not bool(getattr(terminal_info, "connected", False)):
            raise ValueError("MT5 is not connected to the broker.")
        if bool(getattr(terminal_info, "tradeapi_disabled", False)):
            raise ValueError("MT5 has disabled trading through the external Python API.")

    @staticmethod
    def _round_price(value: Decimal, digits: int) -> float:
        quantum = Decimal(1).scaleb(-digits)
        return float(value.quantize(quantum))

    @staticmethod
    def _success_retcodes(connector: Any) -> set[int]:
        return {
            int(getattr(connector, "TRADE_RETCODE_PLACED", 10008)),
            int(getattr(connector, "TRADE_RETCODE_DONE", 10009)),
            int(getattr(connector, "TRADE_RETCODE_DONE_PARTIAL", 10010)),
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

    def _checked_send(
        self,
        connector: Any,
        request: dict[str, object],
        *,
        pending: bool,
    ) -> Any:
        last_check: Any = None
        last_result: Any = None
        for filling_mode in self._filling_modes(connector, pending=pending):
            candidate = {**request, "type_filling": filling_mode}
            check = connector.order_check(candidate)
            last_check = check
            if check is None or int(getattr(check, "retcode", -1)) != 0:
                continue
            result = connector.order_send(candidate)
            last_result = result
            if result is not None and int(getattr(result, "retcode", -1)) in (
                self._success_retcodes(connector)
            ):
                return result
            invalid_fill = int(getattr(connector, "TRADE_RETCODE_INVALID_FILL", 10030))
            if result is None or int(getattr(result, "retcode", -1)) != invalid_fill:
                return result
        detail = self._result_error(last_result or last_check)
        raise ValueError(f"MT5 order check failed. {detail}")

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

    def execute(
        self,
        session: Session,
        account: Account,
        request: DemoOrderRequest,
        *,
        actor: str,
    ) -> DemoOrderOutcome:
        connector = self._connector()
        broker_result: Any = None
        try:
            self._initialize(connector, account)
            if not connector.symbol_select(request.symbol, True):
                raise ValueError(f"Could not enable {request.symbol} in MT5 Market Watch.")
            symbol_info = connector.symbol_info(request.symbol)
            tick = connector.symbol_info_tick(request.symbol)
            if symbol_info is None or tick is None:
                raise ValueError(f"No current broker price is available for {request.symbol}.")
            digits = max(0, int(getattr(symbol_info, "digits", 5)))
            is_pending = request.order_type is not OrderType.MARKET
            entry = request.entry_price
            stop = request.stop_loss
            target = request.take_profit
            if not is_pending:
                entry = Decimal(str(tick.ask if request.side is Side.BUY else tick.bid))
                stop_distance = abs(request.entry_price - request.stop_loss)
                stop = entry - stop_distance if request.side is Side.BUY else entry + stop_distance
                if request.take_profit is not None:
                    target_distance = abs(request.take_profit - request.entry_price)
                    target = (
                        entry + target_distance
                        if request.side is Side.BUY
                        else entry - target_distance
                    )
            trade_request: dict[str, object] = {
                "action": int(
                    getattr(
                        connector,
                        "TRADE_ACTION_PENDING" if is_pending else "TRADE_ACTION_DEAL",
                    )
                ),
                "symbol": request.symbol,
                "volume": float(request.volume),
                "type": self._order_type(connector, request.side, request.order_type),
                "price": self._round_price(entry, digits),
                "sl": self._round_price(stop, digits),
                "tp": self._round_price(target, digits) if target is not None else 0.0,
                "deviation": request.max_slippage_points,
                "magic": DEMO_TEST_MAGIC,
                "comment": "AAA copy test open",
                "type_time": int(getattr(connector, "ORDER_TIME_GTC", 0)),
            }
            broker_result = self._checked_send(
                connector,
                trade_request,
                pending=is_pending,
            )
            if broker_result is None or int(getattr(broker_result, "retcode", -1)) not in (
                self._success_retcodes(connector)
            ):
                raise ValueError(self._result_error(broker_result))
            order_ticket = int(getattr(broker_result, "order", 0))
            deal_ticket = int(getattr(broker_result, "deal", 0))
            if is_pending and order_ticket <= 0:
                raise ValueError(
                    "The broker accepted the pending test without an order ticket; "
                    "verify the MT5 Orders tab immediately."
                )
            accepted_id = order_ticket or deal_ticket
            order_kind = "pending order" if is_pending else "position"
            message = f"Demo {order_kind} {accepted_id} placed and left open in MT5."
            outcome = DemoOrderOutcome(
                success=True,
                message=message,
                broker_order_id=str(order_ticket) if order_ticket else "",
                broker_deal_id=str(deal_ticket) if deal_ticket else "",
                executed_price=Decimal(str(getattr(broker_result, "price", entry))),
                broker_retcode=int(getattr(broker_result, "retcode", 0)),
            )
            record_audit(
                session,
                actor=actor,
                action="copy_test.demo_order_placed",
                target_type="account",
                target_id=account.id,
                message=message,
                details={
                    "symbol": request.symbol,
                    "volume": str(request.volume),
                    "order": outcome.broker_order_id,
                    "deal": outcome.broker_deal_id,
                    "left_open": True,
                },
            )
            return outcome
        except (OSError, RuntimeError, TypeError, ValueError) as exc:
            message = str(exc) or "Unknown demo-order execution error."
            record_audit(
                session,
                actor=actor,
                action="copy_test.demo_order_failed",
                target_type="account",
                target_id=account.id,
                severity=AuditSeverity.WARNING,
                message=message,
                details={
                    "broker_retcode": getattr(broker_result, "retcode", None),
                    "broker_order": getattr(broker_result, "order", None),
                },
            )
            return DemoOrderOutcome(
                success=False,
                message=message,
                broker_order_id=str(getattr(broker_result, "order", "") or ""),
                broker_deal_id=str(getattr(broker_result, "deal", "") or ""),
                broker_retcode=getattr(broker_result, "retcode", None),
            )
        finally:
            with suppress(AttributeError, RuntimeError):
                connector.shutdown()
