#property strict
#property description "Tester-only, no-trade H1 exporter for independent signal verification"
string names[6]={"USTEC","BTCUSD","XAUUSD","EURUSD","GBPUSD","USDJPY"};
int OnInit(){if(!MQLInfoInteger(MQL_TESTER))return INIT_FAILED;for(int i=0;i<6;i++){SymbolSelect(names[i],true);MqlRates r[];CopyRates(names[i],PERIOD_H1,D'2021.06.01',D'2021.06.02',r);}return INIT_SUCCEEDED;}
void OnTick(){}
double OnTester(){
 FolderCreate("CalyxMarketStyles20260929",FILE_COMMON);
 for(int i=0;i<6;i++){
  MqlRates r[];int n=CopyRates(names[i],PERIOD_H1,D'2021.06.01',D'2026.09.26 23:59:59',r);
  if(n<1000){PrintFormat("MS_EXPORT_FAIL %s n=%d code=%d",names[i],n,GetLastError());continue;}
  int f=FileOpen("CalyxMarketStyles20260929\\"+names[i]+"-H1.csv",FILE_WRITE|FILE_CSV|FILE_ANSI|FILE_COMMON,',');
  FileWrite(f,"time","open","high","low","close","spread");int d=(int)SymbolInfoInteger(names[i],SYMBOL_DIGITS);
  for(int k=0;k<n;k++)FileWrite(f,(long)r[k].time,DoubleToString(r[k].open,d),DoubleToString(r[k].high,d),DoubleToString(r[k].low,d),DoubleToString(r[k].close,d),r[k].spread);
  FileClose(f);PrintFormat("MS_EXPORT_OK %s rows=%d from=%s to=%s",names[i],n,TimeToString(r[0].time),TimeToString(r[n-1].time));
 }
 return 0;
}
