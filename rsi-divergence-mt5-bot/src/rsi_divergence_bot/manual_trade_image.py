from __future__ import annotations

import base64
import logging
from typing import Literal

from pydantic import BaseModel, Field

from .config import AppConfig
from .telegram_signals import GeminiSignalParser


class ManualTradeImageParse(BaseModel):
    symbol: str = Field(description="Trading symbol such as BTCUSD, XAUUSD, EURUSD.")
    side: Literal["buy", "sell"]
    stop_loss: float
    tps: list[float] = Field(default_factory=list, description="Take profit prices in order.")
    lot: float | None = Field(default=None, description="Lot size if visible in the image.")
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    notes: str = Field(default="", max_length=300)


class ManualTradeImageParseResult(BaseModel):
    text: str
    parsed: ManualTradeImageParse
    provider: str | None = None


_SYSTEM_PROMPT = (
    "You read trading signal screenshots and extract one live trade setup. "
    "Return structured output only. Normalize GOLD/XAU to XAUUSD when clear. "
    "Use side=buy or side=sell. Include every visible TP in order. "
    "If lot/volume is visible, include it. If the image is not a trade signal, "
    "set confidence to 0 and use placeholder values."
)

_ALLOWED_MIME = {
    "image/jpeg",
    "image/jpg",
    "image/png",
    "image/webp",
    "image/gif",
}


def format_manual_trade_text(parsed: ManualTradeImageParse) -> str:
    side = parsed.side.upper()
    symbol = (parsed.symbol or "").strip()
    lines = [f"{symbol} {side}", f"SL {parsed.stop_loss:g}"]
    for index, tp in enumerate(parsed.tps, start=1):
        lines.append(f"TP{index} {tp:g}")
    if parsed.lot is not None and parsed.lot > 0:
        lines.append(f"LOT {parsed.lot:g}")
    return "\n".join(lines)


def parse_trade_image(
    config: AppConfig,
    image_bytes: bytes,
    mime_type: str,
    logger: logging.Logger | None = None,
) -> ManualTradeImageParseResult:
    log = logger or logging.getLogger(__name__)
    mime = normalize_image_mime(mime_type)
    if mime not in _ALLOWED_MIME:
        raise ValueError(f"Unsupported image type: {mime_type or 'unknown'}")
    if not image_bytes:
        raise ValueError("Image file is empty.")
    if len(image_bytes) > 8 * 1024 * 1024:
        raise ValueError("Image must be 8 MB or smaller.")

    errors: list[str] = []
    openai_key = GeminiSignalParser.openai_api_key(config)
    if openai_key:
        try:
            parsed = _parse_with_openai(config, image_bytes, mime, openai_key)
            return _build_result(parsed, "openai", log)
        except Exception as exc:  # noqa: BLE001
            errors.append(f"OpenAI: {exc}")
            log.warning("MANUAL TRADE IMAGE OpenAI failed, trying Gemini fallback: %s", exc)

    gemini_key = GeminiSignalParser.gemini_api_key(config)
    if gemini_key:
        try:
            parsed = _parse_with_gemini(config, image_bytes, mime, gemini_key)
            return _build_result(parsed, "gemini", log)
        except Exception as exc:  # noqa: BLE001
            errors.append(f"Gemini: {exc}")
            log.warning("MANUAL TRADE IMAGE Gemini fallback failed: %s", exc)

    if errors:
        raise RuntimeError("; ".join(errors))
    raise RuntimeError(
        "No LLM API key configured. Set telegram_signals.openai_api_key or OPENAI_API_KEY, "
        "or telegram_signals.gemini_api_key or GEMINI_API_KEY."
    )


def normalize_image_mime(mime_type: str) -> str:
    mime = (mime_type or "image/png").split(";", 1)[0].strip().lower()
    if mime == "image/jpg":
        return "image/jpeg"
    return mime


def _build_result(
    parsed: ManualTradeImageParse,
    provider: str,
    logger: logging.Logger,
) -> ManualTradeImageParseResult:
    if parsed.confidence <= 0 or not parsed.symbol or not parsed.tps or parsed.stop_loss <= 0:
        raise ValueError("Could not find a valid trade signal in the image.")
    text = format_manual_trade_text(parsed)
    logger.info(
        "MANUAL TRADE IMAGE provider=%s symbol=%s side=%s tps=%s confidence=%.2f",
        provider,
        parsed.symbol,
        parsed.side,
        len(parsed.tps),
        parsed.confidence,
    )
    return ManualTradeImageParseResult(text=text, parsed=parsed, provider=provider)


def _parse_with_openai(
    config: AppConfig,
    image_bytes: bytes,
    mime_type: str,
    api_key: str,
) -> ManualTradeImageParse:
    from langchain_core.messages import HumanMessage, SystemMessage
    from langchain_openai import ChatOpenAI

    llm = ChatOpenAI(
        model=config.telegram_signals.openai_model,
        api_key=api_key,
        temperature=0,
    ).with_structured_output(ManualTradeImageParse)
    encoded = base64.b64encode(image_bytes).decode("ascii")
    data_url = f"data:{mime_type};base64,{encoded}"
    messages = [
        SystemMessage(content=_SYSTEM_PROMPT),
        HumanMessage(
            content=[
                {
                    "type": "text",
                    "text": "Extract the trade signal from this screenshot.",
                },
                {"type": "image_url", "image_url": {"url": data_url}},
            ]
        ),
    ]
    result = llm.invoke(messages)
    if not isinstance(result, ManualTradeImageParse):
        return ManualTradeImageParse.model_validate(result)
    return result


def _parse_with_gemini(
    config: AppConfig,
    image_bytes: bytes,
    mime_type: str,
    api_key: str,
) -> ManualTradeImageParse:
    from langchain_core.messages import HumanMessage, SystemMessage
    from langchain_google_genai import ChatGoogleGenerativeAI

    llm = ChatGoogleGenerativeAI(
        model=config.telegram_signals.gemini_model,
        google_api_key=api_key,
        temperature=0,
    ).with_structured_output(ManualTradeImageParse)
    encoded = base64.b64encode(image_bytes).decode("ascii")
    data_url = f"data:{mime_type};base64,{encoded}"
    messages = [
        SystemMessage(content=_SYSTEM_PROMPT),
        HumanMessage(
            content=[
                {
                    "type": "text",
                    "text": "Extract the trade signal from this screenshot.",
                },
                {"type": "image_url", "image_url": {"url": data_url}},
            ]
        ),
    ]
    result = llm.invoke(messages)
    if not isinstance(result, ManualTradeImageParse):
        return ManualTradeImageParse.model_validate(result)
    return result


def llm_configured(config: AppConfig) -> bool:
    return GeminiSignalParser.llm_configured(config)
