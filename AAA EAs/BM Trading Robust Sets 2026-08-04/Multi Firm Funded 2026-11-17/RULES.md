# Multi-firm funded income — rules frozen 2026-11-17 (before any run)

Owner 2026-11-17: "yes verify the rules and run the combined simulation" (best combination of firms for ~$10k/month with our best EAs).

## Stream (unchanged, no new backtest)
Best 1-Step 11 EAs as installable now (no Sell Nasdaq, + UK100 Monday dip, weekend / holiday flat applied):
`Best 1-Step UK100 Monday 2026-11-11/INPUTS-B1XM.json`, 3,721 native trades 2021-10-07 -> 2026-10-06 with 5-min floating marks.
Parity: total R must equal that study's ledger (418.8 R, 3,721 trades).
R = (gross + commission + swap) / risk at the stop. Floating R at each mark = (mark gross + entry commission) / risk (swap not marked).
Every account risks a FIXED % of its initial size per trade (no guard, no daily stop, no compounding). Accounts of the same type on the
same path take identical trades, so they are 100% correlated; different firms differ only by their rules.

## Official rules read 2026-11-17 (own pages; quotes kept in REPORT.md)
| Type | Size | Challenge | Daily loss | Max loss | Funded split / cycle | Fee (USD) |
|---|---|---|---|---|---|---|
| FTMO 1-Step | 100k | 10%, best day <= 50% of total profit | 3% from 00:00 CE(S)T balance (equity tested) | 10% end-of-day trailing (highest midnight balance), locks at initial | 90%, request from day 14, on demand; consistency 50% gates the reward; reward resets the trailing limit | EUR 499 non-refundable = $579 at an ASSUMED 1.16 |
| FTMO 2-Step | 100k | 10% then 5%, 4 trading days per phase | 5% from 00:00 CE(S)T balance | 10% static | 80%, day 14, on demand | EUR 540 refundable with the first reward = $626 (1.16 ASSUMED) |
| FundingPips 2-Step Standard (5% daily option) | 100k | 8% then 5%, 3 days | 5%, from the higher of day-start balance / equity (third-party; official page silent) | 10% static | 80% bi-weekly, min reward 1% | ASSUMED $550 + 10% Swing add-on (needed to hold overnight on Master) = $605 |
| FundingPips 2-Step Pro | 100k | 6% then 6%, 0 days | 3% from higher of day-start balance / equity (official help) | 6% static | 80% bi-weekly (ASSUMED same as Standard), min 1% | $466 (official home page) + 10% Swing = $513 |
| The5ers High Stakes | 100k | 10% then 5%, 3 profitable days (>= 0.5%) per step | 5% (ASSUMED breach, from higher of day-start balance / equity) | 10% (ASSUMED static) | 80%, bi-weekly from day 14 (third-party) | ASSUMED $495, refund with first payout (page shows "Refund" at step 2) |
| FundedNext Stellar 2-Step | 25k (EAs NOT allowed >= $50k) | 8% then 5%, 5 days per phase | 5% of initial, from higher of day-start balance / equity (ASSUMED) | 10% static | 80%, first after 21 days then every 14 | ASSUMED $200 |

Allocation caps used: FTMO $400k (previously known, the FAQ only mentions "maximum capital allocation"), FundingPips $400k across
evaluation + Master (official help), The5ers High Stakes 1 x $100k (official page), FundedNext: per-trader cap not found -> up to 4 x $25k (ASSUMED).

## Modelling (same for all)
- Day = 00:00 Prague (CE(S)T) for every firm (MT5 server midnight is 1 h later; approximation).
- Each day: breach if min equity (5-min marks) <= floor, or day-start anchor - min equity >= daily limit. Targets / payouts on the
  closed balance at day end. Funded start 3 days after the final pass. A breached slot buys a new challenge the next day (fee charged).
- Payout: every cycle the whole closed profit above the initial size is withdrawn (if >= minimum and the consistency rule holds;
  otherwise retried daily); the balance returns to the initial size. Trader income = split x profit; refunds paid with the first reward.
- Not modelled: news windows (FTMO 2 min, FundingPips 5 min, The5ers 2 min), scaling plans, add-ons other than Swing, payment lag,
  firm discretion / KYC refusals, a new account inheriting that day's open trades (it starts at the day boundary).
- Evidence: MC 1,000 paths x 36 months from random 28-day blocks (seed 20261117) + history (start every 14 days, 36 months).
- Risk grid per type: 0.25 / 0.4 / 0.5 / 0.75 / 1.0 %. In-sample replay; a backtest is not a forecast.
