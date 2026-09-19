"""Individual native HTML reproductions and bounded execution-cost sensitivity."""
import json,shutil
import run_research as r

def main():
    r.compile_ea()
    archive=r.ROOT/'Batch Reproductions';archive.mkdir(exist_ok=True)
    comparisons=[]
    for case in (0,2):
        path=r.ROOT/'Runs'/f'3y-case{case}-d1.json'
        old=json.loads(path.read_text());shutil.copy2(path,archive/path.name)
        oldtrades=json.loads((r.ROOT/'Audit'/f'3y-case{case}-d1-trades.json').read_text())
        result=r.run('3y',case,1,True)[0]
        newtrades=json.loads((r.ROOT/'Audit'/f'3y-case{case}-d1-trades.json').read_text())
        assert oldtrades==newtrades,'Native individual run did not reproduce batch trade ledger'
        for k in ('net_profit','trades','net_pf','net_win_rate','max_equity_dd_pct','observed_equity_dd_pct','commission','swap'):
            assert old[k]==result[k],(case,k,old[k],result[k])
        comparisons.append({'case':case,'batch_report':old['report'],'individual_report':result['report'],'all_trades_identical':True})
    for case in (0,2):r.run('6m',case,1000)
    r.save(r.ROOT/'reproduction-checks.json',comparisons)
    print('INDIVIDUAL NATIVE REPRODUCTIONS VERIFIED',flush=True)
if __name__=='__main__':main()
