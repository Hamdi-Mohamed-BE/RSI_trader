"""Native exit ledgers -> matched shared-account FTMO overlay; no trading API."""
from pathlib import Path
import ast,gzip,hashlib,html,json,math,random,re,statistics,sys
from collections import defaultdict
ROOT=Path(__file__).resolve().parent;BASE=ROOT.parent
sys.path.insert(0,str(BASE/'FTMO Paper Application 2026-09-26'))
import compare as c
import six_ea as six
import phase_breakdown as ph
import additions as a
CFG=json.loads((ROOT/'run-config.json').read_text())
NAMES=list(CFG['eas'])
KEYS=[CFG['eas'][n]['key'] for n in NAMES]
PROFILES={
 'A Current exits':dict.fromkeys(NAMES,'native'),
 'B All 0.75R':dict.fromkeys(NAMES,'rr075'),
 'C All 0.50R':dict.fromkeys(NAMES,'rr050'),
 'D Non-news 0.75R':{n:'native' if n in ('xau','xag') else 'rr075' for n in NAMES},
 'E Strategy-specific':{'gold':'profile','overnight':'atr','ema':'atr','orb':'profile','xau':'native','xag':'native'},
 'G Non-news M15 ATR':{n:'native' if n in ('xau','xag') else 'atr' for n in NAMES},
}
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def save(p,x):p.write_text(json.dumps(x,indent=2,allow_nan=False),encoding='utf-8')
def clean(s):return html.unescape(re.sub(r'<[^>]+>','',s)).strip()
def num(s):return float(s.replace(' ','').replace(',','') or 0)
def epoch(s):return c.datetime.fromisoformat(s.replace('.','-',2).replace(' ','T')).replace(tzinfo=c.UTC).timestamp()
def report_text(path):
 b=gzip.decompress(path.read_bytes());return b.decode('utf-16') if b[:2] in (b'\xff\xfe',b'\xfe\xff') else b.decode('utf-8-sig')
def orders(body):
 marker=body.lower().find('<b>orders</b>');end=body.lower().find('<b>deals</b>');out=defaultdict(list)
 for row in re.findall(r'<tr\b[^>]*>(.*?)</tr>',body[marker:end],re.I|re.S):
  cells=[clean(v) for v in re.findall(r'<td\b[^>]*>(.*?)</td>',row,re.I|re.S)]
  if len(cells)<11 or not re.fullmatch(r'\d{4}\.\d{2}\.\d{2} \d{2}:\d{2}:\d{2}',cells[0]) or cells[9]!='filled':continue
  if not cells[6] or cells[3].lower() not in ('buy','sell','buy stop','sell stop'):continue
  key=(epoch(cells[8]),cells[2],'Long' if cells[3].startswith('buy') else 'Short')
  out[key].append({'stop':num(cells[6]),'target':num(cells[7]),'placed':epoch(cells[0]),'price':num(cells[5])})
 return out
def load_case(n,v):
 path=ROOT/'native'/(n+'-'+v);meta=read(path/'run.json');assert meta['ok']
 ts=read(path/'trades.json');body=report_text(path/'report.htm.gz');oo=orders(body)
 # Maximal (cash) DD and maximum relative-percent DD can occur at different times.
 dd=re.search(r'>\s*Equity Drawdown Relative:\s*</td>\s*<td[^>]*>\s*<b>(.*?)</b>',body,re.I|re.S)
 assert dd,(n,v,'missing native relative equity drawdown')
 meta['metrics']['relative_equity_drawdown_pct']=float(re.search(r'([\d.]+)%',clean(dd.group(1))).group(1))
 assert abs(sum(t['net_profit'] for t in ts)-meta['metrics']['net_profit'])<.10,(n,v,'cash')
 assert len(ts)==meta['metrics']['trades'],(n,v,'trade count/partial exits')
 placements=[];byevent={}
 if n in ('xau','xag'):
  journal=gzip.decompress((path/'journal.txt.gz').read_bytes()).decode()
  pat=r'News Pulse: (NFP|CPI|FOMC) two-sided orders placed\. Buy ([\d.]+), sell ([\d.]+), SL distance \$([\d.]+),.*?Server placement=([\d.]+ [\d:]+), event=([\d.]+ [\d:]+), lead=(\d+)s'
  for m in re.finditer(pat,journal):
   kind,buy,sell,sl,placed,event,lead=m.groups();ev=epoch(event)
   hold=(300 if kind=='CPI' else 120 if kind=='FOMC' else 60) if n=='xau' else 60
   byevent[ev]={'key':CFG['eas'][n]['key'],'kind':kind,'epoch':ev,'op':epoch(placed),'until':ev+hold+1,
                'buy':float(buy),'sell':float(sell),'sl':2. if n=='xau' else .02,'symbol':CFG['eas'][n]['symbol']}
  placements=list(byevent.values());assert len(placements)>0,(n,v,'no news placements')
 rr=[]
 for t in ts:
  op=epoch(t['open_time']);cl=max(op+.001,epoch(t['close_time']));contract=c.SPECS[t['symbol']][0]
  matches=oo[op,t['symbol'],t['side']];assert len(matches)==1,(n,v,op,matches)
  stop=matches[0]['stop'];sign=1 if t['side']=='Long' else -1
  assert sign*(t['open_price']-stop)>0,(n,v,t,stop)
  r=dict(t,key=CFG['eas'][n]['key'],news=n in ('xau','xag'),op=op,cl=cl,stop=stop,target=matches[0]['target'],
         unit_risk=abs(t['open_price']-stop)*contract,risk_quality='native_initial_order',
         unit_gross=t['gross_profit']/t['volume'],unit_comm=t['commission']/t['volume'],unit_swap=t['swap']/t['volume'])
  assert abs(sign*(t['close_price']-t['open_price'])*contract*t['volume']-t['gross_profit'])<.05,(n,v,t)
  if r['news']:
   ev=int(t['entry_comment'].split('|')[1]);assert ev in byevent
   r.update(event=ev,unit_risk=byevent[ev]['sl']*contract)
  rr.append(r)
 return rr,placements,meta

def protection_engine(enabled):
 ns=six.make_engine('strict_round_down')
 if not enabled:return ns
 # Rebuild exactly the strict replay, changing only prospective ordinary entry budget.
 source=(c.SOURCE/'simulate.py').read_text(encoding='utf-8-sig')
 replacements={
  'if challenge and phase<3 and t>=max(ready,last_entry)+30*DAY:':'if False:',
  'lot=rounded(news_risk/riskunit);risk=lot*riskunit':
   "lot=rounded(news_risk/riskunit)\n            if lot<.01:\n                counts['news_min_lot_over_budget']+=1;continue\n            risk=lot*riskunit\n            assert risk<=news_risk+1e-7",
  "lot=rounded(RISK/r['unit_risk']);risk=lot*r['unit_risk'];marg=margin(sym,lot,r['open_price'])":
   "remaining=CAPITAL*(1.1 if phase==1 else 1.05)-bal\n                budget=RISK*(.5 if challenge and phase<3 and 0<remaining<=2*RISK else 1.)\n                lot=rounded(budget/r['unit_risk'])\n                if lot<.01:\n                    counts['min_lot_over_budget']+=1;continue\n                risk=lot*r['unit_risk'];marg=margin(sym,lot,r['open_price'])\n                assert risk<=budget+1e-7",
 }
 for old,new in replacements.items():assert source.count(old)==1;source=source.replace(old,new)
 node=next(n for n in ast.parse(source).body if isinstance(n,ast.FunctionDef) and n.name=='replay')
 exec(compile(ast.Module(body=[node],type_ignores=[]),'target_protection','exec'),ns)
 return ns
def streaks(rr):
 ws=ls=mw=ml=0
 for t in sorted(rr,key=lambda r:r['cl']):
  ws=ws+1 if t['net_profit']>0 else 0;ls=ls+1 if t['net_profit']<0 else 0;mw=max(mw,ws);ml=max(ml,ls)
 return [mw,ml]
def main():
 c.verify_sources();native={};metas={};native_rows=[]
 for n,e in CFG['eas'].items():
  for v in e['variants']:
   native[n,v]=load_case(n,v);rr,pp,m=native[n,v];metas[n+'-'+v]=m
   native_rows.append({'ea':n,'variant':v,'metrics':m['metrics'],'streaks':streaks(rr),'em_summary':m['em_summary'],'flags':m['flags']})
 save(ROOT/'NATIVE_AUDIT.json',native_rows)
 original=c.read(c.SOURCE/'prepared.json');orb,_=six.load_orb();original['rows'][six.ORB]=orb
 baseline_parity={}
 for n,e in CFG['eas'].items():
  old=[r for r in original['rows'][e['key']] if c.END-180*c.DAY<=r['op']<c.END and r['cl']<c.END]
  new=[r for r in native[n,'native'][0] if c.END-180*c.DAY<=r['op']<c.END and r['cl']<c.END]
  oi={(r['op'],r['side']):r for r in old};ni={(r['op'],r['side']):r for r in new};common=oi.keys()&ni.keys()
  baseline_parity[n]={'old_trades':len(old),'new_trades':len(new),'matched_entry_times':len(common),
     'exact_price_exit_matches':sum(all(abs(oi[k][f]-ni[k][f])<1e-8 for f in ('open_price','close_price','cl')) for k in common),
     'old_only':[[c.iso(k[0]),k[1]] for k in oi.keys()-ni.keys()],
     'new_only':[[c.iso(k[0]),k[1]] for k in ni.keys()-oi.keys()]}
 save(ROOT/'BASELINE_PARITY.json',baseline_parity)
 profiles=[(n,p,False) for n,p in PROFILES.items()]+[
  ('F Strategy-specific + target protection',PROFILES['E Strategy-specific'],True),
  ('H Current + target protection',PROFILES['A Current exits'],True)]
 rng=random.Random(20260926);samples=[[rng.randrange(26) for _ in range(26)] for _ in range(1000)]
 result={'generated_utc':c.iso(c.datetime.now(c.UTC).timestamp()),'native':native_rows,'baseline_parity':baseline_parity,
         'source_start':c.iso(ph.POOL_START),'source_end':c.iso(c.END),'paths_per_case':1000,'cases':[]}
 save(ROOT/'PORTFOLIOS_FROZEN.json',[{'name':n,'exits':p,'target_protection':t} for n,p,t in profiles])
 controls={}
 for name,profile,protect in profiles:
  data={'rows':{},'placements':[]}
  for n,v in profile.items():
   rr,pp,_=native[n,v];data['rows'][CFG['eas'][n]['key']]=rr;data['placements']+=pp
  weeks=c.pool(data,ph.POOL_START,26)
  ns=protection_engine(protect)
  for stress in (False,True):
   sims=[]
   for sample in samples:
    rr,pp=c.sample_rows(data,KEYS,ph.POOL_START,weeks,sample,c.START,c.START+180*c.DAY)
    sims.append(ns['replay'](rr,pp,c.START,c.START+180*c.DAY,stress=stress,news_risk=10.))
   hs=c.END-180*c.DAY
   rr=[dict(r) for rows in data['rows'].values() for r in rows if hs<=r['op']<c.END and r['cl']<c.END]
   pp=[dict(p) for p in data['placements'] if hs<=p['op']<c.END]
   hist=ns['replay'](rr,pp,hs,c.END,stress=stress,news_risk=10.,challenge=False,detail=True)
   hc=ns['replay'](rr,pp,hs,c.END,stress=stress,news_risk=10.,detail=True)
   six.reconcile(hist,True)
   if name.startswith('A '):controls[stress]=sims
   summary=ph.summarize(sims,ns)
   entry={'name':name,'profile':profile,'protection':protect,'stress':stress,'historical':hist,'historical_challenge':hc,
          'summary':summary,'aggregate180':c.summarize(sims,180),'paths':a.compact_paths(sims),
          'paired_paid180':a.paired(controls[stress],sims,'receipt_at',180)}
   result['cases'].append(entry);save(ROOT/'RESULTS.json',result)
   print(name,'stress' if stress else 'reference',json.dumps({'net':hist['balance']-10000,'trades':hist['trades'],'wr':hist['win_rate'],'pf':hist['pf'],'dd':hist['model_dd_pct'],'last':summary['horizons'][-1]}),flush=True)
 print('COMPLETE: 24 native cases, 16000 paired simulations',flush=True)
if __name__=='__main__':main()
