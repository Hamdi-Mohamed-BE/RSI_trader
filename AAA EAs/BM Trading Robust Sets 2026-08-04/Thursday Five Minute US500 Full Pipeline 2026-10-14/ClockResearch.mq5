#property strict
#property description "Clock study: tester-only. Never permitted on live/demo charts."
#include <Trade/Trade.mqh>
input int InpWeekday=3; // Monday=0
input int InpEntryMinuteET=610;
input int InpHoldMinutes=5;
input int InpSide=1;
input double InpLots=1.0;
input string InpTag="clock-study";
CTrade trader;
int dayKey=-1,failures=0,eqFile=INVALID_HANDLE,dealFile=INVALID_HANDLE;
bool entered=false;
datetime exitAt=0,lastMinute=0;
double equityPeak=10000,maxDD=0,dayPeak=10000,maxDailyDD=0,dayStart=10000,maxDailyStartLoss=0;
int Sunday(int year,int month,int nth)
{
 MqlDateTime d;ZeroMemory(d);d.year=year;d.mon=month;d.day=1;
 datetime t=StructToTime(d);TimeToStruct(t,d);
 return 1+(7-d.day_of_week)%7+7*(nth-1);
}
bool Summer(int year,int month,int day)
{
 if(month<3 || month>11)return false;
 if(month>3 && month<11)return true;
 if(month==3)return day>=Sunday(year,3,2);
 return day<Sunday(year,11,1);
}
int OnInit()
{
 if(!MQLInfoInteger(MQL_TESTER))return INIT_FAILED;
 if(InpSide!=1 && InpSide!=-1)return INIT_PARAMETERS_INCORRECT;
 trader.SetExpertMagicNumber(26101401);trader.SetDeviationInPoints(100);trader.SetTypeFillingBySymbol(_Symbol);
 eqFile=FileOpen(InpTag+"-equity.jsonl",FILE_WRITE|FILE_TXT|FILE_ANSI|FILE_COMMON,0,CP_UTF8);
 dealFile=FileOpen(InpTag+"-deals.jsonl",FILE_WRITE|FILE_TXT|FILE_ANSI|FILE_COMMON,0,CP_UTF8);
 if(eqFile==INVALID_HANDLE || dealFile==INVALID_HANDLE)return INIT_FAILED;
 equityPeak=AccountInfoDouble(ACCOUNT_EQUITY);dayPeak=equityPeak;dayStart=equityPeak;
 return INIT_SUCCEEDED;
}
void OnTick()
{
 MqlTick tick;if(!SymbolInfoTick(_Symbol,tick))return;
 // Exness US500 histories are UTC server-clock. New York offset changes by calendar date.
 MqlDateTime d;TimeToStruct(tick.time,d);int key=d.year*10000+d.mon*100+d.day;
 if(key!=dayKey){dayKey=key;entered=false;dayPeak=AccountInfoDouble(ACCOUNT_EQUITY);dayStart=AccountInfoDouble(ACCOUNT_BALANCE);}
 int offset=Summer(d.year,d.mon,d.day)?4:5;
 datetime midnight=tick.time-(d.hour*3600+d.min*60+d.sec);
 datetime entryAt=midnight+(InpEntryMinuteET+offset*60)*60;
 if(PositionSelect(_Symbol) && exitAt>0 && tick.time>=exitAt)
 {
   if(!trader.PositionClose(_Symbol)){failures++;Print("CLOSE_FAILED ",trader.ResultRetcode());}
 }
 int weekday=(d.day_of_week+6)%7;
 if(!entered && weekday==InpWeekday && tick.time>=entryAt && tick.time<entryAt+60 && !PositionSelect(_Symbol))
 {
  entered=true;exitAt=entryAt+InpHoldMinutes*60;
  bool ok=InpSide>0?trader.Buy(InpLots,_Symbol,0,0,0,"Clock research"):trader.Sell(InpLots,_Symbol,0,0,0,"Clock research");
  if(!ok){failures++;Print("ENTRY_FAILED ",trader.ResultRetcode());}
 }
 double equity=AccountInfoDouble(ACCOUNT_EQUITY);double balance=AccountInfoDouble(ACCOUNT_BALANCE);
 equityPeak=MathMax(equityPeak,equity);dayPeak=MathMax(dayPeak,equity);
 maxDD=MathMax(maxDD,(equityPeak-equity)/equityPeak*100);
 maxDailyDD=MathMax(maxDailyDD,(dayPeak-equity)/dayPeak*100);
 maxDailyStartLoss=MathMax(maxDailyStartLoss,(dayStart-equity)/dayStart*100);
 datetime minute=tick.time-tick.time%60;
 if(minute!=lastMinute || PositionSelect(_Symbol))
 {
   // Minute sample plus every in-position quote. Metrics above update on every tick.
   if(minute!=lastMinute){FileWriteString(eqFile,StringFormat("{\"epoch\":%I64d,\"balance\":%.2f,\"equity\":%.2f}\n",(long)tick.time,balance,equity));lastMinute=minute;}
 }
}
void OnDeinit(const int reason)
{
 if(!MQLInfoInteger(MQL_TESTER))return;
 HistorySelect(0,TimeCurrent());
 for(int i=0;i<HistoryDealsTotal();i++)
 {
   ulong ticket=HistoryDealGetTicket(i);long type=HistoryDealGetInteger(ticket,DEAL_TYPE);
   if(type!=DEAL_TYPE_BUY && type!=DEAL_TYPE_SELL)continue;
   FileWriteString(dealFile,StringFormat("{\"ticket\":%I64u,\"position_id\":%I64d,\"epoch\":%I64d,\"entry\":%I64d,\"type\":%I64d,\"price\":%.8f,\"volume\":%.4f,\"profit\":%.2f,\"commission\":%.2f,\"swap\":%.2f,\"fee\":%.2f}\n",ticket,HistoryDealGetInteger(ticket,DEAL_POSITION_ID),HistoryDealGetInteger(ticket,DEAL_TIME),HistoryDealGetInteger(ticket,DEAL_ENTRY),type,HistoryDealGetDouble(ticket,DEAL_PRICE),HistoryDealGetDouble(ticket,DEAL_VOLUME),HistoryDealGetDouble(ticket,DEAL_PROFIT),HistoryDealGetDouble(ticket,DEAL_COMMISSION),HistoryDealGetDouble(ticket,DEAL_SWAP),HistoryDealGetDouble(ticket,DEAL_FEE)));
 }
 if(eqFile!=INVALID_HANDLE)FileClose(eqFile);if(dealFile!=INVALID_HANDLE)FileClose(dealFile);
 int f=FileOpen(InpTag+"-stats.json",FILE_WRITE|FILE_TXT|FILE_ANSI|FILE_COMMON,0,CP_UTF8);
 if(f!=INVALID_HANDLE){FileWriteString(f,StringFormat("{\"balance\":%.2f,\"equity_dd_pct\":%.8f,\"daily_equity_dd_pct\":%.8f,\"daily_start_loss_pct\":%.8f,\"failures\":%d,\"open_positions\":%d,\"point\":%.8f,\"tick_value\":%.8f,\"contract\":%.8f}",AccountInfoDouble(ACCOUNT_BALANCE),maxDD,maxDailyDD,maxDailyStartLoss,failures,PositionsTotal(),SymbolInfoDouble(_Symbol,SYMBOL_POINT),SymbolInfoDouble(_Symbol,SYMBOL_TRADE_TICK_VALUE),SymbolInfoDouble(_Symbol,SYMBOL_TRADE_CONTRACT_SIZE)));FileClose(f);}
}
