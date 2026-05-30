"""
HFT Scalper — tweak everything here.
All values are plain constants; change and re-run bot.py.
"""

# ── Symbols & connection ─────────────────────────────────────────────────────
# USD crypto pairs on your broker — edit list to match Market Watch names
SYMBOLS = [
    "BTCUSD",
    "ETHUSD",
    "LTCUSD",
    "SOLUSD",
    "XRPUSD",
    "ADAUSD",
]

MT5_TERMINAL_PATH = None        # None = attach to already-open MT5 (recommended)
                                # or r"C:\Program Files\MetaTrader 5\terminal64.exe"
MT5_LOGIN = None
MT5_PASSWORD = None
MT5_SERVER = None

# ── Position sizing ───────────────────────────────────────────────────────────
LOT_SIZE = 0.3                  # default lot for all symbols
# Optional per-symbol lot override, e.g. {"BTCUSD": 0.01, "ETHUSD": 0.05}
SYMBOL_LOTS: dict[str, float] = {}

MAX_OPEN_POSITIONS = 6          # total open trades across all cryptos
MAX_OPEN_POSITIONS_PER_SYMBOL = 1
MAGIC_NUMBER = 20260530

# ── Per-trade $ targets — broker SL/TP placed at these levels ────────────────
STOP_LOSS_USD = 8.0             # max loss per trade (~$8)
TAKE_PROFIT_USD = 20.0          # target win per trade (~$20) → 2.5:1 R:R
# Optional per-symbol (take_profit_usd, stop_loss_usd)
SYMBOL_TP_SL_USD: dict[str, tuple[float, float]] = {
    "BTCUSD": (30.0, 15.0),     # BTC moves slower in $ terms at same lot
    "ETHUSD": (18.0, 8.0),
    "SOLUSD": (12.0, 6.0),
    "XRPUSD": (10.0, 5.0),
    "ADAUSD": (10.0, 5.0),
    "LTCUSD": (12.0, 6.0),
}
PLACE_BROKER_SLTP = True        # attach SL/TP to every order in MT5
USE_SOFTWARE_SLTP_BACKUP = True # bot also closes if broker SL/TP missing

# ── Session goal ─────────────────────────────────────────────────────────────
SESSION_TARGET_PROFIT_USD = 100.0
SESSION_MAX_LOSS_USD = 40.0

# ── Pace (patient mode) ───────────────────────────────────────────────────────
FAST_MODE = False
USE_TICK_FIRST = False
STATUS_EVERY_SECONDS = 15

# ── Timing ───────────────────────────────────────────────────────────────────
LOOP_SLEEP_SECONDS = 0.5
MIN_SECONDS_BETWEEN_ENTRIES = 60.0   # per symbol — wait before re-entering same coin
MAX_POSITION_AGE_SECONDS = 0

# ── Order execution ─────────────────────────────────────────────────────────
DEVIATION_POINTS = 2000
ORDER_COMMENT = "hft-scalp"

# ── Strategy (M5 trend + confirmation) ───────────────────────────────────────
TIMEFRAME = "M5"
FAST_EMA_PERIOD = 8
SLOW_EMA_PERIOD = 21
RSI_PERIOD = 14
RSI_BUY_BELOW = 50
RSI_SELL_ABOVE = 50
TICK_MOMENTUM_COUNT = 10
MIN_SIGNAL_SCORE = 3
TICK_MIN_MOVE_POINTS = 200      # default; altcoins often need lower values
# Optional per-symbol tick noise filter, e.g. {"XRPUSD": 50, "ADAUSD": 30}
SYMBOL_TICK_MIN_POINTS: dict[str, int] = {
    "ETHUSD": 150,
    "LTCUSD": 100,
    "SOLUSD": 80,
    "XRPUSD": 50,
    "ADAUSD": 30,
}

# ── Safety filters ───────────────────────────────────────────────────────────
MAX_SPREAD_POINTS = 5000
MIN_FREE_MARGIN_USD = 50.0
TRADING_HOURS_UTC = None

# ── Logging ──────────────────────────────────────────────────────────────────
VERBOSE = True

# Legacy single-symbol alias (diagnose / backward compat)
SYMBOL = SYMBOLS[0]
