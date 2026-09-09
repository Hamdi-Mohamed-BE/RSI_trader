//+------------------------------------------------------------------+
//|                    Calyx Value Area Reversion EA.mq5             |
//| Research reconstruction of LuxAlgo's value-area reclaim idea.   |
//| Uses broker tick activity, not centralized exchange order flow.  |
//+------------------------------------------------------------------+
#property strict
#property version   "1.00"
#property description "Previous-day value-area failed-breakout reversion research EA."

#include <Trade/Trade.mqh>

enum ENUM_VAR_DIRECTION
{
   VAR_BOTH=0,
   VAR_LONG_ONLY=1,
   VAR_SHORT_ONLY=2
};

enum ENUM_VAR_CONFIRMATION
{
   VAR_STRICT_ENGULF=0,
   VAR_BODY_ENGULF=1,
   VAR_DIRECTIONAL_RECLAIM=2,
   VAR_WICK_REJECTION=3
};

enum ENUM_VAR_STOP
{
   VAR_BREAKOUT_EXTREME=0,
   VAR_SIGNAL_EXTREME=1,
   VAR_ATR_STOP=2,
   VAR_PERCENT_STOP=3
};

enum ENUM_VAR_TARGET
{
   VAR_TARGET_POC=0,
   VAR_TARGET_OPPOSITE_EDGE=1,
   VAR_TARGET_FIXED_R=2
};

enum ENUM_VAR_SESSION
{
   VAR_ALL_DAY=0,
   VAR_ASIA=1,
   VAR_LONDON=2,
   VAR_NEW_YORK=3,
   VAR_LONDON_NY_OVERLAP=4
};

enum ENUM_VAR_REGIME
{
   VAR_REGIME_NONE=0,
   VAR_REGIME_EMA_ALIGNED=1,
   VAR_REGIME_EMA_INVERSE=2,
   VAR_REGIME_EMA_SLOPE=3
};

input group "Frozen raw source reconstruction"
input bool                  InpEnableTrading=true;
input ENUM_TIMEFRAMES       InpSignalTimeframe=PERIOD_M15;
input ENUM_TIMEFRAMES       InpProfileTimeframe=PERIOD_M15;
input int                   InpProfileRows=60;
input double                InpValueAreaPercent=70.0;
input int                   InpMaximumBarsAfterBreakout=5;
input double                InpMaximumBreakoutVolumeRatio=1.00;
input double                InpMinimumReclaimVolumeRatio=1.00;
input ENUM_VAR_CONFIRMATION InpConfirmation=VAR_STRICT_ENGULF;

input group "Stops, target and management"
input ENUM_VAR_STOP         InpStopMode=VAR_BREAKOUT_EXTREME;
input double                InpStopBufferATR=0.10;
input double                InpStopATR=1.00;
input double                InpStopPercent=0.50;
input ENUM_VAR_TARGET       InpTargetMode=VAR_TARGET_POC;
input double                InpRewardRisk=1.50;
input double                InpBreakEvenAtR=0.0;
input double                InpBreakEvenLockR=0.05;
input double                InpTrailStartR=0.0;
input double                InpTrailATR=1.50;
input int                   InpMaximumHoldingBars=0;

input group "Session and direction"
input ENUM_VAR_SESSION      InpSession=VAR_ALL_DAY;
input ENUM_VAR_DIRECTION    InpDirection=VAR_BOTH;
input bool                  InpWeekdaysOnly=false;
input int                   InpAsiaStartUTC=0;
input int                   InpAsiaEndUTC=8;
input int                   InpLondonStartUTC=7;
input int                   InpLondonEndUTC=12;
input int                   InpNewYorkStartUTC=13;
input int                   InpNewYorkEndUTC=20;
input int                   InpOverlapStartUTC=13;
input int                   InpOverlapEndUTC=16;
input int                   InpTesterServerUTCOffsetHours=0;

input group "Pipeline filters"
input ENUM_VAR_REGIME       InpRegimeMode=VAR_REGIME_NONE;
input ENUM_TIMEFRAMES       InpRegimeTimeframe=PERIOD_H1;
input int                   InpRegimeEMAPeriod=50;
input double                InpMinimumADX=0.0;
input double                InpMaximumADX=0.0;
input ENUM_TIMEFRAMES       InpADXTimeframe=PERIOD_M30;
input int                   InpADXPeriod=14;
input double                InpMinimumDailyATRPercent=0.0;
input double                InpMaximumDailyATRPercent=0.0;
input double                InpMaximumSpreadATR=0.25;

input group "Risk and execution"
input double                InpRiskPercent=1.00;
input int                   InpMaximumTradesPerDay=2;
input long                  InpMagic=990909001;
input int                   InpMaximumDeviationPoints=80;

struct ProfileData
{
   bool valid;
   datetime from_time;
   datetime to_time;
   double low;
   double high;
   double val;
   double vah;
   double poc;
};

struct BreakoutState
{
   bool active;
   int bars;
   double volume;
   double extreme;
};

CTrade g_trade;
ProfileData g_profile;
BreakoutState g_long_break;
BreakoutState g_short_break;
datetime g_last_bar=0;
datetime g_profile_session=0;
int g_trade_day=0;
int g_trades_today=0;
double g_initial_risk=0.0;

double Activity(const MqlRates &bar)
{
   if(bar.real_volume>0) return (double)bar.real_volume;
   return (double)bar.tick_volume;
}

double NormalizePrice(const double price)
{
   double tick=SymbolInfoDouble(_Symbol,SYMBOL_TRADE_TICK_SIZE);
   if(tick<=0.0) tick=SymbolInfoDouble(_Symbol,SYMBOL_POINT);
   if(tick<=0.0) return price;
   int digits=(int)SymbolInfoInteger(_Symbol,SYMBOL_DIGITS);
   return NormalizeDouble(MathRound(price/tick)*tick,digits);
}

double NormalizeVolume(const double raw)
{
   double minimum=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MIN);
   double maximum=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MAX);
   double step=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_STEP);
   if(minimum<=0.0 || maximum<=0.0 || step<=0.0 || raw<minimum) return 0.0;
   double volume=MathFloor(raw/step+1e-9)*step;
   volume=MathMax(minimum,MathMin(maximum,volume));
   int digits=0;
   double probe=step;
   while(digits<8 && MathAbs(probe-MathRound(probe))>1e-9)
   {
      probe*=10.0;
      digits++;
   }
   return NormalizeDouble(volume,digits);
}

int DayKey(const datetime when)
{
   MqlDateTime value;
   TimeToStruct(when,value);
   return value.year*10000+value.mon*100+value.day;
}

bool HourAllowed(const int hour,const int start_hour,const int end_hour)
{
   if(start_hour==end_hour) return true;
   if(start_hour<end_hour) return hour>=start_hour && hour<end_hour;
   return hour>=start_hour || hour<end_hour;
}

bool SessionAllows(const datetime server_time)
{
   datetime utc_time=server_time-InpTesterServerUTCOffsetHours*3600;
   MqlDateTime value;
   TimeToStruct(utc_time,value);
   if(InpWeekdaysOnly && (value.day_of_week==0 || value.day_of_week==6)) return false;
   if(InpSession==VAR_ALL_DAY) return true;
   if(InpSession==VAR_ASIA) return HourAllowed(value.hour,InpAsiaStartUTC,InpAsiaEndUTC);
   if(InpSession==VAR_LONDON) return HourAllowed(value.hour,InpLondonStartUTC,InpLondonEndUTC);
   if(InpSession==VAR_NEW_YORK) return HourAllowed(value.hour,InpNewYorkStartUTC,InpNewYorkEndUTC);
   return HourAllowed(value.hour,InpOverlapStartUTC,InpOverlapEndUTC);
}

bool IndicatorValue(const int handle,const int buffer_number,const int shift,double &value)
{
   if(handle==INVALID_HANDLE) return false;
   double buffer[1];
   bool ok=CopyBuffer(handle,buffer_number,shift,1,buffer)==1;
   if(ok) value=buffer[0];
   IndicatorRelease(handle);
   return ok && MathIsValidNumber(value) && value>=0.0;
}

bool ATRValue(const ENUM_TIMEFRAMES timeframe,const int shift,double &value)
{
   return IndicatorValue(iATR(_Symbol,timeframe,14),0,shift,value) && value>0.0;
}

bool EMAValue(const ENUM_TIMEFRAMES timeframe,const int period,const int shift,double &value)
{
   return IndicatorValue(iMA(_Symbol,timeframe,period,0,MODE_EMA,PRICE_CLOSE),0,shift,value) && value>0.0;
}

bool ADXValue(double &value)
{
   return IndicatorValue(iADX(_Symbol,InpADXTimeframe,InpADXPeriod),0,1,value);
}

void ResetBreakout(BreakoutState &state)
{
   state.active=false;
   state.bars=0;
   state.volume=0.0;
   state.extreme=0.0;
}

void ResetProfile()
{
   g_profile.valid=false;
   g_profile.from_time=0;
   g_profile.to_time=0;
   g_profile.low=0.0;
   g_profile.high=0.0;
   g_profile.val=0.0;
   g_profile.vah=0.0;
   g_profile.poc=0.0;
}

bool BuildPreviousDayProfile()
{
   ResetProfile();
   datetime from_time=iTime(_Symbol,PERIOD_D1,1);
   datetime to_time=iTime(_Symbol,PERIOD_D1,0);
   if(from_time<=0 || to_time<=from_time) return false;
   MqlRates bars[];
   int copied=CopyRates(_Symbol,InpProfileTimeframe,from_time,to_time-1,bars);
   if(copied<4) return false;

   double low=DBL_MAX;
   double high=-DBL_MAX;
   double total_activity=0.0;
   for(int index=0;index<copied;index++)
   {
      low=MathMin(low,bars[index].low);
      high=MathMax(high,bars[index].high);
      total_activity+=Activity(bars[index]);
   }
   if(high<=low || total_activity<=0.0) return false;

   int rows=MathMax(16,MathMin(240,InpProfileRows));
   double step=(high-low)/(double)rows;
   if(step<=0.0) return false;
   double profile[];
   ArrayResize(profile,rows);
   ArrayInitialize(profile,0.0);
   for(int index=0;index<copied;index++)
   {
      int first=(int)MathFloor((bars[index].low-low)/step);
      int last=(int)MathFloor((bars[index].high-low)/step);
      first=MathMax(0,MathMin(rows-1,first));
      last=MathMax(0,MathMin(rows-1,last));
      if(last<first)
      {
         int swap=first;
         first=last;
         last=swap;
      }
      int touched=MathMax(1,last-first+1);
      double share=Activity(bars[index])/(double)touched;
      for(int bin=first;bin<=last;bin++) profile[bin]+=share;
   }

   int poc_bin=0;
   for(int bin=1;bin<rows;bin++)
      if(profile[bin]>profile[poc_bin]) poc_bin=bin;
   int low_bin=poc_bin;
   int high_bin=poc_bin;
   double included=profile[poc_bin];
   double wanted=total_activity*MathMax(1.0,MathMin(99.0,InpValueAreaPercent))/100.0;
   while(included<wanted && (low_bin>0 || high_bin<rows-1))
   {
      double below=(low_bin>0 ? profile[low_bin-1] : -1.0);
      double above=(high_bin<rows-1 ? profile[high_bin+1] : -1.0);
      if(above>=below && high_bin<rows-1)
      {
         high_bin++;
         included+=profile[high_bin];
      }
      else if(low_bin>0)
      {
         low_bin--;
         included+=profile[low_bin];
      }
      else break;
   }

   g_profile.valid=true;
   g_profile.from_time=from_time;
   g_profile.to_time=to_time;
   g_profile.low=low;
   g_profile.high=high;
   g_profile.val=NormalizePrice(low+(double)low_bin*step);
   g_profile.vah=NormalizePrice(low+(double)(high_bin+1)*step);
   g_profile.poc=NormalizePrice(low+((double)poc_bin+0.5)*step);
   return g_profile.val<g_profile.poc && g_profile.poc<g_profile.vah;
}

bool DirectionAllowed(const int direction)
{
   if(direction>0) return InpDirection==VAR_BOTH || InpDirection==VAR_LONG_ONLY;
   return InpDirection==VAR_BOTH || InpDirection==VAR_SHORT_ONLY;
}

bool SpreadPasses(const double atr)
{
   if(InpMaximumSpreadATR<=0.0) return true;
   MqlTick tick;
   if(!SymbolInfoTick(_Symbol,tick)) return false;
   return tick.ask-tick.bid<=InpMaximumSpreadATR*atr;
}

bool FiltersPass(const int direction,const double price)
{
   if(!DirectionAllowed(direction)) return false;
   if(InpRegimeMode!=VAR_REGIME_NONE)
   {
      double current=0.0;
      double earlier=0.0;
      if(!EMAValue(InpRegimeTimeframe,InpRegimeEMAPeriod,1,current)) return false;
      if(InpRegimeMode==VAR_REGIME_EMA_ALIGNED)
      {
         if(direction>0 && price<=current) return false;
         if(direction<0 && price>=current) return false;
      }
      else if(InpRegimeMode==VAR_REGIME_EMA_INVERSE)
      {
         if(direction>0 && price>=current) return false;
         if(direction<0 && price<=current) return false;
      }
      else
      {
         if(!EMAValue(InpRegimeTimeframe,InpRegimeEMAPeriod,6,earlier)) return false;
         if(direction>0 && current<=earlier) return false;
         if(direction<0 && current>=earlier) return false;
      }
   }
   if(InpMinimumADX>0.0 || InpMaximumADX>0.0)
   {
      double adx=0.0;
      if(!ADXValue(adx)) return false;
      if(InpMinimumADX>0.0 && adx<InpMinimumADX) return false;
      if(InpMaximumADX>0.0 && adx>InpMaximumADX) return false;
   }
   if(InpMinimumDailyATRPercent>0.0 || InpMaximumDailyATRPercent>0.0)
   {
      double daily_atr=0.0;
      if(!ATRValue(PERIOD_D1,1,daily_atr) || price<=0.0) return false;
      double percentage=daily_atr/price*100.0;
      if(InpMinimumDailyATRPercent>0.0 && percentage<InpMinimumDailyATRPercent) return false;
      if(InpMaximumDailyATRPercent>0.0 && percentage>InpMaximumDailyATRPercent) return false;
   }
   return true;
}

bool SelectOurPosition(ulong &ticket,int &direction)
{
   ticket=0;
   direction=0;
   for(int index=PositionsTotal()-1;index>=0;index--)
   {
      ulong candidate=PositionGetTicket(index);
      if(candidate==0 || !PositionSelectByTicket(candidate)) continue;
      if(PositionGetString(POSITION_SYMBOL)!=_Symbol || PositionGetInteger(POSITION_MAGIC)!=InpMagic) continue;
      ticket=candidate;
      direction=(PositionGetInteger(POSITION_TYPE)==POSITION_TYPE_BUY ? 1 : -1);
      return true;
   }
   return false;
}

double RiskVolume(const ENUM_ORDER_TYPE type,const double entry,const double stop)
{
   double one_lot_loss=0.0;
   if(!OrderCalcProfit(type,_Symbol,1.0,entry,stop,one_lot_loss)) return 0.0;
   one_lot_loss=MathAbs(one_lot_loss);
   if(one_lot_loss<=0.0) return 0.0;
   double budget=AccountInfoDouble(ACCOUNT_EQUITY)*InpRiskPercent/100.0;
   return NormalizeVolume(budget/one_lot_loss);
}

bool ConfirmationPasses(const MqlRates &signal,const MqlRates &previous,const int direction)
{
   double body=MathAbs(signal.close-signal.open);
   double range=MathMax(signal.high-signal.low,_Point);
   bool directional=(direction>0 ? signal.close>signal.open : signal.close<signal.open);
   if(!directional) return false;
   if(InpConfirmation==VAR_STRICT_ENGULF)
   {
      if(direction>0)
         return previous.close<previous.open && signal.open<=previous.close && signal.close>=previous.open;
      return previous.close>previous.open && signal.open>=previous.close && signal.close<=previous.open;
   }
   if(InpConfirmation==VAR_BODY_ENGULF)
      return body>=MathAbs(previous.close-previous.open);
   if(InpConfirmation==VAR_DIRECTIONAL_RECLAIM)
      return true;
   if(direction>0)
      return MathMin(signal.open,signal.close)-signal.low>=body && (signal.close-signal.low)/range>=0.60;
   return signal.high-MathMax(signal.open,signal.close)>=body && (signal.high-signal.close)/range>=0.60;
}

double StopPrice(const MqlRates &signal,const int direction,const double entry,const double atr,
                 const double breakout_extreme)
{
   double stop=0.0;
   if(InpStopMode==VAR_BREAKOUT_EXTREME)
      stop=(direction>0 ? breakout_extreme-InpStopBufferATR*atr : breakout_extreme+InpStopBufferATR*atr);
   else if(InpStopMode==VAR_SIGNAL_EXTREME)
      stop=(direction>0 ? signal.low-InpStopBufferATR*atr : signal.high+InpStopBufferATR*atr);
   else if(InpStopMode==VAR_ATR_STOP)
      stop=(direction>0 ? entry-InpStopATR*atr : entry+InpStopATR*atr);
   else
      stop=(direction>0 ? entry*(1.0-InpStopPercent/100.0) : entry*(1.0+InpStopPercent/100.0));

   double minimum=MathMax((double)SymbolInfoInteger(_Symbol,SYMBOL_TRADE_STOPS_LEVEL)*_Point,
                          SymbolInfoDouble(_Symbol,SYMBOL_TRADE_TICK_SIZE));
   if(direction>0 && entry-stop<minimum) stop=entry-minimum;
   if(direction<0 && stop-entry<minimum) stop=entry+minimum;
   return NormalizePrice(stop);
}

bool OpenTrade(const MqlRates &signal,const int direction,const double atr,const double breakout_extreme)
{
   MqlTick tick;
   if(!SymbolInfoTick(_Symbol,tick)) return false;
   double entry=(direction>0 ? tick.ask : tick.bid);
   double stop=StopPrice(signal,direction,entry,atr,breakout_extreme);
   double risk=MathAbs(entry-stop);
   if(risk<=0.0) return false;
   double target=0.0;
   if(InpTargetMode==VAR_TARGET_POC) target=g_profile.poc;
   else if(InpTargetMode==VAR_TARGET_OPPOSITE_EDGE) target=(direction>0 ? g_profile.vah : g_profile.val);
   else target=(direction>0 ? entry+InpRewardRisk*risk : entry-InpRewardRisk*risk);
   target=NormalizePrice(target);
   double minimum=MathMax((double)SymbolInfoInteger(_Symbol,SYMBOL_TRADE_STOPS_LEVEL)*_Point,
                          SymbolInfoDouble(_Symbol,SYMBOL_TRADE_TICK_SIZE));
   if(direction>0 && target-entry<minimum) return false;
   if(direction<0 && entry-target<minimum) return false;
   ENUM_ORDER_TYPE type=(direction>0 ? ORDER_TYPE_BUY : ORDER_TYPE_SELL);
   double volume=RiskVolume(type,entry,stop);
   if(volume<=0.0) return false;
   string note="Calyx VAR "+(InpTargetMode==VAR_TARGET_POC ? "POC" : InpTargetMode==VAR_TARGET_OPPOSITE_EDGE ? "EDGE" : "R");
   bool placed=(direction>0 ? g_trade.Buy(volume,_Symbol,0.0,stop,target,note)
                            : g_trade.Sell(volume,_Symbol,0.0,stop,target,note));
   if(placed)
   {
      g_initial_risk=risk;
      g_trades_today++;
   }
   return placed;
}

void ManagePosition(const MqlRates &closed_bar,const double atr)
{
   ulong ticket=0;
   int direction=0;
   if(!SelectOurPosition(ticket,direction)) return;
   double entry=PositionGetDouble(POSITION_PRICE_OPEN);
   double current_stop=PositionGetDouble(POSITION_SL);
   double target=PositionGetDouble(POSITION_TP);
   double initial_risk=g_initial_risk;
   if(initial_risk<=0.0) initial_risk=MathAbs(entry-current_stop);
   if(initial_risk<=0.0) return;
   double progress=(direction>0 ? closed_bar.close-entry : entry-closed_bar.close);
   double proposed=current_stop;
   if(InpBreakEvenAtR>0.0 && progress>=InpBreakEvenAtR*initial_risk)
   {
      double breakeven=entry+direction*InpBreakEvenLockR*initial_risk;
      proposed=(direction>0 ? MathMax(proposed,breakeven) : (proposed<=0.0 ? breakeven : MathMin(proposed,breakeven)));
   }
   if(InpTrailStartR>0.0 && progress>=InpTrailStartR*initial_risk)
   {
      double trail=closed_bar.close-direction*InpTrailATR*atr;
      proposed=(direction>0 ? MathMax(proposed,trail) : (proposed<=0.0 ? trail : MathMin(proposed,trail)));
   }
   bool improves=(direction>0 ? proposed>current_stop+_Point && proposed<closed_bar.close
                              : (current_stop<=0.0 || proposed<current_stop-_Point) && proposed>closed_bar.close);
   if(improves) g_trade.PositionModify(ticket,NormalizePrice(proposed),target);
   if(InpMaximumHoldingBars>0)
   {
      datetime opened=(datetime)PositionGetInteger(POSITION_TIME);
      int seconds=PeriodSeconds(InpSignalTimeframe);
      if(seconds>0 && (closed_bar.time-opened)/seconds>=InpMaximumHoldingBars)
         g_trade.PositionClose(ticket);
   }
}

void AdvanceBreakout(BreakoutState &state,const MqlRates &bar,const int direction)
{
   if(!state.active) return;
   state.bars++;
   if(direction>0 && bar.close<g_profile.val)
   {
      state.volume=Activity(bar);
      state.extreme=MathMin(state.extreme,bar.low);
   }
   if(direction<0 && bar.close>g_profile.vah)
   {
      state.volume=Activity(bar);
      state.extreme=MathMax(state.extreme,bar.high);
   }
   if(state.bars>InpMaximumBarsAfterBreakout) ResetBreakout(state);
}

void ProcessBar()
{
   MqlRates rates[];
   ArraySetAsSeries(rates,true);
   if(CopyRates(_Symbol,InpSignalTimeframe,0,8,rates)<8) return;
   MqlRates signal=rates[1];
   MqlRates previous=rates[2];
   double atr=0.0;
   if(!ATRValue(InpSignalTimeframe,1,atr)) return;

   datetime current_session=iTime(_Symbol,PERIOD_D1,0);
   if(current_session<=0) return;
   if(current_session!=g_profile_session)
   {
      g_profile_session=current_session;
      BuildPreviousDayProfile();
      ResetBreakout(g_long_break);
      ResetBreakout(g_short_break);
   }
   int day=DayKey(signal.time);
   if(day!=g_trade_day)
   {
      g_trade_day=day;
      g_trades_today=0;
   }

   ManagePosition(signal,atr);
   ulong ticket=0;
   int existing_direction=0;
   if(SelectOurPosition(ticket,existing_direction)) return;
   if(!InpEnableTrading || !g_profile.valid || g_trades_today>=InpMaximumTradesPerDay) return;

   bool can_enter=SessionAllows(signal.time) && SpreadPasses(atr);
   double signal_volume=Activity(signal);

   if(g_long_break.active)
   {
      bool inside=signal.close>=g_profile.val && signal.close<=g_profile.vah;
      bool volume_confirms=signal_volume>=g_long_break.volume*InpMinimumReclaimVolumeRatio;
      if(can_enter && inside && volume_confirms && ConfirmationPasses(signal,previous,1) &&
         FiltersPass(1,signal.close) && OpenTrade(signal,1,atr,g_long_break.extreme))
      {
         ResetBreakout(g_long_break);
         ResetBreakout(g_short_break);
         return;
      }
      AdvanceBreakout(g_long_break,signal,1);
   }
   if(g_short_break.active)
   {
      bool inside=signal.close<=g_profile.vah && signal.close>=g_profile.val;
      bool volume_confirms=signal_volume>=g_short_break.volume*InpMinimumReclaimVolumeRatio;
      if(can_enter && inside && volume_confirms && ConfirmationPasses(signal,previous,-1) &&
         FiltersPass(-1,signal.close) && OpenTrade(signal,-1,atr,g_short_break.extreme))
      {
         ResetBreakout(g_long_break);
         ResetBreakout(g_short_break);
         return;
      }
      AdvanceBreakout(g_short_break,signal,-1);
   }

   double previous_volume=Activity(previous);
   if(!g_long_break.active && signal.close<g_profile.val &&
      signal_volume<=previous_volume*InpMaximumBreakoutVolumeRatio)
   {
      g_long_break.active=true;
      g_long_break.bars=0;
      g_long_break.volume=signal_volume;
      g_long_break.extreme=signal.low;
   }
   if(!g_short_break.active && signal.close>g_profile.vah &&
      signal_volume<=previous_volume*InpMaximumBreakoutVolumeRatio)
   {
      g_short_break.active=true;
      g_short_break.bars=0;
      g_short_break.volume=signal_volume;
      g_short_break.extreme=signal.high;
   }
}

int OnInit()
{
   if(InpRiskPercent<=0.0 || InpProfileRows<16 || InpValueAreaPercent<=0.0 ||
      InpValueAreaPercent>=100.0 || InpMaximumBarsAfterBreakout<1 || InpRegimeEMAPeriod<2)
      return INIT_PARAMETERS_INCORRECT;
   g_trade.SetExpertMagicNumber(InpMagic);
   g_trade.SetDeviationInPoints(InpMaximumDeviationPoints);
   g_trade.SetTypeFillingBySymbol(_Symbol);
   ResetProfile();
   ResetBreakout(g_long_break);
   ResetBreakout(g_short_break);
   return INIT_SUCCEEDED;
}

void OnTick()
{
   datetime current=iTime(_Symbol,InpSignalTimeframe,0);
   if(current<=0 || current==g_last_bar) return;
   g_last_bar=current;
   ProcessBar();
}

double OnTester()
{
   double profit=TesterStatistics(STAT_PROFIT);
   double initial=TesterStatistics(STAT_INITIAL_DEPOSIT);
   double pf=TesterStatistics(STAT_PROFIT_FACTOR);
   double dd=TesterStatistics(STAT_EQUITY_DDREL_PERCENT);
   double trades=TesterStatistics(STAT_TRADES);
   if(initial<=0.0 || trades<20.0 || pf<=0.0) return -1000000.0+profit;
   double return_pct=100.0*profit/initial;
   return return_pct*MathSqrt(MathMin(trades,150.0)/150.0)*MathMin(pf,3.0)/(1.0+MathMax(dd,0.0));
}
