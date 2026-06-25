from __future__ import annotations

import asyncio
import logging
import sys
from pathlib import Path

from .config import load_settings
from .mt5_client import BrokerError, MT5Client
from .parser import SignalParser
from .storage import Storage
from .telegram_service import TelegramSignalService
from .trade_manager import PositionWatcher, TradeManager


def configure_logging(level: str) -> None:
    logging.basicConfig(
        level=getattr(logging, level, logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )


async def main() -> int:
    env_path = Path(".env")
    settings = load_settings(env_path if env_path.exists() else None)
    configure_logging(settings.log_level)

    missing = settings.validate()
    if missing:
        logging.error("Missing required config: %s", ", ".join(missing))
        return 2

    storage = Storage(settings.state_db)
    broker = MT5Client(settings)

    try:
        broker.connect(required=not settings.dry_run)
    except BrokerError as exc:
        logging.error("%s", exc)
        return 2

    parser = SignalParser(max_age_seconds=settings.max_signal_age_seconds)
    trade_manager = TradeManager(settings, storage, broker)
    watcher = PositionWatcher(settings, storage, broker)
    telegram = TelegramSignalService(settings, storage, parser, trade_manager.handle_signal)

    watcher_task = asyncio.create_task(watcher.run_forever())
    try:
        await telegram.run_forever()
    finally:
        watcher_task.cancel()
        broker.shutdown()

    return 0


def run() -> None:
    try:
        raise SystemExit(asyncio.run(main()))
    except KeyboardInterrupt:
        sys.exit(130)
