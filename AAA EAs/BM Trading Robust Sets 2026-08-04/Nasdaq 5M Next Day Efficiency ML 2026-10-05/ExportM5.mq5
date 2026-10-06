#property strict
#property description "Research-only past USTEC M5 export. Cannot trade."
bool done=false;
void Export()
{
 if(done || !MQLInfoInteger(MQL_TESTER))return;
 MqlRates bars[];
 int n=CopyRates(_Symbol,PERIOD_M5,D'2020.01.01',D'2026.10.03',bars);
 if(n<100000){Print("ER_EXPORT_WAIT n=",n," err=",GetLastError());return;}
 int f=FileOpen("CalyxNasdaqER20261005-M5.csv",FILE_WRITE|FILE_CSV|FILE_ANSI|FILE_COMMON,',');
 if(f==INVALID_HANDLE){Print("ER_EXPORT_ERROR ",GetLastError());return;}
 FileWrite(f,"time","open","high","low","close","tick_volume","spread");
 for(int k=0;k<n;k++)FileWrite(f,(long)bars[k].time,DoubleToString(bars[k].open,2),DoubleToString(bars[k].high,2),DoubleToString(bars[k].low,2),DoubleToString(bars[k].close,2),bars[k].tick_volume,bars[k].spread);
 FileClose(f);done=true;
 Print("ER_EXPORT_OK n=",n," first=",TimeToString(bars[0].time)," last=",TimeToString(bars[n-1].time));
}
int OnInit(){if(!MQLInfoInteger(MQL_TESTER))return INIT_FAILED;return INIT_SUCCEEDED;}
void OnTick(){}
double OnTester(){Export();return 0;}
