# MT5 integration agents

This directory contains the versioned MQL5 protocol include and the optional master/follower low-latency integration agents. The normal Windows launcher currently uses the qualified Python MT5 reconciliation path, which does not require attaching these EAs.

## Installation

1. Copy `Include/AAA/CopierProtocol.mqh` into the terminal's `MQL5/Include/AAA` directory.
2. Copy the appropriate file from `Experts` into `MQL5/Experts`.
3. Compile in MetaEditor and attach exactly one agent to a dedicated chart in each portable terminal.
4. Copy the account UUID and pipe name from the control plane into the EA inputs.

Both agents are disabled by default. The executor currently exercises connection, identity, framing, acknowledgement, and safety-gate behavior but deliberately rejects order placement. Do not weaken this boundary until the demo qualification checklist in `PLAN.md` passes with actual broker demo terminals.

The hot-path protocol is UTF-8-compatible JSON, one message per newline, over local Windows named pipes. Account passwords never appear in EA inputs, JSON messages, or process arguments.
