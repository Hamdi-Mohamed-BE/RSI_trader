Nasdaq M5 October-only controlled comparison, generated 7 October 2026.

Open Results.html for the full trade ledger and every successful trailing-stop update.
Effective native window: 1 October 00:00 UTC through 7 October 00:00 UTC exclusive.
Native tester capped the requested end at today's start. Today (7 October) is NOT included.

Current DI ON: 2 entries, 2 natural completed wins, net +$106.66 (+1.0666%), maximum floating drawdown 1.52%.
DI OFF: 3 entries, 2 natural completed wins, one position open at cutoff.
DI OFF closed net +$107.80; cutoff liquidation valuation -$1.68; total +$106.12 (+1.0612%); max floating drawdown 2.38%.
Both natural closed-position win rates are 100% (2/2). The native DI-OFF 66.67% includes the forced cutoff valuation.
Net closed-position PF has no finite value because there are no closed losing positions.
This is far too small a sample to infer a reliable edge or choose a permanent DI setting.

USD 10,000 flat start; 1% equity risk target; standalone adaptive overlay off.
Exact current production EX5 used in both tests. Only InpRequireDIAgreement differs.
Exness USTEC CFD (not exchange NQ futures), real ticks 100%, 150 ms simulated delay.
No fixed TP; 0.60% initial price stop; ATR14 x6 trailing starts at +1R; overnight/weekend positions permitted.
Commission/swap included, bid/ask spread and slippage already reflected in native fills.
No live-account orders or changes; no production, BAT, website or Git changes.

COMPARISON.json: enriched results with UTC/NY/Lagos times, sizing and trailing history.
VERIFICATION.json: independent raw-native-deal reconciliation and actual date-window checks.
HTML-QA.json: offline HTML structural verification.
native/<case>/trades.csv and Parameters.set: original simulated positions and exact applied inputs.
Native report and detailed journal archives are gitignored because native machine/account identifiers may appear.

run.py reuses the existing verified isolated tester harness in the preceding duration-comparison folder.
run_no_di.py executes the single-input DI-OFF comparison; report.py independently reconciles source reports.
