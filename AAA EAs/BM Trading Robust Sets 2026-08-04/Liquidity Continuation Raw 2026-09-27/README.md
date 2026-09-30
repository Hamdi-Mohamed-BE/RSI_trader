# Calyx Liquidity Continuation — raw research

Approved independent reconstruction on US30 / US100 / US500 / XAU / BTC. This is not the private T-812 implementation. No production or FTMO deployment.

- `RULES.md`: frozen causal rules, assumptions, synthetic control, costs and promotion gate.
- `run-config.json`, `BUILD.json`: fixed cases and source/binary/rules identities.
- `Liquidity.mq5` / `.ex5`: tester-only EA, clean native compile.
- `run.py`: one isolated MT5 tester at a time, Model 4, 150 ms delay, no live trading API. Retains and validates completed cases when resumed. Never targets normal MT5 or Ava.
- `REPORT.md`, `RESULTS.json`: current completed results; always check completed/expected count.
- `balance-1y.png`: closed-balance comparison, not floating-equity curve.
- `VERIFICATION.json`: helper tests and independent retained-evidence checks.
- `audit_bars.py`, `ExportAudit.mq5`, `BAR_VERIFICATION.json`: after the grid finishes, export native historical bars with a non-trading tester-only script and independently rebuild levels, completed-bar ATR and breakout/retest confirmations. The audit does not alter strategy parameters or performance results.
- `OPERATIONS.md`: engineering issues and their resolution, including the exact completed research process closed when MT5 failed to shut down.
- `native/<case>`: SET, tester INI, gzip native report/journal, net deal ledger, order audit, run metadata.

## Reproduce / resume

Use the existing local Python 3.13 runtime. From this directory:

```powershell
& 'C:\Program Files\Python313\python.exe' .\run.py grid
& 'C:\Program Files\Python313\python.exe' .\verify.py
& 'C:\Program Files\Python313\python.exe' .\audit_bars.py
& 'C:\Program Files\Python313\python.exe' .\report.py
& 'C:\Program Files\Python313\python.exe' .\plot.py
```

Do NOT launch another copy while this study or another isolated tester owns the research terminal. The runner refuses a busy terminal/port rather than stopping it. A fresh source/build requires a separate study version; don't overwrite evidence and call it the original raw run.

The 300-day no-trade warmup supplies historical synthetic-level donors. Native headline history quality includes warmup; deal statistics use only the requested period. Sources are broker CFDs and may include generated ticks before real coverage. Passing a raw statistical gate is not permission to optimize/deploy and is not proof of future profits. All four overlapping windows are observed research data, not a pristine optimization holdout.
