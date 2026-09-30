"""Build raw research comparison from audited native artifacts."""
from pathlib import Path
import json,gzip,re,hashlib
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import audit
ROOT=Path(__file__).resolve().parent
NAMES={"reversal":"Reversal","continuation":"Continuation","combined":"Combined","control":"Plain ORB control"}
def save(p,v):p.write_text(json.dumps(v,indent=2,allow_nan=False),encoding="utf-8")
def load(p):return json.loads(p.read_text())
def pfstr(v):return "n/a" if v is None else f"{v:.2f}"
def row(r):
 s=r["net_stats"];m=r["metrics"]
 return f'| {NAMES[r["variant"]]} | {s["trades"]} | {s["trades_per_month"]:.1f} / {s["trades_per_weekday"]:.2f} | {s["return_pct"]:+.2f}% | {s["net_usd"]:+,.2f} | {s["win_rate_pct"]:.2f}% | {pfstr(s["profit_factor"])} | {m["max_equity_dd_pct"]:.2f}% | {s["max_win_streak"]} / {s["max_loss_streak"]} |'
def main():
 records=[];build=load(ROOT/"BUILD.json")
 for p in sorted((ROOT/"native").glob("*/run.json")):
  m=load(p)
  if m["period"]=="smoke":continue
  assert m["source_sha256"]==build["source_sha256"] and m["config_sha256"]==build["config_sha256"]
  ap=p.parent/"AUDIT.json";assert ap.exists(),f"Audit missing: {p.parent.name}"
  a=load(ap);assert a["ok"] and a["report_sha256"]==m["report_sha256"]
  tr=load(p.parent/"trades.json");net=a["net_stats"]
  engine={code:audit.stats([t for t in tr if t["entry_comment"]=="NY30 "+code],m["start"],m["end"]) for code in ("R","C","O") if any(t["entry_comment"]=="NY30 "+code for t in tr)}
  running=10000.
  for k in sorted(net["monthly"]):
   z=net["monthly"][k];z["start_balance"]=round(running,2);z["return_pct"]=100*z["net_usd"]/running if running else None
   running+=z["net_usd"];z["end_balance"]=round(running,2)
  costs=[]
  for extra in (.20,.50):
   tx=[{**t,"net_profit":t["net_profit"]-extra*100*t["volume"]} for t in tr]
   st=audit.stats(tx,m["start"],m["end"])
   costs.append({"extra_roundtrip_price_USD_per_oz":extra,**{k:st[k] for k in ("net_usd","return_pct","profit_factor","win_rate_pct")}})
  overnight=[t for t in tr if audit.dt(t["open_time"]).astimezone(audit.NY).date()!=audit.dt(t["close_time"]).astimezone(audit.NY).date()]
  balance=[];cash=10000.
  for t in tr:cash+=t["net_profit"];balance.append({"time":t["close_time"],"balance":round(cash,2)})
  records.append(dict(**m,net_stats=net,engines=engine,audit={k:v for k,v in a.items() if k!="net_stats"},hypothetical_cost_sensitivity=costs,
    overnight_count=len(overnight),overnight_net=sum(t["net_profit"] for t in overnight),balance=balance))
 assert len(records)==24,("incomplete",len(records))
 native={(r["period"],r["variant"]):r for r in records if r["model"]==4};decisions=[]
 for v in ("reversal","continuation","combined"):
  passes=[]
  for period in ("3y","5y"):
   r=native[period,v];c=native[period,"control"];s=r["net_stats"];cs=c["net_stats"]
   ratio=s["return_pct"]/r["metrics"]["max_equity_dd_pct"] if r["metrics"]["max_equity_dd_pct"] else 0
   cratio=cs["return_pct"]/c["metrics"]["max_equity_dd_pct"] if c["metrics"]["max_equity_dd_pct"] else 0
   okay=s["trades"]>=30 and s["return_pct"]>0 and (s["profit_factor"] or 0)>=1.15 and (s["profit_factor"] or 0)>(cs["profit_factor"] or 0) and ratio>cratio
   passes.append({"period":period,"numeric_gate":okay,"return_to_equity_dd":ratio})
  coverage=all("100% real ticks" in native[p,v]["metrics"]["history_quality"] and audit.dt(native[p,v]["start"])>=audit.dt("2026.01.01") for p in ("3y","5y"))
  decisions.append({"variant":v,"periods":passes,"numeric_pass":all(x["numeric_gate"] for x in passes),"full_real_tick_confirmation":coverage,"qualified":all(x["numeric_gate"] for x in passes) and coverage})
 save(ROOT/"RESULTS.json",{"complete":True,"native_runs":len(records),"smoke_runs":4,"parameters_searched":False,"tested_strategy_variants":4,"promotion_decisions":decisions,"records":records})
 text=["# Gold NY30 Value Area + VWAP — raw native results","",
 "Research only; no production deployment. Four definitions frozen before tests, no parameter tuning.","",
 "## Interpretation",
 "- USD 10,000 initial balance, target 1% current equity; lots rounded UP per raw pipeline. Includes native broker bid/ask, commission, swaps and 150ms simulated execution delay.",
 "- 09:30–10:00 New York range transferred to XAUUSD; M1 signals, 70% tick-volume profile, anchored VWAP +/-1 volume-weighted SD, structural SL plus one tick, 3R, max two combined entries/day, request flat 15:55. See RULES.md for every assumption.",
 "- Reversal gross break-even at VWAP touch; continuation no BE. One attempt per engine/day.",
 "- **Sizing is NOT a hard 1% cap. Latest 6m actual initial risk reached 1.265%. In the depleted 5y combined path, the 0.01 minimum lot exposed 8.444% of equity on 2026-03-03 (roughly USD 58.71 risk on USD 695.22 equity). Thus the long result includes a minimum-lot sizing effect, not just a constant-percentage strategy edge. A strict live risk policy would skip undersized trades or round down; no such rule was retrofitted after testing.**",
 "- **Win rate and PF below use completed trades AFTER all commission and swap. Native MT5 headline wins can include gross break-even exits that lose after entry costs.** Native metrics are preserved separately.",
 "- DD is native maximum relative EQUITY drawdown, not the closed-balance graph. Streaks use net results. Frequency denominator: calendar months and weekdays in the full window, including no-trade days.",
 "- **Model 4 is requested mode, not proof of historical real ticks. Real ticks begin 2026-01-01. Older segments are generated/mixed; the latest 6m lies inside available real-tick history.**",
 "- Overlapping windows are descriptive in-sample comparisons, NOT independent holdouts. This is not a funded-account simulation or proof of future profitability.",""]
 header="| Version | Trades | /month /weekday | Return | Net USD | Net win rate | Net PF | Max equity DD | Longest W/L |"
 for period in ("6m","1y","3y","5y"):
  start,end=load(ROOT/"run-config.json")["periods"][period]
  text+=["## "+period+f" — {start} to {end} (end exclusive)","",header,"|---|---:|---:|---:|---:|---:|---:|---:|---:|"]
  for v in NAMES:text.append(row(native[period,v]))
  text.append("")
 text+=["## Coverage and execution","","| Window | Version | Native history quality | Overnight positions | Max actual initial SL risk | Entry / close / BE failures |","|---|---|---|---:|---:|---:|"]
 for period in ("6m","1y","3y","5y"):
  for v in NAMES:
   r=native[period,v];f=r["flags"]
   text.append(f'| {period} | {NAMES[v]} | {r["metrics"]["history_quality"]} | {r["overnight_count"]} | {r["audit"]["max_actual_initial_risk_pct"]:.3f}% | {f["entry_fail"]} / {f["close_fail"]} / {f["be_fail"]} |')
 text+=["","No overnight or closed-market loss is erased. Actual initial risk uses fill-to-original-stop before costs; realized SL losses can exceed that through slippage.",
 "Profile is an M1 HLC3/tick-count binning proxy, NOT COMEX volume-at-price or exact TradingView/Deepcharts parity. Broker history and symbol specs are not independently reconstructed historical fee schedules.",
 "", "## Predeclared raw gate",""]
 for d in decisions:
  text.append(f'- **{NAMES[d["variant"]]}: '+("numeric PASS" if d["numeric_pass"] else "FAIL")+"**. "+", ".join(x["period"]+": "+("pass" if x["numeric_gate"] else "fail") for x in d["periods"])+". Full long-window real-tick confirmation: "+str(d["full_real_tick_confirmation"])+".")
 text+=["","No variant is promoted without both numeric qualification and data confirmation. Do not automatically optimize a raw failure.",
 "", "## Model 1 long-window screening — not real-tick confirmation","",header,"|---|---:|---:|---:|---:|---:|---:|---:|---:|"]
 for period in ("3y","5y"):
  text.append(f"| **{period}** | | | | | | | | |")
  for r in records:
   if r["period"]==period and r["model"]==1:text.append(row(r))
 text+=["","## Monthly net USD — latest 6m","","| Month | Reversal | Continuation | Combined | Control |","|---|---:|---:|---:|---:|"]
 months=sorted(set(k for v in NAMES for k in native["6m",v]["net_stats"]["monthly"]))
 for month in months:text.append("| "+month+" | "+" | ".join(f'{native["6m",v]["net_stats"]["monthly"].get(month,{}).get("net_usd",0):+,.2f}' for v in NAMES)+" |")
 text+=["","First/last calendar months may be partial. All windows' monthly counts, wins, starting/ending balances and returns: RESULTS.json.",
 "", "## Gross break-even versus net outcomes — latest 6m", "",
 "| Version | Trades moved to BE | Of those, net losses | Net P&L of all BE-moved trades (USD) |", "|---|---:|---:|---:|"]
 for v in NAMES:
  a=native["6m",v]["audit"]
  text.append(f'| {NAMES[v]} | {a["trades_moved_to_be"]} | {a["be_moved_trades_net_losses"]} | {a["be_moved_trades_net_usd"]:+,.2f} |')
 text+=["", "Moving the stop to entry does not exit the trade; some BE-protected trades continue to TP. The negative subset includes commission/slippage losses, not just full-stop losses.",
 "", "## Extra cost sensitivity — latest 6m",
 "", "Hypothetical ledger subtraction, NOT a native rerun or measured live slippage. Add USD 0.20 / 0.50 per ounce round trip at original lots; future lot sizing, signals, exits and margin are not resimulated.",
 "", "| Version | Extra round-trip price cost | Net USD | Return | PF |","|---|---:|---:|---:|---:|"]
 for v in NAMES:
  for s in native["6m",v]["hypothetical_cost_sensitivity"]:text.append(f'| {NAMES[v]} | {s["extra_roundtrip_price_USD_per_oz"]:.2f} | {s["net_usd"]:+,.2f} | {s["return_pct"]:+.2f}% | {pfstr(s["profit_factor"])} |')
 text+=["","## Verification","",
 "- Clean compile: 0 errors/warnings; EA refuses live initialization.",
 "- Four smoke tests plus 24 main serial isolated native tests; fresh reports, inputs, symbol, dates, frozen hashes and delay checked.",
 "- Independent profile/VWAP/band, signal-state, closed-bar timing, stop/target, volume, cash P&L, position overlap, daily cap and break-even audits. Native totals reconcile to completed deals.",
 "- Compressed original reports, journals, M1 bars and profiles plus trade ledgers retained. No live chart/BAT/website/production changes.",
 "", "## Sources","",
 "- Source reel/user transcript: https://www.instagram.com/reel/DacxHJqNuUZ/",
 "- Official indicator description (not published equations): https://helpdesk.deepcharts.com/portal/en/kb/articles/deep-m-ivb",
 "- VWAP concepts: https://www.tradingview.com/support/solutions/43000502018-volume-weighted-average-price-vwap/",
 "- Volume profile concepts and volume types: https://www.tradingview.com/support/solutions/43000502040-volume-profile-indicators-basic-concepts/",""]
 (ROOT/"REPORT.md").write_text("\n".join(text),encoding="utf-8")
 plt.rcParams.update({"font.size":11})
 fig,axes=plt.subplots(2,1,figsize=(12,9.0),constrained_layout=True)
 colors={"reversal":"#D55E00","continuation":"#0072B2","combined":"#009E73","control":"#777777"}
 for ax,period in zip(axes,("6m","5y")):
  for v in NAMES:
   rec=native[period,v];values=rec["balance"]
   x=[audit.dt(rec["start"])]+[audit.dt(z["time"]) for z in values];y=[10000]+[z["balance"] for z in values]
   ax.step(x,y,where="post",label=NAMES[v],color=colors[v],linestyle="--" if v=="control" else "-",linewidth=2.1 if v=="combined" else 1.5)
  ax.axhline(10000,color="#555555",linewidth=.7,alpha=.5);ax.set_ylabel("Closed-trade balance (USD)")
  ax.set_title(period+(" — real-tick period" if period=="6m" else " — mixed/generated historical ticks"),loc="left")
  ax.grid(alpha=.15);ax.set_xlabel("Date");ax.legend(ncol=2,frameon=False,fontsize=10)
 fig.suptitle("Gold NY30 raw comparison — USD 10,000 start\n1% target, NOT a hard cap; minimum lots can exceed it\nClosed balance, not floating equity",fontsize=13)
 fig.savefig(ROOT/"balance_comparison.png",dpi=160);plt.close(fig)
 checks=dict(ok=True,main_runs=len(records),smoke_runs=4,source_hash_unchanged=True,
  profile_checks=sum(r["audit"]["profile_checks"] for r in records),bar_checks=sum(r["audit"]["bar_indicator_checks"] for r in records),
  signal_checks=sum(r["audit"]["signal_checks"] for r in records),trade_checks=sum(r["audit"]["trade_checks"] for r in records),
  be_checks=sum(r["audit"]["breakeven_checks"] for r in records),native_source_hash=build["source_sha256"])
 assert hashlib.sha256((ROOT/"GoldNY30.mq5").read_bytes()).hexdigest()==build["source_sha256"]
 assert hashlib.sha256((ROOT/"run-config.json").read_bytes()).hexdigest()==build["config_sha256"]
 save(ROOT/"CHECKS.json",checks)
 print(json.dumps({"checks":checks,"gate":decisions},indent=2),flush=True)
if __name__=="__main__":main()
