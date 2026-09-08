# Slow Multi-Asset Trend Research

This folder contains Step 3 of the new-strategy research plan. It is deliberately separate from every production installer and website manifest.

Start with `REPORT.md`. Reproduce in this order:

1. `py -3 acquire_data.py`
2. `py -3 research.py`
3. `py -3 native.py`
4. `py -3 walk_forward.py`
5. `py -3 build_report.py`
6. `py -3 verify_research.py`

The EA is tester-only and rejects non-tester initialization. Primary risk is hard-locked at 1% per trade. The broad screen and native MT5 evidence are intentionally labelled separately.
