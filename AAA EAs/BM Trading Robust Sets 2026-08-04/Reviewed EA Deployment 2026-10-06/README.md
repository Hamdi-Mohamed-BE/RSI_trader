# reviwed_Eas — owner-selected portfolio, October 6, 2026

Run `../reviwed_Eas.bat` when you decide to install. This package was built and dry-checked, **not installed**.
The original normal roster remains 37; this opt-in profile selects 25. Other BATs, FTMO, Ava and client licences
keep their existing configurations. The shared manifest is `selection.json`; website `/ea-review` and `/eas`
phase filters use the same selection identity. The original dated 13/14/10 review is archived, not erased.

The launcher asks for:

1. Normal risk: fixed USD target or current-equity percentage (default 1%). Fixed USD is exact only where the EA
   supports a cash input; otherwise its percentage equivalent is calculated from balance at installation and
   subsequently floats with equity. Lot rounding UP / minimum lots, gaps and fees can exceed the target.
2. Separate **news percentage per order** (default 0.75%), as in Best Recommended. News Pulse uses equity; V9
   uses balance. Both pending directions remain enabled. Four simultaneous straddles plan eight times this
   percentage, plus V9; news stays exempt from adaptive stops. No shared daily-loss/equity cap is added.
3. Individual DI ON/OFF: Nasdaq 5M and USDJPY London. Default ON preserves the published preset; USDJPY ADX20
   stays ON. OFF is a custom selection, not covered by DI-ON results. No new DI filter is added to other EAs.
4. Confirmation, then the existing supported terminal selection/account/symbol checks. No broker/login switch.

The original 13 keeps plus all three DMCs, Gold Overnight, all five news bots and the owner's saved Trend
Progression 1.5R candidate plus both US30/US100 hourly EAs make 25. DMC strategy/exit rules and Gold Overnight raw rules are unchanged.
Hourly rules and hours are unchanged. Normal USD/% selection sizes them against each frozen historical worst
completed-trade loss; they have NO stop-loss, so future losses can exceed this scenario budget. Their retained
website returns are the original fixed-one-lot benchmark, not results for the chosen history-sized portfolio.
Only this profile changes Trend to 1.5R / 3-bar swing stop / no BE or trailing / no ADX or DI; the original
compiled production EA already supports those inputs. Other normal BATs retain 0.6R and FTMO stays separate.

**Passed to live trading phase is an owner deployment decision, not a statistical validation pass or guarantee.**
Recent weakness, tiny samples, news execution risks, failed robustness and older generated ticks remain visible.
Trend's prior study is not newly certified under the latest-two-year OOS policy. No performance tests were rerun,
no portfolio returns were recomputed, and old caches are not relabelled as reviewed shared-account results.

Safe validation: `reviwed_Eas.bat -ValidateOnly` (no account probe/terminal changes). Pure-function tests are in
`../_Auto Deploy/Test-Reviewed-Portfolio.ps1`. Installation uses a distinct profile and preserves existing trades;
it changes the active profile, so previously attached excluded EAs stop running there when the owner installs.
It does not delete their binaries, close positions or install a manager for positions of excluded bots.
Review open positions and keep their protection/management arrangements before switching profiles.
