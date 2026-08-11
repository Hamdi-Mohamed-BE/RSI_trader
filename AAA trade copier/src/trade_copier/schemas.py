from decimal import Decimal
from pathlib import Path

from pydantic import BaseModel, Field, field_validator

from .domain.enums import AccountRole, AccountState, RiskMode


class LoginInput(BaseModel):
    email: str = Field(min_length=3, max_length=254)
    password: str = Field(min_length=1, max_length=256)


class AccountCreate(BaseModel):
    display_name: str = Field(min_length=2, max_length=120)
    login: str = Field(min_length=3, max_length=32)
    broker_server: str = Field(min_length=2, max_length=160)
    terminal_path: str = Field(default="", max_length=500)
    role: AccountRole = AccountRole.FOLLOWER
    state: AccountState = AccountState.DISABLED
    trade_mode: str = Field(default="demo", max_length=32)
    position_mode: str = Field(default="hedging", max_length=32)
    risk_profile_id: str | None = None
    password: str = Field(default="", max_length=256)

    @field_validator("terminal_path")
    @classmethod
    def validate_terminal_path(cls, value: str) -> str:
        if not value:
            return value
        path = Path(value)
        if path.suffix.lower() != ".exe":
            raise ValueError("Terminal path must point to terminal64.exe.")
        return str(path)


class AccountUpdate(BaseModel):
    display_name: str = Field(min_length=2, max_length=120)
    broker_server: str = Field(min_length=2, max_length=160)
    terminal_path: str = Field(default="", max_length=500)
    role: AccountRole
    state: AccountState
    trade_mode: str = Field(max_length=32)
    position_mode: str = Field(max_length=32)
    risk_profile_id: str | None = None

    @field_validator("terminal_path")
    @classmethod
    def validate_terminal_path(cls, value: str) -> str:
        return AccountCreate.validate_terminal_path(value)


class RiskProfileCreate(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    mode: RiskMode = RiskMode.STOP_PERCENT
    risk_percent: Decimal = Field(default=Decimal("1.0"), gt=0, le=Decimal("10"))
    fixed_cash_risk: Decimal | None = Field(default=None, gt=0)
    fixed_lots: Decimal | None = Field(default=None, gt=0)
    max_total_open_risk_percent: Decimal = Field(default=Decimal("5.0"), gt=0, le=Decimal("50"))
    max_daily_loss_percent: Decimal = Field(default=Decimal("3.0"), gt=0, le=Decimal("50"))
    max_spread_points: int = Field(default=50, ge=0, le=10000)
    max_slippage_points: int = Field(default=30, ge=0, le=10000)
    max_open_positions: int = Field(default=10, ge=1, le=1000)
    reject_without_stop: bool = True


class SymbolMappingCreate(BaseModel):
    follower_account_id: str
    master_symbol: str = Field(min_length=2, max_length=32)
    follower_symbol: str = Field(min_length=2, max_length=32)
    price_offset: Decimal = Decimal("0")
    preserve_relative_stops: bool = True


class AdminCreate(BaseModel):
    email: str = Field(min_length=3, max_length=254)
    password: str = Field(min_length=12, max_length=256)
    display_name: str = Field(default="Administrator", min_length=2, max_length=120)
