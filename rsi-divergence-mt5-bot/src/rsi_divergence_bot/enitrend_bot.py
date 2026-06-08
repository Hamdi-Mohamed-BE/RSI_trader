from __future__ import annotations

import logging
import threading
from dataclasses import asdict, dataclass
from datetime import datetime, timezone

from .config import AppConfig
from .enitrend import (
    EniTrendBacktestSettings,
    MOMENTUM_BOT_COMMENT,
    _OpenTrade,
    _update_protective_stops,
    active_symbol_specs,
    detect_live_entry,
    latest_closed_trend,
)
from .mt5_client import MT5Client
from .state import StateStore
from .symbols import market_key


@dataclass
class MomentumLoopStatus:
    running: bool = False
    started_at: str | None = None
    scans_completed: int = 0
    last_scan_at: str | None = None
    last_error: str | None = None
    last_signals: int = 0
    last_placed: int = 0
    last_skipped: int = 0
    last_closed: int = 0
    active_symbols: int = 0
    poll_seconds: int = 60


@dataclass
class MomentumScanSummary:
    signals: int = 0
    placed: int = 0
    skipped: int = 0
    closed: int = 0
    errors: int = 0


class EniTrendMomentumBot:
    def __init__(
        self,
        config: AppConfig,
        client: MT5Client,
        state: StateStore,
        logger: logging.Logger,
        daily_risk_status=None,
    ):
        self.config = config
        self.client = client
        self.state = state
        self.logger = logger
        self.daily_risk_status = daily_risk_status
        self._settings = EniTrendBacktestSettings()
        self._poll_seconds = 60
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None
        self._status = MomentumLoopStatus()

    def momentum_magic(self) -> int:
        return int(self.config.bot.magic) + 1001

    def is_running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    def status(self) -> dict:
        data = asdict(self._status)
        data["running"] = self.is_running()
        data["dry_run"] = self.config.bot.dry_run
        data["settings"] = asdict(self._settings)
        data["active_symbol_count"] = len(self.config.enabled_symbols)
        data["active_symbols"] = [item.symbol for item in self.config.enabled_symbols]
        return data

    def start(self, settings: EniTrendBacktestSettings, *, poll_seconds: int = 60) -> dict:
        if self.is_running():
            return self.status()
        if not self.config.enabled_symbols:
            raise ValueError("No enabled symbols in Settings.")
        self._settings = settings
        self._poll_seconds = max(15, int(poll_seconds))
        self._stop_event.clear()
        self._status = MomentumLoopStatus(
            running=True,
            started_at=datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
            poll_seconds=self._poll_seconds,
            active_symbols=len(self.config.enabled_symbols),
        )
        self._thread = threading.Thread(target=self._loop, name="enitrend-momentum-bot", daemon=True)
        self._thread.start()
        if self.config.bot.dry_run:
            self.logger.info(
                "MOMENTUM BOT START dry_run=true poll=%ss symbols=%s tf=%s/%s",
                self._poll_seconds,
                len(self.config.enabled_symbols),
                settings.execution_timeframe,
                settings.higher_timeframe,
            )
        else:
            self.logger.warning(
                "MOMENTUM BOT START dry_run=false LIVE ORDERS poll=%ss symbols=%s tf=%s/%s",
                self._poll_seconds,
                len(self.config.enabled_symbols),
                settings.execution_timeframe,
                settings.higher_timeframe,
            )
        return self.status()

    def stop(self) -> dict:
        if not self.is_running():
            self._status.running = False
            return self.status()
        self.logger.info("MOMENTUM BOT STOP requested")
        self._stop_event.set()
        if self._thread is not None:
            self._thread.join(timeout=self._poll_seconds + 60)
        self._status.running = False
        self.logger.info("MOMENTUM BOT STOPPED scans=%s", self._status.scans_completed)
        return self.status()

    def run_once(self) -> MomentumScanSummary:
        self.client.initialize()
        summary = MomentumScanSummary()
        if self.daily_risk_status:
            daily = self.daily_risk_status()
            if daily.get("halted"):
                self.logger.warning("MOMENTUM BOT daily guard active — skipping new entries")
                return summary

        summary.closed += self._manage_open_positions()
        open_keys = self._open_market_keys()

        for spec in active_symbol_specs(self.config):
            try:
                outcome = self._scan_symbol(spec, open_keys=open_keys)
                if outcome == "placed":
                    summary.placed += 1
                    summary.signals += 1
                    open_keys.add(market_key(spec.display_symbol))
                elif outcome == "paper":
                    summary.placed += 1
                    summary.signals += 1
                    open_keys.add(market_key(spec.display_symbol))
                elif outcome == "signal":
                    summary.signals += 1
                    summary.skipped += 1
                elif outcome == "skipped":
                    summary.skipped += 1
            except Exception as exc:  # noqa: BLE001
                summary.errors += 1
                self.logger.exception("MOMENTUM SCAN ERROR %s: %s", spec.display_symbol, exc)
        return summary

    def _loop(self) -> None:
        while not self._stop_event.is_set():
            try:
                summary = self.run_once()
                self._status.scans_completed += 1
                self._status.last_scan_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
                self._status.last_signals = summary.signals
                self._status.last_placed = summary.placed
                self._status.last_skipped = summary.skipped
                self._status.last_closed = summary.closed
                self._status.last_error = None
                if summary.signals or summary.placed or summary.closed:
                    self.logger.info(
                        "MOMENTUM SCAN signals=%s placed=%s skipped=%s closed=%s errors=%s",
                        summary.signals,
                        summary.placed,
                        summary.skipped,
                        summary.closed,
                        summary.errors,
                    )
            except Exception as exc:  # noqa: BLE001
                self._status.last_error = str(exc)
                self.logger.exception("MOMENTUM BOT ERROR %s", exc)
            if self._stop_event.wait(self._poll_seconds):
                break
        self._status.running = False

    def _open_market_keys(self) -> set[str]:
        keys: set[str] = set()
        magic = self.momentum_magic()
        for pos in self.client.open_positions(magic):
            if int(pos.get("magic") or 0) != magic:
                continue
            if MOMENTUM_BOT_COMMENT not in str(pos.get("comment") or ""):
                continue
            keys.add(market_key(str(pos.get("symbol") or "")))
        return keys

    def _momentum_positions(self) -> list[dict]:
        magic = self.momentum_magic()
        rows: list[dict] = []
        for pos in self.client.open_positions(magic):
            if int(pos.get("magic") or 0) != magic:
                continue
            if MOMENTUM_BOT_COMMENT not in str(pos.get("comment") or ""):
                continue
            rows.append(pos)
        return rows

    def _manage_open_positions(self) -> int:
        closed = 0
        settings = self._settings
        for pos in self._momentum_positions():
            symbol = str(pos.get("symbol") or "")
            side = str(pos.get("side") or "")
            spec = next(
                (item for item in active_symbol_specs(self.config) if item.mt5_symbol == symbol),
                None,
            )
            if spec is None:
                continue
            trend_data = latest_closed_trend(self.client, spec, settings)
            if trend_data is None:
                continue
            trend, atr_value, closed_row = trend_data
            if side == "buy" and trend == -1:
                if not self.config.bot.dry_run:
                    self.client.close_position(int(pos["ticket"]), symbol)
                self.logger.warning("MOMENTUM CLOSE %s buy trend_flip ticket=%s", spec.display_symbol, pos["ticket"])
                closed += 1
                continue
            if side == "sell" and trend == 1:
                if not self.config.bot.dry_run:
                    self.client.close_position(int(pos["ticket"]), symbol)
                self.logger.warning("MOMENTUM CLOSE %s sell trend_flip ticket=%s", spec.display_symbol, pos["ticket"])
                closed += 1
                continue

            if settings.use_break_even or settings.use_trailing_stop:
                entry = float(pos.get("price_open") or 0.0)
                initial_sl = float(pos.get("sl") or 0.0) or None
                tp = float(pos.get("tp") or 0.0) or None
                open_trade = _OpenTrade(
                    side=side,
                    signal_time=closed_row.time,
                    entry_time=closed_row.time,
                    entry=entry,
                    volume=float(pos.get("volume") or settings.volume),
                    initial_sl=initial_sl,
                    sl=initial_sl,
                    tp=tp if tp else None,
                    risk_distance=settings.stop_loss_atr_multiplier * atr_value,
                    entry_index=0,
                )
                _update_protective_stops(open_trade, closed_row, settings)
                new_sl = open_trade.sl
                if new_sl is not None and initial_sl is not None and new_sl != initial_sl and not self.config.bot.dry_run:
                    self.client.update_position_sl(
                        int(pos["ticket"]),
                        symbol,
                        float(new_sl),
                        float(tp or 0.0),
                    )
        return closed

    def _scan_symbol(self, spec, *, open_keys: set[str]) -> str:
        key = market_key(spec.display_symbol)
        if key in open_keys:
            return "skipped"

        signal = detect_live_entry(self.client, spec, self._settings)
        if signal is None:
            return "skipped"

        if self.state.is_seen(signal.setup_id):
            return "skipped"

        self.logger.warning(
            "MOMENTUM SIGNAL %s %s entry=%.5f sl=%s tp=%s vol=%s signal_time=%s",
            signal.display_symbol,
            signal.side.upper(),
            signal.entry,
            signal.sl,
            signal.tp,
            signal.volume,
            signal.signal_time,
        )

        if self.config.bot.dry_run:
            self.state.mark_seen(signal.setup_id)
            return "paper"

        if signal.sl is None and signal.tp is None:
            result = self.client.send_market_bare(
                signal.mt5_symbol,
                signal.side,
                signal.volume,
                self.momentum_magic(),
                MOMENTUM_BOT_COMMENT,
            )
        elif signal.sl is not None and signal.tp is not None:
            result = self.client.send_market(
                signal.mt5_symbol,
                signal.side,
                signal.volume,
                float(signal.sl),
                float(signal.tp),
                self.momentum_magic(),
                MOMENTUM_BOT_COMMENT,
            )
        else:
            self.logger.warning("MOMENTUM SKIP %s partial SL/TP not supported live", signal.display_symbol)
            self.state.mark_seen(signal.setup_id)
            return "skipped"

        retcode = getattr(result, "retcode", None)
        if retcode == self.client.TRADE_DONE:
            self.state.mark_seen(signal.setup_id)
            return "placed"

        self.logger.warning("MOMENTUM FAILED %s retcode=%s", signal.display_symbol, retcode)
        return "skipped"
