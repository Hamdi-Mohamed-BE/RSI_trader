CALYX NAMED PORTFOLIOS - 2026-10-22
One folder per portfolio. Open the folder and run its BAT; each folder also holds EAs\ and Sets\ (exact copies of what that BAT
installs, hashes in PORTFOLIO.json) and a README listing every EA.
  FTMO guarded - Current 14\            17 EAs. FTMO account BAT (FTMO USD 10K only) + ANY BROKER TEST BAT (same EAs, broker-neutral guard).
  Current 14 + ORB 0.5R\                17 EAs, no shared guard.
  ORB-only - All five at 0.5R\          5 ORBs at 0.5R.
  Full EA portfolio - Recommended Adaptive\   37 EAs, adaptive risk, news separate.
  Prop ready\                           9 EAs, broker-neutral guard 0.5%. Also Codex_Best_FTMO.bat (same package/safety state) and both guides.
  Best Prop Portfolio 2026-10-20\       9 EAs, guard 1% / 4.5% / 3%, Nasdaq DI OFF default (own installer).
  MT 5 init\                            Create MT5 Instance.bat: new empty MT5 copy for another account.
Shared engine (do not move or rename): Start-LiveProfile.ps1, Profiles.json, ORB05-policy.json, ORB05 Sets\, Packages\.
Each BAT asks for risk type/value, then separate DI ON/OFF for Nasdaq and USDJPY where included (ADX20 stays).
FTMO: default fixed USD50, or equity %; all requests remain capped at USD50, with existing guard restrictions. FTMO accounts only.
FTMO ANY BROKER TEST: same 17 EAs/settings with the Prop Ready broker-neutral guard (0.5% of saved initial balance, scaled limits); any hedging account/broker/currency; asks Challenge/Verification/continuous (default continuous). Shares the Prop Ready saved baseline/safety state on the same account. No FTMO pass rate is inherited.
Prop ready: nine EAs (Core 4 plus five 0.5R ORBs), broker-neutral demo/live hedging accounts. Default fixed 50 in account currency, or 0.5% equity; hard cap 0.5% of persisted initial balance with scaled daily/exposure guards. Default continuous mode, not a phase profit stop. Separate DI prompts; see Prop ready\PROP READY GUIDE.txt. Local launcher only.
Codex_Best_FTMO: the same nine selected EAs and unchanged guarded binaries, with its own named MT5 profile. Broker-neutral, not FTMO/USD/10K restricted. Prompts risk, both DI filters (default ON) and Challenge/Verification/continuous mode (default Challenge). Shares the retained Prop Ready baseline and safety latches; see Prop ready\Codex_Best_FTMO GUIDE.txt. Cash means account currency, not currency conversion. Local launcher only.
Current14+ORB: default 0.5% per trade/module, fixed USD default 50; no shared daily stop.
ALL FIVE ORBS: 0.5R in FTMO (17 EAs), Current14+ORB (17), ORB-only (5), normal/full (37) and reviewed profiles.
ORB-only: same default 0.5%/USD50; owner-approved despite NY PF0.97 and Selective five-trade sample. Legacy BAT filename retained.
Full: lower starting allocation 0.25% or USD25, news separately 0.10% per order; no-stop hourly exposure remains.
These defaults are starting allocations, not optimal settings or guaranteed maximum losses. Published history is not recalculated for custom selections.
Normal MT5 hedging account required. Installers ask for terminal/account and confirmation; inspect all charts before using Algo Trading.
To check files without accessing MT5, append -ValidateOnly to a BAT. Never use PreflightOnly as an offline test (it reads the account).
