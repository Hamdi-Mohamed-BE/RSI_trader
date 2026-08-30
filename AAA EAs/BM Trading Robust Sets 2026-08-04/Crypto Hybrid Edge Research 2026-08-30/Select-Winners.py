from __future__ import annotations
import argparse,json,re
from pathlib import Path
from bs4 import BeautifulSoup
SYMBOLS=("btcusd","ethusd")
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
 initial=number(v.get("Initial Deposit"))or 10000.;net=number(v.get("Total Net Profit"));return{"return_pct":net/initial*100,"pf":number(v.get("Profit Factor")),"dd":percent(v.get("Equity Drawdown Maximal")),"trades":int(number(v.get("Total Trades"))),"win_rate":percent(v.get("Profit Trades (% of total)"))}
def main():
 p=argparse.ArgumentParser();p.add_argument("--reports",type=Path,required=True);p.add_argument("--output",type=Path,required=True);a=p.parse_args();pattern=re.compile(r"^(btcusd|ethusd)--(.+)--development\.htm$",re.I);rows=[]
 for path in a.reports.glob("*.htm"):
  m=pattern.match(path.name)
  if not m:continue
  row=parse(path);row.update({"symbol":m.group(1).lower(),"variant":m.group(2),"report":str(path)});row["score"]=row["return_pct"]+9*(row["pf"]-1)-.55*row["dd"]+.03*(row["win_rate"]-50)-max(0,40-row["trades"])*.2
  if row["trades"]<15 or row["pf"]<=0:row["score"]=-1e9+row["trades"]
  rows.append(row)
 selected={}
 for symbol in SYMBOLS:
  candidates=[r for r in rows if r["symbol"]==symbol]
  if not candidates:raise RuntimeError(f"No reports for {symbol}")
  selected[symbol]=max(candidates,key=lambda r:r["score"])
 a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(selected,indent=2),encoding="utf-8")
if __name__=="__main__":main()

