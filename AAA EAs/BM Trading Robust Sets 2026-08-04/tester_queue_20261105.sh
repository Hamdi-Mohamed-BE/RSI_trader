#!/usr/bin/env bash
# One tester at a time (owner rule). Waits for the running Nasdaq chain, then: Nasdaq new versions, Nasdaq streams inputs + FTMO queue, USDJPY optimisation.
B="/c/Users/hama101/Desktop/geek/ai trader/AAA EAs/BM Trading Robust Sets 2026-08-04"; N="$B/Nasdaq 5M Candle Rule 2026-11-05"; U="$B/USDJPY London Optimization 2026-11-05"
until grep -q "STREAMS DONE" "$N/streams.log" 2>/dev/null; do sleep 30; done
cd "$B/../EA store"
uv run python "$N/nas.py" native > "$N/native2.log" 2>&1; echo "nasdaq native2 exit $?"
uv run python "$N/nas.py" streams > "$N/streams2.log" 2>&1; echo "nasdaq streams2 exit $?"
uv run --with pandas --with numpy python "$N/nas.py" inputs > "$N/inputs.log" 2>&1; echo "nasdaq inputs exit $?"
(uv run --with pandas --with numpy python "$N/nas.py" runall 8 > "$N/runall.log" 2>&1 &)
uv run python "$U/opt.py" > "$U/opt.log" 2>&1; echo "usdjpy opt exit $?"
