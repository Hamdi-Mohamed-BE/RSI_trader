"""Create a standalone offline client report from audited native evidence."""
import json,gzip,math,statistics,importlib.util,hashlib
from datetime import datetime,timedelta
from build import ROOT,CLIENT,BASE,sha
spec=importlib.util.spec_from_file_location('stats',BASE/'No Wick Multi Asset Raw 2026-09-30/analyse.py')
s=importlib.util.module_from_spec(spec);spec.loader.exec_module(s)

def statistics_for(trades,start,end,symbol,native=None):
    trades=sorted(trades,key=lambda t:(t['close_time'],t.get('ea',''),int(t.get('exit_deal',t['number']))))
    n=s.trade_statistics(trades,start,end,symbol)
    cash=peak=10000.;maxdd=0.;curve=[[start.replace('.','-'),cash,0]];monthly={};streak=[];daily={}
    for t in trades:
        cash+=t['net_profit'];peak=max(peak,cash);dd=100*(peak-cash)/peak;maxdd=max(maxdd,dd)
        curve.append([t['close_time'],round(cash,2),round(dd,4)])
        key=t['close_time'][:7];monthly[key]=monthly.get(key,0)+t['net_profit']
        day=t['close_time'][:10];daily[day]=daily.get(day,0)+t['net_profit']
        direction=1 if t['net_profit']>0 else -1 if t['net_profit']<0 else 0
        count=(abs(streak[-1])+1 if streak and direction and streak[-1]*direction>0 else 1)*direction
        streak.append(count)
    a=datetime.strptime(start,'%Y.%m.%d');b=datetime.strptime(end,'%Y.%m.%d');returns=[];balance=10000.
    while a<b:
        key=a.strftime('%Y-%m-%d');pnl=daily.get(key,0)
        if a.weekday()<5 or pnl:
            returns.append(pnl/balance if balance>0 else 0)
        balance+=pnl;a+=timedelta(days=1)
    avgwin=sum(t['net_profit'] for t in trades if t['net_profit']>0)/max(1,n['wins'])
    avgloss=-sum(t['net_profit'] for t in trades if t['net_profit']<0)/max(1,n['losses'])
    n.update(return_pct=n['net_profit']/100,closed_dd_pct=maxdd,
      equity_dd_pct=native['relative_equity_dd_pct'] if native else None,
      payoff_ratio=avgwin/avgloss if avgloss else None,average_win=avgwin,average_loss=avgloss,
      daily_sharpe_proxy=statistics.mean(returns)/statistics.stdev(returns)*math.sqrt(252) if len(returns)>1 and statistics.stdev(returns)>0 else None,
      curve=curve,monthly=[[k,round(v,2)] for k,v in sorted(monthly.items())],streak=streak,
      start=start,end=end,history_quality=native.get('history_quality') if native else None)
    return n

def main():
    m=json.loads((ROOT/'manifest.json').read_text());datasets={};hashes=[]
    for mode in ('fixed','balance'):
        datasets[mode]={}
        for period in ('6m','3m'):
            parts={};combined=[]
            for row in m['entries']:
                folder=ROOT/'tests-native'/f"nw-{row['symbol']}-{row['slug']}-{mode}-{period}"
                meta=json.loads((folder/'run.json').read_text());assert meta['audited']
                assert meta['ex5_sha256']==row['ex5_sha256']==sha(CLIENT/row['expert'])
                assert meta['trades_sha256']==sha(folder/'trades.json.gz')
                assert hashlib.sha256(gzip.decompress(next(folder.glob('*.htm.gz')).read_bytes())).hexdigest()==meta['report_sha256']
                trades=json.loads(gzip.decompress((folder/'trades.json.gz').read_bytes()))
                assert len(trades)==meta['metrics']['trades']
                assert abs(sum(t['net_profit'] for t in trades)-meta['metrics']['net_profit'])<max(.05,len(trades)*.011)
                for t in trades:t['ea']=row['slug']
                parts[row['slug']]=statistics_for(trades,meta['start'],meta['end_exclusive'],row['symbol'],meta['metrics'])
                combined+=trades;hashes.append({'case':meta['case'],'report':meta['report_sha256'],'ledger':meta['trades_sha256'],'ex5':row['ex5_sha256']})
            parts['all']=statistics_for(combined,meta['start'],meta['end_exclusive'],'PORTFOLIO')
            datasets[mode][period]=parts
    payload={'licence':m['licence'],'bots':[{k:r[k] for k in ('slug','label','symbol','period','ex5_sha256')} for r in m['entries']],
             'datasets':datasets,'built':datetime.now().isoformat(timespec='seconds'),'evidence':hashes}
    details=ROOT/'ea-details-cache.json'
    if details.exists():payload['ea_details']=json.loads(details.read_text(encoding='utf-8'))
    text=(ROOT/'report.template.html').read_text(encoding='utf-8').replace('__DATA__',json.dumps(payload,separators=(',',':')).replace('<','\\u003c'))
    (CLIENT/'Performance and Setup.html').write_text(text,encoding='utf-8')
    (ROOT/'report-data.json').write_text(json.dumps(payload,indent=2))
    print('Rendered client HTML with 20 audited runs')
if __name__=='__main__':main()
