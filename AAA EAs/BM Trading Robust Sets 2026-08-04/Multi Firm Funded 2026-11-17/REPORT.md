# Multi-firm funded income for ~$10k/month (2026-11-17)

Rules and assumptions are frozen in RULES.md. Code: sim.py (days | run [cost] | combos [cost]) and mix.py.
Results: TYPES.json, TYPES_cost0.05.json, COMBOS*.json, MIXES.json.

Stream: the Best 1-Step 11-EA weekend-flat ledger (3,721 trades, 2021-10 → 2026-10, 62.1/month, 2.96/day).
Parity: 418.8 R, exact match with the source study.

Method: Python replay with 5-minute floating marks, no guard, risk as a fixed % of the initial balance. 1,000 Monte Carlo paths over 36 months.
- Each slot buys a new challenge after a breach.
- All profit is withdrawn every cycle.
- In-sample; a backtest is not a forecast.

## Official rules verified 2026-11-17
- **FTMO** (ftmo.com trading-objectives, how-it-works, FAQ):
  - 1-Step: 10% target, 3% daily from the 00:00 CE(S)T balance, 10% end-of-day trailing max loss, 50% consistency, 90% split, reward from day 14. Fee EUR 499, non-refundable.
  - 2-Step: 10% / 5% targets, 5% daily, 10% static, 4 trading days per phase, 80% split. Fee EUR 540, refundable.
  - Funded Standard accounts may not hold through breaks of more than 2 hours, and have a 2-minute news window.
  - EAs are allowed.
  - $400k per-trader cap: from earlier knowledge, not on the pages read.
- **FundingPips** (fundingpips.com/trading-objectives, help centre):
  - 2-Step Standard: 8% / 5% targets, 3% or 5% daily, 10% max loss.
  - 2-Step Pro: 6% / 6% targets, 3% daily, 6% max loss. Fee $466.
  - Master accounts need a +10% Swing add-on to hold overnight or over weekends.
  - News: no opening or closing within 5 minutes of high-impact news.
  - Split: 80% bi-weekly (minimum 1%), or 100% on demand with a 35% consistency rule.
  - EAs: your own EA is allowed for full automation if you can prove ownership (source code). Third-party EAs may only manage trades or risk.
  - Cap: $400k across evaluation and Master accounts.
- **The5ers** (the5ers.com):
  - High Stakes: 10% / 5% targets, 5% daily, 10% max loss, 3 profitable days of at least 0.5% per step, 80% split and up.
  - Only one $50k or $100k account per trader.
  - News: no trades in the 2 minutes either side of high-impact news.
  - Hyper Growth tops out at $50k (not $100k as earlier assumed).
  - EA policy, payout timing and the daily-loss basis were NOT found.
- **FundedNext** (help.fundednext.com):
  - **EAs are not permitted on accounts of $50k or more**, so only accounts under $50k (largest $25k) are usable.
  - Stellar 2-Step: 8% / 5% targets, 5% daily, 10% static max loss, 80% split.
  - 1-Step: 3% daily, 6% static.
- **Not confirmed:** the FundingPips Standard $100k price ($550 assumed), The5ers High Stakes $100k price ($495 assumed), the FundedNext $25k price ($200 assumed) and the FundedNext account cap.

## Per account (MC 36 months, best risk per firm)

| Account ($100k) | Risk | Fee per attempt | Attempts in 36 m | Fees in 36 m | Funded breaches | First payout (median day) | Net per month (median) | Net per month (+0.05R cost) |
|---|---|---|---|---|---|---|---|---|
| FTMO 1-Step | 0.5% | $579 | 1.63 | $943 | 0.55 | 134 | $2,755 | $1,316 |
| FTMO 2-Step | 0.75% | $626 (refundable) | 2.82 | $1,766 | 1.54 | 111 | $3,563 | $1,639 |
| FundingPips 2-Step Standard | 0.75% | $605 (incl. Swing) | 2.94 | $1,782 | 1.68 | 102 | $3,610 | $1,721 |
| The5ers High Stakes | 0.75% | $495 (refundable) | 2.83 | $1,400 | 1.55 | 111 | $3,562 | $1,649 |
| FundingPips 2-Step Pro (6% max loss) | 0.5% | $513 | 3.53 | $1,809 | 2.06 | 132 | $2,148 | $837 |
| FundedNext 2-Step $25k | 0.75% | $200 | 2.87 | $574 | 1.59 | 107 | $894 | $423 |

At 1% risk the 2-Step-style accounts earn more ($4.4k–4.6k), but they need 6.7–6.9 attempts and 4 funded breaches in 3 years.
FTMO 1-Step at 0.75% or more is worse, because its 3% daily limit and trailing max loss breach often.
Fees in 36 m are gross; refunds are paid back with the first reward.

## Combinations (MC, 36 months)

| Mix | Capital | Net per month median (p10–p90) | P(36-month average ≥ $10k) | Year 1 per month | Months with no payout | Upfront fees | Fees in 36 m | +0.05R cost: median, P(≥ $10k) |
|---|---|---|---|---|---|---|---|---|
| A: 2 FTMO 1-Step + 2 FP Std + 1 The5ers, all 0.5% | $500k | $12,731 ($8,995–16,784) | 83% | $9,724 | 24% | $2,863 | $4,236 | $6,099, 11% |
| B: 1 FTMO 2-Step + 1 FP Std + 1 The5ers, all 0.75% | $300k | $10,718 ($7,332–14,304) | 60% | $8,821 | 26% | $1,726 | $4,948 | $5,013, 3% |
| **C: 2 FTMO 1-Step 0.5% + 1 FTMO 2-Step + 1 FP Std + 1 The5ers 0.75%** | $500k | **$16,227 ($11,218–21,596)** | **95%** | $13,194 | 25% | $2,884 | $6,834 | $7,619, 28% |
| D: 2 FTMO 1-Step 0.5% + 2 FTMO 2-Step + 4 FP Std + 1 The5ers 0.75% | $900k | $30,693 | 99.8% | $25,171 | 25% | $5,326 | $13,946 | $14,443, 77% |

- Per firm for C:
  - FTMO: 3 accounts, $1,784 upfront, 6.1 attempts, $3,652 in fees.
  - FundingPips: 1 account, $605 upfront, 2.9 attempts, $1,782.
  - The5ers: 1 account, $495 upfront, 2.8 attempts, $1,400.
- All accounts trade the same EAs, so months are correlated: about 1 month in 4 pays nothing in any mix.
- The edge is thin. At +0.05R extra cost per trade (about half the +0.11R edge), income roughly halves.

Not modelled:
- news windows;
- scaling plans;
- payment lag;
- firm discretion, or reviews of identical EA trading across accounts;
- the The5ers daily-loss basis (assumed a breach);
- a new account inheriting open trades.

## Addendum 1 (2026-11-17): no-opposite-trade rule
Trigger: FundingPips support (signed "AI Support Assistant") replied that a buy and a sell on the same symbol is forbidden hedging, with no
exceptions, even when the two trades come from independent strategies. It is checked at the end of the evaluation and before every reward.

The current stream has this overlap on 262 days (313 trades).

Rule tested (nohedge.py): going through the trades in open order, skip a trade when an accepted trade on the same symbol in the opposite
direction is still open. 0 overlaps remain.

Effect on the stream:
- Trades: 3,721 → 3,428 (293 skipped, 57.1/month, 2.72/day).
- R: 418.8 → 406.2. PF: 1.291 → 1.305.
- Worst intraday equity: −5.04R → −5.51R (the opposite trades had acted as a partial hedge).

Skipped per EA:

| EA | Skipped | R of the skipped trades |
|---|---|---|
| Overnight Bias ORB | 120 | −7.1 |
| XAU RSI VWAP | 93 | +10.6 |
| ORB VP Volume Confirmed | 35 | +13.2 |
| Gold Band Wave | 18 | −6.6 |
| US100 Selective ORB V3 | 11 | +2.5 |
| Other EAs | ≤ 8 each | — |

Nasdaq 5M, USDJPY London and UK100 Monday are never skipped.

Per account, net per month median (as installed → no-opposite rule):

| Account | Net per month | Attempts in 36 m |
|---|---|---|
| FTMO 1-Step 0.5% | $2,755 → $2,664 | 1.63 → 1.75 |
| FTMO 2-Step 0.75% | $3,563 → $3,377 | 2.82 → 3.28 |
| FP Standard 0.75% | $3,610 → $3,445 | 2.94 → 3.40 |
| The5ers HS 0.75% | $3,563 → $3,380 | 2.83 → 3.27 |
| FP Pro 0.5% | $2,148 → $1,906 | — |

Mixes (no-opposite rule):

| Mix | Net per month median | P(36-month average ≥ $10k) | Fees in 36 m | +0.05R cost: median, P(≥ $10k) |
|---|---|---|---|---|
| A | $12,300 | 78% | $4,496 | — |
| B | $10,202 | 53% | $5,735 | — |
| C | $15,485 | 91% | $7,757 | $7,861, 29% |
| D | $29,225 | 99.8% | $15,987 | $14,770, 76% |

Months with no payout: about 28%.

The rule is NOT built into the EAs yet. It needs:
- a shared entry check across all magics on the account;
- deleting or cancelling pending orders that would fill against an opposite position.

Results: TYPES_nohedge*.json, MIXES_nohedge.json, NOHEDGE.json.

## Addendum 2 (2026-11-17): fewer gold EAs, chosen on the last 12 months (owner)
Rules were fixed before any simulation (gold.py). The four non-gold EAs all stay. The no-opposite rule is applied after the EA filter.

Last year = 2025-10-06 → 2026-10-06. Choosing on that year is HINDSIGHT; the same year is inside every result below.

| Version | Gold EAs dropped | EAs | 5 y trades | 5 y R | 5 y PF | Last year: trades, R, PF |
|---|---|---|---|---|---|---|
| ALL11 + no-opposite | — | 11 | 3,428 | 406.2 | 1.305 | 635, 111.9, 1.49 |
| G6 (last-year R > 0) | Gold Band Wave | 10 | 3,199 | 405.0 | 1.325 | 596, 118.3, 1.56 |
| G4 (PF ≥ 1.25) | + RSI VWAP | 9 | 3,017 | 393.6 | 1.330 | 565, 118.7, 1.59 |
| G3 (R/trade ≥ 0.10) | + EMA3 | 8 | 2,828 | 385.0 | 1.339 | 526, 113.6, 1.60 |

Effect on the accounts:
- Fewer gold EAs means fewer breaches. FTMO 1-Step at 0.75% becomes usable on G3: $3,739/month with 3.1 attempts (11 EAs: 8.4 attempts).
- G3 worst intraday equity: −4.0R (11 EAs: −5.5R).

Mixes (MC, 36 months):

| Version | Mix | Net per month median | P10 | P(≥ $10k) | Attempts | Fees | +0.05R cost: median, P(≥ $10k) |
|---|---|---|---|---|---|---|---|
| ALL11 | C | $15,485 | $10,361 | 91.3% | 13.4 | $7,757 | $7,861, 29% |
| G3 | C | $15,125 | $10,727 | 93.6% | 8.9 | $5,128 | $8,481, 35% |
| G3 | E (all 5 accounts at 0.75%) | $17,494 | $12,168 | 97.6% | 12.5 | $7,226 | $9,642, 47% |
| G6 | E | $17,657 | $12,088 | 96.6% | 17.4 | $10,059 | $8,971, 40% |

Results: GOLD.json, GOLD_MIXES.json, TYPES_G*.json, MIXES_G*.json.

## Addendum 3 (2026-11-17): owner roster, now the Best 1-Step profile (9 EAs)
EMA3 and RSI VWAP kept; Gold Band Wave and XAU Squeeze removed (b9.py).

Stream:

| Version | Trades (per month) | R | PF | Last year: trades, R, PF | Worst intraday equity |
|---|---|---|---|---|---|
| B9 as installed | 3,310 (55.2) | 393.1 | 1.303 | 627, 117.4, 1.53 | −4.3R |
| B9NH (no-opposite rule) | 3,077 (51.3) | 375.7 | 1.309 | 579, 115.6, 1.56 | −4.8R |

Per account, as installed:

| Account | Net per month | Attempts in 36 m |
|---|---|---|
| FTMO 1-Step 0.5% | $2,594 | 1.3 |
| FTMO 1-Step 0.75% | $3,587 | 4.4 |
| FTMO 2-Step 0.75% | $3,372 | 2.2 |
| FP Standard 0.75% | $3,437 | 2.3 |
| The5ers HS 0.75% | $3,375 | 2.2 |

Mixes (MC 36 months; Mix F = 2 FTMO 1-Step + 2 FTMO 2-Step + The5ers HS at 0.75%, no FundingPips):

| Mix | Version | Net per month median | P(≥ $10k) | Attempts | Fees | +0.05R cost |
|---|---|---|---|---|---|---|
| E | B9 | $17,302 | 96.2% | 15.6 | $9,027 | $8,233 |
| F | B9 | $17,236 | 96.2% | 15.6 | $9,040 | — |
| C | B9 | $15,435 | 94.7% | 9.4 | $5,431 | — |
| E | B9NH | $16,096 | 93.9% | — | — | — |

Results: B9.json, B9_MIXES.json, TYPES_B9*.json.

## Addendum 4 (2026-11-17): cost, return and time to get funded (9-EA Best 1-Step as installed, MC 36 months)
sim.py now records each slot's first funded day (same seed; the other numbers are unchanged). Results: TYPES_B9*.json (funded_within,
first_funded_day_*), B9_TIMING.json.

Per account (median days from purchase):

| Account | Funded | Funded ≤ 60 / 90 / 180 d | First payout | Net per month |
|---|---|---|---|---|
| FTMO 1-Step 0.75% | 59 d | 52 / 77 / 98% | 117 d | $3,587 |
| FTMO 1-Step 0.5% | 92 d | — | — | — |
| FP Standard 0.75% | 81 d | — | — | — |
| FTMO 2-Step 0.75% | 96 d | — | — | — |
| The5ers HS 0.75% | 96 d | — | — | — |
| FTMO 2-Step / The5ers 0.5% | 142 d | — | — | — |

History starts (2021-23 included) are slower: FTMO 1-Step 0.75% median 82 d, 2-Step 116 d.

Mix F (2 FTMO 1-Step + 2 FTMO 2-Step + The5ers at 0.75%):

| Measure | Base | +0.05R cost |
|---|---|---|
| Upfront fees | $2,905 | — |
| Fees in 36 months | $9,040 | $16,438 |
| Most cash out at once | median $2,905, p90 $5,811 | $4,063 |
| Break-even | month 4 | month 6 |
| First account funded | 59 d (p25–p75 39–87) | 87 d |
| All five funded | 96 d | 149 d |
| First payout | 105 d | 158 d |
| Year-1 net | median $168k (p10 $60k) | $66k |
| 36-month net | median $620k (p10 $424k, p90 $828k) | $293k (p10 $135k) |
