#property copyright "Calyx Nasdaq momentum research"
#property version   "2.00"
#property strict

#include <Trade/Trade.mqh>
#include "SafeRegimeFilter.mqh"
#include "DynamicTrailingSessionFilter.mqh"
#include "..\..\..\_Shared\CalyxAdaptivePortfolio.mqh"

enum ENUM_N5_STOP_MODE
  {
   N5_STOP_ATR=0,
   N5_STOP_SIGNAL_CANDLE=1
  };

input group "Signal"
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

input group "Stop and target"
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

input group "Position management"
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

input group "Time conversion"
input bool InpAutoServerUtcOffsetLive=true;
input int  InpServerUtcOffsetHours=0;

input group "Risk and execution"
input bool   InpEnableTrading=true;
input double InpRiskPercent=1.00;
input bool   InpAdaptivePortfolioControls=false;
input double InpMaximumSpreadATR=0.00;
input long   InpMagic=862020;
input int    InpMaximumDeviationPoints=50;

CTrade g_trade;
int g_ema_handle=INVALID_HANDLE;
int g_atr_handle=INVALID_HANDLE;
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
   // The research executable is hard-capped at one percent per trade.
   double applied_risk=MathMin(InpRiskPercent,1.00);
   const double adaptive=CalyxAdaptiveRiskMultiplier(InpAdaptivePortfolioControls,InpMagic);
   if(adaptive<=0.0) return 0.0;
   double cash=AccountInfoDouble(ACCOUNT_EQUITY)*applied_risk*adaptive/100.0;
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
   SendEntry(direction,atr,rates[1],SelectedRewardRisk(rates[1],atr));
  }

int OnInit()
  {
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
      InpMinimumEMADistanceATR<0.0 || InpMaximumEMADistanceATR<0.0 || InpRelativeVolumePeriod<0 || InpMinimumRelativeVolume<0.0)
      return INIT_PARAMETERS_INCORRECT;
   g_ema_handle=iMA(_Symbol,InpSignalTimeframe,InpEMAPeriod,0,MODE_EMA,PRICE_CLOSE);
   g_atr_handle=iATR(_Symbol,InpSignalTimeframe,InpATRPeriod);
   if(g_ema_handle==INVALID_HANDLE || g_atr_handle==INVALID_HANDLE) return INIT_FAILED;
   g_trade.SetExpertMagicNumber((ulong)InpMagic);
   g_trade.SetTypeFillingBySymbol(_Symbol);
   g_last_bar_time=iTime(_Symbol,InpSignalTimeframe,0);
   return INIT_SUCCEEDED;
  }

void OnDeinit(const int reason)
  {
   if(g_ema_handle!=INVALID_HANDLE) IndicatorRelease(g_ema_handle);
   if(g_atr_handle!=INVALID_HANDLE) IndicatorRelease(g_atr_handle);
  }

void OnTick()
  {
   DTS_ManageDynamicTrailing(InpMagic);
   ManagePosition();
   datetime bar_time=iTime(_Symbol,InpSignalTimeframe,0);
   if(bar_time<=0 || bar_time==g_last_bar_time) return;
   g_last_bar_time=bar_time;
   ProcessNewBar();
  }
