#property copyright "Independent Hybrid CVD research build"
#property version   "1.00"
#property strict

#include "Research_Common.mqh"

enum ENUM_HYBRID_CVD_MODE
{
   CVD_TREND_CONTINUATION=0,
   CVD_DIVERGENCE_REVERSAL=1,
   CVD_BOTH_SETUPS=2
};

input group "Signal model"
input ENUM_TIMEFRAMES   InpSignalTimeframe=PERIOD_M5;
input ENUM_HYBRID_CVD_MODE InpSignalMode=CVD_TREND_CONTINUATION;
input int               InpFastEMAPeriod=20;
input int               InpSlowEMAPeriod=50;
input int               InpBreakoutLookback=6;
input int               InpDivergenceLookback=12;

input group "Hybrid CVD proxy"
input int    InpFastCVDMinutes=30;
input double InpDirectionWeight=0.70;
input double InpFastCVDMinRatio=0.12;
input double InpSessionCVDMinRatio=0.025;
input double InpDivergenceMinImprovement=0.08;
input int    InpVolumeLookback=20;
input double InpMinRelativeVolume=1.00;

input group "Session and VWAP"
input int  InpSessionStartUTC=12;
input int  InpSessionEndUTC=21;
input int  InpTesterServerUTCOffsetHours=0;
input bool InpRequireVWAP=true;
input bool InpFlatAtSessionEnd=true;
input int  InpMaximumTradesPerDay=2;

input group "Risk and exits"
input int    InpATRPeriod=14;
input double InpStopATR=1.50;
input double InpRewardRisk=2.00;
input double InpBreakEvenAtR=1.00;
input double InpBreakEvenLockR=0.10;
input double InpTrailStartR=1.50;
input double InpTrailATR=1.50;
input double InpMaximumSpreadATR=0.15;
input double InpRiskPercent=1.00;
input bool   InpEnableLong=true;
input bool   InpEnableShort=true;
input long   InpMagic=861212;
input int    InpMaxDeviationPoints=100;

datetime g_last_bar=0;
int g_fast_ema=INVALID_HANDLE;
int g_slow_ema=INVALID_HANDLE;
int g_atr=INVALID_HANDLE;
int g_trading_day=-1;
int g_trades_today=0;
double g_initial_risk=0.0;

datetime ToUTC(const datetime server_time)
{
   if((bool)MQLInfoInteger(MQL_TESTER))
      return server_time-InpTesterServerUTCOffsetHours*3600;
   return server_time-(TimeCurrent()-TimeGMT());
}

datetime FromUTC(const datetime utc_time)
{
   if((bool)MQLInfoInteger(MQL_TESTER))
      return utc_time+InpTesterServerUTCOffsetHours*3600;
   return utc_time+(TimeCurrent()-TimeGMT());
}

int UTCDateKey(const datetime server_time)
{
   MqlDateTime p;
   TimeToStruct(ToUTC(server_time),p);
   return p.year*10000+p.mon*100+p.day;
}

int UTCHour(const datetime server_time)
{
   MqlDateTime p;
   TimeToStruct(ToUTC(server_time),p);
   return p.hour;
}

bool InSession(const datetime server_time)
{
   int hour=UTCHour(server_time);
   if(InpSessionStartUTC<InpSessionEndUTC)
      return hour>=InpSessionStartUTC && hour<InpSessionEndUTC;
   return hour>=InpSessionStartUTC || hour<InpSessionEndUTC;
}

datetime SessionAnchor(const datetime server_time)
{
   datetime utc=ToUTC(server_time);
   MqlDateTime p;
   TimeToStruct(utc,p);
   p.hour=InpSessionStartUTC;
   p.min=0;
   p.sec=0;
   datetime anchor=StructToTime(p);
   if(InpSessionStartUTC>=InpSessionEndUTC && utc<anchor)
      anchor-=86400;
   return FromUTC(anchor);
}

bool HybridStats(const datetime from_time,const datetime to_time,
                 double &delta,double &volume,double &vwap)
{
   delta=0.0;
   volume=0.0;
   vwap=0.0;
   if(to_time<=from_time) return false;
   MqlRates rates[];
   ArraySetAsSeries(rates,false);
   int copied=CopyRates(_Symbol,PERIOD_M1,from_time,to_time-1,rates);
   if(copied<2) return false;
   double weight=MathMax(0.0,MathMin(1.0,InpDirectionWeight));
   double previous_close=rates[0].open;
   double price_volume=0.0;
   for(int i=0;i<copied;i++)
   {
      double direction=0.0;
      if(rates[i].close>rates[i].open) direction=1.0;
      else if(rates[i].close<rates[i].open) direction=-1.0;
      else if(rates[i].close>previous_close) direction=1.0;
      else if(rates[i].close<previous_close) direction=-1.0;
      double range=rates[i].high-rates[i].low;
      double close_location=(range>0.0 ? (2.0*rates[i].close-rates[i].high-rates[i].low)/range : 0.0);
      close_location=MathMax(-1.0,MathMin(1.0,close_location));
      double bar_volume=(double)rates[i].tick_volume;
      double signed_pressure=weight*direction+(1.0-weight)*close_location;
      delta+=bar_volume*signed_pressure;
      volume+=bar_volume;
      price_volume+=bar_volume*(rates[i].high+rates[i].low+rates[i].close)/3.0;
      previous_close=rates[i].close;
   }
   if(volume<=0.0) return false;
   vwap=price_volume/volume;
   return true;
}

double RelativeVolume(const int shift)
{
   if(InpVolumeLookback<2) return 1.0;
   long current=iVolume(_Symbol,InpSignalTimeframe,shift);
   double total=0.0;
   int valid=0;
   for(int i=shift+1;i<=shift+InpVolumeLookback;i++)
   {
      long value=iVolume(_Symbol,InpSignalTimeframe,i);
      if(value>0) { total+=(double)value; valid++; }
   }
   if(current<=0 || valid==0 || total<=0.0) return 0.0;
   return (double)current/(total/valid);
}

bool PriceBreakout(const bool is_long)
{
   if(InpBreakoutLookback<1) return true;
   double close1=iClose(_Symbol,InpSignalTimeframe,1);
   if(is_long)
   {
      double level=RT_Highest(_Symbol,InpSignalTimeframe,2,InpBreakoutLookback);
      return level!=EMPTY_VALUE && close1>level;
   }
   double level=RT_Lowest(_Symbol,InpSignalTimeframe,2,InpBreakoutLookback);
   return level!=EMPTY_VALUE && close1<level;
}

bool DivergenceSignal(const bool is_long,const datetime signal_close)
{
   int lookback=MathMax(4,InpDivergenceLookback);
   double price1=(is_long ? iLow(_Symbol,InpSignalTimeframe,1) : iHigh(_Symbol,InpSignalTimeframe,1));
   double prior=(is_long ? RT_Lowest(_Symbol,InpSignalTimeframe,2,lookback)
                         : RT_Highest(_Symbol,InpSignalTimeframe,2,lookback));
   if(prior==EMPTY_VALUE) return false;
   bool price_extreme=(is_long ? price1<prior : price1>prior);
   if(!price_extreme) return false;

   int minutes=MathMax(5,InpFastCVDMinutes);
   double recent_delta,recent_volume,recent_vwap;
   double prior_delta,prior_volume,prior_vwap;
   if(!HybridStats(signal_close-minutes*60,signal_close,recent_delta,recent_volume,recent_vwap)) return false;
   if(!HybridStats(signal_close-2*minutes*60,signal_close-minutes*60,prior_delta,prior_volume,prior_vwap)) return false;
   double recent_ratio=recent_delta/recent_volume;
   double prior_ratio=prior_delta/prior_volume;
   if(is_long)
      return recent_ratio-prior_ratio>=InpDivergenceMinImprovement && iClose(_Symbol,InpSignalTimeframe,1)>iOpen(_Symbol,InpSignalTimeframe,1);
   return prior_ratio-recent_ratio>=InpDivergenceMinImprovement && iClose(_Symbol,InpSignalTimeframe,1)<iOpen(_Symbol,InpSignalTimeframe,1);
}

bool SelectOurPosition(ulong &ticket)
{
   for(int i=PositionsTotal()-1;i>=0;i--)
   {
      ticket=PositionGetTicket(i);
      if(ticket==0) continue;
      if(PositionGetString(POSITION_SYMBOL)==_Symbol && PositionGetInteger(POSITION_MAGIC)==InpMagic)
         return true;
   }
   ticket=0;
   return false;
}

void ManagePosition(const double atr)
{
   ulong ticket=0;
   if(!SelectOurPosition(ticket)) { g_initial_risk=0.0; return; }
   long type=PositionGetInteger(POSITION_TYPE);
   double open=PositionGetDouble(POSITION_PRICE_OPEN);
   double stop=PositionGetDouble(POSITION_SL);
   double target=PositionGetDouble(POSITION_TP);
   if(g_initial_risk<=0.0) g_initial_risk=MathAbs(open-stop);
   if(g_initial_risk<=0.0 || atr<=0.0) return;
   MqlTick tick;
   if(!SymbolInfoTick(_Symbol,tick)) return;
   double current=(type==POSITION_TYPE_BUY ? tick.bid : tick.ask);
   double profit_distance=(type==POSITION_TYPE_BUY ? current-open : open-current);
   double profit_r=profit_distance/g_initial_risk;
   double candidate=stop;

   if(profit_r>=InpBreakEvenAtR)
   {
      double locked=(type==POSITION_TYPE_BUY ? open+InpBreakEvenLockR*g_initial_risk
                                             : open-InpBreakEvenLockR*g_initial_risk);
      if(type==POSITION_TYPE_BUY) candidate=MathMax(candidate,locked);
      else if(candidate<=0.0) candidate=locked;
      else candidate=MathMin(candidate,locked);
   }
   if(InpTrailATR>0.0 && profit_r>=InpTrailStartR)
   {
      double trailing=(type==POSITION_TYPE_BUY ? current-InpTrailATR*atr : current+InpTrailATR*atr);
      if(type==POSITION_TYPE_BUY) candidate=MathMax(candidate,trailing);
      else if(candidate<=0.0) candidate=trailing;
      else candidate=MathMin(candidate,trailing);
   }
   candidate=RT_Price(_Symbol,candidate);
   bool valid=(type==POSITION_TYPE_BUY ? candidate<tick.bid && candidate>stop
                                       : candidate>tick.ask && (stop<=0.0 || candidate<stop));
   if(valid && !ResearchTrade.PositionModify(ticket,candidate,target))
      Print("Hybrid CVD stop update failed: ",ResearchTrade.ResultRetcodeDescription());
}

bool OpenTrade(const bool is_long,const double atr,const string comment)
{
   MqlTick tick;
   if(!SymbolInfoTick(_Symbol,tick)) return false;
   double entry=(is_long ? tick.ask : tick.bid);
   double stop=RT_Price(_Symbol,is_long ? entry-InpStopATR*atr : entry+InpStopATR*atr);
   double risk=MathAbs(entry-stop);
   if(risk<=0.0) return false;
   double target=RT_Price(_Symbol,is_long ? entry+InpRewardRisk*risk : entry-InpRewardRisk*risk);
   ENUM_ORDER_TYPE type=(is_long ? ORDER_TYPE_BUY : ORDER_TYPE_SELL);
   double lots=RT_LotsForRisk(_Symbol,type,entry,stop,InpRiskPercent);
   if(lots<=0.0) return false;
   bool ok=(is_long ? ResearchTrade.Buy(lots,_Symbol,0.0,stop,target,comment)
                    : ResearchTrade.Sell(lots,_Symbol,0.0,stop,target,comment));
   if(ok)
   {
      g_initial_risk=risk;
      g_trades_today++;
      return true;
   }
   Print("Hybrid CVD entry failed: ",ResearchTrade.ResultRetcodeDescription());
   return false;
}

int OnInit()
{
   if(InpFastEMAPeriod<2 || InpSlowEMAPeriod<=InpFastEMAPeriod || InpATRPeriod<2 ||
      InpStopATR<=0.0 || InpRewardRisk<=0.0 || InpFastCVDMinutes<5 || InpRiskPercent<=0.0)
      return INIT_PARAMETERS_INCORRECT;
   g_fast_ema=iMA(_Symbol,InpSignalTimeframe,InpFastEMAPeriod,0,MODE_EMA,PRICE_CLOSE);
   g_slow_ema=iMA(_Symbol,InpSignalTimeframe,InpSlowEMAPeriod,0,MODE_EMA,PRICE_CLOSE);
   g_atr=iATR(_Symbol,InpSignalTimeframe,InpATRPeriod);
   if(g_fast_ema==INVALID_HANDLE || g_slow_ema==INVALID_HANDLE || g_atr==INVALID_HANDLE)
      return INIT_FAILED;
   ResearchTrade.SetExpertMagicNumber((ulong)InpMagic);
   ResearchTrade.SetDeviationInPoints(InpMaxDeviationPoints);
   ResearchTrade.SetTypeFillingBySymbol(_Symbol);
   return INIT_SUCCEEDED;
}

void OnDeinit(const int reason)
{
   if(g_fast_ema!=INVALID_HANDLE) IndicatorRelease(g_fast_ema);
   if(g_slow_ema!=INVALID_HANDLE) IndicatorRelease(g_slow_ema);
   if(g_atr!=INVALID_HANDLE) IndicatorRelease(g_atr);
}

void OnTick()
{
   if(!RT_NewBar(_Symbol,InpSignalTimeframe,g_last_bar)) return;
   double atr=RT_Buffer(g_atr,0,1);
   if(atr==EMPTY_VALUE || atr<=0.0) return;
   ManagePosition(atr);

   datetime current_bar=iTime(_Symbol,InpSignalTimeframe,0);
   int date_key=UTCDateKey(current_bar);
   if(date_key!=g_trading_day)
   {
      g_trading_day=date_key;
      g_trades_today=0;
   }
   if(!InSession(current_bar))
   {
      if(InpFlatAtSessionEnd && RT_PositionCount(_Symbol,InpMagic)>0)
         RT_CloseAll(_Symbol,InpMagic,InpMaxDeviationPoints);
      return;
   }
   if(RT_PositionCount(_Symbol,InpMagic)>0 || g_trades_today>=InpMaximumTradesPerDay) return;

   MqlTick tick;
   if(!SymbolInfoTick(_Symbol,tick)) return;
   if(InpMaximumSpreadATR>0.0 && tick.ask-tick.bid>InpMaximumSpreadATR*atr) return;
   if(RelativeVolume(1)<InpMinRelativeVolume) return;

   datetime signal_close=current_bar;
   double fast_delta,fast_volume,unused_vwap;
   double session_delta,session_volume,session_vwap;
   if(!HybridStats(signal_close-InpFastCVDMinutes*60,signal_close,fast_delta,fast_volume,unused_vwap)) return;
   if(!HybridStats(SessionAnchor(signal_close),signal_close,session_delta,session_volume,session_vwap)) return;
   double fast_ratio=fast_delta/fast_volume;
   double session_ratio=session_delta/session_volume;
   double close1=iClose(_Symbol,InpSignalTimeframe,1);
   double fast_ema=RT_Buffer(g_fast_ema,0,1);
   double slow_ema=RT_Buffer(g_slow_ema,0,1);
   if(fast_ema==EMPTY_VALUE || slow_ema==EMPTY_VALUE) return;

   bool continuation_allowed=(InpSignalMode==CVD_TREND_CONTINUATION || InpSignalMode==CVD_BOTH_SETUPS);
   bool divergence_allowed=(InpSignalMode==CVD_DIVERGENCE_REVERSAL || InpSignalMode==CVD_BOTH_SETUPS);
   bool long_signal=false;
   bool short_signal=false;
   string long_comment="Hybrid CVD long";
   string short_comment="Hybrid CVD short";

   if(continuation_allowed)
   {
      long_signal=InpEnableLong && fast_ema>slow_ema && (!InpRequireVWAP || close1>session_vwap) &&
                  fast_ratio>=InpFastCVDMinRatio && session_ratio>=InpSessionCVDMinRatio && PriceBreakout(true);
      short_signal=InpEnableShort && fast_ema<slow_ema && (!InpRequireVWAP || close1<session_vwap) &&
                   fast_ratio<=-InpFastCVDMinRatio && session_ratio<=-InpSessionCVDMinRatio && PriceBreakout(false);
   }
   if(divergence_allowed && !long_signal && !short_signal)
   {
      long_signal=InpEnableLong && (!InpRequireVWAP || close1<session_vwap) && DivergenceSignal(true,signal_close);
      short_signal=InpEnableShort && (!InpRequireVWAP || close1>session_vwap) && DivergenceSignal(false,signal_close);
      long_comment="Hybrid CVD divergence long";
      short_comment="Hybrid CVD divergence short";
   }
   if(long_signal) OpenTrade(true,atr,long_comment);
   else if(short_signal) OpenTrade(false,atr,short_comment);
}
