#property copyright "US100 direct opening-range breakout research EA"
#property version   "1.00"
#property strict

#include <Trade/Trade.mqh>

input group "New York opening range"
input int             InpCashOpenHour=9;
input int             InpCashOpenMinute=30;
input int             InpOpeningRangeMinutes=30;
input int             InpEntryCutoffMinutesAfterOpen=330;
input int             InpFlatHour=15;
input int             InpFlatMinute=0;
input ENUM_TIMEFRAMES InpSignalTimeframe=PERIOD_M5;
input bool            InpWeekdaysOnly=true;

input group "Direct breakout"
input int             InpTradeDirection=1; // 0=both, 1=long only, 2=short only
input bool            InpRequireDirectionalBreakoutCandle=false;
input double          InpBreakoutBufferPoints=0.0;
input bool            InpOneTradePerDay=true;

input group "Volatility-targeted sizing and exits"
input double          InpRiskPercent=1.0;
input double          InpRewardRisk=1.0;
input double          InpStopBufferPoints=0.0;
input double          InpMaximumSpreadRiskPercent=10.0;
input int             InpMaximumDeviationPoints=50;
input long            InpMagic=86260829;

input group "Broker clock"
input bool            InpUseAutomaticLiveServerOffset=true;
input int             InpTesterServerUTCOffsetHours=0;
input int             InpManualLiveServerUTCOffsetHours=0;
input bool            InpShowRange=true;

CTrade trade;
datetime g_last_bar=0;
int g_session_key=0;
bool g_range_ready=false;
bool g_traded_today=false;
double g_range_high=0.0;
double g_range_low=0.0;

int NthSunday(const int year,const int month,const int occurrence)
{
   MqlDateTime value={0};
   value.year=year; value.mon=month; value.day=1; value.hour=12;
   datetime first=StructToTime(value);
   TimeToStruct(first,value);
   return 1+((7-value.day_of_week)%7)+(occurrence-1)*7;
}

int NewYorkUTCOffsetHours(const datetime utc_time)
{
   MqlDateTime value; TimeToStruct(utc_time,value);
   MqlDateTime start={0},finish={0};
   start.year=value.year; start.mon=3; start.day=NthSunday(value.year,3,2); start.hour=7;
   finish.year=value.year; finish.mon=11; finish.day=NthSunday(value.year,11,1); finish.hour=6;
   return (utc_time>=StructToTime(start) && utc_time<StructToTime(finish) ? -4 : -5);
}

bool NewYorkDateUsesDST(const MqlDateTime &ny)
{
   int march=NthSunday(ny.year,3,2);
   int november=NthSunday(ny.year,11,1);
   if(ny.mon>3 && ny.mon<11) return true;
   if(ny.mon<3 || ny.mon>11) return false;
   if(ny.mon==3) return ny.day>=march;
   return ny.day<november;
}

int ServerUTCOffsetSeconds()
{
   if((bool)MQLInfoInteger(MQL_TESTER)) return InpTesterServerUTCOffsetHours*3600;
   if(!InpUseAutomaticLiveServerOffset) return InpManualLiveServerUTCOffsetHours*3600;
   datetime server=TimeTradeServer();
   if(server<=0) server=TimeCurrent();
   datetime utc=TimeGMT();
   if(utc<=0) return InpManualLiveServerUTCOffsetHours*3600;
   return (int)MathRound((double)(server-utc)/1800.0)*1800;
}

datetime ServerToNewYork(const datetime server_time)
{
   datetime utc=server_time-ServerUTCOffsetSeconds();
   return utc+NewYorkUTCOffsetHours(utc)*3600;
}

datetime NewYorkToServer(const MqlDateTime &source)
{
   MqlDateTime local=source;
   datetime value=StructToTime(local);
   int offset=(NewYorkDateUsesDST(source) ? -4 : -5);
   return value-offset*3600+ServerUTCOffsetSeconds();
}

datetime NYTime(const MqlDateTime &date,const int hour,const int minute)
{
   MqlDateTime value=date;
   value.hour=hour; value.min=minute; value.sec=0;
   return NewYorkToServer(value);
}

int DateKey(const MqlDateTime &value)
{
   return value.year*10000+value.mon*100+value.day;
}

double NormalizePrice(const double raw)
{
   double tick=SymbolInfoDouble(_Symbol,SYMBOL_TRADE_TICK_SIZE);
   if(tick<=0.0) tick=SymbolInfoDouble(_Symbol,SYMBOL_POINT);
   if(tick<=0.0) return raw;
   return NormalizeDouble(MathRound(raw/tick)*tick,(int)SymbolInfoInteger(_Symbol,SYMBOL_DIGITS));
}

double NormalizeVolume(const double raw)
{
   double minimum=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MIN);
   double maximum=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MAX);
   double step=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_STEP);
   if(minimum<=0.0 || maximum<=0.0 || step<=0.0 || raw<minimum) return 0.0;
   double lots=MathFloor((MathMin(raw,maximum)+1e-12)/step)*step;
   return NormalizeDouble(lots,8);
}

double LotsForRisk(const ENUM_ORDER_TYPE order_type,const double entry,const double stop)
{
   double result=0.0;
   if(!OrderCalcProfit(order_type,_Symbol,1.0,entry,stop,result) || result==0.0) return 0.0;
   double risk_cash=AccountInfoDouble(ACCOUNT_EQUITY)*InpRiskPercent/100.0;
   return NormalizeVolume(risk_cash/MathAbs(result));
}

bool SelectOurPosition(ulong &ticket)
{
   for(int index=PositionsTotal()-1;index>=0;index--)
   {
      ulong candidate=PositionGetTicket(index);
      if(candidate==0) continue;
      if(PositionGetString(POSITION_SYMBOL)==_Symbol && PositionGetInteger(POSITION_MAGIC)==InpMagic)
      {
         ticket=candidate;
         return true;
      }
   }
   return false;
}

bool TradedOnDate(const MqlDateTime &date)
{
   MqlDateTime start=date;
   start.hour=0; start.min=0; start.sec=0;
   MqlDateTime finish=start;
   finish.hour=23; finish.min=59; finish.sec=59;
   if(!HistorySelect(NewYorkToServer(start),NewYorkToServer(finish))) return false;
   for(int index=HistoryDealsTotal()-1;index>=0;index--)
   {
      ulong deal=HistoryDealGetTicket(index);
      if(deal==0) continue;
      if(HistoryDealGetString(deal,DEAL_SYMBOL)==_Symbol &&
         HistoryDealGetInteger(deal,DEAL_MAGIC)==InpMagic &&
         HistoryDealGetInteger(deal,DEAL_ENTRY)==DEAL_ENTRY_IN)
         return true;
   }
   return false;
}

string ObjectName(const string suffix)
{
   return StringFormat("FABIO_ORB_%I64d_%s_%s",InpMagic,_Symbol,suffix);
}

void DeleteRangeObjects()
{
   ObjectDelete(0,ObjectName("HIGH"));
   ObjectDelete(0,ObjectName("LOW"));
}

void DrawRangeLine(const string suffix,const double price,const color line_color)
{
   if((bool)MQLInfoInteger(MQL_TESTER) || !InpShowRange || price<=0.0) return;
   string name=ObjectName(suffix);
   if(ObjectFind(0,name)<0) ObjectCreate(0,name,OBJ_HLINE,0,0,price);
   ObjectSetDouble(0,name,OBJPROP_PRICE,price);
   ObjectSetInteger(0,name,OBJPROP_COLOR,line_color);
   ObjectSetInteger(0,name,OBJPROP_STYLE,STYLE_DASH);
   ObjectSetInteger(0,name,OBJPROP_SELECTABLE,false);
}

bool BuildOpeningRange(const MqlDateTime &date)
{
   datetime from=NYTime(date,InpCashOpenHour,InpCashOpenMinute);
   datetime to=from+InpOpeningRangeMinutes*60-1;
   MqlRates rates[];
   int copied=CopyRates(_Symbol,InpSignalTimeframe,from,to,rates);
   int expected=InpOpeningRangeMinutes*60/PeriodSeconds(InpSignalTimeframe);
   if(copied<expected) return false;
   g_range_high=-DBL_MAX;
   g_range_low=DBL_MAX;
   for(int index=0;index<copied;index++)
   {
      g_range_high=MathMax(g_range_high,rates[index].high);
      g_range_low=MathMin(g_range_low,rates[index].low);
   }
   g_range_ready=(g_range_high>g_range_low);
   if(g_range_ready)
   {
      DrawRangeLine("HIGH",g_range_high,clrMediumSeaGreen);
      DrawRangeLine("LOW",g_range_low,clrTomato);
   }
   return g_range_ready;
}

bool SpreadOK(const double risk)
{
   MqlTick tick;
   if(!SymbolInfoTick(_Symbol,tick) || risk<=0.0) return false;
   return (tick.ask-tick.bid)/risk*100.0<=InpMaximumSpreadRiskPercent;
}

bool EnterTrade(const int direction)
{
   if(g_traded_today) return false;
   ulong existing=0;
   if(SelectOurPosition(existing)) return false;
   MqlTick tick;
   if(!SymbolInfoTick(_Symbol,tick)) return false;
   double point=SymbolInfoDouble(_Symbol,SYMBOL_POINT);
   double entry=(direction>0 ? tick.ask : tick.bid);
   double stop=(direction>0 ? g_range_low-InpStopBufferPoints*point : g_range_high+InpStopBufferPoints*point);
   stop=NormalizePrice(stop);
   double risk=(direction>0 ? entry-stop : stop-entry);
   if(risk<=0.0 || !SpreadOK(risk)) return false;
   double minimum=(double)SymbolInfoInteger(_Symbol,SYMBOL_TRADE_STOPS_LEVEL)*point;
   if(risk<minimum) return false;
   double target=NormalizePrice(direction>0 ? entry+InpRewardRisk*risk : entry-InpRewardRisk*risk);
   if(MathAbs(target-entry)<minimum) return false;
   ENUM_ORDER_TYPE type=(direction>0 ? ORDER_TYPE_BUY : ORDER_TYPE_SELL);
   double lots=LotsForRisk(type,entry,stop);
   if(lots<=0.0)
   {
      Print("Fabio ORB skipped: risk-sized volume is below the broker minimum or contract data is unavailable.");
      return false;
   }
   trade.SetExpertMagicNumber((ulong)InpMagic);
   trade.SetTypeFillingBySymbol(_Symbol);
   trade.SetDeviationInPoints(InpMaximumDeviationPoints);
   bool sent=(direction>0 ? trade.Buy(lots,_Symbol,0.0,stop,target,"Fabio ORB long")
                          : trade.Sell(lots,_Symbol,0.0,stop,target,"Fabio ORB short"));
   if(!sent)
   {
      Print("Fabio ORB entry failed: ",trade.ResultRetcode()," ",trade.ResultRetcodeDescription());
      return false;
   }
   g_traded_today=true;
   return true;
}

void EvaluateClosedBar(const MqlDateTime &date)
{
   MqlRates closed[];
   ArraySetAsSeries(closed,true);
   if(CopyRates(_Symbol,InpSignalTimeframe,1,1,closed)!=1) return;
   MqlRates bar=closed[0];
   datetime open=NYTime(date,InpCashOpenHour,InpCashOpenMinute);
   datetime range_end=open+InpOpeningRangeMinutes*60;
   datetime cutoff=open+InpEntryCutoffMinutesAfterOpen*60;
   if(bar.time<range_end || bar.time>=cutoff) return;
   double point=SymbolInfoDouble(_Symbol,SYMBOL_POINT);
   double buffer=InpBreakoutBufferPoints*point;
   int direction=0;
   if(bar.close>g_range_high+buffer) direction=1;
   else if(bar.close<g_range_low-buffer) direction=-1;
   if(direction==0) return;
   if(InpTradeDirection==1 && direction<0) return;
   if(InpTradeDirection==2 && direction>0) return;
   if(InpRequireDirectionalBreakoutCandle)
   {
      if(direction>0 && bar.close<=bar.open) return;
      if(direction<0 && bar.close>=bar.open) return;
   }
   EnterTrade(direction);
}

void ManagePosition(const MqlDateTime &now_ny)
{
   ulong ticket=0;
   if(!SelectOurPosition(ticket)) return;
   int now_minutes=now_ny.hour*60+now_ny.min;
   if(now_minutes<InpFlatHour*60+InpFlatMinute) return;
   trade.SetExpertMagicNumber((ulong)InpMagic);
   trade.SetTypeFillingBySymbol(_Symbol);
   trade.SetDeviationInPoints(InpMaximumDeviationPoints);
   if(!trade.PositionClose(ticket)) Print("Fabio ORB session close failed: ",trade.ResultRetcodeDescription());
}

void ResetSession(const MqlDateTime &date)
{
   g_session_key=DateKey(date);
   g_range_ready=false;
   g_traded_today=(InpOneTradePerDay ? TradedOnDate(date) : false);
   g_range_high=0.0;
   g_range_low=0.0;
   DeleteRangeObjects();
}

void ProcessStrategy()
{
   datetime now_server=TimeCurrent();
   if(now_server<=0) return;
   MqlDateTime now_ny;
   TimeToStruct(ServerToNewYork(now_server),now_ny);
   if(DateKey(now_ny)!=g_session_key) ResetSession(now_ny);
   ManagePosition(now_ny);
   datetime current=iTime(_Symbol,InpSignalTimeframe,0);
   if(current<=0 || current==g_last_bar) return;
   g_last_bar=current;
   if(g_traded_today || (InpWeekdaysOnly && (now_ny.day_of_week==0 || now_ny.day_of_week==6))) return;
   datetime open=NYTime(now_ny,InpCashOpenHour,InpCashOpenMinute);
   datetime range_end=open+InpOpeningRangeMinutes*60;
   datetime cutoff=open+InpEntryCutoffMinutesAfterOpen*60;
   if(now_server<range_end || now_server>=cutoff+PeriodSeconds(InpSignalTimeframe)) return;
   if(!g_range_ready && !BuildOpeningRange(now_ny)) return;
   EvaluateClosedBar(now_ny);
}

int OnInit()
{
   int signal_seconds=PeriodSeconds(InpSignalTimeframe);
   if(signal_seconds<=0 || InpOpeningRangeMinutes<5 || (InpOpeningRangeMinutes*60)%signal_seconds!=0 ||
      InpEntryCutoffMinutesAfterOpen<=InpOpeningRangeMinutes || InpEntryCutoffMinutesAfterOpen>390 ||
      InpTradeDirection<0 || InpTradeDirection>2 || InpRiskPercent<=0.0 || InpRiskPercent>5.0 ||
      InpRewardRisk<=0.0 || InpMaximumSpreadRiskPercent<=0.0 || InpMagic<=0)
      return INIT_PARAMETERS_INCORRECT;
   g_last_bar=iTime(_Symbol,InpSignalTimeframe,0);
   EventSetTimer(10);
   return INIT_SUCCEEDED;
}

void OnDeinit(const int reason)
{
   EventKillTimer();
   DeleteRangeObjects();
}

void OnTick(){ ProcessStrategy(); }
void OnTimer(){ ProcessStrategy(); }

double OnTester()
{
   double trades=TesterStatistics(STAT_TRADES);
   double profit=TesterStatistics(STAT_PROFIT);
   double pf=TesterStatistics(STAT_PROFIT_FACTOR);
   double dd=TesterStatistics(STAT_EQUITY_DDREL_PERCENT);
   if(trades<80.0 || profit<=0.0 || pf<1.02 || dd<=0.0) return -1000.0+trades;
   return (profit/dd)*MathMin(2.0,MathSqrt(trades/200.0))*MathMin(pf,3.0);
}
