# LTA / M5 VWAP and developing POC — frozen raw comparison

Research only. Production, live charts, BATs, website and Git remain unchanged.

Window: 2025-10-05 00:00 through 2026-10-05 00:00 exclusive, Exness XAUUSD, USD 10,000, 1% current equity intended stop risk. Existing ceil/min-lot sizing retained; actual risk may exceed 1%. Native Model 4 with 150 ms delay, broker spread/swap. Available real ticks begin 2026-01-01; earlier ticks may be generated.

Baseline: exact current production EX5 + canonical active ALL DAY SET. Last installed XAUUSD snapshot has Markov Safe disabled; recommended BAT default Safe also tested and explicitly labelled. No account-wide adaptive controls. Same one-position, two-loss pause and direction controls across cases.

M5 legacy control: only execution timeframe changes M15 -> M5. Prior-day/week profile timeframe stays M15 to isolate execution changes. Full new flow computes previous-day profile and developing profile on M5.

New flow (ours where unspecified): completed M5 signal and live bid/ask entry both inside yesterday's 70% value area. Broker D1 boundaries; yesterday means prior available D1 session. Profile: same LTA 64-bin uniform bar-range volume allocation, real volume if available else tick volume. Yesterday's range end strictly exclusive. Developing profile uses only today's completed M5 bars (minimum 8). Session VWAP uses volume-weighted M5 typical prices (H+L+C)/3, reset at broker D1 start. This is a CFD approximation, not centralized exchange volume-at-price or tick VWAP.

Strong = directional candle, body >=60% of high-low range and close in top25% for long / bottom25% for short. Long close above VWAP and developing POC; short mirrors below. No extra crossing/retest requirement, no full-day containment condition. Retain LTA D1/H1 macro bias and momentum archetype (new signal replaces EM1/EM4); no required zone revisit. Also test AND variant requiring an unchanged original LTA M5 signal.

New entry stop: lowest low of 3 completed M5 candles minus existing .12 ATR(14) buffer for long, highest high plus buffer for short. AND variant retains original LTA structural stop. Reject illegal stops/targets, don't chase or enter without stop. Target frozen yesterday VAH for long / VAL for short. No minimum-RR filter added.

At first completed M5 candle that started after entry and closes past frozen yesterday POC in trade direction, close50% (broker step rounded down, both legs >=minimum) and move remainder SL to actual entry. Entry may already be beyond POC: requires a later candle and a currently profitable, broker-legal BE quote. Partial flag set only after successful partial execution; BE retried without taking another partial. At minimum lot, partial is skipped and logged, BE still attempted. Stop never loosened. No other BE/trailing/time exits for flow trades. POC/target do not roll at midnight.

No optimization. Closed positions (all partials plus entry/exit commissions, swap, fee) count once for PF, win rate and streaks. Native floating equity DD; daily sampled mark-to-market Sharpe annualized sqrt252, cash-balance and equity charts clearly separated. Last-year comparison is research, not multi-year validation or a forecast.

Off-switch copy must match production position/deal history exactly; hashes, SETs, native reports, export/cost audits and unit checks retained. Optional Safe rows are context, not a search/rank to select after observing outcomes.
