# Telegram → MetaTrader 5 Signal Copier

## 1. Project Goal

Build a local Windows/VPS service that reads messages from a configured Telegram chat/channel every 10 seconds, detects whether each message is a valid trading signal, extracts the order details using a deterministic parser plus Gemini AI validation, then places the trade on the currently active MetaTrader 5 account.

The system must include a simple FastAPI web dashboard for:

- Turning the copier on/off.
- Configuring Telegram credentials and target chat.
- Configuring Gemini API key/model.
- Configuring risk mode: fixed lot, percentage risk, or hard USD risk cap.
- Viewing recent Telegram messages.
- Viewing LLM parsing JSON.
- Viewing placed orders, active trades, errors, and trade-management status.
- Enabling/disabling automatic break-even when TP1 is reached.

Example signal format:

```text
USDCAD BUY NOW
STOPLOSS @ 1.41425

TP @ 1.41750
TP @ 1.41875
TP @ 1.42050
```

Expected interpretation:

```json
{
  "is_signal": true,
  "symbol_raw": "USDCAD",
  "side": "buy",
  "order_type": "market",
  "entry_price": null,
  "stop_loss": 1.41425,
  "take_profits": [1.41750, 1.41875, 1.42050],
  "final_take_profit": 1.42050,
  "break_even_trigger_tp": 1.41750
}
```

---

## 2. Core Requirements

### 2.1 Telegram Reader

The system reads messages from one configured Telegram chat/channel.

Supported settings:

- `TELEGRAM_API_ID`
- `TELEGRAM_API_HASH`
- `TELEGRAM_BOT_TOKEN` if using bot mode
- `TELEGRAM_SESSION_STRING` or local Telethon session file if using user-client mode
- `TELEGRAM_CHAT_LINK`
- `COPIER_ENABLED=true|false`
- `POLL_INTERVAL_SECONDS=10`

Recommended implementation:

- Use `Telethon` for reliable channel/chat reading.
- Store the last processed Telegram message ID per chat.
- Poll every 10 seconds.
- Save every new message to the database before processing.

Important filtering rules:

- Ignore forwarded messages.
- Ignore replies unless `ALLOW_REPLY_SIGNALS=true` is enabled.
- Ignore edited duplicates already processed.
- Ignore messages with no trading intent.
- Ignore ads, promotions, results screenshots, referral messages, broker links, and educational posts.
- Ignore signals with missing required fields unless settings allow manual review.

Minimum required signal fields before live execution:

- Symbol.
- Direction: buy or sell.
- Order type: market or pending.
- Stop loss.
- At least one take-profit.

If no stop loss exists, default behavior must be: **do not place the trade**.

---

## 3. Signal Detection and Parsing

Use a two-layer parser:

1. **Deterministic parser first**
   - Fast regex/parser for common signal patterns.
   - Handles `BUY NOW`, `SELL NOW`, `BUY LIMIT`, `SELL LIMIT`, `BUY STOP`, `SELL STOP`.
   - Extracts symbol, SL, TP list, entry price, order type.

2. **Gemini AI classifier/parser second**
   - Used when deterministic parsing is incomplete or ambiguous.
   - Used as a validation layer even when deterministic parsing succeeds.
   - Must return strict JSON only.

Default Gemini model:

```text
gemini-3.0-flash
```

Make this configurable from the settings page.

### 3.1 Supported Signal Keywords

The parser should understand common variations:

```text
BUY NOW
SELL NOW
BUY MARKET
SELL MARKET
BUY LIMIT
SELL LIMIT
BUY STOP
SELL STOP
ENTRY
ENTRIES
SL
STOPLOSS
STOP LOSS
TP
TP1
TP2
TP3
TAKE PROFIT
TARGET
FINAL TP
```

### 3.2 Order Type Mapping

| Message Text | Internal Order Type | MT5 Action |
|---|---|---|
| `BUY NOW` | `market_buy` | Market buy |
| `SELL NOW` | `market_sell` | Market sell |
| `BUY LIMIT` | `buy_limit` | Pending buy limit |
| `SELL LIMIT` | `sell_limit` | Pending sell limit |
| `BUY STOP` | `buy_stop` | Pending buy stop |
| `SELL STOP` | `sell_stop` | Pending sell stop |

### 3.3 LLM JSON Schema

The LLM must return exactly this JSON shape:

```json
{
  "is_signal": true,
  "confidence": 0.0,
  "ignore_reason": null,
  "message_type": "signal",
  "symbol_raw": "USDCAD",
  "side": "buy",
  "order_type": "market",
  "pending_type": null,
  "entry_price": null,
  "stop_loss": 1.41425,
  "take_profits": [1.4175, 1.41875, 1.4205],
  "final_take_profit": 1.4205,
  "break_even_trigger_tp": 1.4175,
  "risk_warnings": [],
  "parser_notes": []
}
```

Allowed values:

```text
message_type: signal | ad | result | education | reply | forwarded | unknown
side: buy | sell | null
order_type: market | pending | null
pending_type: buy_limit | sell_limit | buy_stop | sell_stop | null
```

### 3.4 Gemini Prompt

Store this in `app/llm/prompts.py`:

```text
You are a strict forex/CFD signal parser.

Task:
Decide whether the Telegram message is a real actionable trading signal.
If it is a signal, extract the symbol, side, order type, pending type, entry price, stop loss, take profits, final take profit, and break-even trigger TP.

Rules:
- Return JSON only. No markdown. No explanation outside JSON.
- Ignore ads, promotions, broker links, copied results, screenshots text, education posts, and normal chat messages.
- If the message is forwarded, a reply, an ad, or not actionable, return is_signal=false.
- BUY NOW, SELL NOW, BUY MARKET, SELL MARKET mean market order.
- BUY LIMIT, SELL LIMIT, BUY STOP, SELL STOP mean pending order.
- If several TPs exist, final_take_profit is the farthest TP in the trade direction.
- break_even_trigger_tp is TP1 unless TP1 is missing.
- If stop loss is missing, add a risk warning.
- If entry is missing for a pending order, return is_signal=false.
- Use null for unknown fields.
- Use numbers for prices, not strings.

Return this exact JSON schema:
{
  "is_signal": boolean,
  "confidence": number,
  "ignore_reason": string | null,
  "message_type": "signal" | "ad" | "result" | "education" | "reply" | "forwarded" | "unknown",
  "symbol_raw": string | null,
  "side": "buy" | "sell" | null,
  "order_type": "market" | "pending" | null,
  "pending_type": "buy_limit" | "sell_limit" | "buy_stop" | "sell_stop" | null,
  "entry_price": number | null,
  "stop_loss": number | null,
  "take_profits": number[],
  "final_take_profit": number | null,
  "break_even_trigger_tp": number | null,
  "risk_warnings": string[],
  "parser_notes": string[]
}
```

---

## 4. Validation Rules Before Placing Trades

After parsing, validate the signal before sending it to MT5.

Required checks:

- `is_signal=true`.
- Confidence >= configured minimum, default `0.80`.
- Copier is enabled.
- Message was not processed before.
- Symbol can be resolved to a broker symbol.
- MT5 terminal is connected.
- Account trading is allowed.
- SL exists.
- Final TP exists.
- Direction and SL/TP make sense:
  - Buy: SL below entry/market price, TP above entry/market price.
  - Sell: SL above entry/market price, TP below entry/market price.
- Spread does not exceed optional max-spread setting.
- Daily trade limit not exceeded, if configured.
- Symbol exposure limit not exceeded, if configured.
- `order_check()` passes before `order_send()`.

If validation fails, save the error in the message/order log and show it on the dashboard.

---

## 5. MT5 Integration

Use the official Python package:

```text
MetaTrader5
```

The MT5 terminal must already be installed, opened, logged in, and connected to the active trading account on the same Windows machine/VPS running this app.

### 5.1 MT5 Client Responsibilities

Create `app/trading/mt5_client.py`.

Responsibilities:

- Initialize/shutdown MT5 connection.
- Get active account info.
- Get symbols list.
- Get symbol info.
- Get current bid/ask/tick.
- Send market orders.
- Send pending orders.
- Modify SL/TP.
- Read active positions.
- Read active orders.
- Run `order_check()` before `order_send()`.
- Normalize lots to broker min/max/step.
- Return structured error responses.

### 5.2 Market Order Price Rules

| Side | Execution Price |
|---|---|
| Buy | Ask |
| Sell | Bid |

### 5.3 Stop/TP Placement

Use:

- SL = parsed stop loss.
- TP = final take-profit.
- TP1 = break-even trigger only, unless partial-close feature is added later.

MVP behavior:

- Open one trade with final TP.
- When TP1 is touched, move SL to break-even if enabled.

Future optional behavior:

- Split the signal into multiple positions, one per TP.
- Close partial volume at TP1/TP2.

---

## 6. Broker Symbol Auto-Discovery

Some brokers use symbols like:

```text
EURUSD
EURUSDm
EURUSDc
EURUSD-STD
EURUSD.raw
XAUUSD
XAUUSDm
XAUUSD-STD
GOLD
USDCAD
USDCADm
```

Create `app/trading/symbol_resolver.py`.

### 6.1 Symbol Resolution Strategy

Input:

```text
USDCAD
```

Resolution algorithm:

1. Load all broker symbols using `mt5.symbols_get()`.
2. Normalize each broker symbol:
   - Uppercase.
   - Remove common suffixes: `m`, `c`, `.m`, `.c`, `.raw`, `.pro`, `-STD`, `_STD`, `-VIP`, `_VIP`.
   - Remove separators: `.`, `_`, `-` for comparison only.
3. Try exact match first.
4. Try normalized match.
5. Try alias match.
6. Prefer visible symbols.
7. If symbol is not visible, call `symbol_select(symbol, True)`.
8. Cache the mapping for speed, but refresh it before every order placement or after symbol failure.

Example output:

```json
{
  "requested_symbol": "USDCAD",
  "broker_symbol": "USDCADm",
  "match_type": "normalized_suffix",
  "confidence": 0.96
}
```

### 6.2 Alias Map

Support a configurable alias map:

```json
{
  "GOLD": ["XAUUSD", "XAUUSDm", "XAUUSD-STD"],
  "SILVER": ["XAGUSD", "XAGUSDm"],
  "BTC": ["BTCUSD", "BTCUSDm", "BTCUSD-STD"],
  "US30": ["US30", "DJ30", "DJI", "US30.cash"],
  "NAS100": ["NAS100", "USTEC", "US100", "NAS100.cash"]
}
```

---

## 7. Risk and Lot Calculation

Create `app/trading/risk.py`.

The user can choose one risk mode from the settings page:

1. Fixed lot.
2. Percentage of balance/equity.
3. Hard USD risk cap.

### 7.1 Settings

```json
{
  "risk_mode": "fixed_lot",
  "fixed_lot": 0.01,
  "risk_percent": 1.0,
  "risk_usd_cap": 10.0,
  "use_equity_instead_of_balance": true,
  "allow_min_lot_if_risk_too_small": true,
  "max_lot": null
}
```

### 7.2 Lot Formula

For percentage risk:

```text
risk_amount = account_equity * risk_percent / 100
```

For hard USD cap:

```text
risk_amount = risk_usd_cap
```

Risk per 1 lot:

```text
price_distance = abs(entry_price - stop_loss)
risk_per_lot = price_distance / tick_size * tick_value
lot = risk_amount / risk_per_lot
```

Then normalize:

```text
lot = floor_to_broker_step(lot)
lot = min(lot, broker_max_lot)
lot = max(lot, broker_min_lot) if allow_min_lot_if_risk_too_small=true
```

Important behavior requested:

- If calculated lot is below broker min lot, use broker min lot.
- Save a warning because this can exceed the configured risk amount.

Example warning:

```json
{
  "warning": "Calculated lot 0.003 is below broker minimum 0.01. Using broker minimum lot. Actual risk may exceed configured cap."
}
```

### 7.3 Safety Defaults

Default settings should be conservative:

```text
COPIER_ENABLED=false
RISK_MODE=fixed_lot
FIXED_LOT=0.01
MOVE_TO_BREAK_EVEN_ENABLED=true
MIN_LLM_CONFIDENCE=0.80
ALLOW_NO_SL=false
MAX_TRADES_PER_DAY=0  # 0 means unlimited
```

Live trading should not start automatically until the user enables the copier from the web settings page.

---

## 8. Break-Even Trade Manager

Create `app/trading/trade_manager.py`.

Behavior:

- Poll active MT5 positions every 10 seconds.
- For positions created by this copier, check whether TP1 has been reached.
- If TP1 reached and break-even setting is enabled:
  - Buy: move SL to entry price or entry + optional offset.
  - Sell: move SL to entry price or entry - optional offset.
- Save break-even action status in the database.
- Do not modify the same trade twice.

Settings:

```json
{
  "move_to_break_even_enabled": true,
  "break_even_offset_points": 0,
  "break_even_trigger": "tp1"
}
```

Trade metadata must store:

```json
{
  "telegram_message_id": 123,
  "symbol_raw": "USDCAD",
  "broker_symbol": "USDCADm",
  "side": "buy",
  "entry_price": 1.41500,
  "stop_loss_original": 1.41425,
  "take_profits": [1.41750, 1.41875, 1.42050],
  "final_take_profit": 1.42050,
  "break_even_trigger_tp": 1.41750,
  "break_even_done": false,
  "mt5_ticket": 123456789
}
```

---

## 9. Web App

Use:

```text
FastAPI
Jinja2
HTMX optional
SQLite
SQLModel or SQLAlchemy
```

### 9.1 Pages

#### Dashboard: `/`

Show:

- Copier status: on/off.
- MT5 connection status.
- Active account number/server/balance/equity.
- Active positions created by copier.
- Last 20 Telegram messages.
- Last 20 order attempts.
- Last errors.

#### Messages: `/messages`

Show table:

- Timestamp.
- Chat ID.
- Message ID.
- Raw text preview.
- Ignored/processed status.
- Signal detected yes/no.
- LLM confidence.
- Parsed JSON.
- Error if any.

#### Trades: `/trades`

Show table:

- Symbol raw.
- Broker symbol.
- Side.
- Order type.
- Lot.
- Entry.
- SL.
- Final TP.
- TP1 BE trigger.
- MT5 ticket.
- Placement status.
- Break-even status.
- Error.

#### Settings: `/settings`

Editable settings:

- Telegram API ID.
- Telegram API hash.
- Telegram bot token / bot ID if used.
- Telegram chat link.
- Gemini API key.
- Gemini model, default `gemini-3.0-flash`.
- Copier enabled on/off.
- Break-even enabled on/off.
- Risk mode.
- Fixed lot.
- Risk percent.
- USD risk cap.
- Use balance or equity.
- Min LLM confidence.
- Max spread optional.
- Max trades per day optional.
- Allow broker min lot if calculated risk lot is below min lot.

### 9.2 API Endpoints

```text
GET  /
GET  /messages
GET  /trades
GET  /settings
POST /settings
POST /api/copier/start
POST /api/copier/stop
GET  /api/status
GET  /api/messages
GET  /api/trades
POST /api/messages/{id}/reprocess
POST /api/trades/{id}/move-break-even
```

---

## 10. Database Schema

Use SQLite for MVP.

Database path:

```text
storage/copier.db
```

### 10.1 `settings`

```text
id
key
value_json
updated_at
```

### 10.2 `telegram_messages`

```text
id
chat_id
message_id
message_date
raw_text
is_reply
is_forwarded
is_edited
ignored
ignore_reason
processed
created_at
updated_at
```

Unique index:

```text
(chat_id, message_id)
```

### 10.3 `llm_parse_results`

```text
id
telegram_message_db_id
provider
model
prompt_version
raw_response_json
normalized_json
confidence
is_signal
error
created_at
```

### 10.4 `order_attempts`

```text
id
telegram_message_db_id
symbol_raw
broker_symbol
side
order_type
pending_type
entry_price
stop_loss
take_profits_json
final_take_profit
break_even_trigger_tp
lot
risk_mode
risk_amount
status
mt5_request_json
mt5_result_json
error
created_at
```

Status values:

```text
pending_validation
ignored
validation_failed
order_check_failed
send_failed
placed
```

### 10.5 `managed_trades`

```text
id
order_attempt_id
mt5_ticket
position_identifier
symbol_raw
broker_symbol
side
lot
entry_price
stop_loss_original
stop_loss_current
final_take_profit
break_even_trigger_tp
break_even_enabled
break_even_done
break_even_done_at
status
created_at
updated_at
```

### 10.6 `system_events`

```text
id
level
source
message
details_json
created_at
```

---

## 11. Background Loops

Use FastAPI lifespan startup to run async background tasks.

### 11.1 Telegram Poll Loop

Every 10 seconds:

1. Check if copier is enabled.
2. Read new Telegram messages.
3. Save raw messages.
4. Filter replies/forwarded/ad-like messages.
5. Parse possible signals.
6. Validate.
7. Resolve broker symbol.
8. Calculate lot.
9. Send order to MT5.
10. Save result.

### 11.2 Trade Manager Loop

Every 10 seconds:

1. Load active managed trades.
2. Fetch active MT5 positions.
3. Check TP1 reached.
4. Move SL to break-even if enabled.
5. Save result/errors.

### 11.3 Health Loop

Every 30 seconds:

1. Check MT5 connection.
2. Check Telegram connection.
3. Save status to memory/database.

---

## 12. Clean Modular Project Structure

```text
telegram-mt5-copier/
│
├── app/
│   ├── __init__.py
│   ├── main.py
│   │
│   ├── core/
│   │   ├── __init__.py
│   │   ├── config.py
│   │   ├── logging.py
│   │   ├── security.py
│   │   └── constants.py
│   │
│   ├── db/
│   │   ├── __init__.py
│   │   ├── database.py
│   │   ├── models.py
│   │   └── repositories.py
│   │
│   ├── telegram/
│   │   ├── __init__.py
│   │   ├── client.py
│   │   ├── poller.py
│   │   └── filters.py
│   │
│   ├── llm/
│   │   ├── __init__.py
│   │   ├── gemini_client.py
│   │   ├── parser.py
│   │   ├── prompts.py
│   │   └── schemas.py
│   │
│   ├── trading/
│   │   ├── __init__.py
│   │   ├── mt5_client.py
│   │   ├── symbol_resolver.py
│   │   ├── risk.py
│   │   ├── order_builder.py
│   │   └── trade_manager.py
│   │
│   ├── services/
│   │   ├── __init__.py
│   │   ├── copier_service.py
│   │   ├── settings_service.py
│   │   ├── message_service.py
│   │   └── status_service.py
│   │
│   ├── web/
│   │   ├── __init__.py
│   │   ├── routes.py
│   │   └── forms.py
│   │
│   ├── api/
│   │   ├── __init__.py
│   │   └── routes.py
│   │
│   ├── templates/
│   │   ├── base.html
│   │   ├── dashboard.html
│   │   ├── messages.html
│   │   ├── trades.html
│   │   └── settings.html
│   │
│   └── static/
│       ├── css/
│       │   └── app.css
│       └── js/
│           └── app.js
│
├── storage/
│   ├── copier.db
│   └── sessions/
│
├── tests/
│   ├── test_parser.py
│   ├── test_symbol_resolver.py
│   ├── test_risk.py
│   └── test_order_builder.py
│
├── .env.example
├── pyproject.toml
├── run.bat
└── plan.md
```

---

## 13. Environment Variables

Create `.env.example`:

```env
APP_HOST=127.0.0.1
APP_PORT=8787
DATABASE_URL=sqlite:///storage/copier.db

COPIER_ENABLED=false
POLL_INTERVAL_SECONDS=10

TELEGRAM_MODE=user
TELEGRAM_API_ID=
TELEGRAM_API_HASH=
TELEGRAM_BOT_TOKEN=
TELEGRAM_SESSION_STRING=
TELEGRAM_CHAT_LINK=
ALLOW_REPLY_SIGNALS=false

GEMINI_API_KEY=
GEMINI_MODEL=gemini-3.0-flash
MIN_LLM_CONFIDENCE=0.80

RISK_MODE=fixed_lot
FIXED_LOT=0.01
RISK_PERCENT=1.0
RISK_USD_CAP=10.0
USE_EQUITY_INSTEAD_OF_BALANCE=true
ALLOW_MIN_LOT_IF_RISK_TOO_SMALL=true
MAX_LOT=

MOVE_TO_BREAK_EVEN_ENABLED=true
BREAK_EVEN_OFFSET_POINTS=0

ALLOW_NO_SL=false
MAX_SPREAD_POINTS=
MAX_TRADES_PER_DAY=0
```

---

## 14. Recommended Dependencies

```text
fastapi
uvicorn[standard]
jinja2
python-multipart
pydantic
pydantic-settings
sqlmodel
sqlalchemy
aiosqlite
python-dotenv
telethon
google-genai
MetaTrader5
tenacity
loguru
orjson
httpx
pytest
ruff
```

---

## 15. Implementation Order

### Phase 1 — Project Foundation

1. Create `pyproject.toml` using `uv`.
2. Add FastAPI app in `app/main.py`.
3. Add SQLite database and models.
4. Add settings service.
5. Add dashboard/settings pages.

### Phase 2 — Telegram Reader

1. Add Telethon client.
2. Connect to configured chat.
3. Poll new messages every 10 seconds.
4. Save messages to database.
5. Add filtering for forwards/replies/ads.

### Phase 3 — Parser

1. Add deterministic parser.
2. Add Gemini parser.
3. Add Pydantic validation schema.
4. Save raw LLM response and normalized parsed JSON.
5. Add parser tests using real examples.

### Phase 4 — MT5 Trading

1. Add MT5 connection wrapper.
2. Add symbol resolver.
3. Add risk/lot calculation.
4. Add order builder.
5. Add order validation and `order_check()`.
6. Place market/pending orders.
7. Save order result.

### Phase 5 — Trade Management

1. Track copier-created trades.
2. Poll active positions.
3. Move SL to break-even when TP1 is reached.
4. Show break-even status on dashboard.

### Phase 6 — Hardening

1. Add duplicate detection.
2. Add max daily trades.
3. Add max spread filter.
4. Add detailed logs.
5. Add retry/backoff for Telegram/Gemini failures.
6. Add dry-run mode.
7. Add tests for parser, risk, and symbol resolution.

---

## 16. Important Edge Cases

### 16.1 Multiple Symbols in One Message

Default MVP:

- Ignore multi-symbol messages unless parser can identify exactly one actionable symbol.

Future:

- Split into multiple order attempts.

### 16.2 Multiple Entries

Example:

```text
BUY XAUUSD
ENTRY 2330 - 2335
SL 2322
TP 2350
```

MVP behavior:

- Use the midpoint as entry for pending orders only if enabled.
- Otherwise mark as manual review.

### 16.3 Market Order With Old Price

For `BUY NOW` / `SELL NOW`, use current MT5 bid/ask.

Optional setting:

```text
MAX_SIGNAL_AGE_SECONDS=120
```

If message is older than this, ignore it.

### 16.4 Duplicate Signals

Prevent duplicate orders by checking:

- Telegram chat ID + message ID.
- Text hash.
- Symbol + side + SL + final TP within a recent time window.

### 16.5 Broker Min Lot Higher Than Risk Lot

Requested behavior:

- Use broker minimum lot.
- Save warning.
- Show warning clearly on dashboard.

### 16.6 MT5 Not Connected

Do not crash.

Save error:

```text
MT5 terminal not connected or account trading disabled.
```

Show it in dashboard.

---

## 17. Testing Plan

### 17.1 Parser Tests

Create test cases for:

```text
USDCAD BUY NOW
STOPLOSS @ 1.41425
TP @ 1.41750
TP @ 1.41875
TP @ 1.42050
```

Expected:

```text
market buy, SL 1.41425, final TP 1.42050, TP1 1.41750
```

Other cases:

- `SELL NOW`.
- `BUY LIMIT` with entry.
- `SELL LIMIT` with entry.
- `BUY STOP` with entry.
- Missing SL.
- Missing TP.
- Forwarded result screenshot text.
- Ad/promotional message.
- Reply message.

### 17.2 Risk Tests

Test:

- Fixed lot.
- Percent risk.
- USD cap risk.
- Lot below broker minimum.
- Lot above broker maximum.
- Invalid SL/entry distance.

### 17.3 Symbol Resolver Tests

Test mappings:

```text
EURUSD -> EURUSDm
EURUSD -> EURUSDc
EURUSD -> EURUSD-STD
XAUUSD -> XAUUSD-STD
GOLD -> XAUUSD
BTC -> BTCUSD
```

### 17.4 MT5 Dry-Run Tests

Add dry-run mode so order requests can be generated without sending to broker.

---

## 18. Logging

Use structured logs with `loguru`.

Log files:

```text
storage/logs/app.log
storage/logs/telegram.log
storage/logs/orders.log
storage/logs/errors.log
```

Every order attempt must log:

- Raw Telegram message.
- Parser result.
- Symbol resolution.
- Risk calculation.
- MT5 order request.
- MT5 result.
- Error if failed.

---

## 19. Security Notes

- Store API keys in `.env` or encrypted settings, not hardcoded.
- Hide sensitive values in dashboard by default.
- Do not expose the FastAPI server publicly without authentication.
- Default host should be `127.0.0.1`.
- Add basic password authentication before exposing on a VPS.
- Never log full Telegram session strings or full API keys.

---

## 20. Done Definition

The MVP is complete when:

- `run.bat` installs dependencies with `uv` and starts FastAPI.
- Dashboard opens locally.
- Settings page saves Telegram/Gemini/risk/copier settings.
- Telegram messages are polled every 10 seconds.
- Forwarded/reply/ad messages are ignored.
- Valid signals are parsed into strict JSON.
- Broker symbol is auto-resolved.
- Lot is calculated using selected risk mode.
- Orders are sent to the active MT5 account.
- Raw LLM JSON, placement status, and errors are visible in the dashboard.
- Active copier trades are tracked.
- SL moves to break-even when TP1 is reached if enabled.
