import json
from dataclasses import dataclass
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel

from apps.ai_config.models import AgentDefinition
from apps.ai_config.services.model_factory import build_chat_model


class AgentInvocationError(RuntimeError):
    """Raised when a configured agent does not return its required schema."""


@dataclass(frozen=True)
class StructuredInvocation[SchemaType: BaseModel]:
    parsed: SchemaType
    input_tokens: int
    output_tokens: int


def invoke_agent_structured[SchemaType: BaseModel](
    agent: AgentDefinition,
    schema: type[SchemaType],
    payload: dict[str, Any],
) -> StructuredInvocation[SchemaType]:
    model = build_chat_model(
        agent.primary_model,
        max_output_tokens=agent.max_output_tokens,
    )
    runnable = model.with_structured_output(schema, include_raw=True)
    response = runnable.invoke(
        [
            SystemMessage(content=agent.prompt.system_prompt),
            HumanMessage(content=json.dumps(payload, ensure_ascii=False, default=str)),
        ]
    )
    if not isinstance(response, dict) or response.get("parsed") is None:
        raise AgentInvocationError(f"The {agent.name} returned an invalid response.")

    parsed = schema.model_validate(response["parsed"])
    usage = getattr(response.get("raw"), "usage_metadata", None) or {}
    return StructuredInvocation(
        parsed=parsed,
        input_tokens=int(usage.get("input_tokens", 0)),
        output_tokens=int(usage.get("output_tokens", 0)),
    )
