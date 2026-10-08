#property strict
#property version "3.00"
#include <Trade/Trade.mqh>
#include "CalyxAdaptivePortfolio.mqh"
#include "RiskSupport.mqh"



// Research copy 2026-09-25 of Nasdaq 5M Candle Momentum DI EA v2.10 (production source unchanged).
// Adds, default OFF: N5_STOP_PERCENT initial stop and slow-MA trailing, to recreate the management seen in the
// user's QUANT_LAB "Momentum v2.0" video (0.60% stop, no target, stop trailed on a slow MA, held overnight).

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



enum ENUM_N5_STOP_MODE
  {
   N5_STOP_ATR=0,
   N5_STOP_SIGNAL_CANDLE=1,
   N5_STOP_PERCENT=2
  };
input ENUM_TIMEFRAMES InpSignalTimeframe=PERIOD_M5;
input int    InpSignalHourNY=9;
input int    InpSignalMinuteNY=30;
input int    InpEMAPeriod=12;
input bool   InpAllowLong=true;
input bool   InpAllowShort=true;
input bool   InpRequireEMASlope=false;
input double InpMinimumBodyATR=0.00;
input double InpMaximumBodyATR=0.00;
input double InpMinimumBodyFraction=0.00;
input double InpMinimumEMADistanceATR=0.00;
input double InpMaximumEMADistanceATR=0.00;
input int    InpRelativeVolumePeriod=0;
input double InpMinimumRelativeVolume=0.00;
input bool   InpRequireDIAgreement=false; // true: longs need +DI>-DI, shorts need -DI>+DI on the closed signal bar
input int    InpDIPeriod=14;
input int               InpATRPeriod=14;
input ENUM_N5_STOP_MODE InpStopMode=N5_STOP_ATR;
input double            InpInitialStopATR=4.00;
input double            InpSignalStopBufferATR=0.10;
input double            InpMaximumStopATR=0.00;
input bool              InpUseFixedTarget=false;
input double            InpRewardRisk=2.00;
input bool              InpUseAdaptiveRR=false;
input double            InpAdaptiveStrongBodyATR=1.00;
input double            InpAdaptiveStrongRR=3.00;
input double            InpInitialStopPercent=0.60;   // used only by N5_STOP_PERCENT (percent of entry price)
input bool   InpUseATRTrailing=true;
input double InpTrailingATR=6.00;
input double InpTrailStartR=1.00;
input bool   InpUseBreakEven=false;
input double InpBreakEvenTriggerR=1.00;
input double InpBreakEvenLockR=0.00;
input int    InpMaximumHoldingMinutes=0;
input bool   InpCloseAtSessionEnd=true;
input int    InpCloseHourNY=15;
input int    InpCloseMinuteNY=55;
input bool   InpUseMATrailing=false;        // research: stop follows a slow MA (closed bar), never loosened
input int    InpTrailMAPeriod=200;
input ENUM_MA_METHOD InpTrailMAMethod=MODE_EMA;
input double InpTrailMAStartR=0.50;         // start trailing once open profit >= this many R
input bool InpAutoServerUtcOffsetLive=true;
input int  InpServerUtcOffsetHours=0;
input bool   InpEnableTrading=true;
input double InpRiskPercent=1.00;
input bool   InpAdaptivePortfolioControls=false;
input double InpMaximumSpreadATR=0.00;
input long   InpMagic=862020;
input int    InpMaximumDeviationPoints=50;

CTrade g_trade;
int g_ema_handle=INVALID_HANDLE;
int g_atr_handle=INVALID_HANDLE;
int g_adx_handle=INVALID_HANDLE;
int g_trail_ma_handle=INVALID_HANDLE;
datetime g_last_bar_time=0;

double NormalizePrice(const double price)
  {
   return NormalizeDouble(price,(int)SymbolInfoInteger(_Symbol,SYMBOL_DIGITS));
  }

double NormalizeLots(const double raw_lots)
  {
   double minimum=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MIN);
   double maximum=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MAX);
   double step=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_STEP);
   if(raw_lots<=0.0 || minimum<=0.0 || maximum<=0.0 || step<=0.0) return 0.0;
   double lots=MathCeil((MathMin(raw_lots,maximum)-1e-12)/step)*step;
   lots=MathMax(minimum,MathMin(maximum,lots));
   if(lots>raw_lots+1e-12)
      PrintFormat("Risk sizing rounded %.8f lots up to broker-valid %.8f lots; actual risk exceeds the selected target.",raw_lots,lots);
   return lots;
  }

double LotsForRisk(const ENUM_ORDER_TYPE type,const double entry,const double stop)
  {
   // This package uses the selected per-trade allocation; original 1% behavior is retained at 1%.
   double applied_risk=InpRiskPercent; // User-selected allocation in this standalone package.
   const double adaptive=CalyxAdaptiveRiskMultiplier(InpAdaptivePortfolioControls,InpMagic);
   if(adaptive<=0.0) return 0.0;
   double cash=FP_RiskBudget(applied_risk,adaptive);
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

double RelativeVolume(const int signal_shift)
  {
   if(InpRelativeVolumePeriod<2) return 999.0;
   long signal_volume=iVolume(_Symbol,InpSignalTimeframe,signal_shift);
   if(signal_volume<=0) return 0.0;
   double total=0.0;
   int valid=0;
   for(int shift=signal_shift+1;shift<=signal_shift+InpRelativeVolumePeriod;shift++)
     {
      long volume=iVolume(_Symbol,InpSignalTimeframe,shift);
      if(volume<=0) continue;
      total+=(double)volume;
      valid++;
     }
   if(valid<InpRelativeVolumePeriod/2 || total<=0.0) return 0.0;
   return (double)signal_volume/(total/valid);
  }

double SelectedRewardRisk(const MqlRates &signal,const double atr)
  {
   if(!InpUseAdaptiveRR || atr<=0.0) return InpRewardRisk;
   double body=MathAbs(signal.close-signal.open)/atr;
   return (body>=InpAdaptiveStrongBodyATR ? InpAdaptiveStrongRR : InpRewardRisk);
  }

bool SendEntry(const int direction,const double atr,const MqlRates &signal,const double reward_risk)
  {
   if(!DTS_EntrySessionAllowed()) return false;
   if(!HAMA_SafeRegimeAllowsDirection(direction)) return false;
   MqlTick tick;
   if(!SymbolInfoTick(_Symbol,tick)) return false;
   double entry=(direction>0 ? tick.ask : tick.bid);
   double stop=(InpStopMode==N5_STOP_SIGNAL_CANDLE
                ? (direction>0 ? signal.low-InpSignalStopBufferATR*atr : signal.high+InpSignalStopBufferATR*atr)
                : entry-direction*InpInitialStopATR*atr);
   if(InpStopMode==N5_STOP_PERCENT)
      stop=entry-direction*entry*InpInitialStopPercent/100.0;
   if(InpMaximumStopATR>0.0 && MathAbs(entry-stop)>InpMaximumStopATR*atr)
      stop=entry-direction*InpMaximumStopATR*atr;
   stop=NormalizePrice(stop);
   double point=SymbolInfoDouble(_Symbol,SYMBOL_POINT);
   double broker_gap=MathMax((double)SymbolInfoInteger(_Symbol,SYMBOL_TRADE_STOPS_LEVEL),
                             (double)SymbolInfoInteger(_Symbol,SYMBOL_TRADE_FREEZE_LEVEL))*point;
   if(direction>0 && stop>=entry-broker_gap) stop=NormalizePrice(entry-broker_gap);
   if(direction<0 && stop<=entry+broker_gap) stop=NormalizePrice(entry+broker_gap);
   double risk=MathAbs(entry-stop);
   double target=0.0;
   if(InpUseFixedTarget)
     {
      target=NormalizePrice(entry+direction*reward_risk*risk);
      if(MathAbs(target-entry)<broker_gap) target=NormalizePrice(entry+direction*broker_gap);
     }
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
   string prefix=(InpUseMarkovRegimeFilter ? "Safe " : "");
   string comment=prefix+(direction>0 ? "N5EMA long" : "N5EMA short");
   bool sent=(direction>0 ? g_trade.Buy(lots,_Symbol,0.0,stop,target,comment)
                          : g_trade.Sell(lots,_Symbol,0.0,stop,target,comment));
   if(sent) StoreInitialRisk();
   else Print("N5EMA order rejected: ",g_trade.ResultRetcodeDescription());
   return sent;
  }

double ExtremeSinceOpen(const bool buy,const datetime opened,const MqlTick &tick)
  {
   int shift=iBarShift(_Symbol,InpSignalTimeframe,opened,false);
   if(shift<0) shift=0;
   int count=shift+1;
   double values[];
   ArraySetAsSeries(values,true);
   double extreme=(buy ? tick.bid : tick.ask);
   if(buy)
     {
      if(CopyHigh(_Symbol,InpSignalTimeframe,0,count,values)==count)
         extreme=MathMax(extreme,values[ArrayMaximum(values)]);
     }
   else
     {
      if(CopyLow(_Symbol,InpSignalTimeframe,0,count,values)==count)
         extreme=MathMin(extreme,values[ArrayMinimum(values)]);
     }
   return extreme;
  }

bool ModifyPosition(const ulong ticket,const double stop)
  {
   double target=PositionGetDouble(POSITION_TP);
   g_trade.SetExpertMagicNumber((ulong)InpMagic);
   g_trade.SetDeviationInPoints(InpMaximumDeviationPoints);
   if(!g_trade.PositionModify(ticket,NormalizePrice(stop),target))
     {
      Print("N5EMA stop modification failed: ",g_trade.ResultRetcodeDescription());
      return false;
     }
   return true;
  }

void ManagePosition()
  {
   ulong ticket=0;
   if(!SelectOurPosition(ticket)) return;
   datetime opened=(datetime)PositionGetInteger(POSITION_TIME);
   if(InpMaximumHoldingMinutes>0 && TimeCurrent()>=opened+InpMaximumHoldingMinutes*60)
     {
      g_trade.SetExpertMagicNumber((ulong)InpMagic);
      g_trade.SetDeviationInPoints(InpMaximumDeviationPoints);
      if(!g_trade.PositionClose(ticket,(ulong)InpMaximumDeviationPoints))
         Print("N5EMA time close failed: ",g_trade.ResultRetcodeDescription());
      return;
     }
   if(InpCloseAtSessionEnd && IsAtOrAfterSessionClose(TimeCurrent()))
     {
      g_trade.SetExpertMagicNumber((ulong)InpMagic);
      g_trade.SetDeviationInPoints(InpMaximumDeviationPoints);
      if(!g_trade.PositionClose(ticket,(ulong)InpMaximumDeviationPoints))
         Print("N5EMA session close failed: ",g_trade.ResultRetcodeDescription());
      return;
     }

   MqlTick tick;
   if(!SymbolInfoTick(_Symbol,tick)) return;
   bool buy=PositionGetInteger(POSITION_TYPE)==POSITION_TYPE_BUY;
   double open=PositionGetDouble(POSITION_PRICE_OPEN);
   double current=(buy ? tick.bid : tick.ask);
   double stop=PositionGetDouble(POSITION_SL);
   double initial_risk=InitialRiskForSelectedPosition();
   if(initial_risk<=0.0) return;
   double favorable=(buy ? current-open : open-current);
   double point=SymbolInfoDouble(_Symbol,SYMBOL_POINT);
   double broker_gap=MathMax((double)SymbolInfoInteger(_Symbol,SYMBOL_TRADE_STOPS_LEVEL),
                             (double)SymbolInfoInteger(_Symbol,SYMBOL_TRADE_FREEZE_LEVEL))*point;

   if(InpUseBreakEven && favorable>=InpBreakEvenTriggerR*initial_risk)
     {
      double candidate=open+(buy ? 1.0 : -1.0)*InpBreakEvenLockR*initial_risk;
      candidate=(buy ? MathMin(candidate,tick.bid-broker_gap) : MathMax(candidate,tick.ask+broker_gap));
      bool improves=(buy ? candidate>stop+point : stop<=0.0 || candidate<stop-point);
      if(improves) ModifyPosition(ticket,candidate);
     }

   if(InpUseMATrailing && g_trail_ma_handle!=INVALID_HANDLE && favorable>=InpTrailMAStartR*initial_risk)
     {
      double ma=0.0;
      if(ReadIndicatorValue(g_trail_ma_handle,1,ma) && ma>0.0)
        {
         double candidate=(buy ? MathMin(ma,tick.bid-broker_gap) : MathMax(ma,tick.ask+broker_gap));
         candidate=NormalizePrice(candidate);
         stop=PositionGetDouble(POSITION_SL);
         bool improves=(buy ? candidate>stop+point : stop<=0.0 || candidate<stop-point);
         if(improves) ModifyPosition(ticket,candidate);
        }
     }

   if(!InpUseATRTrailing) return;
   if(InpTrailStartR>0.0 && favorable<InpTrailStartR*initial_risk) return;
   double atr=0.0;
   if(!ReadIndicatorValue(g_atr_handle,0,atr)) return;
   double extreme=ExtremeSinceOpen(buy,opened,tick);
   double candidate=extreme+(buy ? -1.0 : 1.0)*InpTrailingATR*atr;
   candidate=(buy ? MathMin(candidate,tick.bid-broker_gap) : MathMax(candidate,tick.ask+broker_gap));
   candidate=NormalizePrice(candidate);
   stop=PositionGetDouble(POSITION_SL);
   bool improves=(buy ? candidate>stop+point : stop<=0.0 || candidate<stop-point);
   if(improves) ModifyPosition(ticket,candidate);
  }

bool DIAgrees(const int direction)
  {
   if(!InpRequireDIAgreement) return true;
   double plus_di[],minus_di[];
   // iADX buffers: 0=ADX, 1=+DI, 2=-DI. Shift 1 is the completed 09:30 NY signal bar.
   if(g_adx_handle==INVALID_HANDLE || CopyBuffer(g_adx_handle,1,1,1,plus_di)!=1 || CopyBuffer(g_adx_handle,2,1,1,minus_di)!=1) return false;
   return (direction>0 ? plus_di[0]>minus_di[0] : minus_di[0]>plus_di[0]);
  }

bool SignalQualityPasses(const int direction,const MqlRates &signal,const double ema,const double previous_ema,const double atr)
  {
   if(atr<=0.0) return false;
   double body=MathAbs(signal.close-signal.open);
   double range=signal.high-signal.low;
   double body_atr=body/atr;
   double body_fraction=(range>0.0 ? body/range : 0.0);
   double distance=MathAbs(signal.close-ema)/atr;
   if(InpMinimumBodyATR>0.0 && body_atr<InpMinimumBodyATR) return false;
   if(InpMaximumBodyATR>0.0 && body_atr>InpMaximumBodyATR) return false;
   if(InpMinimumBodyFraction>0.0 && body_fraction<InpMinimumBodyFraction) return false;
   if(InpMinimumEMADistanceATR>0.0 && distance<InpMinimumEMADistanceATR) return false;
   if(InpMaximumEMADistanceATR>0.0 && distance>InpMaximumEMADistanceATR) return false;
   if(InpRequireEMASlope && ((direction>0 && ema<=previous_ema) || (direction<0 && ema>=previous_ema))) return false;
   if(InpRelativeVolumePeriod>=2 && InpMinimumRelativeVolume>0.0 && RelativeVolume(1)<InpMinimumRelativeVolume) return false;
   return true;
  }

void ProcessNewBar()
  {
   MqlRates rates[];
   ArraySetAsSeries(rates,true);
   if(CopyRates(_Symbol,InpSignalTimeframe,0,3,rates)!=3) return;
   if(!IsNewYorkTime(rates[1].time,InpSignalHourNY,InpSignalMinuteNY)) return;
   int date_key=NewYorkDateKey(rates[1].time);
   ulong ticket=0;
   if(SelectOurPosition(ticket) || AlreadyTradedOnNewYorkDate(date_key) || !InpEnableTrading) return;

   double ema=0.0,previous_ema=0.0,atr=0.0;
   if(!ReadIndicatorValue(g_ema_handle,1,ema) || !ReadIndicatorValue(g_ema_handle,2,previous_ema) ||
      !ReadIndicatorValue(g_atr_handle,1,atr)) return;
   if(!CurrentSpreadPasses(atr)) return;
   int direction=(rates[1].close>ema ? 1 : (rates[1].close<ema ? -1 : 0));
   if(direction==0 || (direction>0 && !InpAllowLong) || (direction<0 && !InpAllowShort)) return;
   if(!SignalQualityPasses(direction,rates[1],ema,previous_ema,atr)) return;
   if(!DIAgrees(direction)) return;
   SendEntry(direction,atr,rates[1],SelectedRewardRisk(rates[1],atr));
  }

int OnInit()
  {
 if(!FP_InputsValid(InpRiskPercent))return INIT_PARAMETERS_INCORRECT;
   if(!DTS_InputsValid()) return INIT_PARAMETERS_INCORRECT;
   bool timeframe_valid=(InpSignalTimeframe==PERIOD_M1 || InpSignalTimeframe==PERIOD_M5 ||
                         InpSignalTimeframe==PERIOD_M15 || InpSignalTimeframe==PERIOD_M30);
   if(!timeframe_valid || InpSignalHourNY<0 || InpSignalHourNY>23 || InpSignalMinuteNY<0 || InpSignalMinuteNY>59 ||
      InpEMAPeriod<2 || InpATRPeriod<2 || InpInitialStopATR<=0.0 || InpSignalStopBufferATR<0.0 ||
      InpRewardRisk<=0.0 || InpAdaptiveStrongRR<=0.0 || InpAdaptiveStrongBodyATR<=0.0 ||
      InpTrailingATR<=0.0 || InpTrailStartR<0.0 || InpBreakEvenTriggerR<0.0 || InpBreakEvenLockR<0.0 ||
      InpRiskPercent<=0.0 || InpRiskPercent>10.0 || InpMaximumHoldingMinutes<0 ||
      InpCloseHourNY<0 || InpCloseHourNY>23 || InpCloseMinuteNY<0 || InpCloseMinuteNY>59 ||
      InpMinimumBodyATR<0.0 || InpMaximumBodyATR<0.0 || InpMinimumBodyFraction<0.0 || InpMinimumBodyFraction>1.0 ||
      InpMinimumEMADistanceATR<0.0 || InpMaximumEMADistanceATR<0.0 || InpRelativeVolumePeriod<0 || InpMinimumRelativeVolume<0.0 || InpDIPeriod<2)
      return INIT_PARAMETERS_INCORRECT;
   g_ema_handle=iMA(_Symbol,InpSignalTimeframe,InpEMAPeriod,0,MODE_EMA,PRICE_CLOSE);
   g_atr_handle=iATR(_Symbol,InpSignalTimeframe,InpATRPeriod);
   if(g_ema_handle==INVALID_HANDLE || g_atr_handle==INVALID_HANDLE) return INIT_FAILED;
   if(InpRequireDIAgreement)
     {
      g_adx_handle=iADX(_Symbol,InpSignalTimeframe,InpDIPeriod);
      if(g_adx_handle==INVALID_HANDLE) return INIT_FAILED;
     }
   if(InpUseMATrailing)
     {
      if(InpTrailMAPeriod<2 || InpTrailMAStartR<0.0) return INIT_PARAMETERS_INCORRECT;
      g_trail_ma_handle=iMA(_Symbol,InpSignalTimeframe,InpTrailMAPeriod,0,InpTrailMAMethod,PRICE_CLOSE);
      if(g_trail_ma_handle==INVALID_HANDLE) return INIT_FAILED;
     }
   if(InpStopMode==N5_STOP_PERCENT && (InpInitialStopPercent<=0.0 || InpInitialStopPercent>10.0)) return INIT_PARAMETERS_INCORRECT;
   g_trade.SetExpertMagicNumber((ulong)InpMagic);
   g_trade.SetTypeFillingBySymbol(_Symbol);
   g_last_bar_time=iTime(_Symbol,InpSignalTimeframe,0);
   FP_Heartbeat(InpMagic,true);return INIT_SUCCEEDED;
  }

void OnDeinit(const int reason)
  {
   if(g_ema_handle!=INVALID_HANDLE) IndicatorRelease(g_ema_handle);
   if(g_atr_handle!=INVALID_HANDLE) IndicatorRelease(g_atr_handle);
   if(g_adx_handle!=INVALID_HANDLE) IndicatorRelease(g_adx_handle);
   if(g_trail_ma_handle!=INVALID_HANDLE) IndicatorRelease(g_trail_ma_handle);
  }

void OnTick()
  {
 if(!FP_BindingOK())return;FP_Heartbeat(InpMagic);
   DTS_ManageDynamicTrailing(InpMagic);
   ManagePosition();
   datetime bar_time=iTime(_Symbol,InpSignalTimeframe,0);
   if(bar_time<=0 || bar_time==g_last_bar_time) return;
   g_last_bar_time=bar_time;
   ProcessNewBar();
  }
