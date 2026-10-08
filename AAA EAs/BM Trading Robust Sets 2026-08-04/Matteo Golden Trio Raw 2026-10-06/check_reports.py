"""Final artifact QA: links, yearly/monthly cash flows, evidence and no promotion."""
from pathlib import Path
from html.parser import HTMLParser
from urllib.parse import urlparse,unquote
import json
import pandas as pd
import run as r

class Links(HTMLParser):
    def __init__(self):super().__init__();self.links=[];self.charts=0
    def handle_starttag(self,tag,attrs):
        if tag=='a':self.links.extend(v for k,v in attrs if k=='href')
        if tag=='svg':self.charts+=1

checked=[]
for mode,(name,tf,slug) in r.CASES.items():
    root=r.R/slug;result=json.loads((root/'results.json').read_text());audit=json.loads((root/'verification.json').read_text())
    assert audit['ok'] and audit['entries_verified']==result['summary']['trades']
    assert sum(x['trades'] for x in result['years'])==result['summary']['trades']
    assert abs(sum(x['net'] for x in result['years'])-result['summary']['net'])<.001
    monthly=pd.read_csv(root/'Monthly.csv');assert monthly.trades.sum()==result['summary']['trades']
    assert abs(monthly.net.sum()-result['summary']['net'])<.001
    page=root/'Results.html';parser=Links();body=page.read_text(encoding='utf-8');parser.feed(body)
    local=[unquote(urlparse(link).path) for link in parser.links if not urlparse(link).scheme]
    assert all((page.parent/link).exists() for link in local),local
    assert parser.charts==1 and result['native']['history_quality'] in body
    baseline=r.R/'Execution Audit Baseline - not final'/slug/'trades.json'
    if mode in [1,3]:
        assert json.loads(baseline.read_text())==json.loads((root/'native/trades.json').read_text()),'Quote-check regression changed unrelated strategy'
    checked.append({'strategy':name,'local_links':len(local),'annual_and_monthly_parity':True,'entries':audit['entries_verified']})
index=r.R/'Results.html';parser=Links();parser.feed(index.read_text(encoding='utf-8'))
assert parser.charts==3
assert all((index.parent/unquote(urlparse(link).path)).exists() for link in parser.links if not urlparse(link).scheme)
config=json.loads((r.R/'run-config.json').read_text());assert config['optimisation'] is False and config['live_changes'] is False
r.save(r.R/'report-qa.json',{'ok':True,'reports':checked,'independent_charts':3,'no_live_changes':True,'vault_overnight_trade_for_trade_regression':True})
print(json.dumps(checked,indent=2))
