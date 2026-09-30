"""Static scientific figure of existing native position ledgers, no new backtest."""
from datetime import datetime
import json
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.ticker import FuncFormatter
import report
ROOT=report.ROOT;CFG=report.CFG
fig,axes=plt.subplots(2,2,figsize=(15,9),sharex=True,constrained_layout=True)
colors={5:'#157aa3',15:'#b95b18'}
for ax,asset in zip(axes.flat,CFG['symbols']):
 for tf in CFG['timeframes']:
  p=ROOT/'native'/f'{asset}-M{tf}-reversal-1y'/'trades.json'
  if not p.exists():continue
  trades=json.loads(p.read_text());times=[datetime.strptime(CFG['windows']['1y'],'%Y.%m.%d')];balance=[10000]
  for t in trades:times.append(datetime.fromisoformat(t['close_time']));balance.append(balance[-1]+t['net_profit'])
  times.append(datetime.strptime(CFG['end'],'%Y.%m.%d'));balance.append(balance[-1])
  ax.step(times,balance,where='post',label=f'M{tf}: {balance[-1]/100-100:+.2f}%',color=colors[tf],linewidth=1.5)
 ax.axhline(10000,color='#555555',linestyle='--',linewidth=.7)
 ax.set_title(asset,loc='left',fontweight='bold');ax.grid(alpha=.18);ax.legend(loc='best')
 ax.yaxis.set_major_formatter(FuncFormatter(lambda x,pos:f'${x/1000:.1f}k'))
 ax.xaxis.set_major_locator(mdates.MonthLocator(interval=3));ax.xaxis.set_major_formatter(mdates.DateFormatter('%b %Y'))
 ax.spines[['top','right']].set_visible(False)
fig.suptitle('Previous-day sweep rejection | M5 vs M15\nNative closed balance, $10,000 per run, 1% planned risk, 2R | not floating equity',fontsize=16)
fig.savefig(ROOT/'balance-1y.png',dpi=170)
print('Saved balance-1y.png')
