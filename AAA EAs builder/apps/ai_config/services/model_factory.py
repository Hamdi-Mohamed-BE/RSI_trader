from typing import Any

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_google_genai import ChatGoogleGenerativeAI

from apps.ai_config.models import AIModel, Gateway


class ModelConfigurationError(ValueError):
    """Raised when an administrator-managed model cannot be constructed safely."""


_ALLOWED_PARAMETERS = {
    "temperature",
    "max_tokens",
    "max_retries",
    "top_p",
    "thinking_level",
}


def build_chat_model(model: AIModel, *, max_output_tokens: int | None = None) -> BaseChatModel:
    """Build a LangChain chat model from validated database configuration."""
    gateway = model.gateway
    if not model.enabled or not gateway.enabled:
        raise ModelConfigurationError("The selected model or gateway is disabled.")
    if not gateway.has_api_key:
        raise ModelConfigurationError("The selected gateway has no API credential.")
    if gateway.provider != Gateway.Provider.GOOGLE:
        raise ModelConfigurationError(f"Unsupported gateway provider: {gateway.provider}.")

    parameters: dict[str, Any] = {
        key: value for key, value in model.default_parameters.items() if key in _ALLOWED_PARAMETERS
    }
    parameters["vertexai"] = bool(gateway.extra_config.get("vertexai", False))
    if max_output_tokens is not None:
        parameters["max_tokens"] = min(max_output_tokens, model.max_output_tokens)

    return ChatGoogleGenerativeAI(
        model=model.provider_model_id,
        api_key=gateway.get_api_key(),
        timeout=gateway.timeout_seconds,
        **parameters,
    )
