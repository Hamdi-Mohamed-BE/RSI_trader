"""Verify every native individual-engine selection run, separate from final diagnostics."""
import hashlib,json
from params import ROOT,save
from native import group_stats,hashes
from audit_management import audit

def main():
    dest=ROOT.parent/'3 way gold Independent Engines 2026-09-13'
    rows=[]
    for path in sorted((ROOT/'Runs').glob('ind*.json')):
        r=json.loads(path.read_text())
        assert r['source_hashes']==hashes()
        assert hashlib.sha256((ROOT/r['report']).read_bytes()).hexdigest()==r['report_sha256']
        stem=f"{r['period']}-engine{r['engine']}-d{r['execution_delay_ms']}"
        ts=json.loads((ROOT/'Audit'/(stem+'-trades.json')).read_text())
        s=group_stats(ts)
        for key in ('net_profit','commission','swap','fee'):
            assert abs(s[key]-r[key])<.01,(path,key)
        assert s['trades']==r['trades']
        rows.append(dict(period=r['period'],**audit(r)))
    assert len(rows)==22,('Expected 18 primary and four dedup-audit runs',len(rows))
    save(dest/'native-selection-verification.json',dict(native_runs=rows,source_hashes=hashes(),all_ledgers_reconciled=True))
    print('SELECTION AUDIT PASS',len(rows),'native runs,',sum(x['entries'] for x in rows),'trades')

if __name__=='__main__':main()
