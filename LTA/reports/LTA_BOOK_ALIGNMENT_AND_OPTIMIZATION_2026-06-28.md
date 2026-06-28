# LTA Book Alignment and One-Month Optimization

## Test window

- Window: 2026-05-28 through 2026-06-28
- Starting balance: $300
- Risk per accepted trade: 5% of realized account balance
- Daily LTA cap: 3 trades
- Partial TP: disabled
- Intrabar assumption: conservative; an already-active stop is counted before a new target when both fit inside one candle
- Historical spread: deducted and rejected when spread exceeded 0.10R

## Symbols tested

XAUUSD, XAGUSD, BTCUSD, US30, US100, EURUSD, GBPUSD, USDJPY, USDCAD, AUDUSD, NZDUSD, and USDCHF were tested on M15, M30, and H1 where MT5 history was available.

Forex candidates were additionally filtered through the live H1/H4/D1 agreement rule. The 10:00-13:00 New York strict window and its score/internal-structure requirements were also applied.

## Book-alignment changes

- Profiles now preserve MT5 real and tick volume separately and label the selected source.
- Bar volume is distributed through each candle's traded price range instead of assigned entirely to its close.
- POC, contiguous 70% value area, VAH, VAL, HVNs, and LVNs are calculated from the resulting histogram.
- Previous Daily, Early Previous Daily, Previous Weekly, Early Previous Weekly, and midweek Current Weekly ranges use New York session anchors.
- Fixed profiles require an actual consolidation followed by expansion.
- Swing profiles use wick-to-wick pivot legs.
- Entry Models 1-4 now include touch count, internal-swing profile, structure-break, and relative-volume rules.
- Low-volume lower-timeframe entries require stronger EM2/EM3 confirmation.

## Volume-source result

The connected broker returned 0% positive `real_volume` for both XAUUSD and XAGUSD over the latest seven-day M15 sample. The live engine therefore uses `tick_volume_proxy` and exposes that label in signals and logs.

TradingView MCP can supply current screener volume and technical snapshots, but it does not expose the historical intraday volume-at-price series needed to reproduce Fixed Range Volume Profile. It is not used as a historical profile feed.

## Selected LTA configuration

| Symbol | Timeframe | Final RR | Management |
|---|---:|---:|---|
| XAUUSD | M15 | 1:6 | TP1 -> BE, TP2 -> TP1, then one-R trailing stages |
| XAGUSD | M15 | 1:1 | Full close at TP1 |

All active LTA sessions were retained: Asia 19:00-02:00, London/New York 03:00-17:00, in `America/New_York`.

BTCUSD, US30, US100, and the tested majors were not retained because they were negative, too sparse, or lost acceptable expectancy after spread, strict-session, and historical HTF gates.

## Final validation

The final LTA-only validation used the current entry engine, no ORB candidates, no partial close, spread rejection, strict-session gating, per-symbol RR, and close-time account settlement.

| Exit policy | Ending balance | Return | Trades | Positive outcomes | Max drawdown |
|---|---:|---:|---:|---:|---:|
| Structure stop + staged trailing | **$703.12** | **+134.37%** | 20 | 70.0% | 10.0% |
| Current adaptive stop + smart invalidation | $282.68 | -5.77% | 23 | 52.17% | 11.65% |

The evidence favored the original structure stop. `AUTO_DYNAMIC_STOP_ENABLED` and `AUTO_SMART_EXIT_ENABLED` are disabled for LTA; position sizing still keeps account risk at 5% by adjusting lot size to the stop distance.

## Caution

This is an in-sample one-month optimization, not a profit guarantee. Tick volume is broker-specific, and live slippage, minimum lots, fills, and spread spikes can produce materially different results. The selected settings should be revalidated on an unseen period before increasing risk.
