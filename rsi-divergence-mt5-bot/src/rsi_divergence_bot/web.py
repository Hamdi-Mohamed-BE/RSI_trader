from __future__ import annotations

import asyncio
import hashlib
import hmac
import os
from dataclasses import asdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import parse_qs, quote

from fastapi import FastAPI, File, HTTPException, Query, Request, UploadFile
from pydantic import BaseModel, Field, field_validator
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

from .backtest import optimize_symbol_timeframes, run_backtest, run_chart_backtest
from .bot import SignalBot
from .symbols import market_key, resolve_trade_symbol
from .config import (
    AppConfig,
    StrategyMode,
    add_telegram_channel,
    broker_symbol_suffix,
    append_broker_symbol_suffix_enabled,
    update_append_broker_symbol_suffix,
    default_symbol_lot,
    update_default_forex_lot,
    remove_telegram_channel,
    save_config,
    symbol_asset_group,
    update_bot_strategy,
    update_signal_algorithm,
    update_symbol_enabled,
    update_symbol_lots,
    update_symbol_timeframes,
    update_symbol_trade_names,
    update_telegram_channel,
    update_telegram_ignore_open_trades,
)
from .config_snapshots import (
    apply_snapshot,
    delete_snapshot,
    list_snapshots,
    load_snapshot,
    save_snapshot,
)
from .decision import resolve_trade_filters
from .logging_utils import recent_logs
from .live_summary import build_live_summary
from .manual_trade import _validate_geometry, parse_manual_trade
from .manual_trade_image import llm_configured as manual_trade_image_llm_configured
from .manual_trade_image import parse_trade_image
from .strategy_modes import canonical_strategy
from .telegram_signals import TelegramSignalsBot
from .timeframes import SUPPORTED_TIMEFRAMES, timeframe_options_payload, validate_timeframe

STATIC_DIR = Path(__file__).resolve().parent / "static"


class SymbolSettings(BaseModel):
    lots: dict[str, float] = Field(default_factory=dict)
    enabled: dict[str, bool] = Field(default_factory=dict)
    timeframes: dict[str, str] = Field(default_factory=dict)
    demo_symbols: dict[str, str] = Field(default_factory=dict)
    live_symbols: dict[str, str] = Field(default_factory=dict)
    default_forex_lot: float | None = Field(default=None, gt=0)
    append_broker_symbol_suffix: bool | None = None
    persist: bool = True


class LotUpdates(BaseModel):
    lots: dict[str, float] = Field(min_length=1)
    persist: bool = True


class ManualTradeRequest(BaseModel):
    text: str = Field(min_length=1)
    confirm_live: bool = False


class TelegramSignalsStartRequest(BaseModel):
    protect_tp: bool = False


class TelegramHardCopyRequest(BaseModel):
    message_id: str = Field(min_length=8)


class TelegramChannelUpsertRequest(BaseModel):
    url: str = Field(min_length=3)
    name: str | None = None
    enabled: bool = True
    persist: bool = True


class TelegramChannelUpdateRequest(BaseModel):
    url: str = Field(min_length=3)
    name: str | None = None
    enabled: bool | None = None
    persist: bool = True


class TelegramChannelRemoveRequest(BaseModel):
    url: str = Field(min_length=3)
    persist: bool = True


class TelegramSettingsRequest(BaseModel):
    ignore_open_symbol_trades: bool | None = None
    persist: bool = True


class BotSettingsRequest(BaseModel):
    strategy: StrategyMode | None = None
    signal_algorithm: str | None = None
    use_daily_loss_guard: bool | None = None
    max_daily_loss_pct: float | None = Field(default=None, ge=0)
    persist: bool = True


class AutoRunStartRequest(BaseModel):
    lots: dict[str, float] = Field(default_factory=dict)
    enabled: dict[str, bool] = Field(default_factory=dict)
    timeframes: dict[str, str] = Field(default_factory=dict)
    persist: bool = True
    strategy: StrategyMode | None = None
    strategy_persist: bool = True
    signal_algorithm: str | None = None


class RunOnceRequest(BaseModel):
    lots: dict[str, float] = Field(default_factory=dict)
    enabled: dict[str, bool] = Field(default_factory=dict)
    timeframes: dict[str, str] = Field(default_factory=dict)
    persist: bool = True
    strategy: StrategyMode | None = None
    strategy_persist: bool = False


class SnapshotSaveRequest(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    note: str = ""


class SnapshotApplyRequest(BaseModel):
    persist: bool = True


class TimeframeOptimizeRequest(BaseModel):
    start: datetime | None = None
    end: datetime | None = None
    starting_balance: float = Field(default=1000.0, gt=0)
    timeframes: list[str] = Field(default_factory=list)
    persist: bool = True


class Mt5TestTradeRequest(BaseModel):
    symbol: str = Field(default="XAUUSD", min_length=1)
    side: str = Field(default="buy", min_length=1)
    volume: float = Field(default=0.01, gt=0)
    confirm_live: bool = False

    @field_validator("confirm_live", mode="before")
    @classmethod
    def coerce_confirm_live(cls, value: object) -> bool:
        if value is None:
            return False
        return bool(value)


def create_app(
    config: AppConfig,
    bot: SignalBot,
    config_path: Path,
) -> FastAPI:
    app = FastAPI(title="RSI Divergence MT5 Bot")
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
    telegram_bot = TelegramSignalsBot(
        config,
        bot.client,
        bot.state,
        bot.logger,
        bot.daily_risk_status,
        config_path=config_path,
    )

    def telegram_channels_payload() -> list[dict]:
        return [channel.model_dump(mode="python") for channel in config.telegram_signals.channels]

    def ensure_telegram_stopped_for_channel_edit() -> None:
        if telegram_bot.is_running():
            raise HTTPException(
                status_code=409,
                detail="Stop the Telegram copier before adding, removing, or editing channels.",
            )

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
                "demo_symbol": item.demo_symbol,
                "live_symbol": item.live_symbol,
                "asset_group": symbol_asset_group(item),
                "enabled": item.enabled,
                "timeframe": item.timeframe,
                "optimized_timeframe": item.optimized_timeframe,
                "reset_timeframe": item.optimized_timeframe or item.timeframe,
                "lot_per_leg": item.lot_per_leg,
                "reset_lot_per_leg": default_symbol_lot(item, config),
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

    def apply_symbol_settings(
        lots: dict[str, float],
        enabled: dict[str, bool],
        timeframes: dict[str, str],
        demo_symbols: dict[str, str],
        live_symbols: dict[str, str],
        persist: bool,
    ) -> list[dict]:
        try:
            updated_lots = update_symbol_lots(config, lots)
            updated_enabled = update_symbol_enabled(config, enabled)
            updated_timeframes = update_symbol_timeframes(config, timeframes)
            updated_demo = update_symbol_trade_names(config, demo_symbols, live_symbols)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

        unknown_lots = sorted(set(lots) - set(updated_lots))
        if unknown_lots:
            raise HTTPException(status_code=400, detail=f"Unknown symbols in lots: {', '.join(unknown_lots)}")

        unknown_enabled = sorted(set(enabled) - set(updated_enabled))
        if unknown_enabled:
            raise HTTPException(status_code=400, detail=f"Unknown symbols in enabled: {', '.join(unknown_enabled)}")

        unknown_timeframes = sorted(set(timeframes) - set(updated_timeframes))
        if unknown_timeframes:
            raise HTTPException(status_code=400, detail=f"Unknown symbols in timeframes: {', '.join(unknown_timeframes)}")

        unknown_demo = sorted(set(demo_symbols) - set(updated_demo))
        if unknown_demo:
            raise HTTPException(status_code=400, detail=f"Unknown symbols in demo_symbols: {', '.join(unknown_demo)}")

        unknown_live = sorted(set(live_symbols) - set(updated_demo))
        if unknown_live:
            raise HTTPException(status_code=400, detail=f"Unknown symbols in live_symbols: {', '.join(unknown_live)}")

        if persist:
            save_config(config_path, config)

        bot.logger.info(
            "SYMBOL SETTINGS persist=%s lots=%s enabled=%s timeframes=%s",
            persist,
            len(lots),
            len(enabled),
            len(timeframes),
        )
        return symbol_payload()

    def apply_signal_algorithm(algorithm: str, persist: bool) -> None:
        if bot.is_auto_loop_running() and algorithm != config.bot.signal_algorithm:
            raise HTTPException(
                status_code=409,
                detail="Stop auto run before changing the signal algorithm.",
            )
        update_signal_algorithm(config, algorithm)  # type: ignore[arg-type]
        if persist:
            save_config(config_path, config)
        bot.logger.info("BOT SIGNAL ALGORITHM algorithm=%s persist=%s", config.bot.signal_algorithm, persist)

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

    def apply_config_from_snapshot(slug: str, persist: bool) -> dict:
        try:
            snapshot = load_snapshot(config_path, slug)
        except FileNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

        next_strategy = canonical_strategy(snapshot.bot.strategy)
        if bot.is_auto_loop_running() and next_strategy != config.bot.strategy:
            raise HTTPException(
                status_code=409,
                detail="Stop auto run before applying a snapshot with a different strategy.",
            )

        apply_snapshot(config_path, slug=slug, target=config, persist=persist)
        bot.client.config = config.mt5
        telegram_bot.config = config
        bot.logger.info("CONFIG SNAPSHOT apply slug=%s persist=%s strategy=%s", slug, persist, config.bot.strategy)
        return {
            "status": "saved" if persist else "applied",
            "slug": slug,
            "strategy": config.bot.strategy,
            "dry_run": config.bot.dry_run,
            "symbol_stats": symbol_stats(),
        }

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

    @app.on_event("shutdown")
    async def shutdown_mt5() -> None:
        await asyncio.to_thread(bot.client.shutdown, force=True)

    @app.post("/api/mt5/test-trade")
    async def mt5_test_trade(body: Mt5TestTradeRequest) -> dict:
        if not config.bot.dry_run and not body.confirm_live:
            raise HTTPException(status_code=400, detail="Live confirmation is required.")
        side = body.side.lower()
        if side not in {"buy", "sell"}:
            raise HTTPException(status_code=400, detail="side must be buy or sell")
        symbol = body.symbol.strip().upper()
        volume = float(body.volume)
        trade_symbol = resolve_trade_symbol(
            symbol,
            config,
            is_demo=config.mt5.is_demo,
            append_suffix=config.mt5.append_broker_symbol_suffix,
        )
        bot.logger.warning(
            "MT5 TEST TRADE requested symbol=%s trade_symbol=%s side=%s volume=%s dry_run=%s",
            symbol,
            trade_symbol,
            side,
            volume,
            config.bot.dry_run,
        )
        try:
            await require_mt5_ready()
            result = await asyncio.to_thread(
                bot.executor.place_test_trade,
                trade_symbol,
                side,
                volume,
            )
        except HTTPException:
            raise
        except Exception as exc:  # noqa: BLE001
            bot.logger.exception("MT5 TEST TRADE failed: %s", exc)
            raise HTTPException(status_code=500, detail=str(exc)) from exc

        bot.logger.warning(
            "MT5 TEST TRADE done symbol=%s side=%s status=%s",
            trade_symbol,
            side,
            result.get("status"),
        )
        return {"status": result.get("status", "failed"), **result}

    @app.get("/")
    @app.get("/backtest")
    @app.get("/settings")
    @app.get("/manual-trade")
    @app.get("/live-summary")
    @app.get("/logs")
    @app.get("/telegram-signals")
    def index() -> FileResponse:
        return FileResponse(STATIC_DIR / "index.html")

    @app.get("/api/symbols")
    def api_symbols() -> dict:
        stats = symbol_stats()
        return {
            "symbols": symbol_payload(),
            "symbol_stats": stats,
            "default_forex_lot": config.risk.default_forex_lot,
            "timeframe_options": timeframe_options_payload(),
            "broker_symbol_suffix": broker_symbol_suffix(config),
            "append_broker_symbol_suffix": append_broker_symbol_suffix_enabled(config),
        }

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
                "signal_algorithm": config.bot.signal_algorithm,
                "silver_optimized": config.bot.silver_optimized.model_dump(mode="python"),
                "trade_decision_profile": config.bot.trade_decision_profile,
                "max_concurrent_setups": config.bot.max_concurrent_setups,
            },
            "risk": config.risk.model_dump(mode="python"),
            "mt5": {
                "broker_symbol_suffix": broker_symbol_suffix(config),
                "append_broker_symbol_suffix": append_broker_symbol_suffix_enabled(config),
            },
            "telegram_signals": {
                "enabled": config.telegram_signals.enabled,
                "poll_seconds": config.telegram_signals.poll_seconds,
                "telegram_url": config.telegram_signals.telegram_url,
                "channels": [channel.model_dump(mode="python") for channel in config.telegram_signals.channels],
                "openai_model": config.telegram_signals.openai_model,
                "openai_api_key_configured": bool(
                    config.telegram_signals.openai_api_key or os.getenv("OPENAI_API_KEY")
                ),
                "gemini_model": config.telegram_signals.gemini_model,
                "gemini_api_key_configured": bool(
                    config.telegram_signals.gemini_api_key or os.getenv("GEMINI_API_KEY")
                ),
                "llm_configured": bool(
                    (config.telegram_signals.openai_api_key or os.getenv("OPENAI_API_KEY"))
                    or (config.telegram_signals.gemini_api_key or os.getenv("GEMINI_API_KEY"))
                ),
                "ignore_open_symbol_trades": config.telegram_signals.ignore_open_symbol_trades,
                "max_tps": config.telegram_signals.max_tps,
                "default_lot": config.telegram_signals.default_lot,
                "max_message_age_seconds": config.telegram_signals.max_message_age_seconds,
            },
            "decision_filters": asdict(resolve_trade_filters(config)),
            "timeframe_options": timeframe_options_payload(),
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
        if body.default_forex_lot is not None:
            try:
                update_default_forex_lot(config, body.default_forex_lot)
            except ValueError as exc:
                raise HTTPException(status_code=400, detail=str(exc)) from exc
            if body.persist:
                save_config(config_path, config)

        if body.append_broker_symbol_suffix is not None:
            update_append_broker_symbol_suffix(config, body.append_broker_symbol_suffix)
            if body.persist:
                save_config(config_path, config)

        if (
            not body.lots
            and not body.enabled
            and not body.timeframes
            and not body.demo_symbols
            and not body.live_symbols
            and body.default_forex_lot is None
            and body.append_broker_symbol_suffix is None
        ):
            stats = symbol_stats()
            return {
                "status": "noop",
                "symbols": symbol_payload(),
                "symbol_stats": stats,
                "default_forex_lot": config.risk.default_forex_lot,
                "broker_symbol_suffix": broker_symbol_suffix(config),
                "append_broker_symbol_suffix": append_broker_symbol_suffix_enabled(config),
            }

        symbols = apply_symbol_settings(
            body.lots,
            body.enabled,
            body.timeframes,
            body.demo_symbols,
            body.live_symbols,
            body.persist,
        )
        stats = symbol_stats()
        return {
            "status": "saved" if body.persist else "applied",
            "symbols": symbols,
            "symbol_stats": stats,
            "default_forex_lot": config.risk.default_forex_lot,
            "broker_symbol_suffix": broker_symbol_suffix(config),
            "append_broker_symbol_suffix": append_broker_symbol_suffix_enabled(config),
        }

    @app.post("/api/symbols/lots")
    def update_lots(body: LotUpdates) -> dict:
        return update_settings(SymbolSettings(lots=body.lots, persist=body.persist))

    @app.post("/api/symbols/timeframes/reset")
    def reset_timeframes(body: SnapshotApplyRequest | None = None) -> dict:
        persist = True if body is None else body.persist
        updates = {
            item.symbol: (item.optimized_timeframe or item.timeframe)
            for item in config.symbols
        }
        symbols = apply_symbol_settings({}, {}, updates, {}, {}, persist)
        return {
            "status": "saved" if persist else "applied",
            "symbols": symbols,
            "symbol_stats": symbol_stats(),
        }

    @app.post("/api/symbols/timeframes/optimize")
    async def optimize_timeframes(body: TimeframeOptimizeRequest | None = None) -> dict:
        body = body or TimeframeOptimizeRequest()
        end = body.end or datetime.now(timezone.utc).replace(microsecond=0)
        start = body.start or (end - timedelta(days=30))
        candidates = body.timeframes or list(SUPPORTED_TIMEFRAMES)
        try:
            candidates = [validate_timeframe(item) for item in candidates]
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

        bot.logger.info(
            "TIMEFRAME OPTIMIZE START %s -> %s symbols=%s candidates=%s",
            start.isoformat(),
            end.isoformat(),
            len(config.enabled_symbols),
            len(candidates),
        )
        await require_mt5_ready()
        try:
            result = await asyncio.to_thread(
                optimize_symbol_timeframes,
                bot.client,
                config,
                start,
                end,
                body.starting_balance,
                candidates,
                bot.logger,
            )
        except Exception as exc:  # noqa: BLE001
            bot.logger.exception("TIMEFRAME OPTIMIZE failed: %s", exc)
            raise HTTPException(status_code=503, detail=f"Timeframe optimization failed: {exc}") from exc

        for row in result["symbols"]:
            symbol_cfg = next((item for item in config.symbols if item.symbol == row["symbol"]), None)
            if symbol_cfg is None:
                continue
            best_timeframe = validate_timeframe(row["best_timeframe"])
            symbol_cfg.timeframe = best_timeframe  # type: ignore[assignment]
            symbol_cfg.optimized_timeframe = best_timeframe  # type: ignore[assignment]

        if body.persist:
            save_config(config_path, config)

        bot.logger.info("TIMEFRAME OPTIMIZE DONE symbols=%s persist=%s", len(result["symbols"]), body.persist)
        return {
            "status": "saved" if body.persist else "applied",
            "optimization": result,
            "symbols": symbol_payload(),
            "symbol_stats": symbol_stats(),
        }

    @app.get("/api/logs")
    def logs() -> list[str]:
        return recent_logs(200)

    @app.post("/api/bot/settings")
    def update_bot_settings(body: BotSettingsRequest) -> dict:
        if body.strategy is not None:
            apply_bot_strategy(body.strategy, body.persist)
        if body.signal_algorithm is not None:
            apply_signal_algorithm(body.signal_algorithm, body.persist)
        if body.use_daily_loss_guard is not None:
            config.risk.use_daily_loss_guard = body.use_daily_loss_guard
        if body.max_daily_loss_pct is not None:
            config.risk.max_daily_loss_pct = body.max_daily_loss_pct
        if body.persist and (body.use_daily_loss_guard is not None or body.max_daily_loss_pct is not None):
            save_config(config_path, config)
        return {
            "status": "saved" if body.persist else "applied",
            "strategy": config.bot.strategy,
            "signal_algorithm": config.bot.signal_algorithm,
            "risk": config.risk.model_dump(mode="python"),
            "auto_run": bot.auto_loop_status(include_mt5=False),
        }

    @app.get("/api/daily-risk")
    async def api_daily_risk() -> dict:
        await require_mt5_ready()
        try:
            return await asyncio.to_thread(bot.daily_risk_status)
        except Exception as exc:  # noqa: BLE001
            raise HTTPException(status_code=500, detail=str(exc)) from exc

    @app.get("/api/config/snapshots")
    def api_config_snapshots() -> dict:
        return {"snapshots": list_snapshots(config_path)}

    @app.post("/api/config/snapshots")
    def api_save_config_snapshot(body: SnapshotSaveRequest) -> dict:
        try:
            entry = save_snapshot(
                config_path,
                name=body.name,
                config=config,
                note=body.note,
            )
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        bot.logger.info("CONFIG SNAPSHOT saved slug=%s name=%s", entry["slug"], entry["name"])
        return {"status": "saved", "snapshot": entry}

    @app.post("/api/config/snapshots/{slug}/apply")
    def api_apply_config_snapshot(slug: str, body: SnapshotApplyRequest) -> dict:
        result = apply_config_from_snapshot(slug, body.persist)
        return {
            **result,
            "symbols": symbol_payload(),
            "auto_run": bot.auto_loop_status(),
        }

    @app.delete("/api/config/snapshots/{slug}")
    def api_delete_config_snapshot(slug: str) -> dict:
        try:
            delete_snapshot(config_path, slug)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        bot.logger.info("CONFIG SNAPSHOT deleted slug=%s", slug)
        return {"status": "deleted", "slug": slug}

    @app.post("/api/run-once")
    async def run_once(body: RunOnceRequest | None = None) -> dict:
        if body is not None:
            if body.lots or body.enabled or body.timeframes:
                apply_symbol_settings(
                    body.lots,
                    body.enabled,
                    body.timeframes,
                    {},
                    {},
                    body.persist,
                )
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

    @app.post("/api/manual-trade/parse-image")
    async def parse_manual_trade_image(image: UploadFile = File(...)) -> dict:
        if not manual_trade_image_llm_configured(config):
            raise HTTPException(
                status_code=400,
                detail=(
                    "LLM API key missing. Set telegram_signals.openai_api_key or OPENAI_API_KEY "
                    "(primary), or telegram_signals.gemini_api_key or GEMINI_API_KEY (fallback)."
                ),
            )
        content = await image.read()
        mime = image.content_type or "image/png"
        try:
            result = await asyncio.to_thread(parse_trade_image, config, content, mime, bot.logger)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except RuntimeError as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc
        except Exception as exc:  # noqa: BLE001
            bot.logger.exception("MANUAL TRADE IMAGE parse failed: %s", exc)
            raise HTTPException(status_code=503, detail=f"Image parse failed: {exc}") from exc
        return {
            "status": "parsed",
            "text": result.text,
            "provider": result.provider,
            "parsed": result.parsed.model_dump(mode="python"),
            "llm_configured": True,
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
            is_demo = config.mt5.is_demo
            trade_symbol = resolve_trade_symbol(
                plan.symbol,
                config,
                is_demo=is_demo,
                append_suffix=config.mt5.append_broker_symbol_suffix,
            )
            tick = await asyncio.to_thread(bot.client.tick, trade_symbol)
            if tick is None:
                raise ValueError(f"No live tick for {trade_symbol}.")
            from .manual_trade import _field as manual_field

            entry = float(manual_field(tick, "ask") if plan.side == "buy" else manual_field(tick, "bid"))
            _validate_geometry(plan, entry)
            symbol_cfg = next((item for item in config.symbols if item.symbol == plan.symbol), None)
            setup_id = f"manual:{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"
            result = await asyncio.to_thread(
                bot.executor.place_market_setup,
                setup_id=setup_id,
                symbol=trade_symbol,
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
    def auto_run_status(include_mt5: bool = Query(False)) -> dict:
        status = bot.auto_loop_status(include_mt5=include_mt5)
        status.update(symbol_stats())
        return status

    @app.post("/api/auto-run/start")
    async def auto_run_start(body: AutoRunStartRequest | None = None) -> dict:
        if body is not None:
            if body.lots or body.enabled or body.timeframes:
                apply_symbol_settings(
                    body.lots,
                    body.enabled,
                    body.timeframes,
                    {},
                    {},
                    body.persist,
                )
            if body.strategy is not None:
                apply_bot_strategy(body.strategy, body.strategy_persist)
            if body.signal_algorithm is not None:
                apply_signal_algorithm(body.signal_algorithm, body.strategy_persist)
        await require_mt5_ready()
        status = bot.start_auto_loop()
        status.update(symbol_stats())
        status["signal_algorithm"] = config.bot.signal_algorithm
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

    @app.get("/api/live-summary")
    async def live_summary(
        start: datetime = Query(...),
        end: datetime = Query(...),
    ) -> dict:
        try:
            await require_mt5_ready()
            return await asyncio.to_thread(build_live_summary, bot.client, start, end)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except Exception as exc:  # noqa: BLE001
            bot.logger.exception("LIVE SUMMARY failed: %s", exc)
            raise HTTPException(status_code=503, detail=f"Live summary failed: {exc}") from exc

    @app.get("/api/telegram-signals/status")
    def telegram_signals_status() -> dict:
        return telegram_bot.status()

    @app.post("/api/telegram-signals/start")
    async def telegram_signals_start(body: TelegramSignalsStartRequest) -> dict:
        if not telegram_bot.status().get("llm_configured"):
            raise HTTPException(
                status_code=400,
                detail=(
                    "LLM API key missing. Set telegram_signals.openai_api_key or OPENAI_API_KEY "
                    "(primary), or telegram_signals.gemini_api_key or GEMINI_API_KEY (fallback)."
                ),
            )
        await require_mt5_ready()
        result = telegram_bot.start(protect_tp=body.protect_tp)
        start_error = result.get("start_error")
        if start_error:
            raise HTTPException(status_code=503, detail=start_error)
        return result

    @app.post("/api/telegram-signals/stop")
    def telegram_signals_stop() -> dict:
        return telegram_bot.stop()

    @app.patch("/api/telegram-signals/settings")
    def telegram_signals_settings(body: TelegramSettingsRequest) -> dict:
        if body.ignore_open_symbol_trades is not None:
            update_telegram_ignore_open_trades(config, ignore_open=body.ignore_open_symbol_trades)
            if body.persist:
                save_config(config_path, config)
            bot.logger.info(
                "TELEGRAM SETTINGS ignore_open_symbol_trades=%s persist=%s",
                config.telegram_signals.ignore_open_symbol_trades,
                body.persist,
            )
        return {
            "status": "saved" if body.persist else "applied",
            **telegram_bot.status(),
        }

    @app.post("/api/telegram-signals/clear-messages")
    def telegram_signals_clear_messages() -> dict:
        return telegram_bot.clear_message_history()

    @app.post("/api/telegram-signals/hard-copy")
    async def telegram_signals_hard_copy(body: TelegramHardCopyRequest) -> dict:
        await require_mt5_ready()
        result = telegram_bot.hard_copy_message(body.message_id)
        if result.get("status") == "error":
            raise HTTPException(status_code=400, detail=str(result.get("reason") or "hard copy failed"))
        return {**result, **telegram_bot.status()}

    @app.get("/api/telegram-signals/channels")
    def telegram_signals_channels() -> dict:
        return {"channels": telegram_channels_payload()}

    @app.post("/api/telegram-signals/channels")
    def telegram_signals_add_channel(body: TelegramChannelUpsertRequest) -> dict:
        ensure_telegram_stopped_for_channel_edit()
        try:
            channel = add_telegram_channel(
                config,
                body.url,
                name=body.name,
                enabled=body.enabled,
            )
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        if body.persist:
            save_config(config_path, config)
        bot.logger.info("TELEGRAM CHANNEL add name=%s url=%s enabled=%s", channel.name, channel.url, channel.enabled)
        return {"status": "added", "channel": channel.model_dump(mode="python"), "channels": telegram_channels_payload()}

    @app.patch("/api/telegram-signals/channels")
    def telegram_signals_update_channel(body: TelegramChannelUpdateRequest) -> dict:
        try:
            channel = update_telegram_channel(
                config,
                body.url,
                name=body.name,
                enabled=body.enabled,
            )
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        if body.persist:
            save_config(config_path, config)
        bot.logger.info(
            "TELEGRAM CHANNEL update name=%s url=%s enabled=%s",
            channel.name,
            channel.url,
            channel.enabled,
        )
        return {"status": "updated", "channel": channel.model_dump(mode="python"), "channels": telegram_channels_payload()}

    @app.post("/api/telegram-signals/channels/remove")
    def telegram_signals_remove_channel(body: TelegramChannelRemoveRequest) -> dict:
        ensure_telegram_stopped_for_channel_edit()
        try:
            removed = remove_telegram_channel(config, body.url)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        if body.persist:
            save_config(config_path, config)
        bot.logger.info("TELEGRAM CHANNEL remove name=%s url=%s", removed.name, removed.url)
        return {"status": "removed", "channel": removed.model_dump(mode="python"), "channels": telegram_channels_payload()}

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
        signal_algorithm: str | None = Query(None),
    ) -> dict:
        run_config = config
        if signal_algorithm:
            run_config = config.model_copy(deep=True)
            update_signal_algorithm(run_config, signal_algorithm)  # type: ignore[arg-type]
        bot.logger.info(
            "BACKTEST START %s -> %s strategy=%s signal_algorithm=%s",
            start.isoformat(),
            end.isoformat(),
            run_config.bot.strategy,
            run_config.bot.signal_algorithm,
        )
        try:
            await require_mt5_ready()
            result = await asyncio.to_thread(
                run_backtest,
                bot.client,
                run_config,
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
