from __future__ import annotations

import logging
import threading
from dataclasses import asdict, dataclass
from datetime import datetime, timezone

from .config import AppConfig, trade_symbol_for_account
from . import forex_trade
from .daily_risk import compute_daily_risk_status
from .decision import resolve_trade_filters
from .mt5_client import MT5Client
from .live_session import LIVE_SCAN_BARS
from .state import StateStore
from .signal_engine import latest_closed_signal
from .symbols import resolve_trade_symbol
from .strategy import Signal
from .trader import TradeExecutor


@dataclass
class LoopStatus:
    running: bool = False
    started_at: str | None = None
    scans_completed: int = 0
    last_scan_at: str | None = None
    last_error: str | None = None
    last_signals: int = 0
    last_placed: int = 0
    last_skipped: int = 0


@dataclass
class ScanSummary:
    signals: int = 0
    placed: int = 0
    skipped: int = 0
    errors: int = 0
    daily_halted: bool = False
    daily_loss: float = 0.0
    daily_loss_limit: float = 0.0


class SignalBot:
    def __init__(self, config: AppConfig, logger: logging.Logger):
        self.config = config
        self.logger = logger
        self.client = MT5Client(config.mt5)
        self.state = StateStore(config.bot.state_file)
        self.executor = TradeExecutor(config, self.client, self.state, logger)
        self._stop_event = threading.Event()
        self._loop_thread: threading.Thread | None = None
        self._status = LoopStatus()

    def _is_demo_account(self) -> bool:
        return bool(self.config.mt5.is_demo)

    def _place_signal(self, signal) -> str:
        trade_symbol = resolve_trade_symbol(
            signal.symbol,
            self.config,
            is_demo=self._is_demo_account(),
            append_suffix=self.config.mt5.append_broker_symbol_suffix,
        )
        if trade_symbol != signal.symbol:
            signal = Signal(
                setup_id=signal.setup_id,
                symbol=trade_symbol,
                market_key=signal.market_key,
                name=signal.name,
                side=signal.side,
                time=signal.time,
                entry=signal.entry,
                sl=signal.sl,
                tps=list(signal.tps),
                lot_per_leg=signal.lot_per_leg,
                risk_distance=signal.risk_distance,
                session=signal.session,
                reason=signal.reason,
                algorithm=signal.algorithm,
                trail_atr_mult=signal.trail_atr_mult,
                ema_fast_len=signal.ema_fast_len,
                ema_slow_len=signal.ema_slow_len,
                atr_at_entry=signal.atr_at_entry,
            )
        if signal.algorithm == "forex_trade":
            forex_cfg = self.config.bot.forex_trade
            spread_allowed, spread_reason = forex_trade.spread_ok(self.client, trade_symbol, forex_cfg)
            if not spread_allowed:
                self.logger.info("SPREAD SKIP %s %s", trade_symbol, spread_reason)
                return "skipped"
            lot = forex_trade.resolve_lot_size(
                self.client,
                trade_symbol,
                signal.risk_distance,
                forex_cfg,
                fallback_lot=signal.lot_per_leg,
            )
            signal = forex_trade.with_lot(signal, lot)
        return self.executor.place_signal(signal)

    def run_once(self) -> ScanSummary:
        self.client.initialize()
        self.executor.manage_tp_protection()
        if self.config.bot.signal_algorithm == "forex_trade":
            forex_trade.manage_rsi_exits(
                self.client,
                self.config,
                self.logger,
                is_demo=self._is_demo_account(),
            )
        summary = ScanSummary()
        daily_risk = self.daily_risk_status()
        summary.daily_halted = bool(daily_risk.get("halted"))
        summary.daily_loss = float(daily_risk.get("loss", 0.0) or 0.0)
        summary.daily_loss_limit = float(daily_risk.get("loss_limit", 0.0) or 0.0)
        if summary.daily_halted:
            if daily_risk.get("win_halted"):
                self.logger.warning(
                    "DAILY WIN HALT active date=%s gain=%.2f target=%.2f start_equity=%.2f equity=%.2f; no new trades today",
                    daily_risk.get("date"),
                    float(daily_risk.get("gain", 0.0) or 0.0),
                    float(daily_risk.get("win_target", 0.0) or 0.0),
                    float(daily_risk.get("start_equity", 0.0) or 0.0),
                    float(daily_risk.get("equity", 0.0) or 0.0),
                )
            else:
                self.logger.warning(
                    "DAILY LOSS HALT active date=%s loss=%.2f limit=%.2f peak_equity=%.2f equity=%.2f; no new trades today",
                    daily_risk.get("date"),
                    summary.daily_loss,
                    summary.daily_loss_limit,
                    float(daily_risk.get("peak_equity", daily_risk.get("start_balance", 0.0)) or 0.0),
                    float(daily_risk.get("equity", 0.0) or 0.0),
                )
            return summary

        for symbol_cfg in self.config.enabled_symbols:
            try:
                trade_symbol = trade_symbol_for_account(symbol_cfg, is_demo=self._is_demo_account())
                if self.config.bot.signal_algorithm == "forex_trade":
                    forex_cfg = self.config.bot.forex_trade
                    if not forex_trade.symbol_allowed(symbol_cfg, forex_cfg):
                        continue
                    timeframe = forex_cfg.timeframe
                    bars = max(LIVE_SCAN_BARS, forex_cfg.bars)
                else:
                    timeframe = symbol_cfg.timeframe
                    bars = LIVE_SCAN_BARS
                df = self.client.rates(trade_symbol, timeframe, bars)
                signal = latest_closed_signal(self.config, df, symbol_cfg, self.config.risk)
                if signal is None:
                    self.logger.info("NO SIGNAL %s %s", symbol_cfg.symbol, timeframe)
                    continue
                summary.signals += 1
                outcome = self._place_signal(signal)
                if outcome in ("placed", "paper"):
                    summary.placed += 1
                else:
                    summary.skipped += 1
            except Exception as exc:  # noqa: BLE001
                summary.errors += 1
                self.logger.exception("SCAN ERROR %s %s: %s", symbol_cfg.symbol, symbol_cfg.timeframe, exc)
        return summary

    def is_auto_loop_running(self) -> bool:
        return self._loop_thread is not None and self._loop_thread.is_alive()

    def auto_loop_status(self, *, include_mt5: bool = True) -> dict:
        status = asdict(self._status)
        status["running"] = self.is_auto_loop_running()
        status["dry_run"] = self.config.bot.dry_run
        status["poll_seconds"] = self.config.bot.poll_seconds
        status["strategy"] = self.config.bot.strategy
        status["trade_decision_profile"] = self.config.bot.trade_decision_profile
        status["max_concurrent_setups"] = self.config.bot.max_concurrent_setups
        status["decision_filters"] = asdict(resolve_trade_filters(self.config))
        status["max_setups_active"] = status["decision_filters"]["max_setups"]
        if include_mt5:
            try:
                status["daily_risk"] = self.daily_risk_status()
            except Exception as exc:  # noqa: BLE001
                status["daily_risk"] = {"error": str(exc), "halted": False}
        else:
            cached = self.state.read().get("daily_risk", {})
            if not self.config.risk.daily_loss_guard_active() and not self.config.risk.daily_win_guard_active():
                status["daily_risk"] = {
                    "enabled": False,
                    "halted": False,
                    "use_daily_loss_guard": self.config.risk.use_daily_loss_guard,
                    "max_daily_loss_pct": self.config.risk.max_daily_loss_pct,
                    "use_daily_win_guard": self.config.risk.use_daily_win_guard,
                    "daily_win_target_mode": self.config.risk.daily_win_target_mode,
                    "max_daily_win_pct": self.config.risk.max_daily_win_pct,
                    "max_daily_win_usd": self.config.risk.max_daily_win_usd,
                }
            else:
                status["daily_risk"] = cached or {
                    "enabled": True,
                    "halted": False,
                }
                if status["daily_risk"]:
                    status["daily_risk"] = {
                        **status["daily_risk"],
                        "enabled": True,
                        "use_daily_loss_guard": self.config.risk.use_daily_loss_guard,
                        "max_daily_loss_pct": self.config.risk.max_daily_loss_pct,
                        "use_daily_win_guard": self.config.risk.use_daily_win_guard,
                        "daily_win_target_mode": self.config.risk.daily_win_target_mode,
                        "max_daily_win_pct": self.config.risk.max_daily_win_pct,
                        "max_daily_win_usd": self.config.risk.max_daily_win_usd,
                    }
        return status

    def daily_risk_status(self) -> dict:
        return compute_daily_risk_status(self.client, self.state, self.config.risk)

    def start_auto_loop(self) -> dict:
        if self.is_auto_loop_running():
            return self.auto_loop_status()

        self._stop_event.clear()
        self._status = LoopStatus(
            running=True,
            started_at=datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        )
        self._loop_thread = threading.Thread(target=self._auto_loop, name="rsi-bot-loop", daemon=True)
        self._loop_thread.start()
        self.state.set_auto_loop_enabled(True)
        if self.config.bot.dry_run:
            self.logger.info(
                "AUTO LOOP START dry_run=true poll=%ss strategy=%s profile=%s",
                self.config.bot.poll_seconds,
                self.config.bot.strategy,
                self.config.bot.trade_decision_profile,
            )
        else:
            self.logger.warning(
                "AUTO LOOP START dry_run=false LIVE ORDERS ENABLED poll=%ss strategy=%s profile=%s",
                self.config.bot.poll_seconds,
                self.config.bot.strategy,
                self.config.bot.trade_decision_profile,
            )
        return self.auto_loop_status()

    def stop_auto_loop(self) -> dict:
        if not self.is_auto_loop_running():
            self._status.running = False
            self.state.set_auto_loop_enabled(False)
            return self.auto_loop_status()

        self.logger.info("AUTO LOOP STOP requested")
        self._stop_event.set()
        if self._loop_thread is not None:
            self._loop_thread.join(timeout=self.config.bot.poll_seconds + 60)
        self._status.running = False
        self.state.set_auto_loop_enabled(False)
        self.logger.info("AUTO LOOP STOPPED scans=%s", self._status.scans_completed)
        return self.auto_loop_status()

    def _auto_loop(self) -> None:
        self.logger.info(
            "BOT LOOP strategy=%s profile=%s dry_run=%s poll=%ss",
            self.config.bot.strategy,
            self.config.bot.trade_decision_profile,
            self.config.bot.dry_run,
            self.config.bot.poll_seconds,
        )
        while not self._stop_event.is_set():
            try:
                summary = self.run_once()
                self._status.scans_completed += 1
                self._status.last_scan_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
                self._status.last_signals = summary.signals
                self._status.last_placed = summary.placed
                self._status.last_skipped = summary.skipped
                self._status.last_error = None
                if summary.signals or summary.placed:
                    self.logger.info(
                        "SCAN DONE signals=%s placed=%s skipped=%s errors=%s",
                        summary.signals,
                        summary.placed,
                        summary.skipped,
                        summary.errors,
                    )
            except Exception as exc:  # noqa: BLE001
                self._status.last_error = str(exc)
                self.logger.exception("BOT ERROR %s", exc)

            if self._stop_event.wait(self.config.bot.poll_seconds):
                break

        self._status.running = False

    def run_forever(self) -> None:
        self._stop_event.clear()
        try:
            self._auto_loop()
        except KeyboardInterrupt:
            self.logger.info("BOT STOPPED by user")
