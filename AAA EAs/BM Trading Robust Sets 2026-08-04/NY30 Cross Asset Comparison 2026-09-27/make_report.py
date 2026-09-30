"""Verified cross-asset raw comparisons; no optimisation or live API."""
from pathlib import Path
import json,gzip,re,hashlib
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter
ROOT=Path(__file__).resolve().parent;BASE=ROOT.parent
ASSETS=("Gold","US100","US500")
V={"reversal":"Reversal","continuation":"Continuation","combined":"Combined","control":"Plain ORB"}
COLORS={"reversal":"#D55E00","continuation":"#0072B2","combined":"#009E73","control":"#777777"}
def load(p):return json.loads(p.read_text(encoding="utf-8"))
def f(x,d=2):return "n/a" if x is None else f"{x:.{d}f}"
def main():
 rows=[];smokes=[];builds={}
 for asset in ASSETS:
  study=BASE/(asset+" NY30 Value Area VWAP Raw 2026-09-27")
  build=load(study/"BUILD.json");builds[asset]=build
  review=load(study/"FINAL_REVIEW.json");assert review["ok"] and review["reports"]==28
  completed=list((study/"native").glob("*/run.json"));assert len(completed)==28
  for p in completed:
   m=load(p);a=load(p.parent/"AUDIT.json");assert a["ok"]
   report=gzip.decompress((p.parent/"report.htm.gz").read_bytes())
   assert hashlib.sha256(report).hexdigest()==m["report_sha256"]==a["report_sha256"]
   assert all(m[k]==build[k] for k in ("source_sha256","binary_sha256","config_sha256","rules_sha256"))
   journal=gzip.decompress((p.parent/"journal.txt.gz").read_bytes()).decode()
   spec=re.search(r"NY30_SPEC[^\r\n]+",journal)[0]
   trades=load(p.parent/"trades.json")
   overnight=sum(t["open_time"][:10]!=t["close_time"][:10] for t in trades)
   row=dict(asset=asset,folder=str(p.parent),period=m["period"],variant=m["variant"],model=m["model"],
    start=m["start"],end=m["end"],net=a["net_stats"],equity_dd=m["metrics"]["max_equity_dd_pct"],
    quality=m["metrics"]["history_quality"],real_ticks=m["real_ticks"],max_risk=a["max_actual_initial_risk_pct"],
    audit=a,spec=spec,flags=m["flags"],summary=m["summary"],trades=trades,overnight_utc=overnight)
   (smokes if m["period"]=="smoke" else rows).append(row)
 assert len(rows)==72 and len(smokes)==12
 assert len({b["source_sha256"] for b in builds.values()})==len({b["binary_sha256"] for b in builds.values()})==1
 idx={(r["asset"],r["period"],r["variant"],r["model"]):r for r in rows}
 gates=[]
 for asset in ASSETS:
  for variant in ("reversal","continuation","combined"):
   checks=[]
   for period in ("3y","5y"):
    r=idx[asset,period,variant,4];c=idx[asset,period,"control",4];n=r["net"];cn=c["net"]
    checks.append(n["trades"]>=30 and n["return_pct"]>0 and (n["profit_factor"] or 0)>=1.15 and
     (n["profit_factor"] or 0)>(cn["profit_factor"] or 0) and n["return_pct"]/r["equity_dd"]>cn["return_pct"]/c["equity_dd"])
   full_ticks=all(idx[asset,p,variant,4]["quality"]=="100% real ticks" for p in ("3y","5y"))
   verdict=("Numerical candidate; further validation required" if full_ticks else "Numerical candidate only; incomplete real-tick history") if all(checks) else "FAIL raw numerical gate"
   gates.append(dict(asset=asset,variant=variant,numerical_gate=all(checks),real_tick_confirmation=full_ticks,verdict=verdict))
 (ROOT/"RESULTS.json").write_text(json.dumps(dict(builds=builds,gates=gates,rows=rows),indent=2,allow_nan=False),encoding="utf-8")
 decision="None of the new profile/VWAP variants passes the frozen long-window raw gate." if not any(g["numerical_gate"] for g in gates) else "Some variants pass the numerical screen, but still require independent validation."
 recent=[r for r in rows if r["model"]==4 and r["period"]=="6m" and r["variant"]!="control" and r["net"]["return_pct"]>0]
 recent_note="Positive new variants over the latest six months: "+(", ".join(r["asset"]+" "+V[r["variant"]]+" "+f(r["net"]["return_pct"])+"%" for r in recent) or "none")+". This does not override the long-window gate."
 md=["# NY30 Value Area + VWAP - Gold vs US100 vs US500","",decision,"",recent_note,"",
 "Research only. Unchanged gold strategy transferred to USTEC (US100) and US500 in the isolated Exness tester. Live trading, production EAs, BATs and website were not changed.","",
 "## Test design and interpretation","",
 "- Four predeclared versions: reversal, continuation, combined (shared limits), plain M1-close ORB control. Identical compiled binary/source across all assets; no tuning.",
 "- Combined means reversal + continuation on ONE asset. Gold, US100 and US500 are separate tests, not a simultaneous three-asset portfolio or an overlay on your production system.",
 "- 09:30-10:00 New York opening profile; M1 entries; 64 bins; 70% value area. Broker M1 tick-volume/HLC3 proxy, NOT exchange volume-at-price. VWAP anchored 09:30; +/-1 volume-weighted standard deviation.",
 "- Reversal fades an opening-range excursion after a later close back inside value area; gross break-even on favorable VWAP touch. Continuation requires a band/VA breakout and later retest. Fixed 3R target; structural stop plus one symbol tick; skip stops under three current spreads.",
 "- Two entries maximum/day for combined/control, one attempt/engine; one position; entry cutoff 15:30 NY, flat request 15:55, broker-open execution only.",
 "- USD 10,000 starts, 1% current-equity TARGET, lots rounded upward exactly as in gold. Rounding, minimum lots and fills can exceed 1%; actual maxima below. This is NOT a strict 1% cap or an FTMO simulation. Tester leverage setting 1:2000.",
 "- Initial-risk maxima measure actual fill to ORIGINAL stop price, before commission, swaps and stop-fill slippage. They are not maximum possible loss or realized loss.",
 "- Broker spread/commission/swap as charged by native tester, plus 150ms execution delay. Delay-based slippage is simulated, not measured live execution. Historical broker specification/cost changes are not independently reconstructed.",
 "- End date 2026-09-27 exclusive. Windows overlap: descriptive backtests, not independent out-of-sample validation. Model 4 requests real ticks but generates missing history; actual coverage is disclosed.",
 "- Net win rate and PF recomputed AFTER commission/swap. Gross break-even can be net loss. Equity DD is maximum relative floating-equity drawdown from native report, not balance-curve DD.",
 "- Trades/day uses all Monday-Friday dates, including holidays/no-trade days. Streaks use net outcomes; exactly flat outcomes break streaks.",
 "- Frozen raw gate: positive return, PF >=1.15, >=30 trades, beat control on PF and return/equity-DD on BOTH 3y and 5y. No automatic optimization/promotion.",""]
 for period in ("6m","1y","3y","5y"):
  e=idx["Gold",period,"combined",4]
  md += [f"## {period}: {e['start']} to {e['end']} exclusive","",
   "| Asset | Version | Trades | /month | /weekday | Net USD | Return | Net win | Net PF | Equity DD | Max W/L |",
   "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|"]
  for asset in ASSETS:
   for v,label in V.items():
    r=idx[asset,period,v,4];n=r["net"]
    md.append(f"| {asset} | {label} | {n['trades']} | {f(n['trades_per_month'],1)} | {f(n['trades_per_weekday'])} | {n['net_usd']:+,.2f} | {n['return_pct']:+.2f}% | {f(n['win_rate_pct'])}% | {f(n['profit_factor'])} | {f(r['equity_dd'])}% | {n['max_win_streak']}/{n['max_loss_streak']} |")
  md+=[""]
 md+=["## Frozen gate results","","| Asset | Version | Decision |","|---|---|---|"]
 for g in gates:md.append(f"| {g['asset']} | {V[g['variant']]} | {g['verdict']} |")
 md+=["","## Coverage and actual initial-risk maxima","","| Asset | Period | Reported real-tick coverage | Max risk reversal | Continuation | Combined | Control |","|---|---|---|---:|---:|---:|---:|"]
 for asset in ASSETS:
  for period in ("6m","1y","3y","5y"):
   rs=[idx[asset,period,v,4] for v in V]
   md.append(f"| {asset} | {period} | "+", ".join(sorted(set(r["quality"] for r in rs)))+" | "+" | ".join(f(r["max_risk"],3)+"%" for r in rs)+" |")
  r=idx[asset,"5y","combined",4]
  md+=["",f"{asset} native specification: {r['spec']}. Real-tick journal: "+("; ".join(r["real_ticks"]) or "None recorded")+".",""]
 md+=["Gold 5y combined includes a minimum-lot trade after severe balance erosion. Initial risk is NOT realized loss on that trade. Upward rounding is retained for comparison, not recommended as a hard-risk implementation.",
 "", "## Last 6 months: monthly net USD and closed trades","",
 "Partial March/September months included. Closed-trade profits are NOT funded payouts. Each version has its own 10,000 USD starting account."]
 for asset in ASSETS:
  rs=[idx[asset,"6m",v,4] for v in V];months=sorted(set(k for r in rs for k in r["net"]["monthly"]))
  md+=["",f"### {asset}","","| Month | Reversal USD (trades) | Continuation USD (trades) | Combined USD (trades) | Control USD (trades) |","|---|---:|---:|---:|---:|"]
  for month in months:
   cells=[]
   for r in rs:
    z=r["net"]["monthly"].get(month,dict(net_usd=0,trades=0));cells.append(f"{z['net_usd']:+,.2f} ({z['trades']})")
   md.append("| "+month+" | "+" | ".join(cells)+" |")
 md+=["","## 6m costs, break-even and average streaks","","| Asset | Version | Commission USD | Swap USD | BE moved / net losses | Avg win/loss streak | UTC-date overnight crossings |","|---|---|---:|---:|---:|---:|---:|"]
 for asset in ASSETS:
  for v in V:
   r=idx[asset,"6m",v,4];a=r["audit"];n=r["net"]
   md.append(f"| {asset} | {V[v]} | {n['commission']:,.2f} | {n['swap']:,.2f} | {a.get('trades_moved_to_be','n/a')}/{a.get('be_moved_trades_net_losses','n/a')} | {f(n['avg_win_streak'])}/{f(n['avg_loss_streak'])} | {r['overnight_utc']} |")
 md+=["","## Model 1 long-window screen (NOT real ticks)","","| Asset | Period | Version | Return | Net PF | Equity DD | Trades |","|---|---|---|---:|---:|---:|---:|"]
 for asset in ASSETS:
  for period in ("3y","5y"):
   for v in V:
    r=idx[asset,period,v,1];n=r["net"]
    md.append(f"| {asset} | {period} | {V[v]} | {n['return_pct']:+.2f}% | {f(n['profit_factor'])} | {f(r['equity_dd'])}% | {n['trades']} |")
 checks={k:sum(r["audit"][k] for r in rows+smokes) for k in ("profile_checks","bar_indicator_checks","signal_checks","trade_checks","breakeven_checks")}
 md+=["","## Verification","",f"84 verified native cases: 56 new indices cases (48 main + 8 smoke), plus 28 existing gold cases reused. All reports reconcile to deal ledgers; all final reviews pass. Totals: {json.dumps(checks)}.",
 "",f"Shared source SHA-256: {builds['Gold']['source_sha256']}.","",f"Shared binary SHA-256: {builds['Gold']['binary_sha256']}.",
 "","Charts show closed-trade balance, NOT floating equity. Complete rows and ledgers are in RESULTS.json and each asset's research directory.",""]
 (ROOT/"REPORT.md").write_text("\n".join(md),encoding="utf-8")
 fig,axes=plt.subplots(3,2,figsize=(13,11),sharey="col");handles=None
 for i,asset in enumerate(ASSETS):
  for j,period in enumerate(("6m","5y")):
   ax=axes[i,j]
   for v,label in V.items():
    r=idx[asset,period,v,4];t=r["trades"]
    x=[pd.Timestamp(r["start"].replace(".","-"))]+[pd.Timestamp(z["close_time"]) for z in t]
    y=np.r_[10000,10000+np.cumsum([z["net_profit"] for z in t])]
    ax.step(x,y,where="post",label=label,color=COLORS[v],lw=1.8 if v=="combined" else 1.2,ls="--" if v=="control" else "-")
   ax.axhline(10000,color="#AAAAAA",lw=.7);ax.grid(alpha=.18)
   ax.set_title(asset+" - "+period+" | "+idx[asset,period,"combined",4]["quality"],fontsize=10)
   ax.set_ylabel("Closed balance (USD)");ax.set_xlabel("Date")
   ax.yaxis.set_major_formatter(FuncFormatter(lambda x,p:f"{x/1000:.1f}k"))
   ax.tick_params(axis="x",labelsize=8);ax.tick_params(axis="y",labelsize=9)
   if handles is None:handles=ax.get_legend_handles_labels()
 fig.suptitle("Same NY30 rules across three assets - no tuning",fontsize=16,y=.99)
 fig.legend(*handles,loc="upper center",bbox_to_anchor=(.5,.958),ncol=4,frameon=False)
 fig.text(.5,.016,"10,000 USD starts | 1% target (not a cap) | 3R target | native costs + 150ms delay\nLong windows contain generated ticks. Balance curves understate floating-equity drawdown.",ha="center",fontsize=10)
 fig.tight_layout(rect=(0,.065,1,.93));fig.savefig(ROOT/"balance_comparison.png",dpi=160);plt.close(fig)
 fig,axes=plt.subplots(3,1,figsize=(9,11),sharex=True,sharey=True)
 for ax,asset in zip(axes,ASSETS):
  for v,label in V.items():
   r=idx[asset,"6m",v,4];t=r["trades"]
   x=[pd.Timestamp(r["start"].replace(".","-"))]+[pd.Timestamp(z["close_time"]) for z in t]
   y=np.r_[10000,10000+np.cumsum([z["net_profit"] for z in t])]
   ax.step(x,y,where="post",label=label,color=COLORS[v],lw=2 if v=="combined" else 1.5,ls="--" if v=="control" else "-")
  ax.axhline(10000,color="#AAAAAA",lw=.8);ax.grid(alpha=.2)
  ax.set_title(asset,fontsize=14,loc="left");ax.set_ylabel("Balance (USD)",fontsize=12)
  ax.yaxis.set_major_formatter(FuncFormatter(lambda x,p:f"{x/1000:.1f}k"))
  ax.tick_params(labelsize=11)
 axes[-1].set_xlabel("March 27 - September 26, 2026",fontsize=12)
 fig.suptitle("NY30 raw strategy - last six months",fontsize=18,y=.99)
 fig.legend(*axes[0].get_legend_handles_labels(),loc="upper center",bbox_to_anchor=(.5,.956),ncol=2,frameon=False,fontsize=12)
 fig.text(.5,.015,"Separate 10,000 USD accounts | 3R target | 1% risk target, not a cap\n100% real ticks | native costs + 150ms delay\nClosed balance shown; floating-equity drawdown can be larger.",ha="center",fontsize=10)
 fig.tight_layout(rect=(0,.085,1,.90));fig.savefig(ROOT/"balance_6m.png",dpi=140);plt.close(fig)
 print(json.dumps(dict(cases=len(rows)+len(smokes),gates=gates,checks=checks),indent=2))
if __name__=="__main__":main()
