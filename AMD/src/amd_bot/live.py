from __future__ import annotations

from datetime import datetime, timedelta, timezone
import time as clock

import MetaTrader5 as mt5

from .config import Config
from .engine import backtest_symbol
from .mt5_data import connection, discover_symbols, load_m1, symbol_metadata


UTC = timezone.utc


def run_live(config: Config, once: bool = False) -> None:
    """Protected scanner.

    The scanner prints newly confirmed historical/today signals. Order execution
    remains locked unless both ENABLE_TRADING=true and DRY_RUN=false. This first
    version intentionally does not submit orders until forward validation passes.
    """
    if config.enable_trading and not config.dry_run:
        raise RuntimeError(
            "Live order submission is intentionally locked in v0.1. "
            "Run the forward scanner and validate it before enabling execution."
        )
    while True:
        now = datetime.now(UTC)
        start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        with connection() as account:
            symbols = discover_symbols(config.symbols)
            print(
                f"[{now.isoformat()}] account={account.login} "
                f"server={account.server} balance=${account.balance:,.2f} "
                "mode=DRY-RUN"
            )
            for canonical, symbol in symbols.items():
                meta = symbol_metadata(symbol)
                frame = load_m1(
                    symbol,
                    start,
                    now,
                    config.root / "data" / "live",
                    refresh=True,
                )
                trades = backtest_symbol(
                    frame,
                    symbol,
                    float(meta["point"]),
                    config,
                    start,
                    now,
                )
                if not trades:
                    print(f"  {canonical:<7} no confirmed AMD setup")
                    continue
                latest = trades[-1]
                print(
                    f"  {canonical:<7} {latest.phase.upper()} "
                    f"{latest.side.upper()} entry={latest.entry:.5f} "
                    f"SL={latest.initial_stop:.5f} TP={latest.target:.5f} "
                    f"status={latest.exit_reason}"
                )
        if once:
            return
        clock.sleep(config.poll_seconds)
