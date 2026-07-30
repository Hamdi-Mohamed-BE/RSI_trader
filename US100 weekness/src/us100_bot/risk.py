from __future__ import annotations

from .config import Config
from .normalization import PriceNormalizer


def position_volume(
    cfg: Config,
    norm: PriceNormalizer,
    equity: float,
    stop_pips: float,
    risk_fraction: float = 1.0,
) -> tuple[float, float]:
    if cfg.risk_mode.lower() == "fixed":
        volume = norm.round_volume(cfg.fixed_lot)
    else:
        desired = min(
            equity * cfg.risk_percent / 100.0 * risk_fraction,
            cfg.max_risk_cash * risk_fraction,
        )
        volume = norm.round_volume(desired / norm.risk_per_lot(stop_pips))
    actual = norm.risk_per_lot(stop_pips) * volume
    return volume, actual

