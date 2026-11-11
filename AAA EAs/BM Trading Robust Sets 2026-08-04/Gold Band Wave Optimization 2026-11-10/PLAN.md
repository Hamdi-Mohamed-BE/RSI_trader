# Gold Band Wave (XAUUSD): optimisation plan, frozen 2026-11-10 before any result

**Owner request (2026-11-10):** optimise every strategy added today.
- The current raw version stays active, unchanged, in the P4 BATs and on the website.
- Any result here is a research candidate until the owner decides.

**Data split:** `data_split.research_split('2019-01-01', '2026-11-11')`.
- Development: 2019-01 to 2023-11.
- Validation: the following 12 months, to 2024-11.
- OOS: the last 2 calendar years. It was previously seen in the raw study, so it is not untouched.

**Engine:** `../research_opt_engine.py`, the same method as the other searches. Every run is recorded in RUNS.jsonl.
- **Research EA:** `EA/Gold Band Wave Research EA.mq5` is built by `build_ea.py` from the raw EA with asserted edits. All defaults equal the raw rules.
- **Parity:** before any search, the defaults must reproduce the raw ledger (`nw-XAUUSD-GBW-all`, 455 trades) trade for trade.
- **Screening:** native Model 1. Finalists are confirmed in Model 4, and Model 4 decides every gate.
- **Run settings:** $10k, 1% risk, 150 ms delay.

**Staged search, top 3 settings carried forward per stage:**
1. Timeframe: H1 / H4 / D1.
2. Bollinger lengths: short 10 / 20 / 30 x long 40 / 50 / 100.
3. Deviation: 1.5 / 2 / 2.5.
4. Signal SMA: 5 / 9 / 14 / 21.
5. Trend SMA: off / 100 / 200.
6. Stop: 1 / 1.5 / 2 / 3 / 4 x ATR(14).
7. Target: none / 1 / 2 / 3 / 4 / 6 R.
8. Exit on the opposite cross: yes / no.
9. Management: static; break-even at 1 R; ATR trail of 2 / 3 / 4 x ATR once the trade is 1 R in profit.
10. Direction: long only / short only / both.

**Development score:** return / equity drawdown, with PF >= 1.15, >= 100 trades and positive return.

**Gates:** the same as the Overnight Bias ORB plan: plateau >= 70%, validation once, OOS once, and three-way Monte Carlo (resample red <= 5%, randomize red <= 10%). Buy and hold XAUUSD is shown alongside.
