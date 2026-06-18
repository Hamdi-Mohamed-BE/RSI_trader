# LTA Book-Based Trading Agent + Backtesting Tool

You are an expert AI trading-system engineer, quantitative analyst, and Python/FastAPI developer.

Your job is to read and understand the trading book located in:

```txt
C:\Users\hama101\Desktop\geek\ai trader\LTA
```

The book may be long, so read it in chunks. Extract the full trading methodology, rules, terminology, setups, confirmations, invalidations, examples, and risk-management principles. Do not skip details. Your first goal is to understand the strategy deeply enough to trade only the highest-quality setups.

Before writing code, inspect the folder, identify the book file format, read it in chunks, summarize the strategy rules, then create the base prompt. Only after that start coding the FastAPI app.

---

## Main Objectives

### 1. Create a Base Trading Prompt From the Book

Create a file inside the same folder:

```txt
C:\Users\hama101\Desktop\geek\ai trader\LTA\LTA_BASE_TRADING_PROMPT.md
```

This prompt must allow another AI trading agent to quickly understand and apply the book’s strategy.

The prompt should include:

- Strategy name and core philosophy
- Market structure rules
- Bias-building process
- Entry model
- Exit model
- Stop-loss placement rules
- Take-profit rules
- A+ setup criteria
- Setup invalidation rules
- Risk-management rules
- Symbol-specific notes for:
  - XAUUSD
  - XAGUSD
  - BTCUSD
- Timeframe hierarchy
- Session/time filters if mentioned
- News/event filters if mentioned
- Checklist before entering a trade
- Trade examples translated into actionable rules
- Clear “DO NOT TRADE” conditions
- Final decision framework:
  - A+ setup = allowed
  - B setup = skip
  - unclear setup = skip
  - revenge/random trade = skip

The final prompt must be practical, direct, and usable by another AI agent without needing to reread the whole book.

---

## 2. Build a Simple Automated Backtesting + Trading Research Tool

After creating the base trading prompt, build a simple local Python app using FastAPI.

Project location:

```txt
C:\Users\hama101\Desktop\geek\ai trader\LTA
```

Suggested structure:

```txt
LTA/
│
├── app/
│   ├── main.py
│   ├── config.py
│   ├── mt5_client.py
│   ├── strategy_engine.py
│   ├── backtester.py
│   ├── risk_manager.py
│   ├── models.py
│   ├── tradingview_mcp.py
│   └── templates/
│       └── index.html
│
├── data/
├── reports/
├── LTA_BASE_TRADING_PROMPT.md
├── requirements.txt
├── .env.example
└── README.md
```

---

## Supported Symbols

Start with only these symbols:

```txt
XAUUSD
XAGUSD
BTCUSD
US30
```

The user must be able to configure:

- Starting balance
- Lot size per symbol
- Risk per trade
- Max trades per day
- Max daily loss
- Max total drawdown
- Trading sessions
- Timeframes
- Whether live trading is enabled or disabled

Default mode must be **backtesting only**.

Live trading must be disabled unless explicitly enabled in config.

---

## Core Rule: Only A+ Setups

The app must only detect and test A+ setups.

Do not trade:

- weak setups
- late entries
- unclear structure
- emotional/revenge trades
- setups without confirmation
- setups against higher-timeframe bias
- setups during dangerous news unless the strategy allows it
- trades with poor risk-to-reward
- trades where stop loss is unclear
- trades where invalidation is not obvious

Every signal must receive a quality score.

Example scoring:

```txt
90–100 = A+ setup, allowed
80–89 = A setup, optional for research only
Below 80 = skip
```

For automated trading, only allow trades with score >= 90.

---

## FastAPI UI Requirements

Create a simple browser UI.

The UI should allow the user to:

- Select symbol: XAUUSD, XAGUSD, BTCUSD, US30
- Set starting balance
- Set backtest lot size per symbol
- Set live automation lot risk percent
- Select date range for backtest
- Select timeframe
- Run backtest
- View trade list
- View win rate
- View profit/loss
- View max drawdown
- View average R:R
- View A+ setup count
- View skipped setup count
- View reason why each setup was accepted or rejected
- Export results to CSV or JSON

The UI can be simple HTML/Jinja for now. No need for React unless necessary.

---

## MT5 Integration

Use the MetaTrader 5 Python package if available.

Implement an `mt5_client.py` module that can:

- Connect to MT5
- Check if MT5 is running
- Fetch historical candles
- Fetch symbol info
- Fetch current bid/ask
- Normalize lot size
- Calculate live lot size from current account balance, configured risk percent, and stop-loss distance
- Calculate pip/point value
- Prepare an order object
- Optionally place orders only if live trading is enabled

Do not place live trades by default.

Use safe defaults.

---

## TradingView MCP / MT5 MCP

If TradingView MCP, MT5 MCP, or other MCP tools are available, use them where helpful.

Use them for:

- fetching chart context
- validating market structure
- comparing TradingView and MT5 candles
- collecting historical data
- testing the strategy visually or programmatically

But the app must still run locally with Python/FastAPI and MT5.

---

## Strategy Engine

Create a `strategy_engine.py` that converts the book strategy into code.

It must include:

```python
def detect_bias(candles, timeframe):
    pass

def detect_market_structure(candles):
    pass

def detect_aoi(candles):
    pass

def detect_entry_confirmation(candles):
    pass

def score_setup(context):
    pass

def generate_signal(context):
    pass
```

Each signal must include:

```json
{
  "symbol": "XAUUSD",
  "timeframe": "M5",
  "direction": "BUY",
  "entry": 2350.50,
  "stop_loss": 2346.20,
  "take_profit": 2363.40,
  "risk_reward": 5.0,
  "setup_score": 94,
  "setup_grade": "A+",
  "reasons": [
    "Higher timeframe bullish bias",
    "Clean liquidity sweep",
    "Strong rejection candle",
    "Entry aligned with book rules"
  ],
  "invalidation": "Break below rejection candle low",
  "status": "allowed"
}
```

Rejected setups must also be logged with reasons.

Example:

```json
{
  "symbol": "BTCUSD",
  "timeframe": "M5",
  "setup_score": 72,
  "setup_grade": "B",
  "status": "rejected",
  "reasons": [
    "Higher timeframe bias unclear",
    "Entry came too late",
    "Risk-to-reward below minimum"
  ]
}
```

---

## Backtester

Create a `backtester.py` that:

- Loads candle data from MT5
- Runs the strategy over historical candles
- Simulates trades
- Applies spread/commission assumptions
- Tracks balance
- Tracks drawdown
- Tracks wins/losses
- Tracks R multiples
- Tracks skipped trades
- Outputs a detailed report

Backtest report must include:

```txt
Symbol
Timeframe
Date range
Starting balance
Ending balance
Net profit
Win rate
Total trades
Wins
Losses
Max drawdown
Average R:R
Best trade
Worst trade
A+ setups taken
Setups rejected
Reason breakdown for rejected setups
```

---

## Risk Manager

Create a `risk_manager.py` that handles:

- Lot size validation
- Backtest per-symbol lot config
- Live dynamic lot sizing from `MAX_LOT_RISK_PCT`
- Live bid/ask spread guard from `MAX_SPREAD_RISK_PERCENT` and `MAX_SPREAD_POINTS`
- Start balance
- Max risk per trade
- Max daily loss
- Max drawdown
- Max number of trades per day
- Symbol activity cooldown after any MT5 open or close event
- Stop trading after daily loss limit
- Stop trading after max drawdown
- Reject trades where risk is too high

The risk manager must always have final authority.

A trade can only pass if:

```txt
strategy_score >= 90
risk is acceptable
RR is acceptable
symbol is allowed
session is allowed
daily loss limit not reached
drawdown limit not reached
```

---

## Config Example

Create `.env.example` or config file with:

```env
LIVE_TRADING=false

START_BALANCE=1000

MAX_LOT_RISK_PCT=3.0
MAX_SPREAD_RISK_PERCENT=15
MAX_SPREAD_POINTS=0
AUTO_SYMBOL_ACTIVITY_COOLDOWN_MINUTES=60

MAX_RISK_PER_TRADE_PERCENT=1
MAX_DAILY_LOSS_PERCENT=3
MAX_TOTAL_DRAWDOWN_PERCENT=8
MAX_TRADES_PER_DAY=3

MIN_SETUP_SCORE=90
MIN_RISK_REWARD=5.0
```

---

## Important Safety Rules

Do not enable live trading automatically.

Do not place market orders unless:

```txt
LIVE_TRADING=true
setup_score >= 90
risk manager approves
bid/ask spread is acceptable
symbol is allowed
dynamic lot size is valid
stop loss exists
take profit exists
```

If any condition is missing, reject the trade.

The first version should focus on:

1. reading the book,
2. creating the trading prompt,
3. converting the rules into a clear strategy engine,
4. backtesting only,
5. simple UI.

Live trading can be added later only after the backtester is stable.

---

## Deliverables

Create the following files:

```txt
LTA_BASE_TRADING_PROMPT.md
README.md
requirements.txt
.env.example
app/main.py
app/config.py
app/mt5_client.py
app/strategy_engine.py
app/backtester.py
app/risk_manager.py
app/models.py
app/templates/index.html
```

The README must explain:

- how to install requirements
- how to run the FastAPI app
- how to connect MT5
- how to run a backtest
- how to configure backtest lot sizes and live dynamic risk-percent sizing
- how to enable/disable live trading
- what the strategy engine currently supports
- what still needs manual validation

---

## Final Instruction

Be strict.

The goal is not to take many trades.

The goal is to take only clean A+ trades that fully match the book.

When unsure, skip the trade.

No forced trades. No weak confirmations. No guessing.

First create the book-based trading prompt, then build the automated backtesting UI around it.
