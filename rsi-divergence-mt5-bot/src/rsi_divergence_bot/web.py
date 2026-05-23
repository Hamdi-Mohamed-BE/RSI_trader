from __future__ import annotations

import asyncio
import hashlib
import hmac
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import parse_qs, quote

from fastapi import FastAPI, HTTPException, Query, Request
from pydantic import BaseModel, Field
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

from .backtest import run_backtest, run_chart_backtest
from .bot import SignalBot
from .config import (
    AppConfig,
    StrategyMode,
    default_symbol_lot,
    save_config,
    update_bot_strategy,
    update_symbol_enabled,
    update_symbol_lots,
)
from .decision import resolve_trade_filters
from .logging_utils import recent_logs
from .manual_trade import _validate_geometry, parse_manual_trade
from .strategy_modes import canonical_strategy
from .symbols import market_key
from .telegram_signals import TelegramSignalsBot

STATIC_DIR = Path(__file__).resolve().parent / "static"


class SymbolSettings(BaseModel):
    lots: dict[str, float] = Field(default_factory=dict)
    enabled: dict[str, bool] = Field(default_factory=dict)
    persist: bool = True


class LotUpdates(BaseModel):
    lots: dict[str, float] = Field(min_length=1)
    persist: bool = True


class ManualTradeRequest(BaseModel):
    text: str = Field(min_length=1)
    confirm_live: bool = False


class TelegramSignalsStartRequest(BaseModel):
    protect_tp: bool = False


class BotSettingsRequest(BaseModel):
    strategy: StrategyMode
    persist: bool = True


class AutoRunStartRequest(BaseModel):
    lots: dict[str, float] = Field(default_factory=dict)
    enabled: dict[str, bool] = Field(default_factory=dict)
    persist: bool = True
    strategy: StrategyMode | None = None
    strategy_persist: bool = True


class RunOnceRequest(BaseModel):
    lots: dict[str, float] = Field(default_factory=dict)
    enabled: dict[str, bool] = Field(default_factory=dict)
    persist: bool = True
    strategy: StrategyMode | None = None
    strategy_persist: bool = False


def create_app(config: AppConfig, bot: SignalBot, config_path: Path) -> FastAPI:
    app = FastAPI(title="RSI Divergence MT5 Bot")
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
    telegram_bot = TelegramSignalsBot(config, bot.client, bot.state, bot.logger, bot.daily_risk_status)

    def auth_token() -> str:
        seed = f"{config.auth.username}:{config.auth.password}".encode("utf-8")
        return hmac.new(seed, b"rsi-divergence-mt5-bot", hashlib.sha256).hexdigest()

    def authenticated(request: Request) -> bool:
        cookie = request.cookies.get(config.auth.cookie_name, "")
        return hmac.compare_digest(cookie, auth_token())

    def safe_next(value: str | None) -> str:
        if not value or not value.startswith("/") or value.startswith("//"):
            return "/"
        return value

    @app.middleware("http")
    async def require_login(request: Request, call_next):
        path = request.url.path
        if path in {"/login", "/favicon.ico"} or path.startswith("/static/"):
            return await call_next(request)

        if authenticated(request):
            return await call_next(request)

        if path.startswith("/api/"):
            return JSONResponse({"detail": "Authentication required"}, status_code=401)

        login_url = f"/login?next={quote(path)}"
        return RedirectResponse(login_url, status_code=303)

    @app.get("/login")
    def login_page() -> FileResponse:
        return FileResponse(STATIC_DIR / "login.html")

    @app.post("/login")
    async def login(request: Request):
        body = (await request.body()).decode("utf-8")
        form = parse_qs(body)
        username = form.get("username", [""])[0]
        password = form.get("password", [""])[0]
        next_url = safe_next(form.get("next", ["/"])[0])

        if username != config.auth.username or password != config.auth.password:
            return RedirectResponse(f"/login?error=1&next={quote(next_url)}", status_code=303)

        response = RedirectResponse(next_url, status_code=303)
        response.set_cookie(
            config.auth.cookie_name,
            auth_token(),
            max_age=60 * 60 * 24 * 7,
            httponly=True,
            samesite="lax",
        )
        return response

    @app.get("/logout")
    def logout():
        response = RedirectResponse("/login", status_code=303)
        response.delete_cookie(config.auth.cookie_name)
        return response

    def symbol_payload() -> list[dict]:
        return [
            {
                "symbol": item.symbol,
                "market_key": item.key,
                "name": item.name,
                "enabled": item.enabled,
                "timeframe": item.timeframe,
                "lot_per_leg": item.lot_per_leg,
                "reset_lot_per_leg": default_symbol_lot(item),
                "max_setup_risk_usd": item.max_setup_risk_usd,
                "confirmation": item.confirmation,
                "sessions": item.sessions,
            }
            for item in config.symbols
        ]

    def symbol_stats() -> dict:
        enabled = config.enabled_symbols
        return {
            "total": len(config.symbols),
            "enabled": len(enabled),
            "lots_used": {item.symbol: item.lot_per_leg for item in enabled},
        }

    def apply_symbol_settings(lots: dict[str, float], enabled: dict[str, bool], persist: bool) -> list[dict]:
        try:
            updated_lots = update_symbol_lots(config, lots)
            updated_enabled = update_symbol_enabled(config, enabled)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

        unknown_lots = sorted(set(lots) - set(updated_lots))
        if unknown_lots:
            raise HTTPException(status_code=400, detail=f"Unknown symbols in lots: {', '.join(unknown_lots)}")

        unknown_enabled = sorted(set(enabled) - set(updated_enabled))
        if unknown_enabled:
            raise HTTPException(status_code=400, detail=f"Unknown symbols in enabled: {', '.join(unknown_enabled)}")

        if persist:
            save_config(config_path, config)

        bot.logger.info("SYMBOL SETTINGS persist=%s symbols=%s", persist, len(lots))
        return symbol_payload()

    def apply_bot_strategy(strategy: StrategyMode, persist: bool) -> None:
        normalized = canonical_strategy(strategy)
        if bot.is_auto_loop_running() and normalized != config.bot.strategy:
            raise HTTPException(
                status_code=409,
                detail="Stop auto run before changing the shared bot strategy.",
            )
        update_bot_strategy(config, strategy)
        if persist:
            save_config(config_path, config)
        bot.logger.info("BOT STRATEGY strategy=%s persist=%s", config.bot.strategy, persist)

    async def require_mt5_ready() -> dict:
        status = await asyncio.to_thread(bot.client.connection_status)
        if not status.get("connected"):
            detail = status.get("error") or "MT5 is not connected yet."
            raise HTTPException(status_code=503, detail=f"MT5 not ready: {detail}")
        return status

    @app.on_event("startup")
    async def connect_mt5_on_startup() -> None:
        async def wait_for_mt5_and_start() -> None:
            max_attempts = 90
            delay_seconds = 10
            for attempt in range(1, max_attempts + 1):
                if bot.is_auto_loop_running():
                    return
                try:
                    status = await asyncio.to_thread(bot.client.connection_status)
                    if status.get("connected"):
                        bot.logger.info(
                            "MT5 connected login=%s server=%s balance=%s",
                            status.get("login"),
                            status.get("server"),
                            status.get("balance"),
                        )
                        if config.bot.auto_start or bot.state.auto_loop_enabled():
                            loop_status = bot.start_auto_loop()
                            if config.bot.dry_run:
                                bot.logger.info(
                                    "AUTO START signal loop dry_run=true poll=%ss profile=%s enabled_symbols=%s",
                                    config.bot.poll_seconds,
                                    config.bot.trade_decision_profile,
                                    len(config.enabled_symbols),
                                )
                            else:
                                bot.logger.warning(
                                    "AUTO START signal loop dry_run=false LIVE ORDERS ENABLED poll=%ss profile=%s enabled_symbols=%s",
                                    config.bot.poll_seconds,
                                    config.bot.trade_decision_profile,
                                    len(config.enabled_symbols),
                                )
                            bot.logger.info("AUTO START loop running=%s", loop_status.get("running"))
                        return
                    error = status.get("error")
                except Exception as exc:  # noqa: BLE001
                    error = str(exc)

                if attempt == 1 or attempt % 6 == 0:
                    bot.logger.warning(
                        "MT5 not ready yet attempt=%s/%s error=%s",
                        attempt,
                        max_attempts,
                        error,
                    )
                await asyncio.sleep(delay_seconds)

            bot.logger.warning("MT5 did not become ready; auto loop was not started")

        asyncio.create_task(wait_for_mt5_and_start())

    @app.get("/")
    @app.get("/backtest")
    @app.get("/settings")
    @app.get("/manual-trade")
    @app.get("/logs")
    @app.get("/telegram-signals")
    def index() -> FileResponse:
        return FileResponse(STATIC_DIR / "index.html")

    @app.get("/api/config")
    def api_config() -> dict:
        now = datetime.now(timezone.utc).replace(microsecond=0)
        stats = symbol_stats()
        return {
            "bot": {
                "dry_run": config.bot.dry_run,
                "auto_start": config.bot.auto_start,
                "poll_seconds": config.bot.poll_seconds,
                "magic": config.bot.magic,
                "strategy": config.bot.strategy,
                "trade_decision_profile": config.bot.trade_decision_profile,
                "max_concurrent_setups": config.bot.max_concurrent_setups,
            },
            "risk": config.risk.model_dump(mode="python"),
            "telegram_signals": {
                "enabled": config.telegram_signals.enabled,
                "poll_seconds": config.telegram_signals.poll_seconds,
                "telegram_url": config.telegram_signals.telegram_url,
                "channels": [channel.model_dump(mode="python") for channel in config.telegram_signals.channels],
                "gemini_model": config.telegram_signals.gemini_model,
                "gemini_api_key_configured": bool(config.telegram_signals.gemini_api_key),
                "ignore_open_symbol_trades": config.telegram_signals.ignore_open_symbol_trades,
                "max_tps": config.telegram_signals.max_tps,
                "default_lot": config.telegram_signals.default_lot,
                "max_message_age_seconds": config.telegram_signals.max_message_age_seconds,
            },
            "decision_filters": asdict(resolve_trade_filters(config)),
            "auto_run": bot.auto_loop_status(),
            "symbols": symbol_payload(),
            "symbol_stats": stats,
            "defaults": {
                "backtest_start": "2026-05-13T00:00:00+00:00",
                "backtest_end": now.isoformat(),
                "starting_balance": 1000.0,
            },
        }

    @app.post("/api/symbols/settings")
    def update_settings(body: SymbolSettings) -> dict:
        if not body.lots and not body.enabled:
            stats = symbol_stats()
            return {
                "status": "noop",
                "symbols": symbol_payload(),
                "symbol_stats": stats,
            }

        symbols = apply_symbol_settings(body.lots, body.enabled, body.persist)
        stats = symbol_stats()
        return {
            "status": "saved" if body.persist else "applied",
            "symbols": symbols,
            "symbol_stats": stats,
        }

    @app.post("/api/symbols/lots")
    def update_lots(body: LotUpdates) -> dict:
        return update_settings(SymbolSettings(lots=body.lots, persist=body.persist))

    @app.get("/api/logs")
    def logs() -> list[str]:
        return recent_logs(200)

    @app.post("/api/bot/settings")
    def update_bot_settings(body: BotSettingsRequest) -> dict:
        apply_bot_strategy(body.strategy, body.persist)
        return {
            "status": "saved" if body.persist else "applied",
            "strategy": config.bot.strategy,
            "auto_run": bot.auto_loop_status(),
        }

    @app.post("/api/run-once")
    async def run_once(body: RunOnceRequest | None = None) -> dict:
        if body is not None:
            if body.lots or body.enabled:
                apply_symbol_settings(body.lots, body.enabled, body.persist)
            if body.strategy is not None:
                apply_bot_strategy(body.strategy, body.strategy_persist)
        await require_mt5_ready()
        try:
            summary = await asyncio.to_thread(bot.run_once)
        except Exception as exc:  # noqa: BLE001
            bot.logger.exception("MANUAL SCAN failed: %s", exc)
            raise HTTPException(status_code=503, detail=f"MT5 scan failed: {exc}") from exc
        stats = symbol_stats()
        return {
            "status": "scan complete",
            "dry_run": config.bot.dry_run,
            "strategy": config.bot.strategy,
            "signals": summary.signals,
            "placed": summary.placed,
            "skipped": summary.skipped,
            "errors": summary.errors,
            "daily_halted": summary.daily_halted,
            "daily_loss": summary.daily_loss,
            "daily_loss_limit": summary.daily_loss_limit,
            **stats,
        }

    @app.post("/api/manual-trade")
    async def manual_trade(body: ManualTradeRequest) -> dict:
        if not body.confirm_live:
            raise HTTPException(status_code=400, detail="Live confirmation is required.")
        try:
            await require_mt5_ready()
            plan = parse_manual_trade(body.text, config)
            daily_risk = await asyncio.to_thread(bot.daily_risk_status)
            if daily_risk.get("enabled") and daily_risk.get("halted"):
                raise HTTPException(
                    status_code=409,
                    detail=(
                        "Daily loss guard is active. "
                        f"Loss {daily_risk.get('loss')} reached limit {daily_risk.get('loss_limit')}."
                    ),
                )
            bot.logger.warning(
                "MANUAL LIVE TRADE requested symbol=%s side=%s lot=%s sl=%s tps=%s",
                plan.symbol,
                plan.side,
                plan.lot,
                plan.sl,
                plan.tps,
            )
            tick = await asyncio.to_thread(bot.client.tick, plan.symbol)
            if tick is None:
                raise ValueError(f"No live tick for {plan.symbol}.")
            from .manual_trade import _field as manual_field

            entry = float(manual_field(tick, "ask") if plan.side == "buy" else manual_field(tick, "bid"))
            _validate_geometry(plan, entry)
            symbol_cfg = next((item for item in config.symbols if item.symbol == plan.symbol), None)
            setup_id = f"manual:{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"
            result = await asyncio.to_thread(
                bot.executor.place_market_setup,
                setup_id=setup_id,
                symbol=plan.symbol,
                market_key=symbol_cfg.key if symbol_cfg else market_key(plan.symbol),
                side=plan.side,
                sl=plan.sl,
                tps=plan.tps,
                lot_per_leg=plan.lot,
                entry_price=entry,
                comment="manual test trade",
            )
            result = {
                "symbol": plan.symbol,
                "side": plan.side,
                "lot": plan.lot,
                "entry": entry,
                "sl": plan.sl,
                "tps": plan.tps,
                **result,
            }
        except ValueError as exc:
            bot.logger.warning("MANUAL LIVE TRADE rejected: %s", exc)
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except Exception as exc:  # noqa: BLE001
            bot.logger.exception("MANUAL LIVE TRADE failed: %s", exc)
            raise HTTPException(status_code=500, detail=str(exc)) from exc

        bot.logger.warning(
            "MANUAL LIVE TRADE done symbol=%s side=%s status=%s",
            result["symbol"],
            result["side"],
            result.get("status"),
        )
        return {"status": result.get("status", "sent"), **result}

    @app.get("/api/auto-run/status")
    def auto_run_status() -> dict:
        status = bot.auto_loop_status()
        status.update(symbol_stats())
        return status

    @app.post("/api/auto-run/start")
    async def auto_run_start(body: AutoRunStartRequest | None = None) -> dict:
        if body is not None:
            if body.lots or body.enabled:
                apply_symbol_settings(body.lots, body.enabled, body.persist)
            if body.strategy is not None:
                apply_bot_strategy(body.strategy, body.strategy_persist)
        await require_mt5_ready()
        status = bot.start_auto_loop()
        status.update(symbol_stats())
        return status

    @app.post("/api/auto-run/stop")
    def auto_run_stop() -> dict:
        return bot.stop_auto_loop()

    @app.get("/api/live")
    async def live_data() -> dict:
        try:
            return await asyncio.to_thread(bot.client.live_snapshot, config.bot.magic)
        except Exception as exc:  # noqa: BLE001
            return {
                "updated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
                "bot_magic": config.bot.magic,
                "connected": False,
                "error": str(exc),
                "account": None,
                "positions": [],
                "deals": [],
            }

    @app.get("/api/telegram-signals/status")
    def telegram_signals_status() -> dict:
        return telegram_bot.status()

    @app.post("/api/telegram-signals/start")
    async def telegram_signals_start(body: TelegramSignalsStartRequest) -> dict:
        if not config.telegram_signals.gemini_api_key and not telegram_bot.status().get("gemini_api_key_configured"):
            raise HTTPException(
                status_code=400,
                detail="Gemini API key missing. Set telegram_signals.gemini_api_key in config.yaml or GEMINI_API_KEY.",
            )
        await require_mt5_ready()
        return telegram_bot.start(protect_tp=body.protect_tp)

    @app.post("/api/telegram-signals/stop")
    def telegram_signals_stop() -> dict:
        return telegram_bot.stop()

    @app.post("/api/telegram-signals/clear-messages")
    def telegram_signals_clear_messages() -> dict:
        return telegram_bot.clear_message_history()

    @app.get("/api/backtest/chart")
    async def backtest_chart(
        symbol: str = Query(...),
        timeframe: str = Query("M5"),
        start: datetime = Query(...),
        end: datetime = Query(...),
    ) -> dict:
        bot.logger.info(
            "CHART BACKTEST %s %s %s -> %s strategy=%s",
            symbol,
            timeframe,
            start.isoformat(),
            end.isoformat(),
            config.bot.strategy,
        )
        try:
            await require_mt5_ready()
            result = await asyncio.to_thread(
                run_chart_backtest,
                bot.client,
                config,
                symbol,
                timeframe,
                start,
                end,
            )
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except Exception as exc:  # noqa: BLE001
            raise HTTPException(status_code=500, detail=str(exc)) from exc
        bot.logger.info(
            "CHART BACKTEST DONE %s bars=%s trades=%s",
            symbol,
            result["summary"]["bars"],
            result["summary"]["trades"],
        )
        return result

    @app.get("/api/backtest")
    async def backtest(
        start: datetime = Query(...),
        end: datetime = Query(...),
        starting_balance: float = Query(1000.0, gt=0),
    ) -> dict:
        bot.logger.info(
            "BACKTEST START %s -> %s strategy=%s",
            start.isoformat(),
            end.isoformat(),
            config.bot.strategy,
        )
        try:
            await require_mt5_ready()
            result = await asyncio.to_thread(
                run_backtest,
                bot.client,
                config,
                start,
                end,
                starting_balance,
                bot.logger,
            )
        except HTTPException:
            raise
        except Exception as exc:  # noqa: BLE001
            bot.logger.exception("BACKTEST failed: %s", exc)
            raise HTTPException(status_code=503, detail=f"Backtest failed: {exc}") from exc
        result.update(symbol_stats())
        bot.logger.info("BACKTEST DONE total_pnl=%s", result.get("total_pnl"))
        return result

    return app
