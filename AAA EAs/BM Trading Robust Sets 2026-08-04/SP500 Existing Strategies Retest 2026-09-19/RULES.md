# S&P 500 existing-EA transfer test — frozen scope

Research only. No live installation, trading, website/BAT changes, or optimization.

Test the 12 distinct active presets comprising all seven active ORBs and five other US100 strategies. Archived/unpromoted experiments and alternative optimization passes are not active EAs and are not included. The current Recommended selection for Sell Nasdaq is its dedicated Dynamic Exit preset.

Use the currently connected normal account, dynamically resolve its standard S&P 500 contract, and reject a changed account. Current discovery: Exness-MT5Trial16 Zero demo; US500 (not US500_x100). Window 2025-09-19 inclusive through 2026-09-19 exclusive. Each test is independent, USD 10,000, original chart timeframe, saved base risk 1%, current account leverage, native Model 4, fixed 150 ms execution delay. These are not a shared-account portfolio or adaptive-governor simulation.

Preserve all entry/exit/stop/target/trailing/filter thresholds and risk settings. Only the traded chart symbol and historical server clock are mapped to this broker. In DMC, InpTesterServerClockMode=0 and InpResearchBrokerUtcOffsetMinutes=0 preserve the intended UTC session on Exness history. Do not optimize absolute point/pip thresholds for the new asset. Adaptive controls retain their original standalone false default. No 0.25 Nasdaq portfolio allocation is added to the saved standalone preset.

Compile tester-only audit wrappers which include original EA sources unchanged. Instrument equity but do not intercept or alter orders. Save source/include/SET/build hashes, native report, exact inputs, journal, parsed trades, commissions, swaps, monthly returns and equity drawdown. Assert report inputs match the tested SET and net cash flows reconcile with final balance.

Broker bid/ask spread and native reported commissions/swaps are included. Execution delay is a modeled stress, not measured live slippage. Model 4 can synthesize ticks outside real history: report actual coverage and warnings. Current earlier tests on this account reported 71% real-tick quality with real ticks starting January 2026. Do not market this as a full year of real ticks.

Report maximum floating-equity drawdown as the larger of native relative equity DD and the wrapper tick-observed DD; retain both. Count trade wins/PF net of costs. Break-even trades after fees may be losses. Keep raw existing rules even if the transfer performs badly. Results do not authorize deployment.

Gold overnight Value Area full pipeline is the next phase, not part of this transfer test. It must not enter the live system before full validation and an explicit promotion decision.
