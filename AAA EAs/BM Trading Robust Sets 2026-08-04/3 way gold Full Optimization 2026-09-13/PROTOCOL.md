# 3 way gold — parameter optimization protocol

Declared 2026-09-13 before search results. Raw evidence is preserved in the sibling Raw Research folder. All work is research/tester only: no live attachment, account switches, BAT/website edits, or Git push.

## Selection and validation

Development: 2021-09-05 through 2024-09-05 exclusive. Validation: 2024-09-05 through 2025-09-05. Locked diagnostic: 2025-09-05 through 2026-09-05. The raw strategy's aggregate history was already viewed, so these are chronological research splits, NOT pristine unseen out-of-sample data.

1. Check parameterized EA defaults against the complete native raw six-month trade ledger. Fail closed on any discrepancy.
2. Cache broker M1 and H1 history read-only. Independently verify EMA, ADX/DI, RSI and ATR against native exported decisions.
3. Deterministic broad randomized discrete parameter search, 1,536 configurations per engine plus the raw baseline, then one-at-a-time neighborhood refinement around train-only leaders. This is a bounded broad search, not exhaustive enumeration of all possible parameter combinations. Search counts and every candidate are saved.
4. Screening uses conservative M1 OHLC simulation: SL before TP if both occur in a minute, gap stop at first executable price, bid/ask spread, fixed contract100, round-UP/minlot0.01, current per-lot commission and swap estimates. Those are APPROXIMATE rankings, not MT5 results. Management uses only the previous completed H1 bar, never the current minute high to move a stop retroactively.
5. Build shared-account three-engine combinations (matching global ATR/direction/management settings), compare train and validation, and send four finalists to native MT5 Model4 on both splits. Include the raw settings as a control. Pick a eligible finalist on the worse split score, not highest total return. If none qualifies, label the best exploratory candidate rejected rather than falsely recommended.
6. Freeze selected settings before the final diagnostic. Native selected versus raw for 6m/1y/3y/5y/2019–2026. Native execution-delay stresses: 100ms and 500ms on the locked period. Extra round-trip spread/slippage/commission sensitivity and 1,000 block-bootstrap equity paths are diagnostics, NOT a substitute for tick/prop-firm testing.
7. Verify source hashes, trade/fee totals, decision/entry causality, one position per engine, risk overshoot, equity DD, and true tick coverage. Save EA, research sets, all search evidence and report. No settings are modified after seeing the locked diagnostic.

## Search space

- Common direction: both / long-only / short-only; ATR14 alternatives10/20.
- Momentum pullback EMA10/20/30; fast trend EMA30/50/75; slow100/150/200/300; ADX length10/14/20 and threshold15/20/25/30/35.
- Trend change fastEMA5/9/13; slowEMA21/34/55; RSI length7/14/21; symmetric confirmation threshold50/55/60.
- Breakout lookback10/20/30/55; true-range expansion1.0/1.25/1.5/2.0 ATR; risingATR off/on.
- Stops1.0/1.5/2.0/2.5/3.0 ATR; targets0.5/0.75/1/1.5/2/3R.
- Management: fixed / break-even / H1-close ATR trailing / both. Trigger0.75/1/1.5R; trailing1/1.5/2/3ATR. TP remains present. No martingale or new external filters.
- Nominal equity risk0.30% per engine during signal selection. Combined allocation masks may disable engines for diagnosis, but the main three-engine candidate retains all three. Separate allocation/risk sensitivities0.15/0.30/0.50% are reported; increasing risk is not evidence of a stronger signal.

Train screen score favors log PF, return-to-drawdown, sufficient trades, and positive annual subperiods. Native eligibility: positive net P/L and PF>1.05 in both splits, at least60 development and20 validation trades, max equity DD<=20% in both, no stopout. Native rank is the lower split score; target higher sample counts rather than cherry-picking a few wins. Parameter selection cannot guarantee future profitability.

## Data and cost limits

Connected broker expected Exness-MT5Trial16 Zero demo, $10K test starts, leverage1:2000. Original server credentials stay in existing isolated terminal configuration. Native real tick coverage begins2026-01-01; earlier missing real ticks are generated. One-millisecond baseline delay is optimistic. Native fee/swap schedules are the loaded tester conditions, not a historical broker fee/leverage reconstruction. No FTMO pass/payout assertion is authorized.

References: [MT5 optimization and forward testing](https://www.metatrader5.com/en/terminal/help/algotrading/strategy_optimization), [MT5 testing limitations](https://www.metatrader5.com/en/terminal/help/algotrading/testing_features). Engine motivation and creator limitations remain in the raw RULES.md. The online sources do not supply universally best parameter values.
