from django.contrib import admin
from unfold.admin import ModelAdmin

from .forms import GatewayAdminForm
from .models import AgentDefinition, AIModel, Gateway, PromptVersion, WorkflowDefinition


@admin.register(Gateway)
class GatewayAdmin(ModelAdmin):
    form = GatewayAdminForm
    list_display = (
        "name",
        "provider",
        "enabled",
        "health",
        "credential_state",
        "priority",
        "updated_at",
    )
    list_filter = ("provider", "enabled", "health")
    search_fields = ("name", "key", "base_url")
    readonly_fields = (
        "api_key_fingerprint",
        "health",
        "last_tested_at",
        "created_at",
        "updated_at",
    )
    fieldsets = (
        ("Gateway", {"fields": ("name", "key", "provider", "base_url", "enabled")}),
        (
            "Limits",
            {"fields": ("priority", "timeout_seconds", "max_concurrency", "daily_budget_usd")},
        ),
        ("Credential", {"fields": ("api_key", "api_key_fingerprint")}),
        ("Provider options", {"fields": ("extra_config", "notes")}),
        ("Health", {"fields": ("health", "last_tested_at")}),
        ("Audit timestamps", {"fields": ("created_at", "updated_at"), "classes": ("collapse",)}),
    )

    @admin.display(description="Credential", boolean=True)
    def credential_state(self, obj: Gateway) -> bool:
        return obj.has_api_key


@admin.register(AIModel)
class AIModelAdmin(ModelAdmin):
    list_display = ("name", "gateway", "provider_model_id", "enabled", "fallback_model")
    list_filter = ("enabled", "gateway", "supports_structured_output", "supports_tools")
    search_fields = ("name", "key", "provider_model_id")
    autocomplete_fields = ("gateway", "fallback_model")


@admin.register(PromptVersion)
class PromptVersionAdmin(ModelAdmin):
    list_display = ("name", "key", "version", "purpose", "published", "updated_at")
    list_filter = ("published",)
    search_fields = ("name", "key", "purpose", "system_prompt")


@admin.register(AgentDefinition)
class AgentDefinitionAdmin(ModelAdmin):
    list_display = ("name", "key", "version", "primary_model", "published")
    list_filter = ("published", "primary_model__gateway")
    search_fields = ("name", "key", "purpose")
    autocomplete_fields = ("prompt", "primary_model", "fallback_model")


@admin.register(WorkflowDefinition)
class WorkflowDefinitionAdmin(ModelAdmin):
    list_display = ("name", "key", "version", "published", "token_budget", "cost_budget_usd")
    list_filter = ("published",)
    search_fields = ("name", "key")
