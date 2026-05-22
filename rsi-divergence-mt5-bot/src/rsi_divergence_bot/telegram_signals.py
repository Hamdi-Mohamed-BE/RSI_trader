from __future__ import annotations

import hashlib
import logging
import os
import re
import threading
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Literal

from pydantic import BaseModel, Field

from .config import AppConfig, SymbolConfig, TelegramChannelConfig
from .manual_trade import resolve_symbol
from .mt5_client import MT5Client, _field
from .state import StateStore
from .symbols import market_key
from .trader import TradeExecutor

from .telegram_html_parser import (
    ParsedChatMessage,
    ParseDiagnostics,
    looks_like_ad,
    parse_all_messages,
    parse_chatlist_preview,
    parse_latest_message,
    pick_latest_non_ad,
)

TelegramAction = Literal["buy", "sell", "buy_limit", "sell_limit", "buy_stop", "sell_stop", "none"]
COMMENT_PREFIX = "signal bot"

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


class GeminiSignalParser:
    def __init__(self, config: AppConfig):
        self.config = config

    def parse(self, message: str) -> ParsedTelegramSignal:
        api_key = self.config.telegram_signals.gemini_api_key or os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise RuntimeError("Gemini API key missing. Set telegram_signals.gemini_api_key or GEMINI_API_KEY.")

        try:
            from langchain_core.output_parsers import PydanticOutputParser
            from langchain_core.prompts import ChatPromptTemplate
            from langchain_google_genai import ChatGoogleGenerativeAI
        except ImportError as exc:  # pragma: no cover - depends on optional runtime install
            raise RuntimeError("LangChain Gemini packages are not installed. Run `uv sync`.") from exc

        parser = PydanticOutputParser(pydantic_object=ParsedTelegramSignal)
        prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    "You extract trade signals from Telegram messages. "
                    "Return only structured output. If the message is not a trade signal, use action='none'. "
                    "Use action='buy' or action='sell' for live/now/market trades. "
                    "Use buy_limit, sell_limit, buy_stop, or sell_stop for pending orders. "
                    "Normalize GOLD/XAU to XAUUSD when clear. Keep prices exactly as written.",
                ),
                (
                    "human",
                    "Message:\n{message}\n\n{format_instructions}",
                ),
            ]
        )
        llm = ChatGoogleGenerativeAI(model=self.config.telegram_signals.gemini_model, google_api_key=api_key)
        chain = prompt | llm | parser
        result = chain.invoke({"message": message, "format_instructions": parser.get_format_instructions()})
        if not isinstance(result, ParsedTelegramSignal):
            result = ParsedTelegramSignal.model_validate(result)
        return result


class TelegramSignalsBot:
    def __init__(
        self,
        config: AppConfig,
        client: MT5Client,
        state: StateStore,
        logger: logging.Logger,
        daily_risk_status: Callable[[], dict] | None = None,
    ):
        self.config = config
        self.client = client
        self.state = state
        self.logger = logger
        self.daily_risk_status = daily_risk_status
        self.parser = GeminiSignalParser(config)
        self.executor = TradeExecutor(config, client, state, logger)
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None
        self._status = TelegramLoopStatus()
        self._seen_messages: set[str] = set()
        self._channel_pages: dict[str, object] = {}

    def start(self, *, protect_tp: bool = False) -> dict:
        if self.is_running():
            return self.status()
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
        data["gemini_model"] = self.config.telegram_signals.gemini_model
        data["gemini_api_key_configured"] = bool(
            self.config.telegram_signals.gemini_api_key or os.getenv("GEMINI_API_KEY")
        )
        data["channels"] = [channel.model_dump(mode="python") for channel in self._enabled_channels()]
        data["recent_messages"] = self.state.recent_telegram_messages(25)
        return data

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
        self.logger.info(
            "TELEGRAM history cleared messages=%s seen_ids=%s",
            removed["messages_removed"],
            removed["seen_removed"],
        )
        return {"status": "cleared", **removed, **self.status()}

    def _loop(self) -> None:
        playwright = None
        context = None
        try:
            from playwright.sync_api import sync_playwright

            profile_dir = Path(self.config.telegram_signals.browser_user_data_dir)
            if not profile_dir.is_absolute():
                profile_dir = Path(self.config.bot.state_file).resolve().parent.parent / profile_dir
            profile_dir.mkdir(parents=True, exist_ok=True)

            playwright = sync_playwright().start()
            context = self._open_browser(playwright, profile_dir)
            channels = self._enabled_channels()
            self._channel_pages = self._open_all_channel_windows(context, channels)
            self._status.browser_open = True
            self.logger.warning(
                "TELEGRAM SIGNALS browser opened with %s channel window(s). Login if asked. channels=%s",
                len(self._channel_pages),
                [channel.name for channel in channels],
            )

            while not self._stop_event.is_set():
                try:
                    if self._status.protect_tp:
                        self.executor.manage_tp_protection(enabled=True)
                    channels = self._enabled_channels()
                    self.logger.info(
                        "TELEGRAM ROUND channels=%s windows=%s",
                        [channel.name for channel in channels],
                        len(self._channel_pages),
                    )
                    for channel in channels:
                        page = self._ensure_channel_page(context, channel)
                        self._read_channel(page, channel)
                    self._status.last_error = None
                except Exception as exc:  # noqa: BLE001
                    self._status.last_error = str(exc)
                    self.logger.exception("TELEGRAM SIGNALS loop error: %s", exc)

                if self._stop_event.wait(self.config.telegram_signals.poll_seconds):
                    break
        except Exception as exc:  # noqa: BLE001
            self._status.last_error = str(exc)
            self.logger.exception("TELEGRAM SIGNALS failed to start: %s", exc)
        finally:
            self._status.running = False
            self._status.browser_open = False
            self._channel_pages = {}
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
            self.logger.info("TELEGRAM SIGNALS stopped")

    def _enabled_channels(self) -> list[TelegramChannelConfig]:
        return [channel for channel in self.config.telegram_signals.channels if channel.enabled]

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
        pages: dict[str, object] = {}
        for index, channel in enumerate(channels):
            page = context.pages[0] if index == 0 and context.pages else context.new_page()
            self.logger.info("TELEGRAM WINDOW OPEN channel=%s url=%s", channel.name, channel.url)
            page.goto(channel.url, wait_until="domcontentloaded", timeout=60_000)
            if index == 0:
                self._wait_for_telegram_ready(page)
            self._wait_for_chat_messages(page, channel)
            self._scroll_chat_to_bottom(page)
            pages[channel.url] = page
            page.wait_for_timeout(800)
        return pages

    def _ensure_channel_page(self, context, channel: TelegramChannelConfig):
        page = self._channel_pages.get(channel.url)
        if page is not None and not page.is_closed():
            return page

        self.logger.warning("TELEGRAM WINDOW REOPEN channel=%s url=%s", channel.name, channel.url)
        page = context.new_page()
        page.goto(channel.url, wait_until="domcontentloaded", timeout=60_000)
        self._wait_for_chat_messages(page, channel)
        self._scroll_chat_to_bottom(page)
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
        deadline_ms = 20_000
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

        for attempt in range(4):
            page.evaluate(_TELEGRAM_NAVIGATE_CHAT_JS, {"hash": self._channel_hash(channel.url), "name": channel.name})
            page.wait_for_timeout(700 + attempt * 400)
            state = page.evaluate(_TELEGRAM_CHAT_STATE_JS)
            if state.get("readableBubbleCount", 0) > 0 or state.get("bubbleCount", 0) > 0:
                return

        page.goto(channel.url, wait_until="domcontentloaded", timeout=60_000)
        page.wait_for_timeout(1200)

    def _scroll_chat_to_bottom(self, page, *, attempts: int = 4) -> None:
        for _ in range(attempts):
            page.evaluate(_TELEGRAM_SCROLL_CHAT_JS)
            page.wait_for_timeout(450)

    def _capture_chat_html(self, page) -> tuple[str, str]:
        payload = page.evaluate(_TELEGRAM_CHAT_HTML_JS)
        html = str(payload.get("html") or "")
        source = str(payload.get("selector") or "unknown")
        if len(html.strip()) > 80:
            return html, source
        return page.content(), "document"

    def _read_channel(self, page, channel: TelegramChannelConfig) -> None:
        try:
            self._scroll_chat_to_bottom(page, attempts=2)
            self._status.last_channel = channel.name

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
            )
        except Exception as exc:  # noqa: BLE001
            self._status.last_error = f"{channel.name}: {exc}"
            self.logger.exception("TELEGRAM CHANNEL READ ERROR channel=%s url=%s error=%s", channel.name, channel.url, exc)

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

        for attempt in range(5):
            self._scroll_chat_to_bottom(page, attempts=1)
            page.wait_for_timeout(350 + attempt * 250)
            html, source = self._capture_chat_html(page)
            candidates, diagnostics = parse_all_messages(html, source=source)
            last_diagnostics = diagnostics

            chosen, skipped_ad = self._pick_clean_message(candidates)
            if chosen is not None:
                return chosen, diagnostics, skipped_ad

            if skipped_ad:
                self._scroll_chat_up(page, attempts=2)
                continue

        for scroll_up_pass in range(4):
            self._scroll_chat_up(page, attempts=1)
            page.wait_for_timeout(600)
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
                reason="Gemini returned action=none",
                message_key=message_key,
                message_timestamp=message_timestamp,
                age_seconds=self._message_age(message_timestamp),
            )
            self.logger.info("TELEGRAM SKIP channel=%s no trade signal hash=%s", channel.name, message_id[:10])
            return

        self._status.parsed_signals += 1
        result = self._place_parsed_signal(parsed, source_id=message_id, channel=channel)
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
        )
        self._status.last_result = result
        self._status.last_action_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
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
    ) -> None:
        now = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
        payload: dict = {
            "status": status,
            "channel_name": channel.name,
            "channel_url": channel.url,
            "text_preview": message[:500],
            "parsed": parsed,
            "result": result,
            "reason": reason,
            "updated_at": now,
            "last_seen_at": now,
        }
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
        result = self.executor.apply_breakeven(setup)
        result["channel"] = channel.name
        return result

    def _place_parsed_signal(self, parsed: ParsedTelegramSignal, *, source_id: str, channel: TelegramChannelConfig) -> dict:
        if self.daily_risk_status:
            daily = self.daily_risk_status()
            if daily.get("halted"):
                return {"status": "skipped", "channel": channel.name, "reason": "daily loss guard is active", "daily_risk": daily}

        if not parsed.symbol:
            return {"status": "skipped", "channel": channel.name, "reason": "missing symbol"}
        symbol_cfg = resolve_symbol(parsed.symbol, self.config)
        if symbol_cfg is None:
            return {"status": "skipped", "channel": channel.name, "reason": f"unknown symbol {parsed.symbol}"}
        if parsed.stop_loss is None:
            return {"status": "skipped", "channel": channel.name, "reason": "missing stop loss"}
        tps = [float(tp) for tp in parsed.tps[: self.config.telegram_signals.max_tps]]
        if not tps:
            return {"status": "skipped", "channel": channel.name, "reason": "missing take profits"}

        if self.config.telegram_signals.ignore_open_symbol_trades and self._has_open_market(symbol_cfg):
            return {"status": "skipped", "channel": channel.name, "reason": f"open position exists for {symbol_cfg.key}", "symbol": symbol_cfg.symbol}

        lot = self.config.telegram_signals.default_lot or symbol_cfg.lot_per_leg
        plan = {
            "channel": channel.name,
            "symbol": symbol_cfg.symbol,
            "action": parsed.action,
            "entry": parsed.entry,
            "sl": float(parsed.stop_loss),
            "tps": tps,
            "lot": float(lot),
        }
        entry_price = self._validate_plan(plan)

        self.logger.warning(
            "TELEGRAM SIGNAL channel=%s parsed symbol=%s action=%s entry=%s sl=%s tps=%s lot=%s dry_run=%s",
            channel.name,
            plan["symbol"],
            plan["action"],
            entry_price,
            plan["sl"],
            plan["tps"],
            plan["lot"],
            self.config.bot.dry_run,
        )
        if self.config.bot.dry_run:
            return {"status": "paper", **plan, "entry_price": entry_price}

        tickets: list[dict] = []
        failed: list[dict] = []
        for index, tp in enumerate(tps, start=1):
            if parsed.action in {"buy", "sell"}:
                result = self.client.send_market(
                    symbol_cfg.symbol,
                    parsed.action,
                    float(lot),
                    float(parsed.stop_loss),
                    float(tp),
                    self.config.bot.magic,
                    f"{COMMENT_PREFIX} TP{index}",
                )
            else:
                result = self.client.send_pending(
                    symbol_cfg.symbol,
                    parsed.action,
                    float(lot),
                    float(parsed.entry),
                    float(parsed.stop_loss),
                    float(tp),
                    self.config.bot.magic,
                    f"{COMMENT_PREFIX} TP{index}",
                )
            row = {
                "tp_index": index,
                "tp": float(tp),
                "retcode": getattr(result, "retcode", None),
                "order": int(getattr(result, "order", 0) or getattr(result, "deal", 0) or 0),
                "result": str(result),
            }
            if row["retcode"] in {self.client.TRADE_DONE, self.client.TRADE_PLACED} and row["order"]:
                tickets.append(row)
            else:
                failed.append(row)

        if tickets:
            setup_id = f"telegram:{source_id[:16]}"
            self.state.add_setup(
                {
                    "setup_id": setup_id,
                    "symbol": symbol_cfg.symbol,
                    "market_key": symbol_cfg.key,
                    "side": "buy" if parsed.action.startswith("buy") else "sell",
                    "tickets": [row["order"] for row in tickets],
                    "tps": tps,
                    "sl": float(parsed.stop_loss),
                    "entry_price": float(entry_price),
                    "moved_to_tp": 0,
                    "breakeven_applied": False,
                    "created_at": datetime.now(timezone.utc).isoformat(),
                    "source": "telegram_signals",
                    "channel_url": channel.url,
                    "channel_name": channel.name,
                }
            )
            return {"status": "placed", **plan, "entry_price": entry_price, "setup_id": setup_id, "tickets": tickets, "failed": failed}

        return {"status": "failed", **plan, "entry_price": entry_price, "tickets": tickets, "failed": failed}

    def _has_open_market(self, symbol_cfg: SymbolConfig) -> bool:
        target_key = symbol_cfg.key
        positions = self.client.positions() or []
        for pos in positions:
            symbol = str(_field(pos, "symbol", ""))
            if market_key(symbol) == target_key:
                return True
        return False

    def _validate_plan(self, plan: dict) -> float:
        action = str(plan["action"])
        symbol = str(plan["symbol"])
        tick = self.client.tick(symbol)
        if tick is None:
            raise ValueError(f"No tick for {symbol}")
        bid = float(_field(tick, "bid", 0.0) or 0.0)
        ask = float(_field(tick, "ask", 0.0) or 0.0)
        sl = float(plan["sl"])
        tps = [float(tp) for tp in plan["tps"]]
        entry = ask if action == "buy" else bid if action == "sell" else float(plan["entry"] or 0.0)
        if entry <= 0:
            raise ValueError(f"{action} requires an entry price")

        if action == "buy":
            if sl >= ask or any(tp <= ask for tp in tps):
                raise ValueError(f"Invalid BUY geometry ask={ask} sl={sl} tps={tps}")
        elif action == "sell":
            if sl <= bid or any(tp >= bid for tp in tps):
                raise ValueError(f"Invalid SELL geometry bid={bid} sl={sl} tps={tps}")
        elif action == "buy_limit":
            if not (entry < ask and sl < entry and all(tp > entry for tp in tps)):
                raise ValueError(f"Invalid BUY LIMIT geometry ask={ask} entry={entry} sl={sl} tps={tps}")
        elif action == "sell_limit":
            if not (entry > bid and sl > entry and all(tp < entry for tp in tps)):
                raise ValueError(f"Invalid SELL LIMIT geometry bid={bid} entry={entry} sl={sl} tps={tps}")
        elif action == "buy_stop":
            if not (entry > ask and sl < entry and all(tp > entry for tp in tps)):
                raise ValueError(f"Invalid BUY STOP geometry ask={ask} entry={entry} sl={sl} tps={tps}")
        elif action == "sell_stop":
            if not (entry < bid and sl > entry and all(tp < entry for tp in tps)):
                raise ValueError(f"Invalid SELL STOP geometry bid={bid} entry={entry} sl={sl} tps={tps}")
        else:
            raise ValueError(f"Unsupported action: {action}")
        return entry


def _clean_message(text: str) -> str:
    lines = [line.strip() for line in text.replace("\u200b", "").splitlines()]
    lines = [line for line in lines if line]
    return "\n".join(lines)


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
