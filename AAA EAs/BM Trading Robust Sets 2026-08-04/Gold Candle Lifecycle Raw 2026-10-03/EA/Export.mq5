#property strict
#property version "1.00"
#property description "Tester-only, no-order candle timing collector."
input datetime InpFrom=D'2025.09.25';
input datetime InpTo=D'2026.10.03';
int OnInit(){if(!MQLInfoInteger(MQL_TESTER))return INIT_FAILED;return INIT_SUCCEEDED;}
void OnTick(){}
bool Export(const ENUM_TIMEFRAMES tf,const string label)
{
 int f=FileOpen("GoldLifecycle20261003-"+label+".csv",FILE_WRITE|FILE_CSV|FILE_ANSI|FILE_COMMON,',');
 if(f==INVALID_HANDLE)return false;
 FileWrite(f,"time","open","high","low","close","tick_volume","spread");
 MqlRates r[];int n=CopyRates(_Symbol,tf,InpFrom,InpTo-1,r);
 for(int i=0;i<n;i++)FileWrite(f,(long)r[i].time,DoubleToString(r[i].open,_Digits),DoubleToString(r[i].high,_Digits),DoubleToString(r[i].low,_Digits),DoubleToString(r[i].close,_Digits),r[i].tick_volume,r[i].spread);
 FileClose(f);Print("LIFECYCLE_EXPORT ",label," ",n);return n>0;
}
void OnDeinit(const int reason)
{
 if(!MQLInfoInteger(MQL_TESTER))return;
 bool ok=Export(PERIOD_M1,"M1");ok=Export(PERIOD_H1,"H1") && ok;ok=Export(PERIOD_H4,"H4") && ok;ok=Export(PERIOD_D1,"D1") && ok;
 int f=FileOpen("GoldLifecycle20261003-spec.csv",FILE_WRITE|FILE_CSV|FILE_ANSI|FILE_COMMON,',');
 FileWrite(f,"point","tick_size","contract_size","volume_min","volume_step","stops_level");
 FileWrite(f,_Point,SymbolInfoDouble(_Symbol,SYMBOL_TRADE_TICK_SIZE),SymbolInfoDouble(_Symbol,SYMBOL_TRADE_CONTRACT_SIZE),SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MIN),SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_STEP),SymbolInfoInteger(_Symbol,SYMBOL_TRADE_STOPS_LEVEL));FileClose(f);
 if(ok)Print("LIFECYCLE_EXPORT_OK");
}
