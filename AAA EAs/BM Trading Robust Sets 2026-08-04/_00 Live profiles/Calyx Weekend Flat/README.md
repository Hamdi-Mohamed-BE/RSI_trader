# Calyx Weekend Flat (2026-11-11)

Owner: "update all profiles to go flat before weekend and holidays". FTMO Standard / 1-Step FTMO Accounts may not hold positions through market breaks
longer than 2 hours (ftmo.com FAQ "Can I hold positions overnight or over the weekend?", read 2026-11-11); challenges and Swing accounts may.

## What it is
`Calyx Weekend Flat.mq5` is a helper EA on ONE extra chart (H1, the profile's first symbol). It never opens trades. Every 5 seconds and on every tick it:
- closes the account's EA positions (magic != 0; manual trades untouched unless InpIncludeManual=true) and deletes EA pending orders
- **30 minutes before any break of 2 hours or more** in that symbol's broker trading sessions (SymbolInfoSessionTrade, merged over midnight): Friday close,
  daily breaks longer than 2 hours. Inside the window (until the market reopens) any newly opened EA position is closed at once.
- **US holidays** (built in, New York time; MT5 does not expose broker holiday schedules):
  - early-halt days, US indices / metals / oil: flat 12:00 NY on MLK, Presidents, Memorial, Juneteenth (observed), July 4 (observed), Labor, Thanksgiving,
    the Friday after Thanksgiving and July 3 (Mon-Thu); trading allowed again after 18:30 NY (23:00 on the Friday after Thanksgiving).
  - full closures: flat 12:00 NY on the trading day before Good Friday (US indices / metals / other indices) and before Christmas and New Year (also FX);
    allowed again from 00:00 NY on the next weekday.
  - crypto (BTC/ETH/...) is excluded from holiday rules; it is only closed if its own sessions have a 2-hour gap.
- optional `MQL5\Files\Common\CalyxHolidayFlat.csv` for broker-announced closures (FTMO "Trading Updates" page):
  `from_date,from_HH:MM_NY,to_date,to_HH:MM_NY,symbols` e.g. `2026.12.24,11:00,2026.12.28,00:00,ALL` or `2026.04.06,00:00,2026.04.07,00:00,GER40;UK100`.

## Installers
Every maintained installer asks `Close every EA trade before weekends and market holidays? ON or OFF [ON]` (parameter `-WeekendFlat ON|OFF`; -ValidateOnly / -Yes
use ON) and, with ON, installs `MQL5\Experts\Calyx Weekend Flat\Calyx Weekend Flat.ex5` and adds the helper as the last chart. The portfolio chart audits
ignore the helper chart. Wired by `wire_weekendflat.py patch` (originals in `before/`): shared `Calyx-InstallChoices.ps1`; 13 guarded installers (Best 1-Step,
Core 9 x2, P4 x2, Best Prop 9/15, ftmo 1_step, Prop Ready/Codex, FTMO-AnyBroker, FTMO, funded_v1, Turbo5); 7 no-guard package installers (Best1Step, Core9,
Edge10, Mixed22, P4, ORB-only, Current 14 + ORB05; EX5 copied into each package, Checksums.json refreshed); canonical `_Auto Deploy/Install-BMTradingPortfolio.ps1`
(Full EA, Dynamic / Recommended / Full Safe / 100K / 900 / claude / BEST RECOMMENDED, FTMO 10K SWING via Start-LiveProfile, reviewed). Ava is NOT changed.
Generators (Best 1-Step / Core 9 / P4 / Best Prop 15 `build.py installer`) reproduce the patched installers byte for byte.

## Tester audit (test_weekendflat.py -> TEST_RESULTS.json, native Model 4, InpTestOpen = 0.01 lot at 11:00 NY every weekday while flat)
USTEC, XAUUSD, USDJPY x 2025-11-17 -> 2026-01-10 and 2026-05-18 -> 2026-07-11: 60 test trades, 60 closed by the helper, 0 held over a Saturday, 0 failed closes.
Fridays closed 16:25-16:30 New York in winter and summer; holidays at 12:00 NY (Thanksgiving, the Friday after, Dec 24, Dec 31, Memorial, Juneteenth, July 3 observed).
The first build failed the summer weeks (the broker session table ends Friday an hour after the real summer close): fixed by the Friday 17:00 New York backstop.

## Not yet proven / limits
- Every profile's backtests, FTMO simulations and website histories were run WITHOUT the weekend / holiday close. Weekend-holding trades (Nasdaq 5M carries,
  EMA3, Gold Band Wave, 3 Way Gold, trend EAs) are cut at the Friday flat time; an EA does not re-enter the same move after the weekend.
- Holiday times are conservative rules, not the broker's calendar; add exact closures to the CSV. UK / EU holidays (Easter Monday, bank holidays) are not built in.
- If the platform rejects a close (market already closed) it retries every 5 seconds; a position still open when the break starts stays open.
- Guarded EAs record the helper's closes as normal closes in their ledgers.
