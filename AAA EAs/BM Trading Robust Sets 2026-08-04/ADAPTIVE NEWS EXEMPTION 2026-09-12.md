# Recommended Adaptive — news exemption

The shared installer disables `InpAdaptivePortfolioControls` for exactly four EAs:

- News Pulse XAU
- News Pulse XAG
- News Pulse BTC
- Gold News V9 Direction

This applies to all normal-MT5 BATs using the shared installer, including
`RECOMMENDED ADAPTIVE.bat`. Even a stale selected SET with the switch enabled is
overridden. The installer audits the effective switch and locked risk before
installing the profile. Selected news SETs also explicitly disable the switch.

News stays at the existing 0.75% planned risk per entry. Two-sided News Pulse
therefore plans 1.50% combined per event/chart. No adaptive daily stop, account
drawdown taper, loss-streak taper or Nasdaq allocation reduction is applied to
these four EAs. Signal/calendar filters, quote and broker constraints, native
stops, margin checks and exits remain unchanged. This does not guarantee that
every event will fill or that realized loss cannot exceed planned risk.

All non-News rules are unchanged. News P/L remains part of account-wide daily
closed P/L and drawdown calculations, so it can affect subsequent non-News risk.

The website applies the same exemption to its cached-trade portfolio replay.
Every news trade already present in the underlying current-profile ledger is
retained at a 1.0 risk multiplier, with its original recorded P/L and costs.
Individual EA backtests are not changed. Gold News V9 remains evidence pending;
no historical trades are invented for it. Older News Pulse generated-tick and
simulated-execution limitations still apply.

Reapply `RECOMMENDED ADAPTIVE.bat` to activate the new profile on MT5. Updating
the website/Git repository alone does not modify already attached chart inputs.
No Ava terminal, live positions or attached MT5 charts were changed by this update.

## Replayed portfolio comparison

Same retained trades, starting with $10,000; period end is 5 September 2026
(exclusive). Figures are net of recorded/scaled commission and swap. Drawdown
below is realized-balance drawdown, not floating-equity drawdown.

| Period | Previous return | News-exempt return | Previous DD | News-exempt DD | News-exempt trades |
|---|---:|---:|---:|---:|---:|
| 6 months | +169.93% | +180.70% | 8.88% | 10.09% | 850 |
| 1 year | +587.09% | +601.26% | 5.60% | 6.08% | 1,684 |
| 3 years | +2,241.10% | +2,288.14% | 8.27% | 8.57% | 4,453 |
| 5 years | +3,331.15% | +3,879.57% | 10.10% | 9.54% | 7,002 |

News real-tick coverage is 100% / 67% / 22% / 13% for these four windows.
Generated historical ticks and simulated execution materially limit conclusions
about live news profitability. Exempting news increased drawdown in the shorter
three windows; a higher replay return does not establish a safer live portfolio.
