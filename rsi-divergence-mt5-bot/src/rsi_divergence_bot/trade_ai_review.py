from __future__ import annotations

import json
import logging
import os
from typing import Any

from pydantic import BaseModel, Field

from .config import AiTradeReviewConfig, AppConfig, SymbolConfig
from .decision import TradeDecision
from .strategy import Signal
from .strategy_modes import canonical_strategy


class TradeAiReviewResult(BaseModel):
    approved: bool
    confidence: float = Field(ge=0.0, le=1.0)
    reason: str = Field(default="", max_length=500)
    provider: str | None = None


def ai_review_applies(config: AppConfig) -> bool:
    cfg = config.bot.ai_trade_review
    if not cfg.enabled:
        return False
    strategy = canonical_strategy(config.bot.strategy)
    if not cfg.strategies:
        return True
    allowed = {canonical_strategy(item) for item in cfg.strategies}
    return strategy in allowed


def backtest_ai_review_active(config: AppConfig, use_ai_review: bool) -> bool:
    if not use_ai_review:
        return False
    cfg = config.bot.ai_trade_review
    strategy = canonical_strategy(config.bot.strategy)
    if not cfg.strategies:
        return True
    allowed = {canonical_strategy(item) for item in cfg.strategies}
    return strategy in allowed


def effective_ai_review_min_confidence(config: AppConfig, override: float | None = None) -> float:
    if override is not None:
        return override
    return config.bot.ai_trade_review.min_confidence


def resolve_openai_key(config: AppConfig) -> str | None:
    review = config.bot.ai_trade_review
    key = review.openai_api_key or config.telegram_signals.openai_api_key or os.getenv("OPENAI_API_KEY")
    return key.strip() if key else None


def resolve_gemini_key(config: AppConfig) -> str | None:
    review = config.bot.ai_trade_review
    key = review.gemini_api_key or config.telegram_signals.gemini_api_key or os.getenv("GEMINI_API_KEY")
    return key.strip() if key else None


def resolve_openai_model(config: AppConfig) -> str:
    review = config.bot.ai_trade_review
    if review.openai_model:
        return review.openai_model
    return config.telegram_signals.openai_model


def resolve_gemini_model(config: AppConfig) -> str:
    review = config.bot.ai_trade_review
    if review.gemini_model:
        return review.gemini_model
    return config.telegram_signals.gemini_model


def llm_configured(config: AppConfig) -> bool:
    return bool(resolve_openai_key(config) or resolve_gemini_key(config))


def build_review_payload(
    config: AppConfig,
    signal: Signal,
    decision: TradeDecision,
    symbol_cfg: SymbolConfig | None = None,
    live_price: float | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "symbol": signal.symbol,
        "market_key": signal.market_key,
        "side": signal.side,
        "strategy": canonical_strategy(config.bot.strategy),
        "trade_decision_profile": config.bot.trade_decision_profile,
        "session": signal.session,
        "signal_reason": signal.reason,
        "entry": signal.entry,
        "stop_loss": signal.sl,
        "take_profits": signal.tps,
        "lot_per_leg": signal.lot_per_leg,
        "risk_distance": signal.risk_distance,
        "risk_usd": round(decision.risk_usd, 2),
        "spread": round(decision.spread, 6),
        "spread_atr": round(decision.spread_atr, 4),
        "tp1_distance": round(decision.tp1_distance, 6),
        "min_tp1_distance": round(decision.min_tp1_distance, 6),
        "dry_run": config.bot.dry_run,
    }
    if live_price is not None:
        payload["live_price"] = round(live_price, 6)
    if symbol_cfg is not None:
        payload["timeframe"] = symbol_cfg.timeframe
        payload["confirmation"] = symbol_cfg.confirmation
        payload["rr_levels"] = symbol_cfg.rr
    return payload


class TradeAiReviewer:
    _SYSTEM_PROMPT = (
        "You review RSI divergence trade setups before live execution. "
        "Approve only when structure, risk/reward, and context look reasonable. "
        "Reject weak, overextended, or unclear setups. "
        "Return approved=false when unsure. Keep reason short and actionable."
    )

    def __init__(self, config: AppConfig, logger: logging.Logger | None = None):
        self.config = config
        self.logger = logger or logging.getLogger(__name__)
        self.last_review: dict[str, Any] | None = None

    def review(
        self,
        signal: Signal,
        decision: TradeDecision,
        *,
        symbol_cfg: SymbolConfig | None = None,
        live_price: float | None = None,
    ) -> TradeAiReviewResult:
        if not llm_configured(self.config):
            result = TradeAiReviewResult(
                approved=False,
                confidence=0.0,
                reason="AI review enabled but no OpenAI/Gemini API key configured",
                provider=None,
            )
            self._remember(signal, result)
            return result

        payload = build_review_payload(
            self.config,
            signal,
            decision,
            symbol_cfg=symbol_cfg,
            live_price=live_price,
        )
        trade_json = json.dumps(payload, indent=2, sort_keys=True)
        errors: list[str] = []

        openai_key = resolve_openai_key(self.config)
        if openai_key:
            try:
                result = self._review_with_openai(trade_json, openai_key)
                result.provider = "openai"
                self._remember(signal, result)
                return result
            except Exception as exc:  # noqa: BLE001
                errors.append(f"OpenAI: {exc}")
                self.logger.warning("AI REVIEW OpenAI failed, trying Gemini fallback: %s", exc)

        gemini_key = resolve_gemini_key(self.config)
        if gemini_key:
            try:
                result = self._review_with_gemini(trade_json, gemini_key)
                result.provider = "gemini"
                self._remember(signal, result)
                return result
            except Exception as exc:  # noqa: BLE001
                errors.append(f"Gemini: {exc}")
                self.logger.warning("AI REVIEW Gemini fallback failed: %s", exc)

        reason = "; ".join(errors) if errors else "No LLM provider available"
        result = TradeAiReviewResult(approved=False, confidence=0.0, reason=reason, provider=None)
        self._remember(signal, result)
        return result

    def _remember(self, signal: Signal, result: TradeAiReviewResult) -> None:
        self.last_review = {
            "setup_id": signal.setup_id,
            "symbol": signal.symbol,
            "approved": result.approved,
            "confidence": result.confidence,
            "reason": result.reason,
            "provider": result.provider,
        }

    def _invoke_llm(self, llm, trade_json: str) -> TradeAiReviewResult:
        from langchain_core.output_parsers import PydanticOutputParser
        from langchain_core.prompts import ChatPromptTemplate

        parser = PydanticOutputParser(pydantic_object=TradeAiReviewResult)
        prompt = ChatPromptTemplate.from_messages(
            [
                ("system", self._SYSTEM_PROMPT),
                (
                    "human",
                    "Review this proposed trade setup:\n{trade_json}\n\n{format_instructions}",
                ),
            ]
        )
        chain = prompt | llm | parser
        result = chain.invoke({"trade_json": trade_json, "format_instructions": parser.get_format_instructions()})
        if not isinstance(result, TradeAiReviewResult):
            result = TradeAiReviewResult.model_validate(result)
        return result

    def _review_with_openai(self, trade_json: str, api_key: str) -> TradeAiReviewResult:
        try:
            from langchain_openai import ChatOpenAI
        except ImportError as exc:  # pragma: no cover
            raise RuntimeError("LangChain OpenAI package is not installed. Run `uv sync`.") from exc
        llm = ChatOpenAI(model=resolve_openai_model(self.config), api_key=api_key, temperature=0)
        return self._invoke_llm(llm, trade_json)

    def _review_with_gemini(self, trade_json: str, api_key: str) -> TradeAiReviewResult:
        try:
            from langchain_google_genai import ChatGoogleGenerativeAI
        except ImportError as exc:  # pragma: no cover
            raise RuntimeError("LangChain Gemini packages are not installed. Run `uv sync`.") from exc
        llm = ChatGoogleGenerativeAI(
            model=resolve_gemini_model(self.config),
            google_api_key=api_key,
            temperature=0,
        )
        return self._invoke_llm(llm, trade_json)


def ai_review_status(config: AppConfig, last_review: dict[str, Any] | None = None) -> dict[str, Any]:
    cfg: AiTradeReviewConfig = config.bot.ai_trade_review
    return {
        "enabled": cfg.enabled,
        "use_in_backtest": cfg.use_in_backtest,
        "active_for_strategy": ai_review_applies(config),
        "min_confidence": cfg.min_confidence,
        "strategies": list(cfg.strategies),
        "openai_model": resolve_openai_model(config),
        "openai_api_key_configured": bool(resolve_openai_key(config)),
        "gemini_model": resolve_gemini_model(config),
        "gemini_api_key_configured": bool(resolve_gemini_key(config)),
        "llm_configured": llm_configured(config),
        "last_review": last_review,
    }
