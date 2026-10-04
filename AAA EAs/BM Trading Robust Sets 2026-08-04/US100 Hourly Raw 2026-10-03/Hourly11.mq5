#property strict
#property description "Tester-only 11 to noon NY timing model. Fixed lot; no stop-loss."
#include <Trade/Trade.mqh>
input double InpLots=1.0;
input long InpMagic=10031112;
input string InpTag="hourly";
CTrade trade;
int usedDay=-1,entries=0,failures=0,closeFailures=0,f=INVALID_HANDLE;
datetime BuildTime(int y,int m,int d,int hour){MqlDateTime x;ZeroMemory(x);x.year=y;x.mon=m;x.day=d;x.hour=hour;return StructToTime(x);}
int Sunday(int y,int m,int nth){MqlDateTime x;TimeToStruct(BuildTime(y,m,1,0),x);return 1+(7-x.day_of_week)%7+(nth-1)*7;}
datetime NewYork(datetime server){MqlDateTime x;TimeToStruct(server,x);datetime a=BuildTime(x.year,3,Sunday(x.year,3,2),7),b=BuildTime(x.year,11,Sunday(x.year,11,1),6);return server+((server>=a&&server<b)?-4:-5)*3600;}
int OnInit(){
 if(!MQLInfoInteger(MQL_TESTER))return INIT_FAILED;
 trade.SetExpertMagicNumber(InpMagic);trade.SetTypeFillingBySymbol(_Symbol);trade.SetDeviationInPoints(1000);
 f=FileOpen("US100Hourly20261003-"+InpTag+"-fills.csv",FILE_WRITE|FILE_CSV|FILE_ANSI|FILE_COMMON,',');if(f==INVALID_HANDLE)return INIT_FAILED;
 FileWrite(f,"time","action","bid","ask","result_price","retcode");return INIT_SUCCEEDED;
}
void OnTick(){
 MqlDateTime ny;TimeToStruct(NewYork(TimeCurrent()),ny);int date=ny.year*10000+ny.mon*100+ny.day;
 if(PositionSelect(_Symbol)&&PositionGetInteger(POSITION_MAGIC)==InpMagic){
  if(ny.hour>=12||date!=usedDay){
   MqlTick q;SymbolInfoTick(_Symbol,q);bool ok=trade.PositionClose(_Symbol);
   FileWrite(f,(long)TimeCurrent(),"CLOSE",q.bid,q.ask,trade.ResultPrice(),trade.ResultRetcode());
   if(!ok||trade.ResultRetcode()!=TRADE_RETCODE_DONE)closeFailures++;
  }return;
 }
 if(ny.day_of_week<1||ny.day_of_week>5||ny.hour!=11||ny.min!=0||usedDay==date)return;
 usedDay=date;MqlTick q;SymbolInfoTick(_Symbol,q);bool ok=trade.Buy(InpLots,_Symbol,0,0,0,"11NY to noon");
 FileWrite(f,(long)TimeCurrent(),"BUY",q.bid,q.ask,trade.ResultPrice(),trade.ResultRetcode());
 if(ok&&trade.ResultRetcode()==TRADE_RETCODE_DONE)entries++;else failures++;
}
void OnDeinit(const int reason){if(f!=INVALID_HANDLE)FileClose(f);PrintFormat("HOUR_NATIVE_SUMMARY entries=%d entry_fail=%d close_fail=%d",entries,failures,closeFailures);}
