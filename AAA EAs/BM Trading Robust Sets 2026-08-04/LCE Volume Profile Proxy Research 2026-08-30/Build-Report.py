from __future__ import annotations
import argparse, csv, json, re
from datetime import datetime
from pathlib import Path
import matplotlib.pyplot as plt
from bs4 import BeautifulSoup

LABELS = {"us500":"US500", "ustec":"USTEC", "xauusd":"XAUUSD", "btcusd":"BTCUSD"}
VARIANTS = {
 "literal-20d-neutral-rth":dict(days=20,rows=160,spacing=.75,zone=.15,penetration=.50,cloud=0,end=16,min_r=.75),
 "early-20d-neutral":dict(days=20,rows=160,spacing=.75,zone=.15,penetration=.50,cloud=0,end=12,min_r=.75),
 "early-20d-score1":dict(days=20,rows=160,spacing=.75,zone=.15,penetration=.50,cloud=1,end=12,min_r=.75),
 "early-20d-score2":dict(days=20,rows=160,spacing=.75,zone=.15,penetration=.50,cloud=2,end=12,min_r=.75),
 "deep-20d-score1":dict(days=20,rows=160,spacing=.75,zone=.15,penetration=.75,cloud=1,end=12,min_r=.75),
 "robust-40d-score1":dict(days=40,rows=200,spacing=1.,zone=.15,penetration=.50,cloud=1,end=12,min_r=.75),
 "quick-10d-score1":dict(days=10,rows=120,spacing=.60,zone=.15,penetration=.50,cloud=1,end=12,min_r=.75),
 "quality-20d-score1-r125":dict(days=20,rows=160,spacing=.75,zone=.15,penetration=.50,cloud=1,end=12,min_r=1.25),
}
def compact(value:str)->str:return " ".join(value.replace("\xa0"," ").split())
def number(value:str|None)->float:
    match=re.search(r"[-+]?\d+(?:[,.]\d{3})*(?:\.\d+)?",compact(value or "").replace(" ",""));return float(match.group(0).replace(",","")) if match else 0.
def percent(value:str|None)->float:
    match=re.search(r"([-+]?\d+(?:\.\d+)?)%",compact(value or ""));return float(match.group(1)) if match else 0.
def parse(path:Path)->dict:
    soup=BeautifulSoup(path.read_text(encoding="utf-16",errors="replace"),"html.parser");values={}
    for row in soup.find_all("tr"):
        cells=[compact(cell.get_text(" ",strip=True)) for cell in row.find_all(["td","th"],recursive=False)]
        for index,cell in enumerate(cells[:-1]):
            if cell.endswith(":"):values[cell[:-1]]=cells[index+1]
    deals=[];in_deals=False
    for row in soup.find_all("tr"):
        if compact(row.get_text(" ",strip=True))=="Deals":in_deals=True;continue
        if not in_deals:continue
        cells=[compact(cell.get_text(" ",strip=True)) for cell in row.find_all("td",recursive=False)]
        if len(cells)!=13 or not re.fullmatch(r"\d{4}\.\d{2}\.\d{2} \d{2}:\d{2}:\d{2}",cells[0]) or cells[3].lower()=="balance":continue
        deals.append({"time":datetime.strptime(cells[0],"%Y.%m.%d %H:%M:%S"),"commission":number(cells[8]),"swap":number(cells[9]),"profit":number(cells[10]),"cashflow":number(cells[8])+number(cells[9])+number(cells[10])})
    initial=number(values.get("Initial Deposit")) or 10000.;net=number(values.get("Total Net Profit"));wins=values.get("Profit Trades (% of total)","");losses=values.get("Loss Trades (% of total)","");edd=values.get("Equity Drawdown Maximal","");bdd=values.get("Balance Drawdown Maximal","")
    return {"initial":initial,"final":initial+net,"net":net,"return_pct":net/initial*100.,"profit_factor":number(values.get("Profit Factor")),"win_rate_pct":percent(wins),"wins":int(number(wins)),"losses":int(number(losses)),"trades":int(number(values.get("Total Trades"))),"equity_dd_amount":number(edd),"equity_dd_pct":percent(edd),"balance_dd_amount":number(bdd),"balance_dd_pct":percent(bdd),"gross_profit":number(values.get("Gross Profit")),"gross_loss":number(values.get("Gross Loss")),"largest_win":number(values.get("Largest profit trade")),"largest_loss":number(values.get("Largest loss trade")),"average_win":number(values.get("Average profit trade")),"average_loss":number(values.get("Average loss trade")),"expected_payoff":number(values.get("Expected Payoff")),"recovery_factor":number(values.get("Recovery Factor")),"sharpe":number(values.get("Sharpe Ratio")),"history_quality":values.get("History Quality",""),"commission":sum(x["commission"] for x in deals),"swap":sum(x["swap"] for x in deals),"deals":deals}
def identify(path:Path,phase:str)->tuple[str,str]:
    match=re.match(rf"^(us500|ustec|xauusd|btcusd)--(.+)--{phase}\.htm$",path.name,re.I)
    if not match:raise ValueError(path.name)
    return match.group(1).lower(),match.group(2)
def style(ax):
    ax.set_facecolor("#0b1714");ax.tick_params(colors="#9eb1ac");ax.grid(color="#31443f",alpha=.35,linewidth=.6)
    for spine in ax.spines.values():spine.set_color("#31443f")
def graph(row:dict,path:Path,title:str):
    balance=row["initial"];times=[];balances=[]
    for deal in row["deals"]:balance+=deal["cashflow"];times.append(deal["time"]);balances.append(balance)
    fig,ax=plt.subplots(figsize=(10.5,4.4),dpi=160);fig.patch.set_facecolor("#07110f");style(ax)
    if times:ax.plot(times,balances,color="#67f5c3",linewidth=1.7)
    else:ax.axhline(row["initial"],color="#67f5c3",linewidth=1.7)
    ax.axhline(row["initial"],color="#7a8d88",linewidth=.8,linestyle="--");ax.set_title(title,color="white",fontsize=13,pad=12);ax.set_ylabel("Realized balance (USD)",color="#c9d8d4");fig.tight_layout();fig.savefig(path,bbox_inches="tight");plt.close(fig)
def combined(rows:list[dict],path:Path):
    fig,ax=plt.subplots(figsize=(11.5,5.4),dpi=170);fig.patch.set_facecolor("#07110f");style(ax)
    for row in sorted(rows,key=lambda x:x["return_pct"],reverse=True):
        balance=row["initial"];times=[];returns=[]
        for deal in row["deals"]:balance+=deal["cashflow"];times.append(deal["time"]);returns.append((balance/row["initial"]-1)*100)
        if times:ax.plot(times,returns,linewidth=1.6,label=row["symbol"])
    ax.axhline(0,color="#9eb1ac",linewidth=.9,linestyle="--");ax.set_title("LCE volume-profile proxy — locked return",color="white",fontsize=14,pad=12);ax.set_ylabel("Return from $10,000 (%)",color="#c9d8d4");ax.legend(facecolor="#0b1714",edgecolor="#31443f",labelcolor="white");fig.tight_layout();fig.savefig(path,bbox_inches="tight");plt.close(fig)
def set_text(v:dict,magic:int)->str:
    values={"InpExecutionTimeframe":5,"InpServerUTCOffsetHours":0,"InpEntryStartHourNY":9,"InpEntryStartMinuteNY":30,"InpEntryEndHourNY":v["end"],"InpForcedCloseHourNY":16,"InpMaximumTradesPerDay":2,"InpStopAfterFirstWinner":"true","InpProfileLookbackDays":v["days"],"InpProfileTimeframe":15,"InpProfileRows":v["rows"],"InpMinimumNodeVolumeFactor":1.,"InpMinimumNodeSpacingH1ATR":v["spacing"],"InpZoneHalfWidthSpacingFraction":v["zone"],"InpLevelPenetration":v["penetration"],"InpMaximumProfileNodes":24,"InpFastEMAPeriod":20,"InpSlowEMAPeriod":50,"InpATRPeriod":14,"InpCloudFlatATR":.05,"InpMinimumCloudScore":v["cloud"],"InpUseH1Cloud":"true","InpUseM30Cloud":"true","InpUseM15Cloud":"true","InpUseM5Cloud":"true","InpStructureLookbackBars":6,"InpStopBufferATR":.10,"InpMinimumTargetR":v["min_r"],"InpRiskPercent":1.,"InpMoveToBreakEven":"true","InpBreakEvenTargetFraction":.50,"InpMaximumSpreadATR":.10,"InpMaximumDeviationPoints":50,"InpAllowLong":"true","InpAllowShort":"true","InpMagic":magic}
    return "\n".join(f"{k}={v}" for k,v in values.items())+"\n"
def decision(row:dict)->str:
    if row["return_pct"]>=5 and row["profit_factor"]>=1.15 and row["equity_dd_pct"]<=15 and row["trades"]>=20 and row["development_return_pct"]>0 and row["development_pf"]>=1.1 and row["development_trades"]>=20:return "KEEP CANDIDATE"
    if row["return_pct"]>0 and row["profit_factor"]>1:return "WATCH — NOT ROBUST"
    return "REJECT"
def main():
    parser=argparse.ArgumentParser();parser.add_argument("--development",type=Path,required=True);parser.add_argument("--locked",type=Path,required=True);parser.add_argument("--selected",type=Path,required=True);parser.add_argument("--output",type=Path,required=True);args=parser.parse_args();selected=json.loads(args.selected.read_text(encoding="utf-8"));charts=args.output/"Charts";sets=args.output/"Sets";charts.mkdir(parents=True,exist_ok=True);sets.mkdir(parents=True,exist_ok=True)
    dev={}
    for path in args.development.glob("*.htm"):
        try:symbol,variant=identify(path,"development")
        except ValueError:continue
        dev[(symbol,variant)]=parse(path)
    rows=[];details=[]
    for path in args.locked.glob("*.htm"):
        try:symbol,variant=identify(path,"locked")
        except ValueError:continue
        row=parse(path);row.update({"symbol":LABELS[symbol],"slug":symbol,"variant":variant});d=dev.get((symbol,variant),{});row["development_return_pct"]=d.get("return_pct",0.);row["development_pf"]=d.get("profit_factor",0.);row["development_dd_pct"]=d.get("equity_dd_pct",0.);row["development_trades"]=d.get("trades",0);row["decision"]=decision(row);graph(row,charts/f"{symbol}-locked-equity.png",f"{LABELS[symbol]} — locked 2025-08-29 to 2026-08-28");(sets/f"SELECTED - {LABELS[symbol]} M5 - LCE Volume Profile Proxy - 1pct.set").write_text(set_text(VARIANTS[variant],86330000+len(rows)),encoding="utf-8");details.append(row);rows.append({k:v for k,v in row.items() if k!="deals"})
    combined(details,charts/"all-symbols-locked-equity.png");rows.sort(key=lambda x:x["return_pct"],reverse=True);(args.output/"RESULTS.json").write_text(json.dumps(rows,indent=2),encoding="utf-8")
    if rows:
        with (args.output/"RESULTS.csv").open("w",newline="",encoding="utf-8-sig") as handle:writer=csv.DictWriter(handle,fieldnames=rows[0].keys());writer.writeheader();writer.writerows(rows)
    lines=["# LCE volume-profile level breakout — MT5 walk-forward validation","","This is a transparent proxy for the public LCE rules. The proprietary hand-drawn level chart is replaced by rolling tick-volume high-volume nodes fixed at the New York open.","","## Locked last-year results","","| Symbol | Selected variant | Development return / PF | Locked return / PF | Win rate | Equity DD | Trades | Decision |","|---|---|---:|---:|---:|---:|---:|---|"]
    for r in rows:lines.append(f"| {r['symbol']} | {r['variant']} | {r['development_return_pct']:+.2f}% / {r['development_pf']:.2f} | {r['return_pct']:+.2f}% / {r['profit_factor']:.2f} | {r['win_rate_pct']:.2f}% | {r['equity_dd_pct']:.2f}% | {r['trades']} | {r['decision']} |")
    lines += ["","## Test integrity","","- Exness MT5 Trial 16; native Every Tick model with random execution delay.","- $10,000 initial balance, 1:2000 leverage and 1% equity risk per trade.","- Development: 2024-08-29 through 2025-08-28. Untouched locked test: 2025-08-29 through 2026-08-28.","- Broker spread, commission and swap are included.","- CFD tick volume is only a broker-activity proxy; it is not centralized CME volume.","- No active BAT or website file was changed."]
    (args.output/"FULL REPORT.md").write_text("\n".join(lines)+"\n",encoding="utf-8")
if __name__=="__main__":main()

