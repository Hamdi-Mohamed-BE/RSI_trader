# Four-month extension: raw Gold plus XAU/XAG News on $10K Swing

Research only. No native tester run, account connection, orders, deployment, website or BAT changes.

## Primary comparison

The requested four-month window is interpreted as **19 May 2026 inclusive through 18 September 2026**, end exclusive 19 September: 123 calendar days. Start fresh with $10,000, one attempt. It is not a claim about unobserved trading after September.

Keep exactly the preceding study's primary configuration: raw Gold Overnight Value Area $100 target initial stop risk; News Pulse XAU and XAG $10 per pending order each, both directions retained. Fixed-reference dollar sizing, rounding up to 0.01 lots, $200 new-entry daily closed-loss gate, $200 planned-open-risk cap, 80% conservative-equity margin ceiling. Global Swing gold/silver 1:15; full gross margin reserved for both pending sides with no hedge relief. Trading rules and parameters are not optimized again.

FTMO numerical assumptions are unchanged: Phase 1 +10%, Phase 2 +5%, four distinct Prague entry days per phase, flat before transition, $500 daily equity-loss allowance relative to Prague midnight balance, $9,000 static equity floor; balance resets between phases. No 1-Step Best Day rule. Two business days to Verification, five to funded activation, 14 calendar days from first funded trade before request, 80% first reward share, four business days from request to modeled receipt. Administrative delays are assumptions, not guarantees. Stop the evaluation path at the first payout request or a modeled breach; do not treat its ending balance as continued trading through September. Challenge fee/refund and taxes are not included.

Source fills and paths remain saved Exness native MT5 tests, not FTMO. Reference retains recorded spread and fees. Stress uses the independent 250ms native news run plus the same extra adverse-price and commission assumptions as the two-month study. Floating-equity checks remain minute/second adverse-mark proxies, not exact synchronized FTMO equity. The underlying model and its two-month results are regression-tested before extending the date range.

## Resampling

Primary four-month estimate: 1,000 joint weekly-block bootstrap paths, deterministic seed 20260919. Retain all three EAs, same-event news legs, and within-week timing together. The partial first week, 19–22 May, is included in the historical replay but excluded from the bootstrap source pool. Source pool is the 17 complete Monday–Friday trading weeks 25 May–18 September. Eighteen sampled calendar weeks are placed beginning Monday 18 May, then clipped to the exact Tuesday 19 May–Saturday 19 September window. There are no source positions or pending orders crossing a week boundary. End-of-horizon trades are checked for correct entry/exit matching.

The reference and stress runs use exactly the same sampled week indexes. Bootstrap percentages describe the model and observed sample, NOT calibrated probabilities of future funding or payout. Only eleven macro release dates occur in the full four-month sample. News settings were fitted on the same year, including these four months. These are not 1,000 independent real challenges.

Report the old two-month percentages alongside the new four-month ones, with the explicit caveat that both horizon AND historical sample change. Also run a clearly labeled horizon-only sensitivity using the original nine-week July–September pool resampled to 123 days; this changes the available time without introducing earlier May/June patterns. Preserve New York within-week wall-clock schedules through the synthetic autumn daylight-saving transition. It remains synthetic, not observed future performance.

Numerical target success does not ensure FTMO approval or reward eligibility. The exact pre-news straddle design needs FTMO confirmation because Swing's permission to trade news does not override the separate forbidden-practices rules. No approval probability is assigned.

## Official references, rechecked 19 September 2026

- https://ftmo.com/en/trading-objectives/
- https://ftmo.com/en/faq/how-do-i-withdraw-my-profits/
- https://ftmo.com/en/faq/ftmo-swing-account-type/
- https://ftmo.com/en/forbidden-trading-practices/
- https://ftmo.com/en/blog/trading-updates/trading-update-2-feb-2026/
- https://ftmo.com/en/blog/trading-updates/trading-update-7-may-2026/
