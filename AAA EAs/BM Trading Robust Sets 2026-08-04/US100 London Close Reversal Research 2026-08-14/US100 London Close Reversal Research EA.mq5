#property copyright "AAA transparent research EA"
#property version   "1.00"
#property strict

#include <Trade/Trade.mqh>

input group "Research safety gate"
input bool   InpEnableTrading=false;

input group "London-close reversal rule"
input int    InpLondonCloseHour=17;
input int    InpLondonCloseMinute=0;
input int    InpCandleLookback=1;
input double InpMinimumNetBodyPrice=25.0;
input double InpStopDistancePrice=50.0;
input double InpRewardRisk=2.0;
input int    InpMaximumHoldMinutes=90;
input bool   InpBreakEvenAtOneR=true;
input double InpRiskPercent=1.0;

input group "Execution"
input long   InpMagic=814170050;
input double InpMaximumSpreadPrice=0.0;
input int    InpMaxDeviationPoints=100;

input group "Broker clock"
input bool   InpUseAutomaticLiveServerOffset=true;
input int    InpManualLiveServerUTCOffsetHours=0;
input bool   InpTesterUsesEETEEST=true;
input int    InpTesterManualUTCOffsetHours=0;

CTrade g_trade;
datetime g_last_m1_bar=0;
int g_last_attempt_date=0;

int DaysInMonth(const int year,const int month)
{
   if(month==2) return ((year%4==0 && year%100!=0) || year%400==0 ? 29 : 28);
   if(month==4 || month==6 || month==9 || month==11) return 30;
   return 31;
}

int LastSunday(const int year,const int month)
{
   MqlDateTime p={0};
   p.year=year; p.mon=month; p.day=DaysInMonth(year,month); p.hour=12;
   datetime stamp=StructToTime(p);
   TimeToStruct(stamp,p);
   return DaysInMonth(year,month)-p.day_of_week;
}

int TesterEETOffsetSeconds(const datetime server_time)
{
   MqlDateTime p;
   TimeToStruct(server_time,p);
   bool summer=false;
   if(p.mon>3 && p.mon<10) summer=true;
   else if(p.mon==3)
   {
      int last=LastSunday(p.year,3);
      summer=(p.day>last || (p.day==last && p.hour>=3));
   }
   else if(p.mon==10)
   {
      int last=LastSunday(p.year,10);
      summer=(p.day<last || (p.day==last && p.hour<4));
   }
   return (summer ? 3 : 2)*3600;
}

int ServerOffsetSeconds(const datetime server_time)
{
   if((bool)MQLInfoInteger(MQL_TESTER))
      return (InpTesterUsesEETEEST ? TesterEETOffsetSeconds(server_time) : InpTesterManualUTCOffsetHours*3600);
   if(!InpUseAutomaticLiveServerOffset) return InpManualLiveServerUTCOffsetHours*3600;
   datetime server=TimeTradeServer();
   if(server<=0) server=TimeCurrent();
   datetime utc=TimeGMT();
   if(utc<=0) return InpManualLiveServerUTCOffsetHours*3600;
   return (int)MathRound((double)(server-utc)/1800.0)*1800;
}

datetime ServerToUTC(const datetime server_time)
{
   return server_time-ServerOffsetSeconds(server_time);
}

bool LondonDSTAtUTC(const datetime utc)
{
   MqlDateTime p;
   TimeToStruct(utc,p);
   MqlDateTime start={0},finish={0};
   start.year=p.year; start.mon=3; start.day=LastSunday(p.year,3); start.hour=1;
   finish.year=p.year; finish.mon=10; finish.day=LastSunday(p.year,10); finish.hour=1;
   return utc>=StructToTime(start) && utc<StructToTime(finish);
}

datetime ServerToLondon(const datetime server_time)
{
   datetime utc=ServerToUTC(server_time);
   return utc+(LondonDSTAtUTC(utc) ? 3600 : 0);
}

int DateKey(const MqlDateTime &p)
{
   return p.year*10000+p.mon*100+p.day;
}

double NormalizePrice(const double value)
{
   double tick_size=SymbolInfoDouble(_Symbol,SYMBOL_TRADE_TICK_SIZE);
   if(tick_size<=0.0) tick_size=SymbolInfoDouble(_Symbol,SYMBOL_POINT);
   int digits=(int)SymbolInfoInteger(_Symbol,SYMBOL_DIGITS);
   return NormalizeDouble(MathRound(value/tick_size)*tick_size,digits);
}

double NormalizeVolume(const double raw)
{
   double minimum=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MIN);
   double maximum=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MAX);
   double step=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_STEP);
   if(minimum<=0.0 || step<=0.0 || raw<minimum) return 0.0;
   return NormalizeDouble(MathFloor((MathMin(raw,maximum)+1e-12)/step)*step,8);
}

double LotsForRisk(const ENUM_ORDER_TYPE type,const double entry,const double stop)
{
   double one_lot_result=0.0;
   if(!OrderCalcProfit(type,_Symbol,1.0,entry,stop,one_lot_result) || MathAbs(one_lot_result)<=0.0) return 0.0;
   double risk_cash=AccountInfoDouble(ACCOUNT_EQUITY)*InpRiskPercent/100.0;
   return NormalizeVolume(risk_cash/MathAbs(one_lot_result));
}

bool SelectOurPosition(ulong &ticket)
{
   for(int i=PositionsTotal()-1;i>=0;i--)
   {
      ulong candidate=PositionGetTicket(i);
      if(candidate>0 && PositionGetString(POSITION_SYMBOL)==_Symbol && PositionGetInteger(POSITION_MAGIC)==InpMagic)
      {
         ticket=candidate;
         return true;
      }
   }
   return false;
}

bool NewM1Bar()
{
   datetime current=iTime(_Symbol,PERIOD_M1,0);
   if(current<=0 || current==g_last_m1_bar) return false;
   g_last_m1_bar=current;
   return true;
}

void ManagePosition()
{
   ulong ticket=0;
   if(!SelectOurPosition(ticket) || !PositionSelectByTicket(ticket)) return;

   datetime opened=(datetime)PositionGetInteger(POSITION_TIME);
   if(InpMaximumHoldMinutes>0 && TimeCurrent()-opened>=InpMaximumHoldMinutes*60)
   {
      if(!g_trade.PositionClose(ticket,(ulong)InpMaxDeviationPoints))
         Print("London reversal time exit failed: ",g_trade.ResultRetcode()," ",g_trade.ResultRetcodeDescription());
      return;
   }

   if(!InpBreakEvenAtOneR) return;
   double open=PositionGetDouble(POSITION_PRICE_OPEN);
   double stop=PositionGetDouble(POSITION_SL);
   double target=PositionGetDouble(POSITION_TP);
   long type=PositionGetInteger(POSITION_TYPE);
   double initial_risk=MathAbs(target-open)/MathMax(InpRewardRisk,0.01);
   if(initial_risk<=0.0) return;

   MqlTick tick;
   if(!SymbolInfoTick(_Symbol,tick)) return;
   bool reached=(type==POSITION_TYPE_BUY ? tick.bid-open>=initial_risk : open-tick.ask>=initial_risk);
   bool needs_move=(type==POSITION_TYPE_BUY ? stop<open : stop>open);
   if(reached && needs_move)
   {
      if(!g_trade.PositionModify(ticket,NormalizePrice(open),target))
         Print("London reversal break-even failed: ",g_trade.ResultRetcode()," ",g_trade.ResultRetcodeDescription());
   }
}

double ClosedCandleNetBody()
{
   MqlRates bars[];
   ArraySetAsSeries(bars,true);
   int copied=CopyRates(_Symbol,PERIOD_M15,1,InpCandleLookback,bars);
   if(copied!=InpCandleLookback) return EMPTY_VALUE;
   double body=0.0;
   for(int i=0;i<copied;i++) body+=bars[i].close-bars[i].open;
   return body;
}

void EvaluateEntry()
{
   if(!InpEnableTrading) return;
   ulong ticket=0;
   if(SelectOurPosition(ticket)) return;

   MqlDateTime london;
   TimeToStruct(ServerToLondon(TimeCurrent()),london);
   if(london.day_of_week<1 || london.day_of_week>5) return;
   if(london.hour!=InpLondonCloseHour || london.min!=InpLondonCloseMinute) return;

   int date_key=DateKey(london);
   if(g_last_attempt_date==date_key) return;
   g_last_attempt_date=date_key;

   double body=ClosedCandleNetBody();
   if(body==EMPTY_VALUE || MathAbs(body)<InpMinimumNetBodyPrice) return;
   int direction=(body>0.0 ? -1 : 1);

   MqlTick tick;
   if(!SymbolInfoTick(_Symbol,tick)) return;
   double spread=tick.ask-tick.bid;
   if(InpMaximumSpreadPrice>0.0 && spread>InpMaximumSpreadPrice)
   {
      Print("London reversal skipped: spread ",DoubleToString(spread,2)," exceeds limit ",DoubleToString(InpMaximumSpreadPrice,2));
      return;
   }

   double entry=(direction>0 ? tick.ask : tick.bid);
   double stop=NormalizePrice(entry-direction*InpStopDistancePrice);
   double target=NormalizePrice(entry+direction*InpStopDistancePrice*InpRewardRisk);
   ENUM_ORDER_TYPE order_type=(direction>0 ? ORDER_TYPE_BUY : ORDER_TYPE_SELL);
   double lots=LotsForRisk(order_type,entry,stop);
   if(lots<=0.0)
   {
      Print("London reversal skipped: calculated volume is below broker minimum or contract data is unavailable.");
      return;
   }

   g_trade.SetExpertMagicNumber((ulong)InpMagic);
   g_trade.SetTypeFillingBySymbol(_Symbol);
   g_trade.SetDeviationInPoints(InpMaxDeviationPoints);
   bool sent=(direction>0
      ? g_trade.Buy(lots,_Symbol,0.0,stop,target,"US100 London close reversal BUY")
      : g_trade.Sell(lots,_Symbol,0.0,stop,target,"US100 London close reversal SELL"));
   if(!sent)
      Print("London reversal entry failed: ",g_trade.ResultRetcode()," ",g_trade.ResultRetcodeDescription());
}

int OnInit()
{
   if(InpLondonCloseHour<0 || InpLondonCloseHour>23 || InpLondonCloseMinute<0 || InpLondonCloseMinute>59 ||
      InpCandleLookback<1 || InpMinimumNetBodyPrice<0.0 || InpStopDistancePrice<=0.0 || InpRewardRisk<=0.0 ||
      InpMaximumHoldMinutes<1 || InpRiskPercent<=0.0 || InpRiskPercent>5.0 || InpMagic<=0)
      return INIT_PARAMETERS_INCORRECT;

   g_trade.SetExpertMagicNumber((ulong)InpMagic);
   if(!InpEnableTrading)
      Print("RESEARCH GATE OFF: the 2026 confirmation lost 9.30% with 17.77% maximum drawdown. Not approved for live deployment.");
   return INIT_SUCCEEDED;
}

void OnTick()
{
   if(!InpEnableTrading) return;
   ManagePosition();
   if(NewM1Bar()) EvaluateEntry();
}
