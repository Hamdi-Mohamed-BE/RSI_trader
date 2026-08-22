#property copyright "Codex research implementation from supplied Asia second-hour description"
#property version   "1.00"
#property strict

#include <Trade/Trade.mqh>

input group "Asia second-hour model (UTC)"
input bool   InpEnableTrading=true;
input int    InpSecondHourUTC=1;
input int    InpMinimumDriveMinutes=20;
input int    InpSweepDeadlineMinute=30;
input double InpMinimumDriveEfficiency=0.60;
input int    InpStructureLookbackBars=5;
input double InpDisplacementBodyATR=0.50;
input bool   InpRequireFVG=false;
input int    InpEntryExpiryMinutes=20;

input group "Stops and extension target"
input int    InpATRPeriod=14;
input double InpStopBufferATR=0.10;
input double InpTargetPreviousRangeFraction=0.50;
input double InpMinimumRewardRisk=1.00;
input int    InpFlatHourUTC=8;

input group "Risk and execution"
input double InpRiskPercent=1.00;
input long   InpMagic=862103;
input int    InpMaximumDeviationPoints=50;
input bool   InpAutoServerUtcOffsetLive=true;
input int    InpServerUtcOffsetHours=0;

CTrade g_trade;
int g_atr_handle=INVALID_HANDLE;
datetime g_last_m1=0;
int g_date_key=0;
double g_previous_high=0.0;
double g_previous_low=0.0;
double g_hour_open=0.0;
double g_hour_high=0.0;
double g_hour_low=0.0;
int g_qualified_direction=0;
int g_setup_direction=0;
double g_setup_entry=0.0;
double g_setup_stop=0.0;
datetime g_setup_created=0;

double NormalizePrice(const double price)
{
   return NormalizeDouble(price,(int)SymbolInfoInteger(_Symbol,SYMBOL_DIGITS));
}

double NormalizeLots(const double raw)
{
   double minimum=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MIN);
   double maximum=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MAX);
   double step=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_STEP);
   if(step<=0.0) return 0.0;
   double lots=MathFloor(raw/step+1e-9)*step;
   if(lots<minimum) return 0.0;
   return MathMin(maximum,lots);
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

bool ReadATR(const int shift,double &value)
{
   double data[];
   if(g_atr_handle==INVALID_HANDLE || CopyBuffer(g_atr_handle,0,shift,1,data)!=1) return false;
   value=data[0]; return value>0.0;
}

int ServerUtcOffsetSeconds()
{
   if(!InpAutoServerUtcOffsetLive || (bool)MQLInfoInteger(MQL_TESTER)) return InpServerUtcOffsetHours*3600;
   datetime server=TimeTradeServer(),utc=TimeGMT();
   if(server<=0 || utc<=0) return InpServerUtcOffsetHours*3600;
   return (int)MathRound((double)(server-utc)/1800.0)*1800;
}

datetime ServerToUTC(const datetime server_time)
{
   return server_time-ServerUtcOffsetSeconds();
}

int UTCDateKey(const datetime server_time)
{
   MqlDateTime p; TimeToStruct(ServerToUTC(server_time),p);
   return p.year*10000+p.mon*100+p.day;
}

bool IsOurPosition(ulong &ticket)
{
   for(int i=PositionsTotal()-1;i>=0;i--)
   {
      ticket=PositionGetTicket(i);
      if(ticket>0 && PositionGetString(POSITION_SYMBOL)==_Symbol && PositionGetInteger(POSITION_MAGIC)==InpMagic) return true;
   }
   ticket=0; return false;
}

bool AlreadyTraded(const int key)
{
   datetime now=TimeCurrent();
   if(!HistorySelect(now-3*86400,now+60)) return false;
   for(int i=HistoryDealsTotal()-1;i>=0;i--)
   {
      ulong deal=HistoryDealGetTicket(i);
      if(deal==0 || HistoryDealGetInteger(deal,DEAL_MAGIC)!=InpMagic || HistoryDealGetString(deal,DEAL_SYMBOL)!=_Symbol) continue;
      long entry=HistoryDealGetInteger(deal,DEAL_ENTRY);
      if(entry!=DEAL_ENTRY_IN && entry!=DEAL_ENTRY_INOUT) continue;
      if(UTCDateKey((datetime)HistoryDealGetInteger(deal,DEAL_TIME))==key) return true;
   }
   return false;
}

void ResetDay(const int key)
{
   g_date_key=key;
   g_previous_high=0.0; g_previous_low=0.0; g_hour_open=0.0; g_hour_high=0.0; g_hour_low=0.0;
   g_qualified_direction=0; g_setup_direction=0; g_setup_entry=0.0; g_setup_stop=0.0; g_setup_created=0;
}

bool DriveQualified(const int sweep_direction,const int minute)
{
   if(minute<InpMinimumDriveMinutes || minute>InpSweepDeadlineMinute) return false;
   int count=minute+1;
   MqlRates bars[]; ArraySetAsSeries(bars,true);
   if(CopyRates(_Symbol,PERIOD_M1,1,count,bars)!=count) return false;
   double total=0.0;
   for(int i=0;i<count-1;i++) total+=MathAbs(bars[i].close-bars[i+1].close);
   if(total<=0.0) return false;
   double net=(sweep_direction<0 ? g_hour_open-bars[0].close : bars[0].close-g_hour_open);
   if(net<=0.0 || net/total<InpMinimumDriveEfficiency) return false;
   for(int i=0;i<count;i++)
   {
      if(sweep_direction<0 && bars[i].close>g_hour_open) return false;
      if(sweep_direction>0 && bars[i].close<g_hour_open) return false;
   }
   return true;
}

double PriorStructureExtreme(const int direction)
{
   double value=(direction>0 ? -DBL_MAX : DBL_MAX);
   for(int shift=2;shift<2+InpStructureLookbackBars;shift++)
   {
      if(direction>0) value=MathMax(value,iHigh(_Symbol,PERIOD_M1,shift));
      else value=MathMin(value,iLow(_Symbol,PERIOD_M1,shift));
   }
   return value;
}

void BuildSetup(const int direction,const MqlRates &signal,const MqlRates &older,const double atr)
{
   bool has_fvg=(direction>0 ? signal.low>older.high : signal.high<older.low);
   if(InpRequireFVG && !has_fvg) return;
   double entry=(has_fvg ? (direction>0 ? (signal.low+older.high)*0.5 : (signal.high+older.low)*0.5)
                         : (signal.open+signal.close)*0.5);
   double stop=(direction>0 ? g_hour_low-InpStopBufferATR*atr : g_hour_high+InpStopBufferATR*atr);
   if((direction>0 && entry<=stop) || (direction<0 && entry>=stop)) return;
   g_setup_direction=direction;
   g_setup_entry=NormalizePrice(entry);
   g_setup_stop=NormalizePrice(stop);
   g_setup_created=TimeCurrent();
}

bool SendEntry(const int direction,const double planned_stop)
{
   MqlTick tick; if(!SymbolInfoTick(_Symbol,tick)) return false;
   double entry=(direction>0 ? tick.ask : tick.bid);
   double risk=MathAbs(entry-planned_stop);
   if(risk<=SymbolInfoDouble(_Symbol,SYMBOL_POINT)) return false;
   double previous_range=g_previous_high-g_previous_low;
   double target_distance=MathMax(InpTargetPreviousRangeFraction*previous_range,InpMinimumRewardRisk*risk);
   double target=entry+direction*target_distance;
   ENUM_ORDER_TYPE type=(direction>0 ? ORDER_TYPE_BUY : ORDER_TYPE_SELL);
   double lots=LotsForRisk(type,entry,planned_stop);
   if(lots<=0.0) return false;
   g_trade.SetExpertMagicNumber((ulong)InpMagic);
   g_trade.SetTypeFillingBySymbol(_Symbol);
   g_trade.SetDeviationInPoints(InpMaximumDeviationPoints);
   bool sent=(direction>0 ? g_trade.Buy(lots,_Symbol,0.0,NormalizePrice(planned_stop),NormalizePrice(target),"Asia H2 long")
                          : g_trade.Sell(lots,_Symbol,0.0,NormalizePrice(planned_stop),NormalizePrice(target),"Asia H2 short"));
   if(!sent) Print("Asia H2 order failed: ",g_trade.ResultRetcodeDescription());
   return sent;
}

void ProcessPendingSetup()
{
   if(g_setup_direction==0) return;
   if(TimeCurrent()-g_setup_created>InpEntryExpiryMinutes*60) { g_setup_direction=0; return; }
   ulong ticket=0;
   if(IsOurPosition(ticket) || AlreadyTraded(g_date_key)) { g_setup_direction=0; return; }
   MqlTick tick; if(!SymbolInfoTick(_Symbol,tick)) return;
   bool touched=(g_setup_direction>0 ? tick.ask<=g_setup_entry : tick.bid>=g_setup_entry);
   bool valid=(g_setup_direction>0 ? tick.ask>g_setup_stop : tick.bid<g_setup_stop);
   if(touched && valid && InpEnableTrading)
   {
      int direction=g_setup_direction; double stop=g_setup_stop;
      g_setup_direction=0;
      SendEntry(direction,stop);
   }
}

void ManageFlatTime()
{
   MqlDateTime utc; TimeToStruct(ServerToUTC(TimeCurrent()),utc);
   if(utc.hour<InpFlatHourUTC) return;
   g_setup_direction=0;
   ulong ticket=0;
   if(IsOurPosition(ticket))
   {
      g_trade.SetExpertMagicNumber((ulong)InpMagic);
      g_trade.PositionClose(ticket,(ulong)InpMaximumDeviationPoints);
   }
}

void ProcessM1Bar()
{
   MqlRates r[]; ArraySetAsSeries(r,true);
   if(CopyRates(_Symbol,PERIOD_M1,0,5,r)!=5) return;
   MqlDateTime utc; TimeToStruct(ServerToUTC(r[1].time),utc);
   int key=utc.year*10000+utc.mon*100+utc.day;
   if(key!=g_date_key) ResetDay(key);
   if(utc.day_of_week<1 || utc.day_of_week>5) return;
   if(utc.hour!=InpSecondHourUTC) return;

   if(g_hour_open<=0.0)
   {
      g_previous_high=iHigh(_Symbol,PERIOD_H1,1);
      g_previous_low=iLow(_Symbol,PERIOD_H1,1);
      g_hour_open=r[1].open;
      g_hour_high=r[1].high;
      g_hour_low=r[1].low;
   }
   g_hour_high=MathMax(g_hour_high,r[1].high);
   g_hour_low=MathMin(g_hour_low,r[1].low);
   if(AlreadyTraded(key)) return;

   if(g_qualified_direction==0 && utc.min<=InpSweepDeadlineMinute)
   {
      if(g_hour_low<g_previous_low && DriveQualified(-1,utc.min)) g_qualified_direction=1;
      else if(g_hour_high>g_previous_high && DriveQualified(1,utc.min)) g_qualified_direction=-1;
   }
   if(g_qualified_direction==0 || utc.min<30 || g_setup_direction!=0) return;

   double atr=0.0; if(!ReadATR(1,atr)) return;
   double body=MathAbs(r[1].close-r[1].open);
   if(body<InpDisplacementBodyATR*atr) return;
   double structure=PriorStructureExtreme(g_qualified_direction);
   bool shift=(g_qualified_direction>0 ? r[1].close>structure && r[1].close>r[1].open
                                      : r[1].close<structure && r[1].close<r[1].open);
   if(shift) BuildSetup(g_qualified_direction,r[1],r[3],atr);
}

int OnInit()
{
   if(InpSecondHourUTC<0 || InpSecondHourUTC>23 || InpMinimumDriveMinutes<1 || InpSweepDeadlineMinute<InpMinimumDriveMinutes ||
      InpSweepDeadlineMinute>45 || InpMinimumDriveEfficiency<=0.0 || InpMinimumDriveEfficiency>1.0 || InpATRPeriod<2 ||
      InpRiskPercent<=0.0 || InpTargetPreviousRangeFraction<=0.0 || InpMinimumRewardRisk<=0.0) return INIT_PARAMETERS_INCORRECT;
   g_atr_handle=iATR(_Symbol,PERIOD_M1,InpATRPeriod);
   if(g_atr_handle==INVALID_HANDLE) return INIT_FAILED;
   g_trade.SetExpertMagicNumber((ulong)InpMagic);
   g_trade.SetTypeFillingBySymbol(_Symbol);
   g_last_m1=iTime(_Symbol,PERIOD_M1,0);
   return INIT_SUCCEEDED;
}

void OnDeinit(const int reason)
{
   if(g_atr_handle!=INVALID_HANDLE) IndicatorRelease(g_atr_handle);
}

void OnTick()
{
   ManageFlatTime();
   ProcessPendingSetup();
   datetime bar=iTime(_Symbol,PERIOD_M1,0);
   if(bar<=0 || bar==g_last_m1) return;
   g_last_m1=bar;
   ProcessM1Bar();
}
