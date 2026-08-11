from decimal import Decimal
from uuid import uuid4

import pytest

from trade_copier.domain.enums import JobStatus, Side, TradeAction
from trade_copier.domain.messages import ExecutionAck, FollowerCommand
from trade_copier.transport.protocol import encode_message
from trade_copier.transport.windows_named_pipe import WindowsNamedPipeTransport


class FakePipeChannel:
    def __init__(self, response: bytes) -> None:
        self.response = response
        self.calls = 0

    def exchange(self, payload: bytes) -> bytes:
        assert payload.endswith(b"\n")
        self.calls += 1
        return self.response

    def close(self) -> None:
        pass


def command() -> FollowerCommand:
    return FollowerCommand(
        job_uid=uuid4(),
        source_event_uid=uuid4(),
        follower_account_id=uuid4(),
        source_order_id="source-order",
        action=TradeAction.MARKET_OPEN,
        side=Side.BUY,
        symbol="XAUUSD",
        volume=Decimal("0.1"),
        entry_price=Decimal("2400"),
        stop_loss=Decimal("2390"),
    )


@pytest.mark.asyncio
async def test_live_pipe_gate_rejects_before_any_io() -> None:
    request = command()
    transport = WindowsNamedPipeTransport(live_execution_permitted=False)
    result = await transport.send(request)
    assert result.status is JobStatus.REJECTED
    assert "safety gates" in result.error


@pytest.mark.asyncio
async def test_verified_pipe_acknowledgement_is_validated() -> None:
    request = command()
    response = ExecutionAck(
        job_uid=request.job_uid,
        follower_account_id=request.follower_account_id,
        status=JobStatus.FILLED,
        filled_price=request.entry_price,
        filled_volume=request.volume,
    )
    channel = FakePipeChannel(encode_message(response))
    transport = WindowsNamedPipeTransport(live_execution_permitted=True)
    transport.register_verified_handle(str(request.follower_account_id), channel)

    result = await transport.send(request)

    assert result.status is JobStatus.FILLED
    assert channel.calls == 1
