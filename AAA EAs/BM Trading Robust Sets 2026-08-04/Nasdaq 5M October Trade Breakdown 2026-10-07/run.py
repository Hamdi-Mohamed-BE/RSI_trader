"""Exact production EX5; reuse the verified isolated native tester harness."""
from pathlib import Path
import importlib.util, json

R=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('october_native',R.parent/'Nasdaq Opening Candle Duration Comparison 2026-10-07/run.py')
d=importlib.util.module_from_spec(spec); spec.loader.exec_module(d)
d.R=R
d.DEST=d.T/'MQL5/Experts/AAA Research/OpeningDuration20261007'
assert d.sha(d.PROD)=='fe9f391db5af2bc3cb0b36e52ae5c0775786c8cb8353abe8b8b7542a2bc72dca'
d.save(R/'SNAPSHOT.json',dict(reference_tick_utc='2026-10-07T14:54:27.897+00:00',reference_tick_bid=31008.36,reference_tick_ask=31009.14,
    note='Read-only live quote reference; actual native history cutoff is independently reported.'))
held=d.lease()
try:
    result=d.run_case(5,'October',production=True,start='2026-10-01',end='2026-10-08',tag='OctoberCurrent20261007')
    d.save(R/'RESULTS.json',result)
    print(json.dumps(dict(native=result['native'],summary=result['summary'],trades=result['trades']),indent=2),flush=True)
finally:
    held.close()
