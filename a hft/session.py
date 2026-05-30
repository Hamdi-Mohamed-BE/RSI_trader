"""Track deals closed by broker TP/SL for session PnL."""

from __future__ import annotations

from datetime import datetime, timedelta

import MetaTrader5 as mt5

import config as cfg


def fetch_closed_profit(ticket: int) -> float | None:
    """Get realized PnL for a closed position ticket."""
    start = datetime.now() - timedelta(days=1)
    deals = mt5.history_deals_get(start, datetime.now())
    if not deals:
        return None

    total = 0.0
    found = False
    for deal in deals:
        if deal.position_id != ticket:
            continue
        if deal.entry != mt5.DEAL_ENTRY_OUT:
            continue
        total += deal.profit + deal.swap + deal.commission
        found = True

    return total if found else None
