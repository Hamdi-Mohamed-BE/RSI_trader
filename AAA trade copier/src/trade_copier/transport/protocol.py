import json
from typing import Any

from pydantic import ValidationError

from ..domain.messages import ExecutionAck, FollowerCommand, SourceTradeMessage


class ProtocolError(ValueError):
    pass


def encode_message(message: SourceTradeMessage | FollowerCommand | ExecutionAck) -> bytes:
    return f"{message.model_dump_json()}\n".encode()


def decode_message(payload: bytes) -> SourceTradeMessage | FollowerCommand | ExecutionAck:
    try:
        data: dict[str, Any] = json.loads(payload.decode().strip())
        message_type = data.get("message_type")
        if message_type == "source_trade":
            return SourceTradeMessage.model_validate(data)
        if message_type == "follower_command":
            return FollowerCommand.model_validate(data)
        if message_type == "execution_ack":
            return ExecutionAck.model_validate(data)
    except (UnicodeDecodeError, json.JSONDecodeError, ValidationError) as exc:
        raise ProtocolError("Invalid copier message.") from exc
    raise ProtocolError("Unknown copier message type.")
