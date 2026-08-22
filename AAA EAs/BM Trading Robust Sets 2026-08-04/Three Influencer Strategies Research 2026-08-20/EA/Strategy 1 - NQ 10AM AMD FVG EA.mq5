#property copyright "Codex research implementation from supplied 10AM AMD description"
#property version   "1.00"
#property strict

#include <Trade/Trade.mqh>

input group "10AM New York model"
input bool   InpEnableTrading=true;
input bool   InpAllowLong=true;
input bool   InpAllowShort=true;
input bool   InpRequireFVG=true;
input bool   InpRequireSMT=false;
input string InpSMTSymbol="US500";
input int    InpSMTLookbackBars=8;
input bool   InpRequireM5CloseAcrossOpen=true;
input double InpManipulationBufferATR=0.05;
input double InpDisplacementBodyATR=0.60;
input int    InpSetupExpiryMinutes=30;

input group "Stops and targets"
input int    InpATRPeriod=14;
input double InpStopBufferATR=0.10;
input double InpFallbackRewardRisk=2.00;
input double InpMinimumLiquidityTargetR=1.00;
input int    InpFlatHourNY=15;
input int    InpFlatMinuteNY=55;

input group "Risk and execution"
input double InpRiskPercent=1.00;
input long   InpMagic=862101;
input int    InpMaximumDeviationPoints=50;
input bool   InpAutoServerUtcOffsetLive=true;
input int    InpServerUtcOffsetHours=0;

CTrade g_trade;
int g_atr_handle=INVALID_HANDLE;
datetime g_last_m1=0;
int g_date_key=0;
double g_ten_open=0.0;
double g_pre_high=0.0;
double g_pre_low=0.0;
double g_manip_high=0.0;
double g_manip_low=0.0;
bool g_swept_up=false;
bool g_swept_down=false;
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
   value=data[0];
   return value>0.0;
}

int ServerUtcOffsetSeconds()
{
   if(!InpAutoServerUtcOffsetLive || (bool)MQLInfoInteger(MQL_TESTER)) return InpServerUtcOffsetHours*3600;
   datetime server=TimeTradeServer(),utc=TimeGMT();
   if(server<=0 || utc<=0) return InpServerUtcOffsetHours*3600;
   return (int)MathRound((double)(server-utc)/1800.0)*1800;
}

datetime BuildUtcTime(const int year,const int month,const int day,const int hour)
{
   MqlDateTime value; ZeroMemory(value);
   value.year=year; value.mon=month; value.day=day; value.hour=hour;
   return StructToTime(value);
}

int NthSunday(const int year,const int month,const int nth)
{
   MqlDateTime first; TimeToStruct(BuildUtcTime(year,month,1,0),first);
   return 1+((7-first.day_of_week)%7)+(nth-1)*7;
}

int NewYorkUtcOffsetHours(const datetime utc_time)
{
   MqlDateTime p; TimeToStruct(utc_time,p);
   datetime start=BuildUtcTime(p.year,3,NthSunday(p.year,3,2),7);
   datetime finish=BuildUtcTime(p.year,11,NthSunday(p.year,11,1),6);
   return (utc_time>=start && utc_time<finish ? -4 : -5);
}

datetime ServerToNewYork(const datetime server_time)
{
   datetime utc_time=server_time-ServerUtcOffsetSeconds();
   return utc_time+NewYorkUtcOffsetHours(utc_time)*3600;
}

int NewYorkDateKey(const datetime server_time)
{
   MqlDateTime p; TimeToStruct(ServerToNewYork(server_time),p);
   return p.year*10000+p.mon*100+p.day;
}

bool IsOurPosition(ulong &ticket)
{
   for(int i=PositionsTotal()-1;i>=0;i--)
   {
      ticket=PositionGetTicket(i);
      if(ticket>0 && PositionGetString(POSITION_SYMBOL)==_Symbol && PositionGetInteger(POSITION_MAGIC)==InpMagic) return true;
   }
   ticket=0;
   return false;
}

bool AlreadyTraded(const int date_key)
{
   datetime now=TimeCurrent();
   if(!HistorySelect(now-3*86400,now+60)) return false;
   for(int i=HistoryDealsTotal()-1;i>=0;i--)
   {
      ulong deal=HistoryDealGetTicket(i);
      if(deal==0 || HistoryDealGetInteger(deal,DEAL_MAGIC)!=InpMagic || HistoryDealGetString(deal,DEAL_SYMBOL)!=_Symbol) continue;
      long entry=HistoryDealGetInteger(deal,DEAL_ENTRY);
      if(entry!=DEAL_ENTRY_IN && entry!=DEAL_ENTRY_INOUT) continue;
      if(NewYorkDateKey((datetime)HistoryDealGetInteger(deal,DEAL_TIME))==date_key) return true;
   }
   return false;
}

void ResetDay(const int key)
{
   g_date_key=key;
   g_ten_open=0.0; g_pre_high=0.0; g_pre_low=0.0;
   g_manip_high=0.0; g_manip_low=0.0;
   g_swept_up=false; g_swept_down=false;
   g_setup_direction=0; g_setup_entry=0.0; g_setup_stop=0.0; g_setup_created=0;
}

bool PassSMT(const int direction)
{
   if(!InpRequireSMT) return true;
   if(InpSMTLookbackBars<3 || !SymbolSelect(InpSMTSymbol,true)) return false;
   double main_now=(direction>0 ? iLow(_Symbol,PERIOD_M1,1) : iHigh(_Symbol,PERIOD_M1,1));
   double ref_now=(direction>0 ? iLow(InpSMTSymbol,PERIOD_M1,1) : iHigh(InpSMTSymbol,PERIOD_M1,1));
   if(main_now<=0.0 || ref_now<=0.0) return false;
   double main_extreme=(direction>0 ? DBL_MAX : -DBL_MAX);
   double ref_extreme=(direction>0 ? DBL_MAX : -DBL_MAX);
   for(int shift=2;shift<2+InpSMTLookbackBars;shift++)
   {
      double m=(direction>0 ? iLow(_Symbol,PERIOD_M1,shift) : iHigh(_Symbol,PERIOD_M1,shift));
      double r=(direction>0 ? iLow(InpSMTSymbol,PERIOD_M1,shift) : iHigh(InpSMTSymbol,PERIOD_M1,shift));
      if(m<=0.0 || r<=0.0) return false;
      if(direction>0) { main_extreme=MathMin(main_extreme,m); ref_extreme=MathMin(ref_extreme,r); }
      else { main_extreme=MathMax(main_extreme,m); ref_extreme=MathMax(ref_extreme,r); }
   }
   return (direction>0 ? main_now<main_extreme && ref_now>=ref_extreme : main_now>main_extreme && ref_now<=ref_extreme);
}

bool M5CloseAcrossOpen(const int direction)
{
   if(!InpRequireM5CloseAcrossOpen) return true;
   double close=iClose(_Symbol,PERIOD_M5,1);
   if(close<=0.0 || g_ten_open<=0.0) return false;
   return (direction>0 ? close>g_ten_open : close<g_ten_open);
}

void BuildSetup(const int direction,const MqlRates &signal,const MqlRates &older,const double atr)
{
   if(!PassSMT(direction) || !M5CloseAcrossOpen(direction)) return;
   double fvg_near=0.0,fvg_far=0.0;
   if(direction>0) { fvg_near=older.high; fvg_far=signal.low; }
   else { fvg_near=older.low; fvg_far=signal.high; }
   bool has_fvg=(direction>0 ? fvg_far>fvg_near : fvg_far<fvg_near);
   if(InpRequireFVG && !has_fvg) return;
   double midpoint=(has_fvg ? (fvg_near+fvg_far)*0.5 : (signal.open+signal.close)*0.5);
   double stop=(direction>0 ? g_manip_low-InpStopBufferATR*atr : g_manip_high+InpStopBufferATR*atr);
   if((direction>0 && midpoint<=stop) || (direction<0 && midpoint>=stop)) return;
   g_setup_direction=direction;
   g_setup_entry=NormalizePrice(midpoint);
   g_setup_stop=NormalizePrice(stop);
   g_setup_created=TimeCurrent();
}

bool SendMarketEntry(const int direction,const double planned_stop)
{
   MqlTick tick; if(!SymbolInfoTick(_Symbol,tick)) return false;
   double entry=(direction>0 ? tick.ask : tick.bid);
   double stop=planned_stop;
   double risk=MathAbs(entry-stop);
   if(risk<=SymbolInfoDouble(_Symbol,SYMBOL_POINT)) return false;
   double liquidity=(direction>0 ? g_pre_high : g_pre_low);
   double target=entry+direction*InpFallbackRewardRisk*risk;
   if(liquidity>0.0)
   {
      double liquid_r=(direction>0 ? liquidity-entry : entry-liquidity)/risk;
      if(liquid_r>=InpMinimumLiquidityTargetR) target=liquidity;
   }
   ENUM_ORDER_TYPE type=(direction>0 ? ORDER_TYPE_BUY : ORDER_TYPE_SELL);
   double lots=LotsForRisk(type,entry,stop);
   if(lots<=0.0) return false;
   g_trade.SetExpertMagicNumber((ulong)InpMagic);
   g_trade.SetTypeFillingBySymbol(_Symbol);
   g_trade.SetDeviationInPoints(InpMaximumDeviationPoints);
   bool sent=(direction>0 ? g_trade.Buy(lots,_Symbol,0.0,NormalizePrice(stop),NormalizePrice(target),"10AM AMD long")
                          : g_trade.Sell(lots,_Symbol,0.0,NormalizePrice(stop),NormalizePrice(target),"10AM AMD short"));
   if(!sent) Print("10AM AMD order failed: ",g_trade.ResultRetcodeDescription());
   return sent;
}

void ProcessPendingSetup()
{
   if(g_setup_direction==0) return;
   if(TimeCurrent()-g_setup_created>InpSetupExpiryMinutes*60) { g_setup_direction=0; return; }
   ulong ticket=0;
   if(IsOurPosition(ticket) || AlreadyTraded(g_date_key)) { g_setup_direction=0; return; }
   MqlTick tick; if(!SymbolInfoTick(_Symbol,tick)) return;
   bool touched=(g_setup_direction>0 ? tick.ask<=g_setup_entry : tick.bid>=g_setup_entry);
   bool valid=(g_setup_direction>0 ? tick.ask>g_setup_stop : tick.bid<g_setup_stop);
   if(touched && valid && InpEnableTrading)
   {
      int direction=g_setup_direction; double stop=g_setup_stop;
      g_setup_direction=0;
      SendMarketEntry(direction,stop);
   }
}

void ManageFlatTime()
{
   MqlDateTime ny; TimeToStruct(ServerToNewYork(TimeCurrent()),ny);
   if(ny.hour<InpFlatHourNY || (ny.hour==InpFlatHourNY && ny.min<InpFlatMinuteNY)) return;
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
   MqlDateTime ny; TimeToStruct(ServerToNewYork(r[1].time),ny);
   int key=ny.year*10000+ny.mon*100+ny.day;
   if(key!=g_date_key) ResetDay(key);
   if(ny.day_of_week<1 || ny.day_of_week>5) return;

   if(ny.hour==9 && ny.min>=30)
   {
      if(g_pre_high<=0.0) { g_pre_high=r[1].high; g_pre_low=r[1].low; }
      else { g_pre_high=MathMax(g_pre_high,r[1].high); g_pre_low=MathMin(g_pre_low,r[1].low); }
      return;
   }
   if(ny.hour==10 && ny.min==0 && g_ten_open<=0.0)
   {
      g_ten_open=r[1].open;
      g_manip_high=r[1].high;
      g_manip_low=r[1].low;
   }
   if(g_ten_open<=0.0 || ny.hour<10 || ny.hour>=12 || AlreadyTraded(key)) return;

   double atr=0.0; if(!ReadATR(1,atr)) return;
   g_manip_high=MathMax(g_manip_high,r[1].high);
   g_manip_low=MathMin(g_manip_low,r[1].low);
   if(r[1].high>g_ten_open+InpManipulationBufferATR*atr) g_swept_up=true;
   if(r[1].low<g_ten_open-InpManipulationBufferATR*atr) g_swept_down=true;
   if(g_setup_direction!=0) return;

   double body=MathAbs(r[1].close-r[1].open);
   if(body<InpDisplacementBodyATR*atr) return;
   bool bull=g_swept_down && InpAllowLong && r[1].close>r[1].open && r[1].close>r[2].high;
   bool bear=g_swept_up && InpAllowShort && r[1].close<r[1].open && r[1].close<r[2].low;
   if(bull) BuildSetup(1,r[1],r[3],atr);
   else if(bear) BuildSetup(-1,r[1],r[3],atr);
}

int OnInit()
{
   if(InpATRPeriod<2 || InpRiskPercent<=0.0 || InpDisplacementBodyATR<=0.0 || InpFallbackRewardRisk<=0.0 || InpSetupExpiryMinutes<1) return INIT_PARAMETERS_INCORRECT;
   g_atr_handle=iATR(_Symbol,PERIOD_M1,InpATRPeriod);
   if(g_atr_handle==INVALID_HANDLE) return INIT_FAILED;
   if(InpRequireSMT && !SymbolSelect(InpSMTSymbol,true)) return INIT_FAILED;
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
