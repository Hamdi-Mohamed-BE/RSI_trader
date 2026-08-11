from typing import Any

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import transaction

from apps.ai_config.models import AIModel, Gateway
from apps.ai_config.services.default_workflow import seed_default_generation_workflow
from apps.ai_config.services.encryption import secret_fingerprint


class Command(BaseCommand):
    help = "Create or update the environment-managed default Gemini gateway and model."

    @transaction.atomic
    def handle(self, *args: Any, **options: Any) -> None:
        api_key = settings.GEMINI_API_KEY.strip()
        model_name = settings.GEMINI_MODEL.strip() or "gemini-3.1-flash-lite"

        gateway, _ = Gateway.objects.update_or_create(
            key="gemini-default",
            defaults={
                "name": "Gemini Default",
                "provider": Gateway.Provider.GOOGLE,
                "enabled": bool(api_key),
                "priority": 10,
                "timeout_seconds": 120,
                "max_concurrency": 2,
                "extra_config": {"vertexai": False},
                "notes": "Environment-managed default Gemini gateway.",
            },
        )

        if api_key and gateway.api_key_fingerprint != secret_fingerprint(api_key):
            gateway.set_api_key(api_key)
            gateway.save(update_fields=("encrypted_api_key", "api_key_fingerprint", "updated_at"))

        model, _ = AIModel.objects.update_or_create(
            key="gemini-default",
            defaults={
                "gateway": gateway,
                "name": "Gemini 3.1 Flash-Lite",
                "provider_model_id": model_name,
                "enabled": gateway.enabled,
                "supports_structured_output": True,
                "supports_tools": True,
                "supports_streaming": True,
                "max_input_tokens": 1_048_576,
                "max_output_tokens": 65_536,
                "default_parameters": {"temperature": 1.0, "max_retries": 2},
            },
        )
        workflow = seed_default_generation_workflow(model)

        credential_status = "configured" if gateway.has_api_key else "not configured"
        message = (
            f"Synced {gateway.name}, {model.provider_model_id}, and {workflow.name}; "
            f"credential {credential_status}."
        )
        self.stdout.write(self.style.SUCCESS(message))
