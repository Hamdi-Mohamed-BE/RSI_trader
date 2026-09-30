"""Render verified results with the installed Python 3.13 scientific runtime."""
import json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

ROOT=Path(__file__).resolve().parent
rows=json.loads((ROOT/'RESULTS.json').read_text())
verification=json.loads((ROOT/'VERIFICATION.json').read_text())
assert verification['passed'] and len(rows)==32
symbols=['USTEC','XAUUSD','XAGUSD','BTCUSD','ETHUSD','EURUSD','USDJPY','GBPJPY']
plt.rcParams.update({'font.size':11})
fig,axes=plt.subplots(4,2,figsize=(12,15),layout='constrained')
for symbol,ax in zip(symbols,axes.flat):
    group=[r for r in rows if r['symbol']==symbol]
    x=np.arange(4); a=[r['raw']['return_pct'] for r in group]; b=[r['optimized']['return_pct'] for r in group]
    raw=ax.bar(x-.18,a,.36,color='#8493a5',label='Raw')
    candidate=ax.bar(x+.18,b,.36,color='#087f8c',label='Selected candidate')
    ax.axhline(0,color='#444',lw=.7)
    ax.set_xticks(x,[r['variant'] for r in group]); ax.set_title(symbol,weight='bold')
    ax.set_ylabel('Return (%)'); ax.grid(axis='y',alpha=.2); ax.set_axisbelow(True)
    ax.bar_label(raw,fmt='%.1f',padding=3,fontsize=10)
    ax.bar_label(candidate,fmt='%.1f',padding=3,fontsize=10)
    lo=min(a+b+[0]); hi=max(a+b+[0]); gap=max(hi-lo,1)
    ax.set_ylim(lo-gap*.17,hi+gap*.23)
axes.flat[0].legend(loc='lower left',fontsize=9)
fig.suptitle('3 Way Volume Profile: all 32 comparisons\n26 Sep 2025–25 Sep 2026 | $10,000 | target 1% risk | independent tests',fontsize=15,weight='bold')
fig.supxlabel('POC = bounce | REV = reversal | BRK = breakout | ALL = combined\nSelected on older data. Mixed real/generated ticks. Research only; not a future-return forecast.',fontsize=10)
fig.savefig(ROOT/'side-by-side.png',dpi=170)
plt.close(fig)
print(ROOT/'side-by-side.png')
