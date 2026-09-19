import json
from pathlib import Path

OUT=Path(__file__).resolve().parent
d=json.loads((OUT/'results.json').read_text())
r=d['runs']['stressed-stop-check']
money=lambda v:f'${v:,.2f}' if v>=0 else f'-${-v:,.2f}'
integer=lambda v:f'${v:,.0f}' if v>=0 else f'-${-v:,.0f}'

lines=['# $10K FTMO Swing challenge → payout-funded account purchases', '',
 '## Read this first', '',
 'This is a conditional retrospective cash-flow replay, not a forecast, verified FTMO backtest, promised investment return or real account transaction. No account was bought, and no live EA/BAT/website was changed.', '',
 'Window: 5 September 2023 to 31 August 2026 (36 calendar rows; September 2023 and 2026 calendar year are partial). Current screenshot fees/current FTMO rule assumptions are applied counterfactually to historical EA trades. They are not claimed to be the offers or rules in effect in 2023.', '',
 'The new simulated portfolio replaces the previously negative News Pulse XAU with DMC Fresh Reaction US100. BTC News stays excluded. The other nine EAs are unchanged. High win rate is a preference, not a requirement that every retained profitable EA exceeds 50%; this remains a mixed-strategy portfolio.', '',
 'DMC replacement isolated stressed screen: 42 three-year trades, 66.7% win rate, PF 1.56; 82 trades in the source five-year ledger. That is a modest sample and was selected retrospectively. US100 Selective ORB V3 had only 19 executed three-year trades; Nasdaq Overnight lost after stress. Two high-win variants had incomplete commission/swap breakdowns and were not silently treated as cost-free.', '',
 '## Buying and cash rules used', '',
 '- Initial own cash is ONLY the $10K challenge fee, not $10,000 of your own trading capital. No additional external money is added later.',
 '- Until total received trader rewards reach $2,000: after a payout/refund settles, buy one largest affordable offered challenge. Leftovers remain in the wallet. Thus small early rewards can buy additional $10K accounts instead of waiting for a bigger tier.',
 '- At $2,000 cumulative trader rewards, switch to the growth stage. First growth batch is pending until an affordable batch is available; then another batch is eligible per further accumulated $2,500 of trader rewards. Refunds add spendable cash but do not count toward these reward thresholds.',
 '- A growth batch spends UP TO $1,100 of available cash, includes at least one $100K challenge, and adds smaller tiers if that increases the total permitted allocation. Equal capital prefers fewer accounts. Unspent money stays in cash. The first growth batch may be smaller than $1,100 when cash is limited.',
 '- If there is not room for a $100K challenge, further growth batches wait. No unrequested retirement, scaling approval, other prop firm, borrowing or additional registration is assumed.',
 '- Reserve the $400K per-trader/strategy cap for all live challenges, verifications and funded accounts combined. This is conservative relative to funded-only interpretations. A simulated failed account releases its slot. Identical accounts use the SAME market history, not independent random returns.',
 '- Each purchase starts a new evaluation on the next weekday. Initial account starts 5 Sep 2023. Both phases must independently achieve +10% / +5% with four distinct entry days. Two weekdays are allowed for phase transition, five for funded activation/KYC. These are modelling assumptions, not guaranteed FTMO processing times.',
 '- 80% trader share. Keep a 2% initial-capital buffer on each funded account. Claim at month end or the first eligible flat opportunity afterward; at least 14 days after first funded trade / previous claim. All pending orders are assumed cancelled for a claim; their full history is not available.',
 '- Cash arrives four weekdays after the claim. Trading pauses during those four weekdays. The base challenge fee is refunded once with the first settled reward; assumed FX/card costs are not refunded. Holidays, real banking delays, review rejection, taxes and VPS costs are not modelled.', '',
 '## Prices', '',
 'The screenshot shows fees in EUR and trading balances in USD. Conversion held constant at EUR 1 = USD 1.1592 (ECB 11 Sep 2026), plus a separately assumed 2% FX/card allowance. Actual checkout/card charges may differ.', '',
 '| Challenge size | Screenshot EUR fee | USD base fee | FX/card allowance | Cash paid |',
 '|---|---:|---:|---:|---:|']
for size,f in d['fees'].items():
    lines.append(f"| {integer(int(size))} | €{f['eur']:,.0f} | {money(f['usd_base'])} | {money(f['usd_fx_cost'])} | {money(f['usd_paid'])} |")
full_batch=sum(d['fees'][str(s)]['usd_paid'] for s in d['batch_at_full_budget'])
lines += ['',f'With $1,100 cash and sufficient headroom, the maximum face-value batch is $100K + $10K + $10K + $10K = $130K allocation for {money(full_batch)}. This maximizes nominal account size, not probability of survival. Small copied accounts remain correlated and vulnerable to lot rounding.', '',
 '## Trading and risk model', '',
 '- Risk target 0.35% per trade for all ten EAs, including remaining XAG News. Each account independently scales its limits: 1% daily closed-loss gate for non-news, 3% planned-open-risk gate for non-news, 4%/7% drawdown and 3/5 loss-streak tapers. News bypasses adaptive gates/tapers, not broker margin constraints.',
 '- Lot rounding is UP to the 0.01 step, including minimum lot. A small account may therefore risk materially more than 0.35%. Margin and risk are replayed separately at $10K/$25K/$50K/$100K, not scaled from a $100K profit chart.',
 '- One shared balance and simultaneous positions within each account. Model Swing leverage: forex 1:30, indices 1:15, metals 1:9; 20% equity margin reserve; no offsetting hedge-margin credit. Exact current FTMO per-symbol terms remain unverified.',
 '- Official 2-Step loss checks modelled at every trade event and midnight CE(S)T: 5% initial-capital daily equity loss relative to midnight balance; static 10% total-loss floor. Targets require all positions flat. No automatic restart or free funded account after a failure.',
 '- Cash-deal checks do not observe real floating equity. The primary scenario treats a simultaneous planned-stop exposure crossing a limit as a hypothetical failure and stops the account. This is not proof the actual account would have breached.',
 '- The exposure proxy uses full estimated initial stop risk even after trailing, news 1.25x/other 1.10x stress, unpaid commission, 0.15R/0.02R extra execution allowance and a fixed 0.05R carry reserve. Future realized swap is NOT used in entry/margin decisions.',
 '- Execution stress: news gross winners x0.65, losers x1.25, extra 0.15R; regular winners x0.90, losers x1.10, extra 0.02R. Commission floor $7/lot round-trip for metals/FX. Double negative recorded swap and discard swap credits. These are sensitivity assumptions, not an FTMO fee quote or calibrated execution model.',
 '- Source balance reconstructed from source risk cash/configured percentage, to avoid double-compounding existing source backtests. Costs scaled by actual rounded lots. Commission split half at entry/exit, swap booked at close. Same-second round trips ordered entry before exit.', '',
 '## Evidence limitations', '',
 '- Remaining News Pulse XAG source reports only 13% real ticks. Its historical news fills and the resulting payout path are not verified FTMO evidence.',
 '- Saved native MT5 closed-deal ledgers lack continuous bid/ask equity, original SL histories, all pending orders and account-specific historical FTMO costs. Model failures can overstate actual losses after trailing; gaps can also exceed planned stops. Closed-only survival can miss real intraday breaches.',
 '- Selection uses knowledge of the full historical period. Cached strategy settings were optimized retrospectively. This is not an out-of-sample business forecast and reinvestment magnifies source-model errors.',
 '- Today\'s fixed prices, USD conversion and simplified weekday delays are deliberately explicit assumptions. Small timing or pricing changes can alter which challenge is bought and when, changing later outcomes.',
 '- No probability of achieving the final cash amount is claimed. Repeated trades across copied accounts are not independent observations. Do not count simulated account allocations as personal wealth.', '',
 '## Overall real-cash ledger — conservative stress scenario', '',
 '| Item | USD |', '|---|---:|',
 f"| External cash initially required | {money(r['initial_external_cash'])} |",
 f"| Trader rewards actually settled in the model | {money(r['rewards_received'])} |",
 f"| Challenge fees paid, including FX allowance | {money(r['fees_paid'])} |",
 f"| Base challenge fees refunded | {money(r['fee_refunds_received'])} |",
 f"| Unrefunded fees on failed accounts | {money(r['failed_unrecovered_fees'])} |",
 f"| Non-refundable FX/card assumptions, all purchases | {money(r['fx_card_cost'])} |",
 f"| Total unrecovered cost | {money(r['unrecovered_costs'])} |",
 f"| Net cash profit = rewards + refunds − all fees paid | {money(r['net_real_cash_profit'])} |",
 f"| Cash wallet = original seed + net cash profit | {money(r['cash_final'])} |",
 f"| Further requested rewards not settled by the cutoff; excluded above | {money(r['pending_rewards'])} |", '',
 f"{r['accounts_purchased']} challenges bought; {r['accounts_failed']} hypothetical failures; {r['accounts_funded_now']} funded accounts surviving, with {integer(r['funded_capital_now'])} simulated allocation. That allocation is NOT withdrawable cash.", '',
 'All seven flagged failures are $10K accounts on 9 January 2026. Four had already received fee refunds; three had not. The three unrecovered base fees total $344.28. Do not subtract this again from net cash: the fees were already counted when purchased.', '',
 '## Yearly cash breakdown', '',
 '| Year | Rewards received | Fees paid | Fee refunds | Failed fees not recovered | Net cash profit | Wallet at year end | Failures | Funded capital at year end |',
 '|---|---:|---:|---:|---:|---:|---:|---:|---:|']
for year,m in r['yearly'].items():
    lines.append(f"| {year} | {money(m['rewards'])} | {money(m['fees_paid'])} | {money(m['refunds'])} | {money(m['failed_unrecovered_fees'])} | {money(m['net_cash'])} | {money(m['cash_end'])} | {m['failures']} | {integer(m['active_funded_capital'])} |")
lines += ['', '2023 covers Sep–Dec; 2026 covers Jan–Aug. Fees on accounts later failed are recognised as unrecovered when failure occurs, but this is not a second cash payment.', '',
 '## Monthly cash breakdown', '',
 '| Month | Rewards received | Fees paid / invested | Fee refunds | Net real cash | Wallet end | Accounts bought | Failures | Funded allocation end |',
 '|---|---:|---:|---:|---:|---:|---:|---:|---:|']
for m in r['monthly']:
    lines.append(f"| {m['month']} | {money(m['rewards'])} | {money(m['fees_paid'])} | {money(m['refunds'])} | {money(m['net_cash'])} | {money(m['cash_end'])} | {m['purchased']} | {m['failures']} | {integer(m['active_funded_capital'])} |")
lines += ['', '## Individual account lifecycle', '',
 '| ID | Size | Purchased | Fee paid | Funded activation | End status | Refund received |', '|---|---:|---|---:|---|---|---|']
for a in r['accounts']:
    funded=a['result']['funded_at']
    status='Failed stop-exposure scenario 2026-01-09' if a['status']=='failed' else a['status']
    lines.append(f"| {a['id']} | {integer(a['size'])} | {a['bought_at'][:10]} | {money(a['fee_total'])} | {funded[:10] if funded else 'Not funded'} | {status} | {'Yes' if a['refund_received'] else 'No'} |")
lines += ['', '## Sensitivity: same reinvestment policy, different execution/breach assumptions', '',
 '| Scenario | Net cash profit | Modelled failures | End funded allocation |', '|---|---:|---:|---:|']
for k,v in d['runs'].items():
    lines.append(f"| {k} | {money(v['net_real_cash_profit'])} | {v['accounts_failed']} | {integer(v['funded_capital_now'])} |")
lines += ['', 'The recorded-fill reference is optimistic and is NOT the recommended expectation. Differences are not statistical confidence intervals: they demonstrate model sensitivity.', '',
 '## EA contributions in a separate constant-$10K funded-start check', '',
 'This verifies the replacement at the small account size; it is NOT the reinvestment wallet. Payout pauses and account-wide controls are active.', '',
 '| EA | Closed trades | Net simulated P/L | Win rate | PF |', '|---|---:|---:|---:|---:|']
for a in d['ten_k_same_account_ea_contributions']:
    lines.append(f"| {a['name']} | {a['closed']} | {money(a['net'])} | {a['win_rate']:.1f}% | {a['pf']:.2f} |")
paper_losses=sum(m['gross_losing_trades'] for m in r['monthly'])
paper_net=sum(m['simulated_trading_net'] for m in r['monthly'])
lines += ['',f"Across all copied evaluation/funded accounts the replay records {sum(m['closed_trades'] for m in r['monthly']):,} closed trades, {money(paper_losses)} gross losing-trade P/L and {money(paper_net)} net simulated trading balance flow. These are fictitious-account trading amounts, not personal cash losses or income. Only settled rewards/refunds minus paid fees enter the cash ledger.", '',
 '## Validation', '',
 '12 deterministic tests passed: seed fee basis, batch budget/headroom, cash/month/year reconciliation, allocation cap, settlement after funding, new phase requirements, correlated failures, once-only refunds, minimum-lot rounding and account-size loss thresholds. Every account replay also checks accounting identities and no orphan/post-failure trades.', '',
 '## Sources checked 13 September 2026', '',
 '- User-provided screenshot: €99/€279/€379/€599/€1,080 fees for $10K/$25K/$50K/$100K/$200K accounts.',
 '- [FTMO maximum allocation](https://ftmo.com/faq/how-many-accounts-can-i-have/)',
 '- [FTMO 2-Step evaluation objectives](https://ftmo.com/en/trading-objectives/)',
 '- [FTMO rewards, timing and profit share](https://ftmo.com/en/faq/how-do-i-withdraw-my-profits/)',
 '- [FTMO fees/refund](https://ftmo.com/faq/are-the-fees-recurrent/)',
 '- [ECB EUR/USD reference rate](https://www.ecb.europa.eu/stats/policy_and_exchange_rates/euro_reference_exchange_rates/html/index.en.html)',
 '- [FTMO published Swing leverage by asset class](https://ftmo.com/en/blog/a-few-answers-to-your-questions/)', '',
 'Recommendation: validate the replacement and news fills on full FTMO tick evidence before treating this as an investment plan. Compare waiting for larger tiers against repeatedly buying $10K accounts; the latter maximises early nominal allocation but produced concentrated small-account failures in this stress scenario.']
(OUT/'REPORT.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
print('REPORT.md saved')
print('NET',money(r['net_real_cash_profit']),'FEES',money(r['fees_paid']),'FAILED FEES',money(r['failed_unrecovered_fees']))
