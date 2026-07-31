from __future__ import annotations

from decimal import Decimal, ROUND_DOWN


def risk_cash(balance: float, risk_pct: float) -> float:
    return max(balance, 0.0) * risk_pct / 100.0


def round_volume(raw: float, minimum: float, maximum: float, step: float) -> float:
    value = max(minimum, min(maximum, raw))
    steps = (Decimal(str(value)) / Decimal(str(step))).quantize(
        Decimal("1"), rounding=ROUND_DOWN
    )
    return float(steps * Decimal(str(step)))


def cash_result(balance: float, risk_pct: float, result_r: float) -> tuple[float, float]:
    at_risk = risk_cash(balance, risk_pct)
    pnl = at_risk * result_r
    return pnl, balance + pnl

