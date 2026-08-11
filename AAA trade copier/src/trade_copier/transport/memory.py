from decimal import Decimal

from ..domain.enums import JobStatus
from ..domain.messages import ExecutionAck, FollowerCommand


class RejectingTransport:
    async def send(self, command: FollowerCommand) -> ExecutionAck:
        return ExecutionAck(
            job_uid=command.job_uid,
            follower_account_id=command.follower_account_id,
            status=JobStatus.REJECTED,
            error="No connected follower transport.",
        )


class DemoFollowerTransport:
    def __init__(self, *, slippage_points: Decimal = Decimal("0")) -> None:
        self.slippage_points = slippage_points
        self.commands: list[FollowerCommand] = []

    async def send(self, command: FollowerCommand) -> ExecutionAck:
        self.commands.append(command)
        fill_price = command.entry_price + self.slippage_points
        return ExecutionAck(
            job_uid=command.job_uid,
            follower_account_id=command.follower_account_id,
            status=JobStatus.FILLED,
            broker_order_id=f"DEMO-{str(command.job_uid)[:8]}",
            broker_position_id=f"POS-{str(command.job_uid)[:8]}",
            requested_price=command.entry_price,
            filled_price=fill_price,
            filled_volume=command.volume,
            broker_result_code=10009,
        )
