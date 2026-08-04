from __future__ import annotations

import pandas as pd

from xau_grid.config import StrategyConfig
from xau_grid.engine import build_plan, planned_loss
from xau_grid.mt5_data import SymbolSpec


SPEC = SymbolSpec("XAUUSD", 0.01, 0.01, 1.0, 100.0, 0.01, 0.01, 100.0, 2)


def test_grid_risk_is_capped_and_equal_sized() -> None:
    config = StrategyConfig(risk_pct=1.0, grid_levels=3, grid_step_atr=0.75, stop_extra_atr=1.2)
    plan = build_plan(pd.Timestamp("2026-01-01", tz="UTC"), 2400.0, 1, 10.0, 25_000.0, config, SPEC)
    assert plan is not None
    assert plan.lot_each >= SPEC.volume_min
    assert planned_loss(plan, SPEC) <= 250.0 + 1e-8
    assert len(set([plan.lot_each for _ in plan.entries])) == 1


def test_minimum_lot_is_rejected_when_it_breaks_risk_cap() -> None:
    config = StrategyConfig(risk_pct=0.1, grid_levels=5, grid_step_atr=1.0, stop_extra_atr=2.0)
    plan = build_plan(pd.Timestamp("2026-01-01", tz="UTC"), 2400.0, 1, 100.0, 100.0, config, SPEC)
    assert plan is None


def test_config_rejects_martingale_sized_grid_depth() -> None:
    try:
        StrategyConfig(grid_levels=6).validate()
    except ValueError as exc:
        assert "GRID_LEVELS" in str(exc)
    else:
        raise AssertionError("unsafe grid depth was accepted")
