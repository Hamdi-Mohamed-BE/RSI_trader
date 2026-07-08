# HamaForex LTA + Crypto MBO Trading Plan

**Purpose:**  
Upgrade the existing LTA-style market analysis plan so that **BTC, ETH, and crypto spot** use Coinbase order-book/MBO-style data for better entry confirmation, while keeping the existing workflow for **gold, forex, indices, and futures confirmation**.

---

## 1. Core Rule

Do **not** replace the LTA framework.

```text
Volume Profile = where to trade
Market Structure = direction
MBO / Level 3 data = confirmation that the entry is real
```

For crypto spot, Coinbase order-book data becomes an extra execution-confirmation layer.

---

## 2. Data Source Plan

### Crypto Spot: BTC, ETH, SOL, Major Coinbase Pairs

Use Coinbase Exchange data.

```text
Primary:
- Coinbase Level 3 / MBO-style order book
- Coinbase WebSocket full channel
- Coinbase REST Level 3 snapshot

Fallback:
- Coinbase Level 2 order book
- Coinbase trades/ticker stream
- TradingView chart only for visual confirmation
```

Best pairs to start with:

```text
BTC-USD
ETH-USD
SOL-USD
XRP-USD if available/liquid
```

Avoid thin/illiquid pairs for automated trading.

---

### Gold / XAUUSD

Keep the current plan.

```text
Primary chart:
- XAUUSD broker chart for execution

Confirmation:
- GC1! / COMEX gold futures for cleaner volume direction
- DXY for dollar pressure
- Volume Profile / FRVP
- HTF supply and demand
```

Use futures for confirmation, but execute on your broker's XAUUSD levels.

---

### US30 / NAS100 / Indices

Keep current plan.

```text
Primary chart:
- Broker CFD chart for execution

Confirmation:
- YM / NQ / ES futures if available
- Session structure
- FRVP / Volume Profile
- HTF supply and demand
```

---

### Forex

Keep current plan.

```text
Primary:
- Broker feed

Confirmation:
- DXY for USD pairs
- Related currency index if available
- HTF market structure
- FRVP / Volume Profile
```

---

## 3. Crypto MBO Architecture

```text
Crypto Data Layer
│
├── Coinbase REST Snapshot
│   └── Get full Level 3 order book at startup
│
├── Coinbase WebSocket Full Channel
│   ├── received
│   ├── open
│   ├── match
│   ├── done
│   └── change
│
├── Local MBO Book Builder
│   ├── Track active bid orders
│   ├── Track active ask orders
│   ├── Track order_id
│   ├── Aggregate by price level
│   ├── Detect sequence gaps
│   └── Rebuild book if desynced
│
├── Microstructure Signal Engine
│   ├── Absorption
│   ├── Iceberg-like behavior
│   ├── Spoof / pull detection
│   ├── Stacked liquidity
│   ├── Aggressive market buys/sells
│   └── Imbalance at key levels
│
└── Strategy Engine
    ├── LTA Volume Profile zones
    ├── Session structure
    ├── HTF bias
    ├── MBO confirmation
    ├── Entry
    ├── Invalidation
    └── TP management
```

---

## 4. Recommended WebSocket Model

For heavy Coinbase full-channel usage, separate major products.

```text
Connection 1: BTC-USD full channel
Connection 2: ETH-USD full channel
Connection 3: SOL-USD full channel
Connection 4: level2 fallback + ticker + heartbeat
```

The bot must include:

```text
- Reconnect logic
- Exponential backoff
- Sequence-gap detection
- Automatic book rebuild
- REST request throttling
- WebSocket subscription limit protection
```

---

## 5. Crypto Spot Strategy Logic

### Main Rule

```text
Do not trade MBO alone.
MBO confirms the LTA zone.
```

The correct order is:

```text
1. HTF bias
2. Volume Profile zone
3. Market structure confirmation
4. MBO confirmation
5. Entry
6. Invalidation
7. TP management
```

---

## 6. A+ Long Setup for BTC / ETH Spot

Use this when price reaches demand, VAL, previous low, or a high-probability support zone.

```text
A+ Long Conditions:

1. Price reaches VAL / demand / previous low.
2. Sellers hit aggressively into the bid.
3. Price stops moving lower.
4. Bid refresh appears repeatedly.
5. Sell pressure fails to break the level.
6. Delta is negative, but price is stable or rising.
7. M5 or M15 closes back above the level.
8. Retest holds.
9. Enter long.
```

### Long Entry Model

```text
Entry:
- Buy retest after reclaim

Stop Loss:
- Below sweep low or below failed support

TP1:
- POC / nearest high-volume node

TP2:
- VAH / next resistance

TP3:
- Prior high / liquidity pool
```

---

## 7. A+ Short Setup for BTC / ETH Spot

Use this when price reaches supply, VAH, previous high, or a high-probability resistance zone.

```text
A+ Short Conditions:

1. Price reaches VAH / supply / previous high.
2. Buyers chase aggressively into the ask.
3. Price stops moving higher.
4. Ask refresh appears repeatedly.
5. Buy pressure fails to break the level.
6. Delta is positive, but price is stable or falling.
7. M5 or M15 closes back below the level.
8. Retest fails.
9. Enter short.
```

### Short Entry Model

```text
Entry:
- Sell retest after rejection

Stop Loss:
- Above sweep high or above failed resistance

TP1:
- POC / nearest high-volume node

TP2:
- VAL / next support

TP3:
- Prior low / liquidity pool
```

---

## 8. MBO Confirmation Rules

### Absorption Long

```text
Signal:
- High sell market volume into support
- Best bid keeps refreshing
- Price does not break lower
- Delta is negative but price holds

Meaning:
- Sellers are being absorbed

Action:
- Look for long only after reclaim / retest
```

### Absorption Short

```text
Signal:
- High buy market volume into resistance
- Best ask keeps refreshing
- Price does not break higher
- Delta is positive but price stalls

Meaning:
- Buyers are being absorbed

Action:
- Look for short only after rejection / retest
```

### Spoof / Pull Warning

```text
Signal:
- Large wall appears near price
- Price moves toward it
- Wall disappears before trade
- No real execution happens at that level

Meaning:
- Liquidity may be fake

Action:
- Do not trust the wall
- Wait for actual trades / absorption / rejection
```

### Breakout Confirmation

```text
Signal:
- Price breaks VAH or VAL
- Aggressive trades continue through the level
- Book imbalance supports direction
- Retest holds

Meaning:
- Breakout has better probability

Action:
- Trade continuation on retest
```

---

## 9. Volume Profile Rules for All Markets

Use these levels:

```text
POC = control / magnet
VAH = upper value edge
VAL = lower value edge
HVN = accepted price area
LVN = rejection / fast-move area
```

### Simple Decision Rules

```text
Price rejects VAH:
- Look for sell

Price reclaims VAH and holds:
- Look for continuation buy

Price rejects VAL:
- Look for buy

Price loses VAL and retests:
- Look for continuation sell

Price sits around POC:
- Usually chop / no trade unless strong confirmation appears
```

---

## 10. Best Timeframes

### Crypto Spot: BTC / ETH

```text
Bias:
- H4 / H1

Setup:
- M30 / M15

Execution:
- M5

Micro-confirmation:
- MBO / Level 3 book
```

### Gold / XAUUSD

```text
Bias:
- H4 / H1

Setup:
- M30 / M15

Execution:
- M5

Confirmation:
- GC futures + DXY
```

### US30 / NAS100

```text
Bias:
- H1

Setup:
- M30 / M15

Execution:
- M5

Confirmation:
- Futures if available
```

---

## 11. Crypto Risk Rules

Crypto moves fast and can wick aggressively.

```text
Max risk per trade:
- 0.25% to 1%

Avoid:
- Chasing breakouts
- Trading inside POC chop
- Trading low-liquidity pairs
- Trading during major exchange outages
- Trading only from order-book walls
```

Recommended minimum RR:

```text
Scalp:
- 1.5R minimum

Clean LTA setup:
- 2R minimum

A+ setup:
- 3R+ target preferred
```

---

## 12. Spot Crypto Execution Notes

For spot crypto:

```text
Long = buy spot
Exit = sell spot
No liquidation risk unless margin is used
No shorting unless exchange/account supports margin or derivatives
```

For pure spot trading, the system should prioritize:

```text
- Long setups after demand absorption
- Exits at VAH / POC / liquidity highs
- Stablecoins as cash balance
- No leverage by default
```

If shorting is needed, use a separate derivatives/perpetual module, not the spot module.

---

## 13. Final HamaForex Plan

```text
Keep LTA as the main strategy framework.

For crypto:
- Add Coinbase Level 3 / MBO-style data
- Use it only as entry confirmation
- Best markets: BTC-USD and ETH-USD first

For gold:
- Keep XAUUSD + GC futures + DXY confirmation

For indices:
- Keep CFD chart + futures confirmation

For forex:
- Keep broker feed + DXY/currency confirmation

Do not replace Volume Profile with MBO.
MBO confirms whether the reaction at the Volume Profile level is real.
```

---

## 14. Practical Scan Template

```text
Symbol:
Market:
Timeframes:
Session:
Current price:
HTF bias:
Important POC:
Important VAH:
Important VAL:
Liquidity high:
Liquidity low:
MBO confirmation:
Preferred direction:
Max SL:
Risk:
```

Example:

```text
Symbol: BTC-USD
Market: Coinbase Spot
Timeframes: H1 + M30 + M15 + M5
Session: NY
Current price: 59,500
HTF bias: bearish below 59,800
POC: 59,450
VAH: 59,900
VAL: 58,900
MBO: ask absorption at VAH
Preferred direction: sell retest
Max SL: 300 points
Risk: 0.5%
```

---

## 15. One-Line Rule

```text
Trade the LTA zone only when the order book proves the reaction is real.
```
