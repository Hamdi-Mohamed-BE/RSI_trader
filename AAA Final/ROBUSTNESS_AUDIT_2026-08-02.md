# Seen/Unseen Robustness Audit — 2026-08-02

## Bottom line

Backtests cannot prove that a bot will make money live. They can expose overfitting and reject weak candidates. Under a strict chronological validation standard, the current suite contains two conditional XAU candidates, one provisional XAU candidate, and two rejected bots.

| Rank | Bot / setup | Best symbol | Untouched result | Decision |
|---:|---|---|---|---|
| 1 | EMA3, H4 EMA200-slope pivot reversal | XAUUSD | 14 trades, 57.14% WR, PF 1.80, +4.82R, 2.97% DD | **Conditional pass** |
| 2 | Asia Breakout, confirmed close + midpoint stop + trailing | XAUUSD | Older unseen period: 67 trades, 47.76% WR, PF 1.36, +10.58R, 16.08% DD | **Conditional pass; reduce risk** |
| 3 | DmC, previous-body bias + reaction/retest | XAUUSD | 8 trades, 50.00% WR, PF 1.35, +1.42R, 4.00% DD | **Provisional; sample too small** |
| 4 | AMD v2, London-only reversal | XAUUSD | Older stress: 45 trades, 37.78% WR, PF 1.11, +5.00R, 19.42% DD; one losing regime | **Reject for live** |
| 5 | US100 Weakness, S2A OCO 3R | NAS100U6 | 3 holdout trades, PF 1.48, but development PF 0.87 and -0.65R | **Reject** |

The strongest current evidence is **EMA3 on XAUUSD H4**. Asia Breakout on XAUUSD has the largest genuinely unseen sample, but its edge fell from PF 4.48 in optimization to PF 1.36 on older data and drawdown rose to 16.08% at the tested 3% risk. That is usable research evidence, not proof of a stable high-PF system.

## Validation rules

- Parameters are chosen only from the development segment.
- Validation and holdout parameters remain frozen.
- Different-broker replay is treated as a feed-robustness test, not as new market time.
- A positive result with fewer than 10 untouched trades is inconclusive.
- A candidate requires positive net R, PF at least 1.30, and acceptable drawdown to pass conditionally.
- A longer stress period overrides an attractive recent window.
- Historical spread is included where supported by the bot's engine. Slippage, rejects, latency, and live gaps can still make live results worse.

## 1. EMA3

### Selected setup

- Symbol/timeframe: **XAUUSD H4**
- Pivot distance: **5 candles left / 5 right**
- Filter: **EMA200 slope**, measured over **6 H4 bars**
- Exit: trailing stop starts at **+1.5R**, trails **1R** behind
- Risk used for comparison: **1% per trade**

| Segment | Dates | Trades | WR | PF | Net R | Max DD |
|---|---|---:|---:|---:|---:|---:|
| Development | 2025-08-02 to 2026-05-02 | 23 | 60.87% | 4.12 | +28.11R | 2.97% |
| Untouched validation | 2026-05-02 to 2026-08-01 | 14 | 57.14% | 1.80 | +4.82R | 2.97% |
| Full | 2025-08-02 to 2026-08-01 | 37 | 59.46% | 3.20 | +32.93R | 5.29% |

Secondary candidates:

- **US30 H1:** 23 untouched trades, 30.43% WR, PF 1.38, +6.12R, 6.79% DD. Positive but weaker and development PF was only 1.21.
- **BTCUSD H4:** 9 untouched trades, 33.33% WR, PF 1.44, +2.48R, 2.97% DD. Too few trades.
- EURUSD, GBPJPY, US100 H1 and XAU H1 failed or were too weak.

Decision: **XAUUSD H4 is the best overall candidate**, but 14 unseen trades are not enough to call it proven. Forward-demo validation remains required.

## 2. Asia Breakout

### Selected setup

- Symbol: **XAUUSD only**
- Entry: confirmed close outside the Asian range
- Stop: Asian-range midpoint
- Nominal target: 3R with trailing management
- Trail: start at +2R, distance 0.5R
- Entry buffer: 3% of Asian range
- ADR filter: Asian range between 5% and 50% of ADR
- Retest window: 4 bars

#### Original optimized sample

| Symbol | Trades | WR | PF | Net R | Max DD |
|---|---:|---:|---:|---:|---:|
| XAUUSD | 18 | 77.78% | 4.48 | +13.90R | 5.30% |
| BTCUSD | 27 | 85.19% | 4.66 | +9.70R | 5.30% |
| EURJPY | 13 | 61.54% | 4.32 | +16.58R | 9.20% |
| GBPJPY | 26 | 84.62% | 4.86 | +8.11R | 5.14% |

#### Frozen configuration on older unseen market time, current MEXAtlantic feed

| Symbol | Dates | Trades | WR | PF | Net R | Max DD | Result |
|---|---|---:|---:|---:|---:|---:|---|
| XAUUSD | 2025-08-02 to 2026-05-02 | 67 | 47.76% | 1.36 | +10.58R | 16.08% | Conditional pass |
| BTCUSD | 2025-08-02 to 2026-05-02 | 117 | 63.25% | 1.10 | +3.66R | 15.53% | Too weak |
| GBPJPY | 2025-08-02 to 2026-05-02 | 97 | 61.86% | 0.98 | -0.48R | 20.49% | Fail |
| EURJPY | 2025-08-02 to 2026-05-02 | 26 | 19.23% | 0.39 | -12.76R | 39.02% | Fail |

#### Frozen different-broker replay, recent period

| Symbol | Dates | Trades | WR | PF | Net R | Max DD |
|---|---|---:|---:|---:|---:|---:|
| XAUUSD | 2026-05-03 to 2026-08-02 | 27 | 74.07% | 3.60 | +18.19R | 5.72% |
| BTCUSD | 2026-05-03 to 2026-08-02 | 39 | 71.79% | 1.80 | +6.39R | 6.08% |
| GBPJPY | 2026-05-03 to 2026-08-02 | 36 | 66.67% | 1.13 | +1.08R | 9.89% |
| EURJPY | 2026-05-03 to 2026-08-02 | 17 | 35.29% | 1.39 | +4.01R | 13.01% |

Decision: keep **XAUUSD only**. Remove EURJPY and GBPJPY. BTCUSD is a forward-watch candidate, not a selected live setup. At the tested 3% risk the older XAU drawdown is too high; use materially lower risk in forward testing.

## 3. DmC

### Selected setup

- Symbol: **XAUUSD**
- Bias: previous daily body
- Confirmation: reaction/retest after the first H4 close
- Exit: trail from +2R at a 1.5R distance
- Maximum hold: 24 hours

| Segment | Dates | Trades | WR | PF | Net R | Max DD |
|---|---|---:|---:|---:|---:|---:|
| Development | 2026-02-03 to 2026-05-02 | 6 | 83.33% | 14.53 | +13.68R | 2.02% |
| Validation | 2026-05-02 to 2026-06-17 | 7 | 57.14% | 2.79 | +5.38R | 2.68% |
| Untouched holdout | 2026-06-17 to 2026-08-01 | 8 | 50.00% | 1.35 | +1.42R | 4.00% |
| Full | 2026-02-03 to 2026-08-01 | 21 | 61.90% | 3.55 | +20.49R | 4.00% |

Decision: provisional only. The untouched edge is positive but has decayed sharply and contains just eight trades. US100 has only eight total trades and is inconclusive.

## 4. AMD

### Original/article model

| Segment | Dates | Trades | WR | PF | Net R | Max DD |
|---|---|---:|---:|---:|---:|---:|
| Development | two-year development window | 76 | 84.21% | 2.18 | +14.25R | 8.73% |
| Frozen untouched year | 2023-07-30 to 2024-07-30 | 43 | 44.19% | 0.12 | -21.15R | 47.81% |

### Best redesign found

- XAUUSD London-only AMD v2 reversal
- Older 2020-2023 stress: 45 trades, 37.78% WR, PF 1.11, +5.00R, 19.42% DD
- Six-year combined: 89 trades, 41.57% WR, PF 1.38, +21.28R, 22.04% DD
- 2022-2023 regime: PF 0.73 and -4R

Decision: **reject for live**. Recent samples look attractive, but the frozen untouched year and one multi-year regime lose heavily. The v2 setup is the best research candidate, not an approved trading setup.

## 5. US100 Weakness

### Best setup found

- NAS100U6
- S2A mode, OCO pending orders, reference-pair entry
- 3R target, one-bar runner trail, 5-point buffer

| Segment | Dates | Trades | WR | PF | Net R | Max DD |
|---|---|---:|---:|---:|---:|---:|
| Development | 2026-06-14 to 2026-07-10 | 14 | 21.43% | 0.87 | -0.65R | 5.93% |
| Validation | 2026-07-12 to 2026-07-20 | 4 | 50.00% | 1.78 | +0.78R | 1.00% |
| Untouched holdout | 2026-07-21 to 2026-07-30 | 3 | 33.33% | 1.48 | +0.48R | 1.00% |
| Full | 2026-06-14 to 2026-07-30 | 21 | 28.57% | 1.09 | +0.62R | 5.93% |

Decision: reject. Positive results in seven later trades do not repair a losing development segment, and the history is too short because the broker's current NAS100 contract began in June.

## Final selection

| Bot | Selected symbol/setup | Status |
|---|---|---|
| EMA3 | XAUUSD H4, pivot 5, EMA200 slope/6, trail 1.5R/1R | Best overall; conditional pass |
| Asia Breakout | XAUUSD confirmed-close, midpoint stop, 3R + trail 2R/0.5R | Conditional pass; lower risk |
| DmC | XAUUSD previous-body + reaction/retest, trail 2R/1.5R | Provisional only |
| AMD | XAUUSD London-only v2 | Research only; rejected for live |
| US100 Weakness | No approved setup | Rejected |

Do **not** run EMA3, Asia Breakout, DmC and AMD on XAU simultaneously as independent 2-3% risks. They share the same underlying instrument and can create hidden correlated exposure. For the next stage, run the selected candidates on demo with one combined XAU risk cap, log every eligible and rejected signal, and require at least 30 frozen forward trades before promoting a setup.

## Software verification

- AMD: 16 tests passed
- Asia Breakout: 14 tests passed
- DmC: 6 tests passed
- EMA3: 12 tests passed
- US100 Weakness: 11 tests passed
- Total: **59 tests passed**

No orders were placed and no live environment was changed during this audit.
