# News Pulse XAU — event-specific v2.16

Approved by the user on 2026-09-19. The shared portfolio installer selects this dedicated XAU executable in all Standard, Full Safe, Dynamic, Best Recommended and Recommended Adaptive BATs. XAG/BTC binaries and presets are unchanged. Legacy A60 and long-only chart patchers are retired to prevent accidental rollback.

| Event | Placement | Anchor | Price offset | SL | TP | Trailing | Forced close |
|---|---|---|---|---|---|---|---|
| NFP | T-10s | Previous closed M1 high/low | $2 | $2 | None | Off | T+60s |
| CPI | T-5s | Previous closed M1 high/low | $1 | $2 | None | Start 1R, distance $10 | T+300s |
| FOMC | T-60s | Current Ask/Bid | $1 | $2 | 5.5R | Start 0.5R, distance $4 | T+120s |

Dollar distances mean gold price units, not cash risk. Closed-M1 buy anchors add the current spread to the high. The broker can reject a stop entry already crossed by price. There is no opposite-order cancellation when one side fills.

Risk remains 0.75% equity per pending side, exempt from Recommended Adaptive. Lot rounding, costs and gaps can exceed the nominal combined 1.50%. Calendar filtering remains restricted to primary high-impact NFP/CPI/FOMC. Timing is broker/calendar based, not VPS local time. Event kind is persisted and recovered from order/position comments so the correct trailing and timeout survive restarts.

The production build matched the selected research replay: +262.10%, 38 trades, PF 10.97, net win rate 65.79%, relative equity DD 6.60%, 2025-09-19 through 2026-09-18. This is HINDSIGHT-OPTIMIZED on 71% real ticks. Earlier-selected parameters underperformed the old preset on later validation (+5.70% versus +19.34%). No future-return claim.

Website 6m/1y/3y/5y evidence uses separate native runs aligned to the website's established 2026-09-05 cutoff, not the September-19 research window. See `News Pulse Event Parameters Research 2026-09-19/Deployment` for manifests, native reports and parity checks.

Run a maintained portfolio BAT to install this build in a terminal. Editing the repository does not replace an already attached live EA. No live terminal is automatically restarted by this promotion.
