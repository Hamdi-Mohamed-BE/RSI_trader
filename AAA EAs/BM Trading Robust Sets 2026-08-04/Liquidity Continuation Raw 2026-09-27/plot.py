"""Scientific figure of retained closed-trade balances, not intratrade equity."""
from datetime import datetime
import json
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.ticker import FuncFormatter
import report
ROOT=report.ROOT
def main():
 rows=report.load();fig,axes=plt.subplots(3,2,figsize=(14,10),layout='constrained')
 styles={'touch':('#0072B2','-','First touch'),'retest':('#D55E00','-','Breakout–retest'),'touch-control':('#0072B2','--','Synthetic touch'),'retest-control':('#D55E00','--','Synthetic retest')}
 for ax,(a,s) in zip(axes.flat,report.CFG['symbols'].items()):
  for v,(color,style,label) in styles.items():
   r=next((x for x in rows if x['asset']==a and x['variant']==v and x['window']=='1y'),None)
   if not r:continue
   p=ROOT/'native'/f'{a}-{v}-1y'/'trades.json';trades=json.loads(p.read_text());balance=10000
   x=[datetime.strptime(r['start'],'%Y.%m.%d')];y=[balance]
   for t in trades:balance+=t['net_profit'];x.append(datetime.fromisoformat(t['close_time']));y.append(balance)
   ax.plot(x,y,color=color,linestyle=style,lw=1.5 if style=='-' else 1,alpha=1 if style=='-' else .75,label=label)
  ax.set_title(a,loc='left',fontsize=13,fontweight='bold');ax.axhline(10000,color='#777777',lw=.6,alpha=.5)
  ax.xaxis.set_major_locator(mdates.MonthLocator(interval=3));ax.xaxis.set_major_formatter(mdates.DateFormatter('%b %y'))
  ax.yaxis.set_major_formatter(FuncFormatter(lambda x,p:f'${x/1000:.1f}k'));ax.grid(alpha=.17);ax.set_xlabel('Date (UTC)');ax.set_ylabel('Closed balance (USD)')
  ax.spines[['top','right']].set_visible(False)
 axes.flat[-1].axis('off');handles,labels=axes.flat[0].get_legend_handles_labels();axes.flat[-1].legend(handles,labels,loc='upper left',frameon=False,fontsize=12)
 axes.flat[-1].text(0,.48,'$10,000 start • 1% equity target risk\nExness CFD data • native Model 4 • 150 ms delay\nSpread, commission and swap included\n\nDashed lines = synthetic-level controls\nClosed balance is NOT floating equity.\nSeparate accounts; not a portfolio.\nNo optimization; not the private T-812 system.',transform=axes.flat[-1].transAxes,fontsize=10,va='top',linespacing=1.4)
 fig.suptitle('Calyx Liquidity Continuation — raw one-year comparison\n27 Sep 2025 – 27 Sep 2026 (exclusive)',fontsize=16)
 fig.savefig(ROOT/'balance-1y.png',dpi=145);plt.close(fig)
 print(ROOT/'balance-1y.png')
if __name__=='__main__':main()
