#property copyright "ICT Macro Liquidity Sweep research implementation"
#property version   "1.00"
#property strict

#include <Trade/Trade.mqh>

enum ENUM_CONFIRMATION_MODE
{
   CONFIRM_FVG_ONLY=0,
   CONFIRM_ORDER_BLOCK_ONLY=1,
   CONFIRM_FVG_OR_ORDER_BLOCK=2,
   CONFIRM_FVG_AND_ORDER_BLOCK=3
};

input group "New York macro window"
input int InpMacroHourNY=9;
input int InpMacroStartMinute=50;
input int InpMacroEndMinute=10;
input int InpServerUTCOffsetHours=0;
input bool InpTradeMonday=true;
input bool InpTradeTuesday=true;
input bool InpTradeWednesday=true;
input bool InpTradeThursday=true;
input bool InpTradeFriday=true;

input group "Liquidity and range"
input int InpLiquidityLookbackBars=60;
input int InpATRPeriod=14;
input double InpMinimumRangeATR=1.50;
input double InpMaximumRangeATR=8.00;
input double InpMinimumSweepATR=0.05;
input double InpMaximumSweepATR=2.50;

input group "Reversal confirmation"
input ENUM_CONFIRMATION_MODE InpConfirmationMode=CONFIRM_FVG_OR_ORDER_BLOCK;
input int InpOrderBlockLookbackBars=8;
input double InpMinimumDisplacementATR=0.35;
input bool InpRequireCloseBackInside=true;
input bool InpAllowLong=true;
input bool InpAllowShort=true;

input group "Stop, target and risk"
input double InpRiskPercent=1.00;
input double InpStopBufferATR=0.10;
input double InpMinimumRewardRisk=1.00;
input double InpMaximumRewardRisk=5.00;
input double InpMaximumSpreadATR=0.12;
input int InpMaximumHoldingMinutes=180;
input bool InpMoveToBreakEven=true;
input double InpBreakEvenAtR=1.00;
input int InpMaximumDeviationPoints=50;
input long InpMagic=862908;

CTrade g_trade;
int g_atr_handle=INVALID_HANDLE;
datetime g_last_m1_bar=0;
int g_macro_day_key=-1;
bool g_range_ready=false;
bool g_traded=false;
bool g_swept_low=false;
bool g_swept_high=false;
datetime g_low_sweep_time=0;
datetime g_high_sweep_time=0;
double g_range_high=0.0;
double g_range_low=0.0;
double g_low_sweep_extreme=0.0;
double g_high_sweep_extreme=0.0;

int NthSunday(const int year,const int month,const int nth)
{
   MqlDateTime first={0};
   first.year=year;
   first.mon=month;
   first.day=1;
   datetime first_time=StructToTime(first);
   MqlDateTime converted={0};
   TimeToStruct(first_time,converted);
   int first_sunday=1+((7-converted.day_of_week)%7);
   return first_sunday+7*(nth-1);
}

bool IsNewYorkDST(const datetime utc_time)
{
   MqlDateTime value={0};
   TimeToStruct(utc_time,value);
   if(value.mon>3 && value.mon<11) return true;
   if(value.mon<3 || value.mon>11) return false;
   if(value.mon==3)
   {
      int start_day=NthSunday(value.year,3,2);
      if(value.day>start_day) return true;
      if(value.day<start_day) return false;
      return value.hour>=7;
   }
   int end_day=NthSunday(value.year,11,1);
   if(value.day<end_day) return true;
   if(value.day>end_day) return false;
   return value.hour<6;
}

datetime ServerToNewYork(const datetime server_time)
{
   datetime utc_time=server_time-InpServerUTCOffsetHours*3600;
   return utc_time+(IsNewYorkDST(utc_time) ? -4*3600 : -5*3600);
}

bool TradingDayAllowed(const int day_of_week)
{
   if(day_of_week==1) return InpTradeMonday;
   if(day_of_week==2) return InpTradeTuesday;
   if(day_of_week==3) return InpTradeWednesday;
   if(day_of_week==4) return InpTradeThursday;
   if(day_of_week==5) return InpTradeFriday;
   return false;
}

int DayKey(const MqlDateTime &value)
{
   return value.year*10000+value.mon*100+value.day;
}

bool IsMacroMinute(const MqlDateTime &ny)
{
   int minute_of_day=ny.hour*60+ny.min;
   int start=InpMacroHourNY*60+InpMacroStartMinute;
   int end=(InpMacroHourNY+1)*60+InpMacroEndMinute;
   return minute_of_day>=start && minute_of_day<end;
}

void ResetMacroState(const int day_key)
{
   g_macro_day_key=day_key;
   g_range_ready=false;
   g_traded=false;
   g_swept_low=false;
   g_swept_high=false;
   g_low_sweep_time=0;
   g_high_sweep_time=0;
   g_range_high=0.0;
   g_range_low=0.0;
   g_low_sweep_extreme=0.0;
   g_high_sweep_extreme=0.0;
}

double NormalizePrice(const double price)
{
   return NormalizeDouble(price,(int)SymbolInfoInteger(_Symbol,SYMBOL_DIGITS));
}

double NormalizeLots(const double raw_lots)
{
   double minimum=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MIN);
   double maximum=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MAX);
   double step=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_STEP);
   if(step<=0.0) return 0.0;
   double lots=MathFloor(raw_lots/step+1e-9)*step;
   if(lots<minimum) return 0.0;
   return MathMin(lots,maximum);
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

bool IsOurSelectedPosition()
{
   return PositionGetString(POSITION_SYMBOL)==_Symbol && PositionGetInteger(POSITION_MAGIC)==InpMagic;
}

bool HasOurPosition()
{
   for(int i=PositionsTotal()-1;i>=0;i--)
      if(PositionGetTicket(i)>0 && IsOurSelectedPosition()) return true;
   return false;
}

bool ReadATR(const int shift,double &value)
{
   double buffer[];
   if(g_atr_handle==INVALID_HANDLE || CopyBuffer(g_atr_handle,0,shift,1,buffer)!=1) return false;
   value=buffer[0];
   return value>0.0;
}

bool SpreadPasses(const double atr)
{
   if(InpMaximumSpreadATR<=0.0) return true;
   MqlTick tick;
   if(!SymbolInfoTick(_Symbol,tick) || tick.ask<=0.0 || tick.bid<=0.0) return false;
   return tick.ask-tick.bid<=InpMaximumSpreadATR*atr;
}

bool PrepareLiquidityRange(const MqlRates &rates[],const double atr)
{
   int available=ArraySize(rates);
   if(available<InpLiquidityLookbackBars+2) return false;
   double high=-DBL_MAX;
   double low=DBL_MAX;
   for(int i=2;i<InpLiquidityLookbackBars+2;i++)
   {
      high=MathMax(high,rates[i].high);
      low=MathMin(low,rates[i].low);
   }
   double width=high-low;
   if(width<=0.0 || atr<=0.0) return false;
   double range_atr=width/atr;
   if(range_atr<InpMinimumRangeATR || (InpMaximumRangeATR>0.0 && range_atr>InpMaximumRangeATR)) return false;
   g_range_high=high;
   g_range_low=low;
   g_range_ready=true;
   return true;
}

bool OrderBlockBreak(const int direction,const MqlRates &rates[])
{
   int available=ArraySize(rates);
   int maximum=MathMin(InpOrderBlockLookbackBars+1,available-1);
   for(int i=2;i<=maximum;i++)
   {
      if(direction>0 && rates[i].close<rates[i].open)
         return rates[1].close>rates[i].high;
      if(direction<0 && rates[i].close>rates[i].open)
         return rates[1].close<rates[i].low;
   }
   return false;
}

bool ConfirmationPasses(const int direction,const MqlRates &rates[],const double atr)
{
   if(ArraySize(rates)<4 || atr<=0.0) return false;
   const MqlRates signal=rates[1];
   double body=MathAbs(signal.close-signal.open);
   if(body<InpMinimumDisplacementATR*atr) return false;
   if(direction>0 && signal.close<=signal.open) return false;
   if(direction<0 && signal.close>=signal.open) return false;

   bool fvg=(direction>0 ? signal.low>rates[3].high : signal.high<rates[3].low);
   bool order_block=OrderBlockBreak(direction,rates);
   if(InpConfirmationMode==CONFIRM_FVG_ONLY) return fvg;
   if(InpConfirmationMode==CONFIRM_ORDER_BLOCK_ONLY) return order_block;
   if(InpConfirmationMode==CONFIRM_FVG_AND_ORDER_BLOCK) return fvg && order_block;
   return fvg || order_block;
}

bool PlaceTrade(const int direction,const double sweep_extreme,const double atr)
{
   MqlTick tick;
   if(!SymbolInfoTick(_Symbol,tick)) return false;
   double entry=(direction>0 ? tick.ask : tick.bid);
   double stop=(direction>0 ? sweep_extreme-InpStopBufferATR*atr : sweep_extreme+InpStopBufferATR*atr);
   double target=(direction>0 ? g_range_high : g_range_low);
   double point=SymbolInfoDouble(_Symbol,SYMBOL_POINT);
   double broker_gap=MathMax((double)SymbolInfoInteger(_Symbol,SYMBOL_TRADE_STOPS_LEVEL),
                             (double)SymbolInfoInteger(_Symbol,SYMBOL_TRADE_FREEZE_LEVEL))*point;
   if(direction>0 && (entry-stop)<broker_gap) stop=entry-broker_gap;
   if(direction<0 && (stop-entry)<broker_gap) stop=entry+broker_gap;
   double risk=MathAbs(entry-stop);
   double reward=(direction>0 ? target-entry : entry-target);
   if(risk<=0.0 || reward<=0.0) return false;
   double rr=reward/risk;
   if(rr<InpMinimumRewardRisk || (InpMaximumRewardRisk>0.0 && rr>InpMaximumRewardRisk)) return false;
   stop=NormalizePrice(stop);
   target=NormalizePrice(target);
   ENUM_ORDER_TYPE type=(direction>0 ? ORDER_TYPE_BUY : ORDER_TYPE_SELL);
   double lots=LotsForRisk(type,entry,stop);
   if(lots<=0.0)
   {
      Print("ICT macro skipped: calculated volume is below broker minimum.");
      return false;
   }

   g_trade.SetExpertMagicNumber((ulong)InpMagic);
   g_trade.SetTypeFillingBySymbol(_Symbol);
   g_trade.SetDeviationInPoints(InpMaximumDeviationPoints);
   bool sent=(direction>0 ? g_trade.Buy(lots,_Symbol,0.0,stop,target,"ICT macro low sweep")
                          : g_trade.Sell(lots,_Symbol,0.0,stop,target,"ICT macro high sweep"));
   if(!sent) Print("ICT macro order rejected: ",g_trade.ResultRetcodeDescription());
   return sent;
}

void ManagePosition()
{
   MqlTick tick;
   if(!SymbolInfoTick(_Symbol,tick)) return;
   g_trade.SetExpertMagicNumber((ulong)InpMagic);
   g_trade.SetDeviationInPoints(InpMaximumDeviationPoints);
   for(int i=PositionsTotal()-1;i>=0;i--)
   {
      ulong ticket=PositionGetTicket(i);
      if(ticket==0 || !IsOurSelectedPosition()) continue;
      bool buy=PositionGetInteger(POSITION_TYPE)==POSITION_TYPE_BUY;
      double open=PositionGetDouble(POSITION_PRICE_OPEN);
      double stop=PositionGetDouble(POSITION_SL);
      double target=PositionGetDouble(POSITION_TP);
      double current=(buy ? tick.bid : tick.ask);
      double initial_risk=MathAbs(open-stop);
      double favorable=(buy ? current-open : open-current);
      if(InpMoveToBreakEven && initial_risk>0.0 && favorable>=InpBreakEvenAtR*initial_risk)
      {
         double candidate=NormalizePrice(open);
         bool improves=(buy ? candidate>stop : candidate<stop);
         if(improves) g_trade.PositionModify(ticket,candidate,target);
      }
      if(InpMaximumHoldingMinutes>0)
      {
         datetime opened=(datetime)PositionGetInteger(POSITION_TIME);
         if(TimeCurrent()>=opened+InpMaximumHoldingMinutes*60)
            g_trade.PositionClose(ticket,(ulong)InpMaximumDeviationPoints);
      }
   }
}

void ProcessClosedBar()
{
   int required=MathMax(InpLiquidityLookbackBars+3,InpOrderBlockLookbackBars+4);
   MqlRates rates[];
   ArraySetAsSeries(rates,true);
   if(CopyRates(_Symbol,PERIOD_M1,0,required,rates)<required) return;
   datetime ny_time=ServerToNewYork(rates[1].time);
   MqlDateTime ny={0};
   TimeToStruct(ny_time,ny);
   int day_key=DayKey(ny);
   if(day_key!=g_macro_day_key) ResetMacroState(day_key);
   if(!TradingDayAllowed(ny.day_of_week) || !IsMacroMinute(ny) || g_traded || HasOurPosition()) return;

   double atr=0.0;
   if(!ReadATR(1,atr)) return;
   if(!g_range_ready && !PrepareLiquidityRange(rates,atr)) return;
   if(!g_range_ready) return;

   const MqlRates signal=rates[1];
   double low_sweep=g_range_low-signal.low;
   double high_sweep=signal.high-g_range_high;
   bool low_reclaim=(!InpRequireCloseBackInside || signal.close>g_range_low);
   bool high_reclaim=(!InpRequireCloseBackInside || signal.close<g_range_high);
   if(low_sweep>=InpMinimumSweepATR*atr && low_sweep<=InpMaximumSweepATR*atr && low_reclaim)
   {
      g_swept_low=true;
      g_low_sweep_time=signal.time;
      g_low_sweep_extreme=signal.low;
   }
   if(high_sweep>=InpMinimumSweepATR*atr && high_sweep<=InpMaximumSweepATR*atr && high_reclaim)
   {
      g_swept_high=true;
      g_high_sweep_time=signal.time;
      g_high_sweep_extreme=signal.high;
   }

   if(!SpreadPasses(atr)) return;
   if(InpAllowLong && g_swept_low && signal.time>g_low_sweep_time && ConfirmationPasses(1,rates,atr))
   {
      if(PlaceTrade(1,g_low_sweep_extreme,atr)) g_traded=true;
      return;
   }
   if(InpAllowShort && g_swept_high && signal.time>g_high_sweep_time && ConfirmationPasses(-1,rates,atr))
   {
      if(PlaceTrade(-1,g_high_sweep_extreme,atr)) g_traded=true;
   }
}

int OnInit()
{
   if(InpMacroHourNY<0 || InpMacroHourNY>22 || InpMacroStartMinute<0 || InpMacroStartMinute>59 ||
      InpMacroEndMinute<0 || InpMacroEndMinute>59 || InpLiquidityLookbackBars<10 || InpATRPeriod<2 ||
      InpRiskPercent<=0.0 || InpMinimumRewardRisk<=0.0 || InpMaximumSweepATR<InpMinimumSweepATR)
      return INIT_PARAMETERS_INCORRECT;
   g_atr_handle=iATR(_Symbol,PERIOD_M1,InpATRPeriod);
   if(g_atr_handle==INVALID_HANDLE) return INIT_FAILED;
   g_trade.SetExpertMagicNumber((ulong)InpMagic);
   g_trade.SetTypeFillingBySymbol(_Symbol);
   g_last_m1_bar=iTime(_Symbol,PERIOD_M1,0);
   return INIT_SUCCEEDED;
}

void OnDeinit(const int reason)
{
   if(g_atr_handle!=INVALID_HANDLE) IndicatorRelease(g_atr_handle);
}

void OnTick()
{
   ManagePosition();
   datetime current_bar=iTime(_Symbol,PERIOD_M1,0);
   if(current_bar<=0 || current_bar==g_last_m1_bar) return;
   g_last_m1_bar=current_bar;
   ProcessClosedBar();
}
