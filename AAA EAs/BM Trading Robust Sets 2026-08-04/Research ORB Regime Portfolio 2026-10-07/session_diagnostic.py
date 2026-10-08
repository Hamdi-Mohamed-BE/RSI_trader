"""Logging-only native diagnostic; never changes or reselects frozen settings."""
print('Logging-only session diagnostic started',flush=True)
import gzip,json
import pandas as pd
import runner as r

original_build=r.build_engine.build
def instrument(cases):
 source=original_build(cases)
 old='if(HHMM(TimeCurrent())>=1555){if(!trade.PositionClose(t))updates++;return;}'
 new='''if(HHMM(TimeCurrent())>=1555){
  static ulong reported=0;
  if(!trade.PositionClose(t)){
   updates++;
   if(reported!=t){
    reported=t;MqlRates b[];
    MqlDateTime date;TimeToStruct(TimeCurrent(),date);
    string sessions="";datetime from,to;
    for(uint index=0;index<10;index++){
     if(!SymbolInfoSessionTrade(_Symbol,(ENUM_DAY_OF_WEEK)date.day_of_week,index,from,to))break;
     sessions+="_"+(string)((long)from)+"-"+(string)((long)to);
    }
    if(CopyRates(_Symbol,PERIOD_M5,1,1,b)==1)Log("close_failure_"+(string)trade.ResultRetcode()+"_"+trade.ResultRetcodeDescription()+"_sessions"+sessions,b[0]);
   }
  }
  return;
 }'''
 assert source.count(old)==1
 return source.replace(old,new)

def main():
 r.build_engine.build=instrument
 frozen=r.load(r.R/'CORRECTED FROZEN.json');outputs={}
 lock=r.lease()
 try:
  for symbol in ['USTEC','XAUUSD']:
   start,end=('2026-01-16','2026-01-20') if symbol=='USTEC' else ('2026-06-19','2026-06-23')
   rows=r.batch('session-diagnostic-'+symbol,[frozen['symbols'][symbol]['selected']['0']],start,end,model=4,optimize=False,verbose=True,symbol=symbol)
   decisions=pd.read_csv(r.R/'native'/rows[0]['stage']/'0-decisions.csv.gz')
   failures=decisions[decisions.reason.str.startswith('close_failure')].to_dict('records')
   outputs[symbol]=dict(logging_only=True,parameter_changes=False,source_freeze_unchanged=True,close_failures=failures,
    trades=rows[0]['trades'],native=rows[0]['native'])
  r.save(r.R/'SESSION DIAGNOSTIC.json',outputs)
  print(json.dumps(outputs,indent=2),flush=True)
 finally:lock.close()
if __name__=='__main__':
 try:main()
 except Exception:
  import traceback
  print(traceback.format_exc(),flush=True)
  raise
