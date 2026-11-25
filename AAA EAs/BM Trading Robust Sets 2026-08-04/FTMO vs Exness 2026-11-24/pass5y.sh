#!/usr/bin/env bash
# Build the FTMO streams, then the frozen multi-firm engine (sim.py days + first_payout.py) for the 3 variants. Run from anywhere.
set -e
ES="/c/Users/hama101/Desktop/geek/ai trader/AAA EAs/EA store"; S="/c/Users/hama101/Desktop/geek/ai trader/AAA EAs/BM Trading Robust Sets 2026-08-04"
cd "$ES"; SKIP=FX_EX uv run python "$S/FTMO vs Exness 2026-11-24/build5y.py"
cd "$S/Multi Firm Funded 2026-11-17"
for v in _FX_EX _FX_FT _FX_FTS; do
  VARIANT=$v uv run --project "$ES" python sim.py days
  VARIANT=$v uv run --project "$ES" python first_payout.py | grep -E "FTMO_1S|FTMO_2S" | cut -c1-200
done
echo PASS5Y DONE
