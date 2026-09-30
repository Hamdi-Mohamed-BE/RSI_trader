#property strict
#property version "1.00"
#property description "Tester-only read-only historical bar exporter; never sends orders."
input datetime InpFrom=D'2020.01.01';
int OnInit(){return MQLInfoInteger(MQL_TESTER)?INIT_SUCCEEDED:INIT_FAILED;}
void OnTick(){}
bool Export(ENUM_TIMEFRAMES tf,string label)
{
 MqlRates bars[];int n=CopyRates(_Symbol,tf,InpFrom,TimeCurrent(),bars);
 if(n<=0){PrintFormat("LC_AUDIT_FAILED %s %d",label,GetLastError());return false;}
 int f=FileOpen("LC_AUDIT_"+_Symbol+"_"+label+".bin",FILE_WRITE|FILE_BIN);
 if(f==INVALID_HANDLE){Print("LC_AUDIT_FILE_FAILED");return false;}
 for(int i=0;i<n;i++){FileWriteLong(f,(long)bars[i].time);FileWriteDouble(f,bars[i].open);FileWriteDouble(f,bars[i].high);FileWriteDouble(f,bars[i].low);FileWriteDouble(f,bars[i].close);FileWriteLong(f,bars[i].tick_volume);}
 FileClose(f);PrintFormat("LC_AUDIT_EXPORTED %s %s rows=%d first=%I64d last=%I64d",_Symbol,label,n,(long)bars[0].time,(long)bars[n-1].time);return true;
}
double OnTester(){bool a=Export(PERIOD_M5,"M5"),b=Export(PERIOD_D1,"D1");return a && b?1:0;}
