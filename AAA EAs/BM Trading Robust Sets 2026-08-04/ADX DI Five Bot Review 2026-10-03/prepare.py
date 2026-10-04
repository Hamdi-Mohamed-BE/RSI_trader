"""Mechanical instrumentation of PRIVATE copies only. Frozen originals are never edited."""
from pathlib import Path
import re,json,hashlib,shutil
R=Path(__file__).resolve().parent;B=R.parent
SPECS={
 'trend':('XAU Trend Progression','Gold Targets Deployment 2026-10-02/EA/Trend Progression EA.mq5','Gold Targets Deployment 2026-10-02/Sets/xau-trend-progression-normal.set','XAUUSD','H4',16388,1),
 'ema3':('EMA3 Gold','AAA Final EAs/AAA Final EMA3 EA/AAA Final EMA3 EA.mq5','Selected Portfolio Settings 2026-09-01/08 EMA3 - H4 PIVOT 1.7R - DYNAMIC 60-20 ONLY.set','XAUUSD','H4',16388,1),
 'asia':('Asia Breakout Gold','AAA Final EAs/AAA Final Asia Breakout EA/AAA Final Asia Breakout EA.mq5','Selected Portfolio Settings 2026-09-01/06 Asia Breakout - DYNAMIC 50-20 - ALL DAY.set','XAUUSD','H1',16385,1),
 'london':('USDJPY London Momentum','London Open FX Momentum Research 2026-09-08/Pipeline/EA/Calyx London Open FX Momentum Pipeline EA.mq5','London Open FX Momentum Research 2026-09-08/Pipeline/Sets/London Open FX Momentum - USDJPY - pipeline selected - 1pct.set','USDJPY','M15',15,1),
 'rsi':('XAU RSI VWAP','RSI VWAP Research 2026-09-02/EA/RSI VWAP Managed EA.mq5','Selected Portfolio Settings 2026-09-01/13 XAU RSI VWAP - CURRENT - ALL DAY.set','XAUUSD','H1',16385,2)}
def read(p):
 b=p.read_bytes();return b.decode('utf-16') if b[:2] in (b'\xff\xfe',b'\xfe\xff') else b.decode('utf-8-sig')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def replace_once(s,old,new):
 assert s.count(old)==1,(old,s.count(old));return s.replace(old,new,1)
def instrument(s,tf):
 # Include location changes only; all algorithmic logic outside admission stays identical.
 s=re.sub(r'#include "(?:\.\.\\)+_Shared\\CalyxAdaptivePortfolio.mqh"','#include "'+str(B/'_Shared/CalyxAdaptivePortfolio.mqh').replace('\\','/')+'"',s)
 s=replace_once(s,'int OnInit()','int OnInit()') if 'int OnInit()' in s else s
 if 'int OnInit()' in s:
  s=re.sub(r'(int OnInit\(\)\s*\{)',r'\1\n   if(!StudyInit()) return INIT_FAILED;',s,count=1)
 if 'void OnDeinit(' in s:s=re.sub(r'(void OnDeinit\([^)]*\)\s*\{)',r'\1\n   StudyClose();',s,count=1)
 elif 'int OnInit()' in s:s+='\nvoid OnDeinit(const int reason) { StudyClose(); }\n'
 return s
def main():
 manifest={}
 for key,(label,src,setting,symbol,period,tf,mode) in SPECS.items():
  original=B/src;sett=B/setting;folder=R/'EA'/key;folder.mkdir(parents=True,exist_ok=True)
  assert original.exists() and original.with_suffix('.ex5').exists() and sett.exists()
  # Copy each bot's own headers, never mix EMA3 and Asia engines.
  for p in original.parent.glob('*.mqh'):
   s=instrument(read(p),tf)
   if p.name=='AAA_Final_Common.mqh':
    s=replace_once(s,'#include <Trade/Trade.mqh>','#include <Trade/Trade.mqh>\n#include "../StudyFilter.mqh"')
    s=replace_once(s,'   AAA_Trade.SetExpertMagicNumber((ulong)magic);\n   AAA_Trade.SetTypeFillingBySymbol(symbol);\n   AAA_Trade.SetDeviationInPoints(20);','   if(!StudyAllow(direction)) return false;\n   AAA_Trade.SetExpertMagicNumber((ulong)magic);\n   AAA_Trade.SetTypeFillingBySymbol(symbol);\n   AAA_Trade.SetDeviationInPoints(20);')
    s=s.replace('AAA_Trade.Buy(', 'StudyBuy(AAA_Trade,').replace('AAA_Trade.Sell(', 'StudySell(AAA_Trade,')
   (folder/p.name).write_text(s,encoding='utf-8')
  s=instrument(read(original),tf)
  if key not in ('ema3','asia'):
   s=replace_once(s,'#include <Trade/Trade.mqh>','#include <Trade/Trade.mqh>\n#include "../StudyFilter.mqh"')
   marker='   trade.SetExpertMagicNumber(InpMagic);' if key in ('trend','rsi') else '   trade.SetExpertMagicNumber((ulong)InpMagic);'
   # First occurrence in the entry function, not OnInit / exit management.
   if key=='london':
    anchor='   if(lots<=0.0) return;\n\n   trade.SetExpertMagicNumber((ulong)InpMagic);'
    s=replace_once(s,anchor,'   if(lots<=0.0) return;\n   if(!StudyAllow(direction)) return;\n\n   trade.SetExpertMagicNumber((ulong)InpMagic);')
   else:
    pos=s.index('void ProcessNewBar()');end=s.index('int OnInit()',pos);part=s[pos:end]
    part=replace_once(part,marker,('   if(!StudyAllow('+('1' if key=='rsi' else 'direction')+')) return;\n')+marker)
    s=s[:pos]+part+s[end:]
   s=s.replace('trade.Buy(','StudyBuy(trade,').replace('trade.Sell(','StudySell(trade,')
  (folder/'Research.mq5').write_text(s,encoding='utf-8')
  shutil.copy2(sett,folder/'BASE.set')
  inputs={}
  for line in read(sett).splitlines():
   if '=' in line and not line.startswith(';'):
    k,v=line.split('=',1);inputs[k]=v.split('||')[0]
  # Original inputs include default-off adaptive controls even if the SET omits them.
  inputs.update(InpRiskPercent='1.0',InpAdaptivePortfolioControls='false')
  manifest[key]=dict(label=label,source=str(original),original=str(original.with_suffix('.ex5')),setting=str(sett),symbol=symbol,period=period,tf=tf,gate=mode,inputs=inputs,original_sha=sha(original.with_suffix('.ex5')),source_sha=sha(original),set_sha=sha(sett))
 (R/'bots.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
 print('Prepared five isolated copies; original sources and binaries unchanged.')
if __name__=='__main__':main()
