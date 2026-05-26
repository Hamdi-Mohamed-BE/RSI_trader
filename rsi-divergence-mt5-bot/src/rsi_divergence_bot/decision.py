from __future__ import annotations

from dataclasses import dataclass

from .config import AppConfig, SymbolConfig
from .daily_risk import daily_loss_setup_risk_cap
from .mt5_client import MT5Client
from .strategy import Signal
from .strategy_modes import is_full_position_strategy, is_single_leg_strategy
from .trade_geometry import invalid_market_geometry


@dataclass(frozen=True)
class TradeDecision:
    allowed: bool
    code: str
    reason: str
    risk_usd: float
    spread: float
    spread_atr: float
    tp1_distance: float
    min_tp1_distance: float


@dataclass(frozen=True)
class TradeFilterSettings:
    spread: bool
    tp1_spread: bool
    risk: bool
    existing_position: bool
    max_setups: bool
    min_tp1_spread_multiple: float


def skip_should_mark_seen(code: str) -> bool:
    """Live bot retries max_setups blocks on the next poll; everything else is marked seen."""
    return code not in {"max_setups"}


def historical_spread_price(row, point: float) -> float:
    try:
        spread_points = float(row.get("spread", 0.0))
    except AttributeError:
        spread_points = float(getattr(row, "spread", 0.0) or 0.0)
    if spread_points <= 0 or point <= 0:
        return 0.0
    return spread_points * point


def signal_risk_usd(client: MT5Client, signal: Signal, *, strategy: str | None = None) -> float:
    leg_risk = client.money_for_distance(signal.symbol, signal.lot_per_leg, signal.risk_distance)
    if strategy and (is_full_position_strategy(strategy) or is_single_leg_strategy(strategy)):
        return leg_risk
    return leg_risk * len(signal.tps)


def profile_uses_entry_filters(profile: str) -> bool:
    return profile in {"safe", "balanced"}


def profile_uses_account_filters(profile: str) -> bool:
    return profile == "safe"


def filter_settings_for_profile(profile: str, skip_if_symbol_has_position: bool = True) -> TradeFilterSettings:
    if profile == "backtest":
        return TradeFilterSettings(
            spread=False,
            tp1_spread=False,
            risk=False,
            existing_position=False,
            max_setups=False,
            min_tp1_spread_multiple=1.5,
        )
    if profile == "balanced":
        return TradeFilterSettings(
            spread=True,
            tp1_spread=True,
            risk=True,
            existing_position=False,
            max_setups=False,
            min_tp1_spread_multiple=1.5,
        )
    return TradeFilterSettings(
        spread=True,
        tp1_spread=True,
        risk=True,
        existing_position=skip_if_symbol_has_position,
        max_setups=True,
        min_tp1_spread_multiple=1.5,
    )


def resolve_trade_filters(config: AppConfig) -> TradeFilterSettings:
    base = filter_settings_for_profile(config.bot.trade_decision_profile, config.risk.skip_if_symbol_has_position)
    risk_cfg = config.risk
    return TradeFilterSettings(
        spread=base.spread if risk_cfg.use_spread_filter is None else risk_cfg.use_spread_filter,
        tp1_spread=base.tp1_spread if risk_cfg.use_tp1_spread_filter is None else risk_cfg.use_tp1_spread_filter,
        risk=base.risk if risk_cfg.use_risk_filter is None else risk_cfg.use_risk_filter,
        existing_position=(
            base.existing_position
            if risk_cfg.use_existing_position_filter is None
            else risk_cfg.use_existing_position_filter
        ),
        max_setups=base.max_setups if risk_cfg.use_max_setups_filter is None else risk_cfg.use_max_setups_filter,
        min_tp1_spread_multiple=risk_cfg.min_tp1_spread_multiple,
    )


def evaluate_trade_signal(
    client: MT5Client,
    config: AppConfig,
    signal: Signal,
    symbol_cfg: SymbolConfig,
    *,
    spread: float | None = None,
    seen: bool = False,
    filters: TradeFilterSettings | None = None,
    execution_filters: bool | None = None,
    market_position_keys: set[str] | None = None,
    active_setup_count: int | None = None,
    day_start_balance: float | None = None,
) -> TradeDecision:
    if filters is None:
        filters = resolve_trade_filters(config)
        if execution_filters is False:
            filters = filter_settings_for_profile("backtest")

    if seen:
        return TradeDecision(
            allowed=False,
            code="duplicate",
            reason=f"duplicate signal {signal.setup_id}",
            risk_usd=0.0,
            spread=0.0,
            spread_atr=0.0,
            tp1_distance=0.0,
            min_tp1_distance=0.0,
        )

    if not signal.tps:
        return TradeDecision(
            allowed=False,
            code="tp1",
            reason="missing TP levels",
            risk_usd=0.0,
            spread=0.0,
            spread_atr=0.0,
            tp1_distance=0.0,
            min_tp1_distance=0.0,
        )

    geometry_error = invalid_market_geometry(signal.side, signal.entry, signal.sl, signal.tps)
    if geometry_error:
        return TradeDecision(
            allowed=False,
            code="geometry",
            reason=geometry_error,
            risk_usd=0.0,
            spread=0.0,
            spread_atr=0.0,
            tp1_distance=0.0,
            min_tp1_distance=0.0,
        )

    needs_spread = filters.spread or filters.tp1_spread
    if spread is None:
        spread_value = client.spread_price(signal.symbol) if needs_spread else 0.0
    else:
        spread_value = max(float(spread), 0.0)
    atr_proxy = signal.risk_distance / symbol_cfg.sl_atr_mult if symbol_cfg.sl_atr_mult else 0.0
    spread_atr = spread_value / atr_proxy if atr_proxy > 0 else float("inf")
    tp1_distance = abs(signal.tps[0] - signal.entry)
    min_tp1_distance = spread_value * filters.min_tp1_spread_multiple
    risk_usd = 0.0

    def decision(allowed: bool, code: str, reason: str) -> TradeDecision:
        return TradeDecision(
            allowed=allowed,
            code=code,
            reason=reason,
            risk_usd=risk_usd,
            spread=spread_value,
            spread_atr=spread_atr,
            tp1_distance=tp1_distance,
            min_tp1_distance=min_tp1_distance,
        )

    if atr_proxy <= 0:
        return decision(False, "invalid_atr", "invalid ATR proxy")

    risk_usd = signal_risk_usd(client, signal, strategy=config.bot.strategy)

    max_spread_atr = config.risk.max_spread_atr
    if filters.spread and spread_atr > max_spread_atr:
        return decision(
            False,
            "spread",
            f"spread/ATR {spread_atr:.2f} > cap {max_spread_atr:.2f} (spread={spread_value:.5f})",
        )

    if filters.tp1_spread and tp1_distance < min_tp1_distance:
        return decision(
            False,
            "tp1",
            f"TP1 too close to spread (tp1_dist={tp1_distance:.5f} min={min_tp1_distance:.5f} spread={spread_value:.5f})",
        )

    max_risk = symbol_cfg.max_setup_risk_usd
    if max_risk is None:
        max_risk = config.risk.max_setup_risk_usd
    if filters.risk and max_risk is not None and risk_usd > max_risk:
        return decision(False, "risk", f"risk {risk_usd:.2f} > cap {max_risk:.2f}")

    max_daily_loss_pct = config.risk.effective_daily_loss_pct()
    if max_daily_loss_pct is not None and day_start_balance is not None and day_start_balance > 0:
        daily_cap = daily_loss_setup_risk_cap(day_start_balance, max_daily_loss_pct)
        if risk_usd > daily_cap:
            return decision(
                False,
                "daily_loss_guard",
                (
                    f"setup risk ${risk_usd:.2f} > daily cap ${daily_cap:.2f} "
                    f"({max_daily_loss_pct:g}% of start-of-day balance ${day_start_balance:.2f})"
                ),
            )

    if filters.existing_position and market_position_keys is not None and signal.market_key in market_position_keys:
        return decision(False, "position", f"existing {signal.market_key} market position found")

    if filters.max_setups and active_setup_count is not None and active_setup_count >= config.bot.max_concurrent_setups:
        return decision(
            False,
            "max_setups",
            f"max concurrent setups reached ({active_setup_count}/{config.bot.max_concurrent_setups})",
        )

    return decision(True, "accepted", "accepted by shared trade decision rules")
