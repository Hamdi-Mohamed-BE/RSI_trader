//+------------------------------------------------------------------+
//|                         POC Fibonacci Volume Profile EA.mq5       |
//| Completed-profile POC + Fibonacci confluence research EA.        |
//| Profiles use broker tick activity; no current-session leakage.   |
//+------------------------------------------------------------------+
#property strict
#property version   "1.00"
#property description "Completed volume-profile POC plus Fibonacci retracement confluence."

#include <Trade/Trade.mqh>

enum ENUM_POCFIB_CONFIRMATION
{
   POCFIB_RECLAIM=0,
   POCFIB_WICK_REJECTION=1,
   POCFIB_STRUCTURE_BREAK=2,
   POCFIB_STRONG_BODY=3
};

enum ENUM_POCFIB_STOP
{
   POCFIB_SIGNAL_STOP=0,
   POCFIB_ATR_STOP=1,
   POCFIB_SWING_STOP=2
};

enum ENUM_POCFIB_TRAIL
{
   POCFIB_NO_TRAIL=0,
   POCFIB_BREAK_EVEN=1,
   POCFIB_DYNAMIC_50_20=2,
   POCFIB_ATR_TRAIL=3,
   POCFIB_DYNAMIC_AND_ATR=4
};

enum ENUM_POCFIB_SESSION
{
   POCFIB_ALL_DAY=0,
   POCFIB_ASIA=1,
   POCFIB_LONDON=2,
   POCFIB_NEW_YORK=3,
   POCFIB_LONDON_NY_OVERLAP=4
};

input group "Completed profile and Fibonacci"
input ENUM_TIMEFRAMES           InpTimeframe=PERIOD_M15;
input ENUM_TIMEFRAMES           InpProfileTimeframe=PERIOD_M15;
input int                       InpProfileLookbackDays=1;
input int                       InpProfileLookbackBars=96;
input int                       InpProfileBins=64;
input double                    InpFibonacciRatio=0.618;
input double                    InpFibonacciToleranceATR=0.20;
input double                    InpPOCTouchToleranceATR=0.08;
input double                    InpMinimumProfileRangeATR=2.0;

input group "Direction and confirmation"
input ENUM_POCFIB_CONFIRMATION  InpConfirmation=POCFIB_STRUCTURE_BREAK;
input ENUM_TIMEFRAMES           InpTrendTimeframe=PERIOD_H1;
input int                       InpTrendEMAPeriod=50;
input double                    InpMinimumDepartureATR=0.75;
input int                       InpDepartureLookbackBars=16;
input double                    InpMinimumBodyATR=0.15;
input double                    InpMinimumCloseLocation=0.60;
input bool                      InpAllowLong=true;
input bool                      InpAllowShort=true;

input group "Stop, reward and management"
input ENUM_POCFIB_STOP          InpStopMode=POCFIB_SIGNAL_STOP;
input int                       InpSwingLookback=5;
input double                    InpStopATR=1.50;
input double                    InpStopBufferATR=0.10;
input double                    InpRewardRisk=1.50;
input ENUM_POCFIB_TRAIL         InpTrailingMode=POCFIB_NO_TRAIL;
input double                    InpBreakEvenAtR=1.00;
input double                    InpBreakEvenLockR=0.05;
input double                    InpDynamicTriggerR=0.50;
input double                    InpDynamicLockR=0.20;
input double                    InpATRTrailStartR=1.00;
input double                    InpATRTrailDistance=2.00;
input int                       InpMaximumHoldingBars=96;

input group "Session - broker server time"
input ENUM_POCFIB_SESSION       InpSession=POCFIB_ALL_DAY;
input int                       InpAsiaStartHour=0;
input int                       InpAsiaEndHour=7;
input int                       InpLondonStartHour=7;
input int                       InpLondonEndHour=13;
input int                       InpNewYorkStartHour=13;
input int                       InpNewYorkEndHour=21;
input int                       InpOverlapStartHour=13;
input int                       InpOverlapEndHour=16;

input group "Risk and execution"
input double                    InpRiskPercent=1.00;
input int                       InpMaximumTradesPerDay=2;
input double                    InpMaximumSpreadATR=0.20;
input ulong                     InpMagic=94041001;
input int                       InpMaximumDeviationPoints=80;

struct ProfileData
{
   bool valid;
   datetime fromTime;
   datetime toTime;
   double low;
   double high;
   double poc;
};

CTrade g_trade;
int g_atrHandle=INVALID_HANDLE;
int g_emaHandle=INVALID_HANDLE;
datetime g_lastBar=0;
int g_profileDay=0;
int g_tradeDay=0;
int g_tradesToday=0;
ProfileData g_profile;

double NormalizePrice(const double price)
{
   return NormalizeDouble(price,(int)SymbolInfoInteger(_Symbol,SYMBOL_DIGITS));
}

int DayKey(const datetime when)
{
   MqlDateTime value;
   TimeToStruct(when,value);
   return value.year*10000+value.mon*100+value.day;
}

bool HourAllowed(const int hour,const int startHour,const int endHour)
{
   if(startHour==endHour) return true;
   if(startHour<endHour) return hour>=startHour && hour<endHour;
   return hour>=startHour || hour<endHour;
}

bool SessionAllows(const datetime when)
{
   if(InpSession==POCFIB_ALL_DAY) return true;
   MqlDateTime value;
   TimeToStruct(when,value);
   if(InpSession==POCFIB_ASIA) return HourAllowed(value.hour,InpAsiaStartHour,InpAsiaEndHour);
   if(InpSession==POCFIB_LONDON) return HourAllowed(value.hour,InpLondonStartHour,InpLondonEndHour);
   if(InpSession==POCFIB_NEW_YORK) return HourAllowed(value.hour,InpNewYorkStartHour,InpNewYorkEndHour);
   return HourAllowed(value.hour,InpOverlapStartHour,InpOverlapEndHour);
}

double Activity(const MqlRates &bar)
{
   if(bar.real_volume>0) return (double)bar.real_volume;
   return (double)bar.tick_volume;
}

bool ReadATR(const int shift,double &value)
{
   double buffer[1];
   if(g_atrHandle==INVALID_HANDLE || CopyBuffer(g_atrHandle,0,shift,1,buffer)!=1) return false;
   value=buffer[0];
   return value>0.0;
}

bool ReadTrendEMA(double &value)
{
   double buffer[1];
   if(g_emaHandle==INVALID_HANDLE || CopyBuffer(g_emaHandle,0,1,1,buffer)!=1) return false;
   value=buffer[0];
   return value>0.0;
}

void ResetProfile()
{
   g_profile.valid=false;
   g_profile.fromTime=0;
   g_profile.toTime=0;
   g_profile.low=0.0;
   g_profile.high=0.0;
   g_profile.poc=0.0;
}

bool BuildCompletedProfile()
{
   ResetProfile();
   MqlRates bars[];
   int copied=0;
   datetime fromTime=0;
   datetime toTime=0;
   if(InpProfileLookbackBars>0)
   {
      copied=CopyRates(_Symbol,InpProfileTimeframe,1,MathMax(16,InpProfileLookbackBars),bars);
      if(copied>0)
      {
         fromTime=bars[0].time;
         toTime=bars[copied-1].time+PeriodSeconds(InpProfileTimeframe);
      }
   }
   else
   {
      int days=MathMax(1,InpProfileLookbackDays);
      fromTime=iTime(_Symbol,PERIOD_D1,days);
      toTime=iTime(_Symbol,PERIOD_D1,0);
      if(fromTime<=0 || toTime<=fromTime) return false;
      copied=CopyRates(_Symbol,InpProfileTimeframe,fromTime,toTime-1,bars);
   }
   if(copied<8) return false;
   double low=DBL_MAX;
   double high=-DBL_MAX;
   double total=0.0;
   for(int index=0;index<copied;index++)
   {
      low=MathMin(low,bars[index].low);
      high=MathMax(high,bars[index].high);
      total+=Activity(bars[index]);
   }
   if(high<=low || total<=0.0) return false;

   int bins=MathMax(16,InpProfileBins);
   double step=(high-low)/(double)bins;
   if(step<=0.0) return false;
   double volume[];
   ArrayResize(volume,bins);
   ArrayInitialize(volume,0.0);
   for(int index=0;index<copied;index++)
   {
      int first=(int)MathFloor((bars[index].low-low)/step);
      int last=(int)MathFloor((bars[index].high-low)/step);
      first=MathMax(0,MathMin(bins-1,first));
      last=MathMax(0,MathMin(bins-1,last));
      if(last<first){int swap=first;first=last;last=swap;}
      int touched=MathMax(1,last-first+1);
      double share=Activity(bars[index])/(double)touched;
      for(int bin=first;bin<=last;bin++) volume[bin]+=share;
   }
   int pocBin=0;
   for(int bin=1;bin<bins;bin++) if(volume[bin]>volume[pocBin]) pocBin=bin;
   g_profile.valid=true;
   g_profile.fromTime=fromTime;
   g_profile.toTime=toTime;
   g_profile.low=low;
   g_profile.high=high;
   g_profile.poc=NormalizePrice(low+((double)pocBin+0.5)*step);
   return true;
}

bool ProfileConfluence(const int direction,const double atr,double &fibPrice)
{
   if(!g_profile.valid || atr<=0.0) return false;
   double range=g_profile.high-g_profile.low;
   if(range<InpMinimumProfileRangeATR*atr) return false;
   double ratio=MathMax(0.10,MathMin(0.90,InpFibonacciRatio));
   fibPrice=direction>0 ? g_profile.high-ratio*range : g_profile.low+ratio*range;
   return MathAbs(g_profile.poc-fibPrice)<=InpFibonacciToleranceATR*atr;
}

bool SpreadPasses(const double atr)
{
   if(InpMaximumSpreadATR<=0.0) return true;
   MqlTick tick;
   if(!SymbolInfoTick(_Symbol,tick)) return false;
   return tick.ask-tick.bid<=InpMaximumSpreadATR*atr;
}

bool SelectOurPosition(ulong &ticket)
{
   ticket=0;
   for(int index=PositionsTotal()-1;index>=0;index--)
   {
      ulong candidate=PositionGetTicket(index);
      if(candidate==0 || !PositionSelectByTicket(candidate)) continue;
      if(PositionGetString(POSITION_SYMBOL)==_Symbol && (ulong)PositionGetInteger(POSITION_MAGIC)==InpMagic)
      {ticket=candidate;return true;}
   }
   return false;
}

bool ConfirmationPasses(const MqlRates &signal,const MqlRates &previous,const int direction,const double atr)
{
   double tolerance=InpPOCTouchToleranceATR*atr;
   bool touched=signal.low<=g_profile.poc+tolerance && signal.high>=g_profile.poc-tolerance;
   if(!touched) return false;
   bool directional=direction>0 ? signal.close>signal.open : signal.close<signal.open;
   if(!directional) return false;
   double range=MathMax(signal.high-signal.low,_Point);
   double body=MathAbs(signal.close-signal.open);
   double closeLocation=direction>0 ? (signal.close-signal.low)/range : (signal.high-signal.close)/range;
   bool reclaim=direction>0 ? signal.close>=g_profile.poc : signal.close<=g_profile.poc;
   bool wick=false;
   if(direction>0) wick=MathMin(signal.open,signal.close)-signal.low>=MathMax(body,0.05*atr);
   else wick=signal.high-MathMax(signal.open,signal.close)>=MathMax(body,0.05*atr);
   bool structure=direction>0 ? signal.close>previous.high : signal.close<previous.low;
   bool strong=body>=InpMinimumBodyATR*atr && closeLocation>=InpMinimumCloseLocation;
   if(InpConfirmation==POCFIB_RECLAIM) return reclaim;
   if(InpConfirmation==POCFIB_WICK_REJECTION) return reclaim && wick;
   if(InpConfirmation==POCFIB_STRUCTURE_BREAK) return reclaim && structure;
   return reclaim && strong;
}

bool DeparturePasses(const MqlRates &rates[],const int direction,const double atr)
{
   int count=MathMin(ArraySize(rates)-1,MathMax(3,InpDepartureLookbackBars));
   for(int index=2;index<=count;index++)
   {
      if(direction>0 && rates[index].high>=g_profile.poc+InpMinimumDepartureATR*atr) return true;
      if(direction<0 && rates[index].low<=g_profile.poc-InpMinimumDepartureATR*atr) return true;
   }
   return false;
}

double StopPrice(const MqlRates &rates[],const int direction,const double entry,const double atr)
{
   double stop=0.0;
   if(InpStopMode==POCFIB_SIGNAL_STOP)
      stop=direction>0 ? rates[1].low-InpStopBufferATR*atr : rates[1].high+InpStopBufferATR*atr;
   else if(InpStopMode==POCFIB_ATR_STOP)
      stop=direction>0 ? entry-InpStopATR*atr : entry+InpStopATR*atr;
   else
   {
      int count=MathMin(ArraySize(rates)-1,MathMax(2,InpSwingLookback));
      stop=direction>0 ? rates[1].low : rates[1].high;
      for(int index=2;index<=count;index++)
         stop=direction>0 ? MathMin(stop,rates[index].low) : MathMax(stop,rates[index].high);
      stop+=direction>0 ? -InpStopBufferATR*atr : InpStopBufferATR*atr;
   }
   double minimum=(double)SymbolInfoInteger(_Symbol,SYMBOL_TRADE_STOPS_LEVEL)*_Point;
   if(direction>0 && entry-stop<minimum) stop=entry-minimum;
   if(direction<0 && stop-entry<minimum) stop=entry+minimum;
   return NormalizePrice(stop);
}

double LotsForRisk(const ENUM_ORDER_TYPE type,const double entry,const double stop)
{
   double riskCash=AccountInfoDouble(ACCOUNT_BALANCE)*InpRiskPercent/100.0;
   if(riskCash<=0.0) return 0.0;
   double loss=0.0;
   if(!OrderCalcProfit(type,_Symbol,1.0,entry,stop,loss)) return 0.0;
   loss=MathAbs(loss);
   if(loss<=0.0) return 0.0;
   double step=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_STEP);
   double minimum=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MIN);
   double maximum=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MAX);
   if(step<=0.0) step=minimum;
   double lots=MathFloor((riskCash/loss)/step)*step;
   lots=MathMax(minimum,MathMin(maximum,lots));
   int digits=step>=1.0 ? 0 : step>=0.1 ? 1 : step>=0.01 ? 2 : 3;
   return NormalizeDouble(lots,digits);
}

bool OpenSignal(const MqlRates &rates[],const int direction,const double atr,const double fibPrice)
{
   MqlTick tick;
   if(!SymbolInfoTick(_Symbol,tick)) return false;
   double entry=direction>0 ? tick.ask : tick.bid;
   double stop=StopPrice(rates,direction,entry,atr);
   double risk=MathAbs(entry-stop);
   if(risk<=0.0) return false;
   double target=NormalizePrice(direction>0 ? entry+InpRewardRisk*risk : entry-InpRewardRisk*risk);
   ENUM_ORDER_TYPE type=direction>0 ? ORDER_TYPE_BUY : ORDER_TYPE_SELL;
   double lots=LotsForRisk(type,entry,stop);
   if(lots<=0.0) return false;
   string note="POCFIB "+DoubleToString(InpFibonacciRatio,3)+" "+DoubleToString(fibPrice,_Digits);
   bool placed=direction>0 ? g_trade.Buy(lots,_Symbol,0.0,stop,target,note) : g_trade.Sell(lots,_Symbol,0.0,stop,target,note);
   if(placed) g_tradesToday++;
   return placed;
}

void ManagePosition(const MqlRates &rates[],const double atr)
{
   ulong ticket=0;
   if(!SelectOurPosition(ticket)) return;
   int direction=PositionGetInteger(POSITION_TYPE)==POSITION_TYPE_BUY ? 1 : -1;
   double entry=PositionGetDouble(POSITION_PRICE_OPEN);
   double currentStop=PositionGetDouble(POSITION_SL);
   double target=PositionGetDouble(POSITION_TP);
   double initialRisk=InpRewardRisk>0.0 ? MathAbs(target-entry)/InpRewardRisk : MathAbs(entry-currentStop);
   if(initialRisk<=0.0) return;
   double progress=direction>0 ? rates[1].close-entry : entry-rates[1].close;
   double proposed=currentStop;
   if(InpTrailingMode==POCFIB_BREAK_EVEN && progress>=InpBreakEvenAtR*initialRisk)
      proposed=entry+direction*InpBreakEvenLockR*initialRisk;
   if((InpTrailingMode==POCFIB_DYNAMIC_50_20 || InpTrailingMode==POCFIB_DYNAMIC_AND_ATR) && progress>=InpDynamicTriggerR*initialRisk)
      proposed=entry+direction*InpDynamicLockR*initialRisk;
   if((InpTrailingMode==POCFIB_ATR_TRAIL || InpTrailingMode==POCFIB_DYNAMIC_AND_ATR) && progress>=InpATRTrailStartR*initialRisk)
   {
      double trail=rates[1].close-direction*InpATRTrailDistance*atr;
      proposed=direction>0 ? MathMax(proposed,trail) : MathMin(proposed,trail);
   }
   bool improves=direction>0 ? proposed>currentStop+_Point && proposed<rates[1].close : (currentStop<=0.0 || proposed<currentStop-_Point) && proposed>rates[1].close;
   if(improves) g_trade.PositionModify(ticket,NormalizePrice(proposed),target);
   if(InpMaximumHoldingBars>0)
   {
      datetime opened=(datetime)PositionGetInteger(POSITION_TIME);
      int seconds=PeriodSeconds(InpTimeframe);
      if(seconds>0 && (rates[1].time-opened)/seconds>=InpMaximumHoldingBars) g_trade.PositionClose(ticket);
   }
}

void ProcessBar()
{
   int required=MathMax(InpDepartureLookbackBars+4,InpSwingLookback+4);
   MqlRates rates[];
   ArraySetAsSeries(rates,true);
   if(CopyRates(_Symbol,InpTimeframe,0,required,rates)<required) return;
   double atr=0.0;
   if(!ReadATR(1,atr)) return;

   int day=DayKey(rates[1].time);
   if(day!=g_tradeDay){g_tradeDay=day;g_tradesToday=0;}
   if(InpProfileLookbackBars>0) BuildCompletedProfile();
   else if(day!=g_profileDay){g_profileDay=day;BuildCompletedProfile();}

   ManagePosition(rates,atr);
   ulong ticket=0;
   if(SelectOurPosition(ticket)) return;
   if(!g_profile.valid || g_tradesToday>=InpMaximumTradesPerDay || !SessionAllows(rates[1].time) || !SpreadPasses(atr)) return;

   double ema=0.0;
   if(!ReadTrendEMA(ema)) return;
   double trendClose=iClose(_Symbol,InpTrendTimeframe,1);
   int candidates[2]={1,-1};
   for(int index=0;index<2;index++)
   {
      int direction=candidates[index];
      if(direction>0 && (!InpAllowLong || trendClose<=ema)) continue;
      if(direction<0 && (!InpAllowShort || trendClose>=ema)) continue;
      double fibPrice=0.0;
      if(!ProfileConfluence(direction,atr,fibPrice)) continue;
      if(!DeparturePasses(rates,direction,atr)) continue;
      if(!ConfirmationPasses(rates[1],rates[2],direction,atr)) continue;
      OpenSignal(rates,direction,atr,fibPrice);
      break;
   }
}

int OnInit()
{
   if(InpRiskPercent<=0.0 || InpRewardRisk<0.5 || InpProfileBins<16 || InpTrendEMAPeriod<2) return INIT_PARAMETERS_INCORRECT;
   g_atrHandle=iATR(_Symbol,InpTimeframe,14);
   g_emaHandle=iMA(_Symbol,InpTrendTimeframe,InpTrendEMAPeriod,0,MODE_EMA,PRICE_CLOSE);
   if(g_atrHandle==INVALID_HANDLE || g_emaHandle==INVALID_HANDLE) return INIT_FAILED;
   g_trade.SetExpertMagicNumber(InpMagic);
   g_trade.SetDeviationInPoints(InpMaximumDeviationPoints);
   g_trade.SetTypeFillingBySymbol(_Symbol);
   return INIT_SUCCEEDED;
}

void OnDeinit(const int reason)
{
   if(g_atrHandle!=INVALID_HANDLE) IndicatorRelease(g_atrHandle);
   if(g_emaHandle!=INVALID_HANDLE) IndicatorRelease(g_emaHandle);
}

void OnTick()
{
   datetime current=iTime(_Symbol,InpTimeframe,0);
   if(current<=0 || current==g_lastBar) return;
   g_lastBar=current;
   ProcessBar();
}

double OnTester()
{
   double profit=TesterStatistics(STAT_PROFIT);
   double initial=TesterStatistics(STAT_INITIAL_DEPOSIT);
   double pf=TesterStatistics(STAT_PROFIT_FACTOR);
   double dd=TesterStatistics(STAT_EQUITY_DDREL_PERCENT);
   double trades=TesterStatistics(STAT_TRADES);
   if(initial<=0.0 || trades<30.0 || pf<=0.0) return -1000000.0+profit;
   double returnPct=100.0*profit/initial;
   return returnPct*MathSqrt(MathMin(trades,150.0)/150.0)*MathMin(pf,3.0)/(1.0+MathMax(dd,0.0));
}
