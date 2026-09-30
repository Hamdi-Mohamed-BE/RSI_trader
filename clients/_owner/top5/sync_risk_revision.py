"""Retain old benchmark evidence honestly when delivering changed sizing logic."""
import json
from build import ROOT,CLIENT
def main():
    m=json.loads((ROOT/'manifest.json').read_text());d=json.loads((ROOT/'report-data.json').read_text())
    assert d['licence']==m['licence']
    for bot,row in zip(d['bots'],m['entries']):
        assert bot['slug']==row['slug'];bot['ex5_sha256']=row['ex5_sha256']
    d['riskPolicyRevision']=True
    d['licenceEditionNote']='RISK POLICY CHANGED: delivered EAs now use the broker minimum lot when selected risk is too small, potentially exceeding your chosen risk. All performance charts and 20 benchmarks shown are historical results of the PREVIOUS skip-below-minimum builds, not backtests of these delivered binaries. Trade counts, returns and drawdown may change. Demo validation is required.'
    (ROOT/'report-data.json').write_text(json.dumps(d,indent=2))
    t=(ROOT/'report.template.html').read_text(encoding='utf-8')
    (CLIENT/'Performance and Setup.html').write_text(t.replace('__DATA__',json.dumps(d,separators=(',',':')).replace('<','\\u003c')),encoding='utf-8')
if __name__=='__main__':main()
