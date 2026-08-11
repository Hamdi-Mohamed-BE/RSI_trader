from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import models

from apps.core.models import TimeStampedModel

from .services.encryption import decrypt_secret, encrypt_secret, secret_fingerprint


class Gateway(TimeStampedModel):
    class Provider(models.TextChoices):
        OPENAI = "openai", "OpenAI"
        ANTHROPIC = "anthropic", "Anthropic"
        GOOGLE = "google", "Google"
        OPENAI_COMPATIBLE = "openai_compatible", "OpenAI-compatible"

    class Health(models.TextChoices):
        UNKNOWN = "unknown", "Unknown"
        PENDING = "pending", "Pending"
        HEALTHY = "healthy", "Healthy"
        UNHEALTHY = "unhealthy", "Unhealthy"

    name = models.CharField(max_length=120)
    key = models.SlugField(unique=True, help_text="Stable internal identifier used by workflows.")
    provider = models.CharField(max_length=32, choices=Provider.choices)
    base_url = models.URLField(blank=True)
    enabled = models.BooleanField(default=False)
    priority = models.PositiveSmallIntegerField(default=100)
    timeout_seconds = models.PositiveSmallIntegerField(default=60)
    max_concurrency = models.PositiveSmallIntegerField(default=2)
    daily_budget_usd = models.DecimalField(
        max_digits=10, decimal_places=2, default=Decimal("10.00")
    )
    extra_config = models.JSONField(default=dict, blank=True)
    encrypted_api_key = models.TextField(blank=True, editable=False)
    api_key_fingerprint = models.CharField(max_length=12, blank=True, editable=False)
    health = models.CharField(max_length=16, choices=Health.choices, default=Health.UNKNOWN)
    last_tested_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ("priority", "name")

    def __str__(self) -> str:
        return f"{self.name} ({self.get_provider_display()})"

    @property
    def has_api_key(self) -> bool:
        return bool(self.encrypted_api_key)

    def set_api_key(self, value: str) -> None:
        self.encrypted_api_key = encrypt_secret(value)
        self.api_key_fingerprint = secret_fingerprint(value)

    def get_api_key(self) -> str:
        return decrypt_secret(self.encrypted_api_key)


class AIModel(TimeStampedModel):
    gateway = models.ForeignKey(Gateway, on_delete=models.PROTECT, related_name="models")
    name = models.CharField(max_length=120)
    key = models.SlugField(unique=True)
    provider_model_id = models.CharField(max_length=160)
    enabled = models.BooleanField(default=False)
    supports_structured_output = models.BooleanField(default=True)
    supports_tools = models.BooleanField(default=True)
    supports_streaming = models.BooleanField(default=True)
    max_input_tokens = models.PositiveIntegerField(null=True, blank=True)
    max_output_tokens = models.PositiveIntegerField(default=8192)
    default_parameters = models.JSONField(default=dict, blank=True)
    input_cost_per_million = models.DecimalField(
        max_digits=10, decimal_places=4, null=True, blank=True
    )
    output_cost_per_million = models.DecimalField(
        max_digits=10, decimal_places=4, null=True, blank=True
    )
    fallback_model = models.ForeignKey(
        "self", on_delete=models.SET_NULL, null=True, blank=True, related_name="fallback_for"
    )

    class Meta:
        ordering = ("gateway__priority", "name")
        constraints = [
            models.UniqueConstraint(
                fields=("gateway", "provider_model_id"), name="unique_gateway_model_id"
            )
        ]

    def __str__(self) -> str:
        return f"{self.name} via {self.gateway.name}"

    def clean(self) -> None:
        if self.fallback_model_id == self.id:
            raise ValidationError({"fallback_model": "A model cannot be its own fallback."})


class PromptVersion(TimeStampedModel):
    name = models.CharField(max_length=120)
    key = models.SlugField()
    version = models.PositiveIntegerField(default=1)
    purpose = models.CharField(max_length=160)
    system_prompt = models.TextField()
    published = models.BooleanField(default=False)

    class Meta:
        ordering = ("key", "-version")
        constraints = [
            models.UniqueConstraint(fields=("key", "version"), name="unique_prompt_version")
        ]

    def __str__(self) -> str:
        return f"{self.name} v{self.version}"


class AgentDefinition(TimeStampedModel):
    name = models.CharField(max_length=120)
    key = models.SlugField()
    version = models.PositiveIntegerField(default=1)
    purpose = models.TextField()
    prompt = models.ForeignKey(PromptVersion, on_delete=models.PROTECT, related_name="agents")
    primary_model = models.ForeignKey(
        AIModel, on_delete=models.PROTECT, related_name="primary_agents"
    )
    fallback_model = models.ForeignKey(
        AIModel,
        on_delete=models.PROTECT,
        related_name="fallback_agents",
        null=True,
        blank=True,
    )
    allowed_tools = models.JSONField(default=list, blank=True)
    input_schema = models.JSONField(default=dict, blank=True)
    output_schema = models.JSONField(default=dict, blank=True)
    max_iterations = models.PositiveSmallIntegerField(default=3)
    max_output_tokens = models.PositiveIntegerField(default=8192)
    timeout_seconds = models.PositiveSmallIntegerField(default=120)
    published = models.BooleanField(default=False)

    class Meta:
        ordering = ("key", "-version")
        constraints = [
            models.UniqueConstraint(fields=("key", "version"), name="unique_agent_version")
        ]

    def __str__(self) -> str:
        return f"{self.name} v{self.version}"

    def clean(self) -> None:
        if self.fallback_model_id and self.fallback_model_id == self.primary_model_id:
            raise ValidationError({"fallback_model": "Choose a different fallback model."})


class WorkflowDefinition(TimeStampedModel):
    name = models.CharField(max_length=120)
    key = models.SlugField()
    version = models.PositiveIntegerField(default=1)
    supported_artifacts = models.JSONField(default=list)
    graph = models.JSONField(
        default=dict, help_text="Validated LangGraph node and edge definition."
    )
    max_repair_loops = models.PositiveSmallIntegerField(default=2)
    token_budget = models.PositiveIntegerField(default=50000)
    cost_budget_usd = models.DecimalField(max_digits=8, decimal_places=2, default=Decimal("2.00"))
    published = models.BooleanField(default=False)

    class Meta:
        ordering = ("key", "-version")
        constraints = [
            models.UniqueConstraint(fields=("key", "version"), name="unique_workflow_version")
        ]

    def __str__(self) -> str:
        return f"{self.name} v{self.version}"
