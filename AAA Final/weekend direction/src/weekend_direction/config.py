from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path

from dotenv import load_dotenv


ROOT = Path(__file__).resolve().parents[2]


def _flag(name: str, default: bool = False) -> bool:
    return os.getenv(name, str(default)).strip().lower() in {"1", "true", "yes", "on"}


def _path(value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else (ROOT / path).resolve()


@dataclass(frozen=True)
class Config:
    ai_news_root: Path
    model_path: Path
    model_metadata_path: Path
    allow_provisional: bool
    momentum_quantile: float
    lead_minutes: int
    stop_usd: float
    reward_risk: float
    history_weeks: int
    sizing_mode: str
    fixed_lot: float
    risk_pct: float
    max_spread_usd: float
    max_slippage_usd: float
    max_daily_loss_pct: float
    max_daily_trades: int
    max_open_risk_pct: float
    min_margin_level_pct: float
    magic: int
    poll_seconds: float
    live_trading: bool
    place_orders: bool
    dry_run: bool

    @property
    def execution_enabled(self) -> bool:
        return self.live_trading and self.place_orders and not self.dry_run

    @classmethod
    def load(cls) -> "Config":
        load_dotenv(ROOT / ".env", override=False)
        return cls(
            ai_news_root=_path(os.getenv("AI_NEWS_ROOT", r"..\..\AI news")),
            model_path=_path(os.getenv("MODEL_PATH", r"..\..\AI news\models\gold_weekend_direction_v2.joblib")),
            model_metadata_path=_path(os.getenv("MODEL_METADATA_PATH", r"..\..\AI news\models\gold_weekend_direction.metadata.json")),
            allow_provisional=_flag("ALLOW_PROVISIONAL_MOMENTUM_MODE"),
            momentum_quantile=float(os.getenv("MOMENTUM_QUANTILE", "0.70")),
            lead_minutes=int(os.getenv("LEAD_MINUTES", "4")),
            stop_usd=float(os.getenv("STOP_USD", "30")),
            reward_risk=float(os.getenv("REWARD_RISK", "3")),
            history_weeks=int(os.getenv("HISTORY_WEEKS", "156")),
            sizing_mode=os.getenv("SIZING_MODE", "risk_pct").strip().lower(),
            fixed_lot=float(os.getenv("FIXED_LOT", "0.01")),
            risk_pct=float(os.getenv("RISK_PCT", "1")),
            max_spread_usd=float(os.getenv("MAX_SPREAD_USD", "5")),
            max_slippage_usd=float(os.getenv("MAX_SLIPPAGE_USD", "3")),
            max_daily_loss_pct=float(os.getenv("MAX_DAILY_LOSS_PCT", "2")),
            max_daily_trades=int(os.getenv("MAX_DAILY_TRADES", "1")),
            max_open_risk_pct=float(os.getenv("MAX_OPEN_RISK_PCT", "1")),
            min_margin_level_pct=float(os.getenv("MIN_MARGIN_LEVEL_PCT", "200")),
            magic=int(os.getenv("MAGIC", "860302")),
            poll_seconds=float(os.getenv("POLL_SECONDS", "5")),
            live_trading=_flag("LIVE_TRADING"),
            place_orders=_flag("PLACE_ORDERS"),
            dry_run=_flag("DRY_RUN", True),
        )
