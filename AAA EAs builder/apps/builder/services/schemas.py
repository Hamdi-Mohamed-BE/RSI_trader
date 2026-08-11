from typing import Any, Literal

from pydantic import BaseModel, Field


class StrategyParameter(BaseModel):
    name: str
    value_type: str
    default: str
    description: str


class StrategySpecification(BaseModel):
    title: str
    summary: str
    entry_rules: list[str]
    exit_rules: list[str]
    risk_rules: list[str]
    filters: list[str]
    no_trade_conditions: list[str]
    parameters: list[StrategyParameter]
    assumptions: list[str]
    implementation_notes: list[str]


class GeneratedArtifact(BaseModel):
    source_code: str = Field(min_length=100)
    explanation: str
    assumptions: list[str] = Field(default_factory=list)


class ReviewIssue(BaseModel):
    severity: Literal["error", "warning"]
    code: str
    message: str
    suggestion: str = ""


class CodeReview(BaseModel):
    passed: bool
    summary: str
    issues: list[ReviewIssue] = Field(default_factory=list)
    repair_instructions: list[str] = Field(default_factory=list)


class GenerationCopilotResponse(BaseModel):
    reply: str = Field(min_length=1)
    proposed_source_code: str | None = None
    change_summary: list[str] = Field(default_factory=list)
    addressed_diagnostics: list[str] = Field(default_factory=list)


class WorkflowNodeConfig(BaseModel):
    id: str
    kind: Literal["architect", "generator", "reviewer", "repairer"]
    agent_key: str
    agent_version: int = 1


class WorkflowGraphConfig(BaseModel):
    nodes: list[WorkflowNodeConfig]

    def agents_by_kind(self) -> dict[str, tuple[str, int]]:
        return {node.kind: (node.agent_key, node.agent_version) for node in self.nodes}


def json_ready(value: BaseModel | dict[str, Any]) -> dict[str, Any]:
    if isinstance(value, BaseModel):
        return value.model_dump(mode="json")
    return value
