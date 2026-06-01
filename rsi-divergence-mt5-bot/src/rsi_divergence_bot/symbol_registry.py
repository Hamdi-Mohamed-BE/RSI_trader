from __future__ import annotations

import logging
from pathlib import Path

from .config import AppConfig, SymbolConfig, add_custom_symbol, save_config
from .manual_trade import resolve_symbol, resolve_symbol_for_telegram
from .mt5_client import MT5Client
from .symbols import market_key, mt5_symbol_candidates


def ensure_symbol_for_signal_copy(
    token: str,
    config: AppConfig,
    client: MT5Client,
    *,
    config_path: Path | None = None,
    persist: bool = True,
    logger: logging.Logger | None = None,
) -> tuple[SymbolConfig | None, bool, bool]:
    """Resolve symbol for Telegram/Tradlia copy; auto-add to settings when missing on MT5.

    Returns (symbol_cfg, created_new, persisted_to_yaml).
  """
    existing = resolve_symbol(token, config)
    if existing is not None:
        return existing, False, False

    symbol_cfg, _memory_only = resolve_symbol_for_telegram(token, config, client, auto_register=False)
    if symbol_cfg is not None:
        for item in config.symbols:
            if item.key == symbol_cfg.key or item.symbol == symbol_cfg.symbol:
                return item, False, False
        return symbol_cfg, False, False

    base = _norm_token(token)
    suffix = config.mt5.broker_symbol_suffix if config.mt5.append_broker_symbol_suffix else ""
    candidates = list(mt5_symbol_candidates(token, suffix))
    mt5_name: str | None = None
    for candidate in candidates:
        if client.symbol_info(candidate) is None or client.tick(candidate) is None:
            continue
        mt5_name = candidate
        break
    if mt5_name is None:
        return None, False, False

    try:
        created = add_custom_symbol(
            config,
            symbol=mt5_name,
            name=token.strip() or mt5_name,
            demo_symbol=mt5_name,
            live_symbol=mt5_name,
            lot_per_leg=config.risk.default_forex_lot,
            enabled=False,
            signal_active=True,
            market_key_override=base if base != market_key(mt5_name) else None,
        )
    except ValueError as exc:
        if "already exists" in str(exc).lower():
            return resolve_symbol(token, config), False, False
        raise

    log = logger or logging.getLogger(__name__)
    log.warning(
        "SIGNAL COPY auto-added symbol=%s key=%s lot=%s enabled=false signal_active=true",
        created.symbol,
        created.key,
        created.lot_per_leg,
    )

    persisted = False
    if persist and config_path is not None:
        save_config(config_path, config)
        persisted = True

    return created, True, persisted


def _norm_token(value: str) -> str:
    import re

    return re.sub(r"[^A-Z0-9]", "", value.upper())
