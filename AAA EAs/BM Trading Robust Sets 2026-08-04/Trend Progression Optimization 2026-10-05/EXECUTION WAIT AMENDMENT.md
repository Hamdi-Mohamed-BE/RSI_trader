# Isolated tester shutdown wait

The ADX stage paused before starting a case because the prior tester's port3000 had not yet released. A read-only check found it had already released a few seconds later; both unrelated live terminals were left untouched.

`resume.py` retains frozen source, plan, runner, parameters and all results. It retries the existing read-only isolated-process/port availability check for at most50seconds, with2second intervals. It never kills any process or bypasses the availability check. Completed cases are reused. This is test orchestration only, not a trading-rule, cost, delay, selection or qualification change. This wrapper and note are separately frozen before resuming.
