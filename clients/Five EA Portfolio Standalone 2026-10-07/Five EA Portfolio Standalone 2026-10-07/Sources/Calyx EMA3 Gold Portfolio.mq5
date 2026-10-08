#property strict
#property version "3.00"
#include <Trade/Trade.mqh>
#include "CalyxAdaptivePortfolio.mqh"
#include "RiskSupport.mqh"



#define AAA_STRATEGY_ID 1
#define AAA_STRATEGY_NAME "AAA Final EMA3"
#define AAA_DEFAULT_ENABLED true
#define AAA_DEFAULT_RISK 1.0
#define AAA_DEFAULT_RR 1.7
#define AAA_DEFAULT_MAGIC 3082026
input bool InpAdaptivePortfolioControls=false;

#define AAA_FINAL_STRATEGY_ENGINE_MQH

#define AAA_FINAL_COMMON_MQH

#define DYNAMIC_TRAILING_SESSION_FILTER_MQH

enum ENUM_DTS_SESSION_MODE
  {
   DTS_SESSION_ALL=0,
   DTS_SESSION_ASIA=1,
   DTS_SESSION_LONDON=2,
   DTS_SESSION_NEW_YORK=3,
   DTS_SESSION_LONDON_NEW_YORK_OVERLAP=4
  };
input bool                  InpUseDynamicTrailingSL=false;
input double                InpDynamicTriggerFraction=0.50;
input double                InpDynamicLockFraction=0.20;
input ENUM_DTS_SESSION_MODE InpResearchSession=DTS_SESSION_ALL;
input int                   InpResearchBrokerUtcOffsetMinutes=180;

struct DTS_TRACKED_POSITION
  {
   ulong    identifier;
   datetime opened;
   double   target_distance;
  };

DTS_TRACKED_POSITION g_dts_positions[];
datetime g_dts_last_m15_bar=0;

bool DTS_InputsValid()
  {
   return InpDynamicTriggerFraction>0.0 && InpDynamicTriggerFraction<=1.0 &&
          InpDynamicLockFraction>=0.0 && InpDynamicLockFraction<InpDynamicTriggerFraction &&
          InpResearchBrokerUtcOffsetMinutes>=-840 && InpResearchBrokerUtcOffsetMinutes<=840;
  }

bool DTS_MinuteInside(const int minute_of_day,const int start_minute,const int end_minute)
  {
   if(start_minute==end_minute) return true;
   if(start_minute<end_minute) return minute_of_day>=start_minute && minute_of_day<end_minute;
   return minute_of_day>=start_minute || minute_of_day<end_minute;
  }

bool DTS_EntrySessionAllowed()
  {
   if(InpResearchSession==DTS_SESSION_ALL) return true;
   datetime utc=TimeCurrent()-InpResearchBrokerUtcOffsetMinutes*60;
   MqlDateTime now; TimeToStruct(utc,now);
   int minute_of_day=now.hour*60+now.min;
   if(InpResearchSession==DTS_SESSION_ASIA)
      return DTS_MinuteInside(minute_of_day,0,8*60);
   if(InpResearchSession==DTS_SESSION_LONDON)
      return DTS_MinuteInside(minute_of_day,7*60,12*60);
   if(InpResearchSession==DTS_SESSION_NEW_YORK)
      return DTS_MinuteInside(minute_of_day,13*60,21*60);
   if(InpResearchSession==DTS_SESSION_LONDON_NEW_YORK_OVERLAP)
      return DTS_MinuteInside(minute_of_day,13*60,16*60);
   return true;
  }

int DTS_FindTracked(const ulong identifier)
  {
   for(int i=0;i<ArraySize(g_dts_positions);i++)
      if(g_dts_positions[i].identifier==identifier) return i;
   return -1;
  }

void DTS_ObservePositions(const long magic)
  {
   for(int i=PositionsTotal()-1;i>=0;i--)
     {
      ulong ticket=PositionGetTicket(i);
      if(ticket==0 || !PositionSelectByTicket(ticket)) continue;
      if(PositionGetString(POSITION_SYMBOL)!=_Symbol || PositionGetInteger(POSITION_MAGIC)!=magic) continue;
      ulong identifier=(ulong)PositionGetInteger(POSITION_IDENTIFIER);
      if(DTS_FindTracked(identifier)>=0) continue;
      ENUM_POSITION_TYPE type=(ENUM_POSITION_TYPE)PositionGetInteger(POSITION_TYPE);
      double entry=PositionGetDouble(POSITION_PRICE_OPEN);
      double target=PositionGetDouble(POSITION_TP);
      double stop=PositionGetDouble(POSITION_SL);
      double distance=0.0;
      if(type==POSITION_TYPE_BUY)
        {
         if(target>entry) distance=target-entry;
         else if(stop>0.0 && stop<entry) distance=entry-stop;
        }
      else
        {
         if(target>0.0 && target<entry) distance=entry-target;
         else if(stop>entry) distance=stop-entry;
        }
      if(distance<=SymbolInfoDouble(_Symbol,SYMBOL_POINT)) continue;
      int size=ArraySize(g_dts_positions);
      ArrayResize(g_dts_positions,size+1);
      g_dts_positions[size].identifier=identifier;
      g_dts_positions[size].opened=(datetime)PositionGetInteger(POSITION_TIME);
      g_dts_positions[size].target_distance=distance;
     }
  }

bool DTS_ModifyStop(const ulong ticket,const double stop,const double target)
  {
   MqlTradeRequest request={};
   MqlTradeResult result={};
   request.action=TRADE_ACTION_SLTP;
   request.position=ticket;
   request.symbol=_Symbol;
   request.sl=NormalizeDouble(stop,(int)SymbolInfoInteger(_Symbol,SYMBOL_DIGITS));
   request.tp=target;
   if(!OrderSend(request,result)) return false;
   return result.retcode==TRADE_RETCODE_DONE || result.retcode==TRADE_RETCODE_DONE_PARTIAL ||
          result.retcode==TRADE_RETCODE_PLACED || result.retcode==TRADE_RETCODE_NO_CHANGES;
  }

void DTS_ManageDynamicTrailing(const long magic)
  {
   if(!InpUseDynamicTrailingSL) return;
   DTS_ObservePositions(magic);
   datetime current_m15=iTime(_Symbol,PERIOD_M15,0);
   if(current_m15<=0) return;
   if(g_dts_last_m15_bar==0)
     {
      g_dts_last_m15_bar=current_m15;
      return;
     }
   if(current_m15==g_dts_last_m15_bar) return;
   g_dts_last_m15_bar=current_m15;
   double closed_price=iClose(_Symbol,PERIOD_M15,1);
   if(closed_price<=0.0) return;
   MqlTick tick;
   if(!SymbolInfoTick(_Symbol,tick)) return;
   double point=SymbolInfoDouble(_Symbol,SYMBOL_POINT);
   double broker_gap=MathMax(point,SymbolInfoInteger(_Symbol,SYMBOL_TRADE_STOPS_LEVEL)*point);

   for(int i=PositionsTotal()-1;i>=0;i--)
     {
      ulong ticket=PositionGetTicket(i);
      if(ticket==0 || !PositionSelectByTicket(ticket)) continue;
      if(PositionGetString(POSITION_SYMBOL)!=_Symbol || PositionGetInteger(POSITION_MAGIC)!=magic) continue;
      ulong identifier=(ulong)PositionGetInteger(POSITION_IDENTIFIER);
      int tracked=DTS_FindTracked(identifier);
      if(tracked<0 || g_dts_positions[tracked].target_distance<=point) continue;
      ENUM_POSITION_TYPE type=(ENUM_POSITION_TYPE)PositionGetInteger(POSITION_TYPE);
      double entry=PositionGetDouble(POSITION_PRICE_OPEN);
      double current_stop=PositionGetDouble(POSITION_SL);
      double target=PositionGetDouble(POSITION_TP);
      double distance=g_dts_positions[tracked].target_distance;
      double desired=0.0;
      if(type==POSITION_TYPE_BUY)
        {
         if(closed_price<entry+InpDynamicTriggerFraction*distance) continue;
         desired=entry+InpDynamicLockFraction*distance;
         desired=MathMin(desired,tick.bid-broker_gap);
         if(desired<=entry || (current_stop>0.0 && desired<=current_stop+point)) continue;
        }
      else
        {
         if(closed_price>entry-InpDynamicTriggerFraction*distance) continue;
         desired=entry-InpDynamicLockFraction*distance;
         desired=MathMax(desired,tick.ask+broker_gap);
         if(desired>=entry || (current_stop>0.0 && desired>=current_stop-point)) continue;
        }
      if(!DTS_ModifyStop(ticket,desired,target))
         Print("Dynamic trailing SL modification failed for position ",ticket);
     }
  }


CTrade AAA_Trade;
int AAA_TesterServerOffsetMode=1; // 1 = EET/EEST broker clock, used only in the Strategy Tester

double AAA_Price(const string symbol,const double value)
{
   return NormalizeDouble(value,(int)SymbolInfoInteger(symbol,SYMBOL_DIGITS));
}

double AAA_Volume(const string symbol,const double raw)
{
   double minimum=SymbolInfoDouble(symbol,SYMBOL_VOLUME_MIN);
   double maximum=SymbolInfoDouble(symbol,SYMBOL_VOLUME_MAX);
   double step=SymbolInfoDouble(symbol,SYMBOL_VOLUME_STEP);
   if(minimum<=0.0 || maximum<=0.0 || step<=0.0 || raw<=0.0) return 0.0;
   double lots=MathCeil((MathMin(raw,maximum)-1e-12)/step)*step;
   lots=MathMax(minimum,MathMin(maximum,lots));
   if(lots>raw+1e-12)
      PrintFormat("Risk sizing rounded %.8f lots up to broker-valid %.8f lots; actual risk exceeds the selected target.",raw,lots);
   return NormalizeDouble(lots,8);
}

double AAA_LotsForRisk(const string symbol,const ENUM_ORDER_TYPE type,const double entry,const double stop,const double risk_percent)
{
   if(risk_percent<=0.0 || entry<=0.0 || stop<=0.0 || entry==stop) return 0.0;
   double one_lot_result=0.0;
   if(!OrderCalcProfit(type,symbol,1.0,entry,stop,one_lot_result)) return 0.0;
   double loss=MathAbs(one_lot_result);
   if(loss<=0.0) return 0.0;
   const double adaptive=CalyxAdaptiveRiskMultiplier(InpAdaptivePortfolioControls,InpMagic);
   if(adaptive<=0.0) return 0.0;
   double risk_cash=FP_RiskBudget(risk_percent,adaptive);
   return AAA_Volume(symbol,risk_cash/loss);
}

bool AAA_HasPosition(const string symbol,const long magic)
{
   for(int i=PositionsTotal()-1;i>=0;i--)
   {
      ulong ticket=PositionGetTicket(i);
      if(ticket==0) continue;
      if(PositionGetString(POSITION_SYMBOL)==symbol && PositionGetInteger(POSITION_MAGIC)==magic) return true;
   }
   return false;
}

bool AAA_HasOrder(const string symbol,const long magic)
{
   for(int i=OrdersTotal()-1;i>=0;i--)
   {
      ulong ticket=OrderGetTicket(i);
      if(ticket==0) continue;
      if(OrderGetString(ORDER_SYMBOL)==symbol && OrderGetInteger(ORDER_MAGIC)==magic) return true;
   }
   return false;
}

bool AAA_HasExposure(const string symbol,const long magic)
{
   return AAA_HasPosition(symbol,magic) || AAA_HasOrder(symbol,magic);
}

void AAA_DeleteOrders(const string symbol,const long magic)
{
   AAA_Trade.SetExpertMagicNumber((ulong)magic);
   for(int i=OrdersTotal()-1;i>=0;i--)
   {
      ulong ticket=OrderGetTicket(i);
      if(ticket==0) continue;
      if(OrderGetString(ORDER_SYMBOL)==symbol && OrderGetInteger(ORDER_MAGIC)==magic)
         AAA_Trade.OrderDelete(ticket);
   }
}

bool AAA_NewBar(const string symbol,const ENUM_TIMEFRAMES timeframe,datetime &last_bar)
{
   datetime current=iTime(symbol,timeframe,0);
   if(current<=0 || current==last_bar) return false;
   last_bar=current;
   return true;
}

double AAA_BufferValue(const int handle,const int buffer,const int shift)
{
   if(handle==INVALID_HANDLE) return EMPTY_VALUE;
   double values[];
   ArraySetAsSeries(values,true);
   if(CopyBuffer(handle,buffer,shift,1,values)!=1) return EMPTY_VALUE;
   return values[0];
}

double AAA_ATR(const string symbol,const ENUM_TIMEFRAMES timeframe,const int period,const int shift=1)
{
   int handle=iATR(symbol,timeframe,period);
   double value=AAA_BufferValue(handle,0,shift);
   if(handle!=INVALID_HANDLE) IndicatorRelease(handle);
   return value;
}

double AAA_MA(const string symbol,const ENUM_TIMEFRAMES timeframe,const int period,const int shift,const ENUM_MA_METHOD method=MODE_EMA)
{
   int handle=iMA(symbol,timeframe,period,0,method,PRICE_CLOSE);
   double value=AAA_BufferValue(handle,0,shift);
   if(handle!=INVALID_HANDLE) IndicatorRelease(handle);
   return value;
}

double AAA_RSI(const string symbol,const ENUM_TIMEFRAMES timeframe,const int period,const int shift=1)
{
   int handle=iRSI(symbol,timeframe,period,PRICE_CLOSE);
   double value=AAA_BufferValue(handle,0,shift);
   if(handle!=INVALID_HANDLE) IndicatorRelease(handle);
   return value;
}

double AAA_ADX(const string symbol,const ENUM_TIMEFRAMES timeframe,const int period,const int shift=1)
{
   int handle=iADX(symbol,timeframe,period);
   double value=AAA_BufferValue(handle,0,shift);
   if(handle!=INVALID_HANDLE) IndicatorRelease(handle);
   return value;
}

int AAA_DaysInMonth(const int year,const int month)
{
   if(month==2) return ((year%4==0 && year%100!=0) || year%400==0 ? 29 : 28);
   if(month==4 || month==6 || month==9 || month==11) return 30;
   return 31;
}

int AAA_LastSunday(const int year,const int month)
{
   MqlDateTime p={0};
   p.year=year; p.mon=month; p.day=AAA_DaysInMonth(year,month); p.hour=12;
   datetime stamp=StructToTime(p);
   TimeToStruct(stamp,p);
   return AAA_DaysInMonth(year,month)-p.day_of_week;
}

int AAA_TesterEETOffsetSeconds(const datetime server_time)
{
   MqlDateTime p;
   TimeToStruct(server_time,p);
   bool summer=false;
   if(p.mon>3 && p.mon<10) summer=true;
   else if(p.mon==3)
   {
      int last=AAA_LastSunday(p.year,3);
      summer=(p.day>last || (p.day==last && p.hour>=3));
   }
   else if(p.mon==10)
   {
      int last=AAA_LastSunday(p.year,10);
      summer=(p.day<last || (p.day==last && p.hour<4));
   }
   return (summer ? 3 : 2)*3600;
}

int AAA_ServerOffsetSeconds()
{
   datetime server=TimeTradeServer();
   if(server<=0) server=TimeCurrent();
   // In MT5 tests TimeGMT() is simulated as server time. Rebuild the active
   // broker's EET/EEST offset so UTC and New York session rules remain testable.
   if((bool)MQLInfoInteger(MQL_TESTER) && AAA_TesterServerOffsetMode==1)
      return AAA_TesterEETOffsetSeconds(server);
   return (int)(server-TimeGMT());
}

datetime AAA_ToUTC(const datetime server_time)
{
   return server_time-AAA_ServerOffsetSeconds();
}

datetime AAA_ToServer(const datetime utc_time)
{
   return utc_time+AAA_ServerOffsetSeconds();
}

int AAA_UTCDateKey(const datetime server_time)
{
   MqlDateTime part;
   TimeToStruct(AAA_ToUTC(server_time),part);
   return part.year*10000+part.mon*100+part.day;
}

datetime AAA_UTCDateTime(const datetime server_time,const int hour,const int minute=0)
{
   MqlDateTime part;
   TimeToStruct(AAA_ToUTC(server_time),part);
   part.hour=hour;
   part.min=minute;
   part.sec=0;
   return AAA_ToServer(StructToTime(part));
}

int AAA_NewYorkOffsetHours(const datetime utc_time)
{
   MqlDateTime p;
   TimeToStruct(utc_time,p);
   // Sufficient deterministic DST approximation for trading-window selection.
   if(p.mon>3 && p.mon<11) return -4;
   if(p.mon<3 || p.mon>11) return -5;
   if(p.mon==3 && p.day>=8) return -4;
   if(p.mon==11 && p.day<8) return -4;
   return -5;
}

datetime AAA_ToNewYork(const datetime server_time)
{
   datetime utc=AAA_ToUTC(server_time);
   return utc+AAA_NewYorkOffsetHours(utc)*3600;
}

datetime AAA_NewYorkToServer(const datetime ny_time)
{
   MqlDateTime p;
   TimeToStruct(ny_time,p);
   // Resolve using the same calendar day; the DST approximation above is stable around session hours.
   datetime guessed_utc=ny_time+5*3600;
   int offset=AAA_NewYorkOffsetHours(guessed_utc);
   return AAA_ToServer(ny_time-offset*3600);
}

bool AAA_SessionRangeUTC(const string symbol,const ENUM_TIMEFRAMES timeframe,const int start_hour,const int end_hour,double &high,double &low)
{
   datetime now=TimeCurrent();
   datetime from=AAA_UTCDateTime(now,start_hour);
   datetime to=AAA_UTCDateTime(now,end_hour)-1;
   MqlRates bars[];
   int count=CopyRates(symbol,timeframe,from,to,bars);
   if(count<=0) return false;
   high=-DBL_MAX;
   low=DBL_MAX;
   for(int i=0;i<count;i++)
   {
      if(bars[i].high>high) high=bars[i].high;
      if(bars[i].low<low) low=bars[i].low;
   }
   return high>low && low<DBL_MAX;
}

bool AAA_SessionRangeNY(const string symbol,const ENUM_TIMEFRAMES timeframe,const int start_hour,const int end_hour,double &high,double &low)
{
   datetime now_ny=AAA_ToNewYork(TimeCurrent());
   MqlDateTime p;
   TimeToStruct(now_ny,p);
   p.hour=start_hour; p.min=0; p.sec=0;
   datetime from=AAA_NewYorkToServer(StructToTime(p));
   p.hour=end_hour;
   datetime to=AAA_NewYorkToServer(StructToTime(p))-1;
   MqlRates bars[];
   int count=CopyRates(symbol,timeframe,from,to,bars);
   if(count<=0) return false;
   high=-DBL_MAX; low=DBL_MAX;
   for(int i=0;i<count;i++)
   {
      if(bars[i].high>high) high=bars[i].high;
      if(bars[i].low<low) low=bars[i].low;
   }
   return high>low && low<DBL_MAX;
}

bool AAA_TradedToday(const string symbol,const long magic)
{
   datetime start=AAA_UTCDateTime(TimeCurrent(),0);
   if(!HistorySelect(start,TimeCurrent())) return false;
   for(int i=HistoryDealsTotal()-1;i>=0;i--)
   {
      ulong ticket=HistoryDealGetTicket(i);
      if(ticket==0) continue;
      if(HistoryDealGetString(ticket,DEAL_SYMBOL)==symbol && HistoryDealGetInteger(ticket,DEAL_MAGIC)==magic &&
         HistoryDealGetInteger(ticket,DEAL_ENTRY)==DEAL_ENTRY_IN) return true;
   }
   return false;
}

bool AAA_SendMarket(const string symbol,const int direction,const double stop,const double reward_risk,const double risk_percent,const long magic,const string comment)
{
   if(!DTS_EntrySessionAllowed()) return false;
   MqlTick tick;
   if(!SymbolInfoTick(symbol,tick)) return false;
   double entry=(direction>0 ? tick.ask : tick.bid);
   double sl=AAA_Price(symbol,stop);
   if((direction>0 && sl>=entry) || (direction<0 && sl<=entry)) return false;
   double tp=AAA_Price(symbol,entry+direction*MathAbs(entry-sl)*reward_risk);
   ENUM_ORDER_TYPE type=(direction>0 ? ORDER_TYPE_BUY : ORDER_TYPE_SELL);
   double lots=AAA_LotsForRisk(symbol,type,entry,sl,risk_percent);
   if(lots<=0.0)
   {
      Print(comment,": size below broker minimum or contract data unavailable");
      return false;
   }
   AAA_Trade.SetExpertMagicNumber((ulong)magic);
   AAA_Trade.SetTypeFillingBySymbol(symbol);
   AAA_Trade.SetDeviationInPoints(20);
   if(direction>0) return AAA_Trade.Buy(lots,symbol,0.0,sl,tp,comment);
   return AAA_Trade.Sell(lots,symbol,0.0,sl,tp,comment);
}

bool AAA_SendPending(const string symbol,const ENUM_ORDER_TYPE type,const double entry,const double stop,const double reward_risk,const double risk_percent,const long magic,const datetime expiry,const string comment)
{
   if(!DTS_EntrySessionAllowed()) return false;
   int direction=(type==ORDER_TYPE_BUY_STOP || type==ORDER_TYPE_BUY_LIMIT ? 1 : -1);
   double price=AAA_Price(symbol,entry);
   double sl=AAA_Price(symbol,stop);
   if((direction>0 && sl>=price) || (direction<0 && sl<=price)) return false;
   double tp=AAA_Price(symbol,price+direction*MathAbs(price-sl)*reward_risk);
   double lots=AAA_LotsForRisk(symbol,(direction>0 ? ORDER_TYPE_BUY : ORDER_TYPE_SELL),price,sl,risk_percent);
   if(lots<=0.0) return false;
   AAA_Trade.SetExpertMagicNumber((ulong)magic);
   AAA_Trade.SetTypeFillingBySymbol(symbol);
   if(type==ORDER_TYPE_BUY_STOP) return AAA_Trade.BuyStop(lots,price,symbol,sl,tp,ORDER_TIME_SPECIFIED,expiry,comment);
   if(type==ORDER_TYPE_SELL_STOP) return AAA_Trade.SellStop(lots,price,symbol,sl,tp,ORDER_TIME_SPECIFIED,expiry,comment);
   if(type==ORDER_TYPE_BUY_LIMIT) return AAA_Trade.BuyLimit(lots,price,symbol,sl,tp,ORDER_TIME_SPECIFIED,expiry,comment);
   if(type==ORDER_TYPE_SELL_LIMIT) return AAA_Trade.SellLimit(lots,price,symbol,sl,tp,ORDER_TIME_SPECIFIED,expiry,comment);
   return false;
}

void AAA_ManageOCO(const string symbol,const long magic)
{
   if(AAA_HasPosition(symbol,magic)) AAA_DeleteOrders(symbol,magic);
}

void AAA_TrailR(const string symbol,const long magic,const double start_r,const double distance_r)
{
   MqlTick tick;
   if(!SymbolInfoTick(symbol,tick)) return;
   AAA_Trade.SetExpertMagicNumber((ulong)magic);
   for(int i=PositionsTotal()-1;i>=0;i--)
   {
      ulong ticket=PositionGetTicket(i);
      if(ticket==0 || PositionGetString(POSITION_SYMBOL)!=symbol || PositionGetInteger(POSITION_MAGIC)!=magic) continue;
      long type=PositionGetInteger(POSITION_TYPE);
      double open=PositionGetDouble(POSITION_PRICE_OPEN);
      double sl=PositionGetDouble(POSITION_SL);
      double tp=PositionGetDouble(POSITION_TP);
      if(sl<=0.0 || tp<=0.0) continue;
      int direction=(type==POSITION_TYPE_BUY ? 1 : -1);
      double initial_r=MathAbs(tp-open);
      double rr=1.0;
      if(initial_r>0.0) rr=MathMax(0.1,initial_r/MathMax(MathAbs(open-sl),SymbolInfoDouble(symbol,SYMBOL_POINT)));
      initial_r=initial_r/rr;
      double price=(direction>0 ? tick.bid : tick.ask);
      if(direction*(price-open)<start_r*initial_r) continue;
      double candidate=AAA_Price(symbol,price-direction*distance_r*initial_r);
      if((direction>0 && candidate>sl && candidate<price) || (direction<0 && (sl==0.0 || candidate<sl) && candidate>price))
         AAA_Trade.PositionModify(ticket,candidate,tp);
   }
}



#define HAMA_PER_EA_SAFE_REGIME_FILTER_MQH

// This gate is compiled into each EA that includes this file. It has no
// account-wide state and cannot approve or reject another EA's trades.
input bool   InpUseMarkovRegimeFilter=false;
input int    InpMarkovReturnWindow=40;
input double InpMarkovThreshold=0.05;
input double InpMarkovSignalGate=0.05;
input int    InpMarkovMinLabels=252;
input int    InpMarkovHistoryBars=2600;

int HAMA_SafeRegimeStateAt(double &closes[],const int index)
{
   double older=closes[index+InpMarkovReturnWindow];
   if(older<=0.0) return 1;
   double rolling_return=closes[index]/older-1.0;
   if(rolling_return>InpMarkovThreshold) return 2;
   if(rolling_return<-InpMarkovThreshold) return 0;
   return 1;
}

bool HAMA_SafeRegimeAllowsDirection(const int direction)
{
   if(!InpUseMarkovRegimeFilter) return true;
   int available=Bars(_Symbol,PERIOD_D1)-1;
   int requested=MathMin(InpMarkovHistoryBars,available);
   if(requested<=InpMarkovReturnWindow+InpMarkovMinLabels) return false;

   double closes[];
   ArraySetAsSeries(closes,true);
   int copied=CopyClose(_Symbol,PERIOD_D1,1,requested,closes);
   int labels=copied-InpMarkovReturnWindow;
   if(labels<=InpMarkovMinLabels) return false;

   double counts[3][3];
   for(int row=0;row<3;row++)
      for(int col=0;col<3;col++) counts[row][col]=0.0;

   // The newest completed D1 label is used only as the forecast state. The
   // transition into it is excluded, matching the no-lookahead research.
   int oldest=labels-1;
   for(int newer=oldest-1;newer>=1;newer--)
   {
      int from=HAMA_SafeRegimeStateAt(closes,newer+1);
      int to=HAMA_SafeRegimeStateAt(closes,newer);
      counts[from][to]+=1.0;
   }

   int state=HAMA_SafeRegimeStateAt(closes,0);
   double total=counts[state][0]+counts[state][1]+counts[state][2];
   if(total<=0.0) return false;
   double signal=(counts[state][2]-counts[state][0])/total;
   return (direction>0 ? signal>InpMarkovSignalGate : signal<-InpMarkovSignalGate);
}


#define AAA_ID_EMA3             1
#define AAA_ID_ASIA             2
#define AAA_ID_DMC              3
#define AAA_ID_AMD              4
#define AAA_ID_US100_WEAKNESS    5
#define AAA_ID_NEWS_PULSE       6
#define AAA_ID_WEEKEND          7
#define AAA_ID_XAU_GRID         8
#define AAA_ID_XAU_WEAKNESS     9
#define AAA_ID_XAU_US100_PORT  10

input bool   InpEnableTrading = AAA_DEFAULT_ENABLED;
input double InpRiskPercent   = AAA_DEFAULT_RISK;
input double InpRewardRisk    = AAA_DEFAULT_RR;
input long   InpMagic         = AAA_DEFAULT_MAGIC;
input int    InpMaxSpreadPoints = 0;
input int    InpTesterServerClockMode = 1; // 1 = EET/EEST (MEX Atlantic); live trading ignores this
input int    InpPivotBars=5;
input int    InpTrendEMA=200;
input int    InpTrendSlopeBars=6;
input bool   InpUseTrailing=true;
input double InpTrailStartR=1.5;
input double InpTrailDistanceR=1.0;
input ENUM_TIMEFRAMES InpEMA3SignalTimeframe=PERIOD_H4;
input int    InpEMA3StopMode=0; // 0=pivot structure, 1=ATR, 2=signal candle, 3=fixed price distance
input int    InpEMA3ATRPeriod=14;
input double InpEMA3StopATR=1.5;
input double InpEMA3SignalBufferATR=0.10;
input double InpEMA3FixedStopPrice=22.5;
input int    InpEMA3FastEMA=20;
input int    InpEMA3MediumEMA=50;
input double InpAsiaBufferPercent=0.03;
input double InpAMDStopBufferRange=0.03;
input double InpDmCFixedStopPrice=22.5;
input bool   InpUseEconomicCalendar=true;
input int    InpNewsExpiryMinutes=15;
input double InpNewsStopPrice=9.0;
input bool   InpAllowProvisionalWeekend=false;
input int    InpGridLevels=3;
input double InpGridRiskPercent=0.5;
input double InpWeaknessATRImpulse=2.0;

datetime g_last_bar=0;
long g_last_event_id=0;

bool AAA_SpreadOK()
{
   if(InpMaxSpreadPoints<=0) return true;
   MqlTick tick;
   double point=SymbolInfoDouble(_Symbol,SYMBOL_POINT);
   return SymbolInfoTick(_Symbol,tick) && point>0.0 && (tick.ask-tick.bid)/point<=InpMaxSpreadPoints;
}

bool AAA_LoadRates(const ENUM_TIMEFRAMES timeframe,const int count,MqlRates &rates[])
{
   ArraySetAsSeries(rates,true);
   return CopyRates(_Symbol,timeframe,0,count,rates)>=count;
}

void AAA_RunEMA3()
{
   if(InpUseTrailing) AAA_TrailR(_Symbol,InpMagic,InpTrailStartR,InpTrailDistanceR);
   ENUM_TIMEFRAMES signal_timeframe=InpEMA3SignalTimeframe;
   if(!AAA_NewBar(_Symbol,signal_timeframe,g_last_bar) || !InpEnableTrading || !AAA_SpreadOK()) return;
   if(AAA_HasExposure(_Symbol,InpMagic)) return;
   MqlRates r[];
   int needed=MathMax(InpPivotBars+3,12);
   if(!AAA_LoadRates(signal_timeframe,needed,r)) return;
   double trend=AAA_MA(_Symbol,signal_timeframe,InpTrendEMA,1);
   double trend_old=AAA_MA(_Symbol,signal_timeframe,InpTrendEMA,1+InpTrendSlopeBars);
   double fast=AAA_MA(_Symbol,signal_timeframe,InpEMA3FastEMA,1);
   double medium=AAA_MA(_Symbol,signal_timeframe,InpEMA3MediumEMA,1);
   double atr=AAA_ATR(_Symbol,signal_timeframe,InpEMA3ATRPeriod,1);
   if(trend==EMPTY_VALUE || trend_old==EMPTY_VALUE || fast==EMPTY_VALUE || medium==EMPTY_VALUE || atr<=0.0) return;
   double prior_high=-DBL_MAX,prior_low=DBL_MAX;
   for(int i=2;i<2+InpPivotBars;i++) { prior_high=MathMax(prior_high,r[i].high); prior_low=MathMin(prior_low,r[i].low); }
   MqlTick tick; if(!SymbolInfoTick(_Symbol,tick)) return;
   if(r[1].close>prior_high && r[1].close>trend && fast>medium && trend>trend_old && HAMA_SafeRegimeAllowsDirection(1))
     {
      double stop=prior_low;
      if(InpEMA3StopMode==1) stop=tick.ask-InpEMA3StopATR*atr;
      else if(InpEMA3StopMode==2) stop=r[1].low-InpEMA3SignalBufferATR*atr;
      else if(InpEMA3StopMode==3) stop=tick.ask-InpEMA3FixedStopPrice;
      if(stop<tick.ask) AAA_SendMarket(_Symbol,1,stop,InpRewardRisk,InpRiskPercent,InpMagic,(InpUseMarkovRegimeFilter ? "Safe AAA EMA3" : "AAA EMA3"));
     }
   else if(r[1].close<prior_low && r[1].close<trend && fast<medium && trend<trend_old && HAMA_SafeRegimeAllowsDirection(-1))
     {
      double stop=prior_high;
      if(InpEMA3StopMode==1) stop=tick.bid+InpEMA3StopATR*atr;
      else if(InpEMA3StopMode==2) stop=r[1].high+InpEMA3SignalBufferATR*atr;
      else if(InpEMA3StopMode==3) stop=tick.bid+InpEMA3FixedStopPrice;
      if(stop>tick.bid) AAA_SendMarket(_Symbol,-1,stop,InpRewardRisk,InpRiskPercent,InpMagic,(InpUseMarkovRegimeFilter ? "Safe AAA EMA3" : "AAA EMA3"));
     }
}

void AAA_RunAsiaBreakout()
{
   if(InpUseTrailing) AAA_TrailR(_Symbol,InpMagic,2.0,0.5);
   if(!AAA_NewBar(_Symbol,PERIOD_H1,g_last_bar) || !InpEnableTrading || !AAA_SpreadOK()) return;
   if(AAA_HasExposure(_Symbol,InpMagic) || AAA_TradedToday(_Symbol,InpMagic)) return;
   MqlDateTime utc; TimeToStruct(AAA_ToUTC(TimeCurrent()),utc);
   if(utc.hour<8 || utc.hour>13) return;
   double high,low;
   if(!AAA_SessionRangeUTC(_Symbol,PERIOD_M15,0,8,high,low)) return;
   MqlRates r[]; if(!AAA_LoadRates(PERIOD_H1,3,r)) return;
   double buffer=(high-low)*InpAsiaBufferPercent;
   double midpoint=(high+low)/2.0;
   if(r[1].close>high+buffer && r[1].low<=high+buffer)
      AAA_SendMarket(_Symbol,1,midpoint,InpRewardRisk,InpRiskPercent,InpMagic,"AAA Asia confirmed retest");
   else if(r[1].close<low-buffer && r[1].high>=low-buffer)
      AAA_SendMarket(_Symbol,-1,midpoint,InpRewardRisk,InpRiskPercent,InpMagic,"AAA Asia confirmed retest");
}

void AAA_RunDmC()
{
   if(!AAA_NewBar(_Symbol,PERIOD_H1,g_last_bar) || !InpEnableTrading || !AAA_SpreadOK()) return;
   if(AAA_HasExposure(_Symbol,InpMagic) || AAA_TradedToday(_Symbol,InpMagic)) return;
   MqlRates day[],hour[];
   if(!AAA_LoadRates(PERIOD_D1,3,day) || !AAA_LoadRates(PERIOD_H1,3,hour)) return;
   double body_high=MathMax(day[1].open,day[1].close);
   double body_low=MathMin(day[1].open,day[1].close);
   MqlTick tick; if(!SymbolInfoTick(_Symbol,tick)) return;
   if(hour[1].low<=body_low && hour[1].close>body_low && hour[1].close>hour[1].open)
      AAA_SendMarket(_Symbol,1,tick.ask-InpDmCFixedStopPrice,InpRewardRisk,InpRiskPercent,InpMagic,"AAA DmC body reaction");
   else if(hour[1].high>=body_high && hour[1].close<body_high && hour[1].close<hour[1].open)
      AAA_SendMarket(_Symbol,-1,tick.bid+InpDmCFixedStopPrice,InpRewardRisk,InpRiskPercent,InpMagic,"AAA DmC body reaction");
}

void AAA_RunAMD()
{
   if(!AAA_NewBar(_Symbol,PERIOD_M15,g_last_bar) || !InpEnableTrading || !AAA_SpreadOK()) return;
   if(AAA_HasExposure(_Symbol,InpMagic) || AAA_TradedToday(_Symbol,InpMagic)) return;
   MqlDateTime utc; TimeToStruct(AAA_ToUTC(TimeCurrent()),utc);
   if(utc.hour<8 || utc.hour>11) return;
   double high,low;
   if(!AAA_SessionRangeUTC(_Symbol,PERIOD_M15,0,8,high,low)) return;
   MqlRates r[]; if(!AAA_LoadRates(PERIOD_M15,3,r)) return;
   double range=high-low;
   double sweep_min=range*0.0002;
   double stop_buffer=range*InpAMDStopBufferRange;
   if(r[1].high>high+sweep_min && r[1].close<high)
      AAA_SendMarket(_Symbol,-1,r[1].high+stop_buffer,InpRewardRisk,InpRiskPercent,InpMagic,"AAA AMD London fade");
   else if(r[1].low<low-sweep_min && r[1].close>low)
      AAA_SendMarket(_Symbol,1,r[1].low-stop_buffer,InpRewardRisk,InpRiskPercent,InpMagic,"AAA AMD London fade");
}

void AAA_RunReferencePairOCO()
{
   AAA_ManageOCO(_Symbol,InpMagic);
   if(!AAA_NewBar(_Symbol,PERIOD_M15,g_last_bar) || !InpEnableTrading || !AAA_SpreadOK()) return;
   if(AAA_HasExposure(_Symbol,InpMagic) || AAA_TradedToday(_Symbol,InpMagic)) return;
   MqlRates eval[]; if(!AAA_LoadRates(PERIOD_M15,3,eval)) return;
   datetime closed_ny=AAA_ToNewYork(eval[1].time);
   MqlDateTime ny; TimeToStruct(closed_ny,ny);
   if(ny.hour!=10 || ny.min!=0) return;
   MqlDateTime refpart=ny; refpart.hour=9; refpart.min=15; refpart.sec=0;
   datetime ref_server=AAA_NewYorkToServer(StructToTime(refpart));
   int shift=iBarShift(_Symbol,PERIOD_M15,ref_server,true);
   if(shift<1) return;
   double ref_high=iHigh(_Symbol,PERIOD_M15,shift);
   double ref_low=iLow(_Symbol,PERIOD_M15,shift);
   double london_high,london_low;
   if(!AAA_SessionRangeNY(_Symbol,PERIOD_M15,3,8,london_high,london_low)) return;
   refpart.hour=12; refpart.min=0;
   datetime expiry=AAA_NewYorkToServer(StructToTime(refpart));
   if(expiry<=TimeCurrent()) expiry=TimeCurrent()+60*60;
   double half_risk=InpRiskPercent/2.0;
   if(eval[1].close>eval[1].open && london_high>ref_high && london_high>ref_low)
   {
      AAA_SendPending(_Symbol,ORDER_TYPE_SELL_LIMIT,ref_high,london_high,InpRewardRisk,half_risk,InpMagic,expiry,"AAA weakness limit");
      AAA_SendPending(_Symbol,ORDER_TYPE_SELL_STOP,ref_low,london_high,InpRewardRisk,half_risk,InpMagic,expiry,"AAA weakness stop");
   }
   else if(eval[1].close<eval[1].open && london_low<ref_low && london_low<ref_high)
   {
      AAA_SendPending(_Symbol,ORDER_TYPE_BUY_LIMIT,ref_low,london_low,InpRewardRisk,half_risk,InpMagic,expiry,"AAA weakness limit");
      AAA_SendPending(_Symbol,ORDER_TYPE_BUY_STOP,ref_high,london_low,InpRewardRisk,half_risk,InpMagic,expiry,"AAA weakness stop");
   }
}

bool AAA_FindUpcomingPPI(datetime &event_time,long &event_id)
{
   if((bool)MQLInfoInteger(MQL_TESTER))
   {
      // Official BLS release dates inside the requested 2025-08-05 through
      // 2026-08-04 test window. Economic-calendar APIs are unavailable in MT5 tests.
      int dates[10]={20250814,20250910,20251125,20260114,20260130,20260227,20260318,20260414,20260513,20260611};
      int extra_date=20260715;
      datetime now_ny=AAA_ToNewYork(TimeCurrent());
      MqlDateTime p; TimeToStruct(now_ny,p);
      int key=p.year*10000+p.mon*100+p.day;
      bool match=(key==extra_date);
      for(int i=0;i<ArraySize(dates);i++) if(key==dates[i]) { match=true; break; }
      if(!match) return false;
      MqlDateTime release=p; release.hour=8; release.min=30; release.sec=0;
      event_time=AAA_NewYorkToServer(StructToTime(release));
      event_id=key;
      return TimeCurrent()>=event_time-InpNewsExpiryMinutes*60 && TimeCurrent()<=event_time+60;
   }
   if(!InpUseEconomicCalendar) return false;
   MqlCalendarValue values[];
   datetime now=TimeCurrent();
   int total=CalendarValueHistory(values,now-60,now+InpNewsExpiryMinutes*60,NULL,"USD");
   if(total<=0) return false;
   for(int i=0;i<total;i++)
   {
      MqlCalendarEvent event;
      if(!CalendarEventById(values[i].event_id,event)) continue;
      if(StringFind(event.name,"Producer Price")<0 && StringFind(event.name,"PPI")<0) continue;
      if(values[i].time>=now-60 && values[i].time<=now+InpNewsExpiryMinutes*60)
      {
         event_time=values[i].time;
         event_id=(long)values[i].event_id;
         return true;
      }
   }
   return false;
}

void AAA_RunNewsPulse()
{
   AAA_ManageOCO(_Symbol,InpMagic);
   if(!AAA_NewBar(_Symbol,PERIOD_M1,g_last_bar) || !InpEnableTrading || !AAA_SpreadOK()) return;
   if(AAA_HasExposure(_Symbol,InpMagic) || AAA_TradedToday(_Symbol,InpMagic)) return;
   datetime event_time=0; long event_id=0;
   if(!AAA_FindUpcomingPPI(event_time,event_id) || event_id==g_last_event_id) return;
   MqlRates r[]; if(!AAA_LoadRates(PERIOD_M1,4,r)) return;
   double entry_buffer=MathMax(SymbolInfoDouble(_Symbol,SYMBOL_POINT)*10,AAA_ATR(_Symbol,PERIOD_M1,14,1)*0.10);
   double buy_entry=r[1].high+entry_buffer;
   double sell_entry=r[1].low-entry_buffer;
   datetime expiry=event_time+InpNewsExpiryMinutes*60;
   bool a=AAA_SendPending(_Symbol,ORDER_TYPE_BUY_STOP,buy_entry,buy_entry-InpNewsStopPrice,InpRewardRisk,InpRiskPercent/2.0,InpMagic,expiry,"AAA PPI buy");
   bool b=AAA_SendPending(_Symbol,ORDER_TYPE_SELL_STOP,sell_entry,sell_entry+InpNewsStopPrice,InpRewardRisk,InpRiskPercent/2.0,InpMagic,expiry,"AAA PPI sell");
   if(a || b) g_last_event_id=event_id;
}

void AAA_RunWeekend()
{
   if(!AAA_NewBar(_Symbol,PERIOD_M15,g_last_bar) || !InpEnableTrading || !InpAllowProvisionalWeekend || !AAA_SpreadOK()) return;
   if(AAA_HasExposure(_Symbol,InpMagic) || AAA_TradedToday(_Symbol,InpMagic)) return;
   MqlDateTime utc; TimeToStruct(AAA_ToUTC(TimeCurrent()),utc);
   if(utc.day_of_week!=5 || utc.hour<19 || utc.hour>21) return;
   MqlRates r[]; if(!AAA_LoadRates(PERIOD_M15,22,r)) return;
   double momentum=r[1].close-r[21].open;
   MqlTick tick; if(!SymbolInfoTick(_Symbol,tick)) return;
   if(momentum>0.0) AAA_SendMarket(_Symbol,1,tick.ask-30.0,InpRewardRisk,InpRiskPercent,InpMagic,"AAA weekend momentum");
   else if(momentum<0.0) AAA_SendMarket(_Symbol,-1,tick.bid+30.0,InpRewardRisk,InpRiskPercent,InpMagic,"AAA weekend momentum");
}

void AAA_RunXAUGrid()
{
   AAA_ManageOCO(_Symbol,InpMagic);
   if(!AAA_NewBar(_Symbol,PERIOD_M15,g_last_bar) || !InpEnableTrading || !AAA_SpreadOK()) return;
   if(AAA_HasExposure(_Symbol,InpMagic)) return;
   MqlDateTime utc; TimeToStruct(AAA_ToUTC(TimeCurrent()),utc);
   if(utc.hour<6 || utc.hour>=19) return;
   MqlRates r[]; if(!AAA_LoadRates(PERIOD_M15,16,r)) return;
   double atr=AAA_ATR(_Symbol,PERIOD_M15,14,1);
   double rsi=AAA_RSI(_Symbol,PERIOD_M15,14,1);
   double adx=AAA_ADX(_Symbol,PERIOD_H1,14,1);
   double h1_50=AAA_MA(_Symbol,PERIOD_H1,50,1),h1_200=AAA_MA(_Symbol,PERIOD_H1,200,1);
   double h1_50_old=AAA_MA(_Symbol,PERIOD_H1,50,4);
   double h4_20=AAA_MA(_Symbol,PERIOD_H4,20,1),h4_50=AAA_MA(_Symbol,PERIOD_H4,50,1),h4_20_old=AAA_MA(_Symbol,PERIOD_H4,20,3);
   if(atr<=0.0 || adx<18.0 || adx>50.0) return;
   double prior_high=-DBL_MAX,prior_low=DBL_MAX;
   for(int i=2;i<=13;i++){ prior_high=MathMax(prior_high,r[i].high); prior_low=MathMin(prior_low,r[i].low); }
   int direction=0;
   if(r[1].close>prior_high && r[1].close>r[1].open && rsi>=55.0 && h1_50>h1_200 && h1_50>h1_50_old && h4_20>=h4_50 && h4_20>h4_20_old) direction=1;
   if(r[1].close<prior_low && r[1].close<r[1].open && rsi<=45.0 && h1_50<h1_200 && h1_50<h1_50_old && h4_20<=h4_50 && h4_20<h4_20_old) direction=-1;
   if(direction==0) return;
   double anchor=(direction>0 ? r[1].high : r[1].low);
   double offsets[3]={0.10,0.35,0.60};
   double deepest=anchor+direction*offsets[2]*atr;
   double common_stop=anchor-direction*1.0*atr;
   datetime expiry=TimeCurrent()+8*60*60;
   int levels=MathMax(1,MathMin(InpGridLevels,3));
   for(int i=0;i<levels;i++)
   {
      double entry=anchor+direction*offsets[i]*atr;
      AAA_SendPending(_Symbol,(direction>0 ? ORDER_TYPE_BUY_STOP : ORDER_TYPE_SELL_STOP),entry,common_stop,2.0,InpGridRiskPercent/levels,InpMagic,expiry,"AAA XAU grid");
   }
}

void AAA_RunXAUWeakness()
{
   AAA_ManageOCO(_Symbol,InpMagic);
   if(!AAA_NewBar(_Symbol,PERIOD_M15,g_last_bar) || !InpEnableTrading || !AAA_SpreadOK()) return;
   if(AAA_HasExposure(_Symbol,InpMagic)) return;
   MqlRates r[]; if(!AAA_LoadRates(PERIOD_M15,36,r)) return;
   double atr=AAA_ATR(_Symbol,PERIOD_M15,14,1);
   if(atr<=0.0) return;
   double tolerance=0.20*atr;
   int first_high=-1,second_high=-1,first_low=-1,second_low=-1;
   for(int newer=4;newer<=16;newer++)
   {
      for(int older=newer+4;older<=MathMin(newer+16,30);older++)
      {
         if(first_high<0 && MathAbs(r[newer].high-r[older].high)<=tolerance){ second_high=newer; first_high=older; }
         if(first_low<0 && MathAbs(r[newer].low-r[older].low)<=tolerance){ second_low=newer; first_low=older; }
      }
   }
   datetime expiry=TimeCurrent()+8*15*60;
   if(first_high>0)
   {
      double resistance=MathMax(r[first_high].high,r[second_high].high);
      double range_low=DBL_MAX; for(int i=1;i<=first_high;i++) range_low=MathMin(range_low,r[i].low);
      double impulse=r[first_high+1].close-r[MathMin(first_high+12,35)].open;
      if(impulse>=InpWeaknessATRImpulse*atr)
         AAA_SendPending(_Symbol,ORDER_TYPE_BUY_STOP,resistance+0.05*atr,range_low-0.05*atr,2.0,InpRiskPercent,InpMagic,expiry,"AAA XAU weakness breakout");
   }
   else if(first_low>0)
   {
      double support=MathMin(r[first_low].low,r[second_low].low);
      double range_high=-DBL_MAX; for(int i=1;i<=first_low;i++) range_high=MathMax(range_high,r[i].high);
      double impulse=r[MathMin(first_low+12,35)].open-r[first_low+1].close;
      if(impulse>=InpWeaknessATRImpulse*atr)
         AAA_SendPending(_Symbol,ORDER_TYPE_SELL_STOP,support-0.05*atr,range_high+0.05*atr,2.0,InpRiskPercent,InpMagic,expiry,"AAA XAU weakness breakout");
   }
}

int OnInit()
{
 if(!FP_InputsValid(InpRiskPercent))return INIT_PARAMETERS_INCORRECT;
   if(!DTS_InputsValid()) return INIT_PARAMETERS_INCORRECT;
   AAA_TesterServerOffsetMode=InpTesterServerClockMode;
   AAA_Trade.SetExpertMagicNumber((ulong)InpMagic);
   AAA_Trade.SetTypeFillingBySymbol(_Symbol);
   Print(AAA_STRATEGY_NAME," loaded on ",_Symbol,". Trading enabled=",InpEnableTrading,"; risk=",DoubleToString(InpRiskPercent,2),"%.");
   FP_Heartbeat(InpMagic,true);return INIT_SUCCEEDED;
}

void OnTick()
{
 if(!FP_BindingOK())return;FP_Heartbeat(InpMagic);
   DTS_ManageDynamicTrailing(InpMagic);
   if(AAA_STRATEGY_ID==AAA_ID_EMA3) AAA_RunEMA3();
   else if(AAA_STRATEGY_ID==AAA_ID_ASIA) AAA_RunAsiaBreakout();
   else if(AAA_STRATEGY_ID==AAA_ID_DMC) AAA_RunDmC();
   else if(AAA_STRATEGY_ID==AAA_ID_AMD) AAA_RunAMD();
   else if(AAA_STRATEGY_ID==AAA_ID_US100_WEAKNESS || AAA_STRATEGY_ID==AAA_ID_XAU_US100_PORT) AAA_RunReferencePairOCO();
   else if(AAA_STRATEGY_ID==AAA_ID_NEWS_PULSE) AAA_RunNewsPulse();
   else if(AAA_STRATEGY_ID==AAA_ID_WEEKEND) AAA_RunWeekend();
   else if(AAA_STRATEGY_ID==AAA_ID_XAU_GRID) AAA_RunXAUGrid();
   else if(AAA_STRATEGY_ID==AAA_ID_XAU_WEAKNESS) AAA_RunXAUWeakness();
}

