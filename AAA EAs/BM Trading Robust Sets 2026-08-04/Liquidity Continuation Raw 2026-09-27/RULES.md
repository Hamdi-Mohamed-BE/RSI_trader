# Calyx Liquidity Continuation — frozen raw protocol

Frozen before results, 2026-09-27. Research only; no installation, optimization or FTMO changes.

## Source and limits
Public source: https://www.telonicstrading.com/research-liquidity-sweeps.html . Its profitable T-812 rules are private. This is an independent reconstruction of the first-touch continuation hypothesis, NOT T-812. The author's volume and directional-flow observations are not published trading thresholds. No volume or flow filter is invented here. Broker CFD quotes are not centralized futures trade prints. BTC is a new transfer, not a market in the cited study.

## Rules (all missing details below are our assumptions)
- Five separate instruments: broker symbols US30, USTEC (US100), US500, XAUUSD, BTCUSD; verify each in the native research journal. Isolated Exness research terminal, not the active/FTMO terminal.
- Eight level slots: previous available completed UTC broker daily high/low; current Asia 00:00–06:00 UTC high/low; current London 07:00–10:00 UTC high/low; prior Monday–Sunday UTC week high/low. London clock is deliberately fixed UTC, NOT DST-adjusted local London. Sessions are completed before use. Session profiles require at least 80% of expected M1 bars. Previous-day means previous available D1 bar (including weekend bars if present).
- Daily/session levels expire at UTC midnight. Weekly levels last to next Monday and are touched at most once that week. A level already crossed when formed is ineligible. Test all available trading hours; no news, trend, spread or direction filters.
- Price for level detection is bid (matching broker chart highs/lows). Buy fills use ask, sell fills bid, and broker exits use the appropriate opposite quote. No fictitious fills at the level.
- A: first touch. The first observed bid crossing from below a high (above a low) triggers a market continuation buy (sell).
- B: breakout–retest. Consume the same first touch; within 30 minutes of it require a completed M5 close beyond the level, then a LATER completed M5 candle that touches the level and closes outside again. Enter at the next available tick. A bar closing across the level can count as the initial break even if it contains the first touch, never as its own retest. No new setup after expiry.
- Both: ATR(14) on completed M5 bars, cached causally. At order submission SL is 1 ATR from executable quote, TP 1 ATR from executable quote (1:1 before costs). Outward SL rounding to tick; nearest TP tick. Broker-invalid geometry is skipped, not widened. Native execution delay 150 ms. No breakeven or trailing. Exit at first tradable tick at/after 60 minutes holding; failed timed exits retry no faster than once/minute. Price gaps, spread and delay may change realized RR/loss.
- $10,000 starting cash; 1% current equity planned initial stop risk, rounded UP to broker lot step/minimum as in existing raw studies. Actual risk can exceed 1%; report it. Reject insufficient margin. Leverage 1:2000 belongs to the research account, NOT FTMO.
- One position per instrument/run. Touches occurring while occupied are consumed, not entered later. Simultaneous events have fixed priority PD high/low, Asia high/low, London high/low, prior-week high/low. No daily trade cap, martingale, re-entry or optimization.

## Synthetic-level control (ours, approximate matched control)
At the same formation clock and for the same level slot/direction, take a past formation's positive distance from then-current bid divided by then-current M5 ATR. Among up to 36 prior formations whose ATR/price is within a factor of two of today's, use the fifth most recent eligible donor. Place a synthetic level at that donor distance times today's ATR on the same side of today's bid. Never use a current/future donor or select on outcomes. Record donor time/distance. Update donor history from actual levels in BOTH real/control runs. Require a positive real distance for both. Warm up 300 calendar days without trading, sufficient for weekly donors where history exists.

Controls match formation clock, direction and broadly volatility-normalized distance, not exact touch time or one-to-one filled trades. They can coincide with other real levels; no artificial removal. Different entry counts/portfolio occupancy are expected. This is NOT the paper's precise control construction, a randomized controlled trial, or proof of causation. No shuffled-price experiment is claimed.

## Windows and decision gate
- End 2026-09-27 exclusive. Raw requested windows 6m (2026-03-27), 1y (2025-09-27), 3y (2023-09-27), 5y (2021-09-27).
- Native Model 4, 150 ms execution delay, historical broker spread/commission/swap. MT5 may generate ticks where real ticks are missing: retain and report journal coverage. No claim of exact historical live commission or exchange queue modeling.
- Four configurations per instrument/window: real touch, real retest, synthetic touch, synthetic retest = 80 runs; no parameter search. Short smoke tests are engineering checks, not additional tuned candidates.
- Raw gate for each real entry model: positive return and PF >=1.15, >=30 trades, and higher PF AND net return than its matching control on BOTH 3y and 5y. Do not promote from a good 6m/1y alone. Sample uncertainty and overlapping windows remain limitations. Failure stops this raw version; optimization needs review/approval.
- Report net return, count/month/day, net win rate with Wilson interval, PF, actual floating equity and balance drawdown, longest/average win/loss streak, months, family breakdown, costs and execution failures. Intrabar equity from native report, not a balance proxy. Frequencies use weekdays for non-crypto and calendar days for BTC.
- Freeze source, binary, rules and configuration hashes; preserve native reports, deals, journal and inputs. Reconcile net P/L. Study code refuses non-tester execution.
