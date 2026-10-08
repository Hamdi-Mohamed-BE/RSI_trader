"""Mechanical namespacing of frozen production sources for an isolated native shared-account test."""
from pathlib import Path
import hashlib, json, re, sys

R=Path(__file__).resolve().parent; B=R.parent
SPECS=[
 ('H30','US30 Hourly Profiles','US30',1,'Hourly Profiles Deployment 2026-10-04/EA/CalyxHourlyProfiles History Sized.mq5','Hourly Profiles Deployment 2026-10-04/Sets/US30.set'),
 ('H100','US100 Hourly Profiles','USTEC',1,'Hourly Profiles Deployment 2026-10-04/EA/CalyxHourlyProfiles History Sized.mq5','Hourly Profiles Deployment 2026-10-04/Sets/US100.set'),
 ('N5','Nasdaq 5M Momentum + DI','USTEC',5,'Nasdaq 5M DI ATR Deployment 2026-09-28/EA/Nasdaq 5M DI Wide ATR EA.mq5','Selected Portfolio Settings 2026-09-01/11 Nasdaq 5M - DI WIDE 0P60PCT ATR6 NO TP - 1PCT.set'),
 ('RV','RSI VWAP Gold','XAUUSD',16385,'RSI VWAP Research 2026-09-02/EA/RSI VWAP Managed EA.mq5','Selected Portfolio Settings 2026-09-01/13 XAU RSI VWAP - CURRENT - ALL DAY.set'),
 ('E3','EMA3 Gold','XAUUSD',16388,'AAA Final EAs/AAA Final EMA3 EA/AAA Final EMA3 EA.mq5','ADX DI Final Selection 2026-10-03/Sets/ema3.set'),
]
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def params(p): return dict(x.split('=',1) for x in p.read_text(encoding='utf-8-sig').splitlines() if '=' in x and not x.startswith(';'))
def save(p,v): p.write_text(json.dumps(v,indent=2),encoding='utf-8')
def mask(s):
 return re.sub(r'//[^\n]*|/\*[\s\S]*?\*/|"(?:\\.|[^"\\])*"',lambda m:' '.join('' for _ in []) if False else ''.join('\n' if c=='\n' else ' ' for c in m[0]),s)
def expand(p,files):
 files[str(p.relative_to(B))]=sha(p)
 def inc(m):
  name=m[1]
  if name.endswith('CalyxAdaptivePortfolio.mqh'): return ''
  return expand((p.parent/name.replace('\\','/')).resolve(),files)
 s=re.sub(r'^\s*#include\s+"([^"]+)"\s*$',inc,p.read_text(encoding='utf-8-sig'),flags=re.M)
 s=re.sub(r'^\s*#include\s+<[^>]+>\s*$','',s,flags=re.M)
 s=re.sub(r'^\s*#(?:property|ifndef|endif)\b[^\n]*','',s,flags=re.M)
 s=re.sub(r'^\s*input\s+group\s+"[^"]*"\s*;?','',s,flags=re.M)
 return s
def own_names(s):
 names=set(re.findall(r'^\s*#define\s+(\w+)',s,re.M))
 clean=re.sub(r'^\s*#.*$','',mask(s),flags=re.M)
 names.update(re.findall(r'\b(?:enum|struct|class)\s+(\w+)',clean))
 for e in re.finditer(r'\benum\s+\w+\s*\{([^}]+)\}',clean):
  names.update(re.findall(r'(?:^|,)\s*(\w+)',e[1]))
 depth=0; begin=0
 for i,c in enumerate(clean):
  if c=='{':
   if depth==0:
    head=clean[begin:i].strip()
    fn=re.search(r'\b(\w+)\s*\([^;]*\)\s*$',head,re.S)
    if fn: names.add(fn[1])
   depth+=1
  elif c=='}':
   depth-=1
   if depth==0: begin=i+1
  elif c==';' and depth==0:
   head=clean[begin:i].strip(); begin=i+1
   decl=re.match(r'(?:(?:input|const|static)\s+)*(\w+)\s+(.+)$',head,re.S)
   if decl:
    # Global declarations here have scalar/array initializers only.
    for part in re.split(r',(?=[^()]*?(?:\(|$))',decl[2]):
     var=re.match(r'\s*(\w+)\s*(?:\[|=|$)',part)
     if var: names.add(var[1])
 return names
def rename(s,names,prefix,symbol,tf):
 # Only identifiers, never strings/comments (trade comments must stay unchanged).
 chunks=re.split(r'("(?:\\.|[^"\\])*"|//[^\n]*|/\*[\s\S]*?\*/)',s)
 for i in range(0,len(chunks),2):
  chunks[i]=re.sub(r'\b[A-Za-z_]\w*\b',lambda m:prefix+'_'+m[0] if m[0] in names else m[0],chunks[i])
  replacements={'_Symbol':prefix+'_Symbol','_Period':prefix+'_Period','_Digits':f'((int)SymbolInfoInteger({prefix}_Symbol,SYMBOL_DIGITS))','_Point':f'SymbolInfoDouble({prefix}_Symbol,SYMBOL_POINT)'}
  for old,new in replacements.items():chunks[i]=re.sub(r'\b'+old+r'\b',new,chunks[i])
 return '\nconst string '+prefix+'_Symbol="'+symbol+'";\nconst ENUM_TIMEFRAMES '+prefix+'_Period=(ENUM_TIMEFRAMES)'+str(tf)+';\n'+''.join(chunks)
def main():
 chunks=['#property strict\n#property version "1.00"\n#include <Trade/Trade.mqh>\n#include "../_Shared/CalyxAdaptivePortfolio.mqh"\ninput int InpCase=0; // 0=all, 1..5=one module only\n']
 records=[]
 for j,(key,label,symbol,tf,src,sp) in enumerate(SPECS,1):
  files={}; s=expand(B/src,files); values=params(B/sp); values['InpRiskPercent']='1.0'; values['InpAdaptivePortfolioControls']='false'
  if key.startswith('H'): values['InpAuditTag']='five20261007-'+key; values['InpAllowRealAccount']='false'
  declared={}
  def freeze(m):
   typ,name,default=m.groups(); value=values.get(name,default.strip()); declared[name]=value
   if typ=='string' and not value.startswith('"'):value=json.dumps(value)
   elif typ.startswith('ENUM_') or typ in ('Profile',): value='('+typ+')'+value
   return 'const '+typ+' '+name+'='+value+';'
  s=re.sub(r'\binput\s+(\w+)\s+(\w+)\s*=\s*([^;]+);',freeze,s)
  assert set(values)<=set(declared),(key,'Unused preset inputs',set(values)-set(declared))
  assert declared['InpRiskPercent']=='1.0' and declared['InpAdaptivePortfolioControls']=='false'
  names=own_names(s); names.update(declared)
  s=rename(s,names,key,symbol,tf)
  # Module timers are consolidated into one shared scheduler; production callbacks otherwise unchanged.
  s=s.replace('EventSetTimer(5);','').replace('EventKillTimer();','')
  chunks.append(s)
  records.append(dict(index=j,key=key,label=label,symbol=symbol,timeframe=tf,source=src,preset=sp,source_sha256=sha(B/src),binary_sha256=sha((B/src).with_suffix('.ex5')),preset_sha256=sha(B/sp),inputs=declared,dependencies=files,namespaced_identifiers=sorted(names)))
 chunks.append('''
int portfolioCurve=INVALID_HANDLE,portfolioDeals=INVALID_HANDLE;
datetime portfolioMinute=0; double portfolioMin=0,portfolioMax=0;
double portfolioPeak=10000,portfolioDD=0; int maxPositions=0;
long seenUS30=-1,seenUSTEC=-1,seenGold=-1;
bool Active(int i){return InpCase==0||InpCase==i;}
void Audit(){double e=AccountInfoDouble(ACCOUNT_EQUITY); portfolioPeak=MathMax(portfolioPeak,e);portfolioDD=MathMax(portfolioDD,100*(portfolioPeak-e)/portfolioPeak);maxPositions=MathMax(maxPositions,PositionsTotal());datetime m=TimeCurrent()/60*60;
 if(m!=portfolioMinute){if(portfolioMinute>0)FileWrite(portfolioCurve,portfolioMinute,AccountInfoDouble(ACCOUNT_BALANCE),e,portfolioMin,portfolioMax,PositionsTotal());portfolioMinute=m;portfolioMin=e;portfolioMax=e;}else{portfolioMin=MathMin(portfolioMin,e);portfolioMax=MathMax(portfolioMax,e);}}
bool Fresh(string symbol,long &seen){MqlTick t;if(!SymbolInfoTick(symbol,t)||t.time_msc==seen||t.bid<=0||t.ask<=0)return false;seen=t.time_msc;return true;}
void Pump(){
 if(Fresh("US30",seenUS30)&&Active(1))H30_OnTick();
 if(Fresh("USTEC",seenUSTEC)){if(Active(2))H100_OnTick();if(Active(3))N5_OnTick();}
 if(Fresh("XAUUSD",seenGold)){if(Active(4))RV_OnTick();if(Active(5))E3_OnTick();}
 Audit();}
int OnInit(){
 if(!MQLInfoInteger(MQL_TESTER)){Print("Research-only adapter refuses live initialization");return INIT_FAILED;}
 if(InpCase<0||InpCase>5||AccountInfoInteger(ACCOUNT_MARGIN_MODE)!=ACCOUNT_MARGIN_MODE_RETAIL_HEDGING)return INIT_PARAMETERS_INCORRECT;
 SymbolSelect("US30",true);SymbolSelect("USTEC",true);SymbolSelect("XAUUSD",true);
 string tag="five20261007-case"+IntegerToString(InpCase);
 portfolioCurve=FileOpen(tag+"-curve.csv",FILE_WRITE|FILE_CSV|FILE_ANSI|FILE_COMMON,',');
 if(portfolioCurve==INVALID_HANDLE)return INIT_FAILED;
 FileWrite(portfolioCurve,"minute","balance_next","equity_next","minimum_equity","maximum_equity","positions_next");
 if(Active(1)&&H30_OnInit()!=INIT_SUCCEEDED)return INIT_FAILED;
 if(Active(2)&&H100_OnInit()!=INIT_SUCCEEDED)return INIT_FAILED;
 if(Active(3)&&N5_OnInit()!=INIT_SUCCEEDED)return INIT_FAILED;
 if(Active(4)&&RV_OnInit()!=INIT_SUCCEEDED)return INIT_FAILED;
 if(Active(5)&&E3_OnInit()!=INIT_SUCCEEDED)return INIT_FAILED;
 EventSetTimer(5);Print("FIVE_INIT case=",InpCase," risk=1% shared native USD account");return INIT_SUCCEEDED;}
void OnTick(){Pump();}
void OnTimer(){Pump();if(Active(1))H30_OnTimer();if(Active(2))H100_OnTimer();Audit();}
void OnDeinit(const int reason){EventKillTimer();if(Active(1))H30_OnDeinit(reason);if(Active(2))H100_OnDeinit(reason);if(Active(3))N5_OnDeinit(reason);if(Active(4))RV_OnDeinit(reason);if(portfolioCurve!=INVALID_HANDLE){if(portfolioMinute>0)FileWrite(portfolioCurve,portfolioMinute,AccountInfoDouble(ACCOUNT_BALANCE),AccountInfoDouble(ACCOUNT_EQUITY),portfolioMin,portfolioMax,PositionsTotal());FileClose(portfolioCurve);}}
double OnTester(){
 Audit();HistorySelect(0,TimeCurrent()+86400);string tag="five20261007-case"+IntegerToString(InpCase);
 int f=FileOpen(tag+"-deals.csv",FILE_WRITE|FILE_CSV|FILE_ANSI|FILE_COMMON,',');
 FileWrite(f,"ticket","position_id","order","time_msc","magic","symbol","entry","type","volume","price","profit","commission","swap","fee","comment","initial_sl","initial_tp");
 for(int i=0;i<HistoryDealsTotal();i++){ulong d=HistoryDealGetTicket(i);long type=HistoryDealGetInteger(d,DEAL_TYPE);if(type!=DEAL_TYPE_BUY&&type!=DEAL_TYPE_SELL)continue;ulong o=(ulong)HistoryDealGetInteger(d,DEAL_ORDER);
 FileWrite(f,d,HistoryDealGetInteger(d,DEAL_POSITION_ID),o,HistoryDealGetInteger(d,DEAL_TIME_MSC),HistoryDealGetInteger(d,DEAL_MAGIC),HistoryDealGetString(d,DEAL_SYMBOL),HistoryDealGetInteger(d,DEAL_ENTRY),type,HistoryDealGetDouble(d,DEAL_VOLUME),HistoryDealGetDouble(d,DEAL_PRICE),HistoryDealGetDouble(d,DEAL_PROFIT),HistoryDealGetDouble(d,DEAL_COMMISSION),HistoryDealGetDouble(d,DEAL_SWAP),HistoryDealGetDouble(d,DEAL_FEE),HistoryDealGetString(d,DEAL_COMMENT),HistoryOrderGetDouble(o,ORDER_SL),HistoryOrderGetDouble(o,ORDER_TP));}FileClose(f);
 Print("FIVE_COMPLETE case=",InpCase," balance=",AccountInfoDouble(ACCOUNT_BALANCE)," measured_dd=",portfolioDD," max_positions=",maxPositions," H30attempted=",H30_attempted," H30accepted=",H30_accepted," H100attempted=",H100_attempted," H100accepted=",H100_accepted);return 0;}
''')
 (R/'SharedPortfolio.mq5').write_text('\n'.join(chunks),encoding='utf-8')
 save(R/'CONFIG.json',dict(start='2026-07-07',end_exclusive='2026-10-07',deposit=10000,risk_percent=1,model=4,delay_ms=150,entries=records,primary_symbol='XAUUSD',dispatch='Primary-symbol ticks plus 5-second timer; each module consumes new symbol quote; hourly timers retained; no production rules optimized',production_changed=False))
 print('Generated namespaced research adapter:',len('\n'.join(chunks)),'characters')
if __name__=='__main__':main()
