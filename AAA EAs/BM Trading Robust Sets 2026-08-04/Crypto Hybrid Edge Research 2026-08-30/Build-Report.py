from __future__ import annotations
import argparse,csv,json,re
from datetime import datetime
from pathlib import Path
import matplotlib.pyplot as plt
from bs4 import BeautifulSoup
LABELS={"btcusd":"BTCUSD","ethusd":"ETHUSD"}
def compact(v:str)->str:return" ".join(v.replace("\xa0"," ").split())
def number(v:str|None)->float:
 m=re.search(r"[-+]?\d+(?:[,.]\d{3})*(?:\.\d+)?",compact(v or"").replace(" ",""));return float(m.group(0).replace(",",""))if m else 0.
def percent(v:str|None)->float:
 m=re.search(r"([-+]?\d+(?:\.\d+)?)%",compact(v or""));return float(m.group(1))if m else 0.
def parse(path:Path)->dict:
 s=BeautifulSoup(path.read_text(encoding="utf-16",errors="replace"),"html.parser");v={}
 for row in s.find_all("tr"):
  cells=[compact(x.get_text(" ",strip=True))for x in row.find_all(["td","th"],recursive=False)]
  for i,c in enumerate(cells[:-1]):
   if c.endswith(":"):v[c[:-1]]=cells[i+1]
 deals=[];inside=False
 for row in s.find_all("tr"):
  if compact(row.get_text(" ",strip=True))=="Deals":inside=True;continue
  if not inside:continue
  c=[compact(x.get_text(" ",strip=True))for x in row.find_all("td",recursive=False)]
  if len(c)!=13 or not re.fullmatch(r"\d{4}\.\d{2}\.\d{2} \d{2}:\d{2}:\d{2}",c[0])or c[3].lower()=="balance":continue
  deals.append({"time":datetime.strptime(c[0],"%Y.%m.%d %H:%M:%S"),"commission":number(c[8]),"swap":number(c[9]),"profit":number(c[10]),"cashflow":number(c[8])+number(c[9])+number(c[10])})
 initial=number(v.get("Initial Deposit"))or 10000.;net=number(v.get("Total Net Profit"));wins=v.get("Profit Trades (% of total)","");losses=v.get("Loss Trades (% of total)","");edd=v.get("Equity Drawdown Maximal","");bdd=v.get("Balance Drawdown Maximal","")
 return{"initial":initial,"final":initial+net,"net":net,"return_pct":net/initial*100,"profit_factor":number(v.get("Profit Factor")),"win_rate_pct":percent(wins),"wins":int(number(wins)),"losses":int(number(losses)),"trades":int(number(v.get("Total Trades"))),"equity_dd_amount":number(edd),"equity_dd_pct":percent(edd),"balance_dd_amount":number(bdd),"balance_dd_pct":percent(bdd),"gross_profit":number(v.get("Gross Profit")),"gross_loss":number(v.get("Gross Loss")),"largest_win":number(v.get("Largest profit trade")),"largest_loss":number(v.get("Largest loss trade")),"average_win":number(v.get("Average profit trade")),"average_loss":number(v.get("Average loss trade")),"expected_payoff":number(v.get("Expected Payoff")),"recovery_factor":number(v.get("Recovery Factor")),"sharpe":number(v.get("Sharpe Ratio")),"history_quality":v.get("History Quality",""),"commission":sum(x["commission"]for x in deals),"swap":sum(x["swap"]for x in deals),"deals":deals}
def identify(path:Path,phase:str):
 m=re.match(rf"^(btcusd|ethusd)--(.+)--{phase}\.htm$",path.name,re.I)
 if not m:raise ValueError(path.name)
 return m.group(1).lower(),m.group(2)
def style(ax):
 ax.set_facecolor("#0b1714");ax.tick_params(colors="#9eb1ac");ax.grid(color="#31443f",alpha=.35,linewidth=.6)
 for s in ax.spines.values():s.set_color("#31443f")
def curve(row,path,title):
 b=row["initial"];t=[];y=[]
 for d in row["deals"]:b+=d["cashflow"];t.append(d["time"]);y.append(b)
 f,a=plt.subplots(figsize=(10.5,4.4),dpi=160);f.patch.set_facecolor("#07110f");style(a);a.plot(t,y,color="#67f5c3",linewidth=1.7)if t else a.axhline(b,color="#67f5c3");a.axhline(row["initial"],color="#7a8d88",linewidth=.8,linestyle="--");a.set_title(title,color="white",fontsize=13,pad=12);a.set_ylabel("Realized balance (USD)",color="#c9d8d4");f.tight_layout();f.savefig(path,bbox_inches="tight");plt.close(f)
def combined(rows,path):
 f,a=plt.subplots(figsize=(11,5.2),dpi=170);f.patch.set_facecolor("#07110f");style(a)
 for row in rows:
  b=row["initial"];t=[];y=[]
  for d in row["deals"]:b+=d["cashflow"];t.append(d["time"]);y.append((b/row["initial"]-1)*100)
  a.plot(t,y,linewidth=1.7,label=row["symbol"])
 a.axhline(0,color="#9eb1ac",linewidth=.9,linestyle="--");a.set_title("Crypto hybrid edge — locked return",color="white",fontsize=14,pad=12);a.set_ylabel("Return from $10,000 (%)",color="#c9d8d4");a.legend(facecolor="#0b1714",edgecolor="#31443f",labelcolor="white");f.tight_layout();f.savefig(path,bbox_inches="tight");plt.close(f)
def decision(r):
 if r["return_pct"]>=5 and r["profit_factor"]>=1.15 and r["equity_dd_pct"]<=15 and r["trades"]>=25 and r["development_return_pct"]>0 and r["development_pf"]>=1.1 and r["development_trades"]>=25:return"KEEP CANDIDATE"
 if r["return_pct"]>0 and r["profit_factor"]>1:return"WATCH — NOT ROBUST"
 return"REJECT"
def main():
 p=argparse.ArgumentParser();p.add_argument("--development",type=Path,required=True);p.add_argument("--locked",type=Path,required=True);p.add_argument("--selected",type=Path,required=True);p.add_argument("--output",type=Path,required=True);a=p.parse_args();charts=a.output/"Charts";sets=a.output/"Sets";charts.mkdir(parents=True,exist_ok=True);sets.mkdir(parents=True,exist_ok=True);dev={}
 for path in a.development.glob("*.htm"):
  try:symbol,variant=identify(path,"development")
  except ValueError:continue
  dev[(symbol,variant)]=parse(path)
 rows=[];details=[]
 for path in a.locked.glob("*.htm"):
  try:symbol,variant=identify(path,"locked")
  except ValueError:continue
  r=parse(path);r.update({"symbol":LABELS[symbol],"slug":symbol,"variant":variant});d=dev.get((symbol,variant),{});r["development_return_pct"]=d.get("return_pct",0);r["development_pf"]=d.get("profit_factor",0);r["development_dd_pct"]=d.get("equity_dd_pct",0);r["development_trades"]=d.get("trades",0);r["decision"]=decision(r);curve(r,charts/f"{symbol}-locked-equity.png",f"{LABELS[symbol]} — locked 2025-08-29 to 2026-08-28");source=next(a.development.glob(f"{symbol}--{variant}--development.htm"));details.append(r);rows.append({k:v for k,v in r.items()if k!="deals"})
 combined(details,charts/"all-crypto-locked-equity.png");rows.sort(key=lambda x:x["return_pct"],reverse=True);(a.output/"RESULTS.json").write_text(json.dumps(rows,indent=2),encoding="utf-8")
 if rows:
  with(a.output/"RESULTS.csv").open("w",newline="",encoding="utf-8-sig")as h:w=csv.DictWriter(h,fieldnames=rows[0].keys());w.writeheader();w.writerows(rows)
 lines=["# Crypto hybrid edge — MT5 walk-forward validation","","Published evidence supports both momentum and conditional intraday reversal in liquid cryptocurrencies. This test compared trend pullbacks, confirmed volatility extremes and breakout-retests using fixed 0.5R, 0.7R and 1R targets.","","| Symbol | Selected strategy | Development return / PF | Locked return / PF | Win rate | Equity DD | Trades | Decision |","|---|---|---:|---:|---:|---:|---:|---|"]
 for r in rows:lines.append(f"| {r['symbol']} | {r['variant']} | {r['development_return_pct']:+.2f}% / {r['development_pf']:.2f} | {r['return_pct']:+.2f}% / {r['profit_factor']:.2f} | {r['win_rate_pct']:.2f}% | {r['equity_dd_pct']:.2f}% | {r['trades']} | {r['decision']} |")
 lines += ["","- Exness MT5 Trial 16, native Every Tick model, random delay, spread, commission and swap included.","- $10,000 initial balance and 1% equity risk per trade.","- Development: 2024-08-29 to 2025-08-28; untouched locked test: 2025-08-29 to 2026-08-28.","- Only BTCUSD and ETHUSD are tradable crypto CFDs on the connected Exness account.","- No active BAT or website file was changed."];(a.output/"FULL REPORT.md").write_text("\n".join(lines)+"\n",encoding="utf-8")
if __name__=="__main__":main()

