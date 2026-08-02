from __future__ import annotations


def progressed_risk_pct(
    base_risk_pct: float,
    loss_streak: int,
    multiplier: float = 1.6,
    max_risk_pct: float | None = None,
) -> float:
    """Return risk for the next trade after ``loss_streak`` closed losses.

    Research can pass ``None`` for the exact uncapped rule. Live callers must
    pass a finite safety cap.
    """
    if base_risk_pct <= 0:
        raise ValueError("base_risk_pct must be positive")
    if loss_streak < 0:
        raise ValueError("loss_streak cannot be negative")
    if multiplier < 1.0:
        raise ValueError("multiplier must be at least 1")
    risk = base_risk_pct * multiplier**loss_streak
    if max_risk_pct is not None:
        if max_risk_pct <= 0:
            raise ValueError("max_risk_pct must be positive when set")
        risk = min(risk, max_risk_pct)
    return float(risk)


def next_loss_streak(current: int, pnl_r: float) -> int:
    """Update a closed-trade streak: loss increments, win resets, BE holds."""
    if pnl_r < -1e-9:
        return current + 1
    if pnl_r > 1e-9:
        return 0
    return current
