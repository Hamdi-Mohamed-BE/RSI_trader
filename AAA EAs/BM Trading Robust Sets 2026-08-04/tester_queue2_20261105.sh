#!/usr/bin/env bash
# One tester at a time (owner rule). Runs the US30 raw test once the Nasdaq work has finished: opt.py starts last in tester_queue_20261105.sh and then waits for DONE.flag before using the tester.
B="/c/Users/hama101/Desktop/geek/ai trader/AAA EAs/BM Trading Robust Sets 2026-08-04"; T="$B/US30 5M Momentum Raw 2026-11-05"
until [ -f "$B/USDJPY London Optimization 2026-11-05/opt.log" ]; do sleep 30; done
cd "$B/../EA store"
uv run python "$T/us30.py" native > "$T/native.log" 2>&1; echo "us30 native exit $?"
touch "$T/DONE.flag"
