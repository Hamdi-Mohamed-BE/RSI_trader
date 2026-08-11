import hashlib

from django.db import transaction
from django.db.models import Max

from apps.builder.models import CodeRevisionProposal, CodeVersion, Project

from .compiler import CompilationResult, compile_mql5_source
from .validators import validate_source


class ProposalApplicationError(ValueError):
    """Raised when a chat proposal cannot be applied as a new immutable version."""


def _compile_proposal(
    proposal: CodeRevisionProposal, validation_status: str, filename: str, source_code: str
) -> CompilationResult:
    is_mql5 = proposal.generation.project.artifact_type in {
        Project.ArtifactType.MT5_EA,
        Project.ArtifactType.MT5_INDICATOR,
    }
    if not is_mql5:
        return CompilationResult(
            CodeVersion.CompilationStatus.NOT_APPLICABLE,
            "MetaEditor compilation applies only to MQL5 artifacts.",
        )
    if validation_status == CodeVersion.ValidationStatus.FAILED:
        return CompilationResult(
            CodeVersion.CompilationStatus.NOT_REQUESTED,
            "Compilation skipped because validation errors remain.",
        )
    return compile_mql5_source(
        generation_id=f"proposal-{proposal.pk}",
        filename=filename,
        source_code=source_code,
    )


def apply_code_proposal(proposal: CodeRevisionProposal) -> CodeVersion:
    if proposal.status != CodeRevisionProposal.Status.PROPOSED:
        raise ProposalApplicationError("This proposal is no longer available to apply.")

    outcome = validate_source(proposal.generation.project, proposal.source_code)
    compilation = _compile_proposal(proposal, outcome.status, outcome.filename, outcome.source_code)

    with transaction.atomic():
        locked_proposal = (
            CodeRevisionProposal.objects.select_for_update()
            .select_related("generation__project")
            .get(pk=proposal.pk)
        )
        if locked_proposal.status != CodeRevisionProposal.Status.PROPOSED:
            raise ProposalApplicationError("This proposal was already handled.")

        project = Project.objects.select_for_update().get(pk=locked_proposal.generation.project_id)
        next_version = (project.code_versions.aggregate(highest=Max("version"))["highest"] or 0) + 1
        code_version = CodeVersion.objects.create(
            project=project,
            version=next_version,
            filename=outcome.filename,
            language=outcome.language,
            source_code=outcome.source_code,
            explanation=locked_proposal.explanation,
            assumptions=["Applied from a project-aware chat proposal after explicit user review."],
            validation_status=outcome.status,
            diagnostics=outcome.diagnostics,
            source_hash=hashlib.sha256(outcome.source_code.encode()).hexdigest(),
            compilation_status=compilation.status,
            compiler_output=compilation.output,
            compiled_at=compilation.compiled_at,
        )
        locked_proposal.status = CodeRevisionProposal.Status.APPLIED
        locked_proposal.applied_version = code_version
        locked_proposal.save(update_fields=("status", "applied_version", "updated_at"))
    return code_version
