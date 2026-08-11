import asyncio
import os

from ..domain.enums import JobStatus
from ..domain.messages import ExecutionAck, FollowerCommand
from .protocol import ProtocolError, decode_message, encode_message
from .windows_pipe_io import DuplexPipeChannel


class WindowsNamedPipeTransport:
    """Guarded adapter for a connected executor pipe.

    The production connection supervisor will own persistent handles. This adapter
    intentionally rejects when a verified handle has not been registered; it never
    falls back to an untested network or file transport.
    """

    def __init__(
        self, *, live_execution_permitted: bool = False, timeout_seconds: float = 5
    ) -> None:
        self.live_execution_permitted = live_execution_permitted
        self.timeout_seconds = timeout_seconds
        self._handles: dict[str, DuplexPipeChannel] = {}
        self._locks: dict[str, asyncio.Lock] = {}

    def register_verified_handle(self, account_id: str, handle: DuplexPipeChannel) -> None:
        if os.name != "nt":
            raise RuntimeError("Named pipes are supported only on Windows.")
        self._handles[account_id] = handle
        self._locks.setdefault(account_id, asyncio.Lock())

    def is_connected(self, account_id: str) -> bool:
        return account_id in self._handles

    def unregister(self, account_id: str) -> None:
        channel = self._handles.pop(account_id, None)
        self._locks.pop(account_id, None)
        if channel is not None:
            channel.close()

    async def send(self, command: FollowerCommand) -> ExecutionAck:
        account_id = str(command.follower_account_id)
        if not self.live_execution_permitted:
            return ExecutionAck(
                job_uid=command.job_uid,
                follower_account_id=command.follower_account_id,
                status=JobStatus.REJECTED,
                error="Live named-pipe execution is disabled by the environment safety gates.",
            )
        if account_id not in self._handles:
            return ExecutionAck(
                job_uid=command.job_uid,
                follower_account_id=command.follower_account_id,
                status=JobStatus.REJECTED,
                error="Follower named pipe is not connected and verified.",
            )
        channel = self._handles[account_id]
        lock = self._locks[account_id]
        try:
            async with lock:
                payload = await asyncio.wait_for(
                    asyncio.to_thread(channel.exchange, encode_message(command)),
                    timeout=self.timeout_seconds,
                )
            response = decode_message(payload)
            if not isinstance(response, ExecutionAck):
                raise ProtocolError("Follower returned a non-acknowledgement message.")
            if response.job_uid != command.job_uid:
                raise ProtocolError("Follower acknowledgement has the wrong job ID.")
            if response.follower_account_id != command.follower_account_id:
                raise ProtocolError("Follower acknowledgement has the wrong account ID.")
            return response
        except (TimeoutError, OSError, ConnectionError, ProtocolError, ValueError) as exc:
            self.unregister(account_id)
            return ExecutionAck(
                job_uid=command.job_uid,
                follower_account_id=command.follower_account_id,
                status=JobStatus.FAILED,
                error=f"Follower pipe exchange failed: {exc}",
            )
