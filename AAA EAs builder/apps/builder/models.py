from decimal import Decimal

from django.conf import settings
from django.db import models

from apps.ai_config.models import WorkflowDefinition
from apps.core.models import TimeStampedModel


class ProjectQuerySet(models.QuerySet):
    def for_user(self, user):
        return self.filter(owner=user)

    def active(self):
        return self.exclude(status=Project.Status.ARCHIVED)


class Project(TimeStampedModel):
    class ArtifactType(models.TextChoices):
        MT5_EA = "mt5_ea", "MT5 Expert Advisor"
        MT5_INDICATOR = "mt5_indicator", "MT5 Indicator"
        PINE_STRATEGY = "pine_strategy", "Pine Strategy"
        PINE_INDICATOR = "pine_indicator", "Pine Indicator"

    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        READY = "ready", "Ready"
        ARCHIVED = "archived", "Archived"

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="projects"
    )
    name = models.CharField(max_length=160)
    artifact_type = models.CharField(max_length=32, choices=ArtifactType.choices)
    symbol = models.CharField(max_length=32, blank=True, default="EURUSD")
    timeframe = models.CharField(max_length=16, blank=True, default="H1")
    description = models.TextField(help_text="Describe the trading rules in plain language.")
    strategy_spec = models.JSONField(default=dict, blank=True)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.DRAFT)

    objects = ProjectQuerySet.as_manager()

    class Meta:
        ordering = ("-updated_at",)
        indexes = [models.Index(fields=("owner", "status", "-updated_at"))]

    def __str__(self) -> str:
        return self.name

    @property
    def latest_code_version(self):
        return self.code_versions.order_by("-version").first()


class Generation(TimeStampedModel):
    class Status(models.TextChoices):
        QUEUED = "queued", "Queued"
        RUNNING = "running", "Running"
        NEEDS_INPUT = "needs_input", "Needs input"
        SUCCEEDED = "succeeded", "Succeeded"
        FAILED = "failed", "Failed"
        CANCELLED = "cancelled", "Cancelled"

    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="generations")
    workflow = models.ForeignKey(
        WorkflowDefinition,
        on_delete=models.PROTECT,
        related_name="generations",
        null=True,
        blank=True,
    )
    workflow_snapshot = models.JSONField(default=dict, blank=True)
    prompt = models.TextField()
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.QUEUED)
    current_step = models.CharField(max_length=120, blank=True)
    progress = models.PositiveSmallIntegerField(default=0)
    input_tokens = models.PositiveIntegerField(default=0)
    output_tokens = models.PositiveIntegerField(default=0)
    estimated_cost_usd = models.DecimalField(
        max_digits=10, decimal_places=4, default=Decimal("0.0000")
    )
    error_summary = models.TextField(blank=True)

    class Meta:
        ordering = ("-created_at",)
        indexes = [models.Index(fields=("project", "status", "-created_at"))]

    def __str__(self) -> str:
        return f"{self.project.name} · {self.get_status_display()}"


class CodeVersion(TimeStampedModel):
    class ValidationStatus(models.TextChoices):
        NOT_RUN = "not_run", "Not run"
        PASSED = "passed", "Passed"
        WARNINGS = "warnings", "Passed with warnings"
        FAILED = "failed", "Failed"

    class CompilationStatus(models.TextChoices):
        NOT_REQUESTED = "not_requested", "Not requested"
        NOT_APPLICABLE = "not_applicable", "Not applicable"
        UNAVAILABLE = "unavailable", "Compiler unavailable"
        PASSED = "passed", "Compiled"
        FAILED = "failed", "Compilation failed"

    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="code_versions")
    generation = models.OneToOneField(
        Generation,
        on_delete=models.SET_NULL,
        related_name="code_version",
        null=True,
        blank=True,
    )
    version = models.PositiveIntegerField()
    filename = models.CharField(max_length=180)
    language = models.CharField(max_length=32)
    source_code = models.TextField()
    explanation = models.TextField(blank=True)
    assumptions = models.JSONField(default=list, blank=True)
    validation_status = models.CharField(
        max_length=16, choices=ValidationStatus.choices, default=ValidationStatus.NOT_RUN
    )
    diagnostics = models.JSONField(default=list, blank=True)
    source_hash = models.CharField(max_length=64, blank=True)
    compilation_status = models.CharField(
        max_length=20,
        choices=CompilationStatus.choices,
        default=CompilationStatus.NOT_REQUESTED,
    )
    compiler_output = models.TextField(blank=True)
    compiled_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ("-version",)
        constraints = [
            models.UniqueConstraint(fields=("project", "version"), name="unique_project_version")
        ]

    def __str__(self) -> str:
        return f"{self.project.name} v{self.version}"


class GenerationChatMessage(TimeStampedModel):
    class Role(models.TextChoices):
        USER = "user", "User"
        ASSISTANT = "assistant", "Assistant"

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        RUNNING = "running", "Running"
        COMPLETED = "completed", "Completed"
        FAILED = "failed", "Failed"

    generation = models.ForeignKey(
        Generation, on_delete=models.CASCADE, related_name="chat_messages"
    )
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="generation_chat_messages",
    )
    role = models.CharField(max_length=16, choices=Role.choices)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.COMPLETED)
    content = models.TextField(blank=True)
    context_snapshot = models.JSONField(default=dict, blank=True)
    input_tokens = models.PositiveIntegerField(default=0)
    output_tokens = models.PositiveIntegerField(default=0)
    error_summary = models.TextField(blank=True)

    class Meta:
        ordering = ("created_at",)
        indexes = [models.Index(fields=("generation", "created_at"))]

    def __str__(self) -> str:
        return f"{self.generation.project.name} · {self.get_role_display()}"


class CodeRevisionProposal(TimeStampedModel):
    class Status(models.TextChoices):
        PROPOSED = "proposed", "Proposed"
        APPLIED = "applied", "Applied"
        DISMISSED = "dismissed", "Dismissed"

    generation = models.ForeignKey(
        Generation, on_delete=models.CASCADE, related_name="code_proposals"
    )
    assistant_message = models.OneToOneField(
        GenerationChatMessage, on_delete=models.CASCADE, related_name="proposal"
    )
    base_version = models.ForeignKey(
        CodeVersion, on_delete=models.PROTECT, related_name="revision_proposals"
    )
    source_code = models.TextField()
    explanation = models.TextField(blank=True)
    change_summary = models.JSONField(default=list, blank=True)
    diagnostics = models.JSONField(default=list, blank=True)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.PROPOSED)
    applied_version = models.ForeignKey(
        CodeVersion,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="applied_from_proposals",
    )

    class Meta:
        ordering = ("-created_at",)

    def __str__(self) -> str:
        return f"Proposal for {self.base_version}"
