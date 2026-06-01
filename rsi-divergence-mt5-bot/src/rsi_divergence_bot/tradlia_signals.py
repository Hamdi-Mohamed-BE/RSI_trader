from __future__ import annotations

import json
import logging
import os
import re
import threading
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from pydantic import ValidationError

from .config import AppConfig, TelegramChannelConfig
from .mt5_client import MT5Client
from .state import StateStore
from .telegram_signals import GeminiSignalParser, ParsedTelegramSignal, TelegramSignalsBot, telegram_trade_fingerprint


def _looks_like_breakeven(text: str) -> bool:
    upper = text.upper()
    return bool(re.search(r"\b(BREAKEVEN|BREAK[\s-]?EVEN)\b", upper))


@dataclass
class TradliaLoopStatus:
    running: bool = False
    started_at: str | None = None
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


class TradliaSignalsBot:
    """Poll Tradlia (Supabase) telegram_signals feed and copy trades via shared MT5 placement logic."""

    _FEED_SYNC_MIN_INTERVAL = 8.0

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
        self._copier = TelegramSignalsBot(
            config,
            client,
            state,
            logger,
            daily_risk_status,
            config_path=config_path,
        )
        self._copier.parser = self.parser
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None
        self._status = TradliaLoopStatus()
        self._seen_ids: set[str] = set()
        self._last_feed_sync_at = 0.0
        self._feed_sync_lock = threading.Lock()

    def start(self, *, protect_tp: bool = False) -> dict:
        if self.is_running():
            return self.status(sync_feed=False)
        if not self._api_configured():
            error = "Tradlia API key and bearer token are required (config or TRADLIA_* env vars)"
            self._status.last_error = error
            return {**self.status(sync_feed=False), "start_error": error}
        self._stop_event.clear()
        self._status = TradliaLoopStatus(
            running=True,
            started_at=datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        )
        self._thread = threading.Thread(target=self._loop, name="tradlia-signals-copy", daemon=True, kwargs={"protect_tp": protect_tp})
        self._thread.start()
        self.logger.warning(
            "TRADLIA SIGNALS START poll=%ss dry_run=%s",
            self.config.tradlia_signals.poll_seconds,
            self.config.bot.dry_run,
        )
        return self.status(sync_feed=False)

    def stop(self) -> dict:
        if not self.is_running():
            self._status.running = False
            return self.status(sync_feed=False)
        self._stop_event.set()
        if self._thread is not None:
            self._thread.join(timeout=self.config.tradlia_signals.poll_seconds + 15)
        self._status.running = False
        return self.status(sync_feed=False)

    def is_running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    def status(self, *, sync_feed: bool = True) -> dict:
        if sync_feed and self._api_configured():
            self._maybe_sync_feed()
        data = asdict(self._status)
        data["running"] = self.is_running()
        data["poll_seconds"] = self.config.tradlia_signals.poll_seconds
        data["api_configured"] = self._api_configured()
        data["api_key_configured"] = bool(self._api_key())
        data["bearer_token_configured"] = bool(self._bearer_token())
        data["llm_configured"] = GeminiSignalParser.llm_configured(self.config)
        data["recent_messages"] = self.state.recent_tradlia_messages(100)
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
        return data

    def sync_feed(self) -> dict:
        if not self._api_configured():
            return {"status": "error", "reason": "Tradlia API credentials missing"}
        count = self._sync_feed_from_api(force=True)
        return {"status": "synced", "messages_synced": count, **self.status(sync_feed=False)}

    def clear_message_history(self) -> dict:
        removed = self.state.clear_tradlia_history()
        self._seen_ids.clear()
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
        self.logger.info("TRADLIA history cleared messages=%s", removed["messages_removed"])
        return {"status": "cleared", **removed, **self.status(sync_feed=False)}

    def hard_copy_message(self, message_id: str) -> dict:
        cleaned_id = str(message_id or "").strip()
        if not cleaned_id:
            return {"status": "error", "reason": "message_id is required"}

        record = self.state.get_tradlia_message(cleaned_id)
        if record is None:
            preview = cleaned_id[:12]
            return {
                "status": "error",
                "reason": (
                    f"Tradlia signal {preview}… was not found in the ledger. "
                    "Refresh the feed or start the copier to sync messages."
                ),
            }

        text = str(record.get("text") or record.get("text_preview") or "").strip()
        if not text:
            return {"status": "error", "reason": "Message has no text to copy"}
        if _looks_like_breakeven(text):
            return {"status": "error", "reason": "Breakeven/update messages cannot be hard copied"}

        channel_name = str(record.get("channel_name") or "Tradlia").strip() or "Tradlia"
        channel = TelegramChannelConfig(
            name=channel_name,
            url=str(record.get("channel_url") or f"tradlia:{cleaned_id}"),
            enabled=True,
        )

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
        result = self._copier._place_parsed_signal(
            parsed,
            source_id=source_id,
            channel=channel,
            hard=True,
            message_id=cleaned_id,
        )
        result["hard_copy"] = True
        result["message_id"] = cleaned_id
        result["tradlia_id"] = cleaned_id

        self._record_message(
            cleaned_id,
            str(result.get("status", "unknown")),
            text,
            channel_name=channel_name,
            channel_url=channel.url,
            parsed=parsed.model_dump(mode="python"),
            result=result,
            reason=result.get("reason"),
            tradlia_time=record.get("tradlia_time"),
        )
        self._status.last_signal = parsed.model_dump(mode="python")
        self._status.last_result = result
        self._status.last_action_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
        status = str(result.get("status", "unknown"))
        reason = str(result.get("reason") or "")
        self._push_action(
            status,
            channel_name,
            symbol=str(result.get("symbol") or parsed.symbol or ""),
            reason=reason or None,
            result=result,
            hard_copy=True,
        )
        if status in {"placed", "paper"}:
            self._status.placed += 1
        elif status == "failed":
            self._status.failed += 1
        else:
            self._status.skipped += 1
        self.logger.warning(
            "TRADLIA HARD COPY id=%s channel=%s status=%s symbol=%s action=%s reason=%s",
            cleaned_id[:10],
            channel_name,
            result.get("status"),
            result.get("symbol"),
            parsed.action,
            reason or result.get("reason"),
        )
        return result

    def _api_configured(self) -> bool:
        return bool(self._api_key() and self._bearer_token())

    def _api_key(self) -> str | None:
        key = self.config.tradlia_signals.api_key or os.getenv("TRADLIA_API_KEY")
        return key.strip() if key else None

    def _bearer_token(self) -> str | None:
        token = self.config.tradlia_signals.bearer_token or os.getenv("TRADLIA_BEARER_TOKEN")
        return token.strip() if token else None

    def _maybe_sync_feed(self) -> None:
        now = time.monotonic()
        if now - self._last_feed_sync_at < self._FEED_SYNC_MIN_INTERVAL:
            return
        try:
            self._sync_feed_from_api(force=False)
        except Exception as exc:  # noqa: BLE001
            self._status.last_error = str(exc)
            self.logger.warning("TRADLIA feed sync failed: %s", exc)

    def _sync_feed_from_api(self, *, force: bool) -> int:
        with self._feed_sync_lock:
            now = time.monotonic()
            if not force and now - self._last_feed_sync_at < self._FEED_SYNC_MIN_INTERVAL:
                return 0
            rows = self._fetch_signals()
            self._last_feed_sync_at = time.monotonic()
        if not rows:
            return 0
        synced = 0
        for row in rows:
            signal_id = str(row.get("id") or "").strip()
            message = str(row.get("message_text") or "").strip()
            if not signal_id or not message:
                continue
            channel_name = str(row.get("channel_name") or "Tradlia").strip() or "Tradlia"
            existing = self.state.get_tradlia_message(signal_id)
            status = str(existing.get("status") or "feed") if existing else "feed"
            if existing and status not in {"", "feed", "seen"}:
                status = str(existing.get("status") or status)
            self._record_message(
                signal_id,
                status,
                message,
                channel_name=channel_name,
                channel_url=f"tradlia:{row.get('channel_id') or signal_id}",
                parsed=existing.get("parsed") if existing else None,
                result=existing.get("result") if existing else None,
                reason=existing.get("reason") if existing else None,
                tradlia_time=row.get("time") or row.get("created_at"),
            )
            synced += 1
        return synced

    def _loop(self, *, protect_tp: bool) -> None:
        if protect_tp:
            self._copier._manage_tp_protection(enabled=True)
        while not self._stop_event.is_set():
            try:
                self._poll_once()
            except Exception as exc:  # noqa: BLE001
                self._status.last_error = str(exc)
                self.logger.exception("TRADLIA poll failed: %s", exc)
            self._stop_event.wait(self.config.tradlia_signals.poll_seconds)
        self._status.running = False

    def _poll_once(self) -> None:
        self._sync_feed_from_api(force=True)
        rows = self._fetch_signals()
        if not rows:
            return
        rows.sort(key=lambda row: str(row.get("time") or row.get("created_at") or ""))
        open_market_keys = self._copier._cached_open_market_keys()
        for row in rows:
            signal_id = str(row.get("id") or "").strip()
            if not signal_id or signal_id in self._seen_ids:
                continue
            self._seen_ids.add(signal_id)
            self._process_row(row, open_market_keys=open_market_keys)

    def _fetch_signals(self) -> list[dict]:
        request = Request(
            self.config.tradlia_signals.api_url,
            headers={
                "accept": "application/json",
                "accept-profile": "public",
                "apikey": self._api_key() or "",
                "authorization": f"Bearer {self._bearer_token() or ''}",
                "user-agent": "rsi-divergence-mt5-bot/1.0",
            },
            method="GET",
        )
        try:
            with urlopen(request, timeout=30) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except HTTPError as exc:
            raise RuntimeError(f"Tradlia API HTTP {exc.code}: {exc.reason}") from exc
        except URLError as exc:
            raise RuntimeError(f"Tradlia API unreachable: {exc}") from exc
        if not isinstance(payload, list):
            raise RuntimeError("Tradlia API returned unexpected payload")
        return [item for item in payload if isinstance(item, dict)]

    def _record_message(
        self,
        message_id: str,
        status: str,
        message: str,
        *,
        channel_name: str,
        channel_url: str,
        parsed: dict | None = None,
        result: dict | None = None,
        reason: str | None = None,
        tradlia_time: str | None = None,
    ) -> None:
        now = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
        payload: dict = {
            "status": status,
            "channel_name": channel_name,
            "channel_url": channel_url,
            "text": message,
            "text_preview": message[:500],
            "parsed": parsed,
            "result": result,
            "reason": reason,
            "is_reply": False,
            "updated_at": now,
            "last_seen_at": now,
        }
        if tradlia_time is not None:
            payload["tradlia_time"] = str(tradlia_time)
        self.state.upsert_tradlia_message(message_id, payload)

    def _process_row(self, row: dict, *, open_market_keys: set[str]) -> None:
        message = str(row.get("message_text") or "").strip()
        channel_name = str(row.get("channel_name") or "Tradlia").strip() or "Tradlia"
        signal_id = str(row.get("id") or "")
        channel_url = f"tradlia:{row.get('channel_id') or signal_id}"
        tradlia_time = row.get("time") or row.get("created_at")
        if not message:
            return

        self._status.messages_seen += 1
        self._status.last_channel = channel_name
        self._status.last_message_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat()

        try:
            parsed = self.parser.parse(message)
        except Exception as exc:  # noqa: BLE001
            self._status.failed += 1
            self._record_message(
                signal_id,
                "parse_failed",
                message,
                channel_name=channel_name,
                channel_url=channel_url,
                reason=str(exc),
                tradlia_time=tradlia_time,
            )
            self._push_action("parse_failed", channel_name, reason=str(exc))
            return

        self._status.last_signal = parsed.model_dump(mode="python")
        if parsed.action == "none":
            self._status.skipped += 1
            self._record_message(
                signal_id,
                "skipped",
                message,
                channel_name=channel_name,
                channel_url=channel_url,
                parsed=parsed.model_dump(mode="python"),
                reason="not a trade signal",
                tradlia_time=tradlia_time,
            )
            self._push_action("skipped", channel_name, reason="not a trade signal")
            return

        self._status.parsed_signals += 1
        channel = TelegramChannelConfig(
            name=channel_name,
            url=channel_url,
            enabled=True,
        )
        trade_hash = telegram_trade_fingerprint(channel, parsed)
        result = self._copier._place_parsed_signal(
            parsed,
            source_id=signal_id,
            channel=channel,
            trade_hash=trade_hash,
            open_market_keys=open_market_keys,
            message_id=signal_id,
            max_tps=self.config.tradlia_signals.max_tps,
            default_lot=self.config.tradlia_signals.default_lot,
            ignore_open_symbol_trades=self.config.tradlia_signals.ignore_open_symbol_trades,
        )
        result["tradlia_id"] = signal_id
        result["channel"] = channel_name

        status = str(result.get("status", "unknown"))
        self._status.last_result = result
        self._status.last_action_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
        self._record_message(
            signal_id,
            status,
            message,
            channel_name=channel_name,
            channel_url=channel_url,
            parsed=parsed.model_dump(mode="python"),
            result=result,
            reason=result.get("reason"),
            tradlia_time=tradlia_time,
        )
        if status == "placed":
            self._status.placed += 1
        elif status in {"skipped", "signal_inactive", "paper"}:
            self._status.skipped += 1
        else:
            self._status.failed += 1
        self._push_action(status, channel_name, symbol=result.get("symbol"), reason=result.get("reason"), result=result)

    def _push_action(
        self,
        status: str,
        channel: str,
        *,
        symbol: str | None = None,
        reason: str | None = None,
        result: dict | None = None,
        hard_copy: bool = False,
    ) -> None:
        entry = {
            "at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
            "kind": "hard_copy" if hard_copy else "tradlia_copy",
            "status": status,
            "channel": channel,
            "symbol": symbol,
            "reason": reason,
            "hard_copy": hard_copy,
        }
        if result:
            entry["result"] = {
                "status": result.get("status"),
                "reason": result.get("reason"),
                "execution_reason": result.get("execution_reason"),
                "symbol": result.get("symbol"),
                "hard_copy": result.get("hard_copy"),
            }
        self._status.recent_actions.append(entry)
        if len(self._status.recent_actions) > 80:
            self._status.recent_actions = self._status.recent_actions[-80:]
