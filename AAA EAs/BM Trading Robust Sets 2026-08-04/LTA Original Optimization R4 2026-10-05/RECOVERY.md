# Execution-rejected settings remain rejected

The target screen stopped on D-18b933befe1e45: one order failure, 1034 executed positions. All executed deals reconciled to MT5 before the zero-failure qualification check. The configuration is ineligible; its executed results are not a qualified candidate.

The frozen EA, input choices, selection thresholds and original runner remain untouched. resume.py changes orchestration only: preserve exact arithmetic for an execution-rejected pass, mark it disqualified before ranking, and continue the other frozen settings. It catches only the specific execution-counter AssertionError after a completed report and deal audit. Other unexpected errors still stop work. Rejected settings cannot enter carry, plateau finalists, selection or recent replays. A frozen recovery-runner hash records this continuation.

No production EA, BAT, website, SET or account change; no unrecorded parameter retuning. This is a research campaign repair, not a claim that failed execution is safe.
