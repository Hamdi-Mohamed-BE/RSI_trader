#property strict
#property version "1.00"
#property description "Tester-only read-only minute availability audit. Never sends orders."
int OnInit(){return MQLInfoInteger(MQL_TESTER)?INIT_SUCCEEDED:INIT_FAILED;}
void OnTick(){}
double OnTester()
{
 MqlRates bars[];int n=CopyRates(_Symbol,PERIOD_M1,D'2021.08.01',TimeCurrent(),bars);
 if(n<=0){PrintFormat("PS_MINUTE_FAILED copy %d",GetLastError());return -1;}
 int f=FileOpen("CalyxPDSweep20260928\\"+_Symbol+"-M1.bin",FILE_COMMON|FILE_WRITE|FILE_BIN);
 if(f==INVALID_HANDLE){Print("PS_MINUTE_FAILED file");return -1;}
 for(int i=0;i<n;i++){FileWriteLong(f,(long)bars[i].time);FileWriteDouble(f,bars[i].open);FileWriteDouble(f,bars[i].high);FileWriteDouble(f,bars[i].low);FileWriteDouble(f,bars[i].close);FileWriteLong(f,bars[i].tick_volume);}
 FileClose(f);PrintFormat("PS_MINUTE_OK rows=%d first=%I64d last=%I64d",n,(long)bars[0].time,(long)bars[n-1].time);return n;
}
