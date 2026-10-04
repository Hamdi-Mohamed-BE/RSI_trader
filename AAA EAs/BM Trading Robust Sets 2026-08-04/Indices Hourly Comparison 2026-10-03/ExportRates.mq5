#property strict
#property description "Tester-only history collector, no order submission."
bool finished=false;
void Export(){
 if(finished || !MQLInfoInteger(MQL_TESTER))return;
 string prefix="IndicesHourly20261003-"+_Symbol;
 int f=FileOpen(prefix+".csv",FILE_WRITE|FILE_CSV|FILE_ANSI|FILE_COMMON,',');
 if(f==INVALID_HANDLE)return;
 FileWrite(f,"time","open","high","low","close","tick_volume","spread");
 int total=0,digits=(int)SymbolInfoInteger(_Symbol,SYMBOL_DIGITS);
 for(int y=2025;y<=2026;y++){
  datetime a=StringToTime(IntegerToString(y)+".01.01"),b=StringToTime(IntegerToString(y+1)+".01.01")-1;
  a=MathMax(a,D'2025.10.03');b=MathMin(b,D'2026.10.03'-1);
  MqlRates r[];int n=CopyRates(_Symbol,PERIOD_M1,a,b,r);
  if(n<1000){FileClose(f);Print("INDEX_EXPORT_WAIT ",_Symbol," ",y," ",n);return;}
  for(int i=0;i<n;i++)FileWrite(f,(long)r[i].time,DoubleToString(r[i].open,digits),DoubleToString(r[i].high,digits),DoubleToString(r[i].low,digits),DoubleToString(r[i].close,digits),r[i].tick_volume,r[i].spread);
  total+=n;Print("INDEX_EXPORT_YEAR ",_Symbol," ",y," ",n," ",TimeToString(r[0].time)," ",TimeToString(r[n-1].time));
 }
 FileClose(f);
 int s=FileOpen(prefix+"-spec.csv",FILE_WRITE|FILE_CSV|FILE_ANSI|FILE_COMMON,',');
 FileWrite(s,"point","tick_size","tick_value_profit","tick_value_loss","contract_size","volume_min","volume_step","swap_long","swap_short","swap_mode","swap_rollover3days");
 FileWrite(s,SymbolInfoDouble(_Symbol,SYMBOL_POINT),SymbolInfoDouble(_Symbol,SYMBOL_TRADE_TICK_SIZE),SymbolInfoDouble(_Symbol,SYMBOL_TRADE_TICK_VALUE_PROFIT),SymbolInfoDouble(_Symbol,SYMBOL_TRADE_TICK_VALUE_LOSS),SymbolInfoDouble(_Symbol,SYMBOL_TRADE_CONTRACT_SIZE),SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MIN),SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_STEP),SymbolInfoDouble(_Symbol,SYMBOL_SWAP_LONG),SymbolInfoDouble(_Symbol,SYMBOL_SWAP_SHORT),(int)SymbolInfoInteger(_Symbol,SYMBOL_SWAP_MODE),(int)SymbolInfoInteger(_Symbol,SYMBOL_SWAP_ROLLOVER3DAYS));FileClose(s);
 finished=true;Print("INDEX_EXPORT_OK ",_Symbol," count=",total);TesterStop();
}
int OnInit(){if(!MQLInfoInteger(MQL_TESTER))return INIT_FAILED;return INIT_SUCCEEDED;}
void OnTick(){if(TimeCurrent()>=D'2026.10.02')Export();}
