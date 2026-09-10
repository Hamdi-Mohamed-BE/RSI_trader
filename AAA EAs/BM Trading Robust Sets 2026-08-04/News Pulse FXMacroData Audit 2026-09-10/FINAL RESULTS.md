# News Pulse — enhanced pipeline and FXMacroData result

## Outcome

FXMacroData found one valid event missing from the Strategy Tester calendar: **NFP on 4 September 2026 at 08:30 New York / 12:30 UTC**. Every event already present in the tester used the correct FXMacroData timestamp.

The source now uses an automatically generated FXMacroData calendar for Strategy Tester. It records exact UTC release epochs, coverage, fetch receipts and a SHA-256 content hash. A backtest must declare its UTC start/end dates and is rejected when the requested window is not fully covered. The deployed EX5, BAT files, website and live portfolio were not changed.

| EA | Current tester | FXMacroData tester | Added event effect |
|---|---:|---:|---:|
| XAUUSD | 8 trades · +25.71% · PF 15.49 · WR 75.00% · DD 1.78% | 9 trades · +35.32% · PF 20.82 · WR 77.78% · DD 1.78% | **+$960.91 / +9.61%** |
| XAGUSD | 8 trades · +66.39% · PF 33.35 · WR 87.50% · DD 2.51% | 9 trades · +93.34% · PF 43.43 · WR 88.89% · DD 2.51% | **+$2,694.67 / +26.95%** |
| EURUSD | 8 trades · +20.33% · PF 10.68 · WR 75.00% · DD 1.37% | 9 trades · +24.90% · PF 12.65 · WR 77.78% · DD 1.37% | **+$456.75 / +4.57%** |

Test window: 12 June through 10 September 2026, USD 10,000 initial balance, Exness MT5 Every Tick generated from M1 broker history, current two-sided settings, fixed 0.75% planned risk per stop and 1.50% maximum planned event exposure. The generated manifest contained **7 events**—3 NFP, 2 CPI and 2 FOMC—and the EA reported that all 7 were successfully processed on every symbol.

The added NFP produced one winning short trade on every symbol. This is only one event and must not be treated as proof that FXMacroData increases future profitability.

## Enhanced-pipeline decision

All three generated-calendar reports remain **WATCH ONLY**. They contain only nine closed trades, below the 30-trade minimum, and no measured broker-specific slippage/cost input was available for the mandatory execution-stress gate. The enhanced audit reports normalized PF values of 21.23 for XAUUSD, 65.34 for XAGUSD and 13.67 for EURUSD, but those high values are not reliable with only nine trades.

The anonymous FXMacroData tier verified seven recent NFP/CPI/FOMC timestamps from 17 June through 4 September 2026. It does not cover the full historical test period, so the calendar cannot yet be promoted as a complete three-to-five-year replacement.

## Current release-time logic

### Live trading

1. The EA asks MT5's built-in economic calendar for upcoming USD events over the next eight days.
2. It identifies NFP, CPI and FOMC from the MT5 event name.
3. MT5 supplies the release timestamp in broker-server time; the EA does not calculate 08:30 or 14:00 for live events.
4. The schedule cache refreshes every five minutes.
5. A one-second timer checks the lead window. Current selected settings place orders at **T-30 seconds**.
6. Placement requires a broker-stamped quote no older than five seconds. The VPS clock and local timezone are ignored.

### Strategy Tester

MT5 does not provide its economic calendar to Strategy Tester. The EA now reads a generated include containing the exact FXMacroData UTC epoch for every NFP, CPI and FOMC release in the approved window. It converts each UTC epoch to the configured tester-server clock; it no longer invents 08:30/14:00 times or maintains release-date arrays by hand.

The generated calendar carries a verified date range and content hash. Tester inputs must declare the exact requested range. Initialization fails outside coverage, runtime escape stops the test, and `OnTester` reports the number of successfully processed events so the runner can assert it equals the manifest count.

## Recommendation

Keep MT5's calendar as the primary live clock. Use FXMacroData as the historical tester-calendar generator and offline validation source. Do not use the released actual value to choose the pre-release order direction: the actual value is not known at T-30, so doing that in a backtest would be look-ahead bias.

Do not deploy the new EX5 yet. First obtain full historical FXMacroData coverage, rebuild every NFP/CPI/FOMC occurrence, rerun three to five years with real ticks or measured execution stress, and require the enhanced pipeline to pass.
