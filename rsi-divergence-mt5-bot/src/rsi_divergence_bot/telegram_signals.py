from __future__ import annotations

import hashlib
import json
import logging
import os
import re
import threading
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Literal

from pydantic import BaseModel, Field, ValidationError

from .config import AppConfig, SymbolConfig, TelegramChannelConfig
from .manual_trade import parse_manual_trade, resolve_symbol_for_telegram
from .mt5_client import MT5Client, _field
from .state import StateStore
from .symbols import market_key, resolve_trade_symbol, settings_mt5_symbol_from_config
from .trade_geometry import default_stop_loss_one_to_one, invalid_market_geometry, synthetic_stop_loss_reference_tp
from .trader import TradeExecutor

from .playwright_runtime import ensure_playwright_runtime, load_sync_playwright, playwright_runtime_error
from .telegram_html_parser import (
    ParsedChatMessage,
    ParseDiagnostics,
    looks_like_ad,
    parse_all_bubbles,
    parse_all_messages,
    parse_chatlist_preview,
    parse_latest_message,
    pick_latest_non_ad,
)

TelegramAction = Literal["buy", "sell", "buy_limit", "sell_limit", "buy_stop", "sell_stop", "none"]


class BrowserSessionError(RuntimeError):
    """Raised when the Playwright browser/context is no longer usable."""

_TELEGRAM_SCROLL_CHAT_JS = """
() => {
  for (const el of document.querySelectorAll('.scrollable.scrollable-y, .bubbles-container .scrollable, .scrollable')) {
    el.scrollTop = el.scrollHeight;
  }
  const inner = document.querySelector('.bubbles-inner');
  if (inner) {
    inner.lastElementChild?.scrollIntoView?.({ block: 'end' });
  }
}
"""

_TELEGRAM_NAVIGATE_CHAT_JS = """
({ hash, name }) => {
  const target = String(hash || '').replace(/^#/, '');
  if (!target) return { ok: false, method: 'missing-hash' };

  const targetVariants = new Set([target]);
  if (/^-\\d+$/.test(target)) {
    if (target.startsWith('-100')) {
      targetVariants.add(target.slice(4));
    } else {
      targetVariants.add(`-100${target.slice(1)}`);
    }
  }

  const matchesTarget = (value) => {
    const raw = String(value || '');
    if (!raw) return false;
    for (const variant of targetVariants) {
      if (raw === variant || raw.includes(variant) || variant.includes(raw)) return true;
    }
    return false;
  };

  const clickRow = (row) => {
    if (!row) return false;
    row.scrollIntoView({ block: 'nearest' });
    row.click();
    return true;
  };

  const titleMatches = (row) => {
    const titleEl = row.querySelector('.peer-title, .dialog-title, .user-title, .title, .name');
    const title = (titleEl?.textContent || row.textContent || '').trim().toLowerCase();
    const wanted = String(name || '').trim().toLowerCase();
    return wanted && title.includes(wanted);
  };

  const rows = Array.from(document.querySelectorAll('.chatlist-chat, .chatlist .chat, .chatlist-chat-padding'));
  for (const row of rows) {
    const peerId = row.getAttribute('data-peer-id') || row.dataset?.peerId || '';
    const href = row.querySelector('a[href]')?.getAttribute('href') || '';
    if (peerId && matchesTarget(peerId)) {
      if (clickRow(row)) return { ok: true, method: 'peer-id', target, peerId };
    }
    if (href && [...targetVariants].some((variant) => href.includes(`#${variant}`) || href.includes(variant))) {
      if (clickRow(row)) return { ok: true, method: 'href', target, href };
    }
    if (titleMatches(row)) {
      if (clickRow(row)) return { ok: true, method: 'title', target, name };
    }
  }

  if (location.hash.slice(1) !== target) {
    location.hash = target;
  }
  return { ok: true, method: 'hash', target, href: location.href };
}
"""

_TELEGRAM_CHAT_HTML_JS = """
() => {
  const selectors = [
    '.bubbles-inner',
    '.bubbles',
    '#column-center .chat',
    '#column-center',
    '.messages-container',
  ];
  for (const selector of selectors) {
    const node = document.querySelector(selector);
    if (!node) continue;
    const html = node.innerHTML || '';
    if (html.trim().length > 80) {
      return { selector, html, url: location.href };
    }
  }
  return { selector: 'document', html: document.documentElement?.outerHTML || '', url: location.href };
}
"""

_TELEGRAM_SCROLL_CHAT_UP_JS = """
() => {
  const scrollers = document.querySelectorAll(
    '#column-center .scrollable.scrollable-y, .bubbles-container .scrollable, .scrollable.scrollable-y'
  );
  for (const el of scrollers) {
    el.scrollTop = Math.max(0, el.scrollTop - Math.max(el.clientHeight * 0.85, 500));
  }
}
"""

_TELEGRAM_CHATLIST_PREVIEW_JS = """
({ hash, name }) => {
  const target = String(hash || '').replace(/^#/, '');
  const targetVariants = new Set([target]);
  if (/^-\\d+$/.test(target)) {
    if (target.startsWith('-100')) targetVariants.add(target.slice(4));
    else targetVariants.add(`-100${target.slice(1)}`);
  }
  const matchesTarget = (value) => {
    const raw = String(value || '');
    if (!raw) return false;
    for (const variant of targetVariants) {
      if (raw === variant || raw.includes(variant) || variant.includes(raw)) return true;
    }
    return false;
  };
  const subtitleSelectors = [
    '.dialog-subtitle',
    '.dialog-subtitle-span-last-message',
    '.dialog-subtitle-span',
    '.row-subtitle',
    '.subtitle',
    '.last-message',
    '.user-last-message',
  ];
  const rows = Array.from(document.querySelectorAll('.chatlist-chat, .chatlist .chat, .chatlist-chat-padding'));
  for (const row of rows) {
    const peerId = row.getAttribute('data-peer-id') || row.dataset?.peerId || '';
    const href = row.querySelector('a[href]')?.getAttribute('href') || '';
    const titleEl = row.querySelector('.peer-title, .dialog-title, .user-title, .title, .name');
    const title = (titleEl?.textContent || '').trim().toLowerCase();
    const wanted = String(name || '').trim().toLowerCase();
    const matched =
      (peerId && matchesTarget(peerId)) ||
      [...targetVariants].some((variant) => href.includes(`#${variant}`) || href.includes(variant)) ||
      (wanted && title && (title.includes(wanted) || wanted.includes(title)));
    if (!matched) continue;
    for (const selector of subtitleSelectors) {
      const node = row.querySelector(selector);
      const text = (node?.innerText || node?.textContent || '').trim();
      if (text) {
        return { text, peerId: peerId || target, source: 'chatlist-preview-js' };
      }
    }
  }
  return null;
}
"""

_TELEGRAM_CHAT_STATE_JS = """
() => {
  const inner = document.querySelector('.bubbles-inner');
  const bubbles = inner ? Array.from(inner.querySelectorAll('.bubble')) : [];
  const readable = bubbles.filter((bubble) => {
    if (bubble.classList.contains('is-date') || bubble.classList.contains('service')) return false;
    const text = (bubble.innerText || bubble.textContent || '').trim();
    return text.length > 0;
  });
  return {
    url: location.href,
    hasChatList: !!document.querySelector('.chatlist, #column-left .chatlist, .chatlist-container'),
    hasBubblesInner: !!inner,
    bubbleCount: bubbles.length,
    readableBubbleCount: readable.length,
    lastBubbleText: readable.length ? (readable[readable.length - 1].innerText || '').trim().slice(0, 180) : '',
  };
}
"""


class ParsedTelegramSignal(BaseModel):
    symbol: str | None = Field(default=None, description="Trading symbol like XAUUSD, EURUSD, BTCUSD, GOLD.")
    action: TelegramAction = Field(description="buy/sell for live market trades, or a pending order type.")
    entry: float | None = Field(default=None, description="Entry price for pending orders. Optional for live buy/sell.")
    stop_loss: float | None = Field(default=None, description="Stop loss price.")
    tps: list[float] = Field(default_factory=list, description="Take profit prices in the planned hit order.")
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)


@dataclass
class TelegramLoopStatus:
    running: bool = False
    started_at: str | None = None
    browser_open: bool = False
    protect_tp: bool = False
    messages_seen: int = 0
    parsed_signals: int = 0
    placed: int = 0
    skipped: int = 0
    failed: int = 0
    last_message_at: str | None = None
    last_action_at: str | None = None
    last_error: str | None = None
    last_channel: str | None = None
    last_signal: dict | None = None
    last_result: dict | None = None
    recent_actions: list[dict] = field(default_factory=list)


@dataclass
class PendingSlWatch:
    message_id: str
    message_key: str | None
    channel: TelegramChannelConfig
    setup_id: str
    tickets: list[int]
    symbol: str
    side: str
    synthetic_sl: float
    started_at: float
    expires_at: float


class GeminiSignalParser:
    _SYSTEM_PROMPT = (
        "You extract trade signals from Telegram messages. "
        "Return only structured output. If the message is not a trade signal, use action='none'. "
        "If the message is a trade update, TP hit, profit report, or reply to an earlier signal, "
        "use action='none' even when BUY/SELL text appears in quoted content. "
        "A fresh signal with symbol + BUY/SELL + SL + one or more TPs is a valid trade even when entry "
        "is written as a range like 4394_4397, 4394-4397, or 4394/4397 — use action='sell' or 'buy' "
        "and leave entry empty for market execution unless it is clearly a pending/limit order. "
        "Use action='buy' or action='sell' for live/now/market trades. "
        "Use buy_limit, sell_limit, buy_stop, or sell_stop for pending orders. "
        "Normalize GOLD/XAU to XAUUSD when clear. Keep prices exactly as written."
    )

    def __init__(self, config: AppConfig, logger: logging.Logger | None = None):
        self.config = config
        self.logger = logger or logging.getLogger(__name__)

    @staticmethod
    def openai_api_key(config: AppConfig) -> str | None:
        key = config.telegram_signals.openai_api_key or os.getenv("OPENAI_API_KEY")
        return key.strip() if key else None

    @staticmethod
    def gemini_api_key(config: AppConfig) -> str | None:
        key = config.telegram_signals.gemini_api_key or os.getenv("GEMINI_API_KEY")
        return key.strip() if key else None

    @classmethod
    def llm_configured(cls, config: AppConfig) -> bool:
        return bool(cls.openai_api_key(config) or cls.gemini_api_key(config))

    def parse(self, message: str) -> ParsedTelegramSignal:
        errors: list[str] = []
        llm_result: ParsedTelegramSignal | None = None
        openai_key = self.openai_api_key(self.config)
        if openai_key:
            try:
                llm_result = self._parse_with_openai(message, openai_key)
                self.logger.info(
                    "TELEGRAM PARSE provider=openai action=%s symbol=%s",
                    llm_result.action,
                    llm_result.symbol,
                )
                if llm_result.action != "none":
                    return llm_result
            except Exception as exc:  # noqa: BLE001
                errors.append(f"OpenAI: {exc}")
                self.logger.warning("TELEGRAM PARSE OpenAI failed, trying Gemini fallback: %s", exc)

        if llm_result is None or llm_result.action == "none":
            gemini_key = self.gemini_api_key(self.config)
            if gemini_key:
                try:
                    llm_result = self._parse_with_gemini(message, gemini_key)
                    self.logger.info(
                        "TELEGRAM PARSE provider=gemini action=%s symbol=%s",
                        llm_result.action,
                        llm_result.symbol,
                    )
                    if llm_result.action != "none":
                        return llm_result
                except Exception as exc:  # noqa: BLE001
                    errors.append(f"Gemini: {exc}")
                    self.logger.warning("TELEGRAM PARSE Gemini fallback failed: %s", exc)

        fallback = fallback_parse_telegram_signal(message, self.config)
        if fallback is not None:
            self.logger.info(
                "TELEGRAM PARSE provider=fallback action=%s symbol=%s sl=%s tps=%s",
                fallback.action,
                fallback.symbol,
                fallback.stop_loss,
                fallback.tps,
            )
            return fallback

        if llm_result is not None:
            return llm_result

        if errors:
            raise RuntimeError("; ".join(errors))
        raise RuntimeError(
            "No LLM API key configured. Set telegram_signals.openai_api_key or OPENAI_API_KEY, "
            "or telegram_signals.gemini_api_key or GEMINI_API_KEY."
        )

    def _invoke_llm(self, llm, message: str) -> ParsedTelegramSignal:
        from langchain_core.output_parsers import PydanticOutputParser
        from langchain_core.prompts import ChatPromptTemplate

        parser = PydanticOutputParser(pydantic_object=ParsedTelegramSignal)
        prompt = ChatPromptTemplate.from_messages(
            [
                ("system", self._SYSTEM_PROMPT),
                ("human", "Message:\n{message}\n\n{format_instructions}"),
            ]
        )
        chain = prompt | llm | parser
        result = chain.invoke({"message": message, "format_instructions": parser.get_format_instructions()})
        if not isinstance(result, ParsedTelegramSignal):
            result = ParsedTelegramSignal.model_validate(result)
        return result

    def _parse_with_openai(self, message: str, api_key: str) -> ParsedTelegramSignal:
        try:
            from langchain_openai import ChatOpenAI
        except ImportError as exc:  # pragma: no cover
            raise RuntimeError("LangChain OpenAI package is not installed. Run `uv sync`.") from exc
        llm = ChatOpenAI(model=self.config.telegram_signals.openai_model, api_key=api_key, temperature=0)
        return self._invoke_llm(llm, message)

    def _parse_with_gemini(self, message: str, api_key: str) -> ParsedTelegramSignal:
        try:
            from langchain_google_genai import ChatGoogleGenerativeAI
        except ImportError as exc:  # pragma: no cover
            raise RuntimeError("LangChain Gemini packages are not installed. Run `uv sync`.") from exc
        llm = ChatGoogleGenerativeAI(
            model=self.config.telegram_signals.gemini_model,
            google_api_key=api_key,
            temperature=0,
        )
        return self._invoke_llm(llm, message)


TelegramSignalParser = GeminiSignalParser


class TelegramSignalsBot:
    def __init__(
        self,
        config: AppConfig,
        client: MT5Client,
        state: StateStore,
        logger: logging.Logger,
        daily_risk_status: Callable[[], dict] | None = None,
        config_path: Path | None = None,
    ):
        self.config = config
        self.config_path = config_path
        self.client = client
        self.state = state
        self.logger = logger
        self.daily_risk_status = daily_risk_status
        self.parser = GeminiSignalParser(config, logger)
        self.executor = TradeExecutor(config, client, state, logger)
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None
        self._status = TelegramLoopStatus()
        self._seen_messages: set[str] = set()
        self._channel_pages: dict[str, object] = {}
        self._open_market_keys: set[str] = set()
        self._open_market_keys_at: float = 0.0
        self._pending_sl_watches: dict[str, PendingSlWatch] = {}

    def start(self, *, protect_tp: bool = False) -> dict:
        if self.is_running():
            return self.status()
        ok, runtime_error = ensure_playwright_runtime()
        if not ok:
            self._status.last_error = runtime_error
            self.logger.error("TELEGRAM SIGNALS start blocked: %s", runtime_error)
            return {**self.status(), "start_error": runtime_error}
        self._stop_event.clear()
        self._status = TelegramLoopStatus(
            running=True,
            started_at=datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
            protect_tp=protect_tp,
        )
        self._thread = threading.Thread(target=self._loop, name="telegram-signals-copy", daemon=True)
        self._thread.start()
        self.logger.warning(
            "TELEGRAM SIGNALS START poll=%ss protect_tp=%s ignore_open_symbol_trades=%s dry_run=%s",
            self.config.telegram_signals.poll_seconds,
            protect_tp,
            self.config.telegram_signals.ignore_open_symbol_trades,
            self.config.bot.dry_run,
        )
        return self.status()

    def stop(self) -> dict:
        if not self.is_running():
            self._status.running = False
            return self.status()
        self.logger.info("TELEGRAM SIGNALS STOP requested")
        self._stop_event.set()
        if self._thread is not None:
            self._thread.join(timeout=self.config.telegram_signals.poll_seconds + 15)
        self._status.running = False
        return self.status()

    def is_running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    def status(self) -> dict:
        data = asdict(self._status)
        data["running"] = self.is_running()
        data["poll_seconds"] = self.config.telegram_signals.poll_seconds
        data["ignore_open_symbol_trades"] = self.config.telegram_signals.ignore_open_symbol_trades
        data["protect_tp"] = self.config.telegram_signals.protect_tp
        data["openai_model"] = self.config.telegram_signals.openai_model
        data["openai_api_key_configured"] = bool(GeminiSignalParser.openai_api_key(self.config))
        data["gemini_model"] = self.config.telegram_signals.gemini_model
        data["gemini_api_key_configured"] = bool(GeminiSignalParser.gemini_api_key(self.config))
        data["llm_configured"] = GeminiSignalParser.llm_configured(self.config)
        data["channels"] = [channel.model_dump(mode="python") for channel in self.config.telegram_signals.channels]
        data["enabled_channel_count"] = len(self._enabled_channels())
        data["recent_messages"] = self.state.recent_telegram_messages(100)
        if self._status.last_action_at or self._status.last_result:
            data["last_action"] = {
                "at": self._status.last_action_at,
                "channel": self._status.last_channel,
                "signal": self._status.last_signal,
                "result": self._status.last_result,
            }
        else:
            data["last_action"] = None
        data["recent_actions"] = list(self._status.recent_actions[-40:])
        data["pending_sl_watches"] = len(self._pending_sl_watches)
        return data

    def _push_action_log(
        self,
        kind: str,
        status: str,
        *,
        channel: str | None = None,
        symbol: str | None = None,
        reason: str | None = None,
        hard_copy: bool = False,
        result: dict | None = None,
    ) -> None:
        at = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
        entry: dict = {
            "at": at,
            "kind": kind,
            "status": status,
            "channel": channel,
            "symbol": symbol,
            "reason": reason,
            "hard_copy": hard_copy,
        }
        if result:
            entry["result"] = {
                key: result.get(key)
                for key in (
                    "status",
                    "reason",
                    "symbol",
                    "action",
                    "side",
                    "ticket",
                    "tickets",
                    "legs",
                    "entry_price",
                    "tickets",
                    "hard_copy",
                    "message_id",
                )
                if result.get(key) is not None
            }
        self._status.recent_actions.append(entry)
        if len(self._status.recent_actions) > 50:
            self._status.recent_actions = self._status.recent_actions[-50:]
        if status in {"failed", "error", "skipped"} and reason:
            self._status.last_error = reason

    def clear_message_history(self) -> dict:
        removed = self.state.clear_telegram_history()
        self._seen_messages.clear()
        self._status.messages_seen = 0
        self._status.parsed_signals = 0
        self._status.placed = 0
        self._status.skipped = 0
        self._status.failed = 0
        self._status.last_message_at = None
        self._status.last_action_at = None
        self._status.last_signal = None
        self._status.last_result = None
        self._status.recent_actions = []
        self.logger.info(
            "TELEGRAM history cleared messages=%s seen_ids=%s",
            removed["messages_removed"],
            removed["seen_removed"],
        )
        return {"status": "cleared", **removed, **self.status()}

    def hard_copy_message(self, message_id: str) -> dict:
        cleaned_id = str(message_id or "").strip()
        if not cleaned_id:
            return {"status": "error", "reason": "message_id is required"}

        record = self.state.get_telegram_message(cleaned_id)
        if record is None:
            preview = cleaned_id[:12]
            return {
                "status": "error",
                "reason": (
                    f"Message {preview}… was not found in the ledger. "
                    "Refresh the page or wait for the copier to sync this chat again."
                ),
            }

        text = str(record.get("text") or record.get("text_preview") or "").strip()
        if not text:
            return {"status": "error", "reason": "Message has no text to copy"}

        if _looks_like_breakeven(text):
            return {"status": "error", "reason": "Breakeven/update messages cannot be hard copied"}

        channel = self._channel_from_record(record)
        parsed_data = record.get("parsed")
        if isinstance(parsed_data, dict) and parsed_data.get("action") not in {None, "none"}:
            try:
                parsed = ParsedTelegramSignal.model_validate(parsed_data)
            except ValidationError as exc:
                first = exc.errors()[0] if exc.errors() else {}
                detail = first.get("msg") or str(exc)
                return {"status": "error", "reason": f"Stored parse data is invalid: {detail}"}
        else:
            try:
                parsed = self.parser.parse(text)
            except Exception as exc:  # noqa: BLE001
                return {"status": "error", "reason": f"Parse failed: {exc}"}

        if parsed.action == "none":
            return {
                "status": "error",
                "reason": "Message is not a trade signal (LLM returned action=none)",
            }

        source_id = f"{cleaned_id}:hard:{int(datetime.now(timezone.utc).timestamp())}"
        result = self._place_parsed_signal(
            parsed,
            source_id=source_id,
            channel=channel,
            hard=True,
            message_id=cleaned_id,
            message_key=record.get("message_key"),
        )
        result["hard_copy"] = True
        result["message_id"] = cleaned_id

        self._record_message(
            cleaned_id,
            str(result.get("status", "unknown")),
            text,
            channel=channel,
            parsed=parsed.model_dump(mode="python"),
            result=result,
            reason=result.get("reason"),
            message_key=record.get("message_key"),
            message_timestamp=record.get("message_timestamp"),
            age_seconds=record.get("age_seconds"),
        )
        self._status.last_signal = parsed.model_dump(mode="python")
        self._status.last_result = result
        self._status.last_action_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
        status = str(result.get("status", "unknown"))
        reason = str(result.get("reason") or "")
        if status in {"failed", "skipped", "error"} and not reason:
            reason = f"hard copy {status}"
        self._push_action_log(
            "hard_copy",
            status,
            channel=channel.name,
            symbol=str(result.get("symbol") or parsed.symbol or ""),
            reason=reason or None,
            hard_copy=True,
            result=result,
        )
        if result["status"] in {"placed", "paper"}:
            self._status.placed += 1
        elif result["status"] == "failed":
            self._status.failed += 1
        else:
            self._status.skipped += 1
        self.logger.warning(
            "TELEGRAM HARD COPY message=%s channel=%s status=%s symbol=%s action=%s reason=%s",
            cleaned_id[:10],
            channel.name,
            result.get("status"),
            result.get("symbol"),
            parsed.action,
            reason or result.get("reason"),
        )
        return result

    def _channel_from_record(self, record: dict) -> TelegramChannelConfig:
        name = str(record.get("channel_name") or "Unknown")
        url = str(record.get("channel_url") or "")
        for channel in self.config.telegram_signals.channels:
            if channel.url == url or channel.name.casefold() == name.casefold():
                return channel
        return TelegramChannelConfig(name=name, url=url, enabled=True)

    def _loop(self) -> None:
        playwright = None
        context = None
        profile_dir = self._browser_profile_dir()
        try:
            sync_playwright = load_sync_playwright()
            playwright = sync_playwright().start()
            context = self._start_browser_session(playwright, profile_dir)
            self.logger.warning(
                "TELEGRAM SIGNALS browser opened with %s channel window(s). Login if asked. channels=%s",
                len(self._channel_pages),
                [channel.name for channel in self._enabled_channels()],
            )

            while not self._stop_event.is_set():
                try:
                    context = self._ensure_browser_session(playwright, profile_dir, context)
                    if self._status.protect_tp:
                        self._manage_tp_protection(enabled=True)
                    channels = self._enabled_channels()
                    self._sync_channel_pages(context, channels)
                    open_market_keys = self._cached_open_market_keys()
                    self.logger.info(
                        "TELEGRAM ROUND channels=%s windows=%s open_markets=%s",
                        [channel.name for channel in channels],
                        len(self._channel_pages),
                        len(open_market_keys),
                    )
                    for channel in channels:
                        try:
                            page = self._ensure_channel_page(context, channel)
                            self._read_channel(page, channel, open_market_keys=open_market_keys)
                        except BrowserSessionError as exc:
                            self._status.last_error = str(exc)
                            self.logger.warning(
                                "TELEGRAM browser session lost while reading %s: %s",
                                channel.name,
                                exc,
                            )
                            context = self._restart_browser_session(playwright, profile_dir, context)
                            break
                        except Exception as exc:  # noqa: BLE001
                            if self._is_browser_closed_error(exc):
                                self._status.last_error = str(exc)
                                self.logger.warning(
                                    "TELEGRAM browser closed while reading %s: %s",
                                    channel.name,
                                    exc,
                                )
                                context = self._restart_browser_session(playwright, profile_dir, context)
                                break
                            self._status.last_error = f"{channel.name}: {exc}"
                            self.logger.exception(
                                "TELEGRAM CHANNEL READ ERROR channel=%s url=%s error=%s",
                                channel.name,
                                channel.url,
                                exc,
                            )
                    else:
                        self._status.last_error = None
                except BrowserSessionError as exc:
                    self._status.last_error = str(exc)
                    self.logger.warning("TELEGRAM browser session lost: %s", exc)
                    context = self._restart_browser_session(playwright, profile_dir, context)
                except Exception as exc:  # noqa: BLE001
                    if self._is_browser_closed_error(exc):
                        self._status.last_error = str(exc)
                        self.logger.warning("TELEGRAM browser closed: %s", exc)
                        context = self._restart_browser_session(playwright, profile_dir, context)
                    else:
                        self._status.last_error = str(exc)
                        self.logger.exception("TELEGRAM SIGNALS loop error: %s", exc)

                if self._stop_event.wait(self.config.telegram_signals.poll_seconds):
                    break
        except ImportError as exc:
            message = playwright_runtime_error(exc)
            self._status.last_error = message
            self.logger.error("TELEGRAM SIGNALS failed to start: %s", message)
        except Exception as exc:  # noqa: BLE001
            self._status.last_error = str(exc)
            self.logger.exception("TELEGRAM SIGNALS failed to start: %s", exc)
        finally:
            self._status.running = False
            self._status.browser_open = False
            self._channel_pages = {}
            self._close_browser_session(playwright, context)
            self.logger.info("TELEGRAM SIGNALS stopped")

    def _browser_profile_dir(self) -> Path:
        profile_dir = Path(self.config.telegram_signals.browser_user_data_dir)
        if not profile_dir.is_absolute():
            profile_dir = Path(self.config.bot.state_file).resolve().parent.parent / profile_dir
        profile_dir.mkdir(parents=True, exist_ok=True)
        return profile_dir

    @staticmethod
    def _is_browser_closed_error(exc: BaseException) -> bool:
        message = str(exc).casefold()
        return "target page, context or browser has been closed" in message or "browser has been closed" in message

    @staticmethod
    def _context_alive(context) -> bool:
        if context is None:
            return False
        try:
            browser = context.browser
            return browser is not None and browser.is_connected()
        except Exception:  # noqa: BLE001
            return False

    @staticmethod
    def _page_alive(page) -> bool:
        if page is None:
            return False
        try:
            return not page.is_closed()
        except Exception:  # noqa: BLE001
            return False

    def _close_browser_session(self, playwright, context) -> None:
        try:
            if context is not None:
                context.close()
        except Exception:  # noqa: BLE001
            pass
        try:
            if playwright is not None:
                playwright.stop()
        except Exception:  # noqa: BLE001
            pass

    def _start_browser_session(self, playwright, profile_dir: Path):
        self._channel_pages = {}
        context = self._open_browser(playwright, profile_dir)
        channels = self._enabled_channels()
        self._channel_pages = self._open_all_channel_windows(context, channels)
        self._status.browser_open = True
        return context

    def _restart_browser_session(self, playwright, profile_dir: Path, context):
        self.logger.warning("TELEGRAM restarting browser session")
        try:
            if context is not None:
                context.close()
        except Exception:  # noqa: BLE001
            pass
        self._channel_pages = {}
        self._status.browser_open = False
        try:
            return self._start_browser_session(playwright, profile_dir)
        except Exception as exc:  # noqa: BLE001
            raise BrowserSessionError(f"Failed to restart Telegram browser: {exc}") from exc

    def _ensure_browser_session(self, playwright, profile_dir: Path, context):
        if self._context_alive(context):
            return context
        return self._restart_browser_session(playwright, profile_dir, context)

    def _enabled_channels(self) -> list[TelegramChannelConfig]:
        return [channel for channel in self.config.telegram_signals.channels if channel.enabled]

    def _sync_channel_pages(self, context, channels: list[TelegramChannelConfig]) -> None:
        enabled_urls = {channel.url for channel in channels}
        for url, page in list(self._channel_pages.items()):
            if url in enabled_urls:
                continue
            try:
                if page is not None and not page.is_closed():
                    page.close()
            except Exception:  # noqa: BLE001
                pass
            self._channel_pages.pop(url, None)

    def _manage_tp_protection(self, *, enabled: bool = True) -> None:
        self.executor.manage_tp_protection(enabled=enabled)

    def _cached_open_market_keys(self, *, ttl_seconds: float = 4.0) -> set[str]:
        now = time.monotonic()
        if now - self._open_market_keys_at < ttl_seconds and self._open_market_keys_at > 0:
            return self._open_market_keys
        keys: set[str] = set()
        try:
            for pos in self.client.positions() or []:
                symbol = str(_field(pos, "symbol", ""))
                if symbol:
                    keys.add(market_key(symbol))
        except Exception as exc:  # noqa: BLE001
            self.logger.warning("TELEGRAM open-market lookup failed: %s", exc)
            return self._open_market_keys
        self._open_market_keys = keys
        self._open_market_keys_at = now
        return keys

    def _open_browser(self, playwright, profile_dir: Path):
        try:
            return playwright.chromium.launch_persistent_context(
                str(profile_dir),
                channel="chrome",
                headless=False,
                viewport={"width": 1280, "height": 900},
            )
        except Exception:
            return playwright.chromium.launch_persistent_context(
                str(profile_dir),
                headless=False,
                viewport={"width": 1280, "height": 900},
            )

    @staticmethod
    def _channel_hash(url: str) -> str:
        if "#" not in url:
            return ""
        return url.split("#", 1)[1]

    @staticmethod
    def _telegram_base_url(url: str) -> str:
        return url.split("#", 1)[0].rstrip("/")

    def _wait_for_telegram_ready(self, page) -> None:
        try:
            page.wait_for_selector(
                ".chatlist, #column-left .chatlist, .chatlist-container, .bubbles-inner",
                timeout=90_000,
            )
        except Exception:  # noqa: BLE001
            self.logger.warning("TELEGRAM chat list did not appear within 90s; login may still be required")
        page.wait_for_timeout(1500)

    def _open_all_channel_windows(self, context, channels: list[TelegramChannelConfig]) -> dict[str, object]:
        if not self._context_alive(context):
            raise BrowserSessionError("browser context closed before opening channel windows")
        pages: dict[str, object] = {}
        for index, channel in enumerate(channels):
            page = self._allocate_channel_page(context, channel.url, prefer_existing=index == 0)
            self.logger.info("TELEGRAM WINDOW OPEN channel=%s url=%s", channel.name, channel.url)
            page.goto(channel.url, wait_until="domcontentloaded", timeout=60_000)
            if index == 0:
                self._wait_for_telegram_ready(page)
            self._wait_for_chat_messages(page, channel)
            self._scroll_chat_to_bottom(page)
            pages[channel.url] = page
            page.wait_for_timeout(400)
        return pages

    @staticmethod
    def _channel_hash_variants(url: str) -> set[str]:
        target = TelegramSignalsBot._channel_hash(url).replace("#", "")
        if not target:
            return set()
        variants = {target}
        if re.fullmatch(r"-\d+", target):
            if target.startswith("-100"):
                variants.add(target[4:])
            else:
                variants.add(f"-100{target[1:]}")
        return variants

    def _channel_page_on_target(self, page, channel: TelegramChannelConfig) -> bool:
        if not self._page_alive(page):
            return False
        variants = self._channel_hash_variants(channel.url)
        if not variants:
            return True
        try:
            current = str(page.url or "")
        except Exception:  # noqa: BLE001
            return False
        current_hash = current.split("#", 1)[1] if "#" in current else ""
        if current_hash in variants:
            return True
        return any(f"#{variant}" in current or variant in current_hash or current_hash in variant for variant in variants)

    def _allocate_channel_page(self, context, channel_url: str, *, prefer_existing: bool = False):
        if not self._context_alive(context):
            raise BrowserSessionError("browser context closed")
        for url, page in list(self._channel_pages.items()):
            if url == channel_url and self._page_alive(page):
                return page
            if not self._page_alive(page):
                self._channel_pages.pop(url, None)
        assigned = {id(page) for page in self._channel_pages.values() if self._page_alive(page)}
        if prefer_existing and context.pages:
            for page in context.pages:
                if self._page_alive(page) and id(page) not in assigned:
                    self._channel_pages[channel_url] = page
                    return page
        try:
            page = context.new_page()
        except Exception as exc:  # noqa: BLE001
            raise BrowserSessionError(str(exc)) from exc
        self._channel_pages[channel_url] = page
        return page

    def _ensure_channel_page(self, context, channel: TelegramChannelConfig):
        if not self._context_alive(context):
            raise BrowserSessionError("browser context closed")

        page = self._channel_pages.get(channel.url)
        if self._page_alive(page) and self._channel_page_on_target(page, channel):
            return page

        if self._page_alive(page):
            self.logger.info("TELEGRAM NAVIGATE channel=%s url=%s", channel.name, channel.url)
            self._open_channel_page(page, channel)
            self._channel_pages[channel.url] = page
            return page

        self.logger.warning("TELEGRAM WINDOW REOPEN channel=%s url=%s", channel.name, channel.url)
        page = self._allocate_channel_page(context, channel.url)
        page.goto(channel.url, wait_until="domcontentloaded", timeout=45_000)
        self._wait_for_chat_messages(page, channel)
        self._scroll_chat_to_bottom(page, attempts=2)
        self._channel_pages[channel.url] = page
        return page

    def _open_channel_page(self, page, channel: TelegramChannelConfig) -> dict:
        target_hash = self._channel_hash(channel.url)
        base_url = self._telegram_base_url(self.config.telegram_signals.telegram_url)
        if not page.url.startswith(base_url):
            page.goto(base_url, wait_until="domcontentloaded", timeout=60_000)
            self._wait_for_telegram_ready(page)

        nav = page.evaluate(
            _TELEGRAM_NAVIGATE_CHAT_JS,
            {"hash": target_hash, "name": channel.name},
        )
        page.wait_for_timeout(600)
        self._wait_for_chat_messages(page, channel)
        self._scroll_chat_to_bottom(page)
        return nav or {}

    def _wait_for_chat_messages(self, page, channel: TelegramChannelConfig) -> None:
        deadline_ms = 12_000
        try:
            page.wait_for_function(
                """
                () => {
                  const inner = document.querySelector('.bubbles-inner');
                  if (!inner) return false;
                  const bubbles = [...inner.querySelectorAll('.bubble')].filter((bubble) =>
                    !bubble.classList.contains('is-date') &&
                    !bubble.classList.contains('service') &&
                    !bubble.classList.contains('is-fake')
                  );
                  return bubbles.length > 0;
                }
                """,
                timeout=deadline_ms,
            )
            return
        except Exception:  # noqa: BLE001
            pass

        for attempt in range(3):
            page.evaluate(_TELEGRAM_NAVIGATE_CHAT_JS, {"hash": self._channel_hash(channel.url), "name": channel.name})
            page.wait_for_timeout(500 + attempt * 250)
            state = page.evaluate(_TELEGRAM_CHAT_STATE_JS)
            if state.get("readableBubbleCount", 0) > 0 or state.get("bubbleCount", 0) > 0:
                return

        page.goto(channel.url, wait_until="domcontentloaded", timeout=60_000)
        page.wait_for_timeout(1200)

    def _scroll_chat_to_bottom(self, page, *, attempts: int = 2) -> None:
        for _ in range(attempts):
            page.evaluate(_TELEGRAM_SCROLL_CHAT_JS)
            page.wait_for_timeout(250)

    def _capture_chat_html(self, page) -> tuple[str, str]:
        payload = page.evaluate(_TELEGRAM_CHAT_HTML_JS)
        html = str(payload.get("html") or "")
        source = str(payload.get("selector") or "unknown")
        if len(html.strip()) > 80:
            return html, source
        return page.content(), "document"

    def _read_channel(
        self,
        page,
        channel: TelegramChannelConfig,
        *,
        open_market_keys: set[str] | None = None,
    ) -> None:
        self._scroll_chat_to_bottom(page, attempts=1)
        self._status.last_channel = channel.name
        self._sync_visible_messages(page, channel)
        self._refresh_pending_sl_watches(page, channel)

        message, diagnostics, skipped_ad = self._read_latest_message(page, channel)
        now = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
        self._status.last_message_at = now

        if not message:
            state = page.evaluate(_TELEGRAM_CHAT_STATE_JS)
            self.logger.info(
                "TELEGRAM POLL channel=%s last=none skipped_ad=%s state=%s parse=%s",
                channel.name,
                skipped_ad,
                state,
                asdict(diagnostics),
            )
            reason = self._empty_reason(state, diagnostics, skipped_ad=skipped_ad)
            self._record_message(
                self._channel_poll_id(channel),
                "empty",
                state.get("lastBubbleText") or "",
                channel=channel,
                reason=reason,
                message_key=None,
                message_timestamp=None,
                age_seconds=None,
            )
            return

        payload = {
            "key": message.key,
            "text": message.text,
            "timestamp": message.timestamp,
        }
        message_id = self._message_id(channel, payload["text"], message_key=payload.get("key"))
        age_seconds = self._message_age(payload.get("timestamp"))
        preview = payload["text"][:220].replace("\n", " | ")
        self.logger.info(
            "TELEGRAM POLL channel=%s mid=%s age=%s source=%s skipped_ad=%s last=%s",
            channel.name,
            (str(payload.get("key") or "")[:16] or message_id[:10]),
            self._format_age(age_seconds),
            message.source,
            skipped_ad,
            preview,
        )

        seen = message_id in self._seen_messages or self.state.is_seen(f"telegram:{message_id}")
        max_age = self.config.telegram_signals.max_message_age_seconds
        stale = age_seconds is not None and age_seconds > max_age

        if seen:
            status, reason = "watching", "latest message already processed"
        elif stale:
            status, reason = "stale", f"message age {age_seconds:.0f}s exceeds {max_age}s"
        else:
            status, reason = "latest", "new latest message"

        self._record_message(
            message_id,
            status,
            payload["text"],
            channel=channel,
            reason=reason,
            message_key=payload.get("key"),
            message_timestamp=payload.get("timestamp"),
            age_seconds=age_seconds,
        )

        if seen:
            return

        if stale:
            self._seen_messages.add(message_id)
            self.state.mark_seen(f"telegram:{message_id}")
            return

        self._process_new_message(
            channel,
            payload["text"],
            message_id=message_id,
            message_key=payload.get("key"),
            message_timestamp=payload.get("timestamp"),
            open_market_keys=open_market_keys,
        )

    def _sync_visible_messages(self, page, channel: TelegramChannelConfig, *, limit: int = 20) -> None:
        html, source = self._capture_chat_html(page)
        bubbles, _diagnostics = parse_all_bubbles(html, source=source)
        if not bubbles:
            return
        for bubble in bubbles[-limit:]:
            message_id = self._message_id(channel, bubble.text, message_key=bubble.key or None)
            existing = self.state.get_telegram_message(message_id)
            if bubble.is_reply:
                if existing and existing.get("status") in {"placed", "paper", "detected", "parse_failed"}:
                    if not existing.get("is_reply"):
                        continue
                self._record_message(
                    message_id,
                    "skipped",
                    bubble.text,
                    channel=channel,
                    reason="reply message (quoted parent)",
                    message_key=bubble.key or None,
                    message_timestamp=bubble.timestamp,
                    age_seconds=self._message_age(bubble.timestamp),
                    is_reply=True,
                )
                continue
            if existing is not None:
                continue
            self._record_message(
                message_id,
                "seen",
                bubble.text,
                channel=channel,
                reason="visible in chat history",
                message_key=bubble.key or None,
                message_timestamp=bubble.timestamp,
                age_seconds=self._message_age(bubble.timestamp),
                is_reply=False,
            )

    @staticmethod
    def _empty_reason(state: dict, diagnostics, *, skipped_ad: bool = False) -> str:
        if skipped_ad:
            return "latest message(s) look like ads; no earlier readable message found"
        if not state.get("hasChatList"):
            return "Telegram chat list not loaded; login to Telegram Web in the opened browser"
        if not state.get("hasBubblesInner"):
            return "chat did not open; check channel URL or subscription access"
        if diagnostics.bubble_count > 0 and diagnostics.message_count == 0:
            return "messages loaded but HTML parser found no text nodes in bubbles"
        if state.get("bubbleCount", 0) > 0 and not state.get("lastBubbleText"):
            return "last message has no readable text (media/sticker only)"
        if diagnostics.html_length <= 80:
            return "chat HTML was empty after navigation"
        return "no readable last message in chat"

    def _scroll_chat_up(self, page, *, attempts: int = 2) -> None:
        for _ in range(attempts):
            page.evaluate(_TELEGRAM_SCROLL_CHAT_UP_JS)
            page.wait_for_timeout(500)

    def _read_latest_message(
        self,
        page,
        channel: TelegramChannelConfig,
    ) -> tuple[ParsedChatMessage | None, ParseDiagnostics, bool]:
        last_diagnostics = ParseDiagnostics()
        skipped_ad = False

        for attempt in range(3):
            self._scroll_chat_to_bottom(page, attempts=1)
            page.wait_for_timeout(250 + attempt * 150)
            html, source = self._capture_chat_html(page)
            candidates, diagnostics = parse_all_messages(html, source=source)
            last_diagnostics = diagnostics

            chosen, skipped_ad = self._pick_clean_message(candidates)
            if chosen is not None:
                return chosen, diagnostics, skipped_ad

            if skipped_ad or diagnostics.reply_count > 0:
                self._scroll_chat_up(page, attempts=2)
                continue

        for scroll_up_pass in range(2):
            self._scroll_chat_up(page, attempts=1)
            page.wait_for_timeout(400)
            html, source = self._capture_chat_html(page)
            candidates, diagnostics = parse_all_messages(html, source=source)
            last_diagnostics = diagnostics
            chosen, pass_skipped = self._pick_clean_message(candidates)
            skipped_ad = skipped_ad or pass_skipped
            if chosen is not None:
                return chosen, diagnostics, skipped_ad

        page_html = page.content()
        preview = parse_chatlist_preview(
            page_html,
            channel_hash=self._channel_hash(channel.url),
            channel_name=channel.name,
        )
        if preview is not None:
            chosen, pass_skipped = self._pick_clean_message([preview])
            skipped_ad = skipped_ad or pass_skipped
            if chosen is not None:
                return chosen, last_diagnostics, skipped_ad

        raw_preview = page.evaluate(
            _TELEGRAM_CHATLIST_PREVIEW_JS,
            {"hash": self._channel_hash(channel.url), "name": channel.name},
        )
        if raw_preview and raw_preview.get("text"):
            preview = ParsedChatMessage(
                key=f"preview:{raw_preview.get('peerId') or channel.name}",
                text=_clean_message(str(raw_preview["text"])),
                timestamp=None,
                source=str(raw_preview.get("source") or "chatlist-preview-js"),
            )
            if preview.text:
                chosen, pass_skipped = self._pick_clean_message([preview])
                skipped_ad = skipped_ad or pass_skipped
                if chosen is not None:
                    return chosen, last_diagnostics, skipped_ad

        return None, last_diagnostics, skipped_ad

    @staticmethod
    def _pick_clean_message(
        candidates: list[ParsedChatMessage],
    ) -> tuple[ParsedChatMessage | None, bool]:
        cleaned: list[ParsedChatMessage] = []
        for message in candidates:
            text = _clean_message(message.text)
            if not text:
                continue
            cleaned.append(
                ParsedChatMessage(
                    key=message.key,
                    text=text,
                    timestamp=message.timestamp,
                    source=message.source,
                )
            )
        if not cleaned:
            return None, False
        chosen, skipped_ad = pick_latest_non_ad(cleaned)
        return chosen, skipped_ad

    def _channel_poll_id(self, channel: TelegramChannelConfig) -> str:
        return hashlib.sha256(f"{channel.url}\n__poll__".encode("utf-8")).hexdigest()

    def _message_age(self, message_timestamp: float | None) -> float | None:
        if message_timestamp is None:
            return None
        return max(0.0, datetime.now(timezone.utc).timestamp() - float(message_timestamp))

    def _format_age(self, age_seconds: float | None) -> str:
        if age_seconds is None:
            return "unknown"
        if age_seconds < 60:
            return f"{age_seconds:.0f}s"
        if age_seconds < 3600:
            return f"{age_seconds / 60:.1f}m"
        return f"{age_seconds / 3600:.1f}h"

    def _process_new_message(
        self,
        channel: TelegramChannelConfig,
        message: str,
        *,
        message_id: str,
        message_key: str | None = None,
        message_timestamp: float | None = None,
        open_market_keys: set[str] | None = None,
    ) -> None:
        if _looks_like_breakeven(message):
            self._seen_messages.add(message_id)
            self.state.mark_seen(f"telegram:{message_id}")
            self._status.messages_seen += 1
            self._status.last_channel = channel.name
            self.logger.info(
                "TELEGRAM BREAKEVEN channel=%s hash=%s text=%s",
                channel.name,
                message_id[:10],
                message[:220].replace("\n", " | "),
            )
            result = self._apply_channel_breakeven(channel)
            self._record_message(
                message_id,
                str(result.get("status", "unknown")),
                message,
                channel=channel,
                result=result,
                reason=str(result.get("reason") or ""),
                message_key=message_key,
                message_timestamp=message_timestamp,
                age_seconds=self._message_age(message_timestamp),
            )
            self._status.last_result = result
            self._status.last_action_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
            if result.get("status") == "skipped":
                self._status.skipped += 1
            elif result.get("status") == "failed":
                self._status.failed += 1
            return

        if len(message.strip()) < 8:
            self._seen_messages.add(message_id)
            self.state.mark_seen(f"telegram:{message_id}")
            self._record_message(
                message_id,
                "skipped",
                message,
                channel=channel,
                reason="message too short to parse",
                message_key=message_key,
                message_timestamp=message_timestamp,
                age_seconds=self._message_age(message_timestamp),
            )
            self.logger.info("TELEGRAM SKIP channel=%s short message hash=%s", channel.name, message_id[:10])
            return

        if _looks_like_trade_update(message):
            self._seen_messages.add(message_id)
            self.state.mark_seen(f"telegram:{message_id}")
            self._status.messages_seen += 1
            self._status.skipped += 1
            self._status.last_channel = channel.name
            self._record_message(
                message_id,
                "skipped",
                message,
                channel=channel,
                reason="trade update / reply message",
                message_key=message_key,
                message_timestamp=message_timestamp,
                age_seconds=self._message_age(message_timestamp),
            )
            self.logger.info(
                "TELEGRAM SKIP channel=%s trade update hash=%s text=%s",
                channel.name,
                message_id[:10],
                message[:220].replace("\n", " | "),
            )
            return

        self._seen_messages.add(message_id)
        self.state.mark_seen(f"telegram:{message_id}")
        self._record_message(
            message_id,
            "detected",
            message,
            channel=channel,
            message_key=message_key,
            message_timestamp=message_timestamp,
            age_seconds=self._message_age(message_timestamp),
        )
        self._status.messages_seen += 1
        self._status.last_channel = channel.name
        self.logger.info(
            "TELEGRAM MESSAGE channel=%s hash=%s text=%s",
            channel.name,
            message_id[:10],
            message[:220].replace("\n", " | "),
        )

        try:
            parsed = self.parser.parse(message)
        except Exception as exc:  # noqa: BLE001
            self._status.failed += 1
            self._record_message(
                message_id,
                "parse_failed",
                message,
                channel=channel,
                reason=str(exc),
                message_key=message_key,
                message_timestamp=message_timestamp,
                age_seconds=self._message_age(message_timestamp),
            )
            self.logger.exception("TELEGRAM PARSE FAILED channel=%s hash=%s: %s", channel.name, message_id[:10], exc)
            return

        self._status.last_signal = parsed.model_dump(mode="python")
        if parsed.action == "none":
            self._status.skipped += 1
            self._record_message(
                message_id,
                "skipped",
                message,
                channel=channel,
                parsed=parsed.model_dump(mode="python"),
                reason="LLM returned action=none",
                message_key=message_key,
                message_timestamp=message_timestamp,
                age_seconds=self._message_age(message_timestamp),
            )
            self.logger.info("TELEGRAM SKIP channel=%s no trade signal hash=%s", channel.name, message_id[:10])
            return

        self._status.parsed_signals += 1
        trade_hash = telegram_trade_fingerprint(channel, parsed)
        result = self._place_parsed_signal(
            parsed,
            source_id=message_id,
            channel=channel,
            trade_hash=trade_hash,
            open_market_keys=open_market_keys,
            message_id=message_id,
            message_key=message_key,
        )
        self._record_message(
            message_id,
            str(result.get("status", "unknown")),
            message,
            channel=channel,
            parsed=parsed.model_dump(mode="python"),
            result=result,
            reason=result.get("reason"),
            message_key=message_key,
            message_timestamp=message_timestamp,
            age_seconds=self._message_age(message_timestamp),
            trade_hash=trade_hash,
        )
        self._status.last_result = result
        self._status.last_action_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
        action_status = str(result.get("status", "unknown"))
        action_reason = str(result.get("reason") or action_status)
        self._push_action_log(
            "signal_copy",
            action_status,
            channel=channel.name,
            symbol=str(result.get("symbol") or parsed.symbol or ""),
            reason=action_reason or None,
            result=result,
        )
        if result["status"] in {"placed", "paper"}:
            self._status.placed += 1
        elif result["status"] == "failed":
            self._status.failed += 1
        else:
            self._status.skipped += 1

    def _message_id(self, channel: TelegramChannelConfig, message: str, *, message_key: str | None = None) -> str:
        payload = f"{channel.url}\n{message_key or ''}\n{message}".encode("utf-8")
        return hashlib.sha256(payload).hexdigest()

    def _record_message(
        self,
        message_id: str,
        status: str,
        message: str,
        *,
        channel: TelegramChannelConfig,
        parsed: dict | None = None,
        result: dict | None = None,
        reason: str | None = None,
        message_key: str | None = None,
        message_timestamp: float | None = None,
        age_seconds: float | None = None,
        trade_hash: str | None = None,
        is_reply: bool = False,
    ) -> None:
        now = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
        payload: dict = {
            "status": status,
            "channel_name": channel.name,
            "channel_url": channel.url,
            "text": message,
            "text_preview": message[:500],
            "parsed": parsed,
            "result": result,
            "reason": reason,
            "is_reply": bool(is_reply),
            "updated_at": now,
            "last_seen_at": now,
        }
        if trade_hash:
            payload["trade_hash"] = trade_hash
        if message_key:
            payload["message_key"] = str(message_key)
        if message_timestamp is not None:
            payload["message_timestamp"] = message_timestamp
        if age_seconds is not None:
            payload["age_seconds"] = round(float(age_seconds), 1)
        self.state.upsert_telegram_message(message_id, payload)

    def _last_channel_setup(self, channel: TelegramChannelConfig) -> dict | None:
        state = self.state.read()
        matches = [
            setup
            for setup in state.get("setups", [])
            if setup.get("source") == "telegram_signals"
            and (
                setup.get("channel_url") == channel.url
                or str(setup.get("channel_name") or "").casefold() == channel.name.casefold()
            )
        ]
        if not matches:
            return None
        return max(matches, key=lambda setup: str(setup.get("created_at") or ""))

    def _apply_channel_breakeven(self, channel: TelegramChannelConfig) -> dict:
        setup = self._last_channel_setup(channel)
        if setup is None:
            return {
                "status": "skipped",
                "channel": channel.name,
                "reason": "no copied telegram setup found for this channel",
            }
        result = self._apply_breakeven(setup)
        result["channel"] = channel.name
        return result

    def _place_parsed_signal(
        self,
        parsed: ParsedTelegramSignal,
        *,
        source_id: str,
        channel: TelegramChannelConfig,
        hard: bool = False,
        trade_hash: str | None = None,
        open_market_keys: set[str] | None = None,
        message_id: str | None = None,
        message_key: str | None = None,
    ) -> dict:
        if not hard and self.daily_risk_status:
            daily = self.daily_risk_status()
            if daily.get("halted"):
                if daily.get("halt_reason") == "win":
                    reason = (
                        "daily win guard is active: "
                        f"gain ${float(daily.get('gain', 0.0) or 0.0):.2f} reached target "
                        f"${float(daily.get('win_target', 0.0) or 0.0):.2f}"
                    )
                else:
                    reason = "daily loss guard is active"
                return {"status": "skipped", "channel": channel.name, "reason": reason, "daily_risk": daily}

        if not parsed.symbol:
            return {"status": "skipped", "channel": channel.name, "reason": "missing symbol"}
        symbol_cfg, auto_registered = resolve_symbol_for_telegram(parsed.symbol, self.config, self.client)
        if symbol_cfg is None:
            return {"status": "skipped", "channel": channel.name, "reason": f"unknown symbol {parsed.symbol}"}
        if auto_registered:
            self.logger.warning(
                "TELEGRAM AUTO-REGISTER symbol=%s key=%s lot=%s",
                symbol_cfg.symbol,
                symbol_cfg.key,
                symbol_cfg.lot_per_leg,
            )

        tps = [float(tp) for tp in parsed.tps[: self.config.telegram_signals.max_tps]]
        if not tps:
            return {"status": "skipped", "channel": channel.name, "reason": "missing take profits"}

        side = "buy" if parsed.action.startswith("buy") else "sell"
        lot = self.config.telegram_signals.default_lot or symbol_cfg.lot_per_leg
        plan = {
            "channel": channel.name,
            "symbol": symbol_cfg.symbol,
            "action": parsed.action,
            "entry": parsed.entry,
            "sl": parsed.stop_loss,
            "tps": tps,
            "lot": float(lot),
        }
        try:
            live_entry = self._live_entry_price(plan, symbol_cfg)
        except ValueError as exc:
            return {"status": "skipped", "channel": channel.name, "reason": str(exc), **plan}

        reference_entry = float(parsed.entry) if parsed.entry is not None else live_entry
        sl_is_synthetic = parsed.stop_loss is None
        if sl_is_synthetic:
            reference_tp = synthetic_stop_loss_reference_tp(tps)
            sl = default_stop_loss_one_to_one(side, reference_entry, reference_tp)
            self.logger.warning(
                "TELEGRAM DEFAULT SL channel=%s symbol=%s side=%s entry=%s ref_tp=%s synthetic_sl=%s",
                channel.name,
                symbol_cfg.symbol,
                side,
                reference_entry,
                reference_tp,
                sl,
            )
        else:
            sl = float(parsed.stop_loss)

        plan["sl"] = sl

        fingerprint = trade_hash or telegram_trade_fingerprint(channel, parsed)
        if not hard and self.state.is_telegram_trade_processed(fingerprint):
            self.logger.info(
                "TELEGRAM SKIP channel=%s duplicate trade hash=%s symbol=%s action=%s",
                channel.name,
                fingerprint[:12],
                parsed.symbol,
                parsed.action,
            )
            return {
                "status": "skipped",
                "channel": channel.name,
                "reason": "duplicate trade already processed",
                "trade_hash": fingerprint,
                "symbol": symbol_cfg.symbol,
                "action": parsed.action,
            }

        if (
            not hard
            and self.config.telegram_signals.ignore_open_symbol_trades
            and self._has_open_market(symbol_cfg, open_market_keys=open_market_keys)
        ):
            result = {
                "status": "skipped",
                "channel": channel.name,
                "reason": f"open position exists for {symbol_cfg.key}",
                "symbol": symbol_cfg.symbol,
                "trade_hash": fingerprint,
            }
            self._mark_processed_trade(fingerprint, parsed, channel, source_id, result, stop_loss_used=sl)
            return result

        geometry_reason = invalid_market_geometry(side, live_entry, sl, tps, label="live price")
        if geometry_reason:
            reason = f"TPs no longer valid: {geometry_reason}" if hard else geometry_reason
            return {"status": "skipped", "channel": channel.name, "reason": reason, **plan, "entry_price": live_entry}

        linked_message_id = message_id or source_id
        log_prefix = "TELEGRAM HARD COPY" if hard else "TELEGRAM SIGNAL"
        self.logger.warning(
            "%s channel=%s parsed symbol=%s action=%s signal_entry=%s live_entry=%s sl=%s synthetic=%s tps=%s lot=%s dry_run=%s",
            log_prefix,
            channel.name,
            plan["symbol"],
            plan["action"],
            plan.get("entry"),
            live_entry,
            sl,
            sl_is_synthetic,
            plan["tps"],
            plan["lot"],
            self.config.bot.dry_run,
        )
        if self.config.bot.dry_run:
            result = {
                "status": "paper",
                **plan,
                "entry_price": live_entry,
                "hard_copy": hard,
                "trade_hash": fingerprint,
                "message_id": linked_message_id,
                "message_key": message_key,
                "tickets": [],
                "sl_synthetic": sl_is_synthetic,
                "sl_pending_refresh": sl_is_synthetic,
            }
            if not hard:
                self._mark_processed_trade(fingerprint, parsed, channel, source_id, result, stop_loss_used=sl)
            if sl_is_synthetic:
                self._register_pending_sl_watch(
                    message_id=linked_message_id,
                    message_key=message_key,
                    channel=channel,
                    setup_id=f"telegram:{source_id[:16]}",
                    tickets=[],
                    symbol=symbol_cfg.symbol,
                    side=side,
                    synthetic_sl=sl,
                )
            return result

        setup_id = f"telegram:hard:{source_id[:24]}" if hard else f"telegram:{source_id[:16]}"
        trade_symbol = settings_mt5_symbol_from_config(symbol_cfg, self.config)
        result = self.executor.place_market_setup(
            setup_id=setup_id,
            symbol=trade_symbol,
            market_key=symbol_cfg.key,
            side=side,
            sl=sl,
            tps=tps,
            lot_per_leg=float(lot),
            entry_price=None,
            execution_mode="split",
            extra_setup={
                "breakeven_applied": False,
                "source": "telegram_signals",
                "channel_url": channel.url,
                "channel_name": channel.name,
                "telegram_message_id": linked_message_id,
                "telegram_message_key": message_key,
                "sl_synthetic": sl_is_synthetic,
            },
            comment=f"TG - {(channel.name or 'Telegram').strip()}"[:31],
        )

        if result.get("status") == "placed":
            tickets = [int(ticket) for ticket in result.get("tickets") or []]
            placed = {
                "status": "placed",
                **plan,
                "entry_price": result.get("entry_price") or live_entry,
                "setup_id": setup_id,
                "trade_hash": fingerprint,
                "message_id": linked_message_id,
                "message_key": message_key,
                "tickets": tickets,
                "sl_synthetic": sl_is_synthetic,
                "sl_pending_refresh": sl_is_synthetic,
                **result,
            }
            if not hard:
                self._mark_processed_trade(fingerprint, parsed, channel, source_id, placed, stop_loss_used=sl)
            if sl_is_synthetic:
                self._register_pending_sl_watch(
                    message_id=linked_message_id,
                    message_key=message_key,
                    channel=channel,
                    setup_id=setup_id,
                    tickets=tickets,
                    symbol=trade_symbol,
                    side=side,
                    synthetic_sl=sl,
                )
            return placed
        failed = {
            "status": "failed" if result.get("status") == "failed" else "skipped",
            **plan,
            "entry_price": result.get("entry_price") or live_entry,
            "trade_hash": fingerprint,
            "message_id": linked_message_id,
            "message_key": message_key,
            **result,
        }
        if not failed.get("reason"):
            failed["reason"] = result.get("reason") or "order placement failed"
        return failed

    def _register_pending_sl_watch(
        self,
        *,
        message_id: str,
        message_key: str | None,
        channel: TelegramChannelConfig,
        setup_id: str,
        tickets: list[int],
        symbol: str,
        side: str,
        synthetic_sl: float,
    ) -> None:
        refresh_seconds = self.config.telegram_signals.sl_refresh_seconds
        now = time.monotonic()
        watch = PendingSlWatch(
            message_id=message_id,
            message_key=message_key,
            channel=channel,
            setup_id=setup_id,
            tickets=list(tickets),
            symbol=symbol,
            side=side,
            synthetic_sl=float(synthetic_sl),
            started_at=now,
            expires_at=now + float(refresh_seconds),
        )
        key = message_key or message_id
        self._pending_sl_watches[key] = watch
        self.logger.warning(
            "TELEGRAM SL WATCH message=%s key=%s setup=%s tickets=%s refresh=%ss synthetic_sl=%s",
            message_id[:10],
            (message_key or "")[:16],
            setup_id,
            tickets,
            refresh_seconds,
            synthetic_sl,
        )

    def _refresh_pending_sl_watches(self, page, channel: TelegramChannelConfig) -> None:
        if not self._pending_sl_watches:
            return
        active = [
            watch
            for watch in self._pending_sl_watches.values()
            if watch.channel.url == channel.url
        ]
        if not active:
            return

        html, source = self._capture_chat_html(page)
        bubbles, _diagnostics = parse_all_bubbles(html, source=source)
        bubble_by_key = {bubble.key: bubble for bubble in bubbles if bubble.key}

        now = time.monotonic()
        for watch in active:
            watch_key = watch.message_key or watch.message_id
            if now >= watch.expires_at:
                self._pending_sl_watches.pop(watch_key, None)
                self.logger.info(
                    "TELEGRAM SL WATCH expired message=%s setup=%s keeping synthetic_sl=%s",
                    watch.message_id[:10],
                    watch.setup_id,
                    watch.synthetic_sl,
                )
                continue

            bubble = bubble_by_key.get(watch.message_key) if watch.message_key else None
            ledger = (
                self.state.find_telegram_message_by_key(watch.message_key)
                if watch.message_key
                else self.state.get_telegram_message(watch.message_id)
            )
            if bubble is None and ledger:
                ledger_text = str(ledger.get("text") or "")
                for candidate in reversed(bubbles):
                    if candidate.text == ledger_text:
                        bubble = candidate
                        break
            if bubble is None:
                continue

            current_text = bubble.text
            previous_text = str((ledger or {}).get("text") or "")
            if current_text == previous_text:
                if (ledger or {}).get("result", {}).get("status") == "updated":
                    self._pending_sl_watches.pop(watch_key, None)
                continue

            try:
                parsed = self.parser.parse(current_text)
            except Exception as exc:  # noqa: BLE001
                self.logger.warning(
                    "TELEGRAM SL WATCH parse failed message=%s setup=%s: %s",
                    watch.message_id[:10],
                    watch.setup_id,
                    exc,
                )
                continue

            refreshed_message_id = self._message_id(channel, current_text, message_key=watch.message_key)
            parsed_payload = parsed.model_dump(mode="python")
            self._record_message(
                refreshed_message_id,
                "sl_refresh",
                current_text,
                channel=channel,
                parsed=parsed_payload,
                message_key=watch.message_key,
                message_timestamp=bubble.timestamp,
                age_seconds=self._message_age(bubble.timestamp),
            )

            if parsed.stop_loss is None:
                continue

            new_sl = float(parsed.stop_loss)
            if abs(new_sl - watch.synthetic_sl) < 1e-9:
                self._pending_sl_watches.pop(watch_key, None)
                continue

            setup = self._get_setup(watch.setup_id)
            if setup is None:
                setup = {
                    "setup_id": watch.setup_id,
                    "symbol": watch.symbol,
                    "side": watch.side,
                    "tickets": watch.tickets,
                    "tps": [float(tp) for tp in ((ledger or {}).get("parsed") or {}).get("tps") or []],
                    "entry_price": (ledger or {}).get("result", {}).get("entry_price"),
                }

            update_result = self.executor.apply_sl_update(
                setup,
                new_sl,
                reason="telegram message updated with stop loss",
            )
            update_result["message_id"] = watch.message_id
            update_result["message_key"] = watch.message_key
            update_result["previous_sl"] = watch.synthetic_sl
            update_result["parsed"] = parsed_payload

            self._record_message(
                refreshed_message_id,
                str(update_result.get("status", "unknown")),
                current_text,
                channel=channel,
                parsed=parsed_payload,
                result=update_result,
                reason=str(update_result.get("reason") or "stop loss updated from telegram"),
                message_key=watch.message_key,
                message_timestamp=bubble.timestamp,
                age_seconds=self._message_age(bubble.timestamp),
            )
            self._push_action_log(
                "sl_refresh",
                str(update_result.get("status", "unknown")),
                channel=channel.name,
                symbol=watch.symbol,
                reason=str(update_result.get("reason") or "stop loss updated from telegram"),
                result=update_result,
            )
            self.logger.warning(
                "TELEGRAM SL UPDATE message=%s setup=%s old_sl=%s new_sl=%s status=%s tickets=%s",
                watch.message_id[:10],
                watch.setup_id,
                watch.synthetic_sl,
                new_sl,
                update_result.get("status"),
                watch.tickets,
            )
            self._pending_sl_watches.pop(watch_key, None)

    def _get_setup(self, setup_id: str) -> dict | None:
        state = self.state.read()
        for setup in state.get("setups", []):
            if str(setup.get("setup_id")) == setup_id:
                return dict(setup)
        return None

    def _mark_processed_trade(
        self,
        trade_hash: str,
        parsed: ParsedTelegramSignal,
        channel: TelegramChannelConfig,
        source_id: str,
        result: dict,
        *,
        stop_loss_used: float | None = None,
    ) -> None:
        self.state.mark_telegram_trade_processed(
            trade_hash,
            {
                "channel_url": channel.url,
                "channel_name": channel.name,
                "symbol": parsed.symbol,
                "action": parsed.action,
                "stop_loss": stop_loss_used if stop_loss_used is not None else parsed.stop_loss,
                "tps": list(parsed.tps),
                "confidence": parsed.confidence,
                "message_id": source_id,
                "tickets": list(result.get("tickets") or []),
                "status": result.get("status"),
                "processed_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
            },
        )

    def _apply_breakeven(self, setup: dict) -> dict:
        return self.executor.apply_breakeven(setup)

    def _has_open_market(self, symbol_cfg: SymbolConfig, *, open_market_keys: set[str] | None = None) -> bool:
        target_key = symbol_cfg.key
        if open_market_keys is not None:
            return target_key in open_market_keys
        positions = self.client.positions() or []
        for pos in positions:
            symbol = str(_field(pos, "symbol", ""))
            if market_key(symbol) == target_key:
                return True
        return False

    def _live_entry_price(self, plan: dict, symbol_cfg) -> float:
        action = str(plan["action"])
        symbol = settings_mt5_symbol_from_config(symbol_cfg, self.config)
        tick = self.client.tick(symbol)
        if tick is None:
            raise ValueError(f"No tick for {symbol}")
        bid = float(_field(tick, "bid", 0.0) or 0.0)
        ask = float(_field(tick, "ask", 0.0) or 0.0)
        if action.startswith("buy"):
            return ask
        if action.startswith("sell"):
            return bid
        entry = float(plan.get("entry") or 0.0)
        if entry <= 0:
            raise ValueError(f"{action} requires an entry price")
        return entry


def _clean_message(text: str) -> str:
    lines = [line.strip() for line in text.replace("\u200b", "").splitlines()]
    lines = [line for line in lines if line]
    return "\n".join(lines)


def _normalize_signal_text(text: str) -> str:
    cleaned = _clean_message(text)
    return re.sub(
        r"(\d+(?:\.\d+)?)\s*[_/\-–—]\s*(\d+(?:\.\d+)?)",
        r"\1 \2",
        cleaned,
    )


def fallback_parse_telegram_signal(text: str, config: AppConfig) -> ParsedTelegramSignal | None:
    if not _looks_like_trade(text):
        return None
    normalized = _normalize_signal_text(text)
    try:
        plan = parse_manual_trade(normalized, config)
    except ValueError:
        return None
    action: TelegramAction = "buy" if plan.side == "buy" else "sell"
    symbol = config_symbol_token(plan.symbol, config)
    return ParsedTelegramSignal(
        symbol=symbol,
        action=action,
        entry=None,
        stop_loss=float(plan.sl),
        tps=[float(tp) for tp in plan.tps],
        confidence=0.75,
    )


def config_symbol_token(resolved_symbol: str, config: AppConfig) -> str:
    target = resolved_symbol.upper()
    for item in config.symbols:
        if item.symbol.upper() == target or item.key.upper() == target:
            if item.key == "XAUUSD":
                return "XAUUSD"
            if item.key == "XAGUSD":
                return "XAGUSD"
            return item.key or item.symbol
    if "XAU" in target or target.endswith("GOLD"):
        return "XAUUSD"
    if "XAG" in target or "SILVER" in target:
        return "XAGUSD"
    return target.replace("-VIP", "").replace("-STD", "")


def _round_price(value: float | None) -> float | None:
    if value is None:
        return None
    return round(float(value), 5)


def telegram_trade_fingerprint(channel: TelegramChannelConfig, parsed: ParsedTelegramSignal) -> str:
    symbol = str(parsed.symbol or "").strip().upper()
    payload: dict[str, object] = {
        "channel": channel.url.casefold(),
        "symbol": symbol,
        "action": parsed.action,
        "stop_loss": _round_price(parsed.stop_loss),
        "tps": [_round_price(tp) for tp in sorted(float(tp) for tp in parsed.tps)],
        "confidence": round(float(parsed.confidence), 2),
    }
    if parsed.entry is not None and parsed.action not in {"buy", "sell"}:
        payload["entry"] = _round_price(parsed.entry)
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:24]


def _looks_like_trade_update(text: str) -> bool:
    cleaned = _clean_message(text)
    if not cleaned:
        return False

    if re.search(r"\b\d+(?:ST|ND|RD|TH)\s+ENTRY\b", cleaned, re.IGNORECASE):
        return True
    if re.search(r"\b\d+\s*PIPS?\s+DONE\b", cleaned, re.IGNORECASE):
        return True
    if re.search(r"\b(?:TP|TARGET)\s*\d+\s*(?:HIT|DONE|✅)", cleaned, re.IGNORECASE):
        return True
    if re.search(r"\bPROFIT\s*(?:ACHIEVED|DONE|BOOKED)\b", cleaned, re.IGNORECASE):
        return True

    profit_rows = re.findall(
        r"(?mi)^(?:buy|sell)\s+\d+(?:\.\d+)?\s+\d+(?:\.\d+)?\s+\d+(?:\.\d+)?\s+\d+(?:\.\d+)?\s*$",
        cleaned,
    )
    if profit_rows:
        return True

    if ".||." in cleaned and profit_rows:
        return True

    if re.search(r"\bDONE\b", cleaned, re.IGNORECASE) and re.search(
        r"\b(?:PIPS|ENTRY|TARGET|PROFIT|✅)\b", cleaned, re.IGNORECASE
    ):
        return True

    return False


def _looks_like_breakeven(text: str) -> bool:
    cleaned = _clean_message(text)
    if not cleaned:
        return False
    if re.search(r"\b(breakeven|break[\s-]?even)\b", cleaned, re.IGNORECASE):
        return True
    if re.search(r"\b(sl|stop\s*loss)\s*(to|@|=)\s*(entry|be|breakeven)\b", cleaned, re.IGNORECASE):
        return True
    compact = re.sub(r"\s+", "", cleaned).casefold()
    return compact == "be" or "breakeven" in compact.replace("-", "")


def _looks_like_trade(text: str) -> bool:
    upper = text.upper()
    if not re.search(r"\b(BUY|SELL)\b", upper):
        return False
    return any(token in upper for token in ("SL", "STOP", "TP", "TARGET", "TAKE PROFIT", "LIMIT", "STOPLOSS"))
