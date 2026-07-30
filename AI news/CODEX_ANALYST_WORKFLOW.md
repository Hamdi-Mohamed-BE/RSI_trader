# Codex Analyst Workflow

The application does not call an LLM provider and never places trades.

## Before a release

1. Open the app 15-30 minutes before a supported event.
2. Enter the event, exact UTC release time, forecast, and previous value.
3. Run the gold-impact prediction.
4. Send the returned `codex_analyst_packet` to Codex in this task.

The answer is `POSITIVE` or `NEGATIVE` for the immediate XAUUSD effect, with
confidence, expected movement, reasons, missing inputs, and invalidation. It is
not an entry or trading instruction.

## At publication

Enter actual, forecast, previous, revision, and an official BLS, BEA, or Federal
Reserve source URL. The post-release analysis may use the published surprise
and statement. Post-release text must never be represented as pre-release data.

## Validation

Run `backtest_gold_direction.py`. It scores every release direction and keeps
the broad and recent holdout windows separate from model selection.
