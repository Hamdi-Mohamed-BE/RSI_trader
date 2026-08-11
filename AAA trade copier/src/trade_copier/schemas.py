from decimal import Decimal
from pathlib import Path

from pydantic import BaseModel, Field, field_validator, model_validator

from .domain.enums import AccountRole, AccountState, OrderType, RiskMode, Side


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


class CopyTestInput(BaseModel):
    symbol: str = Field(min_length=2, max_length=32)
    side: Side
    order_type: OrderType = OrderType.MARKET
    master_volume: Decimal = Field(gt=0, le=Decimal("1000"))
    market_price: Decimal | None = Field(default=None, gt=0)
    entry_price: Decimal = Field(gt=0)
    stop_loss: Decimal = Field(gt=0)
    take_profit: Decimal | None = Field(default=None, gt=0)

    @field_validator("symbol")
    @classmethod
    def normalize_symbol(cls, value: str) -> str:
        return value.strip().upper()

    @model_validator(mode="after")
    def validate_prices(self) -> "CopyTestInput":
        if self.side is Side.BUY and self.stop_loss >= self.entry_price:
            raise ValueError("A buy stop loss must be below entry.")
        if self.side is Side.SELL and self.stop_loss <= self.entry_price:
            raise ValueError("A sell stop loss must be above entry.")
        if self.take_profit is not None:
            if self.side is Side.BUY and self.take_profit <= self.entry_price:
                raise ValueError("A buy take profit must be above entry.")
            if self.side is Side.SELL and self.take_profit >= self.entry_price:
                raise ValueError("A sell take profit must be below entry.")

        if self.order_type is OrderType.MARKET:
            return self
        if self.market_price is None:
            raise ValueError("Reference market price is required for limit and stop orders.")

        if self.order_type is OrderType.LIMIT:
            if self.side is Side.BUY and self.entry_price >= self.market_price:
                raise ValueError("A buy limit entry must be below the market price.")
            if self.side is Side.SELL and self.entry_price <= self.market_price:
                raise ValueError("A sell limit entry must be above the market price.")
        if self.order_type is OrderType.STOP:
            if self.side is Side.BUY and self.entry_price <= self.market_price:
                raise ValueError("A buy stop entry must be above the market price.")
            if self.side is Side.SELL and self.entry_price >= self.market_price:
                raise ValueError("A sell stop entry must be below the market price.")
        return self


class AdminCreate(BaseModel):
    email: str = Field(min_length=3, max_length=254)
    password: str = Field(min_length=12, max_length=256)
    display_name: str = Field(default="Administrator", min_length=2, max_length=120)
