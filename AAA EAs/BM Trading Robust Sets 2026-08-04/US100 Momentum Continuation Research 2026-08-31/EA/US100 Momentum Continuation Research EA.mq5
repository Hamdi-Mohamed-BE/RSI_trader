#property copyright "US100 momentum continuation research EA"
#property version   "1.10"
#property strict

#include <Trade/Trade.mqh>
#include "SafeRegimeFilter.mqh"

enum ENUM_US100_MOMENTUM_MODEL
{
   MOMENTUM_NY_OPEN=0,
   MOMENTUM_H1_CONTINUATION=1
};

input group "Research model"
input ENUM_US100_MOMENTUM_MODEL InpMomentumModel=MOMENTUM_NY_OPEN;

input group "US open signal"
input ENUM_TIMEFRAMES InpSignalTimeframe=PERIOD_M5;
input int InpEMAPeriod=12;
input bool InpAllowLong=true;
input bool InpAllowShort=true;

input group "H1 continuation confirmation"
input bool InpUseH1ContinuationGate=false;
input ENUM_TIMEFRAMES InpContinuationTimeframe=PERIOD_H1;
input int InpMomentumLookback=24;
input double InpMinimumMomentumATR=0.50;
input int InpRangeLookback=48;
input double InpMinimumRangePosition=0.75;
input int InpTrendEMAPeriod=100;
input int InpTrendSlopeBars=1;
input int InpMaximumHoldingBars=120;

input group "Volatility stop and trail"
input int InpATRPeriod=14;
input double InpInitialStopATR=1.50;
input double InpTrailingATR=2.00;
input double InpTrailStartR=0.00;
input bool InpCloseAtSessionEnd=true;
input int InpCloseHourNY=15;
input int InpCloseMinuteNY=55;

input group "Time conversion"
input bool InpAutoServerUtcOffsetLive=true;
input int InpServerUtcOffsetHours=0;

input group "Risk and execution"
input bool InpEnableTrading=true;
input double InpRiskPercent=1.00;
input double InpMaximumSpreadATR=0.00;
input long InpMagic=862020;
input int InpMaximumDeviationPoints=50;

CTrade g_trade;
int g_ema_handle=INVALID_HANDLE;
int g_atr_handle=INVALID_HANDLE;
int g_cont_ema_handle=INVALID_HANDLE;
int g_cont_atr_handle=INVALID_HANDLE;
datetime g_last_bar_time=0;

ENUM_TIMEFRAMES ActiveTimeframe()
{
   return (InpMomentumModel==MOMENTUM_H1_CONTINUATION ? InpContinuationTimeframe : InpSignalTimeframe);
}

double NormalizePrice(const double price)
{
   return NormalizeDouble(price,(int)SymbolInfoInteger(_Symbol,SYMBOL_DIGITS));
}

double NormalizeLots(const double raw_lots)
{
   double minimum=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MIN);
   double maximum=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MAX);
   double step=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_STEP);
   if(step<=0.0) return 0.0;
   double lots=MathFloor(raw_lots/step+1e-9)*step;
   if(lots<minimum) return 0.0;
   return MathMin(lots,maximum);
}

double LotsForRisk(const ENUM_ORDER_TYPE type,const double entry,const double stop)
{
   double cash=AccountInfoDouble(ACCOUNT_EQUITY)*InpRiskPercent/100.0;
   double one_lot=0.0;
   if(cash<=0.0 || !OrderCalcProfit(type,_Symbol,1.0,entry,stop,one_lot)) return 0.0;
   one_lot=MathAbs(one_lot);
   if(one_lot<=0.0) return 0.0;
   return NormalizeLots(cash/one_lot);
}

bool ReadIndicatorValue(const int handle,const int shift,double &value)
{
   double buffer[];
   if(handle==INVALID_HANDLE || CopyBuffer(handle,0,shift,1,buffer)!=1) return false;
   value=buffer[0];
   return value>0.0;
}

int ServerUtcOffsetSeconds()
{
   if(!InpAutoServerUtcOffsetLive || (bool)MQLInfoInteger(MQL_TESTER))
      return InpServerUtcOffsetHours*3600;
   datetime server=TimeTradeServer();
   datetime utc=TimeGMT();
   if(server<=0 || utc<=0) return InpServerUtcOffsetHours*3600;
   return (int)MathRound((double)(server-utc)/1800.0)*1800;
}

datetime BuildUtcTime(const int year,const int month,const int day,const int hour)
{
   MqlDateTime value;
   ZeroMemory(value);
   value.year=year;
   value.mon=month;
   value.day=day;
   value.hour=hour;
   return StructToTime(value);
}

int NthSunday(const int year,const int month,const int nth)
{
   MqlDateTime first;
   TimeToStruct(BuildUtcTime(year,month,1,0),first);
   int first_sunday=1+((7-first.day_of_week)%7);
   return first_sunday+(nth-1)*7;
}

int NewYorkUtcOffsetHours(const datetime utc_time)
{
   MqlDateTime parts;
   TimeToStruct(utc_time,parts);
   datetime dst_start=BuildUtcTime(parts.year,3,NthSunday(parts.year,3,2),7);
   datetime dst_end=BuildUtcTime(parts.year,11,NthSunday(parts.year,11,1),6);
   return (utc_time>=dst_start && utc_time<dst_end ? -4 : -5);
}

datetime ServerToNewYork(const datetime server_time)
{
   datetime utc_time=server_time-ServerUtcOffsetSeconds();
   return utc_time+NewYorkUtcOffsetHours(utc_time)*3600;
}

int NewYorkDateKey(const datetime server_time)
{
   MqlDateTime ny;
   TimeToStruct(ServerToNewYork(server_time),ny);
   return ny.year*10000+ny.mon*100+ny.day;
}

bool IsNewYorkTime(const datetime server_time,const int hour,const int minute)
{
   MqlDateTime ny;
   TimeToStruct(ServerToNewYork(server_time),ny);
   return ny.day_of_week>=1 && ny.day_of_week<=5 && ny.hour==hour && ny.min==minute;
}

bool IsAtOrAfterSessionClose(const datetime server_time)
{
   MqlDateTime ny;
   TimeToStruct(ServerToNewYork(server_time),ny);
   if(ny.day_of_week<1 || ny.day_of_week>5) return false;
   return ny.hour>InpCloseHourNY || (ny.hour==InpCloseHourNY && ny.min>=InpCloseMinuteNY);
}

bool IsOurPosition()
{
   return PositionGetString(POSITION_SYMBOL)==_Symbol && PositionGetInteger(POSITION_MAGIC)==InpMagic;
}

bool SelectOurPosition(ulong &ticket)
{
   for(int index=PositionsTotal()-1;index>=0;index--)
   {
      ticket=PositionGetTicket(index);
      if(ticket>0 && IsOurPosition()) return true;
   }
   ticket=0;
   return false;
}

string RiskKey(const ulong identifier)
{
   return "N5EMA."+(string)InpMagic+"."+(string)identifier+".R";
}

void StoreInitialRisk()
{
   ulong ticket=0;
   if(!SelectOurPosition(ticket)) return;
   double open=PositionGetDouble(POSITION_PRICE_OPEN);
   double stop=PositionGetDouble(POSITION_SL);
   ulong identifier=(ulong)PositionGetInteger(POSITION_IDENTIFIER);
   double risk=MathAbs(open-stop);
   if(identifier>0 && risk>0.0) GlobalVariableSet(RiskKey(identifier),risk);
}

double InitialRiskForSelectedPosition()
{
   ulong identifier=(ulong)PositionGetInteger(POSITION_IDENTIFIER);
   string key=RiskKey(identifier);
   if(identifier>0 && GlobalVariableCheck(key))
   {
      double stored=GlobalVariableGet(key);
      if(stored>0.0) return stored;
   }
   return MathAbs(PositionGetDouble(POSITION_PRICE_OPEN)-PositionGetDouble(POSITION_SL));
}

bool AlreadyTradedOnNewYorkDate(const int date_key)
{
   datetime now=TimeCurrent();
   if(!HistorySelect(now-4*86400,now+3600)) return false;
   for(int index=HistoryDealsTotal()-1;index>=0;index--)
   {
      ulong deal=HistoryDealGetTicket(index);
      if(deal==0) continue;
      if(HistoryDealGetInteger(deal,DEAL_MAGIC)!=InpMagic) continue;
      if(HistoryDealGetString(deal,DEAL_SYMBOL)!=_Symbol) continue;
      long entry=HistoryDealGetInteger(deal,DEAL_ENTRY);
      if(entry!=DEAL_ENTRY_IN && entry!=DEAL_ENTRY_INOUT) continue;
      datetime when=(datetime)HistoryDealGetInteger(deal,DEAL_TIME);
      if(NewYorkDateKey(when)==date_key) return true;
   }
   return false;
}

bool CurrentSpreadPasses(const double atr)
{
   if(InpMaximumSpreadATR<=0.0) return true;
   MqlTick tick;
   if(!SymbolInfoTick(_Symbol,tick) || tick.ask<=0.0 || tick.bid<=0.0) return false;
   return tick.ask-tick.bid<=InpMaximumSpreadATR*atr;
}

bool SendEntry(const int direction,const double atr)
{
   if(!HAMA_SafeRegimeAllowsDirection(direction)) return false;
   MqlTick tick;
   if(!SymbolInfoTick(_Symbol,tick)) return false;
   double entry=(direction>0 ? tick.ask : tick.bid);
   double stop=NormalizePrice(entry-direction*InpInitialStopATR*atr);
   double point=SymbolInfoDouble(_Symbol,SYMBOL_POINT);
   double broker_gap=MathMax((double)SymbolInfoInteger(_Symbol,SYMBOL_TRADE_STOPS_LEVEL),
                             (double)SymbolInfoInteger(_Symbol,SYMBOL_TRADE_FREEZE_LEVEL))*point;
   if(MathAbs(entry-stop)<broker_gap) stop=NormalizePrice(entry-direction*broker_gap);
   ENUM_ORDER_TYPE type=(direction>0 ? ORDER_TYPE_BUY : ORDER_TYPE_SELL);
   double lots=LotsForRisk(type,entry,stop);
   if(lots<=0.0)
   {
      Print("N5EMA skipped: risk-sized volume is below the broker minimum.");
      return false;
   }
   g_trade.SetExpertMagicNumber((ulong)InpMagic);
   g_trade.SetTypeFillingBySymbol(_Symbol);
   g_trade.SetDeviationInPoints(InpMaximumDeviationPoints);
   string comment=(direction>0 ? "N5EMA long" : "N5EMA short");
   bool sent=(direction>0 ? g_trade.Buy(lots,_Symbol,0.0,stop,0.0,comment)
                          : g_trade.Sell(lots,_Symbol,0.0,stop,0.0,comment));
   if(sent) StoreInitialRisk();
   else Print("N5EMA order rejected: ",g_trade.ResultRetcodeDescription());
   return sent;
}

double ExtremeSinceOpen(const bool buy,const datetime opened,const MqlTick &tick)
{
   ENUM_TIMEFRAMES timeframe=ActiveTimeframe();
   int shift=iBarShift(_Symbol,timeframe,opened,false);
   if(shift<0) shift=0;
   int count=shift+1;
   double values[];
   ArraySetAsSeries(values,true);
   double extreme=(buy ? tick.bid : tick.ask);
   if(buy)
   {
      if(CopyHigh(_Symbol,timeframe,0,count,values)==count)
         extreme=MathMax(extreme,values[ArrayMaximum(values)]);
   }
   else
   {
      if(CopyLow(_Symbol,timeframe,0,count,values)==count)
         extreme=MathMin(extreme,values[ArrayMinimum(values)]);
   }
   return extreme;
}

void ManagePosition()
{
   ulong ticket=0;
   if(!SelectOurPosition(ticket)) return;
   if(InpMomentumModel==MOMENTUM_NY_OPEN && InpCloseAtSessionEnd && IsAtOrAfterSessionClose(TimeCurrent()))
   {
      g_trade.SetExpertMagicNumber((ulong)InpMagic);
      g_trade.SetDeviationInPoints(InpMaximumDeviationPoints);
      if(!g_trade.PositionClose(ticket,(ulong)InpMaximumDeviationPoints))
         Print("N5EMA session close failed: ",g_trade.ResultRetcodeDescription());
      return;
   }

   if(InpMomentumModel==MOMENTUM_H1_CONTINUATION && InpMaximumHoldingBars>0)
   {
      datetime opened=(datetime)PositionGetInteger(POSITION_TIME);
      int held_bars=iBarShift(_Symbol,InpContinuationTimeframe,opened,false);
      if(held_bars>=InpMaximumHoldingBars)
      {
         g_trade.SetExpertMagicNumber((ulong)InpMagic);
         g_trade.SetDeviationInPoints(InpMaximumDeviationPoints);
         if(!g_trade.PositionClose(ticket,(ulong)InpMaximumDeviationPoints))
            Print("Momentum continuation time exit failed: ",g_trade.ResultRetcodeDescription());
         return;
      }
   }

   MqlTick tick;
   if(!SymbolInfoTick(_Symbol,tick)) return;
   double atr=0.0;
   int atr_handle=(InpMomentumModel==MOMENTUM_H1_CONTINUATION ? g_cont_atr_handle : g_atr_handle);
   if(!ReadIndicatorValue(atr_handle,0,atr)) return;
   bool buy=PositionGetInteger(POSITION_TYPE)==POSITION_TYPE_BUY;
   double open=PositionGetDouble(POSITION_PRICE_OPEN);
   double current=(buy ? tick.bid : tick.ask);
   double stop=PositionGetDouble(POSITION_SL);
   double initial_risk=InitialRiskForSelectedPosition();
   if(initial_risk<=0.0) return;
   double favorable=(buy ? current-open : open-current);
   if(InpTrailStartR>0.0 && favorable<InpTrailStartR*initial_risk) return;

   datetime opened=(datetime)PositionGetInteger(POSITION_TIME);
   double extreme=ExtremeSinceOpen(buy,opened,tick);
   double candidate=NormalizePrice(extreme+(buy ? -1.0 : 1.0)*InpTrailingATR*atr);
   double point=SymbolInfoDouble(_Symbol,SYMBOL_POINT);
   double broker_gap=MathMax((double)SymbolInfoInteger(_Symbol,SYMBOL_TRADE_STOPS_LEVEL),
                             (double)SymbolInfoInteger(_Symbol,SYMBOL_TRADE_FREEZE_LEVEL))*point;
   if(buy) candidate=MathMin(candidate,tick.bid-broker_gap);
   else candidate=MathMax(candidate,tick.ask+broker_gap);
   candidate=NormalizePrice(candidate);
   bool improves=(buy ? candidate>stop+point : stop<=0.0 || candidate<stop-point);
   if(!improves) return;
   g_trade.SetExpertMagicNumber((ulong)InpMagic);
   g_trade.SetDeviationInPoints(InpMaximumDeviationPoints);
   if(!g_trade.PositionModify(ticket,candidate,0.0))
      Print("N5EMA trail modify failed: ",g_trade.ResultRetcodeDescription());
}

bool H1ContinuationSignal(double &atr)
{
   int required=MathMax(InpMomentumLookback,InpRangeLookback)+2;
   MqlRates rates[];
   ArraySetAsSeries(rates,true);
   if(CopyRates(_Symbol,InpContinuationTimeframe,0,required,rates)!=required) return false;
   if(!ReadIndicatorValue(g_cont_atr_handle,1,atr)) return false;

   double close=rates[1].close;
   double prior=rates[1+InpMomentumLookback].close;
   if(close-prior<InpMinimumMomentumATR*atr) return false;

   double highest=rates[1].high;
   double lowest=rates[1].low;
   for(int index=2;index<=InpRangeLookback;index++)
   {
      highest=MathMax(highest,rates[index].high);
      lowest=MathMin(lowest,rates[index].low);
   }
   if(highest<=lowest) return false;
   double range_position=(close-lowest)/(highest-lowest);
   if(range_position<InpMinimumRangePosition) return false;

   double ema_now=0.0;
   double ema_then=0.0;
   if(!ReadIndicatorValue(g_cont_ema_handle,1,ema_now) ||
      !ReadIndicatorValue(g_cont_ema_handle,1+InpTrendSlopeBars,ema_then)) return false;
   return ema_now>ema_then;
}

void ProcessContinuationNewBar()
{
   if(!InpEnableTrading) return;
   ulong ticket=0;
   if(SelectOurPosition(ticket)) return;
   double atr=0.0;
   if(!H1ContinuationSignal(atr) || !CurrentSpreadPasses(atr)) return;
   SendEntry(1,atr);
}

void ProcessNewBar()
{
   MqlRates rates[];
   ArraySetAsSeries(rates,true);
   if(CopyRates(_Symbol,InpSignalTimeframe,0,3,rates)!=3) return;
   if(!IsNewYorkTime(rates[1].time,9,30)) return;
   int date_key=NewYorkDateKey(rates[1].time);
   ulong ticket=0;
   if(SelectOurPosition(ticket) || AlreadyTradedOnNewYorkDate(date_key) || !InpEnableTrading) return;

   double ema=0.0;
   double atr=0.0;
   if(!ReadIndicatorValue(g_ema_handle,1,ema) || !ReadIndicatorValue(g_atr_handle,1,atr)) return;
   if(!CurrentSpreadPasses(atr)) return;
   if(rates[1].close>ema && InpAllowLong)
   {
      double continuation_atr=0.0;
      if(!InpUseH1ContinuationGate || H1ContinuationSignal(continuation_atr)) SendEntry(1,atr);
   }
   else if(rates[1].close<ema && InpAllowShort) SendEntry(-1,atr);
}

int OnInit()
{
   if(InpSignalTimeframe!=PERIOD_M5 || InpContinuationTimeframe!=PERIOD_H1 ||
      InpEMAPeriod<2 || InpATRPeriod<2 || InpMomentumLookback<1 || InpRangeLookback<2 ||
      InpMinimumMomentumATR<0.0 || InpMinimumRangePosition<0.0 || InpMinimumRangePosition>1.0 ||
      InpTrendEMAPeriod<2 || InpTrendSlopeBars<1 || InpMaximumHoldingBars<0 ||
      InpInitialStopATR<=0.0 || InpTrailingATR<=0.0 || InpRiskPercent<=0.0 ||
      InpCloseHourNY<0 || InpCloseHourNY>23 || InpCloseMinuteNY<0 || InpCloseMinuteNY>59)
      return INIT_PARAMETERS_INCORRECT;
   g_ema_handle=iMA(_Symbol,InpSignalTimeframe,InpEMAPeriod,0,MODE_EMA,PRICE_CLOSE);
   g_atr_handle=iATR(_Symbol,InpSignalTimeframe,InpATRPeriod);
   g_cont_ema_handle=iMA(_Symbol,InpContinuationTimeframe,InpTrendEMAPeriod,0,MODE_EMA,PRICE_CLOSE);
   g_cont_atr_handle=iATR(_Symbol,InpContinuationTimeframe,InpATRPeriod);
   if(g_ema_handle==INVALID_HANDLE || g_atr_handle==INVALID_HANDLE ||
      g_cont_ema_handle==INVALID_HANDLE || g_cont_atr_handle==INVALID_HANDLE) return INIT_FAILED;
   g_trade.SetExpertMagicNumber((ulong)InpMagic);
   g_trade.SetTypeFillingBySymbol(_Symbol);
   g_last_bar_time=iTime(_Symbol,ActiveTimeframe(),0);
   return INIT_SUCCEEDED;
}

void OnDeinit(const int reason)
{
   if(g_ema_handle!=INVALID_HANDLE) IndicatorRelease(g_ema_handle);
   if(g_atr_handle!=INVALID_HANDLE) IndicatorRelease(g_atr_handle);
   if(g_cont_ema_handle!=INVALID_HANDLE) IndicatorRelease(g_cont_ema_handle);
   if(g_cont_atr_handle!=INVALID_HANDLE) IndicatorRelease(g_cont_atr_handle);
}

void OnTick()
{
   ManagePosition();
   ENUM_TIMEFRAMES timeframe=ActiveTimeframe();
   datetime bar_time=iTime(_Symbol,timeframe,0);
   if(bar_time<=0 || bar_time==g_last_bar_time) return;
   g_last_bar_time=bar_time;
   if(InpMomentumModel==MOMENTUM_H1_CONTINUATION) ProcessContinuationNewBar();
   else ProcessNewBar();
}
