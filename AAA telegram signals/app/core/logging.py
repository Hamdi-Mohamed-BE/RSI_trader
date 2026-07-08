import sys
from pathlib import Path
from loguru import logger

# Ensure log dir exists
LOG_DIR = Path("storage/logs")
LOG_DIR.mkdir(parents=True, exist_ok=True)

# Remove default handler
logger.remove()

# 1. Main app log
logger.add(
    LOG_DIR / "app.log",
    rotation="10 MB",
    retention="10 days",
    level="DEBUG",
    format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}"
)

# 2. Telegram poll log
logger.add(
    LOG_DIR / "telegram.log",
    filter=lambda record: record["extra"].get("channel") == "telegram",
    rotation="10 MB",
    retention="10 days",
    level="DEBUG",
    format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {message}"
)

# 3. Order placement log
logger.add(
    LOG_DIR / "orders.log",
    filter=lambda record: record["extra"].get("channel") == "orders",
    rotation="10 MB",
    retention="10 days",
    level="DEBUG",
    format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {message}"
)

# 4. Error log
logger.add(
    LOG_DIR / "errors.log",
    level="ERROR",
    rotation="10 MB",
    retention="30 days",
    format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message} {exception}"
)

# 5. Console output for development
logger.add(
    sys.stdout,
    level="INFO",
    format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{message}</cyan>"
)

# Logger helpers
telegram_logger = logger.bind(channel="telegram")
orders_logger = logger.bind(channel="orders")
