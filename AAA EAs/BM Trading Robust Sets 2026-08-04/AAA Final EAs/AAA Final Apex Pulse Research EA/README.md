# AAA Final Apex Pulse Research EA

## Status: rejected and disabled

This is a transparent EURUSD M1 implementation of the publicly describable Asian-range breakout idea. It is not claimed to reproduce any undisclosed proprietary filters.

Best researched settings:

- Build the Asia range from 00:00 to 07:00 Europe/London.
- Trade breakouts from 08:00 to 12:00 America/New_York.
- Accept Asia ranges from 15 to 40 pips.
- Stop distance: 1.0 times the Asia range.
- Target: 2R.
- Move stop to break-even at 1R.
- Risk: 1% of current equity, maximum one trade per day.

The untouched 2025-2026 Exness test lost 10.49% with PF 0.90 and 18.87% maximum equity drawdown. `InpEnableTrading` is therefore false in the EA defaults, and this EA is not in the active installer.

The `.set` file is retained only to reproduce the rejected test.
