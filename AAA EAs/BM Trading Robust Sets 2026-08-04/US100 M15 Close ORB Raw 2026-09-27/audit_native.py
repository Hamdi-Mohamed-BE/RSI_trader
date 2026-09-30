"""Independent bar-level audit of raw ORB native trades and no-lookahead rules."""
from pathlib import Path
import csv,gzip,importlib.util,json,re,sys
from collections import defaultdict,Counter
from datetime import datetime,timedelta,timezone
from zoneinfo import ZoneInfo
ROOT=Path(__file__).resolve().parent;BASE=ROOT.parent
sys.path.insert(0,str(BASE/'FTMO Exit Management Research 2026-09-27'))
import analyze as a
c=a.c;NY=ZoneInfo('America/New_York')

def audit(period,target):
 path=ROOT/'native'/(period+'-'+target);meta=c.read(path/'run.json')
 assert meta['ok'];trades=c.read(path/'trades.json');body=a.report_text(path/'report.htm.gz');orders=a.orders(body)
 with (path/'bars.csv').open(newline='',encoding='utf-8-sig') as file:bars=[dict(time=a.epoch(x['time']),**{k:float(x[k]) for k in ('open','high','low','close')}) for x in csv.DictReader(file)]
 assert bars and len({r['time'] for r in bars})==len(bars)
 groups=defaultdict(list)
 for r in bars:
  dt=datetime.fromtimestamp(r['time'],NY);r['minute']=dt.hour*60+dt.minute
  if dt.weekday()<5:groups[dt.date().isoformat()].append(r)
 candidates={};ranges={}
 for day,rows in groups.items():
  found=[r for r in rows if r['minute']==570]
  if not found:continue
  assert len(found)==1;opening=found[0];ranges[day]=opening
  for bar in sorted(rows,key=lambda x:x['time']):
   if bar['minute']<585 or bar['minute']+15>=955:continue
   side=1 if bar['close']>opening['high'] else -1 if bar['close']<opening['low'] else 0
   if side:candidates[day]=dict(bar=bar,opening=opening,side=side);break
 journal=gzip.decompress((path/'journal.txt.gz').read_bytes()).decode()
 signals=sorted(set(re.findall(r'ORB15_SIGNAL\|[^\r\n]+',journal)))
 signalmap={}
 for line in signals:
  fields=line.split('|');assert len(fields)==13,fields
  at,bar_at=a.epoch(fields[1]),a.epoch(fields[2]);side=int(fields[3]);rh,rl,bh,bl,bc,entry,stop,tp,lot=map(float,fields[4:])
  day=datetime.fromtimestamp(at,NY).date().isoformat();candidate=candidates[day];bar=candidate['bar'];opening=candidate['opening']
  assert day not in signalmap and side==candidate['side']
  assert bar_at==bar['time'] and at>=bar_at+900 and at-bar_at-900<60
  assert all(abs(x-y)<1e-7 for x,y in ((rh,opening['high']),(rl,opening['low']),(bh,bar['high']),(bl,bar['low']),(bc,bar['close'])))
  assert abs(stop-(bl if side>0 else bh))<1e-7
  assert abs(tp-(entry+side*meta['reward_risk']*abs(entry-stop)))<=.011
  signalmap[day]=dict(at=at,side=side,stop=stop,target=tp,lot=lot)
 summary=sorted(set(re.findall(r'ORB15_SUMMARY ranges=(\d+) signals=(\d+) fills=(\d+) skips=(\d+) close_failures=(\d+)',journal)))
 assert len(summary)==1;range_count,signal_count,filled,skipped,close_fail=map(int,summary[0])
 assert range_count==len(ranges) and signal_count==len(candidates),(period,target,summary,len(ranges),len(candidates))
 assert filled==len(trades)==len(signals),(period,target,filled,len(trades),len(signals))
 assert filled+skipped==signal_count
 result=[];seen=set()
 for t in trades:
  op,cl=a.epoch(t['open_time']),a.epoch(t['close_time']);day=datetime.fromtimestamp(op,NY).date().isoformat()
  signal=signalmap[day];sgn=1 if t['side']=='Long' else -1
  assert day not in seen and sgn==signal['side'] and 0<=op-signal['at']<60;seen.add(day)
  initial=orders[op,t['symbol'],t['side']];assert len(initial)==1
  stop=initial[0]['stop'];assert abs(stop-signal['stop'])<1e-7 and abs(initial[0]['target']-signal['target'])<1e-7
  assert sgn*(t['open_price']-stop)>0 and cl>op
  assert abs(sgn*(t['close_price']-t['open_price'])*t['volume']-t['gross_profit'])<.03
  assert abs(t['gross_profit']+t['commission']+t['swap']-t['net_profit'])<.03
  result.append(dict(t,key='us100-m15-close-orb/'+target,news=False,op=op,cl=cl,stop=stop,target=initial[0]['target'],unit_risk=abs(t['open_price']-stop),
   risk_quality='native_initial_order',unit_gross=t['gross_profit']/t['volume'],unit_comm=t['commission']/t['volume'],unit_swap=t['swap']/t['volume']))
 assert abs(sum(t['net_profit'] for t in trades)-meta['metrics']['net_profit'])<.1
 dd=re.search(r'>\s*Equity Drawdown Relative:\s*</td>\s*<td[^>]*>\s*<b>(.*?)</b>',body,re.I|re.S);assert dd
 eqdd=float(re.search(r'([\d.]+)%',a.clean(dd.group(1))).group(1))
 start=datetime.strptime(meta['start'],'%Y.%m.%d').replace(tzinfo=timezone.utc);end=datetime.strptime(meta['end'],'%Y.%m.%d').replace(tzinfo=timezone.utc)
 weekdays=sum((start+timedelta(days=i)).weekday()<5 for i in range((end-start).days))
 positive=sum(max(t['net_profit'],0) for t in trades);negative=sum(max(-t['net_profit'],0) for t in trades)
 months=defaultdict(lambda:dict(trades=0,wins=0,net=0.))
 for t in trades:
  q=months[t['close_time'][:7]];q['trades']+=1;q['wins']+=t['net_profit']>0;q['net']+=t['net_profit']
 validation=dict(period=period,target=target,independent_range_days=len(ranges),independent_signal_days=len(candidates),verified_signal_entries=len(signals),verified_native_stops=len(trades),skipped_signals=skipped,close_failures=close_fail,
  exact_cash_reconciliation=True,no_lookahead_bar_checks=True,one_entry_per_day=True,first_entry=min(t['open_time'] for t in trades),last_entry=max(t['open_time'] for t in trades),
  overnight_holds=sum(datetime.fromtimestamp(t['op'],NY).date()!=datetime.fromtimestamp(t['cl'],NY).date() for t in result),end_of_test_exits=[t for t in trades if 'end of test' in t['exit_comment'].lower()])
 stats=dict(meta['metrics'],win_rate_pct=100*sum(t['net_profit']>0 for t in trades)/len(trades),profit_factor=positive/negative if negative else None,
  relative_equity_drawdown_pct=eqdd,max_win_loss_streak=a.streaks(result),weekdays=weekdays,trades_per_weekday=len(trades)/weekdays,trades_per_30_days=len(trades)/(end-start).days*30,
  monthly=dict(months),average_win=positive/sum(t['net_profit']>0 for t in trades),average_loss=negative/sum(t['net_profit']<0 for t in trades))
 c.save(path/'AUDIT.json',validation)
 return result,dict(meta=meta,stats=stats,validation=validation)

if __name__=='__main__':
 rows,info=audit(sys.argv[1],sys.argv[2]);print(json.dumps(info,indent=2))
