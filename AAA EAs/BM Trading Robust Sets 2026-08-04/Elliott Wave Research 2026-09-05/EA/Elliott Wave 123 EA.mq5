#property copyright "Private research reconstruction"
#property version   "1.00"
#property strict

#include <Trade/Trade.mqh>
#include "..\..\_Shared\CalyxAdaptivePortfolio.mqh"

enum ENUM_EW_TREND_FILTER
  {
   EW_TREND_NONE=0,
   EW_TREND_EMA50=1,
   EW_TREND_EMA_STACK=2,
   EW_TREND_H4_EMA50=3
  };

enum ENUM_EW_STOP_MODE
  {
   EW_STOP_WAVE2=0,
   EW_STOP_SIGNAL=1,
   EW_STOP_ATR=2
  };

enum ENUM_EW_SESSION
  {
   EW_SESSION_ALL=0,
   EW_SESSION_ASIA=1,
   EW_SESSION_LONDON=2,
   EW_SESSION_NEW_YORK=3,
   EW_SESSION_OVERLAP=4
  };

input double                    InpRiskPercent=1.0;
input bool                      InpAdaptivePortfolioControls=false;
input bool                      InpAllowLong=true;
input bool                      InpAllowShort=true;
input int                       InpPivotStrength=3;
input int                       InpPivotLookback=300;
input double                    InpMinimumWave1ATR=1.50;
input double                    InpMaximumWave1ATR=10.0;
input double                    InpMinimumWave2Retrace=0.382;
input double                    InpMaximumWave2Retrace=0.786;
input double                    InpBreakoutBufferATR=0.05;
input double                    InpMinimumBreakoutBodyATR=0.15;
input ENUM_EW_TREND_FILTER      InpTrendFilter=EW_TREND_EMA50;
input int                       InpFastEMA=20;
input int                       InpSlowEMA=50;
input int                       InpSlopeLookback=3;
input ENUM_EW_STOP_MODE         InpStopMode=EW_STOP_WAVE2;
input double                    InpStopBufferATR=0.10;
input double                    InpStopATR=2.0;
input double                    InpMaximumStopATR=5.0;
input double                    InpRewardRisk=1.50;
input bool                      InpUseBreakEven=false;
input double                    InpBreakEvenAtR=1.0;
input double                    InpBreakEvenLockR=0.0;
input bool                      InpUseATRTrailing=false;
input double                    InpTrailStartAtR=1.0;
input double                    InpTrailATR=2.0;
input bool                      InpUseDynamicM15Stop=false;
input double                    InpDynamicTriggerR=0.50;
input double                    InpDynamicLockR=0.20;
input int                       InpMaximumHoldingBars=0;
input ENUM_EW_SESSION           InpSession=EW_SESSION_ALL;
input double                    InpMaximumSpreadATR=0.15;
input int                       InpMaximumDeviationPoints=80;
input long                      InpMagic=965090001;

struct EWPivot
  {
   int type;
   int shift;
   datetime time;
   double price;
  };

CTrade trade;
int fast_handle=INVALID_HANDLE;
int slow_handle=INVALID_HANDLE;
int atr_handle=INVALID_HANDLE;
int h4_slow_handle=INVALID_HANDLE;
datetime last_bar_time=0;
datetime last_m15_time=0;
datetime last_traded_pattern=0;

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
   if(requested<=0.0 || minimum<=0.0 || maximum<=0.0 || step<=0.0) return 0.0;
   double volume=MathCeil((MathMin(requested,maximum)-1e-12)/step)*step;
   volume=MathMax(minimum,MathMin(maximum,volume));
   if(volume>requested+1e-12)
      PrintFormat("Risk sizing rounded %.8f lots up to broker-valid %.8f lots; actual risk exceeds the selected target.",requested,volume);
   return NormalizeDouble(volume,VolumeDigits(step));
  }

bool ReadBufferValue(const int handle,const int shift,double &value)
  {
   double buffer[1];
   if(handle==INVALID_HANDLE || CopyBuffer(handle,0,shift,1,buffer)!=1) return false;
   value=buffer[0];
   return MathIsValidNumber(value);
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

bool SessionAllowed(const datetime signal_time)
  {
   if(InpSession==EW_SESSION_ALL) return true;
   MqlDateTime stamp;
   TimeToStruct(signal_time,stamp);
   const int hour=stamp.hour;
   if(InpSession==EW_SESSION_ASIA) return hour>=0 && hour<8;
   if(InpSession==EW_SESSION_LONDON) return hour>=7 && hour<13;
   if(InpSession==EW_SESSION_NEW_YORK) return hour>=12 && hour<21;
   if(InpSession==EW_SESSION_OVERLAP) return hour>=12 && hour<16;
   return true;
  }

bool IsPivotLow(const MqlRates &rates[],const int shift,const int strength)
  {
   const double value=rates[shift].low;
   for(int offset=1;offset<=strength;offset++)
     {
      if(value>=rates[shift-offset].low || value>=rates[shift+offset].low) return false;
     }
   return true;
  }

bool IsPivotHigh(const MqlRates &rates[],const int shift,const int strength)
  {
   const double value=rates[shift].high;
   for(int offset=1;offset<=strength;offset++)
     {
      if(value<=rates[shift-offset].high || value<=rates[shift+offset].high) return false;
     }
   return true;
  }

void AddPivot(EWPivot &pivots[],int &count,const int type,const int shift,const datetime time,const double price)
  {
   if(count>0 && pivots[count-1].type==type)
     {
      const bool more_extreme=(type>0 ? price>pivots[count-1].price : price<pivots[count-1].price);
      if(more_extreme)
        {
         pivots[count-1].shift=shift;
         pivots[count-1].time=time;
         pivots[count-1].price=price;
        }
      return;
     }
   const int size=ArraySize(pivots);
   if(count>=size)
     {
      for(int i=1;i<size;i++) pivots[i-1]=pivots[i];
      count=size-1;
     }
   pivots[count].type=type;
   pivots[count].shift=shift;
   pivots[count].time=time;
   pivots[count].price=price;
   count++;
  }

bool TrendAllows(const int direction,const MqlRates &signal)
  {
   if(InpTrendFilter==EW_TREND_NONE) return true;
   if(InpTrendFilter==EW_TREND_H4_EMA50)
     {
      double current=0.0,older=0.0;
      if(!ReadBufferValue(h4_slow_handle,1,current) || !ReadBufferValue(h4_slow_handle,1+InpSlopeLookback,older)) return false;
      return direction>0 ? signal.close>current && current>older : signal.close<current && current<older;
     }
   double fast=0.0,slow=0.0,slow_old=0.0;
   if(!ReadBufferValue(fast_handle,1,fast) || !ReadBufferValue(slow_handle,1,slow) ||
      !ReadBufferValue(slow_handle,1+InpSlopeLookback,slow_old)) return false;
   if(InpTrendFilter==EW_TREND_EMA50)
      return direction>0 ? signal.close>slow && slow>slow_old : signal.close<slow && slow<slow_old;
   return direction>0 ? signal.close>slow && fast>slow && slow>slow_old : signal.close<slow && fast<slow && slow<slow_old;
  }

bool BuildWaveSignal(int &direction,double &atr_value,MqlRates &signal,double &wave2_price,datetime &pattern_time)
  {
   const int strength=MathMax(1,InpPivotStrength);
   const int wanted=MathMax(InpPivotLookback,InpSlowEMA+InpSlopeLookback+20);
   MqlRates rates[];
   ArraySetAsSeries(rates,true);
   const int copied=CopyRates(_Symbol,_Period,0,wanted,rates);
   if(copied<strength*2+20 || !ReadBufferValue(atr_handle,1,atr_value) || atr_value<=0.0) return false;
   signal=rates[1];
   const double body=MathAbs(signal.close-signal.open);
   if(body<InpMinimumBreakoutBodyATR*atr_value) return false;

   EWPivot pivots[64];
   int count=0;
   for(int shift=copied-strength-1;shift>=strength+1;shift--)
     {
      const bool low=IsPivotLow(rates,shift,strength);
      const bool high=IsPivotHigh(rates,shift,strength);
      if(low && !high) AddPivot(pivots,count,-1,shift,rates[shift].time,rates[shift].low);
      else if(high && !low) AddPivot(pivots,count,1,shift,rates[shift].time,rates[shift].high);
     }
   if(count<3) return false;
   const EWPivot first=pivots[count-3];
   const EWPivot impulse=pivots[count-2];
   const EWPivot correction=pivots[count-1];
   if(correction.time==last_traded_pattern || signal.time<=correction.time) return false;

   if(first.type<0 && impulse.type>0 && correction.type<0 && InpAllowLong)
     {
      const double wave1=impulse.price-first.price;
      const double retrace=(impulse.price-correction.price)/wave1;
      if(wave1>=InpMinimumWave1ATR*atr_value && wave1<=InpMaximumWave1ATR*atr_value &&
         correction.price>first.price && retrace>=InpMinimumWave2Retrace && retrace<=InpMaximumWave2Retrace &&
         signal.close>impulse.price+InpBreakoutBufferATR*atr_value && signal.close>signal.open && TrendAllows(1,signal))
        {
         direction=1;
         wave2_price=correction.price;
         pattern_time=correction.time;
         return true;
        }
     }
   if(first.type>0 && impulse.type<0 && correction.type>0 && InpAllowShort)
     {
      const double wave1=first.price-impulse.price;
      const double retrace=(correction.price-impulse.price)/wave1;
      if(wave1>=InpMinimumWave1ATR*atr_value && wave1<=InpMaximumWave1ATR*atr_value &&
         correction.price<first.price && retrace>=InpMinimumWave2Retrace && retrace<=InpMaximumWave2Retrace &&
         signal.close<impulse.price-InpBreakoutBufferATR*atr_value && signal.close<signal.open && TrendAllows(-1,signal))
        {
         direction=-1;
         wave2_price=correction.price;
         pattern_time=correction.time;
         return true;
        }
     }
   return false;
  }

double BuildStop(const int direction,const double entry,const double atr,const MqlRates &signal,const double wave2)
  {
   double stop=(direction>0 ? wave2-InpStopBufferATR*atr : wave2+InpStopBufferATR*atr);
   if(InpStopMode==EW_STOP_SIGNAL)
      stop=(direction>0 ? signal.low-InpStopBufferATR*atr : signal.high+InpStopBufferATR*atr);
   else if(InpStopMode==EW_STOP_ATR)
      stop=(direction>0 ? entry-InpStopATR*atr : entry+InpStopATR*atr);
   const int broker_stops=(int)SymbolInfoInteger(_Symbol,SYMBOL_TRADE_STOPS_LEVEL);
   const double minimum_distance=(broker_stops+2)*_Point;
   if(direction>0 && entry-stop<minimum_distance) stop=entry-minimum_distance;
   if(direction<0 && stop-entry<minimum_distance) stop=entry+minimum_distance;
   return NormalizeDouble(stop,(int)SymbolInfoInteger(_Symbol,SYMBOL_DIGITS));
  }

bool SpreadAllowed(const double atr)
  {
   if(InpMaximumSpreadATR<=0.0) return true;
   const double spread=SymbolInfoDouble(_Symbol,SYMBOL_ASK)-SymbolInfoDouble(_Symbol,SYMBOL_BID);
   return atr>0.0 && spread<=InpMaximumSpreadATR*atr;
  }

double RiskVolume(const int direction,const double entry,const double stop)
  {
   if(InpRiskPercent<=0.0 || (direction>0 && entry<=stop) || (direction<0 && entry>=stop)) return 0.0;
   double loss=0.0;
   const ENUM_ORDER_TYPE type=(direction>0 ? ORDER_TYPE_BUY : ORDER_TYPE_SELL);
   if(!OrderCalcProfit(type,_Symbol,1.0,entry,stop,loss)) return 0.0;
   loss=MathAbs(loss);
   if(loss<=0.0) return 0.0;
   const double adaptive=CalyxAdaptiveRiskMultiplier(InpAdaptivePortfolioControls,InpMagic);
   if(adaptive<=0.0) return 0.0;
   return NormalizeVolume(AccountInfoDouble(ACCOUNT_EQUITY)*InpRiskPercent*adaptive/100.0/loss);
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
   if(InpUseATRTrailing && favourable>=InpTrailStartAtR*risk)
     {
      double atr=0.0;
      if(ReadBufferValue(atr_handle,0,atr))
        {
         const double trail=(type==POSITION_TYPE_BUY ? price-InpTrailATR*atr : price+InpTrailATR*atr);
         candidate=(type==POSITION_TYPE_BUY ? MathMax(candidate,trail) : MathMin(candidate,trail));
        }
     }
   const int broker_stops=(int)SymbolInfoInteger(_Symbol,SYMBOL_TRADE_STOPS_LEVEL);
   if(type==POSITION_TYPE_BUY) candidate=MathMin(candidate,price-(broker_stops+2)*_Point);
   else candidate=MathMax(candidate,price+(broker_stops+2)*_Point);
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
   const int broker_stops=(int)SymbolInfoInteger(_Symbol,SYMBOL_TRADE_STOPS_LEVEL);
   if(type==POSITION_TYPE_BUY) candidate=MathMin(candidate,market-(broker_stops+2)*_Point);
   else candidate=MathMax(candidate,market+(broker_stops+2)*_Point);
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
   int direction=0;
   double atr=0.0,wave2=0.0;
   datetime pattern_time=0;
   MqlRates signal;
   if(!BuildWaveSignal(direction,atr,signal,wave2,pattern_time)) return;
   if(!SessionAllowed(signal.time) || !SpreadAllowed(atr)) return;
   const double entry=(direction>0 ? SymbolInfoDouble(_Symbol,SYMBOL_ASK) : SymbolInfoDouble(_Symbol,SYMBOL_BID));
   const double stop=BuildStop(direction,entry,atr,signal,wave2);
   const double distance=MathAbs(entry-stop);
   if(distance<=0.0 || distance>InpMaximumStopATR*atr) return;
   const double volume=RiskVolume(direction,entry,stop);
   if(volume<=0.0) return;
   const int digits=(int)SymbolInfoInteger(_Symbol,SYMBOL_DIGITS);
   const double take_profit=NormalizeDouble(direction>0 ? entry+InpRewardRisk*distance : entry-InpRewardRisk*distance,digits);
   trade.SetExpertMagicNumber(InpMagic);
   trade.SetDeviationInPoints(InpMaximumDeviationPoints);
   trade.SetTypeFillingBySymbol(_Symbol);
   const bool sent=(direction>0 ? trade.Buy(volume,_Symbol,0.0,stop,take_profit,"EW 1-2-3 long") :
                                  trade.Sell(volume,_Symbol,0.0,stop,take_profit,"EW 1-2-3 short"));
   if(sent) last_traded_pattern=pattern_time;
  }

int OnInit()
  {
   if(InpRiskPercent<=0.0 || InpPivotStrength<1 || InpPivotLookback<50 ||
      InpMinimumWave1ATR<=0.0 || InpMaximumWave1ATR<InpMinimumWave1ATR ||
      InpMinimumWave2Retrace<=0.0 || InpMaximumWave2Retrace>=1.0 ||
      InpMaximumWave2Retrace<=InpMinimumWave2Retrace || InpRewardRisk<=0.0) return INIT_PARAMETERS_INCORRECT;
   fast_handle=iMA(_Symbol,_Period,InpFastEMA,0,MODE_EMA,PRICE_CLOSE);
   slow_handle=iMA(_Symbol,_Period,InpSlowEMA,0,MODE_EMA,PRICE_CLOSE);
   atr_handle=iATR(_Symbol,_Period,14);
   h4_slow_handle=iMA(_Symbol,PERIOD_H4,InpSlowEMA,0,MODE_EMA,PRICE_CLOSE);
   if(fast_handle==INVALID_HANDLE || slow_handle==INVALID_HANDLE || atr_handle==INVALID_HANDLE || h4_slow_handle==INVALID_HANDLE) return INIT_FAILED;
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
   if(h4_slow_handle!=INVALID_HANDLE) IndicatorRelease(h4_slow_handle);
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
