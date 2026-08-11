# AAA Final native MT5 EAs

Built from the rules and selected settings stored in each AAA Final project. These are native MT5 ports; they do not run the Python workers. The two research additions dated 2026-08-10 were optimized and independently replayed before their rejection gates were set.

| AAA Final project | Native MT5 EA | Broker symbol class | Chart | Preset trading status | Preset equity risk |
|---|---|---|---:|---|---:|
| EMA3 | AAA Final EMA3 EA | XAUUSD / GOLD alias | H4 | Enabled | 1.0% |
| asia breakout | AAA Final Asia Breakout EA | XAUUSD / GOLD alias | H1 | Enabled | 1.0% |
| DmC | AAA Final DmC EA | XAUUSD / GOLD alias | H1 | Enabled | 1.0% |
| AMD | AAA Final AMD EA | XAUUSD / GOLD alias | M15 | Disabled: research gate | 1.0% if enabled |
| US100 weekness | AAA Final US100 Weakness EA | US100 / NAS100 / USTEC / UT100 / NDX100 alias | M15 | Enabled | 1.0% total; OCO orders split it |
| US100 weakness exact two-leg | AAA Final US100 Weakness Exact EA | USTEC / US100 alias | M15 | Disabled: latest-year validation failed; manual research only | 1.0% total split equally between two legs |
| news pulse | AAA Final News Pulse EA | XAUUSD / GOLD alias | M1 | Enabled; robust long-only 60-second preset | 1.0% on the buy side; sell side disabled |
| weekend direction | AAA Final Weekend Direction EA | XAUUSD / GOLD alias | M15 | Disabled: provisional gate | 1.0% if enabled |
| XAU Grid | AAA Final XAU Grid EA | XAUUSD / GOLD alias | M15 | Enabled | 0.5% total across grid legs |
| XAU weakness | AAA Final XAU Weakness EA | XAUUSD / GOLD alias | M15 | Disabled: validation gate | 1.0% if enabled |
| XAU US100 weakness | AAA Final XAU US100 Weakness Research EA | XAUUSD / GOLD alias | M15 | Disabled: research-only; its report failed validation | 1.0% total if enabled |
| Apex Pulse transparent research | AAA Final Apex Pulse Research EA | EURUSD | M1 | Disabled: 2025-2026 holdout failed | 1.0% if manually enabled |
| IVB fixed-range volume profile | AAA Final IVB FRVP EA | US30 / DJ30 / WS30 alias class | M1 | Disabled: complete Exness return missed portfolio gate | 1.0% if manually enabled |

## Saved locations

- Each original project has an `mt5` subfolder containing its `.mq5`, compiled `.ex5`, default `.set`, and shared source includes.
- The packaged copies are under `AAA Final EAs` inside `BM Trading Robust Sets 2026-08-04`.
- The active MetaTrader installation also has the compiled EAs under `MQL5\\Experts\\BM Trading\\AAA Final` and the presets under `MQL5\\Profiles\\Tester\\AAA Final EAs`.
- The existing setup BAT now installs the original four BM EAs plus these ten EAs as a 14-chart profile.

## Safety note

A clean compile only proves that MT5 can load the code. It does not prove equivalence to every Python execution detail or future profitability. The disabled defaults preserve the rejection/provisional/research gates recorded in the corresponding project folders.
