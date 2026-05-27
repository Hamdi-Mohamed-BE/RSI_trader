from __future__ import annotations

import logging
import threading
from dataclasses import asdict, dataclass
from datetime import datetime, time, timezone

from .config import AppConfig, trade_symbol_for_account
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
        return self.executor.place_signal(signal)

    def run_once(self) -> ScanSummary:
        self.client.initialize()
        self.executor.manage_tp_protection()
        summary = ScanSummary()
        daily_risk = self.daily_risk_status()
        summary.daily_halted = bool(daily_risk.get("halted"))
        summary.daily_loss = float(daily_risk.get("loss", 0.0) or 0.0)
        summary.daily_loss_limit = float(daily_risk.get("loss_limit", 0.0) or 0.0)
        if summary.daily_halted:
            self.logger.warning(
                "DAILY LOSS HALT active date=%s loss=%.2f limit=%.2f start_balance=%.2f equity=%.2f; no new trades today",
                daily_risk.get("date"),
                summary.daily_loss,
                summary.daily_loss_limit,
                float(daily_risk.get("start_balance", 0.0) or 0.0),
                float(daily_risk.get("equity", 0.0) or 0.0),
            )
            return summary

        for symbol_cfg in self.config.enabled_symbols:
            try:
                trade_symbol = trade_symbol_for_account(symbol_cfg, is_demo=self._is_demo_account())
                df = self.client.rates(trade_symbol, symbol_cfg.timeframe, LIVE_SCAN_BARS)
                signal = latest_closed_signal(self.config, df, symbol_cfg, self.config.risk)
                if signal is None:
                    self.logger.info("NO SIGNAL %s %s", symbol_cfg.symbol, symbol_cfg.timeframe)
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
            status["daily_risk"] = cached or {
                "enabled": self.config.risk.daily_loss_guard_active(),
                "halted": False,
            }
        return status

    def daily_risk_status(self) -> dict:
        risk_cfg = self.config.risk
        max_loss_pct = risk_cfg.effective_daily_loss_pct()
        now = datetime.now(timezone.utc).replace(microsecond=0)
        today = now.date().isoformat()
        account = self.client.account_snapshot()
        equity = float(account["equity"])
        balance = float(account["balance"])
        floating_pnl = float(account.get("floating_pnl", 0.0) or 0.0)

        if not risk_cfg.daily_loss_guard_active():
            return {
                "enabled": False,
                "halted": False,
                "date": today,
                "start_balance": balance,
                "equity": equity,
                "loss": 0.0,
                "loss_limit": 0.0,
                "use_daily_loss_guard": risk_cfg.use_daily_loss_guard,
                "max_daily_loss_pct": risk_cfg.max_daily_loss_pct,
            }

        state = self.state.read()
        daily_risk = state.get("daily_risk", {})
        if daily_risk.get("date") != today:
            day_start = datetime.combine(now.date(), time.min, tzinfo=timezone.utc)
            realized_today = self.client.realized_pnl_since(day_start)
            start_balance = round(balance - realized_today, 2)
            if start_balance <= 0:
                start_balance = balance
            daily_risk = {
                "date": today,
                "start_balance": start_balance,
                "created_at": now.isoformat(),
                "halted": False,
                "halted_at": None,
            }

        start_balance = float(daily_risk.get("start_balance", balance) or balance)
        loss_limit = round(start_balance * float(max_loss_pct) / 100.0, 2)
        loss = round(max(0.0, start_balance - equity), 2)
        halted = loss_limit > 0 and loss >= loss_limit

        if halted and not daily_risk.get("halted"):
            daily_risk["halted_at"] = now.isoformat()
        daily_risk.update(
            {
                "enabled": True,
                "halted": halted,
                "use_daily_loss_guard": risk_cfg.use_daily_loss_guard,
                "max_daily_loss_pct": float(max_loss_pct),
                "loss_limit": loss_limit,
                "loss": loss,
                "equity": round(equity, 2),
                "balance": round(balance, 2),
                "floating_pnl": round(floating_pnl, 2),
                "updated_at": now.isoformat(),
            }
        )
        self.state.update_daily_risk(daily_risk)
        return daily_risk

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
