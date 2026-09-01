#property copyright "Daily Box Theory research reconstruction"
#property version   "1.00"
#property strict

#include <Trade/Trade.mqh>

enum ENUM_BOX_CONFIRMATION
{
   BOX_LITERAL_VIDEO = 0, // short: red bar trades below prior low; long: green bar
   BOX_STRICT_SYMMETRIC = 1 // short/long must close through prior low/high
};

enum ENUM_BOX_STOP_MODE
{
   BOX_STOP_SIGNAL_BAR = 0,
   BOX_STOP_CURRENT_DAY_EXTREME = 1
};

enum ENUM_BOX_TARGET_MODE
{
   BOX_TARGET_FIXED_R = 0,
   BOX_TARGET_MIDLINE = 1,
   BOX_TARGET_OPPOSITE_EDGE = 2
};

input group "Previous-day box"
input double InpZonePercent=15.0;
input ENUM_BOX_CONFIRMATION InpConfirmation=BOX_STRICT_SYMMETRIC;
input ENUM_BOX_STOP_MODE InpStopMode=BOX_STOP_SIGNAL_BAR;
input ENUM_BOX_TARGET_MODE InpTargetMode=BOX_TARGET_FIXED_R;
input double InpRewardRisk=1.50;
input double InpMinimumTargetR=0.50;
input int InpATRPeriod=14;
input double InpStopBufferATR=0.10;

input group "Entry window - broker/tester time"
input bool InpUseSessionFilter=true;
input int InpStartHour=7;
input int InpEndHour=21;
input bool InpOneTradePerDay=true;
input int InpMaximumHoldingMinutes=720;

input group "Risk and execution"
input double InpRiskPercent=1.0;
input double InpMaximumSpreadATR=0.20;
input int InpMaximumDeviationPoints=50;
input long InpMagic=9012601;

CTrade g_trade;
int g_atr_handle=INVALID_HANDLE;
datetime g_last_m5_bar=0;
int g_day_key=0;
bool g_traded_today=false;

double NormalizePrice(const double value)
{
   return NormalizeDouble(value,(int)SymbolInfoInteger(_Symbol,SYMBOL_DIGITS));
}

double NormalizeLots(const double raw)
{
   double minimum=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MIN);
   double maximum=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MAX);
   double step=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_STEP);
   if(step<=0.0 || maximum<minimum) return 0.0;
   double lots=MathFloor(MathMin(raw,maximum)/step+1e-9)*step;
   if(lots<minimum) return 0.0;
   return NormalizeDouble(lots,8);
}

double LotsForRisk(const ENUM_ORDER_TYPE order_type,const double entry,const double stop)
{
   double one_lot=0.0;
   if(!OrderCalcProfit(order_type,_Symbol,1.0,entry,stop,one_lot)) return 0.0;
   one_lot=MathAbs(one_lot);
   if(one_lot<=0.0) return 0.0;
   double risk_money=AccountInfoDouble(ACCOUNT_EQUITY)*InpRiskPercent/100.0;
   return NormalizeLots(risk_money/one_lot);
}

int DateKey(const datetime value)
{
   MqlDateTime part;
   TimeToStruct(value,part);
   return part.year*10000+part.mon*100+part.day;
}

datetime DayStart(const datetime value)
{
   MqlDateTime part;
   TimeToStruct(value,part);
   part.hour=0;
   part.min=0;
   part.sec=0;
   return StructToTime(part);
}

bool SessionAllows(const datetime value)
{
   if(!InpUseSessionFilter || InpStartHour==InpEndHour) return true;
   MqlDateTime part;
   TimeToStruct(value,part);
   if(InpStartHour<InpEndHour) return part.hour>=InpStartHour && part.hour<InpEndHour;
   return part.hour>=InpStartHour || part.hour<InpEndHour;
}

bool SelectOurPosition(ulong &ticket)
{
   for(int index=PositionsTotal()-1;index>=0;index--)
   {
      ticket=PositionGetTicket(index);
      if(ticket>0 && PositionGetString(POSITION_SYMBOL)==_Symbol &&
         PositionGetInteger(POSITION_MAGIC)==InpMagic) return true;
   }
   ticket=0;
   return false;
}

bool TradedSince(const datetime from)
{
   if(!HistorySelect(from,TimeCurrent())) return false;
   for(int index=HistoryDealsTotal()-1;index>=0;index--)
   {
      ulong ticket=HistoryDealGetTicket(index);
      if(ticket==0) continue;
      if(HistoryDealGetString(ticket,DEAL_SYMBOL)!=_Symbol ||
         HistoryDealGetInteger(ticket,DEAL_MAGIC)!=InpMagic ||
         HistoryDealGetInteger(ticket,DEAL_ENTRY)!=DEAL_ENTRY_IN) continue;
      return true;
   }
   return false;
}

bool ReadATR(const int shift,double &atr)
{
   double values[];
   if(g_atr_handle==INVALID_HANDLE || CopyBuffer(g_atr_handle,0,shift,1,values)!=1) return false;
   atr=values[0];
   return atr>0.0;
}

bool ReadBox(double &box_high,double &box_low,double &day_high,double &day_low)
{
   MqlRates daily[];
   ArraySetAsSeries(daily,true);
   if(CopyRates(_Symbol,PERIOD_D1,0,3,daily)<3) return false;
   box_high=daily[1].high;
   box_low=daily[1].low;
   day_high=daily[0].high;
   day_low=daily[0].low;
   return box_high>box_low && day_high>=day_low;
}

bool SpreadAllows(const double atr)
{
   if(InpMaximumSpreadATR<=0.0) return true;
   MqlTick tick;
   if(!SymbolInfoTick(_Symbol,tick)) return false;
   return tick.ask-tick.bid<=atr*InpMaximumSpreadATR;
}

bool StopValid(const int direction,const double entry,double &stop)
{
   double point=SymbolInfoDouble(_Symbol,SYMBOL_POINT);
   double minimum=MathMax((double)SymbolInfoInteger(_Symbol,SYMBOL_TRADE_STOPS_LEVEL),
                          (double)SymbolInfoInteger(_Symbol,SYMBOL_TRADE_FREEZE_LEVEL))*point;
   minimum=MathMax(minimum,point);
   if(direction>0)
   {
      if(stop>=entry-minimum) stop=entry-minimum;
      return stop<entry;
   }
   if(stop<=entry+minimum) stop=entry+minimum;
   return stop>entry;
}

bool SendEntry(const int direction,const MqlRates &signal,const double box_high,const double box_low,
               const double day_high,const double day_low,const double atr)
{
   MqlTick tick;
   if(!SymbolInfoTick(_Symbol,tick)) return false;
   double entry=(direction>0 ? tick.ask : tick.bid);
   double buffer=MathMax(SymbolInfoDouble(_Symbol,SYMBOL_POINT),atr*InpStopBufferATR);
   double stop=0.0;
   if(InpStopMode==BOX_STOP_SIGNAL_BAR)
      stop=(direction>0 ? signal.low-buffer : signal.high+buffer);
   else
      stop=(direction>0 ? day_low-buffer : day_high+buffer);
   stop=NormalizePrice(stop);
   if(!StopValid(direction,entry,stop)) return false;
   stop=NormalizePrice(stop);
   double risk=MathAbs(entry-stop);
   if(risk<=0.0) return false;

   double target=0.0;
   if(InpTargetMode==BOX_TARGET_FIXED_R)
      target=entry+direction*risk*InpRewardRisk;
   else if(InpTargetMode==BOX_TARGET_MIDLINE)
      target=(box_high+box_low)/2.0;
   else
      target=(direction>0 ? box_high : box_low);
   if(direction>0 && target<=entry) return false;
   if(direction<0 && target>=entry) return false;
   if(MathAbs(target-entry)<risk*InpMinimumTargetR) return false;
   target=NormalizePrice(target);

   ENUM_ORDER_TYPE type=(direction>0 ? ORDER_TYPE_BUY : ORDER_TYPE_SELL);
   double lots=LotsForRisk(type,entry,stop);
   if(lots<=0.0) return false;
   g_trade.SetExpertMagicNumber((ulong)InpMagic);
   g_trade.SetDeviationInPoints(InpMaximumDeviationPoints);
   g_trade.SetTypeFillingBySymbol(_Symbol);
   bool sent=(direction>0 ? g_trade.Buy(lots,_Symbol,0.0,stop,target,"Daily Box long")
                          : g_trade.Sell(lots,_Symbol,0.0,stop,target,"Daily Box short"));
   if(!sent) Print("Daily Box entry rejected: ",g_trade.ResultRetcode()," ",g_trade.ResultRetcodeDescription());
   return sent;
}

void ManagePosition()
{
   ulong ticket=0;
   if(!SelectOurPosition(ticket)) return;
   if(InpMaximumHoldingMinutes<=0) return;
   datetime opened=(datetime)PositionGetInteger(POSITION_TIME);
   if(TimeCurrent()-opened>=InpMaximumHoldingMinutes*60)
   {
      g_trade.SetExpertMagicNumber((ulong)InpMagic);
      g_trade.SetDeviationInPoints(InpMaximumDeviationPoints);
      if(!g_trade.PositionClose(ticket,(ulong)InpMaximumDeviationPoints))
         Print("Daily Box time exit failed: ",g_trade.ResultRetcodeDescription());
   }
}

void EvaluateClosedBar()
{
   MqlRates bars[];
   ArraySetAsSeries(bars,true);
   if(CopyRates(_Symbol,PERIOD_M5,0,4,bars)<4) return;
   MqlRates signal=bars[1];
   MqlRates prior=bars[2];
   int key=DateKey(signal.time);
   if(key!=g_day_key)
   {
      g_day_key=key;
      g_traded_today=TradedSince(DayStart(signal.time));
   }
   if(!SessionAllows(signal.time) || (InpOneTradePerDay && g_traded_today)) return;
   ulong ticket=0;
   if(SelectOurPosition(ticket)) return;

   double box_high=0.0,box_low=0.0,day_high=0.0,day_low=0.0;
   if(!ReadBox(box_high,box_low,day_high,day_low)) return;
   double range=box_high-box_low;
   double top_zone=box_high-range*InpZonePercent/100.0;
   double bottom_zone=box_low+range*InpZonePercent/100.0;
   bool near_top=signal.high>=top_zone;
   bool near_bottom=signal.low<=bottom_zone;
   bool red=signal.close<signal.open;
   bool green=signal.close>signal.open;
   bool short_confirm=false;
   bool long_confirm=false;
   if(InpConfirmation==BOX_LITERAL_VIDEO)
   {
      short_confirm=red && signal.low<prior.low;
      long_confirm=green;
   }
   else
   {
      short_confirm=red && signal.close<prior.low;
      long_confirm=green && signal.close>prior.high;
   }

   double atr=0.0;
   if(!ReadATR(1,atr) || !SpreadAllows(atr)) return;
   int direction=0;
   if(near_top && short_confirm) direction=-1;
   else if(near_bottom && long_confirm) direction=1;
   if(direction!=0 && SendEntry(direction,signal,box_high,box_low,day_high,day_low,atr))
      g_traded_today=true;
}

int OnInit()
{
   if(InpZonePercent<=0.0 || InpZonePercent>=50.0 || InpATRPeriod<2 ||
      InpStopBufferATR<0.0 || InpRiskPercent<=0.0 || InpRewardRisk<=0.0 ||
      InpMinimumTargetR<0.0 || InpMagic<=0 || InpStartHour<0 || InpStartHour>23 ||
      InpEndHour<0 || InpEndHour>23) return INIT_PARAMETERS_INCORRECT;
   g_atr_handle=iATR(_Symbol,PERIOD_M5,InpATRPeriod);
   if(g_atr_handle==INVALID_HANDLE) return INIT_FAILED;
   g_trade.SetExpertMagicNumber((ulong)InpMagic);
   g_trade.SetTypeFillingBySymbol(_Symbol);
   g_last_m5_bar=0;
   return INIT_SUCCEEDED;
}

void OnDeinit(const int reason)
{
   if(g_atr_handle!=INVALID_HANDLE) IndicatorRelease(g_atr_handle);
}

void OnTick()
{
   ManagePosition();
   datetime current=iTime(_Symbol,PERIOD_M5,0);
   if(current<=0 || current==g_last_m5_bar) return;
   g_last_m5_bar=current;
   EvaluateClosedBar();
}

double OnTester()
{
   double initial=TesterStatistics(STAT_INITIAL_DEPOSIT);
   double profit=TesterStatistics(STAT_PROFIT);
   double pf=TesterStatistics(STAT_PROFIT_FACTOR);
   double dd=TesterStatistics(STAT_EQUITY_DDREL_PERCENT);
   double trades=TesterStatistics(STAT_TRADES);
   if(initial<=0.0 || trades<20.0 || pf<=0.0) return -1000000.0+profit;
   double result=100.0*profit/initial;
   return result-1.35*dd+8.0*MathLog(MathMax(pf,0.01))+0.02*MathMin(trades,250.0);
}
