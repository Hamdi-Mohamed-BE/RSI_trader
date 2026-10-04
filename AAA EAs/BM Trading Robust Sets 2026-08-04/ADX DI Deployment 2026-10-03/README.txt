CALYX ADX / DI user-selected release - 3 October 2026

Selected entries: EMA3 ADX14 >=25 H4; Asia DI14 H1; USDJPY London
ADX14 >=20 and DI M15; Trend Progression DI14 H4. RSI VWAP unchanged.
Indicators use the last completed bar. Failed indicator reads block new entries,
never protective exits. Risk, adaptive controls, news policy and exit targets
remain the separate choices in each launcher. Filter source and builds are frozen.

Normal installer routes all four matching EAs to the new sources and presets.
FTMO includes EMA3, London and Trend; Asia was not a member and was not added.
FTMO still has fourteen members, $50 maximum planned stop risk, expected-login
guard, news disabled, and unchanged account-protection code. Installer checks
are offline only. Existing attached charts do not change until the user reapplies
the matching BAT. No active MT5 account, chart or trade was changed here.
Client Top 5 membership was preserved: none of these four changed EAs is in that
basket, and its RSI VWAP member is unchanged. Do not overwrite customer licences.

Evidence:
PARITY.json: all 219 selected one-year trades match production entries, exits,
volume and recorded costs. Four production builds: zero errors and warnings.
Long Window Comparison/Comparison.html: before/after 1y, 3y and 5y tables and
15 separate EA closing-balance graph panels; native reports and ledgers alongside.
18 frozen native long-window runs, no further optimization. Baseline is the exact
unfiltered preset from the one-year ADX/DI table, not every old BAT mode. Asia
already has Markov enabled; EMA3 baseline Markov is off. Trend retains 0.6R.
Each standalone EA starts at USD10,000 with 1% equity-risk TARGET and upward /
minimum broker lot rounding, 1:2000 leverage, Model4 and 150ms execution delay.
Windows end 2026-10-02 exclusive; 3y begins 2023-10-02, 5y begins 2021-10-02.
Real broker ticks cover only 25% and 15% respectively; MT5 generates the rest.
DD is native maximum relative equity drawdown, including floating P/L. Graphs
and calendar-daily annualized Sharpe use closing balances, not floating equity.
These are not simultaneous shared portfolios or new guarded FTMO pass forecasts.

Interpretation, not a forecast:
USDJPY filters increase PF and reduce drawdown in both longer windows, but lower
five-year return and slightly lower five-year Sharpe. Asia DI increases PF, return
and Sharpe modestly while slightly increasing drawdown. EMA3 ADX weakens return,
PF, win rate, Sharpe and drawdown over both longer windows. Trend DI reduces DD
but also return, PF and Sharpe; filtered five-year PF is 1.141, below 1.20.
No automatic reversal of the user's selected settings was made. A longer win
streak alone does not establish an edge. The selection year overlaps these
tests, so this is retrospective evidence, not independent forward validation.

Website:
Current standard-mode native caches updated for all five EAs for 1y/3y/5y.
Default catalogue period is 1y. Pre-release 6m and combined/FTMO forecasts stay
archived and are explicitly labelled. Old evidence backed up under before/.
Legacy cache-build paths fail closed instead of overwriting audited release
records. Local website refreshed on 127.0.0.1:8080 only; no Git push or remote
production deployment was requested or performed. See VERIFICATION.json for
the release-specific checks and remaining broader legacy test failures.
