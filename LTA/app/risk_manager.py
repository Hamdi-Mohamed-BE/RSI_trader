from __future__ import annotations

from dataclasses import dataclass
from datetime import date


DEFAULT_CONTRACT_SIZES = {
    "XAUUSD": 100.0,
    "XAGUSD": 5000.0,
    "BTCUSD": 1.0,
    "EURUSD": 100000.0,
    "USDJPY": 100000.0,
    "GBPUSD": 100000.0,
    "USDCAD": 100000.0,
    "USDAUD": 100000.0,
}


@dataclass
class RiskDecision:
    approved: bool
    reasons: list[str]
    risk_amount: float


class RiskManager:
    def __init__(
        self,
        symbol: str,
        lot_size: float,
        starting_balance: float,
        max_risk_percent: float,
        max_daily_loss_percent: float,
        max_drawdown_percent: float,
        max_trades_per_day: int,
        min_setup_score: int,
        min_risk_reward: float,
        contract_size: float | None = None,
    ) -> None:
        self.symbol = symbol
        self.lot_size = lot_size
        self.starting_balance = starting_balance
        self.max_risk_percent = max_risk_percent
        self.max_daily_loss_percent = max_daily_loss_percent
        self.max_drawdown_percent = max_drawdown_percent
        self.max_trades_per_day = max_trades_per_day
        self.min_setup_score = min_setup_score
        self.min_risk_reward = min_risk_reward
        self.contract_size = contract_size or DEFAULT_CONTRACT_SIZES.get(symbol, 1.0)

    def trade_risk_amount(self, entry: float, stop_loss: float) -> float:
        return abs(entry - stop_loss) * self.contract_size * self.lot_size

    def pnl(self, direction: str, entry: float, exit_price: float) -> float:
        if direction == "BUY":
            return (exit_price - entry) * self.contract_size * self.lot_size
        return (entry - exit_price) * self.contract_size * self.lot_size

    def approve(
        self,
        signal: dict,
        balance: float,
        equity_peak: float,
        daily_pnl: float,
        trades_today: int,
    ) -> RiskDecision:
        reasons: list[str] = []
        if signal.get("setup_score", 0) < self.min_setup_score:
            reasons.append("Setup score is below the A+ threshold.")
        if signal.get("risk_reward") is None or signal["risk_reward"] < self.min_risk_reward:
            reasons.append("Risk-to-reward is below the minimum.")
        if signal.get("entry") is None or signal.get("stop_loss") is None or signal.get("take_profit") is None:
            reasons.append("Entry, stop loss, or take profit is missing.")

        risk_amount = 0.0
        if not reasons:
            risk_amount = self.trade_risk_amount(float(signal["entry"]), float(signal["stop_loss"]))
            max_risk_amount = balance * (self.max_risk_percent / 100)
            if risk_amount <= 0:
                reasons.append("Trade risk is zero or invalid.")
            if risk_amount > max_risk_amount:
                reasons.append("Lot size risks more than the allowed percent.")

        daily_loss_limit = self.starting_balance * (self.max_daily_loss_percent / 100)
        if daily_pnl <= -daily_loss_limit:
            reasons.append("Daily loss limit has already been reached.")

        drawdown = 0.0 if equity_peak <= 0 else (equity_peak - balance) / equity_peak * 100
        if drawdown >= self.max_drawdown_percent:
            reasons.append("Maximum drawdown limit has already been reached.")

        if trades_today >= self.max_trades_per_day:
            reasons.append("Maximum trades per day has already been reached.")

        return RiskDecision(approved=not reasons, reasons=reasons, risk_amount=risk_amount)

    @staticmethod
    def day_key(timestamp) -> date:
        return timestamp.date()
