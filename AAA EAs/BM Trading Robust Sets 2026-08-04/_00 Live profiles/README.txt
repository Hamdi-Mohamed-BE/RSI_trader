CALYX NAMED PORTFOLIOS - 2026-10-17
Keep this entire folder and its sibling EA folders together; these small BATs are not standalone embedded distributions.
Each BAT asks for risk type/value, then separate DI ON/OFF for Nasdaq and USDJPY where included (ADX20 stays).
FTMO: default fixed USD50, or equity %; all requests remain capped at USD50, with existing guard restrictions.
Prop ready: nine EAs (Core 4 plus five 0.5R ORBs), same FTMO USD10K Swing guards/default fixed USD50. Separate DI prompts; see PROP READY GUIDE.txt. Local launcher only, not a new website portfolio.
Current14+ORB: default 0.5% per trade/module, fixed USD default 50; no shared daily stop.
ALL FIVE ORBS: 0.5R in FTMO (17 EAs), Current14+ORB (17), ORB-only (5), normal/full (37) and reviewed profiles.
ORB-only: same default 0.5%/USD50; owner-approved despite NY PF0.97 and Selective five-trade sample. Legacy filenames retained.
Full: lower starting allocation 0.25% or USD25, news separately 0.10% per order; no-stop hourly exposure remains.
These defaults are starting allocations, not optimal settings or guaranteed maximum losses. Published history is not recalculated for custom selections.
Normal MT5 hedging account required. Installers ask for terminal/account and confirmation; inspect all charts before using Algo Trading.
To check files without accessing MT5, append -ValidateOnly to a BAT. Never use PreflightOnly as an offline test (it reads the account).
