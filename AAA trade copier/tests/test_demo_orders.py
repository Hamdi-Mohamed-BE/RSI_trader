from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session, sessionmaker

from trade_copier.domain.enums import OrderType, Side
from trade_copier.models import Account
from trade_copier.services.credentials import MemoryCredentialVault
from trade_copier.services.demo_orders import DemoOrderExecutor, DemoOrderRequest


class FakeMt5:
    ACCOUNT_TRADE_MODE_DEMO = 0
    TRADE_ACTION_DEAL = 1
    TRADE_ACTION_PENDING = 5
    TRADE_ACTION_REMOVE = 8
    ORDER_TYPE_BUY = 0
    ORDER_TYPE_SELL = 1
    ORDER_TYPE_BUY_LIMIT = 2
    ORDER_TYPE_SELL_LIMIT = 3
    ORDER_TYPE_BUY_STOP = 4
    ORDER_TYPE_SELL_STOP = 5
    ORDER_TIME_GTC = 0
    ORDER_FILLING_FOK = 0
    ORDER_FILLING_IOC = 1
    ORDER_FILLING_RETURN = 2
    TRADE_RETCODE_PLACED = 10008
    TRADE_RETCODE_DONE = 10009
    TRADE_RETCODE_DONE_PARTIAL = 10010
    TRADE_RETCODE_INVALID_FILL = 10030

    def __init__(self, *, login: int = 472077113, trade_mode: int = 0) -> None:
        self.login_number = login
        self.trade_mode = trade_mode
        self.sent: list[dict[str, object]] = []
        self.shutdown_called = False
        self.reject_order = False

    def initialize(self, path: str, *, timeout: int, portable: bool) -> bool:
        return bool(path and timeout and portable)

    def login(self, login: int, *, password: str, server: str, timeout: int) -> bool:
        return login == self.login_number and bool(password and server and timeout)

    def account_info(self) -> SimpleNamespace:
        return SimpleNamespace(login=self.login_number, trade_mode=self.trade_mode)

    @staticmethod
    def terminal_info() -> SimpleNamespace:
        return SimpleNamespace(connected=True, tradeapi_disabled=False)

    @staticmethod
    def symbol_select(symbol: str, selected: bool) -> bool:
        return bool(symbol and selected)

    @staticmethod
    def symbol_info(symbol: str) -> SimpleNamespace:
        del symbol
        return SimpleNamespace(digits=2)

    @staticmethod
    def symbol_info_tick(symbol: str) -> SimpleNamespace:
        del symbol
        return SimpleNamespace(bid=4349.90, ask=4350.10)

    @staticmethod
    def order_check(request: dict[str, object]) -> SimpleNamespace:
        del request
        return SimpleNamespace(retcode=0, comment="Done")

    def order_send(self, request: dict[str, object]) -> SimpleNamespace:
        self.sent.append(request)
        if self.reject_order:
            return SimpleNamespace(retcode=10006, comment="Request rejected", order=0, deal=0)
        if request["action"] == self.TRADE_ACTION_PENDING:
            return SimpleNamespace(
                retcode=self.TRADE_RETCODE_PLACED,
                comment="Placed",
                order=234,
                deal=0,
                price=request["price"],
                volume=request["volume"],
            )
        return SimpleNamespace(
            retcode=self.TRADE_RETCODE_DONE,
            comment="Done",
            order=123,
            deal=456,
            price=request["price"],
            volume=request["volume"],
        )

    def shutdown(self) -> None:
        self.shutdown_called = True

    @staticmethod
    def last_error() -> tuple[int, str]:
        return (0, "Done")


def build_account(
    session: Session,
    tmp_path: Path,
    vault: MemoryCredentialVault,
    *,
    trade_mode: str = "demo",
) -> Account:
    terminal = tmp_path / "terminal64.exe"
    terminal.touch()
    account = Account(
        display_name="Follower 472077113",
        login="472077113",
        broker_server="Exness-MT5Trial16",
        terminal_path=str(terminal),
        credential_ref=vault.store("demo-password"),
        trade_mode=trade_mode,
    )
    session.add(account)
    session.flush()
    return account


def request(order_type: OrderType = OrderType.MARKET) -> DemoOrderRequest:
    return DemoOrderRequest(
        side=Side.BUY,
        order_type=order_type,
        symbol="XAUUSDm",
        volume=Decimal("0.05"),
        entry_price=Decimal("4320"),
        stop_loss=Decimal("4310"),
        take_profit=None,
        max_slippage_points=30,
    )


def test_market_demo_order_is_placed_and_left_open(
    client: TestClient,
    session_factory: sessionmaker[Session],
    tmp_path: Path,
) -> None:
    del client
    vault = MemoryCredentialVault()
    connector = FakeMt5()
    with session_factory() as session:
        account = build_account(session, tmp_path, vault)
        outcome = DemoOrderExecutor(
            vault=vault,
            mt5_module=connector,
            platform_name="nt",
        ).execute(session, account, request(), actor="test")

        assert outcome.success is True
        assert outcome.broker_order_id == "123"
        assert outcome.broker_deal_id == "456"
        assert outcome.cleanup_id == ""
        assert "left open" in outcome.message
        assert [item["comment"] for item in connector.sent] == ["AAA copy test open"]
        assert connector.shutdown_called is True


def test_pending_demo_order_is_placed_and_left_active(
    client: TestClient,
    session_factory: sessionmaker[Session],
    tmp_path: Path,
) -> None:
    del client
    vault = MemoryCredentialVault()
    connector = FakeMt5()
    with session_factory() as session:
        account = build_account(session, tmp_path, vault)
        outcome = DemoOrderExecutor(
            vault=vault,
            mt5_module=connector,
            platform_name="nt",
        ).execute(session, account, request(OrderType.LIMIT), actor="test")

        assert outcome.success is True
        assert outcome.broker_order_id == "234"
        assert outcome.cleanup_id == ""
        assert "left open" in outcome.message
        assert [item["action"] for item in connector.sent] == [
            connector.TRADE_ACTION_PENDING
        ]


def test_live_account_order_is_blocked(
    client: TestClient,
    session_factory: sessionmaker[Session],
    tmp_path: Path,
) -> None:
    del client
    vault = MemoryCredentialVault()
    connector = FakeMt5(trade_mode=1)
    with session_factory() as session:
        account = build_account(session, tmp_path, vault, trade_mode="live")
        outcome = DemoOrderExecutor(
            vault=vault,
            mt5_module=connector,
            platform_name="nt",
        ).execute(session, account, request(), actor="test")

        assert outcome.success is False
        assert "blocked on live accounts" in outcome.message
        assert connector.sent == []


def test_broker_rejection_is_reported_without_a_second_request(
    client: TestClient,
    session_factory: sessionmaker[Session],
    tmp_path: Path,
) -> None:
    del client
    vault = MemoryCredentialVault()
    connector = FakeMt5()
    connector.reject_order = True
    with session_factory() as session:
        account = build_account(session, tmp_path, vault)
        outcome = DemoOrderExecutor(
            vault=vault,
            mt5_module=connector,
            platform_name="nt",
        ).execute(session, account, request(), actor="test")

        assert outcome.success is False
        assert "10006" in outcome.message
        assert outcome.broker_order_id == ""
        assert len(connector.sent) == 1
