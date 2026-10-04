"""Short isolated native smoke tests; never attach to an active trading terminal."""
from pathlib import Path
import ast, csv, gzip, hashlib, importlib.util, io, json, shutil
from datetime import datetime, timezone

ROOT=Path(__file__).resolve().parent
OLD=ROOT.parent/'Indices Hourly EA Pipeline 2026-10-03/run_native.py'
spec=importlib.util.spec_from_file_location('frozen_native_runner',OLD)
n=importlib.util.module_from_spec(spec);spec.loader.exec_module(n)
n.R=ROOT; n.SOURCE=ROOT/'EA/CalyxHourlyProfiles History Sized.mq5'
n.DEST=n.T/'MQL5/Experts/AAA Research/HourlyProfilesSized20261004'
n.WINDOWS={'smoke':'2026.09.28'}

def main():
    n.free()
    n.DEST.mkdir(parents=True,exist_ok=True)
    shutil.copy2(n.SOURCE.with_suffix('.ex5'),n.DEST/'CalyxHourlyProfiles.ex5')
    source=OLD.read_text()
    f=next(x for x in ast.parse(source).body if isinstance(x,ast.FunctionDef) and x.name=='one')
    code=ast.get_source_segment(source,f).replace('HourlyProfiles20261003','HourlyProfilesSized20261004').replace('hourprofiles20261003','hourprofilesSized20261004').replace('hourprof-20261003','hoursized-v111-20261004')
    code=code.replace("'lots':1,'model':4", "'configured_sizing_mode':(2 if variant=='fixed50' else 1),'risk_percent':0.5,'fixed_cash':50,'model':4")
    code=code.replace("text=(R/(asset+'.set')).read_text()", "text=(R/'Sets'/(asset+'.set')).read_text().replace('InpSizingMode=1','InpSizingMode='+('2' if variant=='fixed50' else '1'))")
    exec(compile(code,'sized_native_smoke','exec'),n.__dict__)
    out=[]
    for asset in ('US30','US100'):
        for variant in ('balance05','fixed50'):
            result=n.one(asset,'smoke',variant)
            folder=ROOT/'native'/result['tag']
            deals=list(csv.DictReader(io.StringIO(gzip.decompress((folder/'deals.csv.gz').read_bytes()).decode())))
            entries=[r for r in deals if r['entry']=='0']
            assert entries and not result['account_failure']
            fills=list(csv.DictReader(io.StringIO(gzip.decompress((folder/'fills.csv.gz').read_bytes()).decode())))
            cash=list(csv.DictReader(io.StringIO(gzip.decompress((folder/'curve.csv.gz').read_bytes()).decode())))
            reference=611.53 if asset=='US30' else 358.71
            for entry in entries:
                t=int(entry['time_msc'])/1000
                # Curves store balance at next minute, so only use observations
                # wholly before the entry for an approximate independent size check.
                def curve_time(value):
                    return float(value) if value.isdigit() else datetime.strptime(value,'%Y.%m.%d %H:%M:%S').replace(tzinfo=timezone.utc).timestamp()
                earlier=[float(c['balance_at_next_sample']) for c in cash if curve_time(c['utc_minute'])+60<t]
                balance=earlier[-1] if earlier else 10000
                expected=max(.05 if asset=='US30' else .01,math.floor((50 if variant=='fixed50' else balance*.005)/reference/.01+1e-9)*.01)
                # Few-cent changes/tick rounding can straddle a single lot step.
                assert abs(float(entry['volume'])-expected)<=.01000001
            record=dict(asset=asset,mode=variant,entries=len(entries),volumes=sorted({float(r['volume']) for r in entries}),
                        no_account_failure=True,report_sha256=result['report_sha256'],inputs_sha256=result['set_sha256'],
                        expert_sha256=n.sha(n.SOURCE.with_suffix('.ex5')),
                        approximate_independent_volume_check=True,window=['2026-09-28','2026-10-03 exclusive'])
            out.append(record)
            (ROOT/'FUNCTIONAL.json').write_text(json.dumps(dict(passed=len(out)==4,checks=out,no_active_terminal_changed=True),indent=2))
    print(json.dumps(out))

import math
if __name__=='__main__': main()
