#property strict
#property description "Research-only M1 history export. No trading functions."
bool finished=false;
void ExportAll()
{
   if(finished || !MQLInfoInteger(MQL_TESTER)) return;
   string symbols[3]={"XAUUSD","USTEC","USDJPY"};
   bool ok=true;
   for(int j=0;j<3;j++)
   {
      MqlRates bars[];
      SymbolSelect(symbols[j],true);
      int count=CopyRates(symbols[j],PERIOD_M1,D'2025.09.26 00:00',D'2026.09.25 00:00',bars);
      if(count<100000) { Print("EXPORT_WAIT ",symbols[j]," bars=",count," error=",GetLastError()); ok=false;continue; }
      string file="CalyxPropCompare20260928_"+symbols[j]+"_M1.csv";
      int f=FileOpen(file,FILE_WRITE|FILE_CSV|FILE_ANSI|FILE_COMMON,',');
      if(f==INVALID_HANDLE){Print("EXPORT_FAILED ",file," ",GetLastError());ok=false;continue;}
      FileWrite(f,"time","open","high","low","close","tick_volume","spread");
      int digits=(int)SymbolInfoInteger(symbols[j],SYMBOL_DIGITS);
      for(int k=0;k<count;k++)
         FileWrite(f,(long)bars[k].time,DoubleToString(bars[k].open,digits),DoubleToString(bars[k].high,digits),DoubleToString(bars[k].low,digits),DoubleToString(bars[k].close,digits),bars[k].tick_volume,bars[k].spread);
      FileClose(f);
      Print("EXPORT_OK ",symbols[j]," bars=",count," first=",TimeToString(bars[0].time)," last=",TimeToString(bars[count-1].time)," point=",DoubleToString(SymbolInfoDouble(symbols[j],SYMBOL_POINT),digits));
   }
   if(ok){finished=true;TesterStop();}
}
int OnInit(){if(!MQLInfoInteger(MQL_TESTER))return INIT_FAILED;ExportAll();return INIT_SUCCEEDED;}
void OnTick(){ExportAll();}
