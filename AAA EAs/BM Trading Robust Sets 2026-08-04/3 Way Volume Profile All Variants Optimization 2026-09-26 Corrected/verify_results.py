"""Read-only evidence checks plus a generated verification summary."""
import gzip
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
import native_engine as e
import run_all as r
import make_report

def main():
    rows=make_report.build()
    checks=[]
    def check(name,passed,details=None):
        checks.append(dict(check=name,passed=bool(passed),details=details))
    e.q.verified_build()
    check('Original frozen production/research dependencies unchanged',True)
    check('All 32 asset/setup comparisons present',len(rows)==32)
    identities={(x['symbol'],x['variant']) for x in rows}
    check('Each requested asset/setup occurs exactly once',identities=={(s,v) for s in r.SYMBOLS for v in r.VARIANTS.values()} and len(rows)==len(identities))
    for symbol in r.SYMBOLS:
        p=e.ROOT/f'parity-{symbol}.json'
        parity=json.loads(p.read_text()) if p.exists() else []
        check(symbol+' raw parity',len(parity)==4 and all(x['net_equal'] and x['trades_equal'] and x['pf_equal'] for x in parity))
        raw_path=e.OUT/(symbol+'-raw-parity')/'results.json'
        if raw_path.exists():
            for baseline in json.loads(raw_path.read_text()):
                variant=r.VARIANTS[baseline['parameters']['setups']]
                actual=json.loads((Path(baseline['audit_folder'])/'positions.json').read_text())
                source=e.q.RAW/'native'/f'3wvp-{symbol}-{variant}-1y'/'trades.json.gz'
                expected=json.loads(gzip.decompress(source.read_bytes()))
                expected.sort(key=lambda p:(p['close_time'],p['open_time']))
                actual.sort(key=lambda p:(p['close_time'],p['open_time']))
                stamp=lambda s:int(datetime.fromisoformat(s).replace(tzinfo=timezone.utc).timestamp())
                same=len(actual)==len(expected) and all(
                    a['open_time']==stamp(b['open_time']) and a['close_time']==stamp(b['close_time'])
                    and abs(a['pnl']-b['net_profit'])<=.021 for a,b in zip(actual,expected))
                check(symbol+' '+variant+' raw trade-by-trade parity',same)
        dev=e.ROOT/f'development-{symbol}.json'
        ledger=json.loads(dev.read_text()) if dev.exists() else []
        for mask,variant in r.VARIANTS.items():
            stages={x['stage'] for x in ledger if x['parameters']['setups']==mask}
            check(symbol+' '+variant+' every search stage completed',stages==set(r.STAGES+['stability']))
        selected_path=e.ROOT/f'selection-{symbol}.json'
        comparison=e.OUT/(symbol+'-last-year-audited')
        frozen_path=comparison/'manifest.json'
        frozen=json.loads(frozen_path.read_text()) if frozen_path.exists() else {}
        selected=json.loads(selected_path.read_text()) if selected_path.exists() else []
        check(symbol+' selection frozen before final comparison report',
              selected_path.exists() and (comparison/'results.json').exists() and
              [x['validation']['parameters'] for x in selected]==frozen.get('cases') and
              frozen_path.stat().st_mtime <= (comparison/'results.json').stat().st_mtime)
        for period in ['validation-audited','last-year-audited']:
            folder=e.OUT/(symbol+'-'+period); path=folder/'results.json'
            records=json.loads(path.read_text()) if path.exists() else []
            check(symbol+' '+period+' native case count',len(records)==(8 if period.startswith('validation') else 4))
            if not records: continue
            report=next(folder.glob('*.xml.gz'))
            sha=hashlib.sha256(gzip.decompress(report.read_bytes())).hexdigest()
            manifest=json.loads((folder/'manifest.json').read_text())
            check(symbol+' '+period+' correct Model 4 and current source',manifest['model']==4 and manifest['logic_sha']==e.h.sha(e.EA/'SearchLogic.mqh') and manifest['audit_sha']==e.h.sha(e.EA/'ExportAudit.mqh'))
            for record in records:
                positions=json.loads((Path(record['audit_folder'])/'positions.json').read_text())
                pm=record['position_metrics']
                check(symbol+' '+period+' case '+str(record['index'])+' cash, count, report hash',
                    abs(sum(x['pnl'] for x in positions)-pm['net_profit'])<=.02 and
                    len(positions)==pm['trades'] and
                    len({x['position_id'] for x in positions})==len(positions) and sha==record['report_sha'])
                check(symbol+' '+period+' case '+str(record['index'])+' no positions outside requested period',
                    all(int(__import__('datetime').datetime.strptime(manifest['start'],'%Y.%m.%d').replace(tzinfo=__import__('datetime').timezone.utc).timestamp()) <= p['open_time'] <= p['close_time'] < int(__import__('datetime').datetime.strptime(manifest['end'],'%Y.%m.%d').replace(tzinfo=__import__('datetime').timezone.utc).timestamp()) for p in positions))
    summary=dict(passed=all(x['passed'] for x in checks),checks=checks,
                 total_checks=len(checks),failed=[x for x in checks if not x['passed']],
                 combinations=len(rows),development_passes=sum(x['development_passes'] for x in rows),
                 unique_vectors=sum(x['unique_vectors'] for x in rows),
                 validation_qualified=sum(x['validation_qualified'] for x in rows),
                 improved_last_year=sum(x['optimized']['return_pct']>x['raw']['return_pct'] for x in rows))
    e.dump(e.ROOT/'VERIFICATION.json',summary)
    print(json.dumps({k:v for k,v in summary.items() if k!='checks'},indent=2))
    if not summary['passed']: raise SystemExit(1)

if __name__=='__main__': main()
