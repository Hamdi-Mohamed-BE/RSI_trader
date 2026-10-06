# Verified session input correction

The exported native report PARITY-acd50e7a5cd7ae/report.htm and its parsed results show InpResearchBrokerUtcOffsetMinutes=0, inherited from the BASE SET. The R4 protocol's descriptive note assumed the include's default180 rather than the actual SET override. This note was incorrect; no EA input or test was changed to180.

Every pass actually uses offset0. Therefore tested broker-clock windows are Asia00–08, London07–12, NewYork13–21 and overlap13–16. These are fixed presets, not separately verified exchange/DST sessions. The final derived report corrects the description and verifies the exported input. All frozen EA choices, measured results, ranking and validation periods remain unchanged. There is no parameter retuning or production change.
