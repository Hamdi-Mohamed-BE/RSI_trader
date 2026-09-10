# DonnFX7 reel reconstruction notes

## Source inspection

- Reel: https://www.instagram.com/reel/DdFLweEt7Kf/
- Creator: DonnFX7 / Mortadha Haddad (`@donnfx7`)
- Caption visible on Instagram: `Trade Breakdown. Community link in bio. Join the family for free.`
- Runtime inspected in full: about 88 seconds.
- Instagram exposes video/audio streams but no subtitle, transcript, or text track for this reel.

## Visible evidence

The reel visibly presents an XAUUSD long from a marked lower demand/discount region toward an upper gray supply/resistance region. It adds a fixed-range volume-profile drawing over a completed price leg and circles repeated reactions/sweeps at horizontal reference levels. A position tool displays the long risk and reward region. The result montage contains both XAUUSD buys and sells, but it does not disclose a repeatable algorithm for drawing zones or anchoring the profile.

## Boundary between observation and inference

Observed: instrument, demand/supply regions, horizontal liquidity reactions, fixed-range volume profile, reversal entry, opposing-zone target.

Inferred for the audit: previous-week anchor, 61.8%-78.6% discount/premium, 128 profile rows, 70% value area, VAL/VAH confluence, H1 EMA50 trend, 16-bar sweep, four-bar confirmation window, 2.5R default target. These assumptions are explicit so they can be replaced if the creator later publishes exact rules.

## Duplicate-work check

This hypothesis overlaps partially with three existing research lines:

- LTA Volume Profile: auction/value-area logic, but not this selective discount-zone sweep sequence.
- POC Fibonacci Volume Profile: rolling POC/Fibonacci confluence, but its XAU version failed locked validation and did not use the reel's two-stage liquidity-sweep confirmation.
- ICT SNR Liquidity Reversal / Engineered Liquidity: sweep and lower-timeframe confirmation, but without the prior-week value-area confluence used here.

For that reason the raw audit tests the combined sequence and includes ablations to show whether the volume component contributes anything.
