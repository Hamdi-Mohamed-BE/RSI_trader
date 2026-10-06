#property strict
#property version "1.00"
#include <Trade/Trade.mqh>
// Tiny isolated simulated position checks whether historical close is accepted.
// Refuses live/demo execution; NOT strategy performance.
CTrade t;bool entered=false,attempted=false;
int OnInit(){if(!(bool)MQLInfoInteger(MQL_TESTER))return INIT_FAILED;t.SetExpertMagicNumber(865001);t.SetTypeFillingBySymbol(_Symbol);return INIT_SUCCEEDED;}
void OnTick(){
 MqlDateTime p;TimeToStruct(TimeCurrent(),p);
 if(p.year!=2025 || p.mon!=12 || p.day!=5)return;
 if(!entered && p.hour==20 && p.min>=53){
  entered=true;MqlTick q;if(!SymbolInfoTick(_Symbol,q))return;
  bool ok=t.Buy(SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MIN),_Symbol,0,NormalizeDouble(q.bid-100,(int)SymbolInfoInteger(_Symbol,SYMBOL_DIGITS)),0,"PROBE");
  PrintFormat("PROBE_HIST_ENTRY time=%s ok=%d retcode=%d reason=%s",TimeToString(TimeCurrent(),TIME_DATE|TIME_SECONDS),ok,t.ResultRetcode(),t.ResultRetcodeDescription());
 }
 if(entered && !attempted && p.hour==20 && p.min>=55){
  attempted=true;
  for(int i=PositionsTotal()-1;i>=0;i--) {
   ulong id=PositionGetTicket(i);if(id==0 || PositionGetInteger(POSITION_MAGIC)!=865001)continue;
   bool ok=t.PositionClose(id);
   PrintFormat("PROBE_HIST_CLOSE time=%s ok=%d retcode=%d reason=%s",TimeToString(TimeCurrent(),TIME_DATE|TIME_SECONDS),ok,t.ResultRetcode(),t.ResultRetcodeDescription());
  }
 }
}
