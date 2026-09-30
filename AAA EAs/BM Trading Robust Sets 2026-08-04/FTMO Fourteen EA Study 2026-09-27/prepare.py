"""Audit fresh native ledgers. No MT5/API imports."""
from pathlib import Path
import ast,gzip,hashlib,html,json,re,sys
from collections import defaultdict
from datetime import datetime,timezone
ROOT=Path(__file__).resolve().parent;BASE=ROOT.parent
OLD=BASE/'FTMO Combination Study 2026-09-19'
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def save(p,v):p.write_text(json.dumps(v,indent=2,allow_nan=False),encoding='utf-8')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
ns=dict(html=html,re=re,Path=Path,Any=object,TAG_RE=re.compile(r'<[^>]+>'),defaultdict=defaultdict,datetime=datetime,timezone=timezone)
for p,names in [(BASE.parent/'EA store/app/mt5_evidence_jobs.py',{'_read_report','_clean','_number'}),(OLD/'prepare.py',{'dt','orders'})]:
 tree=ast.parse(p.read_text(encoding='utf-8-sig'))
 nodes=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in names]
 assert {n.name for n in nodes}==names
 exec(compile(ast.Module(body=nodes,type_ignores=[]),str(p),'exec'),ns)
dt=ns['dt'];orders=ns['orders']
def main():
 frozen=read(ROOT/'FROZEN.json');allrows={};placements=[];audit=[]
 for e in frozen['entries']:
  out=ROOT/'native'/e['slug']
  if not (out/'run.json').exists():continue
  run=read(out/'run.json');rr=read(out/'trades.json');oo=orders(out/'report.htm')
  assert run['ok'] and run['report_sha']==sha(out/'report.htm')
  assert sha(Path(e['expert']))==e['expert_sha'] and sha(Path(e['settings']))==e['settings_sha']
  news=e['slug']=='news-pulse-xau';key=e['slug'];rows=[];matched=0;partials=0
  if news:
   journal=gzip.decompress((out/'journal.txt.gz').read_bytes()).decode()
   pat=r'News Pulse: (NFP|CPI|FOMC) two-sided orders placed\. Buy ([\d.]+), sell ([\d.]+), SL distance \$([\d.]+),.*?Server placement=([\d.]+ [\d:]+), event=([\d.]+ [\d:]+), lead=(\d+)s'
   pp={}
   for m in re.finditer(pat,journal):
    kind,buy,sell,sl,placed,event,lead=m.groups();epoch=dt(event.replace('.','-',2).replace(' ','T'))
    p=dict(key=key,kind=kind,epoch=epoch,op=dt(placed.replace('.','-',2).replace(' ','T')),until=epoch+{'NFP':60,'CPI':300,'FOMC':120}[kind]+1,buy=float(buy),sell=float(sell),sl=float(sl),symbol='XAUUSD')
    if epoch in pp:assert pp[epoch]==p
    pp[epoch]=p
   assert pp,'Missing news placement evidence'
   assert all(abs(p['sl']-2)<1e-8 for p in pp.values())
   placements+=list(pp.values())
  for raw in rr:
   op=dt(raw['open_time']);cl=dt(raw['close_time']);sym=e['symbol'];sgn=1 if raw['side']=='Long' else -1
   match=oo.get((op,raw['symbol'],raw['side']),[])
   assert len(match)==1,(key,raw['number'],op,match)
   initial=match[0];stop=initial['stop'];assert sgn*(raw['open_price']-stop)>0
   contract=100 if sym=='XAUUSD' else 100000 if sym=='USDJPY' else 1
   conv=raw['open_price'] if sym=='USDJPY' else 1
   assert abs(raw['gross_profit']+raw['commission']+raw['swap']-raw['net_profit'])<.03
   expected=sgn*(raw['close_price']-raw['open_price'])*contract*raw['volume']/(raw['close_price'] if sym=='USDJPY' else 1)
   assert abs(expected-raw['gross_profit'])<max(.04,abs(expected)*.002),(key,raw['number'],expected,raw['gross_profit'])
   assert cl>=op
   r=dict(raw,key=key,news=news,symbol=sym,op=op,cl=max(cl,op+.001),stop=stop,target=initial['target'],
    unit_risk=abs(raw['open_price']-stop)*contract/conv,actual_unit_risk=abs(raw['open_price']-stop)*contract/conv,
    unit_gross=raw['gross_profit']/raw['volume'],unit_comm=raw['commission']/raw['volume'],unit_swap=raw['swap']/raw['volume'])
   if news:
    event=int(raw['entry_comment'].split('|')[1]);assert event in pp
    r.update(event=event,unit_risk=pp[event]['sl']*contract)
   matched+=1;rows.append(r)
  assert len({(r['op'],r['side']) for r in rows})==len(rows),'Partial exits need explicit position aggregation'
  assert abs(sum(r['net_profit'] for r in rows)-run['metrics']['net_profit'])<.1
  allrows[key]=rows
  audit.append(dict(ea=key,matched_stops=matched,trades=len(rows),native_metrics=run['metrics'],flags=run['flags'],
   files={str(out/name):sha(out/name) for name in ('report.htm','trades.json','run.json','journal.txt.gz')},
   first=min((r['open_time'] for r in rows),default=None),last=max((r['close_time'] for r in rows),default=None)))
 save(ROOT/'prepared.json',dict(rows=allrows,placements=placements))
 save(ROOT/'DATA_AUDIT.json',dict(eas=audit,complete=len(audit)==14,news_placements=len(placements),
  total_trades=sum(len(v) for v in allrows.values())))
 print(json.dumps(dict(complete=len(audit)==14,counts={k:len(v) for k,v in allrows.items()},news_placements=len(placements))),flush=True)
if __name__=='__main__':main()
