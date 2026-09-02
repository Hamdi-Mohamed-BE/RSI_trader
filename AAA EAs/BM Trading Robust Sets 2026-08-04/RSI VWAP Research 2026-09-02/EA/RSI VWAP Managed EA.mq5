#property copyright "Research reconstruction for private validation"
#property version   "1.00"
#property strict

#include <Trade/Trade.mqh>

enum ENUM_RV_EXIT_MODE
  {
   RV_EXIT_SIGNAL=0,
   RV_EXIT_FIXED_RR=1,
   RV_EXIT_RR_TRAIL=2
  };

enum ENUM_RV_STOP_MODE
  {
   RV_STOP_ATR=0,
   RV_STOP_SWING=1,
   RV_STOP_VWAP=2
  };

enum ENUM_RV_SESSION
  {
   RV_SESSION_ALL=0,
   RV_SESSION_ASIA=1,
   RV_SESSION_LONDON=2,
   RV_SESSION_NEW_YORK=3,
   RV_SESSION_OVERLAP=4
  };

input int               InpRSILength=16;
input double            InpOversold=18.0;
input double            InpOverbought=80.0;
input double            InpRiskPercent=1.0;
input ENUM_RV_EXIT_MODE InpExitMode=RV_EXIT_FIXED_RR;
input ENUM_RV_STOP_MODE InpStopMode=RV_STOP_ATR;
input int               InpATRPeriod=14;
input double            InpStopATR=2.0;
input int               InpSwingLookback=5;
input double            InpStopBufferATR=0.10;
input double            InpRewardRisk=1.0;
input double            InpSignalClosePercent=100.0;
input bool              InpUseBreakEven=false;
input double            InpBreakEvenAtR=0.75;
input double            InpBreakEvenLockR=0.05;
input bool              InpUseATRTrailing=false;
input double            InpTrailStartR=1.0;
input double            InpTrailATR=2.0;
input int               InpMaximumHoldingBars=0;
input ENUM_RV_SESSION   InpSession=RV_SESSION_ALL;
input int               InpMaximumSpreadPoints=0;
input int               InpMaximumDeviationPoints=80;
input long              InpMagic=926090201;

CTrade trade;
int atr_handle=INVALID_HANDLE;
datetime last_bar_time=0;

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
   if(step<=0.0) return 0.0;
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

bool ReadATR(const int shift,double &value)
  {
   double buffer[1];
   if(atr_handle==INVALID_HANDLE || CopyBuffer(atr_handle,0,shift,1,buffer)!=1) return false;
   value=buffer[0];
   return value>0.0 && MathIsValidNumber(value);
  }

bool BuildRsiVwap(double &rsi_closed_1,double &rsi_closed_2,double &vwap_closed_1)
  {
   const int wanted=MathMax(600,InpRSILength*30);
   MqlRates rates[];
   ArraySetAsSeries(rates,true);
   const int copied=CopyRates(_Symbol,_Period,0,wanted,rates);
   if(copied<InpRSILength+20) return false;

   double chronological_vwap[];
   double chronological_rsi[];
   ArrayResize(chronological_vwap,copied);
   ArrayResize(chronological_rsi,copied);
   ArrayInitialize(chronological_rsi,EMPTY_VALUE);

   double sum_price_volume=0.0;
   double sum_volume=0.0;
   int day_key=-1;
   for(int chrono=0;chrono<copied;chrono++)
     {
      const int series_index=copied-1-chrono;
      MqlDateTime stamp;
      TimeToStruct(rates[series_index].time,stamp);
      const int key=stamp.year*1000+stamp.day_of_year;
      if(key!=day_key)
        {
         day_key=key;
         sum_price_volume=0.0;
         sum_volume=0.0;
        }
      double volume=(double)rates[series_index].real_volume;
      if(volume<=0.0) volume=(double)rates[series_index].tick_volume;
      if(volume<=0.0) volume=1.0;
      sum_price_volume+=rates[series_index].close*volume;
      sum_volume+=volume;
      chronological_vwap[chrono]=sum_price_volume/sum_volume;
     }

   double average_gain=0.0;
   double average_loss=0.0;
   for(int chrono=1;chrono<copied;chrono++)
     {
      const double change=chronological_vwap[chrono]-chronological_vwap[chrono-1];
      const double gain=MathMax(change,0.0);
      const double loss=MathMax(-change,0.0);
      if(chrono<=InpRSILength)
        {
         average_gain+=gain;
         average_loss+=loss;
         if(chrono==InpRSILength)
           {
            average_gain/=InpRSILength;
            average_loss/=InpRSILength;
           }
        }
      else
        {
         average_gain=(average_gain*(InpRSILength-1)+gain)/InpRSILength;
         average_loss=(average_loss*(InpRSILength-1)+loss)/InpRSILength;
        }
      if(chrono>=InpRSILength)
        {
         if(average_loss<=0.0) chronological_rsi[chrono]=100.0;
         else
           {
            const double relative_strength=average_gain/average_loss;
            chronological_rsi[chrono]=100.0-100.0/(1.0+relative_strength);
           }
        }
     }

   const int chrono_1=copied-2;
   const int chrono_2=copied-3;
   if(chrono_2<InpRSILength || chronological_rsi[chrono_1]==EMPTY_VALUE || chronological_rsi[chrono_2]==EMPTY_VALUE)
      return false;
   rsi_closed_1=chronological_rsi[chrono_1];
   rsi_closed_2=chronological_rsi[chrono_2];
   vwap_closed_1=chronological_vwap[chrono_1];
   return MathIsValidNumber(rsi_closed_1) && MathIsValidNumber(rsi_closed_2);
  }

bool SessionAllowed(const datetime signal_time)
  {
   if(InpSession==RV_SESSION_ALL) return true;
   MqlDateTime stamp;
   TimeToStruct(signal_time,stamp);
   const int hour=stamp.hour;
   if(InpSession==RV_SESSION_ASIA) return hour>=0 && hour<8;
   if(InpSession==RV_SESSION_LONDON) return hour>=7 && hour<13;
   if(InpSession==RV_SESSION_NEW_YORK) return hour>=12 && hour<21;
   if(InpSession==RV_SESSION_OVERLAP) return hour>=12 && hour<16;
   return true;
  }

bool SpreadAllowed()
  {
   if(InpMaximumSpreadPoints<=0) return true;
   const double ask=SymbolInfoDouble(_Symbol,SYMBOL_ASK);
   const double bid=SymbolInfoDouble(_Symbol,SYMBOL_BID);
   const double point=SymbolInfoDouble(_Symbol,SYMBOL_POINT);
   if(point<=0.0) return false;
   return (ask-bid)/point<=InpMaximumSpreadPoints;
  }

double BuildStop(const double entry,const double atr,const double vwap)
  {
   double stop=entry-InpStopATR*atr;
   if(InpStopMode==RV_STOP_SWING)
     {
      const int count=MathMax(2,InpSwingLookback);
      double lows[];
      ArraySetAsSeries(lows,true);
      if(CopyLow(_Symbol,_Period,1,count,lows)==count)
        {
         int minimum_index=ArrayMinimum(lows,0,count);
         if(minimum_index>=0) stop=lows[minimum_index]-InpStopBufferATR*atr;
        }
     }
   else if(InpStopMode==RV_STOP_VWAP)
     {
      stop=vwap-InpStopBufferATR*atr;
      if(stop>=entry || entry-stop<0.25*atr) stop=entry-InpStopATR*atr;
     }
   const int stop_level=(int)SymbolInfoInteger(_Symbol,SYMBOL_TRADE_STOPS_LEVEL);
   const double point=SymbolInfoDouble(_Symbol,SYMBOL_POINT);
   const double minimum_distance=(stop_level+2)*point;
   if(entry-stop<minimum_distance) stop=entry-minimum_distance;
   return NormalizeDouble(stop,(int)SymbolInfoInteger(_Symbol,SYMBOL_DIGITS));
  }

double RiskVolume(const double entry,const double stop)
  {
   if(entry<=stop || InpRiskPercent<=0.0) return 0.0;
   double loss=0.0;
   if(!OrderCalcProfit(ORDER_TYPE_BUY,_Symbol,1.0,entry,stop,loss)) return 0.0;
   loss=MathAbs(loss);
   if(loss<=0.0) return 0.0;
   const double risk_money=AccountInfoDouble(ACCOUNT_EQUITY)*InpRiskPercent/100.0;
   return NormalizeVolume(risk_money/loss);
  }

void CloseBySignal(const ulong ticket)
  {
   if(!PositionSelectByTicket(ticket)) return;
   const double current=PositionGetDouble(POSITION_VOLUME);
   const double minimum=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MIN);
   if(InpSignalClosePercent>=99.999 || current<=minimum)
     {
      trade.PositionClose(ticket,InpMaximumDeviationPoints);
      return;
     }
   const double requested=NormalizeVolume(current*InpSignalClosePercent/100.0);
   if(requested>=current-minimum/2.0) trade.PositionClose(ticket,InpMaximumDeviationPoints);
   else if(requested>=minimum) trade.PositionClosePartial(ticket,requested,InpMaximumDeviationPoints);
  }

void ManagePosition()
  {
   ulong ticket=0;
   if(!OwnPosition(ticket) || !PositionSelectByTicket(ticket)) return;
   const double entry=PositionGetDouble(POSITION_PRICE_OPEN);
   const double current_stop=PositionGetDouble(POSITION_SL);
   const double current_tp=PositionGetDouble(POSITION_TP);
   const double bid=SymbolInfoDouble(_Symbol,SYMBOL_BID);
   if(entry<=0.0 || current_stop<=0.0 || bid<=entry) return;
   // A trailed stop must not redefine one R.  Fixed-RR positions preserve the
   // original risk in their take-profit distance; fall back to the live stop
   // only for signal-only exits that have no TP.
   double initial_risk=entry-current_stop;
   if(current_tp>entry && InpRewardRisk>0.0)
      initial_risk=(current_tp-entry)/InpRewardRisk;
   if(initial_risk<=0.0) return;
   double candidate=current_stop;
   if(InpUseBreakEven && bid-entry>=InpBreakEvenAtR*initial_risk)
      candidate=MathMax(candidate,entry+InpBreakEvenLockR*initial_risk);
   if(InpUseATRTrailing && bid-entry>=InpTrailStartR*initial_risk)
     {
      double atr=0.0;
      if(ReadATR(0,atr)) candidate=MathMax(candidate,bid-InpTrailATR*atr);
     }
   const double point=SymbolInfoDouble(_Symbol,SYMBOL_POINT);
   const int stops=(int)SymbolInfoInteger(_Symbol,SYMBOL_TRADE_STOPS_LEVEL);
   candidate=MathMin(candidate,bid-(stops+2)*point);
   candidate=NormalizeDouble(candidate,(int)SymbolInfoInteger(_Symbol,SYMBOL_DIGITS));
   if(candidate>current_stop+point) trade.PositionModify(ticket,candidate,current_tp);
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
   double rsi_1=0.0,rsi_2=0.0,vwap_1=0.0;
   if(!BuildRsiVwap(rsi_1,rsi_2,vwap_1)) return;
   ulong ticket=0;
   const bool has_position=OwnPosition(ticket);
   const bool exit_signal=(rsi_2>=InpOverbought && rsi_1<InpOverbought);
   if(has_position)
     {
      CheckMaximumHold(ticket);
      if(exit_signal && OwnPosition(ticket)) CloseBySignal(ticket);
      return;
     }

   const bool entry_signal=(rsi_2<=InpOversold && rsi_1>InpOversold);
   if(!entry_signal || !SpreadAllowed()) return;
   const datetime signal_time=iTime(_Symbol,_Period,1);
   if(!SessionAllowed(signal_time)) return;
   double atr=0.0;
   if(!ReadATR(1,atr)) return;
   const double entry=SymbolInfoDouble(_Symbol,SYMBOL_ASK);
   const double stop=BuildStop(entry,atr,vwap_1);
   const double volume=RiskVolume(entry,stop);
   if(volume<=0.0) return;
   double take_profit=0.0;
   if(InpExitMode!=RV_EXIT_SIGNAL)
      take_profit=NormalizeDouble(entry+InpRewardRisk*(entry-stop),(int)SymbolInfoInteger(_Symbol,SYMBOL_DIGITS));
   trade.SetExpertMagicNumber(InpMagic);
   trade.SetDeviationInPoints(InpMaximumDeviationPoints);
   trade.SetTypeFillingBySymbol(_Symbol);
   trade.Buy(volume,_Symbol,0.0,stop,take_profit,"RSI-VWAP long");
  }

int OnInit()
  {
   if(InpRSILength<2 || InpOversold<0.0 || InpOverbought>100.0 || InpOversold>=InpOverbought)
      return INIT_PARAMETERS_INCORRECT;
   atr_handle=iATR(_Symbol,_Period,InpATRPeriod);
   if(atr_handle==INVALID_HANDLE) return INIT_FAILED;
   trade.SetExpertMagicNumber(InpMagic);
   trade.SetDeviationInPoints(InpMaximumDeviationPoints);
   last_bar_time=iTime(_Symbol,_Period,0);
   return INIT_SUCCEEDED;
  }

void OnDeinit(const int reason)
  {
   if(atr_handle!=INVALID_HANDLE) IndicatorRelease(atr_handle);
  }

void OnTick()
  {
   ManagePosition();
   const datetime current=iTime(_Symbol,_Period,0);
   if(current<=0 || current==last_bar_time) return;
   last_bar_time=current;
   ProcessNewBar();
  }
