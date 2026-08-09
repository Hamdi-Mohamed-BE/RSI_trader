#property copyright "Mechanical research implementation of the supplied gold-liquidity transcript"
#property version   "1.00"
#property strict

#include <Trade/Trade.mqh>

enum ENUM_GLS_ENTRY_MODE
{
   GLS_SWEEP_CLOSE=0,
   GLS_MOMENTUM_CONFIRM=1,
   GLS_MARKET_SHIFT_RETEST=2
};

input group "Strategy"
input bool                  InpEnableTrading=true;
input ENUM_TIMEFRAMES       InpSignalTimeframe=PERIOD_M5;
input ENUM_GLS_ENTRY_MODE   InpEntryMode=GLS_MOMENTUM_CONFIRM;
input int                   InpStructurePivotDepth=2;
input int                   InpStructureLookback=120;
input int                   InpZoneLookbackBars=96;
input int                   InpZoneBreakLookback=8;
input double                InpZoneDisplacementATR=0.80;
input double                InpSweepBufferATR=0.03;
input double                InpSweepRecoveryFraction=0.55;
input int                   InpConfirmationBars=4;
input double                InpConfirmationBodyRatio=0.45;
input int                   InpRetestBars=5;

input group "Targets and protection"
input double                InpStopBufferATR=0.08;
input double                InpMaximumStopATR=2.50;
input double                InpMinimumRewardRisk=1.20;
input double                InpMaximumRewardRisk=3.00;
input int                   InpMaximumHoldingMinutes=180;
input int                   InpMaximumTradesPerDay=2;

input group "Risk and execution"
input double                InpRiskPercent=1.00;
input double                InpMaximumSpreadATRPercent=8.0;
input int                   InpMaxDeviationPoints=30;
input long                  InpMagic=86080801;

input group "UTC trading window"
input bool                  InpUseTradingWindow=true;
input int                   InpStartHourUTC=7;
input int                   InpEndHourUTC=18;
input bool                  InpWeekdaysOnly=true;
input bool                  InpUseAutomaticLiveServerOffset=true;
input int                   InpTesterServerUTCOffsetHours=0;
input int                   InpManualLiveServerUTCOffsetHours=0;

CTrade trade;
int g_atr_m5_handle=INVALID_HANDLE;
int g_atr_m15_handle=INVALID_HANDLE;
datetime g_last_bar=0;
int g_utc_date_key=0;
int g_trades_today=0;

int g_pending_direction=0;
int g_pending_stage=0;
int g_pending_age=0;
double g_protected_extreme=0.0;
double g_sweep_high=0.0;
double g_sweep_low=0.0;
double g_market_shift_level=0.0;
double g_retest_zone_low=0.0;
double g_retest_zone_high=0.0;

int ServerUTCOffsetSeconds()
{
   if((bool)MQLInfoInteger(MQL_TESTER)) return InpTesterServerUTCOffsetHours*3600;
   if(!InpUseAutomaticLiveServerOffset) return InpManualLiveServerUTCOffsetHours*3600;
   datetime server=TimeTradeServer();
   if(server<=0) server=TimeCurrent();
   datetime utc=TimeGMT();
   if(utc<=0) return InpManualLiveServerUTCOffsetHours*3600;
   return (int)MathRound((double)(server-utc)/1800.0)*1800;
}

datetime ServerToUTC(const datetime server_time)
{
   return server_time-ServerUTCOffsetSeconds();
}

int DateKey(const MqlDateTime &p)
{
   return p.year*10000+p.mon*100+p.day;
}

double NormalizePrice(const double price)
{
   double tick=SymbolInfoDouble(_Symbol,SYMBOL_TRADE_TICK_SIZE);
   if(tick<=0.0) tick=SymbolInfoDouble(_Symbol,SYMBOL_POINT);
   if(tick<=0.0) return price;
   return NormalizeDouble(MathRound(price/tick)*tick,(int)SymbolInfoInteger(_Symbol,SYMBOL_DIGITS));
}

double NormalizeVolume(const double raw)
{
   double minimum=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MIN);
   double maximum=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MAX);
   double step=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_STEP);
   if(minimum<=0.0 || maximum<=0.0 || step<=0.0 || raw<minimum) return 0.0;
   double lots=MathFloor((MathMin(raw,maximum)+1e-12)/step)*step;
   return NormalizeDouble(lots,8);
}

double LotsForRisk(const ENUM_ORDER_TYPE order_type,const double entry,const double stop)
{
   if(InpRiskPercent<=0.0 || entry<=0.0 || stop<=0.0 || entry==stop) return 0.0;
   double loss=0.0;
   if(!OrderCalcProfit(order_type,_Symbol,1.0,entry,stop,loss)) return 0.0;
   loss=MathAbs(loss);
   if(loss<=0.0) return 0.0;
   double risk_cash=AccountInfoDouble(ACCOUNT_EQUITY)*InpRiskPercent/100.0;
   return NormalizeVolume(risk_cash/loss);
}

bool LatestIndicatorValue(const int handle,const int shift,double &value)
{
   double buffer[];
   if(handle==INVALID_HANDLE || CopyBuffer(handle,0,shift,1,buffer)!=1) return false;
   value=buffer[0];
   return MathIsValidNumber(value) && value>0.0;
}

bool IsPivotHigh(MqlRates &rates[],const int index,const int depth)
{
   for(int j=1;j<=depth;j++)
      if(rates[index].high<=rates[index-j].high || rates[index].high<=rates[index+j].high) return false;
   return true;
}

bool IsPivotLow(MqlRates &rates[],const int index,const int depth)
{
   for(int j=1;j<=depth;j++)
      if(rates[index].low>=rates[index-j].low || rates[index].low>=rates[index+j].low) return false;
   return true;
}

bool RecentPivots(const ENUM_TIMEFRAMES timeframe,const int start_shift,
                  double &recent_high,double &previous_high,
                  double &recent_low,double &previous_low)
{
   MqlRates rates[];
   ArraySetAsSeries(rates,true);
   int need=InpStructureLookback+2*InpStructurePivotDepth+5;
   int count=CopyRates(_Symbol,timeframe,start_shift,need,rates);
   if(count<2*InpStructurePivotDepth+10) return false;
   recent_high=0.0; previous_high=0.0; recent_low=0.0; previous_low=0.0;
   int highs=0,lows=0;
   for(int i=InpStructurePivotDepth;i<count-InpStructurePivotDepth;i++)
   {
      if(highs<2 && IsPivotHigh(rates,i,InpStructurePivotDepth))
      {
         if(highs==0) recent_high=rates[i].high;
         else previous_high=rates[i].high;
         highs++;
      }
      if(lows<2 && IsPivotLow(rates,i,InpStructurePivotDepth))
      {
         if(lows==0) recent_low=rates[i].low;
         else previous_low=rates[i].low;
         lows++;
      }
      if(highs>=2 && lows>=2) break;
   }
   return highs>=2 && lows>=2;
}

int StructureDirection(const ENUM_TIMEFRAMES timeframe)
{
   double h1=0.0,h2=0.0,l1=0.0,l2=0.0;
   if(!RecentPivots(timeframe,1,h1,h2,l1,l2)) return 0;
   if(h1>h2 && l1>l2) return 1;
   if(h1<h2 && l1<l2) return -1;
   return 0;
}

int AlignedTrendDirection()
{
   int h1=StructureDirection(PERIOD_H1);
   int m15=StructureDirection(PERIOD_M15);
   return (h1!=0 && h1==m15 ? h1 : 0);
}

double CandleBodyRatio(const MqlRates &bar)
{
   double width=bar.high-bar.low;
   return (width>0.0 ? MathAbs(bar.close-bar.open)/width : 0.0);
}

bool FindTouchedZone(const int direction,const MqlRates &signal,const double atr,
                     double &zone_low,double &zone_high)
{
   MqlRates rates[];
   ArraySetAsSeries(rates,true);
   int count=CopyRates(_Symbol,PERIOD_M15,1,InpZoneLookbackBars+InpZoneBreakLookback+10,rates);
   if(count<InpZoneBreakLookback+10) return false;
   for(int i=2;i<count-InpZoneBreakLookback;i++)
   {
      MqlRates base=rates[i];
      MqlRates impulse=rates[i-1];
      double body=MathAbs(impulse.close-impulse.open);
      if(body<InpZoneDisplacementATR*atr) continue;
      double older_high=-DBL_MAX,older_low=DBL_MAX;
      for(int j=i+1;j<=i+InpZoneBreakLookback && j<count;j++)
      {
         older_high=MathMax(older_high,rates[j].high);
         older_low=MathMin(older_low,rates[j].low);
      }
      bool candidate=false;
      if(direction>0)
         candidate=(base.close<base.open && impulse.close>impulse.open && impulse.close>older_high);
      else
         candidate=(base.close>base.open && impulse.close<impulse.open && impulse.close<older_low);
      if(!candidate) continue;

      bool active=true;
      for(int j=0;j<i;j++)
      {
         if(direction>0 && rates[j].close<base.low) { active=false; break; }
         if(direction<0 && rates[j].close>base.high) { active=false; break; }
      }
      if(!active) continue;
      if(signal.low>base.high || signal.high<base.low) continue;
      zone_low=base.low;
      zone_high=base.high;
      return true;
   }
   return false;
}

bool NearestM15Target(const int direction,const double entry,double &target)
{
   MqlRates rates[];
   ArraySetAsSeries(rates,true);
   int count=CopyRates(_Symbol,PERIOD_M15,1,InpStructureLookback+20,rates);
   if(count<20) return false;
   target=(direction>0 ? DBL_MAX : -DBL_MAX);
   bool found=false;
   for(int i=InpStructurePivotDepth;i<count-InpStructurePivotDepth;i++)
   {
      if(direction>0 && IsPivotHigh(rates,i,InpStructurePivotDepth) && rates[i].high>entry)
      {
         if(rates[i].high<target) target=rates[i].high;
         found=true;
      }
      if(direction<0 && IsPivotLow(rates,i,InpStructurePivotDepth) && rates[i].low<entry)
      {
         if(rates[i].low>target) target=rates[i].low;
         found=true;
      }
   }
   return found;
}

bool SelectOurPosition(ulong &ticket)
{
   for(int i=PositionsTotal()-1;i>=0;i--)
   {
      ulong candidate=PositionGetTicket(i);
      if(candidate==0) continue;
      if(PositionGetString(POSITION_SYMBOL)==_Symbol && PositionGetInteger(POSITION_MAGIC)==InpMagic)
      {
         ticket=candidate;
         return true;
      }
   }
   return false;
}

bool SpreadOK(const double atr)
{
   MqlTick tick;
   if(!SymbolInfoTick(_Symbol,tick) || atr<=0.0) return false;
   return (tick.ask-tick.bid)/atr*100.0<=InpMaximumSpreadATRPercent;
}

bool EnterTrade(const int direction,const MqlRates &signal,const double protected_extreme,const double atr)
{
   if(!InpEnableTrading || g_trades_today>=InpMaximumTradesPerDay || !SpreadOK(atr)) return false;
   ulong existing=0;
   if(SelectOurPosition(existing)) return false;
   MqlTick tick;
   if(!SymbolInfoTick(_Symbol,tick)) return false;
   double entry=(direction>0 ? tick.ask : tick.bid);
   double stop=NormalizePrice(direction>0 ? protected_extreme-InpStopBufferATR*atr
                                         : protected_extreme+InpStopBufferATR*atr);
   double risk=(direction>0 ? entry-stop : stop-entry);
   if(risk<=0.0 || risk>InpMaximumStopATR*atr) return false;
   double point=SymbolInfoDouble(_Symbol,SYMBOL_POINT);
   double minimum=SymbolInfoInteger(_Symbol,SYMBOL_TRADE_STOPS_LEVEL)*point;
   if(risk<minimum) return false;

   double logical_target=0.0;
   if(!NearestM15Target(direction,entry,logical_target)) return false;
   double reward=(direction>0 ? logical_target-entry : entry-logical_target);
   if(reward<InpMinimumRewardRisk*risk) return false;
   if(reward>InpMaximumRewardRisk*risk)
      logical_target=(direction>0 ? entry+InpMaximumRewardRisk*risk : entry-InpMaximumRewardRisk*risk);
   double target=NormalizePrice(logical_target);
   ENUM_ORDER_TYPE order_type=(direction>0 ? ORDER_TYPE_BUY : ORDER_TYPE_SELL);
   double lots=LotsForRisk(order_type,entry,stop);
   if(lots<=0.0) return false;

   trade.SetExpertMagicNumber((ulong)InpMagic);
   trade.SetTypeFillingBySymbol(_Symbol);
   trade.SetDeviationInPoints(InpMaxDeviationPoints);
   string comment=StringFormat("GLS %s",direction>0 ? "sweep long" : "sweep short");
   bool sent=(direction>0 ? trade.Buy(lots,_Symbol,0.0,stop,target,comment)
                          : trade.Sell(lots,_Symbol,0.0,stop,target,comment));
   if(!sent)
   {
      Print("Gold liquidity entry failed: ",trade.ResultRetcode()," ",trade.ResultRetcodeDescription());
      return false;
   }
   g_trades_today++;
   return true;
}

void ClearPending()
{
   g_pending_direction=0;
   g_pending_stage=0;
   g_pending_age=0;
   g_protected_extreme=0.0;
   g_sweep_high=0.0;
   g_sweep_low=0.0;
   g_market_shift_level=0.0;
   g_retest_zone_low=0.0;
   g_retest_zone_high=0.0;
}

bool DetectSweep(const MqlRates &signal,const int direction,const double atr,
                 double &protected_extreme,double &market_shift_level)
{
   double recent_high=0.0,previous_high=0.0,recent_low=0.0,previous_low=0.0;
   if(!RecentPivots(InpSignalTimeframe,2,recent_high,previous_high,recent_low,previous_low)) return false;
   double zone_low=0.0,zone_high=0.0;
   if(!FindTouchedZone(direction,signal,atr,zone_low,zone_high)) return false;
   double width=signal.high-signal.low;
   if(width<=0.0) return false;
   if(direction>0)
   {
      bool swept=signal.low<recent_low-InpSweepBufferATR*atr && signal.close>recent_low;
      bool recovered=(signal.close-signal.low)/width>=InpSweepRecoveryFraction;
      if(!swept || !recovered) return false;
      protected_extreme=signal.low;
      market_shift_level=recent_high;
      return true;
   }
   bool swept=signal.high>recent_high+InpSweepBufferATR*atr && signal.close<recent_high;
   bool recovered=(signal.high-signal.close)/width>=InpSweepRecoveryFraction;
   if(!swept || !recovered) return false;
   protected_extreme=signal.high;
   market_shift_level=recent_low;
   return true;
}

bool InTradingWindow(const MqlDateTime &utc)
{
   if(InpWeekdaysOnly && (utc.day_of_week==0 || utc.day_of_week==6)) return false;
   if(!InpUseTradingWindow) return true;
   int minutes=utc.hour*60+utc.min;
   int start=InpStartHourUTC*60;
   int finish=InpEndHourUTC*60;
   if(start<finish) return minutes>=start && minutes<finish;
   return minutes>=start || minutes<finish;
}

int CountTodayEntries(const MqlDateTime &utc_date)
{
   MqlDateTime start=utc_date;
   start.hour=0; start.min=0; start.sec=0;
   datetime from_utc=StructToTime(start);
   datetime from_server=from_utc+ServerUTCOffsetSeconds();
   datetime to_server=from_server+86400-1;
   if(!HistorySelect(from_server,to_server)) return 0;
   int count=0;
   for(int i=0;i<HistoryDealsTotal();i++)
   {
      ulong deal=HistoryDealGetTicket(i);
      if(deal==0) continue;
      if(HistoryDealGetString(deal,DEAL_SYMBOL)==_Symbol &&
         HistoryDealGetInteger(deal,DEAL_MAGIC)==InpMagic &&
         HistoryDealGetInteger(deal,DEAL_ENTRY)==DEAL_ENTRY_IN) count++;
   }
   return count;
}

void ManagePosition()
{
   ulong ticket=0;
   if(!SelectOurPosition(ticket) || !PositionSelectByTicket(ticket)) return;
   datetime opened=(datetime)PositionGetInteger(POSITION_TIME);
   if(opened<=0 || TimeCurrent()-opened<InpMaximumHoldingMinutes*60) return;
   trade.SetExpertMagicNumber((ulong)InpMagic);
   trade.SetTypeFillingBySymbol(_Symbol);
   trade.SetDeviationInPoints(InpMaxDeviationPoints);
   if(!trade.PositionClose(ticket))
      Print("Gold liquidity time exit failed: ",trade.ResultRetcode()," ",trade.ResultRetcodeDescription());
}

void ProcessPending(const MqlRates &bar,const double atr)
{
   if(g_pending_direction==0) return;
   g_pending_age++;
   int direction=g_pending_direction;
   if(InpEntryMode==GLS_MOMENTUM_CONFIRM)
   {
      if(g_pending_age>InpConfirmationBars) { ClearPending(); return; }
      bool body=CandleBodyRatio(bar)>=InpConfirmationBodyRatio;
      bool confirmed=(direction>0 ? bar.close>bar.open && bar.close>g_sweep_high
                                  : bar.close<bar.open && bar.close<g_sweep_low);
      if(body && confirmed)
      {
         double extreme=g_protected_extreme;
         ClearPending();
         EnterTrade(direction,bar,extreme,atr);
      }
      return;
   }

   if(InpEntryMode==GLS_MARKET_SHIFT_RETEST)
   {
      if(g_pending_stage==1)
      {
         if(g_pending_age>InpConfirmationBars) { ClearPending(); return; }
         bool shifted=(direction>0 ? bar.close>g_market_shift_level : bar.close<g_market_shift_level);
         if(shifted)
         {
            g_pending_stage=2;
            g_pending_age=0;
            if(direction>0)
            {
               g_retest_zone_low=bar.low;
               g_retest_zone_high=MathMin(bar.open,bar.close);
            }
            else
            {
               g_retest_zone_low=MathMax(bar.open,bar.close);
               g_retest_zone_high=bar.high;
            }
         }
         return;
      }
      if(g_pending_age>InpRetestBars) { ClearPending(); return; }
      bool touched=bar.low<=g_retest_zone_high && bar.high>=g_retest_zone_low;
      bool confirmed=(direction>0 ? bar.close>bar.open && bar.close>=g_retest_zone_high
                                  : bar.close<bar.open && bar.close<=g_retest_zone_low);
      if(touched && confirmed && CandleBodyRatio(bar)>=InpConfirmationBodyRatio)
      {
         double extreme=g_protected_extreme;
         ClearPending();
         EnterTrade(direction,bar,extreme,atr);
      }
   }
}

void EvaluateClosedBar(const MqlDateTime &utc_now)
{
   MqlRates bars[];
   ArraySetAsSeries(bars,true);
   if(CopyRates(_Symbol,InpSignalTimeframe,1,1,bars)!=1) return;
   MqlRates signal=bars[0];
   double atr=0.0;
   if(!LatestIndicatorValue(g_atr_m15_handle,1,atr)) return;
   if(g_pending_direction!=0)
   {
      ProcessPending(signal,atr);
      return;
   }
   if(!InTradingWindow(utc_now) || g_trades_today>=InpMaximumTradesPerDay) return;
   ulong existing=0;
   if(SelectOurPosition(existing)) return;
   int direction=AlignedTrendDirection();
   if(direction==0) return;
   double protected_extreme=0.0,shift_level=0.0;
   if(!DetectSweep(signal,direction,atr,protected_extreme,shift_level)) return;
   if(InpEntryMode==GLS_SWEEP_CLOSE)
   {
      EnterTrade(direction,signal,protected_extreme,atr);
      return;
   }
   g_pending_direction=direction;
   g_pending_stage=1;
   g_pending_age=0;
   g_protected_extreme=protected_extreme;
   g_sweep_high=signal.high;
   g_sweep_low=signal.low;
   g_market_shift_level=shift_level;
}

void ProcessStrategy()
{
   ManagePosition();
   datetime current_bar=iTime(_Symbol,InpSignalTimeframe,0);
   if(current_bar<=0 || current_bar==g_last_bar) return;
   g_last_bar=current_bar;
   datetime utc_time=ServerToUTC(TimeCurrent());
   MqlDateTime utc; TimeToStruct(utc_time,utc);
   int key=DateKey(utc);
   if(key!=g_utc_date_key)
   {
      g_utc_date_key=key;
      g_trades_today=CountTodayEntries(utc);
      ClearPending();
   }
   EvaluateClosedBar(utc);
}

int OnInit()
{
   if(InpRiskPercent<=0.0 || InpRiskPercent>2.0 || InpStructurePivotDepth<1 ||
      InpStructureLookback<30 || InpZoneLookbackBars<20 || InpZoneBreakLookback<2 ||
      InpZoneDisplacementATR<=0.0 || InpSweepBufferATR<0.0 ||
      InpSweepRecoveryFraction<0.5 || InpSweepRecoveryFraction>1.0 ||
      InpConfirmationBars<1 || InpRetestBars<1 || InpConfirmationBodyRatio<0.0 ||
      InpConfirmationBodyRatio>1.0 || InpMaximumStopATR<=0.0 ||
      InpMinimumRewardRisk<=0.0 || InpMaximumRewardRisk<InpMinimumRewardRisk ||
      InpMaximumHoldingMinutes<5 || InpMaximumTradesPerDay<1 ||
      InpStartHourUTC<0 || InpStartHourUTC>23 || InpEndHourUTC<0 || InpEndHourUTC>23)
      return INIT_PARAMETERS_INCORRECT;
   g_atr_m5_handle=iATR(_Symbol,InpSignalTimeframe,14);
   g_atr_m15_handle=iATR(_Symbol,PERIOD_M15,14);
   if(g_atr_m5_handle==INVALID_HANDLE || g_atr_m15_handle==INVALID_HANDLE) return INIT_FAILED;
   g_last_bar=iTime(_Symbol,InpSignalTimeframe,0);
   EventSetTimer(10);
   return INIT_SUCCEEDED;
}

void OnDeinit(const int reason)
{
   EventKillTimer();
   if(g_atr_m5_handle!=INVALID_HANDLE) IndicatorRelease(g_atr_m5_handle);
   if(g_atr_m15_handle!=INVALID_HANDLE) IndicatorRelease(g_atr_m15_handle);
}

void OnTick()
{
   ProcessStrategy();
}

void OnTimer()
{
   ProcessStrategy();
}

double OnTester()
{
   double trades=TesterStatistics(STAT_TRADES);
   double profit=TesterStatistics(STAT_PROFIT);
   double pf=TesterStatistics(STAT_PROFIT_FACTOR);
   double dd=TesterStatistics(STAT_EQUITY_DDREL_PERCENT);
   if(trades<40.0 || profit<=0.0 || pf<1.05 || dd<=0.0) return -1000.0+trades;
   return (profit/dd)*MathMin(2.0,MathSqrt(trades/80.0))*MathMin(pf,3.0);
}
