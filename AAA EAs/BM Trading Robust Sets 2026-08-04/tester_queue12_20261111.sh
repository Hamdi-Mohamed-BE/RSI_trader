#!/bin/bash
# 2026-11-11: Gold Band Wave (parity now path-only when only swap differs), then Vault Break. One tester at a time.
B="/c/Users/hama101/Desktop/geek/ai trader/AAA EAs/BM Trading Robust Sets 2026-08-04"; E="/c/Users/hama101/Desktop/geek/ai trader/AAA EAs/EA store"
G="$B/Gold Band Wave Optimization 2026-11-10"; cd "$E" && uv run python "$G/opt.py" > "$G/opt.log" 2>&1; echo "gbw exit $?"
sleep 30
V="$B/Vault Break Optimization 2026-11-10"; mv "$V/opt.log" "$V/opt-tester-occupied-20261111.log" 2>/dev/null
cd "$E" && uv run python "$V/opt.py" > "$V/opt.log" 2>&1; echo "vault exit $?"
