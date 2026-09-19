# Capped gold recovery — frozen research protocol

User approval: test the proposed capped gold alternative, not deploy it. XAUUSD only; $3,000; Exness Zero. No live orders, website/BAT edits, optimization of another EA, Git push or account purchase.

## Primary preset and execution rules

- Buy-only, first available quote; no signal, trend, news or session filter added.
- Equal 0.01-lot buys, at most 3 simultaneous positions. Fixed starting-price-anchored $10 steps. Alternative spacings: $20, $30, or 1x previous completed H1 ATR(14), frozen when the basket starts. No lookahead or moving rung after entry.
- Initial candidate: $20 NET basket take-profit; $60 basket loss budget; $90 daily loss threshold; $60 daily realized-profit cap. All dollar limits are fixed dollars, not compounded percentages. They initially represent 2%, 3%, 2% of $3,000, respectively. Limits are not guaranteed fills.
- Basket P&L is account equity minus balance just before first entry; includes entry commission, all open P&L and accrued swap. Historical tester charges apply. Current native XAU commission is $5.50/lot round trip charged at entry; include it when projecting the pre-order protective stop and reconcile actual charged fees afterwards.
- Basket common stop is recomputed so aggregate marked equity at that price reaches the tighter of (basket-start balance minus $60) and (broker-day-start balance minus $90). On an addition it may tighten, never loosen. Do not add if the proposed stop is already within broker minimum distance of executable bid, the projected loss exceeds available budget, or virtual/broker margin is insufficient. No forced rounding up, invented fill or unlimited doubling.
- Every order has a native protective SL; after fills and swap/day changes synchronize all live legs to the same basket SL. Net-profit mode has a common native TP based on the aggregate target, and an every-tick equity check. If one leg closes, close any remainder before restarting. Record stop/gap overshoot rather than clamping reported losses.
- After the first observed daily equity-loss threshold, flatten and lock until next broker date. Daily P&L = equity minus balance at the first tick of the broker date, so carried floating P&L still counts. Closed profit cap stops NEW baskets, not open basket management. Hold overnight unless a stop, target or daily-loss exit fires.
- At first equity <= 0 with open exposure, terminate the test immediately and mark insolvency. Do not credit any later artificial recovery. Broker native stop-out reasons are recorded separately.
- Fixed native leverage 1:2000. A virtual pre-order check also applies current equity tiers (1:1000 at $30k, 1:500 at $100k). Historical news/weekend high-margin windows are unavailable; stress with lower fixed leverage rather than claim they are reconstructed.
- No arbitrary account drawdown halt, withdrawals or top-ups in the main runs. A separate variant may STOP when a closed flat balance reaches $6,000; this is not a real withdrawal simulation.

## Selection protocol (declared before results)

- Baseline equal-lot candidate on standard system windows: 6m/1y/3y/5y ending 2026-09-05 exclusive, identical to original raw comparison. No BTC.
- Coarse development: 2021-09-05 to 2023-09-05. Equal lots, 3 positions, loss $60/daily loss $90/daily profit cap $60. Twelve combinations: spacing {$10,$20,$30,1x H1 ATR14} x basket net target {$10,$20,$30}.
- Validate the top three development candidates on 2023-09-05 to 2024-09-05. Development ranking: exclude insolvency/stop-out; positive net profit and >=30 baskets preferred, then net profit divided by (1 + maximum equity drawdown dollars). Choose by validation net profit / (1 + max equity DD dollars), with at least 20 baskets and positive validation net P&L preferred. All losing candidates remain visible; no mandatory winner promotion.
- Freeze selection before the later check 2024-09-05 to 2026-09-05. Show its standard 6m/1y/3y/5y figures, clearly noting overlap with development rather than pretending those overlapping windows are all out-of-sample.
- One-at-a-time diagnostics on development/validation: capped doubling instead of equal lots; original-price exit instead of net basket exit; $30 basket-loss budget; daily profit cap $30 or none. They do not retroactively change the main selected candidate. Avoid hundreds of unbounded parameter combinations.
- Stress final candidate with longer native execution delay and lower leverage cap. Additional spread/commission/swap/slippage haircuts on recorded trades must be labelled fixed-path sensitivity, not a fresh native path.
- Rolling start checks and stopping-at-$6,000 may be added after selection, preserving parameters. The previous raw results and repeated inspection mean this is historical validation, not a genuinely unseen live test.
- Full trade/deal ledger reconciliation, every-tick equity drawdown, basket and position win rates, fees, profits, exposure, stop overshoots, daily controls, margin rejections and first-$6,000 versus ruin will be reported. Generated ticks before 2026-01-01 must be labelled; do not imply all five years are real ticks.

No profitability, daily-income or loss-limit guarantee. These controls change the original strategy; the original artifacts remain intact.

## Research-terminal safety audit

During development-batch startup, the isolated terminal was found restoring an unrelated old chart EA. It was stopped; its startup configuration now explicitly sets `Experts.Enabled=0`, `Experts.AllowLiveTrading=0`, and a separate empty `CappedResearchOnly` chart profile. A read-only terminal API check confirmed `trade_allowed=False` for the isolated terminal. The normal user terminal was not stopped or reconfigured, and its balance stayed at $9,643.77 with zero open margin. No live order was submitted by the research tools. The interrupted development batch is excluded; the guarded restart uses new per-case magic identifiers.
