#property copyright "Research EA derived from published crypto momentum and reversal evidence"
#property version   "1.00"
#property strict

#include <Trade/Trade.mqh>

enum ENUM_CRYPTO_EDGE_MODE
{
   CRYPTO_TREND_PULLBACK=0,
   CRYPTO_EXTREME_REVERSION=1,
   CRYPTO_BREAKOUT_RETEST=2
};

input group "Strategy"
input ENUM_CRYPTO_EDGE_MODE InpMode=CRYPTO_TREND_PULLBACK;
input ENUM_TIMEFRAMES InpSignalTimeframe=PERIOD_M15;
input int InpATRPeriod=14;
input int InpFastEMAPeriod=20;
input int InpSlowEMAPeriod=50;
input int InpRSIPeriod=14;
input int InpBollingerPeriod=20;
input double InpBollingerDeviation=2.50;
input int InpDonchianBars=20;

input group "Trend pullback"
input bool InpUseH4Trend=true;
input bool InpRequire24HourMomentum=true;
input double InpPullbackTouchATR=0.20;
input int InpStructureLookbackBars=6;

input group "Extreme reversal"
input double InpRSILow=22.0;
input double InpRSIHigh=78.0;
input bool InpReversionWithH1Trend=false;

input group "Breakout retest"
input double InpMinimumBreakoutBodyATR=0.70;
input double InpMinimumVolumeFactor=1.10;
input double InpRetestToleranceATR=0.20;

input group "Trading window and limits"
input bool InpUseUTCSession=false;
input int InpSessionStartHourUTC=7;
input int InpSessionEndHourUTC=21;
input int InpServerUTCOffsetHours=0;
input int InpMaximumTradesPerDay=3;
input int InpMaximumHoldingBars=32;

input group "Risk and execution"
input double InpRiskPercent=1.00;
input double InpRewardRisk=0.70;
input double InpStopBufferATR=0.10;
input double InpMinimumStopATR=0.35;
input double InpMaximumStopATR=2.50;
input bool InpMoveToBreakEven=false;
input double InpBreakEvenAtR=0.50;
input double InpMaximumSpreadATR=0.08;
input int InpMaximumDeviationPoints=80;
input bool InpAllowLong=true;
input bool InpAllowShort=true;
input long InpMagic=863400;

CTrade g_trade;
int g_atr=INVALID_HANDLE;
int g_m15_fast=INVALID_HANDLE;
int g_h1_fast=INVALID_HANDLE,g_h1_slow=INVALID_HANDLE;
int g_h4_fast=INVALID_HANDLE,g_h4_slow=INVALID_HANDLE;
int g_rsi=INVALID_HANDLE;
int g_bands=INVALID_HANDLE;
datetime g_last_bar=0;
long g_day_key=0;
int g_day_trades=0;
double g_initial_risk=0.0;

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

bool IsOurSelectedPosition()
{
   return PositionGetString(POSITION_SYMBOL)==_Symbol && PositionGetInteger(POSITION_MAGIC)==InpMagic;
}

bool HasOurPosition()
{
   for(int index=PositionsTotal()-1;index>=0;index--)
      if(PositionGetTicket(index)>0 && IsOurSelectedPosition()) return true;
   return false;
}

bool BufferValue(const int handle,const int buffer,const int shift,double &value)
{
   double values[];
   if(handle==INVALID_HANDLE || CopyBuffer(handle,buffer,shift,1,values)!=1) return false;
   value=values[0];
   return MathIsValidNumber(value);
}

bool ReadATR(const int shift,double &value)
{
   if(!BufferValue(g_atr,0,shift,value)) return false;
   return value>0.0;
}

long UTCDateKey(const datetime server_time)
{
   MqlDateTime value={0};
   TimeToStruct(server_time-InpServerUTCOffsetHours*3600,value);
   return (long)value.year*10000+(long)value.mon*100+(long)value.day;
}

bool SessionPasses(const datetime server_time)
{
   datetime utc=server_time-InpServerUTCOffsetHours*3600;
   MqlDateTime value={0}; TimeToStruct(utc,value);
   if(!InpUseUTCSession) return true;
   if(InpSessionStartHourUTC<InpSessionEndHourUTC)
      return value.hour>=InpSessionStartHourUTC && value.hour<InpSessionEndHourUTC;
   return value.hour>=InpSessionStartHourUTC || value.hour<InpSessionEndHourUTC;
}

bool SpreadPasses(const double atr)
{
   if(InpMaximumSpreadATR<=0.0) return true;
   MqlTick tick={0};
   if(!SymbolInfoTick(_Symbol,tick) || tick.ask<=0.0 || tick.bid<=0.0) return false;
   return tick.ask-tick.bid<=InpMaximumSpreadATR*atr;
}

int TrendDirection()
{
   double h1fast=0.0,h1slow=0.0,h4fast=0.0,h4slow=0.0;
   if(!BufferValue(g_h1_fast,0,1,h1fast) || !BufferValue(g_h1_slow,0,1,h1slow)) return 0;
   int h1=(h1fast>h1slow ? 1 : h1fast<h1slow ? -1 : 0);
   if(!InpUseH4Trend) return h1;
   if(!BufferValue(g_h4_fast,0,1,h4fast) || !BufferValue(g_h4_slow,0,1,h4slow)) return 0;
   int h4=(h4fast>h4slow ? 1 : h4fast<h4slow ? -1 : 0);
   return h1==h4 ? h1 : 0;
}

double LowestLow(const MqlRates &rates[],const int start,const int count)
{
   double value=DBL_MAX;
   for(int index=start;index<start+count && index<ArraySize(rates);index++) value=MathMin(value,rates[index].low);
   return value;
}

double HighestHigh(const MqlRates &rates[],const int start,const int count)
{
   double value=-DBL_MAX;
   for(int index=start;index<start+count && index<ArraySize(rates);index++) value=MathMax(value,rates[index].high);
   return value;
}

bool PlaceTrade(const int direction,double structural_stop,const double atr,const string comment)
{
   if(HasOurPosition() || g_day_trades>=InpMaximumTradesPerDay) return false;
   if(direction>0 && !InpAllowLong) return false;
   if(direction<0 && !InpAllowShort) return false;
   if(!SpreadPasses(atr)) return false;
   MqlTick tick={0}; if(!SymbolInfoTick(_Symbol,tick)) return false;
   double entry=(direction>0 ? tick.ask : tick.bid);
   double stop=(direction>0 ? structural_stop-InpStopBufferATR*atr : structural_stop+InpStopBufferATR*atr);
   double distance=MathAbs(entry-stop);
   if(distance<InpMinimumStopATR*atr) stop=(direction>0 ? entry-InpMinimumStopATR*atr : entry+InpMinimumStopATR*atr);
   if(MathAbs(entry-stop)>InpMaximumStopATR*atr) return false;
   double point=SymbolInfoDouble(_Symbol,SYMBOL_POINT);
   double broker_gap=MathMax((double)SymbolInfoInteger(_Symbol,SYMBOL_TRADE_STOPS_LEVEL),
                             (double)SymbolInfoInteger(_Symbol,SYMBOL_TRADE_FREEZE_LEVEL))*point;
   if(direction>0 && entry-stop<broker_gap) stop=entry-broker_gap;
   if(direction<0 && stop-entry<broker_gap) stop=entry+broker_gap;
   distance=MathAbs(entry-stop);
   if(distance<=0.0) return false;
   double target=(direction>0 ? entry+InpRewardRisk*distance : entry-InpRewardRisk*distance);
   stop=NormalizePrice(stop); target=NormalizePrice(target);
   ENUM_ORDER_TYPE type=(direction>0 ? ORDER_TYPE_BUY : ORDER_TYPE_SELL);
   double lots=LotsForRisk(type,entry,stop);
   if(lots<=0.0) return false;
   g_trade.SetExpertMagicNumber((ulong)InpMagic);
   g_trade.SetTypeFillingBySymbol(_Symbol);
   g_trade.SetDeviationInPoints(InpMaximumDeviationPoints);
   bool sent=(direction>0 ? g_trade.Buy(lots,_Symbol,0.0,stop,target,comment)
                          : g_trade.Sell(lots,_Symbol,0.0,stop,target,comment));
   if(!sent)
   {
      Print("Crypto hybrid order rejected: ",g_trade.ResultRetcodeDescription());
      return false;
   }
   g_initial_risk=distance;
   return true;
}

bool TrendPullbackSignal(const MqlRates &rates[],const double atr)
{
   int direction=TrendDirection();
   if(direction==0) return false;
   double ema1=0.0,ema2=0.0;
   if(!BufferValue(g_m15_fast,0,1,ema1) || !BufferValue(g_m15_fast,0,2,ema2)) return false;
   int seconds_per_bar=PeriodSeconds(InpSignalTimeframe);
   int momentum_shift=(seconds_per_bar>0 ? (int)MathRound(86400.0/seconds_per_bar)+1 : 97);
   if(InpRequire24HourMomentum && ArraySize(rates)<=momentum_shift) return false;
   bool momentum_long=(!InpRequire24HourMomentum || rates[1].close>rates[momentum_shift].close);
   bool momentum_short=(!InpRequire24HourMomentum || rates[1].close<rates[momentum_shift].close);
   if(direction>0 && momentum_long)
   {
      bool touched=rates[2].low<=ema2+InpPullbackTouchATR*atr;
      bool reclaimed=rates[1].close>ema1 && rates[1].close>rates[1].open && rates[1].close>rates[2].high;
      if(touched && reclaimed)
         return PlaceTrade(1,LowestLow(rates,1,InpStructureLookbackBars),atr,"Crypto trend pullback long");
   }
   if(direction<0 && momentum_short)
   {
      bool touched=rates[2].high>=ema2-InpPullbackTouchATR*atr;
      bool reclaimed=rates[1].close<ema1 && rates[1].close<rates[1].open && rates[1].close<rates[2].low;
      if(touched && reclaimed)
         return PlaceTrade(-1,HighestHigh(rates,1,InpStructureLookbackBars),atr,"Crypto trend pullback short");
   }
   return false;
}

bool ReversionSignal(const MqlRates &rates[],const double atr)
{
   double upper1=0.0,upper2=0.0,lower1=0.0,lower2=0.0,rsi1=0.0,rsi2=0.0;
   if(!BufferValue(g_bands,1,1,upper1) || !BufferValue(g_bands,1,2,upper2) ||
      !BufferValue(g_bands,2,1,lower1) || !BufferValue(g_bands,2,2,lower2) ||
      !BufferValue(g_rsi,0,1,rsi1) || !BufferValue(g_rsi,0,2,rsi2)) return false;
   int trend=(InpReversionWithH1Trend ? TrendDirection() : 0);
   bool long_signal=rates[2].close<lower2 && rsi2<=InpRSILow && rates[1].close>lower1 && rates[1].close>rates[1].open;
   bool short_signal=rates[2].close>upper2 && rsi2>=InpRSIHigh && rates[1].close<upper1 && rates[1].close<rates[1].open;
   if(long_signal && (!InpReversionWithH1Trend || trend>=0))
      return PlaceTrade(1,MathMin(rates[1].low,rates[2].low),atr,"Crypto extreme reversion long");
   if(short_signal && (!InpReversionWithH1Trend || trend<=0))
      return PlaceTrade(-1,MathMax(rates[1].high,rates[2].high),atr,"Crypto extreme reversion short");
   return false;
}

bool BreakoutRetestSignal(const MqlRates &rates[],const double atr)
{
   int direction=TrendDirection();
   if(direction==0) return false;
   double channel_high=HighestHigh(rates,3,InpDonchianBars);
   double channel_low=LowestLow(rates,3,InpDonchianBars);
   double body=MathAbs(rates[2].close-rates[2].open);
   double average_volume=0.0;
   for(int index=3;index<3+InpDonchianBars && index<ArraySize(rates);index++) average_volume+=(double)rates[index].tick_volume;
   average_volume/=InpDonchianBars;
   bool volume_pass=(double)rates[2].tick_volume>=InpMinimumVolumeFactor*average_volume;
   if(direction>0 && rates[2].close>channel_high && body>=InpMinimumBreakoutBodyATR*atr && volume_pass)
   {
      bool retest=rates[1].low<=channel_high+InpRetestToleranceATR*atr && rates[1].close>channel_high && rates[1].close>rates[1].open;
      if(retest) return PlaceTrade(1,MathMin(rates[1].low,rates[2].low),atr,"Crypto breakout retest long");
   }
   if(direction<0 && rates[2].close<channel_low && body>=InpMinimumBreakoutBodyATR*atr && volume_pass)
   {
      bool retest=rates[1].high>=channel_low-InpRetestToleranceATR*atr && rates[1].close<channel_low && rates[1].close<rates[1].open;
      if(retest) return PlaceTrade(-1,MathMax(rates[1].high,rates[2].high),atr,"Crypto breakout retest short");
   }
   return false;
}

void ManagePosition()
{
   MqlTick tick={0}; if(!SymbolInfoTick(_Symbol,tick)) return;
   bool found=false;
   for(int index=PositionsTotal()-1;index>=0;index--)
   {
      ulong ticket=PositionGetTicket(index);
      if(ticket==0 || !IsOurSelectedPosition()) continue;
      found=true;
      bool buy=PositionGetInteger(POSITION_TYPE)==POSITION_TYPE_BUY;
      double open=PositionGetDouble(POSITION_PRICE_OPEN);
      double stop=PositionGetDouble(POSITION_SL);
      double target=PositionGetDouble(POSITION_TP);
      double current=(buy ? tick.bid : tick.ask);
      if(g_initial_risk<=0.0) g_initial_risk=MathAbs(open-stop);
      if(InpMoveToBreakEven && g_initial_risk>0.0)
      {
         double favorable=(buy ? current-open : open-current);
         if(favorable>=InpBreakEvenAtR*g_initial_risk)
         {
            double point=SymbolInfoDouble(_Symbol,SYMBOL_POINT);
            double gap=MathMax((double)SymbolInfoInteger(_Symbol,SYMBOL_TRADE_STOPS_LEVEL),
                               (double)SymbolInfoInteger(_Symbol,SYMBOL_TRADE_FREEZE_LEVEL))*point;
            bool valid=(buy ? open>stop && open<current-gap : (stop<=0.0 || open<stop) && open>current+gap);
            if(valid) g_trade.PositionModify(ticket,NormalizePrice(open),target);
         }
      }
      datetime opened=(datetime)PositionGetInteger(POSITION_TIME);
      if(InpMaximumHoldingBars>0 && TimeCurrent()>=opened+InpMaximumHoldingBars*PeriodSeconds(InpSignalTimeframe))
         g_trade.PositionClose(ticket,(ulong)InpMaximumDeviationPoints);
   }
   if(!found) g_initial_risk=0.0;
}

void ProcessClosedBar()
{
   int required=MathMax(110,InpDonchianBars+10);
   MqlRates rates[]; ArraySetAsSeries(rates,true);
   if(CopyRates(_Symbol,InpSignalTimeframe,0,required,rates)<required) return;
   long day=UTCDateKey(rates[1].time);
   if(day!=g_day_key) { g_day_key=day; g_day_trades=0; }
   if(!SessionPasses(rates[1].time) || HasOurPosition() || g_day_trades>=InpMaximumTradesPerDay) return;
   double atr=0.0; if(!ReadATR(1,atr)) return;
   if(InpMode==CRYPTO_TREND_PULLBACK) TrendPullbackSignal(rates,atr);
   else if(InpMode==CRYPTO_EXTREME_REVERSION) ReversionSignal(rates,atr);
   else BreakoutRetestSignal(rates,atr);
}

int OnInit()
{
   if(InpATRPeriod<2 || InpFastEMAPeriod<2 || InpSlowEMAPeriod<=InpFastEMAPeriod ||
      InpRSIPeriod<2 || InpBollingerPeriod<5 || InpBollingerDeviation<=0.0 || InpDonchianBars<5 ||
      InpStructureLookbackBars<2 || InpRSILow<=0.0 || InpRSIHigh>=100.0 || InpRSILow>=InpRSIHigh ||
      InpSessionStartHourUTC<0 || InpSessionStartHourUTC>23 || InpSessionEndHourUTC<0 || InpSessionEndHourUTC>23 ||
      InpMaximumTradesPerDay<1 || InpMaximumHoldingBars<1 || InpRiskPercent<=0.0 || InpRewardRisk<=0.0 ||
      InpMinimumStopATR<=0.0 || InpMaximumStopATR<=InpMinimumStopATR || InpBreakEvenAtR<=0.0 ||
      InpMaximumSpreadATR<0.0) return INIT_PARAMETERS_INCORRECT;
   g_atr=iATR(_Symbol,InpSignalTimeframe,InpATRPeriod);
   g_m15_fast=iMA(_Symbol,InpSignalTimeframe,InpFastEMAPeriod,0,MODE_EMA,PRICE_CLOSE);
   g_h1_fast=iMA(_Symbol,PERIOD_H1,InpFastEMAPeriod,0,MODE_EMA,PRICE_CLOSE);
   g_h1_slow=iMA(_Symbol,PERIOD_H1,InpSlowEMAPeriod,0,MODE_EMA,PRICE_CLOSE);
   g_h4_fast=iMA(_Symbol,PERIOD_H4,InpFastEMAPeriod,0,MODE_EMA,PRICE_CLOSE);
   g_h4_slow=iMA(_Symbol,PERIOD_H4,InpSlowEMAPeriod,0,MODE_EMA,PRICE_CLOSE);
   g_rsi=iRSI(_Symbol,InpSignalTimeframe,InpRSIPeriod,PRICE_CLOSE);
   g_bands=iBands(_Symbol,InpSignalTimeframe,InpBollingerPeriod,0,InpBollingerDeviation,PRICE_CLOSE);
   if(g_atr==INVALID_HANDLE || g_m15_fast==INVALID_HANDLE || g_h1_fast==INVALID_HANDLE ||
      g_h1_slow==INVALID_HANDLE || g_h4_fast==INVALID_HANDLE || g_h4_slow==INVALID_HANDLE ||
      g_rsi==INVALID_HANDLE || g_bands==INVALID_HANDLE) return INIT_FAILED;
   g_trade.SetExpertMagicNumber((ulong)InpMagic);
   g_trade.SetTypeFillingBySymbol(_Symbol);
   g_last_bar=iTime(_Symbol,InpSignalTimeframe,0);
   return INIT_SUCCEEDED;
}

void ReleaseHandle(int &handle)
{
   if(handle!=INVALID_HANDLE) IndicatorRelease(handle);
   handle=INVALID_HANDLE;
}

void OnDeinit(const int reason)
{
   ReleaseHandle(g_atr); ReleaseHandle(g_m15_fast); ReleaseHandle(g_h1_fast); ReleaseHandle(g_h1_slow);
   ReleaseHandle(g_h4_fast); ReleaseHandle(g_h4_slow); ReleaseHandle(g_rsi); ReleaseHandle(g_bands);
}

void OnTradeTransaction(const MqlTradeTransaction &transaction,const MqlTradeRequest &request,const MqlTradeResult &result)
{
   if(transaction.type!=TRADE_TRANSACTION_DEAL_ADD || transaction.deal==0 || !HistoryDealSelect(transaction.deal)) return;
   if(HistoryDealGetInteger(transaction.deal,DEAL_MAGIC)!=InpMagic || HistoryDealGetString(transaction.deal,DEAL_SYMBOL)!=_Symbol) return;
   long entry=HistoryDealGetInteger(transaction.deal,DEAL_ENTRY);
   if(entry==DEAL_ENTRY_OUT || entry==DEAL_ENTRY_OUT_BY) g_day_trades++;
}

void OnTick()
{
   ManagePosition();
   datetime current=iTime(_Symbol,InpSignalTimeframe,0);
   if(current<=0 || current==g_last_bar) return;
   g_last_bar=current;
   ProcessClosedBar();
}
