from typing import Protocol

from ..domain.messages import ExecutionAck, FollowerCommand


class FollowerTransport(Protocol):
    async def send(self, command: FollowerCommand) -> ExecutionAck: ...


class TransportRouter:
    def __init__(self, fallback: FollowerTransport) -> None:
        self.fallback = fallback
        self._transports: dict[str, FollowerTransport] = {}

    def register(self, account_id: str, transport: FollowerTransport) -> None:
        self._transports[account_id] = transport

    async def send(self, command: FollowerCommand) -> ExecutionAck:
        transport = self._transports.get(str(command.follower_account_id), self.fallback)
        return await transport.send(command)
