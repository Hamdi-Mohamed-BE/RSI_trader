from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path

import uvicorn

from .backtest import run_backtest
from .bot import SignalBot
from .config import load_config
from .logging_utils import setup_logging
from .mt5_account_pool import Mt5AccountPool
from .mt5_account_store import Mt5AccountStore, default_db_path
from .web import create_app


def main() -> None:
    parser = argparse.ArgumentParser("RSI divergence MT5 bot")
    parser.add_argument("command", choices=["web", "run", "once", "backtest"])
    parser.add_argument("--config", default="config.yaml")
    parser.add_argument("--start")
    parser.add_argument("--end")
    args = parser.parse_args()

    config_path = Path(args.config).resolve()
    config = load_config(config_path)
    log_file = Path(config.bot.log_file)
    if not log_file.is_absolute():
        log_file = (config_path.parent / log_file).resolve()
    state_file = Path(config.bot.state_file)
    if not state_file.is_absolute():
        state_file = (config_path.parent / state_file).resolve()
    config.bot.state_file = str(state_file)
    config.bot.log_file = str(log_file)
    logger = setup_logging(log_file)
    if config.bot.dry_run:
        logger.info("STARTUP dry_run=true - no live MT5 orders will be placed")
    else:
        logger.warning("STARTUP dry_run=false - LIVE MT5 orders will be placed")
    runtime_dir = (config_path.parent / "runtime").resolve()
    account_store = Mt5AccountStore(default_db_path(config_path.parent))
    account_pool = Mt5AccountPool(account_store, config, runtime_dir, logger)
    bot = SignalBot(config, logger, account_pool=account_pool)

    try:
        if account_pool.active:
            account_pool.start()
        if args.command == "web":
            app = create_app(config, bot, config_path, account_pool=account_pool)
            logger.info("WEB START http://%s:%s", config.web.host, config.web.port)
            uvicorn.run(app, host=config.web.host, port=config.web.port)
        elif args.command == "run":
            bot.client.initialize()
            bot.run_forever()
        elif args.command == "once":
            bot.client.initialize()
            bot.run_once()
        elif args.command == "backtest":
            if not args.start or not args.end:
                raise SystemExit("--start and --end are required for backtest")
            bot.client.initialize()
            result = run_backtest(
                bot.client,
                config,
                datetime.fromisoformat(args.start),
                datetime.fromisoformat(args.end),
            )
            logger.info("BACKTEST %s", result)
            print(result)
    finally:
        account_pool.stop()
        if not account_pool.active:
            bot.client.shutdown(force=True)


if __name__ == "__main__":
    main()
