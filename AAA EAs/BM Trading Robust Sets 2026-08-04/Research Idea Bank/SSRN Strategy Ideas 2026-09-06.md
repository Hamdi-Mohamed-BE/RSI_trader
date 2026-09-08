# SSRN Strategy Idea Bank — 2026-09-06

Research hypotheses only. None of these ideas has been added to an EA or production preset.

The SSRN blog trading-strategies tag is useful for discovery, but many linked items are working papers rather than independently validated trading systems. Every idea below must pass the Calyx native-MT5 pipeline: realistic costs, 1% risk, one- and three-year samples, out-of-sample checks, session/RR/stop/trailing comparisons, and Monte Carlo testing.

| Priority | Research idea | Candidate EAs/assets | Testable rule | Evidence caution |
|---|---|---|---|---|
| 1 | Volatility-regime switch between momentum and mean reversion | Nasdaq Momentum, Trend Progression, ORBs; US100/XAU/BTC | Permit continuation in calm/expanding ordered trends; reduce risk, stand aside, or enable mean reversion after extreme volatility and failed continuation | Strong concept, but exact thresholds must be walk-forward selected |
| 2 | Liquidity-clock and transaction-count confirmation | LTA, LVN/POC, ORBs, News Pulse | Replace or supplement raw tick volume with relative transaction count and time-of-day-normalized liquidity | MT5 tick count is only a broker-side proxy for centralized volume on CFDs |
| 3 | Crypto weekend as a separate regime, not a blanket ban | BTC/ETH FVG and BTC POC; Monday US100 | Keep weekend trading when the EA edge survives; separately test weekend spot moves/basis as a Monday risk or gap filter | Current Calyx tests reject a blanket weekend ban |
| 4 | Dynamic ensemble of momentum and mean reversion | Portfolio-level overlay; BTC/XAU/US100 | Allocate to the model whose recent regime score is active, with total correlated-risk caps | Extra degrees of freedom create overfitting risk |
| 5 | Cross-asset confirmation for metals | XAU/XAG trend and volume EAs | Use XAU/XAG agreement, divergence, or confirmed lead-lag only as a gate after the traded asset triggers | Recent lead-lag papers are early working papers; do not use as standalone prediction |
| 6 | Gold macro-regime overlay | XAU Trend Progression, XAU Slow Trend | Condition long/short exposure on gold trend plus a long-duration Treasury trend proxy | Requires a reliable cross-asset feed and careful timestamp alignment |
| 7 | Conditional FX momentum | GBPJPY/EURUSD trend EAs | Trade momentum only in favorable carry/forward-discount, low-volatility, low-dispersion states | Carry inputs may not be available consistently from every CFD broker |
| 8 | FVG after a measurable momentum leg with HTF/POC confluence | BTC/ETH Top-Down FVG | Require an M5 impulse threshold, a fresh FVG within a fixed time window, H1 EMA alignment, and nearby POC confluence | The specific recent SSRN paper is unaffiliated and must be independently replicated |
| 9 | Volatility compression release | ORB/Momentum; BTC/US100/XAU | Require multi-timeframe range/ATR compression followed by volume and trend-confirmed expansion | Treat the paper as an idea source, not proof of an edge |
| 10 | Long-only momentum as volatility timing | BTC/US100/XAU trend EAs | Use the signal primarily to exit or reduce exposure during high-volatility states rather than forcing short trades | May improve risk-adjusted return while reducing raw return |

## Source map

- SSRN Blog trading-strategies archive: https://blog.ssrn.com/tag/trading-strategies/
- Intraday liquidity patterns: https://papers.ssrn.com/sol3/papers.cfm?abstract_id=1925826
- Number of trades as an information-flow/liquidity proxy: https://papers.ssrn.com/sol3/Delivery.cfm/SSRN_ID2631560_code2297020.pdf?abstractid=2631560&mirid=1&type=2
- Diversified statistical arbitrage combining momentum and mean reversion: https://papers.ssrn.com/sol3/papers.cfm?abstract_id=1666799
- Momentum/reversal behavior across volatility regimes: https://papers.ssrn.com/sol3/papers.cfm?abstract_id=4342008
- Bitcoin calendar effects: https://papers.ssrn.com/sol3/Delivery.cfm/SSRN_ID4461481_code1669001.pdf?abstractid=3517291&mirid=1
- Crypto weekend effect spilling into Monday stock returns: https://papers.ssrn.com/sol3/papers.cfm?abstract_id=5382090
- Conditional currency momentum: https://papers.ssrn.com/sol3/papers.cfm?abstract_id=4411616
- Currency momentum risk controls: https://papers.ssrn.com/sol3/papers.cfm?abstract_id=3222699
- Gold cross-asset regimes: https://papers.ssrn.com/sol3/papers.cfm?abstract_id=6042135
- Global cross-asset momentum: https://papers.ssrn.com/sol3/papers.cfm?abstract_id=1833722
- Time-series momentum as volatility timing: https://papers.ssrn.com/sol3/papers.cfm?abstract_id=6910478
- Multi-asset momentum/FVG framework (low-authority hypothesis): https://papers.ssrn.com/sol3/papers.cfm?abstract_id=6725880
- XAU/XAG lead-lag framework (low-authority hypothesis): https://papers.ssrn.com/sol3/papers.cfm?abstract_id=7310299
- Volatility-compression framework (low-authority hypothesis): https://papers.ssrn.com/sol3/papers.cfm?abstract_id=5288827
