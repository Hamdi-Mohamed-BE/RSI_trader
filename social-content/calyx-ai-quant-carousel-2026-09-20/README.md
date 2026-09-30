# Calyx — AI × Quant carousel

Prepared 2026-09-20 for manual Instagram / LinkedIn posting. Not published or scheduled.

## Deliverables

Six PNG images, each 1122 × 1402 pixels (approximately 4:5), in upload order:

1. 01-calyx-cover.png — four Calyx project areas, featuring your illustrated avatar.
2. 02-crypto-arbitrage.png — planned BTC-first cross-exchange research and a separate lead-lag experiment.
3. 03-gold-news-bot.png — the built Gold News V9 prediction and MT5 execution workflow.
4. 04-strategy-research.png — raw baseline, candidate testing and evidence comparison.
5. 05-overfitting-checks.png — implemented Deflated Sharpe, bootstrap and stress-audit concepts.
6. 06-building-calyx.png — first-person closing invitation for technical feedback.

Use the numbered images in order. The reference screenshots contained six unique slides and two duplicates; no duplicate slide was recreated. These are original compositions, not screenshots with someone else's name removed.

CAPTIONS.md contains separate LinkedIn and Instagram drafts, plus optional source links. PROMPTS.md records every exact image-generation prompt. ALT-TEXT.md provides descriptions for accessible posting.

## Art direction and production

Built-in image generation was used, one call per final asset. Your supplied avatar defined the illustrated identity and black/lime palette. The cover was then used as the visual reference for the other slides. All six final assets are copied into this workspace; default generated originals remain intact.

Reviewed all six images for spelling, numbering, legibility, consistent style and factual meaning. File checks confirmed identical dimensions, six non-empty PNGs and successful archive creation. Generated text remains rasterized rather than separately editable; the saved prompts support revisions.

The LinkedIn repurposing and humanizer skills shaped the first-person captions and reduced promotional filler. They did not provide financial evidence; project files, the linked task and primary research sources did.

## Project evidence checked

- Crypto plan: ../../AAA crypto arbitage/CRYPTO_ARBITRAGE_MASTER_PLAN.md
  - Explicitly PLAN ONLY. HftBacktest is the planned research foundation, with Hummingbot considered later if justified.
  - Two prefunded venues; buy cheaper BTC and sell held BTC at the other venue, subject to executable depth, both legs' costs and inventory handling.
  - Lead-lag is a separate hypothesis. No profit, speed advantage or live deployment is claimed.
- News Bot task: thread://019ed7cd-f66d-7080-86fa-92e0e1df432b?hostId=local
  - Read the referenced task before relying on it. The September replay example comes from the task's reported FOMC reconstruction, not a new backtest run for this design job.
- Runtime: ../../AI news/README.md and predict_news.py
  - Gold News V9 supports CPI, NFP and FOMC; a pre-release prediction is locked and routed through an MT5 EA bridge, with result logs.
  - Exact entry/risk defaults differ from some historical experiments, so no mutable risk, entry-second or TP setting is advertised on the slides.
  - “Built” means code and runtime components exist; it does not certify a currently connected account, profitability, or operational health.
- Audit: ../../AAA EAs/Calyx Research Pipeline/README.md and calyx_pipeline.py
  - Implemented Deflated Sharpe, trial-count inputs, block bootstrap and cost/stability gates were inspected.
  - A forward-test eligibility result is not a live-investment recommendation or a guarantee that every EA has passed.
  - Closed-P&L risk estimates are not a substitute for MT5 intratrade equity evidence.

## Primary research references

### Arbitrage context

Igor Makarov and Antoinette Schoar, 2020, Journal of Financial Economics, 135(2), 293–319.

MIT Sloan publication page: https://mitsloan.mit.edu/cfi/trading-and-arbitrage-cryptocurrency-markets

The paper studies cross-exchange price differences and constraints on arbitrage. It supplies background, not proof that our specific BTC latency or prefunded strategy is profitable today. The slide uses an attributed reference card rather than a fabricated paper image.

### Deflated Sharpe context

David H. Bailey and Marcos López de Prado, 2014.

Author-hosted paper: https://www.davidhbailey.com/dhbpapers/deflated-sharpe.pdf

Publisher DOI: https://doi.org/10.3905/jpm.2014.40.5.094

This statistical method addresses performance inflation from testing multiple variants and non-normal returns. Its use does not remove all estimation risk, certify an economic edge, or replace forward tests.

## Boundaries

No trading processes, MT5 settings, website data, installations, repositories or live accounts were changed. No trades, new backtests, commits, pushes or social posts were made. Only this social-content package was created.

No model hit rates, backtest returns, fake charts, unsupported live profits, guaranteed payouts, Hawkes-process implementation claim, or giveaway promises are included.

