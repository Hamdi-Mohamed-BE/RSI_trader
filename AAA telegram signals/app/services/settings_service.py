from sqlmodel import Session
from typing import Any, Dict
from app.core.config import settings
from app.db.repositories import SettingsRepository

class SettingsService:
    @staticmethod
    def get(session: Session, key: str) -> Any:
        """Retrieves a setting from the database, falling back to config.py settings."""
        # Convert key to uppercase to match settings attributes
        attr_name = key.upper()
        default_val = getattr(settings, attr_name, None)
        
        # Check database
        db_val = SettingsRepository.get(session, key, default=None)
        if db_val is not None:
            return db_val
            
        return default_val

    @staticmethod
    def set(session: Session, key: str, value: Any):
        """Saves a setting to the database."""
        return SettingsRepository.set(session, key, value)

    @staticmethod
    def get_all(session: Session) -> Dict[str, Any]:
        """Returns all copier settings as a key-value dictionary."""
        # List of all settings we care about
        keys = [
            "copier_enabled",
            "poll_interval_seconds",
            "telegram_mode",
            "telegram_api_id",
            "telegram_api_hash",
            "telegram_bot_token",
            "telegram_chat_link",
            "telegram_read_mode",
            "telegram_browser_headless",
            "allow_reply_signals",
            "gemini_api_key",
            "gemini_model",
            "min_llm_confidence",
            "risk_mode",
            "fixed_lot",
            "symbol_lots",
            "risk_percent",
            "risk_usd_cap",
            "use_equity_instead_of_balance",
            "allow_min_lot_if_risk_too_small",
            "max_lot",
            "move_to_break_even_enabled",
            "break_even_offset_points",
            "allow_no_sl",
            "max_spread_points",
            "max_trades_per_day",
            "stale_signal_max_age_minutes",
            "stale_signal_max_entry_distance_points",
        ]
        
        result = {}
        for key in keys:
            result[key] = SettingsService.get(session, key)
            
        return result
