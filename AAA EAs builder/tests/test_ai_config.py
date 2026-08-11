import pytest
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import override_settings
from django.urls import reverse

from apps.ai_config.forms import GatewayAdminForm
from apps.ai_config.models import (
    AgentDefinition,
    AIModel,
    Gateway,
    PromptVersion,
    WorkflowDefinition,
)


@pytest.mark.django_db
def test_gateway_api_key_is_encrypted_and_write_only():
    form = GatewayAdminForm(
        data={
            "name": "Primary OpenAI",
            "key": "primary-openai",
            "provider": Gateway.Provider.OPENAI,
            "base_url": "",
            "enabled": "on",
            "priority": 100,
            "timeout_seconds": 60,
            "max_concurrency": 2,
            "daily_budget_usd": "10.00",
            "extra_config": "{}",
            "notes": "",
            "api_key": "secret-test-value",
        }
    )
    assert form.is_valid(), form.errors
    gateway = form.save()
    assert gateway.encrypted_api_key != "secret-test-value"
    assert gateway.api_key_fingerprint
    assert gateway.get_api_key() == "secret-test-value"


@pytest.mark.django_db
def test_unfold_admin_pages_load_for_superuser(client):
    admin_user = get_user_model().objects.create_superuser(
        email="admin@example.com", password="strong-admin-test-pass"
    )
    client.force_login(admin_user)
    for url_name in ("admin:index", "admin:ai_config_gateway_add", "admin:accounts_user_add"):
        response = client.get(reverse(url_name))
        assert response.status_code == 200


@pytest.mark.django_db
@override_settings(
    GEMINI_API_KEY="fake-gemini-test-key",
    GEMINI_MODEL="gemini-3.1-flash-lite",
)
def test_sync_llm_config_creates_encrypted_default_and_is_idempotent():
    call_command("sync_llm_config")
    call_command("sync_llm_config")

    gateway = Gateway.objects.get(key="gemini-default")
    model = AIModel.objects.get(key="gemini-default")

    assert Gateway.objects.filter(key="gemini-default").count() == 1
    assert AIModel.objects.filter(key="gemini-default").count() == 1
    assert gateway.provider == Gateway.Provider.GOOGLE
    assert gateway.enabled is True
    assert gateway.encrypted_api_key != "fake-gemini-test-key"
    assert gateway.get_api_key() == "fake-gemini-test-key"
    assert model.gateway == gateway
    assert model.provider_model_id == "gemini-3.1-flash-lite"
    assert model.enabled is True
    assert PromptVersion.objects.filter(published=True).count() == 5
    assert AgentDefinition.objects.filter(published=True).count() == 5
    assert AgentDefinition.objects.filter(key="generation-copilot", published=True).exists()
    assert WorkflowDefinition.objects.filter(key="trading-code-default", published=True).exists()
