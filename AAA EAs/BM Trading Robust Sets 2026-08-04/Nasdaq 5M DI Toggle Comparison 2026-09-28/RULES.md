# Nasdaq 5M: exact DI toggle comparison

Frozen before running, 2026-09-28. Research only; do not change the active EA, launchers or website.

Compare the selected DI + 0.60%-of-price initial stop + ATR trailing version with the same executable and inputs, changing only `InpRequireDIAgreement` from true to false. The DI-on version is the control. No optimization or parameter search. Two configurations, four overlapping windows each, eight native runs.

- Instrument: USTEC (Nasdaq / US100), M5, existing isolated research broker feed.
- Entry: completed 09:30 New York M5 candle, direction from close versus EMA12; one trade per New York day and one position for this EA. DI-on requires DI14 direction agreement on that same closed candle. No later retry for DI disagreement.
- Initial stop: 0.60% of entry price. Risk: planned 1% of current equity, $10,000 initial balance; broker-valid upward lot rounding remains unchanged and can exceed the target. Adaptive portfolio controls off.
- Management: ATR14 trail at 6 ATR after +1R, no fixed target, no breakeven, no MA trail, no forced end-of-session exit. Overnight positions can prevent the next day's entry. Disabling DI can therefore change later trade opportunities, not merely add trades.
- Use the currently selected binary byte-for-byte; no compile or source changes.
- Dates match published evidence: 6m from 2026-03-25; 1y from 2025-09-25; 3y from 2023-09-25; 5y from 2021-09-25. All end 2026-09-25 exclusive. These are not independent holdouts.
- Native MT5 Model 4, 150 ms execution delay, same leverage/currency/broker configuration as the original research. Report broker-recorded commission and swap. Historical spread and ticks come from the tester; this is not a guarantee of live slippage/fills. Real ticks are only available from January 2026; older data may be generated.
- Rerun both sides under the same present history and compare DI-on with archived evidence. Report any drift instead of quietly mixing unmatched baselines.
- Show return, trades, trades/month and weekday, win rate, PF, maximum equity relative drawdown, and winning/losing streaks. Also preserve the original site's drawdown field (percentage at the maximum cash drawdown) separately if different.
- No automatic promotion. Inspect robustness across periods and drawdown, not only the latest return. This comparison does not estimate FTMO pass rates.

Safety: only the isolated portable tester with live trading disabled and an empty profile. Refuse to run if it or its agent port is occupied. Do not touch normal MT5, private account configuration, or other work.
