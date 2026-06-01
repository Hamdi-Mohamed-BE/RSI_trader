from __future__ import annotations

import logging
from pathlib import Path

from .config import AppConfig, SymbolConfig, add_custom_symbol, default_symbol_lot, save_config
from .manual_trade import resolve_symbol
from .mt5_client import MT5Client
from .symbols import (
    find_symbol_config,
    first_available_mt5_symbol,
    market_key,
    signal_copy_broker_symbols,
    token_mt5_symbol_candidates,
)


def ensure_symbol_for_signal_copy(
    token: str,
    config: AppConfig,
    client: MT5Client,
    *,
    config_path: Path | None = None,
    persist: bool = True,
    logger: logging.Logger | None = None,
) -> tuple[SymbolConfig | None, bool, bool]:
    """Resolve symbol for Telegram/Tradlia copy; auto-add to settings when missing.

    Returns (symbol_cfg, created_new, persisted_to_yaml).
    """
    cleaned = (token or "").strip()
    if not cleaned:
        return None, False, False

    base_key, demo_name, live_name = signal_copy_broker_symbols(cleaned)

    existing = resolve_symbol(cleaned, config) or find_symbol_config(config.symbols, base_key)
    if existing is not None:
        return existing, False, False

    suffix = config.mt5.broker_symbol_suffix if config.mt5.append_broker_symbol_suffix else ""
    candidates = token_mt5_symbol_candidates(cleaned, suffix)
    mt5_name = first_available_mt5_symbol(client, candidates)
    if mt5_name is None:
        return None, False, False

    lot = config.risk.default_forex_lot
    provisional = SymbolConfig(
        symbol=base_key,
        name=cleaned,
        demo_symbol=demo_name,
        live_symbol=live_name,
        enabled=False,
        signal_active=True,
        lot_per_leg=lot,
        rr=[1.0, 1.5, 2.0],
    )
    lot = default_symbol_lot(provisional, config)

    try:
        created = add_custom_symbol(
            config,
            symbol=base_key,
            name=cleaned,
            demo_symbol=demo_name,
            live_symbol=live_name,
            lot_per_leg=lot,
            enabled=False,
            signal_active=True,
            market_key_override=base_key,
        )
    except ValueError as exc:
        if "already exists" in str(exc).lower():
            return resolve_symbol(cleaned, config) or find_symbol_config(config.symbols, base_key), False, False
        raise

    log = logger or logging.getLogger(__name__)
    log.warning(
        "SIGNAL COPY auto-added symbol=%s demo=%s live=%s lot=%s mt5_verified=%s",
        created.symbol,
        created.demo_symbol,
        created.live_symbol,
        created.lot_per_leg,
        mt5_name,
    )

    persisted = False
    if persist and config_path is not None:
        save_config(config_path, config)
        persisted = True

    return created, True, persisted
