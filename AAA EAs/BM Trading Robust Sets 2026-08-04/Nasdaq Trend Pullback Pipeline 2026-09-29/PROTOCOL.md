# Nasdaq trend-pullback: frozen confirmation protocol

Date: 2026-09-29. Scope: the H1 USTEC trend-pullback hypothesis from the market-style study, not the separately deployed Nasdaq 5-minute EA. Gold is left unchanged. Bitcoin and GBPUSD wait for user review.

## Decision fixed before new tests

The existing Model 1 screen missed the canonical raw gate: PF 1.084 on 3y and 1.135 on 5y; the 3y same-opportunity random-direction control performed better. Overnight carryovers also occurred despite intended intraday exits. Confirm the unchanged original with Model 4 on 3y and 5y, including its frozen control, then decide at stage 4.

Gate: positive net profit, PF >= 1.15, at least 30 closed positions, and mean net R above the control on BOTH 3y and 5y; execution exceptions must also be resolved. A failed gate stops ordinary optimization. The user has been asked whether to override this for explicitly exploratory optimization; absent that instruction do not search parameters or advance to Monte Carlo, prop simulations, production or deployment.

## Unchanged strategy and execution

- Use the exact original MarketStyles.mq5 and compiled EX5, checked against its original BUILD.json; mode 0, H1 closed bars, 400-bar finite EMA initialization.
- Long: EMA50 > EMA200, EMA50 rising versus five bars ago, prior low at/below EMA20, latest close above prior high and EMA20. Mirror for shorts.
- ATR14 arithmetic true-range average; 1.5 ATR initial stop, 3R target. No trailing, breakeven or tuning.
- Next-hour first eligible tick within five minutes; weekdays 07:00-16:59 UTC; one attempt per date and one open position.
- Exit at eight elapsed hours, 20:00 UTC, or five minutes before the broker's reported weekday session end, whichever first becomes actionable. Existing OnTick behavior is retained: no tick means no executable timed close. Do not exclude carryovers from P&L.
- USD 10,000 deposit, nominal 1% equity risk rounded UP to the lot step, minimum-lot rule and native broker specifications. This is not a hard 1% loss cap. Execution delay 150ms, native spread/swap/commission/fees. The tester cannot prove historical broker financing was reproduced perfectly.
- Control uses the original day hash and seed 290929 to randomize direction at the strategy's qualifying opportunities, with reflected stop and target distances. One frozen seed is a diagnostic, not a statistical proof of significance.

## Evidence and safety

- Fresh tests: 3y 2023-09-27 to 2026-09-27 exclusive; 5y 2021-09-27 to 2026-09-27 exclusive; original and control, Model 4. Ninety-day warm-up, no trades before each start.
- Existing 6m and 1y Model 4 evidence will be reused with its provenance, not called fresh or untouched out-of-sample data. Existing Model 1 screens are retained for comparison.
- Model 4 may generate ticks where broker real ticks are unavailable. Record coverage and do not label the entire five-year result real-tick verified.
- Existing safe native runner is reused with only its artifact ROOT redirected here. No strategy or executable changes. New long-window tags did not exist in the previous study before this run. Record runner and dependency fingerprints.
- Only the isolated MT5-DMC-20260811 tester, empty chart profile, disabled live Experts/DLL, local agent, serial execution. No live terminal API, live orders, Ava, terminal restarts, production SET replacement, installer/site edits or push.
- Check inputs, symbol, dates, execution delay, source hashes, deal/report cash reconciliation, closed volumes, no early trades and execution journals.
- Audit carryovers against available same-feed bar and equity trace timestamps. Separate observed quote gaps from inferred holiday/session causes; do not invent fills.
- Results report return, PF, native maximum equity drawdown, closed positions, positions/month, positions/eligible quoted weekday, net win rate and win/loss streaks. Include actual risk and carryover diagnostics.
- No parameter variants or new signals are evaluated in this confirmation phase. The earlier baseline is already seen data; no out-of-sample claim.
