#property copyright "Private research reconstruction"
#property version   "1.00"
#property strict

#include <Trade/Trade.mqh>

enum ENUM_TP_STOP_MODE
  {
   TP_STOP_SIGNAL=0,
   TP_STOP_SWING=1,
   TP_STOP_ATR=2
  };

enum ENUM_TP_PULLBACK_MODE
  {
   TP_PULLBACK_EMA20=0,
   TP_PULLBACK_EMA50=1,
   TP_PULLBACK_EITHER=2
  };

enum ENUM_TP_CONFIRM_MODE
  {
   TP_CONFIRM_ANY=0,
   TP_CONFIRM_ENGULF=1,
   TP_CONFIRM_PIN=2,
   TP_CONFIRM_BREAK=3
  };

enum ENUM_TP_SESSION
  {
   TP_SESSION_ALL=0,
   TP_SESSION_ASIA=1,
   TP_SESSION_LONDON=2,
   TP_SESSION_NEW_YORK=3,
   TP_SESSION_OVERLAP=4
  };

input double                    InpRiskPercent=1.0;
input bool                      InpAllowLong=true;
input bool                      InpAllowShort=true;
input int                       InpFastEMA=20;
input int                       InpSlowEMA=50;
input int                       InpSlopeLookback=3;
input int                       InpMomentumLookback=24;
input double                    InpMinimumMomentumATR=0.50;
input int                       InpRangeLookback=48;
input double                    InpRangePositionMinimum=0.65;
input bool                      InpUseRangeFilter=false;
input ENUM_TP_PULLBACK_MODE     InpPullbackMode=TP_PULLBACK_EMA20;
input double                    InpPullbackToleranceATR=0.25;
input ENUM_TP_CONFIRM_MODE      InpConfirmation=TP_CONFIRM_ANY;
input double                    InpMinimumBodyATR=0.05;
input double                    InpMaximumSignalATR=2.50;
input ENUM_TP_STOP_MODE         InpStopMode=TP_STOP_SWING;
input int                       InpSwingLookback=5;
input double                    InpStopATR=2.0;
input double                    InpStopBufferATR=0.10;
input double                    InpRewardRisk=1.50;
input bool                      InpUseBreakEven=false;
input double                    InpBreakEvenAtR=1.0;
input double                    InpBreakEvenLockR=0.05;
input bool                      InpUseATRTrailing=false;
input double                    InpTrailStartR=1.0;
input double                    InpTrailATR=2.0;
input bool                      InpUseDynamicM15Stop=false;
input double                    InpDynamicTriggerR=0.50;
input double                    InpDynamicLockR=0.20;
input int                       InpMaximumHoldingBars=0;
input ENUM_TP_SESSION           InpSession=TP_SESSION_ALL;
input bool                      InpUseRegimeGate=false;
input int                       InpRegimeReturnBars=20;
input double                    InpRegimeThresholdATR=2.0;
input int                       InpRegimeTrainingBars=500;
input double                    InpRegimeMinimumProbability=0.40;
input int                       InpMaximumSpreadPoints=0;
input int                       InpMaximumDeviationPoints=80;
input long                      InpMagic=926090301;

CTrade trade;
int fast_handle=INVALID_HANDLE;
int slow_handle=INVALID_HANDLE;
int atr_handle=INVALID_HANDLE;
datetime last_bar_time=0;
datetime last_m15_time=0;

int VolumeDigits(const double step)
  {
   if(step>=1.0) return 0;
   if(step>=0.1) return 1;
   if(step>=0.01) return 2;
   if(step>=0.001) return 3;
   return 4;
  }

double NormalizeVolume(const double requested)
  {
   const double minimum=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MIN);
   const double maximum=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MAX);
   const double step=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_STEP);
   if(step<=0.0 || requested<minimum) return 0.0;
   double volume=MathFloor(requested/step+1e-9)*step;
   volume=MathMax(minimum,MathMin(maximum,volume));
   return NormalizeDouble(volume,VolumeDigits(step));
  }

bool OwnPosition(ulong &ticket)
  {
   ticket=0;
   for(int index=PositionsTotal()-1;index>=0;index--)
     {
      const ulong candidate=PositionGetTicket(index);
      if(candidate==0 || !PositionSelectByTicket(candidate)) continue;
      if(PositionGetString(POSITION_SYMBOL)!=_Symbol) continue;
      if((long)PositionGetInteger(POSITION_MAGIC)!=InpMagic) continue;
      ticket=candidate;
      return true;
     }
   return false;
  }

bool ReadBufferValue(const int handle,const int shift,double &value)
  {
   double buffer[1];
   if(handle==INVALID_HANDLE || CopyBuffer(handle,0,shift,1,buffer)!=1) return false;
   value=buffer[0];
   return value>0.0 && MathIsValidNumber(value);
  }

bool SessionAllowed(const datetime signal_time)
  {
   if(InpSession==TP_SESSION_ALL) return true;
   MqlDateTime stamp;
   TimeToStruct(signal_time,stamp);
   const int hour=stamp.hour; // Broker-server hours, deliberately fixed and reported.
   if(InpSession==TP_SESSION_ASIA) return hour>=0 && hour<8;
   if(InpSession==TP_SESSION_LONDON) return hour>=7 && hour<13;
   if(InpSession==TP_SESSION_NEW_YORK) return hour>=12 && hour<21;
   if(InpSession==TP_SESSION_OVERLAP) return hour>=12 && hour<16;
   return true;
  }

bool SpreadAllowed()
  {
   if(InpMaximumSpreadPoints<=0) return true;
   const double ask=SymbolInfoDouble(_Symbol,SYMBOL_ASK);
   const double bid=SymbolInfoDouble(_Symbol,SYMBOL_BID);
   const double point=SymbolInfoDouble(_Symbol,SYMBOL_POINT);
   return point>0.0 && (ask-bid)/point<=InpMaximumSpreadPoints;
  }

bool BullishPin(const MqlRates &bar)
  {
   const double body=MathAbs(bar.close-bar.open);
   const double lower=MathMin(bar.open,bar.close)-bar.low;
   const double upper=bar.high-MathMax(bar.open,bar.close);
   return bar.close>bar.open && lower>=2.0*MathMax(body,_Point) && lower>upper;
  }

bool BearishPin(const MqlRates &bar)
  {
   const double body=MathAbs(bar.close-bar.open);
   const double upper=bar.high-MathMax(bar.open,bar.close);
   const double lower=MathMin(bar.open,bar.close)-bar.low;
   return bar.close<bar.open && upper>=2.0*MathMax(body,_Point) && upper>lower;
  }

bool BullConfirmation(const MqlRates &signal,const MqlRates &prior)
  {
   const bool engulf=signal.close>signal.open && prior.close<prior.open && signal.open<=prior.close && signal.close>=prior.open;
   const bool pin=BullishPin(signal);
   const bool breaking=signal.close>prior.high && signal.close>signal.open;
   if(InpConfirmation==TP_CONFIRM_ENGULF) return engulf;
   if(InpConfirmation==TP_CONFIRM_PIN) return pin;
   if(InpConfirmation==TP_CONFIRM_BREAK) return breaking;
   return engulf || pin || breaking;
  }

bool BearConfirmation(const MqlRates &signal,const MqlRates &prior)
  {
   const bool engulf=signal.close<signal.open && prior.close>prior.open && signal.open>=prior.close && signal.close<=prior.open;
   const bool pin=BearishPin(signal);
   const bool breaking=signal.close<prior.low && signal.close<signal.open;
   if(InpConfirmation==TP_CONFIRM_ENGULF) return engulf;
   if(InpConfirmation==TP_CONFIRM_PIN) return pin;
   if(InpConfirmation==TP_CONFIRM_BREAK) return breaking;
   return engulf || pin || breaking;
  }

int RegimeStateAt(const MqlRates &rates[],const int shift,const double atr)
  {
   const int older=shift+InpRegimeReturnBars;
   if(older>=ArraySize(rates) || atr<=0.0) return 0;
   const double normalized=(rates[shift].close-rates[older].close)/atr;
   if(normalized>=InpRegimeThresholdATR) return 1;
   if(normalized<=-InpRegimeThresholdATR) return -1;
   return 0;
  }

bool RegimeAllows(const int direction,const MqlRates &rates[],const double atr)
  {
   if(!InpUseRegimeGate) return true;
   const int required=InpRegimeTrainingBars+InpRegimeReturnBars+5;
   if(ArraySize(rates)<required) return false;
   double counts[3][3];
   ArrayInitialize(counts,0.0);
   for(int shift=InpRegimeTrainingBars;shift>=2;shift--)
     {
      const int from=RegimeStateAt(rates,shift,atr)+1;
      const int to=RegimeStateAt(rates,shift-1,atr)+1;
      counts[from][to]+=1.0;
     }
   const int current=RegimeStateAt(rates,1,atr)+1;
   double total=0.0;
   for(int target=0;target<3;target++) total+=counts[current][target];
   if(total<=0.0) return false;
   const int desired=(direction>0 ? 2 : 0);
   double maximum=-1.0;
   int forecast=1;
   for(int target=0;target<3;target++)
     {
      const double probability=counts[current][target]/total;
      if(probability>maximum){maximum=probability;forecast=target;}
     }
   return forecast==desired && maximum>=InpRegimeMinimumProbability;
  }

bool BuildSignal(int &direction,double &atr_value,MqlRates &signal_bar)
  {
   const int wanted=MathMax(InpRegimeTrainingBars+InpRegimeReturnBars+10,InpRangeLookback+InpMomentumLookback+20);
   MqlRates rates[];
   ArraySetAsSeries(rates,true);
   const int copied=CopyRates(_Symbol,_Period,0,wanted,rates);
   if(copied<MathMax(InpSlowEMA+InpSlopeLookback+10,InpMomentumLookback+5)) return false;
   signal_bar=rates[1];
   const MqlRates prior=rates[2];
   double fast=0.0,slow=0.0,slow_old=0.0;
   if(!ReadBufferValue(fast_handle,1,fast) || !ReadBufferValue(slow_handle,1,slow) ||
      !ReadBufferValue(slow_handle,1+InpSlopeLookback,slow_old) || !ReadBufferValue(atr_handle,1,atr_value)) return false;
   const double body=MathAbs(signal_bar.close-signal_bar.open);
   const double range=signal_bar.high-signal_bar.low;
   if(body<InpMinimumBodyATR*atr_value || range>InpMaximumSignalATR*atr_value) return false;
   const double momentum=(signal_bar.close-rates[1+InpMomentumLookback].close)/atr_value;

   double highest=rates[1].high,lowest=rates[1].low;
   const int range_count=MathMin(InpRangeLookback,copied-2);
   for(int shift=2;shift<=range_count;shift++)
     {
      highest=MathMax(highest,rates[shift].high);
      lowest=MathMin(lowest,rates[shift].low);
     }
   const double location=(highest>lowest ? (signal_bar.close-lowest)/(highest-lowest) : 0.5);
   const bool touched_fast=(signal_bar.low<=fast+InpPullbackToleranceATR*atr_value && signal_bar.high>=fast-InpPullbackToleranceATR*atr_value);
   const bool touched_slow=(signal_bar.low<=slow+InpPullbackToleranceATR*atr_value && signal_bar.high>=slow-InpPullbackToleranceATR*atr_value);
   const bool pullback_long=(InpPullbackMode==TP_PULLBACK_EMA20 ? touched_fast : InpPullbackMode==TP_PULLBACK_EMA50 ? touched_slow : touched_fast || touched_slow);
   const bool pullback_short=pullback_long;

   const bool long_trend=signal_bar.close>slow && fast>slow && slow>slow_old && momentum>=InpMinimumMomentumATR;
   const bool short_trend=signal_bar.close<slow && fast<slow && slow<slow_old && momentum<=-InpMinimumMomentumATR;
   const bool long_range=!InpUseRangeFilter || location>=InpRangePositionMinimum;
   const bool short_range=!InpUseRangeFilter || location<=1.0-InpRangePositionMinimum;
   if(InpAllowLong && long_trend && long_range && pullback_long && BullConfirmation(signal_bar,prior) && RegimeAllows(1,rates,atr_value))
     {direction=1;return true;}
   if(InpAllowShort && short_trend && short_range && pullback_short && BearConfirmation(signal_bar,prior) && RegimeAllows(-1,rates,atr_value))
     {direction=-1;return true;}
   return false;
  }

double BuildStop(const int direction,const double entry,const double atr,const MqlRates &signal)
  {
   double stop=(direction>0 ? entry-InpStopATR*atr : entry+InpStopATR*atr);
   if(InpStopMode==TP_STOP_SIGNAL)
      stop=(direction>0 ? signal.low-InpStopBufferATR*atr : signal.high+InpStopBufferATR*atr);
   else if(InpStopMode==TP_STOP_SWING)
     {
      const int count=MathMax(2,InpSwingLookback);
      if(direction>0)
        {
         double lows[]; ArraySetAsSeries(lows,true);
         if(CopyLow(_Symbol,_Period,1,count,lows)==count) stop=lows[ArrayMinimum(lows,0,count)]-InpStopBufferATR*atr;
        }
      else
        {
         double highs[]; ArraySetAsSeries(highs,true);
         if(CopyHigh(_Symbol,_Period,1,count,highs)==count) stop=highs[ArrayMaximum(highs,0,count)]+InpStopBufferATR*atr;
        }
     }
   const int stops=(int)SymbolInfoInteger(_Symbol,SYMBOL_TRADE_STOPS_LEVEL);
   const double minimum_distance=(stops+2)*_Point;
   if(direction>0 && entry-stop<minimum_distance) stop=entry-minimum_distance;
   if(direction<0 && stop-entry<minimum_distance) stop=entry+minimum_distance;
   return NormalizeDouble(stop,(int)SymbolInfoInteger(_Symbol,SYMBOL_DIGITS));
  }

double RiskVolume(const int direction,const double entry,const double stop)
  {
   if(InpRiskPercent<=0.0 || (direction>0 && entry<=stop) || (direction<0 && entry>=stop)) return 0.0;
   double loss=0.0;
   const ENUM_ORDER_TYPE type=(direction>0 ? ORDER_TYPE_BUY : ORDER_TYPE_SELL);
   if(!OrderCalcProfit(type,_Symbol,1.0,entry,stop,loss)) return 0.0;
   loss=MathAbs(loss);
   if(loss<=0.0) return 0.0;
   return NormalizeVolume(AccountInfoDouble(ACCOUNT_EQUITY)*InpRiskPercent/100.0/loss);
  }

double OriginalRisk(const long type,const double entry,const double stop,const double tp)
  {
   if(InpRewardRisk>0.0)
     {
      if(type==POSITION_TYPE_BUY && tp>entry) return (tp-entry)/InpRewardRisk;
      if(type==POSITION_TYPE_SELL && tp<entry) return (entry-tp)/InpRewardRisk;
     }
   return MathAbs(entry-stop);
  }

void ManagePosition()
  {
   ulong ticket=0;
   if(!OwnPosition(ticket) || !PositionSelectByTicket(ticket)) return;
   const long type=PositionGetInteger(POSITION_TYPE);
   const double entry=PositionGetDouble(POSITION_PRICE_OPEN);
   const double current_stop=PositionGetDouble(POSITION_SL);
   const double tp=PositionGetDouble(POSITION_TP);
   const double price=(type==POSITION_TYPE_BUY ? SymbolInfoDouble(_Symbol,SYMBOL_BID) : SymbolInfoDouble(_Symbol,SYMBOL_ASK));
   const double risk=OriginalRisk(type,entry,current_stop,tp);
   if(risk<=0.0) return;
   const double favourable=(type==POSITION_TYPE_BUY ? price-entry : entry-price);
   double candidate=current_stop;
   if(InpUseBreakEven && favourable>=InpBreakEvenAtR*risk)
     {
      const double be=(type==POSITION_TYPE_BUY ? entry+InpBreakEvenLockR*risk : entry-InpBreakEvenLockR*risk);
      candidate=(type==POSITION_TYPE_BUY ? MathMax(candidate,be) : MathMin(candidate,be));
     }
   if(InpUseATRTrailing && favourable>=InpTrailStartR*risk)
     {
      double atr=0.0;
      if(ReadBufferValue(atr_handle,0,atr))
        {
         const double trail=(type==POSITION_TYPE_BUY ? price-InpTrailATR*atr : price+InpTrailATR*atr);
         candidate=(type==POSITION_TYPE_BUY ? MathMax(candidate,trail) : MathMin(candidate,trail));
        }
     }
   const int stops=(int)SymbolInfoInteger(_Symbol,SYMBOL_TRADE_STOPS_LEVEL);
   if(type==POSITION_TYPE_BUY) candidate=MathMin(candidate,price-(stops+2)*_Point);
   else candidate=MathMax(candidate,price+(stops+2)*_Point);
   candidate=NormalizeDouble(candidate,(int)SymbolInfoInteger(_Symbol,SYMBOL_DIGITS));
   const bool improved=(type==POSITION_TYPE_BUY ? candidate>current_stop+_Point : candidate<current_stop-_Point);
   if(improved) trade.PositionModify(ticket,candidate,tp);
  }

void ManageDynamicM15()
  {
   if(!InpUseDynamicM15Stop) return;
   const datetime current=iTime(_Symbol,PERIOD_M15,0);
   if(current<=0 || current==last_m15_time) return;
   last_m15_time=current;
   ulong ticket=0;
   if(!OwnPosition(ticket) || !PositionSelectByTicket(ticket)) return;
   const long type=PositionGetInteger(POSITION_TYPE);
   const double entry=PositionGetDouble(POSITION_PRICE_OPEN);
   const double stop=PositionGetDouble(POSITION_SL);
   const double tp=PositionGetDouble(POSITION_TP);
   const double risk=OriginalRisk(type,entry,stop,tp);
   const double close=iClose(_Symbol,PERIOD_M15,1);
   if(risk<=0.0 || close<=0.0) return;
   const double progress=(type==POSITION_TYPE_BUY ? close-entry : entry-close);
   if(progress<InpDynamicTriggerR*risk) return;
   double candidate=(type==POSITION_TYPE_BUY ? entry+InpDynamicLockR*risk : entry-InpDynamicLockR*risk);
   const double market=(type==POSITION_TYPE_BUY ? SymbolInfoDouble(_Symbol,SYMBOL_BID) : SymbolInfoDouble(_Symbol,SYMBOL_ASK));
   const int stops=(int)SymbolInfoInteger(_Symbol,SYMBOL_TRADE_STOPS_LEVEL);
   if(type==POSITION_TYPE_BUY) candidate=MathMin(candidate,market-(stops+2)*_Point);
   else candidate=MathMax(candidate,market+(stops+2)*_Point);
   candidate=NormalizeDouble(candidate,(int)SymbolInfoInteger(_Symbol,SYMBOL_DIGITS));
   const bool improved=(type==POSITION_TYPE_BUY ? candidate>stop+_Point : candidate<stop-_Point);
   if(improved) trade.PositionModify(ticket,candidate,tp);
  }

void CheckMaximumHold(const ulong ticket)
  {
   if(InpMaximumHoldingBars<=0 || !PositionSelectByTicket(ticket)) return;
   const datetime opened=(datetime)PositionGetInteger(POSITION_TIME);
   const int seconds=PeriodSeconds(_Period);
   if(seconds>0 && TimeCurrent()-opened>=(long)InpMaximumHoldingBars*seconds)
      trade.PositionClose(ticket,InpMaximumDeviationPoints);
  }

void ProcessNewBar()
  {
   ulong ticket=0;
   if(OwnPosition(ticket)) {CheckMaximumHold(ticket); return;}
   if(!SpreadAllowed() || !SessionAllowed(iTime(_Symbol,_Period,1))) return;
   int direction=0;
   double atr=0.0;
   MqlRates signal;
   if(!BuildSignal(direction,atr,signal)) return;
   const double entry=(direction>0 ? SymbolInfoDouble(_Symbol,SYMBOL_ASK) : SymbolInfoDouble(_Symbol,SYMBOL_BID));
   const double stop=BuildStop(direction,entry,atr,signal);
   const double volume=RiskVolume(direction,entry,stop);
   if(volume<=0.0) return;
   const double risk=MathAbs(entry-stop);
   const double take_profit=NormalizeDouble(direction>0 ? entry+InpRewardRisk*risk : entry-InpRewardRisk*risk,(int)SymbolInfoInteger(_Symbol,SYMBOL_DIGITS));
   trade.SetExpertMagicNumber(InpMagic);
   trade.SetDeviationInPoints(InpMaximumDeviationPoints);
   trade.SetTypeFillingBySymbol(_Symbol);
   if(direction>0) trade.Buy(volume,_Symbol,0.0,stop,take_profit,"Trend progression long");
   else trade.Sell(volume,_Symbol,0.0,stop,take_profit,"Trend progression short");
  }

int OnInit()
  {
   if(InpRiskPercent<=0.0 || InpFastEMA<2 || InpSlowEMA<=InpFastEMA || InpRewardRisk<=0.0) return INIT_PARAMETERS_INCORRECT;
   fast_handle=iMA(_Symbol,_Period,InpFastEMA,0,MODE_EMA,PRICE_CLOSE);
   slow_handle=iMA(_Symbol,_Period,InpSlowEMA,0,MODE_EMA,PRICE_CLOSE);
   atr_handle=iATR(_Symbol,_Period,14);
   if(fast_handle==INVALID_HANDLE || slow_handle==INVALID_HANDLE || atr_handle==INVALID_HANDLE) return INIT_FAILED;
   trade.SetExpertMagicNumber(InpMagic);
   trade.SetDeviationInPoints(InpMaximumDeviationPoints);
   last_bar_time=iTime(_Symbol,_Period,0);
   last_m15_time=iTime(_Symbol,PERIOD_M15,0);
   return INIT_SUCCEEDED;
  }

void OnDeinit(const int reason)
  {
   if(fast_handle!=INVALID_HANDLE) IndicatorRelease(fast_handle);
   if(slow_handle!=INVALID_HANDLE) IndicatorRelease(slow_handle);
   if(atr_handle!=INVALID_HANDLE) IndicatorRelease(atr_handle);
  }

void OnTick()
  {
   ManagePosition();
   ManageDynamicM15();
   const datetime current=iTime(_Symbol,_Period,0);
   if(current<=0 || current==last_bar_time) return;
   last_bar_time=current;
   ProcessNewBar();
  }
