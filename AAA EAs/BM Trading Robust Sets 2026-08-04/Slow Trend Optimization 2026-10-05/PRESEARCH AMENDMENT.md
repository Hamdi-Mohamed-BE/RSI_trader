# Pre-search implementation correction

Written before any development screen or candidate selection. Smoke and two shipped-reference parity checks are already complete; no candidate outcomes have been observed.

The frozen protocol specifies an exit-mode3 no-target alternative with a5-day limit. The staged daily-management dictionary can reset an inherited hold limit to0, accidentally creating an unlimited hold rather than the specified time exit. `search.py` wraps canonical inputs to retain5days when exit-mode3 is paired with hold0. Explicit2/5-day limits remain unchanged. This enforces the already-written protocol, changes no original/normal/FTMO reference, search value, ranking threshold, signal engine or production file. Source, original plan and runner hashes remain frozen; the wrapper and this correction have their own frozen signature before search.

Structural stops with no numeric distance parameter cannot supply the full intended joint distance neighbourhood; they get the available RR neighbourhood or are rejected when fewer than3 distinct points exist. This limited check is reported, not presented as a full9-point plateau.
