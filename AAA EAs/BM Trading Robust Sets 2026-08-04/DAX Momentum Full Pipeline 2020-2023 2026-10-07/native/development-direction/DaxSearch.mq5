
input int InpCase=0;
input string InpTag="dax-pipeline";
input bool InpVerbose=false;
input double InpRiskPct=1.0;
int ResearchAnchor=0,ResearchSkipWeekday=0;
double ResearchADXMinimum=0,ResearchADXMaximum=0;
bool ResearchRequireBodyDirection=false,ResearchBerlinClose=false;
int dax_equity_file=INVALID_HANDLE,dax_quotes_file=INVALID_HANDLE;
datetime dax_minute=0;
long dax_ticks=0;
int dax_failed_entries=0,dax_failed_updates=0,dax_closed_updates=0;
string DaxTag(){return InpTag+"-"+(string)InpCase;}
double Cases[][60]={
{5,9,30,12,1,1,0,0,0,0,0,0,0,0,1,14,14,2,4,0.1,0,1,3,0,1,3,0.6,1,4,1,0,1,0,0,0,15,55,0,200,1,0.5,1,0,1,1,0,0,862020,50,0,0.5,0.2,0,0,7,15,0,0,0,0},
{5,9,30,12,1,1,0,0,0,0,0,0,0,0,1,14,14,2,4,0.1,0,1,3,0,1,3,0.6,1,4,1,0,1,0,0,0,15,55,0,200,1,0.5,1,0,1,1,0,0,862020,50,0,0.5,0.2,0,0,7,15,0,0,0,0},
{5,9,30,12,1,1,0,0,0,0,0,0,0,0,1,14,14,2,4,0.1,0,0,2.5,0,1,3,0.6,1,6,1,0,1,0,0,0,15,55,0,200,1,0.5,1,0,1,1,0,0,862020,50,0,0.5,0.2,0,0,0,0,0,0,0,0},
{5,9,30,12,1,1,0,0,0,0,0,0,0,0,1,14,14,2,4,0.1,0,1,3,0,1,3,0.6,1,4,1,0,1,0,0,0,15,55,0,200,1,0.5,1,0,1,1,0,0,862020,50,0,0.5,0.2,0,0,7,15,0,0,1,0},
{5,9,30,12,1,1,0,0,0,0,0,0,0,0,1,14,14,2,4,0.1,0,1,3,0,1,3,0.6,1,4,1,0,1,0,0,0,15,55,0,200,1,0.5,1,0,1,1,0,0,862020,50,0,0.5,0.2,0,0,7,15,0,0,2,0},
{5,9,30,12,1,1,0,0,0,0,0,0,0,0,1,14,14,2,4,0.1,0,1,3,0,1,3,0.6,1,4,1,0,1,0,0,0,15,55,0,200,1,0.5,1,0,1,1,0,0,862020,50,0,0.5,0.2,0,0,7,15,0,0,3,0},
{5,9,30,12,1,0,0,0,0,0,0,0,0,0,1,14,14,2,4,0.1,0,1,3,0,1,3,0.6,1,4,1,0,1,0,0,0,15,55,0,200,1,0.5,1,0,1,1,0,0,862020,50,0,0.5,0.2,0,0,7,15,0,0,0,0},
{5,9,30,12,1,0,0,0,0,0,0,0,0,0,1,14,14,2,4,0.1,0,1,3,0,1,3,0.6,1,4,1,0,1,0,0,0,15,55,0,200,1,0.5,1,0,1,1,0,0,862020,50,0,0.5,0.2,0,0,7,15,0,0,1,0},
{5,9,30,12,1,0,0,0,0,0,0,0,0,0,1,14,14,2,4,0.1,0,1,3,0,1,3,0.6,1,4,1,0,1,0,0,0,15,55,0,200,1,0.5,1,0,1,1,0,0,862020,50,0,0.5,0.2,0,0,7,15,0,0,2,0},
{5,9,30,12,1,0,0,0,0,0,0,0,0,0,1,14,14,2,4,0.1,0,1,3,0,1,3,0.6,1,4,1,0,1,0,0,0,15,55,0,200,1,0.5,1,0,1,1,0,0,862020,50,0,0.5,0.2,0,0,7,15,0,0,3,0},
{5,9,30,12,0,1,0,0,0,0,0,0,0,0,1,14,14,2,4,0.1,0,1,3,0,1,3,0.6,1,4,1,0,1,0,0,0,15,55,0,200,1,0.5,1,0,1,1,0,0,862020,50,0,0.5,0.2,0,0,7,15,0,0,0,0},
{5,9,30,12,0,1,0,0,0,0,0,0,0,0,1,14,14,2,4,0.1,0,1,3,0,1,3,0.6,1,4,1,0,1,0,0,0,15,55,0,200,1,0.5,1,0,1,1,0,0,862020,50,0,0.5,0.2,0,0,7,15,0,0,1,0},
{5,9,30,12,0,1,0,0,0,0,0,0,0,0,1,14,14,2,4,0.1,0,1,3,0,1,3,0.6,1,4,1,0,1,0,0,0,15,55,0,200,1,0.5,1,0,1,1,0,0,862020,50,0,0.5,0.2,0,0,7,15,0,0,2,0},
{5,9,30,12,0,1,0,0,0,0,0,0,0,0,1,14,14,2,4,0.1,0,1,3,0,1,3,0.6,1,4,1,0,1,0,0,0,15,55,0,200,1,0.5,1,0,1,1,0,0,862020,50,0,0.5,0.2,0,0,7,15,0,0,3,0},
{5,9,30,12,1,1,0,0,0,0,0,0,0,0,1,14,14,2,4,0.1,0,1,3,0,1,3,0.6,1,4,1,0,1,0,0,0,15,55,0,200,1,0.5,1,0,1,1,0,0,862020,50,0,0.5,0.2,0,0,7,15,0,0,1,0},
{5,9,30,12,1,1,0,0,0,0,0,0,0,0,1,14,14,2,4,0.1,0,1,3,0,1,3,0.6,1,4,1,0,1,0,0,0,15,55,0,200,1,0.5,1,0,1,1,0,0,862020,50,0,0.5,0.2,0,0,7,15,0,0,2,0},
{5,9,30,12,1,1,0,0,0,0,0,0,0,0,1,14,14,2,4,0.1,0,1,3,0,1,3,0.6,1,4,1,0,1,0,0,0,15,55,0,200,1,0.5,1,0,1,1,0,0,862020,50,0,0.5,0.2,0,0,7,15,0,0,3,0},
{5,9,30,12,1,0,0,0,0,0,0,0,0,0,1,14,14,2,4,0.1,0,1,3,0,1,3,0.6,1,4,1,0,1,0,0,0,15,55,0,200,1,0.5,1,0,1,1,0,0,862020,50,0,0.5,0.2,0,0,7,15,0,0,0,0},
{5,9,30,12,1,0,0,0,0,0,0,0,0,0,1,14,14,2,4,0.1,0,1,3,0,1,3,0.6,1,4,1,0,1,0,0,0,15,55,0,200,1,0.5,1,0,1,1,0,0,862020,50,0,0.5,0.2,0,0,7,15,0,0,1,0},
{5,9,30,12,1,0,0,0,0,0,0,0,0,0,1,14,14,2,4,0.1,0,1,3,0,1,3,0.6,1,4,1,0,1,0,0,0,15,55,0,200,1,0.5,1,0,1,1,0,0,862020,50,0,0.5,0.2,0,0,7,15,0,0,2,0},
{5,9,30,12,1,0,0,0,0,0,0,0,0,0,1,14,14,2,4,0.1,0,1,3,0,1,3,0.6,1,4,1,0,1,0,0,0,15,55,0,200,1,0.5,1,0,1,1,0,0,862020,50,0,0.5,0.2,0,0,7,15,0,0,3,0},
{5,9,30,12,0,1,0,0,0,0,0,0,0,0,1,14,14,2,4,0.1,0,1,3,0,1,3,0.6,1,4,1,0,1,0,0,0,15,55,0,200,1,0.5,1,0,1,1,0,0,862020,50,0,0.5,0.2,0,0,7,15,0,0,0,0},
{5,9,30,12,0,1,0,0,0,0,0,0,0,0,1,14,14,2,4,0.1,0,1,3,0,1,3,0.6,1,4,1,0,1,0,0,0,15,55,0,200,1,0.5,1,0,1,1,0,0,862020,50,0,0.5,0.2,0,0,7,15,0,0,1,0},
{5,9,30,12,0,1,0,0,0,0,0,0,0,0,1,14,14,2,4,0.1,0,1,3,0,1,3,0.6,1,4,1,0,1,0,0,0,15,55,0,200,1,0.5,1,0,1,1,0,0,862020,50,0,0.5,0.2,0,0,7,15,0,0,2,0},
{5,9,30,12,0,1,0,0,0,0,0,0,0,0,1,14,14,2,4,0.1,0,1,3,0,1,3,0.6,1,4,1,0,1,0,0,0,15,55,0,200,1,0.5,1,0,1,1,0,0,862020,50,0,0.5,0.2,0,0,7,15,0,0,3,0}
};
#property copyright "Calyx Nasdaq momentum research"
#property version   "2.10"
#property strict
// Research copy 2026-09-25 of Nasdaq 5M Candle Momentum DI EA v2.10 (production source unchanged).
// Adds, default OFF: N5_STOP_PERCENT initial stop and slow-MA trailing, to recreate the management seen in the
// user's QUANT_LAB "Momentum v2.0" video (0.60% stop, no target, stop trailed on a slow MA, held overnight).

#include <Trade/Trade.mqh>
#include "SafeRegimeFilter.mqh"
#include "DynamicTrailingSessionFilter.mqh"
#include "CalyxAdaptivePortfolio.mqh"

enum ENUM_N5_STOP_MODE
  {
   N5_STOP_ATR=0,
   N5_STOP_SIGNAL_CANDLE=1,
   N5_STOP_PERCENT=2
  };

ENUM_TIMEFRAMES InpSignalTimeframe=PERIOD_M5;
int    InpSignalHourNY=9;
int    InpSignalMinuteNY=30;
int    InpEMAPeriod=12;
bool   InpAllowLong=true;
bool   InpAllowShort=true;
bool   InpRequireEMASlope=false;
double InpMinimumBodyATR=0.00;
double InpMaximumBodyATR=0.00;
double InpMinimumBodyFraction=0.00;
double InpMinimumEMADistanceATR=0.00;
double InpMaximumEMADistanceATR=0.00;
int    InpRelativeVolumePeriod=0;
double InpMinimumRelativeVolume=0.00;

bool   InpRequireDIAgreement=false; // true: longs need +DI>-DI, shorts need -DI>+DI on the closed signal bar
int    InpDIPeriod=14;

int               InpATRPeriod=14;
ENUM_N5_STOP_MODE InpStopMode=N5_STOP_ATR;
double            InpInitialStopATR=4.00;
double            InpSignalStopBufferATR=0.10;
double            InpMaximumStopATR=0.00;
bool              InpUseFixedTarget=false;
double            InpRewardRisk=2.00;
bool              InpUseAdaptiveRR=false;
double            InpAdaptiveStrongBodyATR=1.00;
double            InpAdaptiveStrongRR=3.00;
double            InpInitialStopPercent=0.60;   // used only by N5_STOP_PERCENT (percent of entry price)

bool   InpUseATRTrailing=true;
double InpTrailingATR=6.00;
double InpTrailStartR=1.00;
bool   InpUseBreakEven=false;
double InpBreakEvenTriggerR=1.00;
double InpBreakEvenLockR=0.00;
int    InpMaximumHoldingMinutes=0;
bool   InpCloseAtSessionEnd=true;
int    InpCloseHourNY=15;
int    InpCloseMinuteNY=55;
bool   InpUseMATrailing=false;        // research: stop follows a slow MA (closed bar), never loosened
int    InpTrailMAPeriod=200;
ENUM_MA_METHOD InpTrailMAMethod=MODE_EMA;
double InpTrailMAStartR=0.50;         // start trailing once open profit >= this many R

bool InpAutoServerUtcOffsetLive=true;
int  InpServerUtcOffsetHours=0;

bool   InpEnableTrading=true;
double InpRiskPercent=1.00;
bool   InpAdaptivePortfolioControls=false;
double InpMaximumSpreadATR=0.00;
long   InpMagic=862020;
int    InpMaximumDeviationPoints=50;

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
      if(InpVerbose) PrintFormat("Risk sizing rounded %.8f lots up to broker-valid %.8f lots; actual risk exceeds the selected target.",raw_lots,lots);
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
   TimeToStruct(ResearchBerlinClose?ServerToBerlin(server_time):ServerToNewYork(server_time),ny);
   if(ResearchBerlinClose) return ny.day_of_week>=1 && ny.day_of_week<=5 && (ny.hour>17 || (ny.hour==17 && ny.min>=25));
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
      if(InpVerbose) Print("N5EMA skipped: risk-sized volume is below the broker minimum.");
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
   else {dax_failed_entries++; if(InpVerbose) Print("N5EMA order rejected: ",g_trade.ResultRetcodeDescription());}
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
      dax_failed_updates++; if(g_trade.ResultRetcode()==TRADE_RETCODE_MARKET_CLOSED) dax_closed_updates++;
      if(InpVerbose) Print("N5EMA stop modification failed: ",g_trade.ResultRetcodeDescription());
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
         if(InpVerbose) Print("N5EMA time close failed: ",g_trade.ResultRetcodeDescription());
      return;
     }
   if(InpCloseAtSessionEnd && IsAtOrAfterSessionClose(TimeCurrent()))
     {
      g_trade.SetExpertMagicNumber((ulong)InpMagic);
      g_trade.SetDeviationInPoints(InpMaximumDeviationPoints);
      if(!g_trade.PositionClose(ticket,(ulong)InpMaximumDeviationPoints))
         if(InpVerbose) Print("N5EMA session close failed: ",g_trade.ResultRetcodeDescription());
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
   if(!DaxSignalTime(rates[1].time)) return;
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
   if(!DaxQuality(direction,rates[1])) return;
   if(!DIAgrees(direction)) return;
   SendEntry(direction,atr,rates[1],SelectedRewardRisk(rates[1],atr));
  }

int OnInit()
  {
   if(!MQLInfoInteger(MQL_TESTER) || InpCase<0 || InpCase>=ArrayRange(Cases,0)) return INIT_PARAMETERS_INCORRECT;
   DaxApply();
   if(!DaxOpenAudit()) return INIT_FAILED;
   if(!DTS_InputsValid()) return INIT_PARAMETERS_INCORRECT;
   bool timeframe_valid=(InpSignalTimeframe==PERIOD_M1 || InpSignalTimeframe==PERIOD_M3 || InpSignalTimeframe==PERIOD_M5 || InpSignalTimeframe==PERIOD_M10 ||
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
   if(InpRequireDIAgreement || ResearchADXMinimum>0 || ResearchADXMaximum>0)
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
   return INIT_SUCCEEDED;
  }

void OnDeinit(const int reason)
  {
   if(dax_equity_file!=INVALID_HANDLE) FileClose(dax_equity_file);
   if(dax_quotes_file!=INVALID_HANDLE) FileClose(dax_quotes_file);
   if(g_ema_handle!=INVALID_HANDLE) IndicatorRelease(g_ema_handle);
   if(g_atr_handle!=INVALID_HANDLE) IndicatorRelease(g_atr_handle);
   if(g_adx_handle!=INVALID_HANDLE) IndicatorRelease(g_adx_handle);
   if(g_trail_ma_handle!=INVALID_HANDLE) IndicatorRelease(g_trail_ma_handle);
  }

void OnTick()
  {
   DaxSnapshot();
   DTS_ManageDynamicTrailing(InpMagic);
   ManagePosition();
   datetime bar_time=iTime(_Symbol,InpSignalTimeframe,0);
   if(bar_time<=0 || bar_time==g_last_bar_time) return;
   g_last_bar_time=bar_time;
   ProcessNewBar();
  }

void DaxApply(){
 InpSignalTimeframe=(ENUM_TIMEFRAMES)Cases[InpCase][0];
 InpSignalHourNY=(int)Cases[InpCase][1];
 InpSignalMinuteNY=(int)Cases[InpCase][2];
 InpEMAPeriod=(int)Cases[InpCase][3];
 InpAllowLong=(bool)Cases[InpCase][4];
 InpAllowShort=(bool)Cases[InpCase][5];
 InpRequireEMASlope=(bool)Cases[InpCase][6];
 InpMinimumBodyATR=(double)Cases[InpCase][7];
 InpMaximumBodyATR=(double)Cases[InpCase][8];
 InpMinimumBodyFraction=(double)Cases[InpCase][9];
 InpMinimumEMADistanceATR=(double)Cases[InpCase][10];
 InpMaximumEMADistanceATR=(double)Cases[InpCase][11];
 InpRelativeVolumePeriod=(int)Cases[InpCase][12];
 InpMinimumRelativeVolume=(double)Cases[InpCase][13];
 InpRequireDIAgreement=(bool)Cases[InpCase][14];
 InpDIPeriod=(int)Cases[InpCase][15];
 InpATRPeriod=(int)Cases[InpCase][16];
 InpStopMode=(ENUM_N5_STOP_MODE)Cases[InpCase][17];
 InpInitialStopATR=(double)Cases[InpCase][18];
 InpSignalStopBufferATR=(double)Cases[InpCase][19];
 InpMaximumStopATR=(double)Cases[InpCase][20];
 InpUseFixedTarget=(bool)Cases[InpCase][21];
 InpRewardRisk=(double)Cases[InpCase][22];
 InpUseAdaptiveRR=(bool)Cases[InpCase][23];
 InpAdaptiveStrongBodyATR=(double)Cases[InpCase][24];
 InpAdaptiveStrongRR=(double)Cases[InpCase][25];
 InpInitialStopPercent=(double)Cases[InpCase][26];
 InpUseATRTrailing=(bool)Cases[InpCase][27];
 InpTrailingATR=(double)Cases[InpCase][28];
 InpTrailStartR=(double)Cases[InpCase][29];
 InpUseBreakEven=(bool)Cases[InpCase][30];
 InpBreakEvenTriggerR=(double)Cases[InpCase][31];
 InpBreakEvenLockR=(double)Cases[InpCase][32];
 InpMaximumHoldingMinutes=(int)Cases[InpCase][33];
 InpCloseAtSessionEnd=(bool)Cases[InpCase][34];
 InpCloseHourNY=(int)Cases[InpCase][35];
 InpCloseMinuteNY=(int)Cases[InpCase][36];
 InpUseMATrailing=(bool)Cases[InpCase][37];
 InpTrailMAPeriod=(int)Cases[InpCase][38];
 InpTrailMAMethod=(ENUM_MA_METHOD)Cases[InpCase][39];
 InpTrailMAStartR=(double)Cases[InpCase][40];
 InpAutoServerUtcOffsetLive=(bool)Cases[InpCase][41];
 InpServerUtcOffsetHours=(int)Cases[InpCase][42];
 InpEnableTrading=(bool)Cases[InpCase][43];
 InpRiskPercent=(double)Cases[InpCase][44];
 InpAdaptivePortfolioControls=(bool)Cases[InpCase][45];
 InpMaximumSpreadATR=(double)Cases[InpCase][46];
 InpMagic=(long)Cases[InpCase][47];
 InpMaximumDeviationPoints=(int)Cases[InpCase][48];
 InpUseDynamicTrailingSL=(bool)Cases[InpCase][49];
 InpDynamicTriggerFraction=(double)Cases[InpCase][50];
 InpDynamicLockFraction=(double)Cases[InpCase][51];
 InpResearchSession=(ENUM_DTS_SESSION_MODE)Cases[InpCase][52];
 InpResearchBrokerUtcOffsetMinutes=(int)Cases[InpCase][53];
 ResearchAnchor=(int)Cases[InpCase][54];
 ResearchADXMinimum=(double)Cases[InpCase][55];
 ResearchADXMaximum=(double)Cases[InpCase][56];
 ResearchRequireBodyDirection=(bool)Cases[InpCase][57];
 ResearchSkipWeekday=(int)Cases[InpCase][58];
 ResearchBerlinClose=(bool)Cases[InpCase][59];
 InpRiskPercent=InpRiskPct;
}

datetime ServerToBerlin(const datetime server_time){
 datetime utc=server_time-ServerUtcOffsetSeconds();MqlDateTime x;TimeToStruct(utc,x);
 MqlDateTime march,october;TimeToStruct(BuildUtcTime(x.year,3,31,1),march);TimeToStruct(BuildUtcTime(x.year,10,31,1),october);
 datetime begin=BuildUtcTime(x.year,3,31-march.day_of_week,1),end=BuildUtcTime(x.year,10,31-october.day_of_week,1);
 return utc+(utc>=begin && utc<end?2:1)*3600;
}
bool DaxSignalTime(const datetime server_time){
 if(ResearchAnchor==0)return IsNewYorkTime(server_time,InpSignalHourNY,InpSignalMinuteNY);
 if(ResearchAnchor==5)return IsNewYorkTime(server_time,10,0);
 MqlDateTime b;TimeToStruct(ServerToBerlin(server_time),b);
 if(b.day_of_week<1 || b.day_of_week>5)return false;
 int hour=9,minute=0;
 if(ResearchAnchor==1)hour=8;
 if(ResearchAnchor==3)minute=30;
 if(ResearchAnchor==4)hour=10;
 if(ResearchAnchor==6){hour=8;minute=30;}
 if(ResearchAnchor==7){hour=15;minute=30;}
 return b.hour==hour && b.min==minute;
}
bool DaxQuality(const int direction,const MqlRates &signal){
 if(ResearchRequireBodyDirection && (direction>0?signal.close<=signal.open:signal.close>=signal.open))return false;
 MqlDateTime d;TimeToStruct(ServerToBerlin(signal.time),d);
 if((d.day_of_week==1 && (ResearchSkipWeekday==1 || ResearchSkipWeekday==3)) || (d.day_of_week==5 && (ResearchSkipWeekday==2 || ResearchSkipWeekday==3)))return false;
 if(ResearchADXMinimum>0 || ResearchADXMaximum>0){
  double a=0;if(!ReadIndicatorValue(g_adx_handle,1,a))return false;
  if(ResearchADXMinimum>0 && a<ResearchADXMinimum)return false;
  if(ResearchADXMaximum>0 && a>ResearchADXMaximum)return false;
 }
 return true;
}
void DaxSnapshot(){
 dax_ticks++;datetime now=TimeCurrent();
 if(dax_equity_file==INVALID_HANDLE || now/60==dax_minute)return;
 dax_minute=now/60;FileWrite(dax_equity_file,(long)now,AccountInfoDouble(ACCOUNT_BALANCE),AccountInfoDouble(ACCOUNT_EQUITY));
}
bool DaxOpenAudit(){
 if(!InpVerbose)return true;
 dax_equity_file=FileOpen(DaxTag()+"-equity.csv",FILE_WRITE|FILE_CSV|FILE_COMMON|FILE_ANSI,',');
 dax_quotes_file=FileOpen(DaxTag()+"-quotes.csv",FILE_WRITE|FILE_CSV|FILE_COMMON|FILE_ANSI,',');
 if(dax_equity_file==INVALID_HANDLE || dax_quotes_file==INVALID_HANDLE)return false;
 FileWrite(dax_equity_file,"epoch","balance","equity");
 FileWrite(dax_quotes_file,"deal","position_id","epoch","entry","bid","ask","volume","spread_cash");
 return true;
}
double OnTester(){
 HistorySelect(0,TimeCurrent());
 int out=FileOpen(DaxTag()+"-deals.csv",FILE_WRITE|FILE_CSV|FILE_COMMON|FILE_ANSI,',');
 if(out==INVALID_HANDLE)return -1e99;
 FileWrite(out,"ticket","position_id","epoch","entry","type","volume","price","profit","commission","swap","fee","reason","initial_sl","initial_tp");
 ulong owned[];
 for(int i=0;i<HistoryDealsTotal();i++){
  ulong deal=HistoryDealGetTicket(i);if(deal==0 || HistoryDealGetInteger(deal,DEAL_MAGIC)!=InpMagic || HistoryDealGetInteger(deal,DEAL_ENTRY)!=DEAL_ENTRY_IN)continue;
  int n=ArraySize(owned);ArrayResize(owned,n+1);owned[n]=(ulong)HistoryDealGetInteger(deal,DEAL_POSITION_ID);
 }
 for(int i=0;i<HistoryDealsTotal();i++){
  ulong deal=HistoryDealGetTicket(i);if(deal==0)continue;
  ulong id=(ulong)HistoryDealGetInteger(deal,DEAL_POSITION_ID);bool ours=false;
  for(int j=0;j<ArraySize(owned);j++)if(owned[j]==id){ours=true;break;}if(!ours)continue;
  ulong order=(ulong)HistoryDealGetInteger(deal,DEAL_ORDER);
  FileWrite(out,deal,id,(long)HistoryDealGetInteger(deal,DEAL_TIME),HistoryDealGetInteger(deal,DEAL_ENTRY),HistoryDealGetInteger(deal,DEAL_TYPE),
   HistoryDealGetDouble(deal,DEAL_VOLUME),HistoryDealGetDouble(deal,DEAL_PRICE),HistoryDealGetDouble(deal,DEAL_PROFIT),HistoryDealGetDouble(deal,DEAL_COMMISSION),
   HistoryDealGetDouble(deal,DEAL_SWAP),HistoryDealGetDouble(deal,DEAL_FEE),HistoryDealGetInteger(deal,DEAL_REASON),HistoryOrderGetDouble(order,ORDER_SL),HistoryOrderGetDouble(order,ORDER_TP));
 }
 FileClose(out);
 out=FileOpen(DaxTag()+"-stats.csv",FILE_WRITE|FILE_CSV|FILE_COMMON|FILE_ANSI,',');if(out==INVALID_HANDLE)return -1e99;
 ulong selected=0;
 FileWrite(out,"net","equity_dd","balance_dd","failed_entries","failed_updates","market_closed_updates","balance","open_position","last_quote_epoch","ticks","mt5_sharpe","trades");
 FileWrite(out,TesterStatistics(STAT_PROFIT),TesterStatistics(STAT_EQUITY_DDREL_PERCENT),TesterStatistics(STAT_BALANCE_DDREL_PERCENT),
  dax_failed_entries,dax_failed_updates,dax_closed_updates,AccountInfoDouble(ACCOUNT_BALANCE),(int)SelectOurPosition(selected),(long)TimeCurrent(),dax_ticks,TesterStatistics(STAT_SHARPE_RATIO),TesterStatistics(STAT_TRADES));
 FileClose(out);
 if(dax_equity_file!=INVALID_HANDLE){FileWrite(dax_equity_file,(long)TimeCurrent(),AccountInfoDouble(ACCOUNT_BALANCE),AccountInfoDouble(ACCOUNT_EQUITY));FileFlush(dax_equity_file);}
 return TesterStatistics(STAT_PROFIT);
}
void OnTradeTransaction(const MqlTradeTransaction &trans,const MqlTradeRequest &request,const MqlTradeResult &result){
 if(dax_quotes_file==INVALID_HANDLE || trans.type!=TRADE_TRANSACTION_DEAL_ADD || trans.deal==0)return;
 if(!HistoryDealSelect(trans.deal))return;
 long magic=HistoryDealGetInteger(trans.deal,DEAL_MAGIC),entry=HistoryDealGetInteger(trans.deal,DEAL_ENTRY);
 if(entry==DEAL_ENTRY_IN && magic!=InpMagic)return;
 MqlTick tick;if(!SymbolInfoTick(_Symbol,tick))return;
 double qty=HistoryDealGetDouble(trans.deal,DEAL_VOLUME),cash=0;
 ENUM_ORDER_TYPE kind=HistoryDealGetInteger(trans.deal,DEAL_TYPE)==DEAL_TYPE_BUY?ORDER_TYPE_BUY:ORDER_TYPE_SELL;
 bool priced=OrderCalcProfit(kind,_Symbol,qty,tick.bid,tick.ask,cash);
 FileWrite(dax_quotes_file,trans.deal,HistoryDealGetInteger(trans.deal,DEAL_POSITION_ID),(long)TimeCurrent(),entry,tick.bid,tick.ask,qty,priced?MathAbs(cash):-1);
}
