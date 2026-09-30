#property strict
#property description "Tester-only no-trade M5 history collector"
string symbols[13]={"US30","USTEC","US500","XAUUSD","BTCUSD","ETHUSD","EURUSD","GBPUSD","USDJPY","AUDUSD","NZDUSD","USDCAD","USDCHF"};
int OnInit()
{
   if(!MQLInfoInteger(MQL_TESTER))return INIT_FAILED;
   for(int i=0;i<13;i++){SymbolSelect(symbols[i],true);MqlRates a[];CopyRates(symbols[i],PERIOD_M5,D'2021.09.01',D'2021.09.02',a);}
   return INIT_SUCCEEDED;
}
void OnTick(){}
double OnTester()
{
   if(!MQLInfoInteger(MQL_TESTER))return 0;
   int sf=FileOpen("CalyxBias20260929_specs.csv",FILE_WRITE|FILE_CSV|FILE_ANSI|FILE_COMMON,',');
   FileWrite(sf,"symbol","point","tick_size","digits","contract_size","volume_min","volume_step");
   for(int j=0;j<13;j++)
   {
      MqlRates bars[];
      int n=CopyRates(symbols[j],PERIOD_M5,D'2021.09.27',D'2026.09.26 23:59',bars);
      if(n<1){Print("BIAS_FAILED ",symbols[j]," ",GetLastError());continue;}
      int digits=(int)SymbolInfoInteger(symbols[j],SYMBOL_DIGITS);
      int f=FileOpen("CalyxBias20260929_"+symbols[j]+"_M5.csv",FILE_WRITE|FILE_CSV|FILE_ANSI|FILE_COMMON,',');
      if(f==INVALID_HANDLE){Print("BIAS_FAILED_FILE ",symbols[j]);continue;}
      FileWrite(f,"time","open","high","low","close","tick_volume","spread");
      for(int k=0;k<n;k++)FileWrite(f,(long)bars[k].time,DoubleToString(bars[k].open,digits),DoubleToString(bars[k].high,digits),DoubleToString(bars[k].low,digits),DoubleToString(bars[k].close,digits),bars[k].tick_volume,bars[k].spread);
      FileClose(f);
      FileWrite(sf,symbols[j],DoubleToString(SymbolInfoDouble(symbols[j],SYMBOL_POINT),digits),DoubleToString(SymbolInfoDouble(symbols[j],SYMBOL_TRADE_TICK_SIZE),digits),digits,SymbolInfoDouble(symbols[j],SYMBOL_TRADE_CONTRACT_SIZE),SymbolInfoDouble(symbols[j],SYMBOL_VOLUME_MIN),SymbolInfoDouble(symbols[j],SYMBOL_VOLUME_STEP));
      Print("BIAS_OK ",symbols[j]," count=",n," first=",TimeToString(bars[0].time)," last=",TimeToString(bars[n-1].time));
   }
   FileClose(sf);
   return 0;
}
