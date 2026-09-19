import sys,json,re
from pathlib import Path
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT.parent.parent/'EA store'))
from app.mt5_evidence_jobs import _native_metrics,_native_trades,_read_report,_metric

def parse(name):
 p=ROOT/'native'/name/f'news-event-{name}.htm'
 stats=_native_metrics(p);trades=_native_trades(p,'News Pulse XAU')
 assert abs(sum(t['net_profit'] for t in trades)-stats['net_profit'])<.05
 stats['native_win_rate_pct']=stats['win_rate_pct']
 stats['win_rate_pct']=100*sum(t['net_profit']>0 for t in trades)/len(trades) if trades else 0
 positive=sum(max(0,t['net_profit']) for t in trades);negative=sum(max(0,-t['net_profit']) for t in trades)
 stats['profit_factor']=positive/negative if negative else None
 stats['max_drawdown_pct']=float(re.match(r'([\d.]+)%',_metric(_read_report(p),'Equity Drawdown Relative'))[1])
 stats['commission']=sum(t['commission'] for t in trades);stats['swap']=sum(t['swap'] for t in trades)
 (p.parent/'trades.json').write_text(json.dumps(trades,indent=2))
 (p.parent/'stats.json').write_text(json.dumps(stats,indent=2))
 print(name,stats);print('first_trade',trades[0] if trades else None)
 return stats,trades
if __name__=='__main__':parse(sys.argv[1] if len(sys.argv)>1 else 'NativeBaseline')
