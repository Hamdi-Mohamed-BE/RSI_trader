#property copyright "HAMA Algo Systems - LVN research"
#property version   "1.00"
#property strict

#include <Trade/Trade.mqh>

enum ENUM_LVN_ENTRY_MODE
{
   LVN_RAW_TOUCH=0,
   LVN_CONFIRMED_BREAKOUT=1,
   LVN_CONFIRMED_BOUNCE=2,
   LVN_BREAKOUT_RETEST=3,
   LVN_CONFIRMED_AUTO=4
};

enum ENUM_LVN_STOP_MODE
{
   LVN_SIGNAL_CANDLE_STOP=0,
   LVN_ATR_STOP=1,
   LVN_SWING_STOP=2
};

enum ENUM_LVN_TRAIL_MODE
{
   LVN_NO_TRAILING=0,
   LVN_BREAK_EVEN=1,
   LVN_DYNAMIC_50_20=2,
   LVN_ATR_TRAILING=3,
   LVN_DYNAMIC_AND_ATR=4
};

enum ENUM_LVN_SESSION
{
   LVN_ALL_DAY=0,
   LVN_ASIA=1,
   LVN_LONDON=2,
   LVN_NEW_YORK=3,
   LVN_LONDON_NEW_YORK_OVERLAP=4
};

input group "Signal and composite profile"
input ENUM_TIMEFRAMES InpTimeframe=PERIOD_M15;
input ENUM_LVN_ENTRY_MODE InpEntryMode=LVN_CONFIRMED_AUTO;
input int InpATRPeriod=14;
input int InpProfileLookbackDays=10;
input int InpProfileBins=64;
input double InpMaximumLVNMeanRatio=0.55;
input double InpMinimumNeighborRatio=1.35;
input double InpLevelToleranceATR=0.08;
input int InpRetestMaximumBars=8;

input group "15-minute confirmation"
input double InpMinimumBodyATR=0.20;
input int InpVolumeAverageBars=20;
input double InpMinimumVolumeRatio=1.00;
input double InpMinimumCloseLocation=0.65;

input group "Risk and exits"
input ENUM_LVN_STOP_MODE InpStopMode=LVN_SIGNAL_CANDLE_STOP;
input int InpSwingLookback=5;
input double InpStopATR=1.50;
input double InpStopBufferATR=0.10;
input double InpRewardRisk=1.50;
input ENUM_LVN_TRAIL_MODE InpTrailingMode=LVN_NO_TRAILING;
input double InpBreakEvenAtR=1.00;
input double InpBreakEvenLockR=0.05;
input double InpDynamicTriggerR=0.50;
input double InpDynamicLockR=0.20;
input double InpATRTrailStartR=1.00;
input double InpATRTrailDistance=2.00;
input int InpMaximumHoldingBars=96;

input group "Trading controls"
input ENUM_LVN_SESSION InpSession=LVN_ALL_DAY;
input bool InpAllowLong=true;
input bool InpAllowShort=true;
input int InpMaximumTradesPerDay=2;
input double InpRiskPercent=1.00;
input double InpMaximumSpreadATR=0.20;
input long InpMagic=94040901;
input int InpMaximumDeviationPoints=80;

CTrade g_trade;
int g_atrHandle=INVALID_HANDLE;
datetime g_lastBar=0;
int g_profileDay=-1;
int g_tradeDay=-1;
int g_tradesToday=0;
double g_profileLow=0.0;
double g_profileStep=0.0;
double g_profileMean=0.0;
double g_profile[];
bool g_profileReady=false;
bool g_retestActive=false;
int g_retestDirection=0;
int g_retestAge=0;
double g_retestLevel=0.0;

int DayKey(const datetime when)
{
   MqlDateTime value;
   TimeToStruct(when,value);
   return value.year*1000+value.day_of_year;
}

double NormalizePrice(const double price)
{
   return NormalizeDouble(price,(int)SymbolInfoInteger(_Symbol,SYMBOL_DIGITS));
}

double NormalizeLots(const double raw)
{
   double minimum=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MIN);
   double maximum=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MAX);
   double step=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_STEP);
   if(step<=0.0 || raw<minimum) return 0.0;
   double lots=MathFloor(raw/step+1e-9)*step;
   if(lots<minimum) return 0.0;
   return MathMin(lots,maximum);
}

double LotsForRisk(const ENUM_ORDER_TYPE type,const double entry,const double stop)
{
   double cash=AccountInfoDouble(ACCOUNT_EQUITY)*InpRiskPercent/100.0;
   double oneLot=0.0;
   if(cash<=0.0 || !OrderCalcProfit(type,_Symbol,1.0,entry,stop,oneLot)) return 0.0;
   oneLot=MathAbs(oneLot);
   if(oneLot<=0.0) return 0.0;
   return NormalizeLots(cash/oneLot);
}

bool ReadATR(const int shift,double &atr)
{
   double values[];
   if(g_atrHandle==INVALID_HANDLE || CopyBuffer(g_atrHandle,0,shift,1,values)!=1) return false;
   atr=values[0];
   return atr>0.0;
}

bool SessionAllows(const datetime when)
{
   if(InpSession==LVN_ALL_DAY) return true;
   MqlDateTime value;
   TimeToStruct(when,value);
   int hour=value.hour;
   if(InpSession==LVN_ASIA) return hour>=0 && hour<8;
   if(InpSession==LVN_LONDON) return hour>=7 && hour<16;
   if(InpSession==LVN_NEW_YORK) return hour>=13 && hour<21;
   return hour>=13 && hour<16;
}

bool SelectOurPosition(ulong &ticket)
{
   for(int index=PositionsTotal()-1;index>=0;index--)
   {
      ulong candidate=PositionGetTicket(index);
      if(candidate>0 && PositionGetString(POSITION_SYMBOL)==_Symbol && PositionGetInteger(POSITION_MAGIC)==InpMagic)
      {
         ticket=candidate;
         return true;
      }
   }
   ticket=0;
   return false;
}

string RiskKey(const ulong identifier)
{
   return "LVN."+(string)InpMagic+"."+(string)identifier+".R";
}

void StoreInitialRisk()
{
   ulong ticket=0;
   if(!SelectOurPosition(ticket)) return;
   ulong identifier=(ulong)PositionGetInteger(POSITION_IDENTIFIER);
   double risk=MathAbs(PositionGetDouble(POSITION_PRICE_OPEN)-PositionGetDouble(POSITION_SL));
   if(identifier>0 && risk>0.0) GlobalVariableSet(RiskKey(identifier),risk);
}

double InitialRisk()
{
   ulong identifier=(ulong)PositionGetInteger(POSITION_IDENTIFIER);
   string key=RiskKey(identifier);
   if(identifier>0 && GlobalVariableCheck(key)) return GlobalVariableGet(key);
   return MathAbs(PositionGetDouble(POSITION_PRICE_OPEN)-PositionGetDouble(POSITION_SL));
}

bool BuildCompositeProfile()
{
   int bars=MathMax(96,InpProfileLookbackDays*96);
   MqlRates rates[];
   ArraySetAsSeries(rates,true);
   int copied=CopyRates(_Symbol,InpTimeframe,2,bars,rates);
   if(copied<96) return false;

   double low=rates[0].low;
   double high=rates[0].high;
   for(int index=1;index<copied;index++)
   {
      low=MathMin(low,rates[index].low);
      high=MathMax(high,rates[index].high);
   }
   int binCount=MathMax(16,InpProfileBins);
   double step=(high-low)/binCount;
   if(step<=0.0) return false;

   ArrayResize(g_profile,binCount);
   ArrayInitialize(g_profile,0.0);
   double total=0.0;
   for(int bar=0;bar<copied;bar++)
   {
      int first=(int)MathFloor((rates[bar].low-low)/step);
      int last=(int)MathFloor((rates[bar].high-low)/step);
      first=MathMax(0,MathMin(binCount-1,first));
      last=MathMax(first,MathMin(binCount-1,last));
      int touched=last-first+1;
      double volume=(double)rates[bar].tick_volume;
      double share=touched>0 ? volume/touched : volume;
      for(int bin=first;bin<=last;bin++) g_profile[bin]+=share;
      total+=volume;
   }
   if(total<=0.0) return false;
   g_profileLow=low;
   g_profileStep=step;
   g_profileMean=total/binCount;
   g_profileReady=true;
   return true;
}

bool IsLVN(const int index)
{
   int count=ArraySize(g_profile);
   if(index<=0 || index>=count-1 || g_profileMean<=0.0) return false;
   double current=g_profile[index];
   if(current>g_profileMean*InpMaximumLVNMeanRatio) return false;
   double neighbor=(g_profile[index-1]+g_profile[index+1])/2.0;
   if(neighbor<g_profileMean*0.15) return false;
   return neighbor>=MathMax(current*InpMinimumNeighborRatio,1.0);
}

double AverageVolume(const MqlRates &rates[],const int start,const int count)
{
   double total=0.0;
   int available=ArraySize(rates);
   int used=0;
   for(int index=start;index<start+count && index<available;index++)
   {
      total+=(double)rates[index].tick_volume;
      used++;
   }
   return used>0 ? total/used : 0.0;
}

bool ConfirmationPasses(const MqlRates &bar,const int direction,const double atr,const double averageVolume)
{
   double range=bar.high-bar.low;
   double body=MathAbs(bar.close-bar.open);
   if(range<=0.0 || body<InpMinimumBodyATR*atr) return false;
   if(averageVolume>0.0 && (double)bar.tick_volume<averageVolume*InpMinimumVolumeRatio) return false;
   double location=direction>0 ? (bar.close-bar.low)/range : (bar.high-bar.close)/range;
   return location>=InpMinimumCloseLocation;
}

bool BreakoutAtLevel(const MqlRates &signal,const MqlRates &previous,const double level,const double tolerance,int &direction)
{
   if(previous.close<=level && signal.close>level+tolerance && signal.close>signal.open)
   {
      direction=1;
      return true;
   }
   if(previous.close>=level && signal.close<level-tolerance && signal.close<signal.open)
   {
      direction=-1;
      return true;
   }
   return false;
}

bool BounceAtLevel(const MqlRates &signal,const MqlRates &previous,const double level,const double tolerance,int &direction)
{
   if(previous.close>=level && signal.low<=level && signal.close>level+tolerance && signal.close>signal.open)
   {
      direction=1;
      return true;
   }
   if(previous.close<=level && signal.high>=level && signal.close<level-tolerance && signal.close<signal.open)
   {
      direction=-1;
      return true;
   }
   return false;
}

bool RetestSignal(const MqlRates &signal,const double tolerance,const double atr,const double averageVolume,int &direction,double &level)
{
   if(!g_retestActive) return false;
   g_retestAge++;
   if(g_retestAge>InpRetestMaximumBars)
   {
      g_retestActive=false;
      return false;
   }
   int candidate=g_retestDirection;
   bool touched=(candidate>0 ? signal.low<=g_retestLevel+tolerance : signal.high>=g_retestLevel-tolerance);
   bool held=(candidate>0 ? signal.close>g_retestLevel+tolerance && signal.close>signal.open : signal.close<g_retestLevel-tolerance && signal.close<signal.open);
   if(!touched || !held || !ConfirmationPasses(signal,candidate,atr,averageVolume)) return false;
   direction=candidate;
   level=g_retestLevel;
   g_retestActive=false;
   return true;
}

bool FindSignal(const MqlRates &rates[],const double atr,int &direction,double &level,string &label)
{
   if(!g_profileReady) return false;
   MqlRates signal=rates[1];
   MqlRates previous=rates[2];
   double tolerance=InpLevelToleranceATR*atr;
   double averageVolume=AverageVolume(rates,2,InpVolumeAverageBars);

   if(InpEntryMode==LVN_BREAKOUT_RETEST && RetestSignal(signal,tolerance,atr,averageVolume,direction,level))
   {
      label="retest";
      return (direction>0 ? InpAllowLong : InpAllowShort);
   }

   double bestDistance=DBL_MAX;
   int bestDirection=0;
   double bestLevel=0.0;
   string bestLabel="";
   int count=ArraySize(g_profile);
   for(int bin=1;bin<count-1;bin++)
   {
      if(!IsLVN(bin)) continue;
      double candidateLevel=g_profileLow+(bin+0.5)*g_profileStep;
      if(candidateLevel<signal.low-tolerance || candidateLevel>signal.high+tolerance)
      {
         bool crossed=(MathMin(previous.close,signal.close)<=candidateLevel && MathMax(previous.close,signal.close)>=candidateLevel);
         if(!crossed) continue;
      }

      int candidateDirection=0;
      string candidateLabel="";
      bool valid=false;
      if(InpEntryMode==LVN_RAW_TOUCH)
      {
         if(signal.low<=candidateLevel+tolerance && signal.high>=candidateLevel-tolerance)
         {
            candidateDirection=signal.close>=signal.open ? 1 : -1;
            candidateLabel="raw";
            valid=true;
         }
      }
      else
      {
         int breakoutDirection=0;
         int bounceDirection=0;
         bool breakout=BreakoutAtLevel(signal,previous,candidateLevel,tolerance,breakoutDirection);
         bool bounce=BounceAtLevel(signal,previous,candidateLevel,tolerance,bounceDirection);
         if(InpEntryMode==LVN_BREAKOUT_RETEST && breakout && ConfirmationPasses(signal,breakoutDirection,atr,averageVolume))
         {
            g_retestActive=true;
            g_retestDirection=breakoutDirection;
            g_retestAge=0;
            g_retestLevel=candidateLevel;
            continue;
         }
         if((InpEntryMode==LVN_CONFIRMED_BREAKOUT || InpEntryMode==LVN_CONFIRMED_AUTO) && breakout)
         {
            candidateDirection=breakoutDirection;
            candidateLabel="breakout";
            valid=ConfirmationPasses(signal,candidateDirection,atr,averageVolume);
         }
         if(!valid && (InpEntryMode==LVN_CONFIRMED_BOUNCE || InpEntryMode==LVN_CONFIRMED_AUTO) && bounce)
         {
            candidateDirection=bounceDirection;
            candidateLabel="bounce";
            valid=ConfirmationPasses(signal,candidateDirection,atr,averageVolume);
         }
      }
      if(!valid) continue;
      if((candidateDirection>0 && !InpAllowLong) || (candidateDirection<0 && !InpAllowShort)) continue;
      double distance=MathAbs(signal.close-candidateLevel);
      if(distance<bestDistance)
      {
         bestDistance=distance;
         bestDirection=candidateDirection;
         bestLevel=candidateLevel;
         bestLabel=candidateLabel;
      }
   }
   if(bestDirection==0) return false;
   direction=bestDirection;
   level=bestLevel;
   label=bestLabel;
   return true;
}

double StopPrice(const MqlRates &rates[],const int direction,const double entry,const double atr)
{
   double stop=0.0;
   if(InpStopMode==LVN_SIGNAL_CANDLE_STOP)
      stop=(direction>0 ? rates[1].low-InpStopBufferATR*atr : rates[1].high+InpStopBufferATR*atr);
   else if(InpStopMode==LVN_ATR_STOP)
      stop=(direction>0 ? entry-InpStopATR*atr : entry+InpStopATR*atr);
   else
   {
      int count=MathMin(ArraySize(rates)-1,MathMax(2,InpSwingLookback));
      stop=(direction>0 ? rates[1].low : rates[1].high);
      for(int index=2;index<=count;index++) stop=(direction>0 ? MathMin(stop,rates[index].low) : MathMax(stop,rates[index].high));
      stop+=(direction>0 ? -InpStopBufferATR*atr : InpStopBufferATR*atr);
   }
   double minimum=(double)SymbolInfoInteger(_Symbol,SYMBOL_TRADE_STOPS_LEVEL)*_Point;
   if(direction>0 && entry-stop<minimum) stop=entry-minimum;
   if(direction<0 && stop-entry<minimum) stop=entry+minimum;
   return NormalizePrice(stop);
}

bool SpreadPasses(const double atr)
{
   if(InpMaximumSpreadATR<=0.0) return true;
   MqlTick tick;
   if(!SymbolInfoTick(_Symbol,tick)) return false;
   return tick.ask-tick.bid<=InpMaximumSpreadATR*atr;
}

bool OpenSignal(const MqlRates &rates[],const int direction,const double atr,const string label)
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
   g_trade.SetExpertMagicNumber(InpMagic);
   g_trade.SetDeviationInPoints(InpMaximumDeviationPoints);
   bool placed=direction>0 ? g_trade.Buy(lots,_Symbol,0.0,stop,target,"LVN "+label) : g_trade.Sell(lots,_Symbol,0.0,stop,target,"LVN "+label);
   if(placed)
   {
      StoreInitialRisk();
      g_tradesToday++;
   }
   return placed;
}

void ManagePosition(const MqlRates &rates[],const double atr)
{
   ulong ticket=0;
   if(!SelectOurPosition(ticket)) return;
   long type=PositionGetInteger(POSITION_TYPE);
   int direction=type==POSITION_TYPE_BUY ? 1 : -1;
   double entry=PositionGetDouble(POSITION_PRICE_OPEN);
   double currentStop=PositionGetDouble(POSITION_SL);
   double target=PositionGetDouble(POSITION_TP);
   double risk=InitialRisk();
   if(risk<=0.0) return;
   double progress=direction>0 ? rates[1].close-entry : entry-rates[1].close;
   double proposed=currentStop;

   if(InpTrailingMode==LVN_BREAK_EVEN && progress>=InpBreakEvenAtR*risk)
      proposed=entry+direction*InpBreakEvenLockR*risk;
   if((InpTrailingMode==LVN_DYNAMIC_50_20 || InpTrailingMode==LVN_DYNAMIC_AND_ATR) && progress>=InpDynamicTriggerR*risk)
      proposed=entry+direction*InpDynamicLockR*risk;
   if((InpTrailingMode==LVN_ATR_TRAILING || InpTrailingMode==LVN_DYNAMIC_AND_ATR) && progress>=InpATRTrailStartR*risk)
   {
      double trail=rates[1].close-direction*InpATRTrailDistance*atr;
      if(direction>0) proposed=MathMax(proposed,trail); else proposed=MathMin(proposed,trail);
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
   int required=MathMax(InpVolumeAverageBars+4,InpSwingLookback+4);
   MqlRates rates[];
   ArraySetAsSeries(rates,true);
   if(CopyRates(_Symbol,InpTimeframe,0,required,rates)<required) return;
   double atr=0.0;
   if(!ReadATR(1,atr)) return;

   int day=DayKey(rates[1].time);
   if(day!=g_tradeDay)
   {
      g_tradeDay=day;
      g_tradesToday=0;
      g_retestActive=false;
   }
   if(day!=g_profileDay)
   {
      g_profileDay=day;
      g_profileReady=false;
      BuildCompositeProfile();
   }

   ManagePosition(rates,atr);
   ulong ticket=0;
   if(SelectOurPosition(ticket)) return;
   if(!g_profileReady || g_tradesToday>=InpMaximumTradesPerDay || !SessionAllows(rates[1].time) || !SpreadPasses(atr)) return;

   int direction=0;
   double level=0.0;
   string label="";
   if(FindSignal(rates,atr,direction,level,label)) OpenSignal(rates,direction,atr,label);
}

int OnInit()
{
   if(InpTimeframe!=PERIOD_M15)
      Print("LVN research is designed for completed M15 confirmation bars.");
   g_atrHandle=iATR(_Symbol,InpTimeframe,InpATRPeriod);
   if(g_atrHandle==INVALID_HANDLE) return INIT_FAILED;
   g_trade.SetExpertMagicNumber(InpMagic);
   return INIT_SUCCEEDED;
}

void OnDeinit(const int reason)
{
   if(g_atrHandle!=INVALID_HANDLE) IndicatorRelease(g_atrHandle);
}

void OnTick()
{
   datetime current=iTime(_Symbol,InpTimeframe,0);
   if(current<=0 || current==g_lastBar) return;
   g_lastBar=current;
   ProcessBar();
}
