# Architecture

```text
Coinbase REST L3 snapshot ─┐
                           ├─> synchronized MBO book ─> microstructure engine
Coinbase full WebSocket ───┘              │                    │
        │                                 │                    │
        ├─ sequence gap ─> rebuild        ├─ ladder            ├─ absorption
        └─ repeated failure ─> L2 fallback├─ imbalance         ├─ spoof/pull
                                          └─ stacked liquidity └─ aggressive delta

Manual LTA context ─────────────────┐
HTF bias + structure ───────────────┼─> deterministic ranker ─> A/A+/no-trade
POC/VAH/VAL + supply/demand ────────┤
MBO confirmation ───────────────────┘
```

The server owns all market connections and secrets. The browser receives normalized state over `/stream`. Strategy ranking is deterministic and auditable; an optional AI layer can explain results later but cannot override risk or location gates.
