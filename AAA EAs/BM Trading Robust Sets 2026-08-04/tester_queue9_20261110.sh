#!/bin/bash
# After tester_queue8 (website -> USDJPY -> Vault): Overnight Bias ORB, then Gold Band Wave. One tester at a time.
B="/c/Users/hama101/Desktop/geek/ai trader/AAA EAs/BM Trading Robust Sets 2026-08-04"; E="/c/Users/hama101/Desktop/geek/ai trader/AAA EAs/EA store"
until [ -f "$B/Vault Break Optimization 2026-11-10/DONE.flag" ]; do sleep 60; done
sleep 20
cd "$E" && uv run python "$B/Overnight Bias ORB Optimization 2026-11-10/opt.py" > "$B/Overnight Bias ORB Optimization 2026-11-10/opt.log" 2>&1; echo "onb exit $?"
cd "$E" && uv run python "$B/Gold Band Wave Optimization 2026-11-10/opt.py" > "$B/Gold Band Wave Optimization 2026-11-10/opt.log" 2>&1; echo "gbw exit $?"
touch "$B/Gold Band Wave Optimization 2026-11-10/DONE.flag"
