import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from sqlmodel import Session

from app.core.config import settings
from app.core.logging import logger
from app.db.database import init_db, engine
from app.services.copier_service import copier_service
from app.services.settings_service import SettingsService
from app.trading.mt5_client import mt5_client
from app.web.routes import router as web_router
from app.api.routes import router as api_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup actions
    logger.info("Initializing database...")
    init_db()
    
    # Check copier enabled setting from DB, default to config
    with Session(engine) as session:
        # Load or initialize default settings if DB is empty
        # We can seed settings from settings config
        db_copier_enabled = SettingsService.get(session, "copier_enabled")
        if db_copier_enabled is None:
            # Seed the DB with default values from config settings
            SettingsService.set(session, "copier_enabled", settings.COPIER_ENABLED)
            SettingsService.set(session, "poll_interval_seconds", settings.POLL_INTERVAL_SECONDS)
            SettingsService.set(session, "telegram_mode", settings.TELEGRAM_MODE)
            SettingsService.set(session, "telegram_api_id", settings.TELEGRAM_API_ID)
            SettingsService.set(session, "telegram_api_hash", settings.TELEGRAM_API_HASH)
            SettingsService.set(session, "telegram_bot_token", settings.TELEGRAM_BOT_TOKEN)
            SettingsService.set(session, "telegram_chat_link", settings.TELEGRAM_CHAT_LINK)
            SettingsService.set(session, "telegram_read_mode", settings.TELEGRAM_READ_MODE)
            SettingsService.set(session, "telegram_browser_headless", settings.TELEGRAM_BROWSER_HEADLESS)
            SettingsService.set(session, "allow_reply_signals", settings.ALLOW_REPLY_SIGNALS)
            SettingsService.set(session, "gemini_api_key", settings.GEMINI_API_KEY)
            SettingsService.set(session, "gemini_model", settings.GEMINI_MODEL)
            SettingsService.set(session, "min_llm_confidence", settings.MIN_LLM_CONFIDENCE)
            SettingsService.set(session, "risk_mode", settings.RISK_MODE)
            SettingsService.set(session, "fixed_lot", settings.FIXED_LOT)
            SettingsService.set(session, "symbol_lots", settings.SYMBOL_LOTS)
            SettingsService.set(session, "risk_percent", settings.RISK_PERCENT)
            SettingsService.set(session, "risk_usd_cap", settings.RISK_USD_CAP)
            SettingsService.set(session, "use_equity_instead_of_balance", settings.USE_EQUITY_INSTEAD_OF_BALANCE)
            SettingsService.set(session, "allow_min_lot_if_risk_too_small", settings.ALLOW_MIN_LOT_IF_RISK_TOO_SMALL)
            SettingsService.set(session, "move_to_break_even_enabled", settings.MOVE_TO_BREAK_EVEN_ENABLED)
            SettingsService.set(session, "break_even_offset_points", settings.BREAK_EVEN_OFFSET_POINTS)
            SettingsService.set(session, "allow_no_sl", settings.ALLOW_NO_SL)
            SettingsService.set(session, "max_trades_per_day", settings.MAX_TRADES_PER_DAY)
            SettingsService.set(session, "daily_win_goal_usd", settings.DAILY_WIN_GOAL_USD)
            SettingsService.set(session, "daily_loss_limit_usd", settings.DAILY_LOSS_LIMIT_USD)
            SettingsService.set(session, "stale_signal_max_age_minutes", settings.STALE_SIGNAL_MAX_AGE_MINUTES)
            SettingsService.set(session, "stale_signal_max_entry_distance_points", settings.STALE_SIGNAL_MAX_ENTRY_DISTANCE_POINTS)
            
            db_copier_enabled = settings.COPIER_ENABLED
            
    # Connect MT5 terminal
    mt5_client.connect()
    
    # Start the orchestrator background loop
    copier_service.start()
    
    yield
    
    # Shutdown actions
    logger.info("Stopping copier service background tasks...")
    await copier_service.stop()
    
    # Disconnect MT5 terminal
    mt5_client.disconnect()
    logger.info("Application shutdown complete.")

app = FastAPI(
    title="Telegram MT5 Copier",
    description="Sleek copier routing signal channel notifications to MetaTrader 5 on Windows",
    lifespan=lifespan
)

# Ensure static directories exist
os.makedirs("app/static/css", exist_ok=True)
os.makedirs("app/static/js", exist_ok=True)
os.makedirs("app/static/telegram_media", exist_ok=True)

# Mount static folder
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# Include Routers
app.include_router(web_router)
app.include_router(api_router)
