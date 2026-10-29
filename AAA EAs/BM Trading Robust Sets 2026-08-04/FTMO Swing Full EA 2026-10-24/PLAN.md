# FTMO Swing — Full EA portfolio · Recommended Adaptive (2026-10-24) — plan (written before any result)

**Owner request:** run the Full EA portfolio · Recommended Adaptive under FTMO Swing rules.
- Show the pass rates for phase 1 and phase 2 at 0.5%, 0.75% and 1% risk.
- Show the median days to get funded.
- Show the expected monthly income on 10k, 20k, 50k and 100k accounts, and the expected days before the funded account
  breaches.

Research only: Python replay of frozen ledgers. No MT5, no terminal, nothing installed.

## Signal stream
`Portfolio Long History All ORB05 2026-10-14/RISK_ROWS.json` → `full-eas`. This is the same stream as the website's
Full EA page.
- 22,117 positions over 2021-10-06 → 2026-10-05, covering 36 of the 37 members. Gold News V9 has no ledger and is
  missing, not counted as zero.
- **Unit risk:**
  - filled initial stop;
  - for the no-stop US30/US100 hourly EAs, the frozen historical worst-loss reference;
  - XAU Weakness at half budget per order (`risk_weight` 0.5).

## Sizing = Recommended Adaptive, identical to `EA store/app/portfolio_analytics.py:allocation_replay(adaptive=True)`
- **Normal EAs:** r% of closed balance at entry. Tapers: ×0.5 at ≥4% drawdown from peak and ×0.25 at ≥7%; ×0.5 after 3
  losses in a row in the lane and ×0.25 after 5; Nasdaq 5M ×0.25. No new entries after a −5% (of start) closed-loss UTC
  day.
- **News EAs:** news% per order, with no tapers. Declared: news% = 0.75 × r (0.75% at r = 1%, the BAT default).
- Fractional lots, as on the website. With fractional lots, results scale exactly with account size, so 20k, 50k and
  100k are the 10k results × 2, 5 and 10.
- **Parity check:** the continuous replay with FTMO rules switched off must equal `allocation_replay` to the cent.

## FTMO Swing rules modelled (2-step; check the current FTMO rule page before buying)
- **Phase 1:** +10% target. **Phase 2:** +5% target. Each phase starts from a fresh balance. There is no time limit;
  pass rates are reported within 90, 180 and 365 days.
- **Max daily loss** 5% of initial, measured from the Prague-midnight balance. **Max loss** 10% of initial.
- Weekend holding and news trading are allowed on Swing; leverage 1:30 is not modelled.
- **Target handling:** once closed balance ≥ target, new entries stop; the phase passes if the balance is still ≥ target
  when flat, otherwise trading resumes.
- **Two breach models (bracket):**
  - OPTIMISTIC: closed balance only.
  - PESSIMISTIC: every open position is marked at its full stop (unit risk × lots) at every event.
  - Real floating equity is not in the ledger.
- **Funded:**
  - Fresh account with the same rules and no target.
  - Every 14 days, profit above the initial balance is withdrawn and the trader receives 80%. The balance resets to the
    initial, and the drawdown peak resets.
  - Breach ends the account. Horizon 3 years.
- Funding fee and refund are not modelled; days to funded = phase 1 days + phase 2 days.

## Addendum 1 (before any FTMO result; after the parity check only)
The website-parity replay at 1% shows News Pulse BTC and EURUSD averaging about +7R per trade, with single trades up to
+86R and +110R.
- Those are news-spike fills on generated ticks with full-year fitted presets.
- Compounding them gives absurd balances: $10k → $3.5M inside 2024.
- Two variants are therefore reported:
  - **ALL36:** every recorded member, as the website stream.
  - **NO_NEWS:** the four News Pulse EAs removed. This is the headline, because the news R values are not credible
    evidence for prop sizing.
- Everything else in this plan is unchanged.

## Evidence
- **History:** every weekday start 2021-10-06 → 2025-10-05 (challenge, 365-day window).
- **Monte Carlo:** 2,000 paths of 4-week blocks, seed 20261024 (challenge 365 days; funded 3 years).
- In-sample: these EAs and settings were chosen after seeing this history; ticks before 2026 are generated.
- Every results table shows trades/month and trades/day.
