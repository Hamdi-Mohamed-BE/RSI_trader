from celery import shared_task

from .models import Gateway


@shared_task(ignore_result=False)
def inspect_gateway_configuration(gateway_id: str) -> dict[str, str | bool]:
    gateway = Gateway.objects.get(pk=gateway_id)
    return {
        "gateway": gateway.key,
        "provider": gateway.provider,
        "enabled": gateway.enabled,
        "credential_configured": gateway.has_api_key,
    }
