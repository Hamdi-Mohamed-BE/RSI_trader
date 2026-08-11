from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, TypedDict

from langgraph.graph import END, START, StateGraph
from pydantic import ValidationError

from apps.ai_config.models import AgentDefinition, WorkflowDefinition
from apps.ai_config.services.invocation import invoke_agent_structured
from apps.builder.models import Project

from .schemas import (
    CodeReview,
    GeneratedArtifact,
    StrategySpecification,
    WorkflowGraphConfig,
)
from .validators import validate_source

ProgressCallback = Callable[[str, int], None]


class GenerationRuntimeError(RuntimeError):
    """Raised when a configured generation workflow cannot complete safely."""


class GenerationState(TypedDict):
    specification: dict[str, Any]
    source_code: str
    explanation: str
    assumptions: list[str]
    diagnostics: list[dict[str, str]]
    repair_instructions: list[str]
    repair_count: int
    review_passed: bool
    input_tokens: int
    output_tokens: int


@dataclass(frozen=True)
class RuntimeResult:
    specification: dict[str, Any]
    source_code: str
    explanation: str
    assumptions: list[str]
    diagnostics: list[dict[str, str]]
    review_passed: bool
    input_tokens: int
    output_tokens: int


class GenerationRuntime:
    def __init__(
        self,
        workflow: WorkflowDefinition,
        progress_callback: ProgressCallback | None = None,
    ) -> None:
        self.workflow = workflow
        self.progress_callback = progress_callback or (lambda _step, _progress: None)
        self.agents = self._load_agents()

    def _load_agents(self) -> dict[str, AgentDefinition]:
        try:
            graph = WorkflowGraphConfig.model_validate(self.workflow.graph)
        except ValidationError as exc:
            raise GenerationRuntimeError("The published workflow graph is invalid.") from exc

        configured = graph.agents_by_kind()
        required = {"architect", "generator", "reviewer", "repairer"}
        if not required.issubset(configured):
            raise GenerationRuntimeError("The published workflow is missing a required agent role.")

        agents: dict[str, AgentDefinition] = {}
        for kind, (key, version) in configured.items():
            try:
                agents[kind] = AgentDefinition.objects.select_related(
                    "prompt", "primary_model__gateway"
                ).get(key=key, version=version, published=True, prompt__published=True)
            except AgentDefinition.DoesNotExist as exc:
                raise GenerationRuntimeError(
                    f"The published {kind} agent configuration is unavailable."
                ) from exc
        return agents

    def _add_usage(self, state: GenerationState, usage: tuple[int, int]) -> dict[str, int]:
        input_tokens = state["input_tokens"] + usage[0]
        output_tokens = state["output_tokens"] + usage[1]
        if input_tokens + output_tokens > self.workflow.token_budget:
            raise GenerationRuntimeError("The workflow token budget was exceeded.")
        return {"input_tokens": input_tokens, "output_tokens": output_tokens}

    def run(self, project: Project, prompt: str) -> RuntimeResult:
        project_payload = {
            "artifact_type": project.artifact_type,
            "platform_label": project.get_artifact_type_display(),
            "project_name": project.name,
            "symbol": project.symbol,
            "timeframe": project.timeframe,
            "strategy_brief": project.description,
            "generation_request": prompt,
        }

        def architect(state: GenerationState) -> dict[str, Any]:
            self.progress_callback("Designing explicit strategy rules", 15)
            response = invoke_agent_structured(
                self.agents["architect"], StrategySpecification, project_payload
            )
            return {
                "specification": response.parsed.model_dump(mode="json"),
                **self._add_usage(state, (response.input_tokens, response.output_tokens)),
            }

        def generator(state: GenerationState) -> dict[str, Any]:
            self.progress_callback("Generating complete source code", 40)
            response = invoke_agent_structured(
                self.agents["generator"],
                GeneratedArtifact,
                {**project_payload, "strategy_specification": state["specification"]},
            )
            return {
                "source_code": response.parsed.source_code,
                "explanation": response.parsed.explanation,
                "assumptions": response.parsed.assumptions,
                **self._add_usage(state, (response.input_tokens, response.output_tokens)),
            }

        def reviewer(state: GenerationState) -> dict[str, Any]:
            self.progress_callback("Reviewing behavior and code safety", 70)
            static_outcome = validate_source(project, state["source_code"])
            response = invoke_agent_structured(
                self.agents["reviewer"],
                CodeReview,
                {
                    **project_payload,
                    "strategy_specification": state["specification"],
                    "source_code": static_outcome.source_code,
                    "deterministic_diagnostics": static_outcome.diagnostics,
                },
            )
            diagnostics = static_outcome.diagnostics + [
                issue.model_dump(mode="json") for issue in response.parsed.issues
            ]
            has_errors = any(item["severity"] == "error" for item in diagnostics)
            return {
                "source_code": static_outcome.source_code,
                "diagnostics": diagnostics,
                "repair_instructions": response.parsed.repair_instructions,
                "review_passed": response.parsed.passed and not has_errors,
                **self._add_usage(state, (response.input_tokens, response.output_tokens)),
            }

        def repairer(state: GenerationState) -> dict[str, Any]:
            repair_count = state["repair_count"] + 1
            self.progress_callback(
                f"Repairing reviewer findings ({repair_count}/{self.workflow.max_repair_loops})",
                75 + min(repair_count * 8, 16),
            )
            response = invoke_agent_structured(
                self.agents["repairer"],
                GeneratedArtifact,
                {
                    **project_payload,
                    "strategy_specification": state["specification"],
                    "current_source_code": state["source_code"],
                    "diagnostics": state["diagnostics"],
                    "repair_instructions": state["repair_instructions"],
                },
            )
            return {
                "source_code": response.parsed.source_code,
                "explanation": response.parsed.explanation,
                "assumptions": response.parsed.assumptions,
                "repair_count": repair_count,
                **self._add_usage(state, (response.input_tokens, response.output_tokens)),
            }

        def route_after_review(state: GenerationState) -> str:
            if state["review_passed"] or state["repair_count"] >= self.workflow.max_repair_loops:
                return "complete"
            return "repair"

        graph = StateGraph(GenerationState)
        graph.add_node("architect", architect)
        graph.add_node("generator", generator)
        graph.add_node("reviewer", reviewer)
        graph.add_node("repairer", repairer)
        graph.add_edge(START, "architect")
        graph.add_edge("architect", "generator")
        graph.add_edge("generator", "reviewer")
        graph.add_conditional_edges(
            "reviewer",
            route_after_review,
            {"complete": END, "repair": "repairer"},
        )
        graph.add_edge("repairer", "reviewer")

        initial_state: GenerationState = {
            "specification": {},
            "source_code": "",
            "explanation": "",
            "assumptions": [],
            "diagnostics": [],
            "repair_instructions": [],
            "repair_count": 0,
            "review_passed": False,
            "input_tokens": 0,
            "output_tokens": 0,
        }
        final_state = graph.compile().invoke(initial_state)
        if not final_state["source_code"]:
            raise GenerationRuntimeError("The workflow completed without source code.")
        self.progress_callback("Finalizing version and diagnostics", 95)
        return RuntimeResult(
            specification=final_state["specification"],
            source_code=final_state["source_code"],
            explanation=final_state["explanation"],
            assumptions=final_state["assumptions"],
            diagnostics=final_state["diagnostics"],
            review_passed=final_state["review_passed"],
            input_tokens=final_state["input_tokens"],
            output_tokens=final_state["output_tokens"],
        )
