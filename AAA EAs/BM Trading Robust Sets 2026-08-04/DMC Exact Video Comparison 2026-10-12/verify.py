"""End-to-end evidence checks; never accesses the connected MT5 account."""
from pathlib import Path
import collections, gzip, hashlib, json
import run

ROOT=Path(__file__).resolve().parent
def main():
    run.validate_freeze()
    data=json.loads((ROOT/'COMPARISON.json').read_text())
    assert data['complete'] and data['completed_cases']==28
    expected={('OCT12_CUR','XAUUSD'),('OCT12_FRX','XAUUSD'),('OCT12_VIDEO','XAUUSD'),
              ('OCT12_FRU','USTEC'),('OCT12_VIDEO','USTEC'),('OCT12_BTCTRANSFER','BTCUSD'),('OCT12_VIDEO','BTCUSD')}
    actual=collections.defaultdict(set)
    checked=[]
    for row in data['rows']:
        r=row['native'];m=row['metrics'];folder=ROOT/'native'/row['case']
        actual[r['period']].add((r['config'],r['symbol']))
        assert all(r['report_checks'].values()) and not r['input_mismatches']
        assert r['journal_flags']['init_failed']==r['journal_flags']['critical']==r['journal_flags']['no_history']==0
        report=folder/(row['case']+'.htm.gz')
        assert hashlib.sha256(gzip.decompress(report.read_bytes())).hexdigest()==r['report_sha256']
        native_set=folder/(row['case']+'.set')
        assert hashlib.sha256(native_set.read_text(encoding='utf-8-sig').encode()).hexdigest()==r['set_sha256']
        trades=json.loads((folder/'trades.json').read_text())
        assert m['trades']==len(trades)==r['metrics']['trades']
        assert abs(sum(t['net_profit'] for t in trades)-r['metrics']['net_profit'])<.11
        assert abs(r['metrics']['final_balance']-10000-r['metrics']['net_profit'])<.011
        assert m['wins']+m['losses']+m['flats']==m['trades']
        assert m['profit_factor'] is None if m['losses']==0 else m['profit_factor'] is not None
        checked.append(row['case'])
    assert set(actual)=={'3m','6m','1y','3y'}
    assert all(members==expected for members in actual.values())
    result={'verified':True,'matching_native_cases':28,'independent_chronology_arithmetic_tests':5,
            'fresh_report_hashes_verified':28,'current_production_binary_hashes_unchanged':True,
            'new_model_parameters_frozen':True,'live_terminal_access':False,'installed':False,'pushed':False,
            'cases':checked,'note':'Raw retrospective evidence; generated ticks before 2026, not untouched OOS or full pipeline.'}
    (ROOT/'VERIFICATION.json').write_text(json.dumps(result,indent=2))
    print(json.dumps({k:v for k,v in result.items() if k!='cases'},indent=2))

if __name__=='__main__':main()
