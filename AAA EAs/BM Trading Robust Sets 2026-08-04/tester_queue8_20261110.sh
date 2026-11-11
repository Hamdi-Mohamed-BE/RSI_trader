#!/bin/bash
# Owner 2026-11-10: one tester at a time. Website runs (already running) -> website cache build -> USDJPY optimisation resume -> Vault Break optimisation.
B="/c/Users/hama101/Desktop/geek/ai trader/AAA EAs/BM Trading Robust Sets 2026-08-04"; M="$B/Merge 1Step 60d Search 2026-11-10"; E="/c/Users/hama101/Desktop/geek/ai trader/AAA EAs/EA store"
until grep -q "STAGE DONE web" "$M/tester-web.log" 2>/dev/null; do sleep 30; done
sleep 20
cd "$E" && uv run python "$M/build_web.py" > "$M/build_web.log" 2>&1; echo "build_web exit $?"
echo "USDJPY search resuming (tester_queue8)" >> "$B/USDJPY London Optimization 2026-11-05/opt.log"
cd "$E" && uv run python "$B/USDJPY London Optimization 2026-11-05/opt.py" >> "$B/USDJPY London Optimization 2026-11-05/opt.log" 2>&1; echo "usdjpy exit $?"
cd "$E" && uv run python "$B/Vault Break Optimization 2026-11-10/opt.py" > "$B/Vault Break Optimization 2026-11-10/opt.log" 2>&1; echo "vault exit $?"
touch "$B/Vault Break Optimization 2026-11-10/DONE.flag"
