from django.contrib import admin
from unfold.admin import ModelAdmin

from .models import CodeRevisionProposal, CodeVersion, Generation, GenerationChatMessage, Project


@admin.register(Project)
class ProjectAdmin(ModelAdmin):
    list_display = ("name", "owner", "artifact_type", "symbol", "timeframe", "status", "updated_at")
    list_filter = ("artifact_type", "status", "timeframe")
    search_fields = ("name", "owner__email", "symbol", "description")
    autocomplete_fields = ("owner",)


@admin.register(Generation)
class GenerationAdmin(ModelAdmin):
    list_display = (
        "project",
        "status",
        "current_step",
        "progress",
        "estimated_cost_usd",
        "created_at",
    )
    list_filter = ("status", "workflow")
    search_fields = ("project__name", "project__owner__email", "prompt", "error_summary")
    readonly_fields = (
        "input_tokens",
        "output_tokens",
        "estimated_cost_usd",
        "created_at",
        "updated_at",
    )
    autocomplete_fields = ("project", "workflow")


@admin.register(CodeVersion)
class CodeVersionAdmin(ModelAdmin):
    list_display = (
        "project",
        "version",
        "filename",
        "validation_status",
        "compilation_status",
        "created_at",
    )
    list_filter = ("language", "validation_status", "compilation_status")
    search_fields = ("project__name", "filename", "source_code", "source_hash")
    autocomplete_fields = ("project", "generation")
    readonly_fields = ("compiler_output", "compiled_at", "source_hash", "created_at", "updated_at")


@admin.register(GenerationChatMessage)
class GenerationChatMessageAdmin(ModelAdmin):
    list_display = ("generation", "role", "status", "input_tokens", "output_tokens", "created_at")
    list_filter = ("role", "status")
    search_fields = ("generation__project__name", "generation__project__owner__email", "content")
    readonly_fields = (
        "generation",
        "author",
        "role",
        "status",
        "content",
        "context_snapshot",
        "input_tokens",
        "output_tokens",
        "error_summary",
        "created_at",
        "updated_at",
    )


@admin.register(CodeRevisionProposal)
class CodeRevisionProposalAdmin(ModelAdmin):
    list_display = ("base_version", "status", "applied_version", "created_at")
    list_filter = ("status",)
    search_fields = ("generation__project__name", "explanation", "source_code")
    readonly_fields = (
        "generation",
        "assistant_message",
        "base_version",
        "source_code",
        "explanation",
        "change_summary",
        "diagnostics",
        "applied_version",
        "created_at",
        "updated_at",
    )
