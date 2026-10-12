Five ORBs at 0.5R: October 12, 2026 intraday reconstruction

Open Results.html. Results.json records the observed cutoff, assumptions and
per-EA decisions. This was an offline rule/tick replay, not a completed native
MT5 Strategy Tester run or guarded shared-equity portfolio simulation.

The account-bound broker snapshots, account-specific fetch script and failed
native current-day attempt remain local. They are deliberately not published.
replay_connected.py requires those private input snapshots to rerun. Their data
digest is retained in Results.json for provenance. No live order or installation
was performed by this replay.
