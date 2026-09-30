"""Isolated client-build benchmarks. Never connects to the production terminal."""
import json,gzip,re,shutil,importlib.util
from pathlib import Path
from build import ROOT,EVIDENCE,TESTER,CLIENT,sha

spec=importlib.util.spec_from_file_location('recent',EVIDENCE/'run.py')
r=importlib.util.module_from_spec(spec);spec.loader.exec_module(r)
b=r.b
b.ROOT=ROOT;b.OUT=ROOT/'tests-native';b.STATUS=b.OUT/'status.json'
b.CONFIG.update(expert_dir='CalyxClientTop5',timeout_seconds=3600)

def main():
    assert not b.isolated_running() and not b.port_3000_busy(),'Research tester occupied'
    assert not list((TESTER/'MQL5/Profiles/Charts'/b.CONFIG['profile']).glob('*.chr'))
    common=b.text(TESTER/'Config/common.ini')
    assert int(re.search(r'(?im)^Login\s*=\s*(\d+)',common)[1])==int(r.PRIVATE)
    del common
    b.OUT.mkdir(exist_ok=True)
    manifest=json.loads((ROOT/'manifest.json').read_text())
    dest=TESTER/'MQL5/Experts'/b.CONFIG['expert_dir'];dest.mkdir(exist_ok=True)
    for row in manifest['entries']:
        ex=CLIENT/row['expert'];assert sha(ex)==row['ex5_sha256']
        shutil.copy2(ex,dest/ex.name)
        for mode,value in [('fixed',100),('balance',1)]:
            tag=row['slug']+'-'+mode
            inputs=row['inputs']|{'ClientRiskMode':'0' if mode=='fixed' else '1','ClientRiskValue':str(value)}
            b.CONFIG.update(expert_file=ex.name,period=row['period'],common_inputs=inputs,variants={tag:{'inputs':{}}})
            for period in b.CONFIG['periods']:
                done=b.OUT/f"nw-{row['symbol']}-{tag}-{period}"/'run.json'
                if done.exists():
                    old=json.loads(done.read_text())
                    assert old.get('ex5_sha256',row['ex5_sha256'])==row['ex5_sha256'],'Stale binary evidence'
                    if old.get('audited'):continue
                m=b.run_case(row['symbol'],tag,period)
                folder=b.OUT/m['case'];report=b.REPORT_DIR/(m['case']+'.htm')
                actual=b._report_inputs(report)
                actual.update(dict(re.findall(r'<b>(Client\w+)=([^<]*)</b>',b._read_report(report))))
                assert all(k in actual and b._same_setting(v,actual[k]) for k,v in inputs.items()),'Inputs missing'
                trades=r.closing_deals(report,m['case'])
                assert len(trades)==m['metrics']['trades']
                assert abs(sum(t['net_profit'] for t in trades)-m['metrics']['net_profit'])<max(.05,len(trades)*.011)
                assert not m['journal_flags']['init_failed'] and not m['journal_flags']['critical']
                j=gzip.decompress((folder/'journal.txt.gz').read_bytes()).decode()
                audits=re.findall(r'CLIENT_ENTRY mode=(\d+) target=([\d.]+) planned=([\d.]+)',j)
                assert audits or not trades,'No risk audit entries'
                assert all(float(p)<=float(t)+.011 for _,t,p in audits),'Risk rounding exceeded budget'
                m.update(audited=True,ex5_sha256=row['ex5_sha256'],risk_mode=mode,risk_value=value,risk_audits=len(audits),slug=row['slug'])
                m['metrics']['relative_equity_dd_pct']=b._number(b._metric(b._read_report(report),'Equity Drawdown Relative'))
                (folder/'trades.json.gz').write_bytes(gzip.compress(json.dumps(trades).encode(),mtime=0))
                m['trades_sha256']=sha(folder/'trades.json.gz')
                done.write_text(json.dumps(m,indent=2))
    b.summary();b.status(state='ALL DONE',event='20 client build benchmarks audited')

if __name__=='__main__':main()
