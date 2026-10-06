#property strict
#property version "1.00"
// Read-only availability diagnostic in the isolated tester; never sends orders.
datetime first_tick[3],last_tick[3];long counts[3],after[3],open_after[3];
int dates[3]={20251205,20260109,20260703};
bool SessionOpen()
{
 MqlDateTime p;TimeToStruct(TimeCurrent(),p);int seconds=p.hour*3600+p.min*60+p.sec;
 for(uint i=0;i<20;i++){
  datetime from=0,to=0;if(!SymbolInfoSessionTrade(_Symbol,(ENUM_DAY_OF_WEEK)p.day_of_week,i,from,to))break;
  int a=(int)((long)from%86400),b=(int)((long)to%86400);
  if(a==b || (a<b && seconds>=a && seconds<b) || (a>b && (seconds>=a || seconds<b)))return true;
 }
 return false;
}
int OnInit()
{
 if(!(bool)MQLInfoInteger(MQL_TESTER))return INIT_FAILED;
 for(uint i=0;i<20;i++){
  datetime from=0,to=0;if(!SymbolInfoSessionTrade(_Symbol,FRIDAY,i,from,to))break;
  PrintFormat("PROBE_FRIDAY_SESSION index=%d from_seconds=%d to_seconds=%d",i,(int)((long)from%86400),(int)((long)to%86400));
 }
 return INIT_SUCCEEDED;
}
void OnTick()
{
 MqlDateTime p;TimeToStruct(TimeCurrent(),p);int key=p.year*10000+p.mon*100+p.day;
 for(int i=0;i<3;i++)if(key==dates[i]){
  if(first_tick[i]==0)first_tick[i]=TimeCurrent();last_tick[i]=TimeCurrent();counts[i]++;
  int cutoff=(i==2?19*3600+55*60:20*3600+55*60);
  if(p.hour*3600+p.min*60+p.sec>=cutoff){after[i]++;if(SessionOpen())open_after[i]++;}
 }
}
void OnDeinit(const int reason)
{
 for(int i=0;i<3;i++)PrintFormat("PROBE_DAY date=%d count=%I64d first=%s last=%s ticks_after_NY1555=%I64d session_open_after=%I64d",
   dates[i],counts[i],TimeToString(first_tick[i],TIME_DATE|TIME_SECONDS),TimeToString(last_tick[i],TIME_DATE|TIME_SECONDS),after[i],open_after[i]);
}
