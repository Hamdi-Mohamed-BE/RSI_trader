from unittest.mock import patch

import pytest
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import override_settings
from django.urls import reverse

from apps.ai_config.services.invocation import StructuredInvocation
from apps.builder.models import (
    CodeRevisionProposal,
    CodeVersion,
    Generation,
    GenerationChatMessage,
    Project,
)
from apps.builder.services.chat import ChatResult, answer_generation_chat
from apps.builder.services.compiler import compile_mql5_source
from apps.builder.services.generation import create_generation
from apps.builder.services.revisions import apply_code_proposal
from apps.builder.services.runtime import RuntimeResult
from apps.builder.services.schemas import GenerationCopilotResponse
from apps.builder.services.validators import validate_source
from apps.builder.tasks import generate_trading_code, respond_to_generation_chat


@pytest.fixture
def user(db):
    return get_user_model().objects.create_user(email="owner@example.com", password="test-pass")


@pytest.mark.django_db
def test_project_creation_assigns_signed_in_owner(client, user):
    client.force_login(user)
    response = client.post(
        reverse("builder:create"),
        {
            "name": "EURUSD Momentum",
            "artifact_type": Project.ArtifactType.MT5_EA,
            "symbol": "eurusd",
            "timeframe": "h1",
            "description": "Enter when EMA 50 crosses EMA 200 and risk one percent.",
        },
    )
    project = Project.objects.get()
    assert response.status_code == 302
    assert project.owner == user
    assert project.symbol == "EURUSD"
    assert project.timeframe == "H1"


@pytest.mark.django_db
def test_user_cannot_open_another_users_project(client, user):
    other_user = get_user_model().objects.create_user(
        email="other@example.com", password="test-pass"
    )
    project = Project.objects.create(
        owner=other_user,
        name="Private strategy",
        artifact_type=Project.ArtifactType.MT5_EA,
        description="Private rules",
    )
    client.force_login(user)
    response = client.get(reverse("builder:detail", kwargs={"pk": project.pk}))
    assert response.status_code == 404


@pytest.mark.django_db
@override_settings(
    GEMINI_API_KEY="fake-gemini-test-key",
    GEMINI_MODEL="gemini-3.1-flash-lite",
    GENERATION_RUN_INLINE=False,
)
def test_user_can_start_generation_with_pinned_workflow(client, user):
    call_command("sync_llm_config")
    project = Project.objects.create(
        owner=user,
        name="EURUSD Crossover",
        artifact_type=Project.ArtifactType.MT5_EA,
        symbol="EURUSD",
        timeframe="H1",
        description="Buy when the fast EMA crosses above the slow EMA and use an ATR stop.",
    )
    client.force_login(user)

    with patch("apps.builder.views.dispatch_generation") as dispatch:
        response = client.post(
            reverse("builder:generate", kwargs={"pk": project.pk}),
            {
                "prompt": "Generate the complete EA with one percent risk and one open position.",
                "acknowledge_testing": "on",
            },
        )

    generation = Generation.objects.get(project=project)
    assert response.status_code == 302
    assert generation.workflow is not None
    assert generation.workflow_snapshot["workflow_key"] == "trading-code-default"
    assert len(generation.workflow_snapshot["agents"]) == 4
    dispatch.assert_called_once_with(generation)


def _valid_mql5_source() -> str:
    return """#property strict
#include <Trade/Trade.mqh>
CTrade trade;
input double RiskPercent = 1.0;
int OnInit()
{
   trade.SetExpertMagicNumber(26081001);
   return(INIT_SUCCEEDED);
}
void OnTick()
{
   if(!PositionSelect(_Symbol))
   {
      double ask = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
      double minimumStop = SymbolInfoInteger(_Symbol, SYMBOL_TRADE_STOPS_LEVEL) * _Point;
      double stopDistance = MathMax(500 * _Point, minimumStop);
      double stop = NormalizeDouble(ask - stopDistance, _Digits);
      double target = NormalizeDouble(ask + (stopDistance * 2), _Digits);
      double oneLotLoss = 0.0;
      if(!OrderCalcProfit(ORDER_TYPE_BUY, _Symbol, 1.0, ask, stop, oneLotLoss))
         return;
      double riskMoney = AccountInfoDouble(ACCOUNT_BALANCE) * RiskPercent / 100.0;
      double volume = riskMoney / MathAbs(oneLotLoss);
      if(!trade.Buy(volume, _Symbol, ask, stop, target, "Generated test trade"))
         Print("Trade failed: ", trade.ResultRetcodeDescription());
   }
}
"""


@pytest.mark.django_db
@override_settings(
    GEMINI_API_KEY="fake-gemini-test-key",
    GEMINI_MODEL="gemini-3.1-flash-lite",
)
def test_generation_task_saves_version_and_validation(user):
    call_command("sync_llm_config")
    project = Project.objects.create(
        owner=user,
        name="Safe EA",
        artifact_type=Project.ArtifactType.MT5_EA,
        symbol="EURUSD",
        timeframe="H1",
        description="Open one position with stop loss and take profit.",
    )
    generation = create_generation(project, project.description)
    runtime_result = RuntimeResult(
        specification={"summary": "One-position test strategy"},
        source_code=_valid_mql5_source(),
        explanation="A complete test EA.",
        assumptions=["Demo testing is required."],
        diagnostics=[],
        review_passed=True,
        input_tokens=120,
        output_tokens=240,
    )

    with patch("apps.builder.tasks.GenerationRuntime") as runtime:
        runtime.return_value.run.return_value = runtime_result
        result = generate_trading_code(str(generation.pk))

    generation.refresh_from_db()
    project.refresh_from_db()
    code_version = CodeVersion.objects.get(generation=generation)
    assert result["status"] == Generation.Status.SUCCEEDED
    assert generation.progress == 100
    assert generation.input_tokens == 120
    assert project.status == Project.Status.READY
    assert code_version.version == 1
    assert code_version.validation_status == CodeVersion.ValidationStatus.PASSED
    assert code_version.compilation_status == CodeVersion.CompilationStatus.UNAVAILABLE
    assert len(code_version.source_hash) == 64


@pytest.mark.django_db
def test_static_validator_rejects_incomplete_mql5(user):
    project = Project.objects.create(
        owner=user,
        name="Incomplete EA",
        artifact_type=Project.ArtifactType.MT5_EA,
        description="Test strategy",
    )
    outcome = validate_source(project, "void OnTick() { /* TODO */ }")
    assert outcome.status == CodeVersion.ValidationStatus.FAILED
    assert {item["code"] for item in outcome.diagnostics} >= {
        "source-too-short",
        "placeholder",
        "missing-entry-point",
    }


@pytest.mark.django_db
def test_source_download_is_owner_protected(client, user):
    project = Project.objects.create(
        owner=user,
        name="Download EA",
        artifact_type=Project.ArtifactType.MT5_EA,
        description="Test strategy",
    )
    code_version = CodeVersion.objects.create(
        project=project,
        version=1,
        filename="download_ea.mq5",
        language="mql5",
        source_code=_valid_mql5_source(),
    )
    client.force_login(user)
    workspace = client.get(reverse("builder:detail", kwargs={"pk": project.pk}))
    assert workspace.status_code == 200
    assert b"data-code-editor" in workspace.content
    assert b"download_ea.mq5" in workspace.content

    response = client.get(
        reverse("builder:download", kwargs={"pk": project.pk, "version_pk": code_version.pk})
    )
    assert response.status_code == 200
    assert "download_ea.mq5" in response.headers["Content-Disposition"]

    other_user = get_user_model().objects.create_user(
        email="download-other@example.com", password="test-pass"
    )
    client.force_login(other_user)
    denied = client.get(
        reverse("builder:download", kwargs={"pk": project.pk, "version_pk": code_version.pk})
    )
    assert denied.status_code == 404


@override_settings(MQL5_COMPILER_ENABLED=False)
def test_mql5_compiler_reports_unavailable_when_disabled():
    result = compile_mql5_source(
        generation_id="safe-test-run",
        filename="safe.mq5",
        source_code=_valid_mql5_source(),
    )
    assert result.status == CodeVersion.CompilationStatus.UNAVAILABLE


def test_mql5_compiler_rejects_unsafe_include_before_launch(tmp_path):
    fake_compiler = tmp_path / "metaeditor64.exe"
    fake_compiler.touch()
    with override_settings(
        MQL5_COMPILER_ENABLED=True,
        METAEDITOR_PATH=str(fake_compiler),
        MQL5_COMPILE_WORKDIR=str(tmp_path / "compiler-work"),
        MQL5_COMPILE_TIMEOUT_SECONDS=10,
    ):
        result = compile_mql5_source(
            generation_id="unsafe-test-run",
            filename="unsafe.mq5",
            source_code='#property strict\n#include "..\\private.mqh"\nvoid OnTick() {}',
        )
    assert result.status == CodeVersion.CompilationStatus.FAILED
    assert "refused" in result.output.lower()


def _chat_generation(user):
    project = Project.objects.create(
        owner=user,
        name="Copilot EA",
        artifact_type=Project.ArtifactType.MT5_EA,
        symbol="EURUSD",
        timeframe="H1",
        description="Trade one safe position with one percent balance risk.",
        strategy_spec={"summary": "One-position risk-controlled EA"},
    )
    generation = Generation.objects.create(
        project=project,
        prompt=project.description,
        status=Generation.Status.SUCCEEDED,
        current_step="Generation complete",
        progress=100,
        workflow_snapshot={"workflow_key": "trading-code-default", "workflow_version": 2},
    )
    code_version = CodeVersion.objects.create(
        project=project,
        generation=generation,
        version=1,
        filename="copilot_ea.mq5",
        language="mql5",
        source_code=_valid_mql5_source(),
        validation_status=CodeVersion.ValidationStatus.WARNINGS,
        diagnostics=[
            {
                "severity": "warning",
                "code": "demo-warning",
                "message": "Review the demo position sizing.",
            }
        ],
        source_hash="source-hash-v1",
    )
    return project, generation, code_version


@pytest.mark.django_db
@override_settings(GENERATION_RUN_INLINE=False)
def test_user_can_start_project_aware_chat(client, user):
    project, generation, _code_version = _chat_generation(user)
    client.force_login(user)
    with patch("apps.builder.views.dispatch_chat_response") as dispatch:
        response = client.post(
            reverse(
                "builder:generation-chat",
                kwargs={"pk": project.pk, "generation_pk": generation.pk},
            ),
            {"message": "Explain the current warning and progress."},
        )

    chat_messages = list(generation.chat_messages.all())
    assert response.status_code == 302
    assert [message.role for message in chat_messages] == [
        GenerationChatMessage.Role.USER,
        GenerationChatMessage.Role.ASSISTANT,
    ]
    assert chat_messages[1].status == GenerationChatMessage.Status.PENDING
    dispatch.assert_called_once_with(chat_messages[1])

    page = client.get(
        reverse(
            "builder:generation-detail",
            kwargs={"pk": project.pk, "generation_pk": generation.pk},
        )
    )
    assert page.status_code == 200
    assert b"Project-aware copilot" in page.content
    assert b"Explain the current warning" in page.content


@pytest.mark.django_db
@override_settings(
    GEMINI_API_KEY="fake-gemini-test-key",
    GEMINI_MODEL="gemini-3.1-flash-lite",
)
def test_chat_context_contains_progress_source_diagnostics_and_history(user):
    call_command("sync_llm_config")
    project, generation, code_version = _chat_generation(user)
    GenerationChatMessage.objects.create(
        generation=generation,
        author=user,
        role=GenerationChatMessage.Role.USER,
        content="Please inspect the latest warning.",
    )
    assistant = GenerationChatMessage.objects.create(
        generation=generation,
        role=GenerationChatMessage.Role.ASSISTANT,
        status=GenerationChatMessage.Status.PENDING,
    )
    invocation = StructuredInvocation(
        parsed=GenerationCopilotResponse(
            reply="The run is complete and one warning remains.",
            proposed_source_code=None,
        ),
        input_tokens=50,
        output_tokens=20,
    )

    with patch(
        "apps.builder.services.chat.invoke_agent_structured", return_value=invocation
    ) as invoke:
        result = answer_generation_chat(assistant)

    payload = invoke.call_args.args[2]
    assert payload["generation"]["progress_percent"] == 100
    assert payload["generation"]["workflow_snapshot"]["workflow_version"] == 2
    assert payload["latest_code"]["source_code"] == code_version.source_code
    assert payload["latest_code"]["diagnostics"][0]["code"] == "demo-warning"
    assert payload["conversation"][-1]["content"] == "Please inspect the latest warning."
    assert result.context_snapshot["source_hash"] == "source-hash-v1"


@pytest.mark.django_db
def test_chat_task_creates_reviewable_code_proposal(user):
    _project, generation, code_version = _chat_generation(user)
    assistant = GenerationChatMessage.objects.create(
        generation=generation,
        role=GenerationChatMessage.Role.ASSISTANT,
        status=GenerationChatMessage.Status.PENDING,
    )
    chat_result = ChatResult(
        reply="I prepared a complete corrected source file.",
        input_tokens=100,
        output_tokens=200,
        context_snapshot={"code_version": 1, "source_hash": "source-hash-v1"},
        base_version=code_version,
        proposed_source_code=_valid_mql5_source().replace("26081001", "26081002"),
        proposal_explanation="Updated the magic number and preserved risk controls.",
        change_summary=["Updated the isolated magic number."],
        diagnostics=[],
    )

    with patch("apps.builder.tasks.answer_generation_chat", return_value=chat_result):
        result = respond_to_generation_chat(str(assistant.pk))

    assistant.refresh_from_db()
    proposal = CodeRevisionProposal.objects.get(assistant_message=assistant)
    assert result["proposal_created"] is True
    assert assistant.status == GenerationChatMessage.Status.COMPLETED
    assert assistant.input_tokens == 100
    assert proposal.base_version == code_version
    assert proposal.status == CodeRevisionProposal.Status.PROPOSED


@pytest.mark.django_db
@override_settings(MQL5_COMPILER_ENABLED=False)
def test_applying_chat_proposal_creates_new_version_without_overwrite(user):
    project, generation, base_version = _chat_generation(user)
    assistant = GenerationChatMessage.objects.create(
        generation=generation,
        role=GenerationChatMessage.Role.ASSISTANT,
        status=GenerationChatMessage.Status.COMPLETED,
        content="A complete fix is ready for review.",
    )
    proposal = CodeRevisionProposal.objects.create(
        generation=generation,
        assistant_message=assistant,
        base_version=base_version,
        source_code=_valid_mql5_source().replace("26081001", "26081002"),
        explanation="Changed the magic number while preserving the base version.",
        diagnostics=[],
    )

    applied = apply_code_proposal(proposal)

    proposal.refresh_from_db()
    assert applied.version == 2
    assert applied.generation is None
    assert project.code_versions.filter(pk=base_version.pk, version=1).exists()
    assert proposal.status == CodeRevisionProposal.Status.APPLIED
    assert proposal.applied_version == applied
