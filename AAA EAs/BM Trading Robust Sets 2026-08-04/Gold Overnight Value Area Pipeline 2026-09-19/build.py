"""Deterministic parameterization of frozen raw source; never edits the raw EA."""
import subprocess,shutil
from data import ROOT,RAW,PACKAGE,sha,save
TESTER=PACKAGE/'_Backtests/MT5-DMC-20260811'
SOURCE=ROOT/'Gold Overnight Value Area Research.mq5'
def build():
 original=RAW/'Overnight Profile Raw.mq5';code=original.read_text(encoding='utf-8')
 changes=[
 ('#property version "1.00"','#property version "1.10"'),
 ('input int InpDirectionMode=0;', '''input int InpEntryEndMinute=960; // New York minutes after midnight
input int InpExitMinute=960;
input int InpStopMode=0; // 0=opposite value area, 1=POC
input double InpMinimumR=0;
input double InpTargetR=0; // 0=overnight extreme
input double InpBreakEvenR=0;
input double InpTrailDistanceR=0; // activate at 1R, closed-M5 trailing
double pipeline_initial_risk=0;
datetime pipeline_trail_bar=0;
input int InpDirectionMode=0;'''),
 ('FromNY(today+16*3600)','FromNY(today+InpExitMinute*60)'),
 ('if(now<open || now>=cutoff)return;','if(now<open || now>=cutoff || now>=FromNY(today+InpEntryEndMinute*60))return;'),
 ('double entry=side>0?tick.ask:tick.bid,stop=Price(side>0?val-step:vah+step),target=Price(side>0?hi:lo);',
  'double anchor=InpStopMode==1?poc:(side>0?val:vah);\n double entry=side>0?tick.ask:tick.bid,stop=Price(anchor-side*step),target=Price(side>0?hi:lo);\n if(InpTargetR>0)target=Price(entry+side*InpTargetR*MathAbs(entry-stop));'),
 ('if(!valid){geometry++;Audit("invalid_geometry",now,side,entry,stop,target);return;}',
  'if(!valid || side*(entry-stop)<=0 || MathAbs(target-entry)/MathAbs(entry-stop)<InpMinimumR){geometry++;Audit("invalid_geometry",now,side,entry,stop,target);return;}'),
 ('entries++;Audit("entry",now,side,entry,stop,target,lots,MathAbs(unit)*lots);',
  'pipeline_initial_risk=MathAbs(trade.ResultPrice()-stop);pipeline_trail_bar=0;\n  entries++;Audit("entry",now,side,entry,stop,target,lots,MathAbs(unit)*lots);'),
 ('if(now>=cutoff || Key(ToNY(entered))!=Key(ToNY(now))) {',
  '''if((InpBreakEvenR>0 || InpTrailDistanceR>0) && pipeline_initial_risk>0) {
  MqlTick tick;if(SymbolInfoTick(_Symbol,tick)) {
   int side=PositionGetInteger(POSITION_TYPE)==POSITION_TYPE_BUY?1:-1;
   double entry=PositionGetDouble(POSITION_PRICE_OPEN),sl=PositionGetDouble(POSITION_SL),tp=PositionGetDouble(POSITION_TP);
   double market=side>0?tick.bid:tick.ask,progress=side*(market-entry)/pipeline_initial_risk,candidate=sl;
   if(InpBreakEvenR>0 && progress>=InpBreakEvenR)candidate=side>0?MathMax(candidate,entry):MathMin(candidate,entry);
   datetime current=iTime(_Symbol,PERIOD_M5,0);
   if(InpTrailDistanceR>0 && progress>=1 && current!=pipeline_trail_bar) {
    pipeline_trail_bar=current;MqlRates bar[];
    if(CopyRates(_Symbol,PERIOD_M5,1,1,bar)==1) {
     double level=bar[0].close-side*InpTrailDistanceR*pipeline_initial_risk;
     candidate=side>0?MathMax(candidate,level):MathMin(candidate,level);
    }
   }
   candidate=Price(candidate);
   double minimum=SymbolInfoInteger(_Symbol,SYMBOL_TRADE_STOPS_LEVEL)*_Point;
   if(side*(candidate-sl)>0 && side*(market-candidate)>minimum)trade.PositionModify(id,candidate,tp);
  }
 }
 if(now>=cutoff || Key(ToNY(entered))!=Key(ToNY(now))) {'''),
 ('InpDirectionMode>1 || InpBins<2 || InpRiskPercent<=0',
  'InpDirectionMode>1 || InpBins<2 || InpRiskPercent<=0 || InpEntryEndMinute<=575 || InpExitMinute<=575 || InpStopMode<0 || InpStopMode>1')]
 for old,new in changes:
  assert code.count(old)==1,(old,code.count(old));code=code.replace(old,new,1)
 SOURCE.write_text(code,encoding='utf-8')
 log=ROOT/'compile.log'
 subprocess.run(f'"{TESTER/"MetaEditor64.exe"}" /portable /compile:"{SOURCE}" /log:"{log}"',creationflags=subprocess.CREATE_NO_WINDOW,timeout=90)
 assert '0 errors, 0 warnings' in log.read_text(encoding='utf-16')
 dest=TESTER/'MQL5/Experts/AAA Research/Gold VA Pipeline 20260919';dest.mkdir(parents=True,exist_ok=True)
 shutil.copy2(SOURCE.with_suffix('.ex5'),dest/SOURCE.with_suffix('.ex5').name)
 save(ROOT/'build.json',dict(raw_source_sha256=sha(original),source_sha256=sha(SOURCE),binary_sha256=sha(SOURCE.with_suffix('.ex5')),generator_sha256=sha(ROOT/'build.py')))
 print('COMPILED zero errors/warnings',flush=True)
if __name__=='__main__':build()
