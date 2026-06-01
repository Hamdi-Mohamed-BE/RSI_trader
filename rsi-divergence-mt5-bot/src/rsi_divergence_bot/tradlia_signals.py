from __future__ import annotations

import json
import logging
import os
import threading
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from .config import AppConfig, TelegramChannelConfig
from .mt5_client import MT5Client
from .state import StateStore
from .telegram_signals import GeminiSignalParser, ParsedTelegramSignal, TelegramSignalsBot, telegram_trade_fingerprint


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

    def start(self, *, protect_tp: bool = False) -> dict:
        if self.is_running():
            return self.status()
        if not self._api_configured():
            error = "Tradlia API key and bearer token are required (config or TRADLIA_* env vars)"
            self._status.last_error = error
            return {**self.status(), "start_error": error}
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
        return self.status()

    def stop(self) -> dict:
        if not self.is_running():
            self._status.running = False
            return self.status()
        self._stop_event.set()
        if self._thread is not None:
            self._thread.join(timeout=self.config.tradlia_signals.poll_seconds + 15)
        self._status.running = False
        return self.status()

    def is_running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    def status(self) -> dict:
        data = asdict(self._status)
        data["running"] = self.is_running()
        data["poll_seconds"] = self.config.tradlia_signals.poll_seconds
        data["api_configured"] = self._api_configured()
        data["llm_configured"] = GeminiSignalParser.llm_configured(self.config)
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

    def _api_configured(self) -> bool:
        return bool(self._api_key() and self._bearer_token())

    def _api_key(self) -> str | None:
        key = self.config.tradlia_signals.api_key or os.getenv("TRADLIA_API_KEY")
        return key.strip() if key else None

    def _bearer_token(self) -> str | None:
        token = self.config.tradlia_signals.bearer_token or os.getenv("TRADLIA_BEARER_TOKEN")
        return token.strip() if token else None

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

    def _process_row(self, row: dict, *, open_market_keys: set[str]) -> None:
        message = str(row.get("message_text") or "").strip()
        channel_name = str(row.get("channel_name") or "Tradlia").strip() or "Tradlia"
        signal_id = str(row.get("id") or "")
        if not message:
            return

        self._status.messages_seen += 1
        self._status.last_channel = channel_name
        self._status.last_message_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat()

        try:
            parsed = self.parser.parse(message)
        except Exception as exc:  # noqa: BLE001
            self._status.failed += 1
            self._push_action("parse_failed", channel_name, reason=str(exc))
            return

        self._status.last_signal = parsed.model_dump(mode="python")
        if parsed.action == "none":
            self._status.skipped += 1
            self._push_action("skipped", channel_name, reason="not a trade signal")
            return

        self._status.parsed_signals += 1
        channel = TelegramChannelConfig(
            name=channel_name,
            url=f"tradlia:{row.get('channel_id') or signal_id}",
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
    ) -> None:
        entry = {
            "at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
            "kind": "tradlia_copy",
            "status": status,
            "channel": channel,
            "symbol": symbol,
            "reason": reason,
        }
        if result:
            entry["result"] = {
                "status": result.get("status"),
                "reason": result.get("reason"),
                "execution_reason": result.get("execution_reason"),
                "symbol": result.get("symbol"),
            }
        self._status.recent_actions.append(entry)
        if len(self._status.recent_actions) > 80:
            self._status.recent_actions = self._status.recent_actions[-80:]
