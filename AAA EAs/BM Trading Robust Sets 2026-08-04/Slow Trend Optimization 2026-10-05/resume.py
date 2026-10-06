"""Resume frozen search with exact MT5 Daily/Weekly report-label compatibility."""
from pathlib import Path
import hashlib,importlib.util,json,msvcrt,re
R=Path(__file__).resolve().parent
sp=importlib.util.spec_from_file_location('guarded_slow_search',R/'search.py')
s=importlib.util.module_from_spec(sp);sp.loader.exec_module(s)
p=s.p
raw_read=p.n.h._read_report

def read_report(path):
    body=raw_read(path)
    return re.sub(r'(<td[^>]*>Period:</td>\s*<td[^>]*>\s*<b>)(Daily|Weekly)(?=\s*\()',
        lambda m:m[1]+{'Daily':'D1','Weekly':'W1'}[m[2]],body,flags=re.I)

if __name__=='__main__':
    previous={name:hashlib.sha256((R/name).read_bytes()).hexdigest() for name in ['search.py','PRESEARCH AMENDMENT.md']}
    assert json.loads((R/'PRESEARCH FROZEN.json').read_text())==previous
    signature={name:hashlib.sha256((R/name).read_bytes()).hexdigest() for name in ['resume.py','REPORT LABEL AMENDMENT.md']}
    frozen=R/'REPORT LABEL FROZEN.json'
    if frozen.exists():assert json.loads(frozen.read_text())==signature
    else:p.save(frozen.name,signature)
    assert p.n.freeze()==json.loads((R/'build.json').read_text())['frozen']
    p.canonical=s.canonical
    p.n.h._read_report=read_report
    with (p.n.B/'LTA VWAP Developing POC Comparison 2026-10-05/tester.lock').open('a+b') as lease:
        lease.seek(0);msvcrt.locking(lease.fileno(),msvcrt.LK_NBLCK,1)
        tag='D-88d7e58244ef1f'
        out=R/'native'/tag
        if not (out/'results.json').exists():
            case=json.loads((out/'manifest.json').read_text())['case']
            p.n.CASES[tag]=case
            p.n.run(tag,reanalyze=True)
        p.search();p.plateau();p.choose();p.confirm()
