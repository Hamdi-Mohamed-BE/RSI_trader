import hashlib
import logging

from celery import shared_task
from django.db import transaction
from django.db.models import Max

from apps.ai_config.services.model_factory import ModelConfigurationError
from apps.builder.models import (
    CodeRevisionProposal,
    CodeVersion,
    Generation,
    GenerationChatMessage,
    Project,
)
from apps.builder.services.chat import GenerationChatError, answer_generation_chat
from apps.builder.services.compiler import CompilationResult, compile_mql5_source
from apps.builder.services.runtime import GenerationRuntime, GenerationRuntimeError
from apps.builder.services.validators import validate_source

logger = logging.getLogger(__name__)


@shared_task(ignore_result=False)
def builder_worker_health() -> dict[str, str]:
    return {"status": "ok", "worker": "builder"}


def _public_error(exc: Exception) -> str:
    if isinstance(exc, (GenerationRuntimeError, ModelConfigurationError)):
        return str(exc)
    return "Generation failed unexpectedly. Check the gateway and worker logs, then retry."


@shared_task(ignore_result=False)
def generate_trading_code(generation_id: str) -> dict[str, str | int]:
    generation = Generation.objects.select_related("project", "workflow").get(pk=generation_id)
    if generation.status == Generation.Status.SUCCEEDED:
        return {"status": generation.status, "generation_id": generation_id}

    generation.status = Generation.Status.RUNNING
    generation.current_step = "Starting AI workflow"
    generation.progress = 5
    generation.error_summary = ""
    generation.save(
        update_fields=("status", "current_step", "progress", "error_summary", "updated_at")
    )

    def report_progress(step: str, progress: int) -> None:
        Generation.objects.filter(pk=generation.pk).update(
            current_step=step,
            progress=min(max(progress, 0), 99),
        )

    try:
        if generation.workflow is None:
            raise GenerationRuntimeError("This run has no pinned workflow.")
        result = GenerationRuntime(generation.workflow, report_progress).run(
            generation.project, generation.prompt
        )
        outcome = validate_source(generation.project, result.source_code)
        diagnostics = outcome.diagnostics
        for diagnostic in result.diagnostics:
            if diagnostic not in diagnostics:
                diagnostics.append(diagnostic)

        if any(item.get("severity") == "error" for item in diagnostics):
            validation_status = CodeVersion.ValidationStatus.FAILED
        elif diagnostics:
            validation_status = CodeVersion.ValidationStatus.WARNINGS
        else:
            validation_status = CodeVersion.ValidationStatus.PASSED

        is_mql5 = generation.project.artifact_type in {
            Project.ArtifactType.MT5_EA,
            Project.ArtifactType.MT5_INDICATOR,
        }
        if not is_mql5:
            compilation = CompilationResult(
                CodeVersion.CompilationStatus.NOT_APPLICABLE,
                "MetaEditor compilation applies only to MQL5 artifacts.",
            )
        elif validation_status == CodeVersion.ValidationStatus.FAILED:
            compilation = CompilationResult(
                CodeVersion.CompilationStatus.NOT_REQUESTED,
                "Compilation skipped because validation errors remain.",
            )
        else:
            compilation = compile_mql5_source(
                generation_id=generation_id,
                filename=outcome.filename,
                source_code=outcome.source_code,
            )

        with transaction.atomic():
            project = Project.objects.select_for_update().get(pk=generation.project_id)
            next_version = (
                project.code_versions.aggregate(highest=Max("version"))["highest"] or 0
            ) + 1
            code_version = CodeVersion.objects.create(
                project=project,
                generation=generation,
                version=next_version,
                filename=outcome.filename,
                language=outcome.language,
                source_code=outcome.source_code,
                explanation=result.explanation,
                assumptions=result.assumptions,
                validation_status=validation_status,
                diagnostics=diagnostics,
                source_hash=hashlib.sha256(outcome.source_code.encode()).hexdigest(),
                compilation_status=compilation.status,
                compiler_output=compilation.output,
                compiled_at=compilation.compiled_at,
            )
            project.strategy_spec = result.specification
            project.status = Project.Status.READY
            project.save(update_fields=("strategy_spec", "status", "updated_at"))

            generation.status = Generation.Status.SUCCEEDED
            generation.current_step = "Generation complete"
            generation.progress = 100
            generation.input_tokens = result.input_tokens
            generation.output_tokens = result.output_tokens
            generation.save(
                update_fields=(
                    "status",
                    "current_step",
                    "progress",
                    "input_tokens",
                    "output_tokens",
                    "updated_at",
                )
            )
        return {
            "status": generation.status,
            "generation_id": generation_id,
            "version": code_version.version,
        }
    except Exception as exc:  # task boundary: every failure must update user-visible state
        logger.error("Generation %s failed with %s", generation_id, type(exc).__name__)
        generation.status = Generation.Status.FAILED
        generation.current_step = "Generation failed"
        generation.error_summary = _public_error(exc)
        generation.save(update_fields=("status", "current_step", "error_summary", "updated_at"))
        return {"status": generation.status, "generation_id": generation_id}


@shared_task(ignore_result=False)
def respond_to_generation_chat(message_id: str) -> dict[str, str | bool]:
    started = GenerationChatMessage.objects.filter(
        pk=message_id,
        role=GenerationChatMessage.Role.ASSISTANT,
        status=GenerationChatMessage.Status.PENDING,
    ).update(status=GenerationChatMessage.Status.RUNNING)
    message = GenerationChatMessage.objects.select_related(
        "generation__project", "generation__workflow"
    ).get(pk=message_id)
    if not started:
        return {
            "status": message.status,
            "message_id": message_id,
            "proposal_created": hasattr(message, "proposal"),
        }

    try:
        result = answer_generation_chat(message)
        with transaction.atomic():
            message.content = result.reply
            message.status = GenerationChatMessage.Status.COMPLETED
            message.input_tokens = result.input_tokens
            message.output_tokens = result.output_tokens
            message.context_snapshot = result.context_snapshot
            message.error_summary = ""
            message.save(
                update_fields=(
                    "content",
                    "status",
                    "input_tokens",
                    "output_tokens",
                    "context_snapshot",
                    "error_summary",
                    "updated_at",
                )
            )
            if result.proposed_source_code is not None and result.base_version is not None:
                proposal_created = True
                CodeRevisionProposal.objects.create(
                    generation=message.generation,
                    assistant_message=message,
                    base_version=result.base_version,
                    source_code=result.proposed_source_code,
                    explanation=result.proposal_explanation,
                    change_summary=result.change_summary,
                    diagnostics=result.diagnostics,
                )
            else:
                proposal_created = False
        return {
            "status": message.status,
            "message_id": message_id,
            "proposal_created": proposal_created,
        }
    except Exception as exc:  # task boundary: return a sanitized user-visible failure
        logger.error("Generation chat message %s failed with %s", message_id, type(exc).__name__)
        message.status = GenerationChatMessage.Status.FAILED
        message.error_summary = (
            str(exc)
            if isinstance(exc, (GenerationChatError, ModelConfigurationError))
            else "The copilot could not answer. Check the AI gateway and try again."
        )
        message.save(update_fields=("status", "error_summary", "updated_at"))
        return {
            "status": message.status,
            "message_id": message_id,
            "proposal_created": False,
        }
