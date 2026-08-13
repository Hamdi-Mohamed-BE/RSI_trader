#property copyright "Independent ICT and support/resistance research implementation"
#property version   "1.00"
#property strict

#include <Trade/Trade.mqh>

CTrade g_trade;

enum ENUM_ICT_BIAS_MODE
{
   ICT_BIAS_NONE=0,
   ICT_BIAS_PREMIUM_DISCOUNT=1,
   ICT_BIAS_H1_RANGE=2,
   ICT_BIAS_BOTH=3
};

enum ENUM_ICT_SETUP_STATE
{
   ICT_IDLE=0,
   ICT_SWEPT=1,
   ICT_WAIT_FVG=2
};

input group "Chart and level model"
input ENUM_TIMEFRAMES InpSignalTimeframe=PERIOD_M5;
input int    InpLevelMask=15;                 // 1 previous day, 2 Asia, 4 H1 swing, 8 previous week
input int    InpH1SwingLookback=72;
input int    InpH1SwingWidth=2;
input int    InpTouchLookback=72;
input int    InpTouchSeparationBars=4;
input double InpLevelZoneATR=0.12;
input int    InpMinimumLevelScore=2;
input ENUM_ICT_BIAS_MODE InpBiasMode=ICT_BIAS_PREMIUM_DISCOUNT;

input group "Liquidity raid"
input double InpMinimumSweepATR=0.03;
input double InpMaximumSweepATR=0.70;
input double InpMinimumCloseLocation=0.60;
input int    InpInternalSwingLookback=6;
input int    InpMaximumMSSBars=6;

input group "Displacement and fair value gap"
input double InpDisplacementBodyATR=0.80;
input double InpMinimumFVGATR=0.03;
input double InpFVGRetracement=0.50;
input int    InpMaximumFVGWaitBars=6;
input double InpMaximumEntryChaseATR=0.50;

input group "UTC sessions"
input int    InpAsiaStartUTC=0;
input int    InpAsiaEndUTC=7;
input int    InpSessionStartUTC=7;
input int    InpSessionEndUTC=16;
input int    InpTesterServerUTCOffsetHours=0;
input bool   InpFlatAtSessionEnd=true;
input int    InpMaximumTradesPerDay=1;

input group "Risk and exits"
input int    InpATRPeriod=14;
input double InpStopBufferATR=0.15;
input double InpMinimumStopATR=0.40;
input double InpMaximumStopATR=3.00;
input double InpRewardRisk=2.50;
input double InpBreakEvenAtR=1.00;
input double InpBreakEvenLockR=0.05;
input double InpTrailStartR=10.00;
input double InpTrailATR=1.50;
input double InpMaximumSpreadATR=0.12;
input double InpRiskPercent=1.00;
input bool   InpEnableLong=true;
input bool   InpEnableShort=true;
input long   InpMagic=861313;
input int    InpMaximumDeviationPoints=100;

datetime g_last_bar=0;
int g_atr_handle=INVALID_HANDLE;
int g_date_key=-1;
int g_trades_today=0;
ENUM_ICT_SETUP_STATE g_state=ICT_IDLE;
bool g_long_setup=false;
int g_state_bars=0;
double g_swept_level=0.0;
double g_sweep_extreme=0.0;
double g_mss_level=0.0;
double g_fvg_lower=0.0;
double g_fvg_upper=0.0;
double g_fvg_entry=0.0;
double g_initial_risk=0.0;
datetime g_displacement_time=0;

double Price(const double value)
{
   return NormalizeDouble(value,(int)SymbolInfoInteger(_Symbol,SYMBOL_DIGITS));
}

double Volume(const double raw)
{
   double minimum=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MIN);
   double maximum=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MAX);
   double step=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_STEP);
   if(minimum<=0.0 || maximum<=0.0 || step<=0.0 || raw<minimum) return 0.0;
   double lots=MathFloor((MathMin(raw,maximum)+1e-12)/step)*step;
   return NormalizeDouble(lots,8);
}

double LotsForRisk(const ENUM_ORDER_TYPE type,const double entry,const double stop)
{
   double result=0.0;
   if(InpRiskPercent<=0.0 || entry<=0.0 || stop<=0.0 || entry==stop) return 0.0;
   if(!OrderCalcProfit(type,_Symbol,1.0,entry,stop,result)) return 0.0;
   double one_lot_loss=MathAbs(result);
   if(one_lot_loss<=0.0) return 0.0;
   return Volume(AccountInfoDouble(ACCOUNT_EQUITY)*InpRiskPercent/100.0/one_lot_loss);
}

double BufferValue(const int handle,const int shift)
{
   double values[];
   ArraySetAsSeries(values,true);
   if(handle==INVALID_HANDLE || CopyBuffer(handle,0,shift,1,values)!=1) return EMPTY_VALUE;
   return values[0];
}

bool NewBar()
{
   datetime current=iTime(_Symbol,InpSignalTimeframe,0);
   if(current<=0 || current==g_last_bar) return false;
   g_last_bar=current;
   return true;
}

datetime ToUTC(const datetime server_time)
{
   if((bool)MQLInfoInteger(MQL_TESTER)) return server_time-InpTesterServerUTCOffsetHours*3600;
   return server_time-(TimeCurrent()-TimeGMT());
}

datetime FromUTC(const datetime utc_time)
{
   if((bool)MQLInfoInteger(MQL_TESTER)) return utc_time+InpTesterServerUTCOffsetHours*3600;
   return utc_time+(TimeCurrent()-TimeGMT());
}

datetime UTCMidnight(const datetime server_time)
{
   MqlDateTime p;
   TimeToStruct(ToUTC(server_time),p);
   p.hour=0; p.min=0; p.sec=0;
   return StructToTime(p);
}

int UTCDateKey(const datetime server_time)
{
   MqlDateTime p;
   TimeToStruct(ToUTC(server_time),p);
   return p.year*10000+p.mon*100+p.day;
}

int UTCHour(const datetime server_time)
{
   MqlDateTime p;
   TimeToStruct(ToUTC(server_time),p);
   return p.hour;
}

bool InSession(const datetime server_time)
{
   int hour=UTCHour(server_time);
   if(InpSessionStartUTC<InpSessionEndUTC) return hour>=InpSessionStartUTC && hour<InpSessionEndUTC;
   return hour>=InpSessionStartUTC || hour<InpSessionEndUTC;
}

bool RangeBetweenUTC(const datetime utc_from,const datetime utc_to,double &high,double &low)
{
   high=-DBL_MAX;
   low=DBL_MAX;
   if(utc_to<=utc_from) return false;
   MqlRates rates[];
   ArraySetAsSeries(rates,false);
   int copied=CopyRates(_Symbol,PERIOD_M15,FromUTC(utc_from),FromUTC(utc_to)-1,rates);
   if(copied<=0) return false;
   for(int i=0;i<copied;i++)
   {
      high=MathMax(high,rates[i].high);
      low=MathMin(low,rates[i].low);
   }
   return high>low && high>-DBL_MAX && low<DBL_MAX;
}

bool PreviousDayRange(const datetime server_time,double &high,double &low)
{
   datetime midnight=UTCMidnight(server_time);
   return RangeBetweenUTC(midnight-86400,midnight,high,low);
}

bool AsiaRange(const datetime server_time,double &high,double &low)
{
   datetime midnight=UTCMidnight(server_time);
   datetime utc_now=ToUTC(server_time);
   datetime start=midnight+InpAsiaStartUTC*3600;
   datetime finish=midnight+InpAsiaEndUTC*3600;
   if(InpAsiaEndUTC<=InpAsiaStartUTC) finish+=86400;
   if(utc_now<finish) return false;
   return RangeBetweenUTC(start,finish,high,low);
}

bool ConfirmedH1Swing(const bool want_high,double &level)
{
   int width=MathMax(1,InpH1SwingWidth);
   int maximum=MathMax(width*2+4,InpH1SwingLookback);
   int bars=Bars(_Symbol,PERIOD_H1);
   if(bars<maximum+width+2) maximum=bars-width-2;
   for(int shift=width+1;shift<=maximum;shift++)
   {
      double candidate=(want_high ? iHigh(_Symbol,PERIOD_H1,shift) : iLow(_Symbol,PERIOD_H1,shift));
      if(candidate<=0.0) continue;
      bool confirmed=true;
      for(int j=1;j<=width;j++)
      {
         double newer=(want_high ? iHigh(_Symbol,PERIOD_H1,shift-j) : iLow(_Symbol,PERIOD_H1,shift-j));
         double older=(want_high ? iHigh(_Symbol,PERIOD_H1,shift+j) : iLow(_Symbol,PERIOD_H1,shift+j));
         if(want_high)
         {
            if(candidate<=newer || candidate<older) { confirmed=false; break; }
         }
         else
         {
            if(candidate>=newer || candidate>older) { confirmed=false; break; }
         }
      }
      if(confirmed) { level=candidate; return true; }
   }
   return false;
}

int BuildLevels(const datetime server_time,double &supports[],double &resistances[])
{
   ArrayResize(supports,0);
   ArrayResize(resistances,0);
   double high=0.0,low=0.0;
   if((InpLevelMask&1)!=0 && PreviousDayRange(server_time,high,low))
   {
      int n=ArraySize(supports); ArrayResize(supports,n+1); supports[n]=low;
      n=ArraySize(resistances); ArrayResize(resistances,n+1); resistances[n]=high;
   }
   if((InpLevelMask&2)!=0 && AsiaRange(server_time,high,low))
   {
      int n=ArraySize(supports); ArrayResize(supports,n+1); supports[n]=low;
      n=ArraySize(resistances); ArrayResize(resistances,n+1); resistances[n]=high;
   }
   if((InpLevelMask&4)!=0)
   {
      if(ConfirmedH1Swing(false,low)) { int n=ArraySize(supports); ArrayResize(supports,n+1); supports[n]=low; }
      if(ConfirmedH1Swing(true,high)) { int n=ArraySize(resistances); ArrayResize(resistances,n+1); resistances[n]=high; }
   }
   if((InpLevelMask&8)!=0)
   {
      low=iLow(_Symbol,PERIOD_W1,1); high=iHigh(_Symbol,PERIOD_W1,1);
      if(low>0.0 && high>low)
      {
         int n=ArraySize(supports); ArrayResize(supports,n+1); supports[n]=low;
         n=ArraySize(resistances); ArrayResize(resistances,n+1); resistances[n]=high;
      }
   }
   return MathMax(ArraySize(supports),ArraySize(resistances));
}

int RecentTouches(const double level,const bool support,const double tolerance)
{
   int touches=0;
   int most_recent=-100000;
   int lookback=MathMax(10,InpTouchLookback);
   int separation=MathMax(1,InpTouchSeparationBars);
   for(int shift=3;shift<=lookback;shift++)
   {
      double high=iHigh(_Symbol,InpSignalTimeframe,shift);
      double low=iLow(_Symbol,InpSignalTimeframe,shift);
      double close=iClose(_Symbol,InpSignalTimeframe,shift);
      bool hit=(low<=level+tolerance && high>=level-tolerance);
      bool rejected=(support ? close>level : close<level);
      if(hit && rejected && shift-most_recent>=separation)
      {
         touches++;
         most_recent=shift;
         if(touches>=3) break;
      }
   }
   return touches;
}

int LevelScore(const double level,const bool support,const double tolerance,
               const double &supports[],const double &resistances[])
{
   int score=0;
   if(support)
   {
      for(int i=0;i<ArraySize(supports);i++) if(MathAbs(supports[i]-level)<=tolerance) score++;
   }
   else
   {
      for(int i=0;i<ArraySize(resistances);i++) if(MathAbs(resistances[i]-level)<=tolerance) score++;
   }
   return score+RecentTouches(level,support,tolerance);
}

bool BiasAllows(const bool is_long,const double level,const datetime signal_time)
{
   bool premium_ok=true;
   bool h1_ok=true;
   if(InpBiasMode==ICT_BIAS_PREMIUM_DISCOUNT || InpBiasMode==ICT_BIAS_BOTH)
   {
      double high=0.0,low=0.0;
      premium_ok=PreviousDayRange(signal_time,high,low) && (is_long ? level<=(high+low)/2.0 : level>=(high+low)/2.0);
   }
   if(InpBiasMode==ICT_BIAS_H1_RANGE || InpBiasMode==ICT_BIAS_BOTH)
   {
      double high=0.0,low=0.0;
      h1_ok=ConfirmedH1Swing(true,high) && ConfirmedH1Swing(false,low) && high>low;
      if(h1_ok)
      {
         double close=iClose(_Symbol,PERIOD_H1,1);
         h1_ok=(is_long ? close>=(high+low)/2.0 : close<=(high+low)/2.0);
      }
   }
   return premium_ok && h1_ok;
}

bool FindLiquiditySweep(const bool is_long,const double atr,const datetime signal_time,
                        double &selected,int &selected_score)
{
   double supports[],resistances[];
   if(BuildLevels(signal_time,supports,resistances)<=0) return false;
   double tolerance=InpLevelZoneATR*atr;
   double open=iOpen(_Symbol,InpSignalTimeframe,1);
   double high=iHigh(_Symbol,InpSignalTimeframe,1);
   double low=iLow(_Symbol,InpSignalTimeframe,1);
   double close=iClose(_Symbol,InpSignalTimeframe,1);
   double previous=iClose(_Symbol,InpSignalTimeframe,2);
   double range=high-low;
   if(range<=0.0) return false;
   double close_location=(close-low)/range;
   if(!is_long) close_location=(high-close)/range;
   if(close_location<InpMinimumCloseLocation) return false;

   double levels[];
   if(is_long) ArrayCopy(levels,supports); else ArrayCopy(levels,resistances);
   bool found=false;
   selected_score=-1;
   double best_distance=DBL_MAX;
   for(int i=0;i<ArraySize(levels);i++)
   {
      double level=levels[i];
      double depth=(is_long ? level-low : high-level);
      bool approached=(is_long ? previous>level : previous<level);
      bool reclaimed=(is_long ? close>level : close<level);
      if(!approached || !reclaimed || depth<InpMinimumSweepATR*atr || depth>InpMaximumSweepATR*atr) continue;
      if(!BiasAllows(is_long,level,signal_time)) continue;
      int score=LevelScore(level,is_long,tolerance,supports,resistances);
      if(score<InpMinimumLevelScore) continue;
      double distance=MathAbs(close-level);
      if(!found || score>selected_score || (score==selected_score && distance<best_distance))
      {
         found=true;
         selected=level;
         selected_score=score;
         best_distance=distance;
      }
   }
   return found;
}

double Highest(const int start_shift,const int count)
{
   double value=-DBL_MAX;
   for(int i=start_shift;i<start_shift+count;i++) value=MathMax(value,iHigh(_Symbol,InpSignalTimeframe,i));
   return value;
}

double Lowest(const int start_shift,const int count)
{
   double value=DBL_MAX;
   for(int i=start_shift;i<start_shift+count;i++) value=MathMin(value,iLow(_Symbol,InpSignalTimeframe,i));
   return value;
}

void ResetSetup()
{
   g_state=ICT_IDLE;
   g_state_bars=0;
   g_swept_level=0.0;
   g_sweep_extreme=0.0;
   g_mss_level=0.0;
   g_fvg_lower=0.0;
   g_fvg_upper=0.0;
   g_fvg_entry=0.0;
   g_displacement_time=0;
}

bool SelectOurPosition(ulong &ticket)
{
   for(int i=PositionsTotal()-1;i>=0;i--)
   {
      ticket=PositionGetTicket(i);
      if(ticket==0) continue;
      if(PositionGetString(POSITION_SYMBOL)==_Symbol && PositionGetInteger(POSITION_MAGIC)==InpMagic) return true;
   }
   ticket=0;
   return false;
}

void CloseOurPosition()
{
   ulong ticket=0;
   if(SelectOurPosition(ticket) && !g_trade.PositionClose(ticket,(ulong)InpMaximumDeviationPoints))
      Print("ICT SNR close failed: ",g_trade.ResultRetcodeDescription());
}

void ManagePosition(const double atr)
{
   ulong ticket=0;
   if(!SelectOurPosition(ticket)) { g_initial_risk=0.0; return; }
   long type=PositionGetInteger(POSITION_TYPE);
   double open=PositionGetDouble(POSITION_PRICE_OPEN);
   double stop=PositionGetDouble(POSITION_SL);
   double target=PositionGetDouble(POSITION_TP);
   if(g_initial_risk<=0.0) g_initial_risk=MathAbs(open-stop);
   if(g_initial_risk<=0.0) return;
   MqlTick tick;
   if(!SymbolInfoTick(_Symbol,tick)) return;
   double current=(type==POSITION_TYPE_BUY ? tick.bid : tick.ask);
   double distance=(type==POSITION_TYPE_BUY ? current-open : open-current);
   double achieved_r=distance/g_initial_risk;
   double candidate=stop;
   if(achieved_r>=InpBreakEvenAtR)
   {
      double locked=(type==POSITION_TYPE_BUY ? open+InpBreakEvenLockR*g_initial_risk : open-InpBreakEvenLockR*g_initial_risk);
      if(type==POSITION_TYPE_BUY) candidate=MathMax(candidate,locked);
      else candidate=(candidate<=0.0 ? locked : MathMin(candidate,locked));
   }
   if(InpTrailATR>0.0 && achieved_r>=InpTrailStartR)
   {
      double trailing=(type==POSITION_TYPE_BUY ? current-InpTrailATR*atr : current+InpTrailATR*atr);
      if(type==POSITION_TYPE_BUY) candidate=MathMax(candidate,trailing);
      else candidate=(candidate<=0.0 ? trailing : MathMin(candidate,trailing));
   }
   candidate=Price(candidate);
   bool valid=(type==POSITION_TYPE_BUY ? candidate>stop && candidate<tick.bid : (stop<=0.0 || candidate<stop) && candidate>tick.ask);
   if(valid && !g_trade.PositionModify(ticket,candidate,target))
      Print("ICT SNR stop update failed: ",g_trade.ResultRetcodeDescription());
}

bool OpenPosition(const bool is_long,const double atr)
{
   MqlTick tick;
   if(!SymbolInfoTick(_Symbol,tick)) return false;
   double entry=(is_long ? tick.ask : tick.bid);
   if(MathAbs(entry-g_fvg_entry)>InpMaximumEntryChaseATR*atr) return false;
   double stop=(is_long ? g_sweep_extreme-InpStopBufferATR*atr : g_sweep_extreme+InpStopBufferATR*atr);
   stop=Price(stop);
   double distance=MathAbs(entry-stop);
   if(distance<InpMinimumStopATR*atr || distance>InpMaximumStopATR*atr) return false;
   double target=Price(is_long ? entry+InpRewardRisk*distance : entry-InpRewardRisk*distance);
   ENUM_ORDER_TYPE type=(is_long ? ORDER_TYPE_BUY : ORDER_TYPE_SELL);
   double lots=LotsForRisk(type,entry,stop);
   if(lots<=0.0) return false;
   bool ok=(is_long ? g_trade.Buy(lots,_Symbol,0.0,stop,target,"ICT SNR raid MSS FVG buy")
                    : g_trade.Sell(lots,_Symbol,0.0,stop,target,"ICT SNR raid MSS FVG sell"));
   if(ok)
   {
      g_initial_risk=distance;
      g_trades_today++;
      ResetSetup();
      return true;
   }
   Print("ICT SNR entry failed: ",g_trade.ResultRetcodeDescription());
   return false;
}

int OnInit()
{
   if(InpATRPeriod<2 || InpH1SwingWidth<1 || InpInternalSwingLookback<2 || InpMaximumMSSBars<1 ||
      InpMaximumFVGWaitBars<1 || InpRiskPercent<=0.0 || InpRewardRisk<=0.0 ||
      InpMinimumStopATR<=0.0 || InpMaximumStopATR<=InpMinimumStopATR ||
      InpFVGRetracement<0.0 || InpFVGRetracement>1.0) return INIT_PARAMETERS_INCORRECT;
   g_atr_handle=iATR(_Symbol,InpSignalTimeframe,InpATRPeriod);
   if(g_atr_handle==INVALID_HANDLE) return INIT_FAILED;
   g_trade.SetExpertMagicNumber((ulong)InpMagic);
   g_trade.SetDeviationInPoints(InpMaximumDeviationPoints);
   g_trade.SetTypeFillingBySymbol(_Symbol);
   return INIT_SUCCEEDED;
}

void OnDeinit(const int reason)
{
   if(g_atr_handle!=INVALID_HANDLE) IndicatorRelease(g_atr_handle);
}

void OnTick()
{
   if(!NewBar()) return;
   double atr=BufferValue(g_atr_handle,1);
   if(atr==EMPTY_VALUE || atr<=0.0) return;
   ManagePosition(atr);

   datetime current_bar=iTime(_Symbol,InpSignalTimeframe,0);
   int date_key=UTCDateKey(current_bar);
   if(date_key!=g_date_key)
   {
      g_date_key=date_key;
      g_trades_today=0;
      if(g_state!=ICT_IDLE) ResetSetup();
   }

   if(!InSession(current_bar))
   {
      if(InpFlatAtSessionEnd) CloseOurPosition();
      if(g_state!=ICT_IDLE) ResetSetup();
      return;
   }

   ulong ticket=0;
   if(SelectOurPosition(ticket) || g_trades_today>=InpMaximumTradesPerDay) return;
   MqlTick tick;
   if(!SymbolInfoTick(_Symbol,tick)) return;
   if(InpMaximumSpreadATR>0.0 && tick.ask-tick.bid>InpMaximumSpreadATR*atr) return;

   if(g_state!=ICT_IDLE) g_state_bars++;

   if(g_state==ICT_IDLE)
   {
      double level=0.0;
      int score=0;
      bool long_sweep=InpEnableLong && FindLiquiditySweep(true,atr,current_bar,level,score);
      bool short_sweep=InpEnableShort && FindLiquiditySweep(false,atr,current_bar,level,score);
      if(long_sweep || short_sweep)
      {
         g_long_setup=long_sweep;
         g_swept_level=level;
         g_sweep_extreme=(g_long_setup ? iLow(_Symbol,InpSignalTimeframe,1) : iHigh(_Symbol,InpSignalTimeframe,1));
         g_mss_level=(g_long_setup ? Highest(2,InpInternalSwingLookback) : Lowest(2,InpInternalSwingLookback));
         g_state=ICT_SWEPT;
         g_state_bars=0;
      }
      return;
   }

   double open1=iOpen(_Symbol,InpSignalTimeframe,1);
   double high1=iHigh(_Symbol,InpSignalTimeframe,1);
   double low1=iLow(_Symbol,InpSignalTimeframe,1);
   double close1=iClose(_Symbol,InpSignalTimeframe,1);

   if(g_state==ICT_SWEPT)
   {
      if(g_state_bars>InpMaximumMSSBars) { ResetSetup(); return; }
      bool invalid=(g_long_setup ? close1<g_swept_level-InpMaximumSweepATR*atr : close1>g_swept_level+InpMaximumSweepATR*atr);
      if(invalid) { ResetSetup(); return; }
      bool displacement=MathAbs(close1-open1)>=InpDisplacementBodyATR*atr;
      bool structure_break=(g_long_setup ? close1>g_mss_level : close1<g_mss_level);
      double high3=iHigh(_Symbol,InpSignalTimeframe,3);
      double low3=iLow(_Symbol,InpSignalTimeframe,3);
      bool gap=(g_long_setup ? low1-high3>=InpMinimumFVGATR*atr : low3-high1>=InpMinimumFVGATR*atr);
      if(displacement && structure_break && gap)
      {
         if(g_long_setup) { g_fvg_lower=high3; g_fvg_upper=low1; }
         else { g_fvg_lower=high1; g_fvg_upper=low3; }
         g_fvg_entry=g_fvg_lower+InpFVGRetracement*(g_fvg_upper-g_fvg_lower);
         g_displacement_time=iTime(_Symbol,InpSignalTimeframe,1);
         g_state=ICT_WAIT_FVG;
         g_state_bars=0;
      }
      return;
   }

   if(g_state==ICT_WAIT_FVG)
   {
      if(g_state_bars>InpMaximumFVGWaitBars) { ResetSetup(); return; }
      bool invalid=(g_long_setup ? close1<g_fvg_lower || low1<g_sweep_extreme-InpStopBufferATR*atr
                                 : close1>g_fvg_upper || high1>g_sweep_extreme+InpStopBufferATR*atr);
      if(invalid) { ResetSetup(); return; }
      bool later_bar=iTime(_Symbol,InpSignalTimeframe,1)>g_displacement_time;
      bool touched=low1<=g_fvg_entry && high1>=g_fvg_entry;
      bool confirmed=(g_long_setup ? close1>g_fvg_entry : close1<g_fvg_entry);
      if(later_bar && touched && confirmed)
      {
         if(!OpenPosition(g_long_setup,atr)) ResetSetup();
      }
   }
}
