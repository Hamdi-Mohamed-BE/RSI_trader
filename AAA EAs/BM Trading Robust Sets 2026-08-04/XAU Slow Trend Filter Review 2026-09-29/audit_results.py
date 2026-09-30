"""Independent ledger, sizing geometry, frequency and cooldown checks."""
from pathlib import Path
from datetime import datetime
import json,hashlib,math
ROOT=Path(__file__).resolve().parent
def main():
    results=[]
    for path in sorted((ROOT/'native').glob('*/result.json')):
        row=json.loads(path.read_text());m=row['metrics'];ts=json.loads(path.with_name('trades.json').read_text())
        assert len(ts)==m['trades']
        assert abs(sum(t['net_profit'] for t in ts)-m['net_profit'])<.05
        start=datetime.strptime(row['start'],'%Y.%m.%d');end=datetime.strptime(row['end'],'%Y.%m.%d')
        previous=None;minimum=None
        for t in ts:
            entry=datetime.fromisoformat(t['open_time']);exit=datetime.fromisoformat(t['close_time'])
            assert start<=entry<=exit<end
            assert t['symbol']=='XAUUSD' and t['volume']>0
            assert abs(t['gross_profit']+t['commission']+t['swap']-t['net_profit'])<.011
            assert abs(t['gross_profit']-((t['close_price']-t['open_price'])*(1 if t['side']=='Long' else -1)*100*t['volume']))<.06
            if previous:
                assert entry>=datetime.fromisoformat(previous['close_time'])
                assert (entry-datetime.fromisoformat(previous['open_time'])).total_seconds()>=86400
                delta=(entry-datetime.fromisoformat(previous['close_time'])).total_seconds()/3600
                minimum=delta if minimum is None else min(minimum,delta)
                if int(row['inputs'].get('ResearchExitCooldownHours','0'))==24:assert delta>=24
            previous=t
        results.append(dict(case=row['case'],trades=len(ts),cash_reconciled=True,no_overlap=True,entry_cooldown=True,min_exit_to_next_entry_hours=minimum,nonzero_flags={k:v for k,v in row['flags'].items() if v}))
    build=json.loads((ROOT/'BUILD.json').read_text());assert all(hashlib.sha256(Path(p).read_bytes()).hexdigest()==h for p,h in build.items())
    assert json.loads((ROOT/'PARITY.json').read_text())['passed']
    out=dict(completed_native_tests=len(results),unique_parameter_vectors=len({(json.loads(p.read_text())['variant']) for p in (ROOT/'native').glob('*/result.json')}),checks=results,warning='The account history and recent baseline were already observed; recent windows are not an untouched holdout.')
    (ROOT/'AUDIT.json').write_text(json.dumps(out,indent=2));print(json.dumps(out,indent=2))
if __name__=='__main__':main()
