#!/usr/bin/env bash
# One tester at a time (owner rule). Runs the Sep-to-today comparison in the gap after the Nasdaq native stage; nas.py streams waits for SEP_DONE.flag before it uses the tester.
B="/c/Users/hama101/Desktop/geek/ai trader/AAA EAs/BM Trading Robust Sets 2026-08-04"; N="$B/Nasdaq 5M Candle Rule 2026-11-05"; T="$B/Sep To Today E10 vs FTMO17 2026-11-05"
until grep -qE "^BUYHOLD|Traceback" "$N/native.log"; do sleep 15; done
sleep 20
cd "$B/../EA store"
uv run python "$T/sep.py" native > "$T/native.log" 2>&1; echo "sep native exit $?"
touch "$N/SEP_DONE.flag"
uv run python "$T/sep.py" report > "$T/report.log" 2>&1; echo "sep report exit $?"
