#!/bin/bash
# Replaces queue9 (stopped 2026-11-10 23:41 after the Vault parity end-date fix). Waits for the running ONB study (python PID 8908), re-runs ONB only if it did not finish,
# then Vault Break, then Gold Band Wave. One tester at a time.
B="/c/Users/hama101/Desktop/geek/ai trader/AAA EAs/BM Trading Robust Sets 2026-08-04"; E="/c/Users/hama101/Desktop/geek/ai trader/AAA EAs/EA store"
while tasklist //FI "PID eq 8908" 2>/dev/null | grep -q 8908; do sleep 60; done
sleep 20
O="$B/Overnight Bias ORB Optimization 2026-11-10"
if ! grep -q "SEARCH DONE" "$O/opt.log"; then mv "$O/opt.log" "$O/opt-first-attempt.log"; cd "$E" && uv run python "$O/opt.py" > "$O/opt.log" 2>&1; echo "onb rerun exit $?"; else echo "onb finished first time"; fi
cd "$E" && uv run python "$B/Vault Break Optimization 2026-11-10/opt.py" > "$B/Vault Break Optimization 2026-11-10/opt.log" 2>&1; echo "vault exit $?"
cd "$E" && uv run python "$B/Gold Band Wave Optimization 2026-11-10/opt.py" > "$B/Gold Band Wave Optimization 2026-11-10/opt.log" 2>&1; echo "gbw exit $?"
touch "$B/Gold Band Wave Optimization 2026-11-10/DONE.flag"
