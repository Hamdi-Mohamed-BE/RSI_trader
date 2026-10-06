# Report-label compatibility correction

The first H4 development run completed. The D1 run also completed and generated a fresh native report, but parsing stopped before its metrics were analysed: MT5 spells its Period field `Daily`, not `D1`. Weekly reports can similarly use `Weekly` instead of `W1`.

`resume.py` normalises only these exact labels in the in-memory Period HTML cell used by the existing report reader. Raw native reports, their hashes, inputs, dates, trades, accounting, source, frozen search values, ranking and qualification gates remain unchanged. It retains the original frozen runner and pre-search time-exit guard. The already-completed D1 report is reanalysed from its archived journal and untouched audit exports, rather than changing or rerunning its trading rules. This correction and wrapper are separately hash-frozen before resuming the search.
