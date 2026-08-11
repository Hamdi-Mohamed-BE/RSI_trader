from dataclasses import dataclass
from typing import Any

from django.conf import settings

from apps.ai_config.models import AgentDefinition
from apps.ai_config.services.invocation import invoke_agent_structured
from apps.builder.models import CodeVersion, Generation, GenerationChatMessage

from .schemas import GenerationCopilotResponse
from .validators import strip_markdown_fences, validate_source


class GenerationChatError(RuntimeError):
    """Raised when the project-aware copilot cannot answer safely."""


@dataclass(frozen=True)
class ChatResult:
    reply: str
    input_tokens: int
    output_tokens: int
    context_snapshot: dict[str, Any]
    base_version: CodeVersion | None
    proposed_source_code: str | None
    proposal_explanation: str
    change_summary: list[str]
    diagnostics: list[dict[str, str]]


def _get_copilot_agent() -> AgentDefinition:
    agent = (
        AgentDefinition.objects.select_related("prompt", "primary_model__gateway")
        .filter(
            key="generation-copilot",
            published=True,
            prompt__published=True,
            primary_model__enabled=True,
            primary_model__gateway__enabled=True,
        )
        .order_by("-version")
        .first()
    )
    if agent is None:
        raise GenerationChatError("No published generation copilot is available.")
    return agent


def _conversation_history(
    generation: Generation, assistant_message: GenerationChatMessage
) -> list[dict[str, str]]:
    recent = list(
        generation.chat_messages.filter(status=GenerationChatMessage.Status.COMPLETED)
        .exclude(pk=assistant_message.pk)
        .order_by("-created_at")[:20]
    )
    recent.reverse()
    return [
        {"role": message.role, "content": message.content[:8_000]}
        for message in recent
        if message.content
    ]


def _build_context(
    generation: Generation, assistant_message: GenerationChatMessage
) -> tuple[dict[str, Any], CodeVersion | None, dict[str, Any]]:
    project = generation.project
    latest_version = project.code_versions.order_by("-version").first()
    versions = list(
        project.code_versions.order_by("-version").values(
            "version",
            "filename",
            "language",
            "validation_status",
            "compilation_status",
            "source_hash",
            "created_at",
        )[:10]
    )
    context = {
        "project": {
            "name": project.name,
            "artifact_type": project.artifact_type,
            "symbol": project.symbol,
            "timeframe": project.timeframe,
            "description": project.description,
            "strategy_specification": project.strategy_spec,
            "status": project.status,
        },
        "generation": {
            "id": str(generation.pk),
            "status": generation.status,
            "current_step": generation.current_step,
            "progress_percent": generation.progress,
            "prompt": generation.prompt,
            "input_tokens": generation.input_tokens,
            "output_tokens": generation.output_tokens,
            "error_summary": generation.error_summary,
            "workflow_snapshot": generation.workflow_snapshot,
        },
        "latest_code": (
            {
                "version": latest_version.version,
                "filename": latest_version.filename,
                "language": latest_version.language,
                "source_hash": latest_version.source_hash,
                "source_code": latest_version.source_code[: settings.CHAT_MAX_SOURCE_CHARS],
                "explanation": latest_version.explanation,
                "assumptions": latest_version.assumptions,
                "validation_status": latest_version.validation_status,
                "diagnostics": latest_version.diagnostics,
                "compilation_status": latest_version.compilation_status,
                "compiler_output": latest_version.compiler_output[-10_000:],
            }
            if latest_version
            else None
        ),
        "version_history": versions,
        "conversation": _conversation_history(generation, assistant_message),
        "response_rules": {
            "proposal_requires_complete_source": True,
            "proposal_is_not_applied_automatically": True,
            "never_claim_unverified_compilation_or_performance": True,
        },
    }
    snapshot = {
        "generation_status": generation.status,
        "generation_progress": generation.progress,
        "workflow_key": generation.workflow_snapshot.get("workflow_key", ""),
        "workflow_version": generation.workflow_snapshot.get("workflow_version"),
        "code_version": latest_version.version if latest_version else None,
        "source_hash": latest_version.source_hash if latest_version else "",
        "validation_status": latest_version.validation_status if latest_version else "",
        "compilation_status": latest_version.compilation_status if latest_version else "",
        "diagnostic_count": len(latest_version.diagnostics) if latest_version else 0,
    }
    return context, latest_version, snapshot


def answer_generation_chat(assistant_message: GenerationChatMessage) -> ChatResult:
    generation = Generation.objects.select_related("project", "workflow").get(
        pk=assistant_message.generation_id
    )
    context, latest_version, snapshot = _build_context(generation, assistant_message)
    response = invoke_agent_structured(_get_copilot_agent(), GenerationCopilotResponse, context)

    proposed_source: str | None = None
    diagnostics: list[dict[str, str]] = []
    if response.parsed.proposed_source_code and latest_version is not None:
        proposed_source = strip_markdown_fences(response.parsed.proposed_source_code)
        if proposed_source != latest_version.source_code:
            diagnostics = validate_source(generation.project, proposed_source).diagnostics
        else:
            proposed_source = None

    return ChatResult(
        reply=response.parsed.reply,
        input_tokens=response.input_tokens,
        output_tokens=response.output_tokens,
        context_snapshot=snapshot,
        base_version=latest_version,
        proposed_source_code=proposed_source,
        proposal_explanation=response.parsed.reply,
        change_summary=response.parsed.change_summary,
        diagnostics=diagnostics,
    )


def dispatch_chat_response(assistant_message: GenerationChatMessage) -> None:
    from apps.builder.tasks import respond_to_generation_chat

    if settings.GENERATION_RUN_INLINE:
        respond_to_generation_chat.apply(args=[str(assistant_message.pk)], throw=False)
    else:
        respond_to_generation_chat.delay(str(assistant_message.pk))
