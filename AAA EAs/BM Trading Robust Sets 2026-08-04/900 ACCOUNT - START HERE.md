# BM Trading USD 900 launcher

Use **INSTALL AND RUN ON 900 USD MT5.bat** for a USD account with a balance between $800 and $1,200.

The launcher is separate from the original $100K launcher. It verifies the active account, checks the broker's symbol names and minimum index lot sizes, installs the small-account settings, and opens the **BM Trading 900 - AUTO** profile.

## Installed exposure

| EA | Chart | Small-account input |
|---|---|---:|
| Range Breakout | USDJPY M5 | $40 requested stop risk |
| ATR Candle Breakout | XAUUSD H1 | $40 requested stop risk |
| Go Long | US30 D1 | Broker-specific lot and hard stop targeting $40 |
| Turnaround Tuesday | UT100/NAS100 D1 | Broker-specific lot and hard stop targeting $40 |

The small-account launcher targets $40 per stopped trade, approximately 4.44% of $900. It adds hard stops to Go Long and Turnaround Tuesday and calculates their lots/stops from the connected broker's contract specifications. This changes those two strategies from the original validation, which used no hard stop. Gaps and slippage can still exceed the target.

The earlier replay does not validate these newly added index stops. Run the generated effective presets on demo before relying on them with real funds. Exact presets from the most recent successful installation are saved as `LAST INSTALLED 900 - ... .set` beside each matching EA.

Do not use the original **INSTALL AND RUN ON ACTIVE MT5.bat** on this account. It remains locked to $100K accounts because its position sizes are approximately 100 times too large.
