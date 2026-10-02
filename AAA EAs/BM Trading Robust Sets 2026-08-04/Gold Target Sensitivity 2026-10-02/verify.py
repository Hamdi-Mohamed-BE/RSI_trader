"""Read-only evidence checks; does not connect to MT5 or place/modify orders."""
from run import *
import html.parser
class Images(html.parser.HTMLParser):
 def __init__(self):super().__init__();self.images=[]
 def handle_starttag(self,tag,attrs):
  if tag=='img':self.images.append(dict(attrs)['src'])
def main():
 provenance=load(ROOT/'SOURCES.json');results=load(ROOT/'RESULTS.json');checks={}
 for kind,p in provenance.items():
  assert sha(Path(p['source']))==p['source_sha'];assert sha(Path(p['settings']))==p['settings_sha']
  core=read(ROOT/('EA-'+kind)/'Core.mqh');original=read(Path(p['source']));first='int VolumeDigits' if kind=='T' else 'int ScaleBars'
  a=core[core.index(first):]
  for event in ['OnInit','OnTick','OnDeinit']:a=a.replace('Original'+event+'(',event+'(')
  b=original[original.index(first):];assert re.sub(r'\s+','',a)==re.sub(r'\s+','',b),'Strategy function body changed: '+kind
  assert load(ROOT/('PARITY-'+kind+'.json'))['exact']
  for per,dates in WINDOWS.items():
   rows=results[kind][per];assert len(rows)==7 and [x['parameters']['rr'] for x in rows]==TARGETS
   for row in rows:
    assert row['model']==4 and row['start']==dates[0] and row['end']==dates[1]
    d=read_ledger(row['native_batch'],row['native_index']);assert len(d)==row['stats']['trades']
    assert abs(d.net_profit.sum()-row['net']['net_profit'])<.02
    assert (abs(d.volume-d.closed_volume)<1e-7).all()
    assert (d.actual_risk>0).all() and (d.requested_risk>0).all()
    assert (d.open_epoch>=datetime.strptime(dates[0],'%Y.%m.%d').replace(tzinfo=timezone.utc).timestamp()).all()
    assert row['net']['max_open']<=1
  checks[kind]=dict(source_unchanged=True,settings_unchanged=True,strategy_functions_identical=True,baseline_parity=True,windows=4,targets=7,position_ledgers_reconciled=True)
 picks=load(ROOT/'PICKS.json')
 for kind in 'TS':
  expected=[]
  for i,rr in enumerate(TARGETS):
   a,b=results[kind]['1y'][i],results[kind]['5y'][i]
   if all(r['clean'] and r['stats']['net']>0 and r['net']['profit_factor']>=1.2 and (r['stats']['sharpe'] or 0)>0 and r['stats']['trades']>=minimum for r,minimum in [(a,20),(b,30)]):expected.append(rr)
  assert expected==picks[kind]['screened_targets']
 report=ROOT/'Gold Target Results.html';assert report.exists();parser=Images();parser.feed(report.read_text(encoding='utf-8'));assert parser.images and all((ROOT/p).exists() for p in parser.images)
 save(ROOT/'VERIFICATION.json',dict(passed=True,checks=checks,images=len(parser.images),report_bytes=report.stat().st_size,scope='File/ledger/source/parity checks only; not an out-of-sample edge certification'))
 print(json.dumps(load(ROOT/'VERIFICATION.json'),indent=2),flush=True)
if __name__=='__main__':main()
