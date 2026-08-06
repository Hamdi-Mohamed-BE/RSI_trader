# LTA rule coverage and limits

This EA is an auditable mechanical interpretation of the book, not a claim that the complete discretionary LTA framework has been automated.

## Implemented in the EA

- Previous-day, previous-week and swing volume-profile POC, VAH and VAL with a configurable 70% value area
- Supply/demand bases and expansion candles, including RBR/DBR demand and RBD/DBD supply logic expressed mechanically
- Required expansion volume and an optional requirement that the expansion breaks prior structure
- Higher-timeframe price-structure bias and intraday trend confirmation
- EM1 double-wick, EM2 internal swing-profile, EM3 consolidation/manipulation/expansion and EM4 continuation entry engines
- Fixed RR target, stop beyond the confirming wick/zone plus an ATR buffer
- Equity-based position sizing through the broker's own profit calculator
- Broker-minimum-lot protection, one-position-per-symbol control, and the two-consecutive-loss daily stop
- Contrarian breakeven-at-1R and session/dead-trade controls as optional inputs
- Manual bullish/bearish bias input for a trader who has completed the book's external macro analysis

## Cannot be reproduced from the PDF and this MT5 feed alone

- Smart Money Intelligence/COT positioning, FutureScope seasonality, Stealth Valuation, correlations and open interest
- Centralized futures exchange volume. The requested symbols are broker CFDs; the EA prefers real volume when available and otherwise uses broker tick volume.
- The author's discretionary zone selection, macro narrative, news-failure interpretation and chart-reading judgment
- A reliable high-impact-news filter without a separate calendar/data source
- Psychology, journaling and manual review requirements
- Portfolio-wide correlation checks when several EA instances trade different symbols
- Exact futures-session EPD and Sunday-open levels on every broker; the current profiles use the broker's completed D1/W1 sessions

## Important risk deviation

The book's 2/2/2 rule caps a normal trade at 2% and reduces uncertain or contrarian trades to 1%. The requested test presets override that guidance and use 2.5% for every accepted trade. The EA source defaults remain 2% momentum and 1% contrarian, with an absolute 2.5% safety cap.

