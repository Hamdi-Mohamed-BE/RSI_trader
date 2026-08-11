from typing import Any

from django.conf import settings

from apps.ai_config.models import AgentDefinition, WorkflowDefinition
from apps.builder.models import Generation, Project


class GenerationUnavailableError(ValueError):
    """Raised when no published workflow supports a project."""


def find_published_workflow(artifact_type: str) -> WorkflowDefinition | None:
    workflows = WorkflowDefinition.objects.filter(published=True).order_by("key", "-version")
    return next(
        (workflow for workflow in workflows if artifact_type in workflow.supported_artifacts),
        None,
    )


def build_workflow_snapshot(workflow: WorkflowDefinition) -> dict[str, Any]:
    agent_refs = {
        (node.get("agent_key"), node.get("agent_version", 1))
        for node in workflow.graph.get("nodes", [])
        if isinstance(node, dict) and node.get("agent_key")
    }
    agents = AgentDefinition.objects.filter(
        key__in=[key for key, _version in agent_refs if key]
    ).select_related("prompt", "primary_model__gateway")
    agent_snapshots = [
        {
            "key": agent.key,
            "version": agent.version,
            "prompt_key": agent.prompt.key,
            "prompt_version": agent.prompt.version,
            "model_key": agent.primary_model.key,
            "provider_model_id": agent.primary_model.provider_model_id,
            "gateway_key": agent.primary_model.gateway.key,
        }
        for agent in agents
        if (agent.key, agent.version) in agent_refs
    ]
    return {
        "workflow_key": workflow.key,
        "workflow_version": workflow.version,
        "graph": workflow.graph,
        "agents": sorted(agent_snapshots, key=lambda item: item["key"]),
        "token_budget": workflow.token_budget,
        "cost_budget_usd": str(workflow.cost_budget_usd),
    }


def create_generation(project: Project, prompt: str) -> Generation:
    workflow = find_published_workflow(project.artifact_type)
    if workflow is None:
        raise GenerationUnavailableError(
            "No published AI workflow supports this project type. "
            "Ask an administrator to publish one."
        )
    return Generation.objects.create(
        project=project,
        workflow=workflow,
        workflow_snapshot=build_workflow_snapshot(workflow),
        prompt=prompt,
        status=Generation.Status.QUEUED,
        current_step="Queued for generation",
        progress=0,
    )


def dispatch_generation(generation: Generation) -> None:
    from apps.builder.tasks import generate_trading_code

    if settings.GENERATION_RUN_INLINE:
        generate_trading_code.apply(args=[str(generation.pk)], throw=False)
    else:
        generate_trading_code.delay(str(generation.pk))
