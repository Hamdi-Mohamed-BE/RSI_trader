#ifndef AAA_FINAL_STRATEGY_ENGINE_MQH
#define AAA_FINAL_STRATEGY_ENGINE_MQH

#include "AAA_Final_Common.mqh"

#define AAA_ID_EMA3             1
#define AAA_ID_ASIA             2
#define AAA_ID_DMC              3
#define AAA_ID_AMD              4
#define AAA_ID_US100_WEAKNESS    5
#define AAA_ID_NEWS_PULSE       6
#define AAA_ID_WEEKEND          7
#define AAA_ID_XAU_GRID         8
#define AAA_ID_XAU_WEAKNESS     9
#define AAA_ID_XAU_US100_PORT  10

#ifndef AAA_DEFAULT_MARKOV_FILTER
#define AAA_DEFAULT_MARKOV_FILTER false
#endif

input bool   InpEnableTrading = AAA_DEFAULT_ENABLED;
input double InpRiskPercent   = AAA_DEFAULT_RISK;
input double InpRewardRisk    = AAA_DEFAULT_RR;
input long   InpMagic         = AAA_DEFAULT_MAGIC;
input int    InpMaxSpreadPoints = 0;
input int    InpTesterServerClockMode = 1; // 1 = EET/EEST (MEX Atlantic); live trading ignores this

input group "No-lookahead D1 Markov regime filter"
input bool   InpUseMarkovRegimeFilter = AAA_DEFAULT_MARKOV_FILTER;
input int    InpMarkovReturnWindow = 40;
input double InpMarkovThreshold = 0.05;
input double InpMarkovSignalGate = 0.05;
input int    InpMarkovMinLabels = 252;
input int    InpMarkovHistoryBars = 2600;

input group "EMA3"
input int    InpPivotBars=5;
input int    InpTrendEMA=200;
input int    InpTrendSlopeBars=6;
input bool   InpUseTrailing=true;
input double InpTrailStartR=1.5;
input double InpTrailDistanceR=1.0;

input group "Session strategies"
input double InpAsiaBufferPercent=0.03;
input double InpAMDStopBufferRange=0.03;
input double InpDmCFixedStopPrice=22.5;

input group "News and weekend safety gates"
input bool   InpUseEconomicCalendar=true;
input int    InpNewsExpiryMinutes=15;
input double InpNewsStopPrice=9.0;
input bool   InpAllowProvisionalWeekend=false;

input group "Grid and weakness"
input int    InpGridLevels=3;
input double InpGridRiskPercent=0.5;
input double InpWeaknessATRImpulse=2.0;

datetime g_last_bar=0;
long g_last_event_id=0;

bool AAA_SpreadOK()
{
   if(InpMaxSpreadPoints<=0) return true;
   MqlTick tick;
   double point=SymbolInfoDouble(_Symbol,SYMBOL_POINT);
   return SymbolInfoTick(_Symbol,tick) && point>0.0 && (tick.ask-tick.bid)/point<=InpMaxSpreadPoints;
}

bool AAA_LoadRates(const ENUM_TIMEFRAMES timeframe,const int count,MqlRates &rates[])
{
   ArraySetAsSeries(rates,true);
   return CopyRates(_Symbol,timeframe,0,count,rates)>=count;
}

int AAA_MarkovStateAt(MqlRates &daily[],const int index)
{
   double older=daily[index+InpMarkovReturnWindow].close;
   if(older<=0.0) return 1;
   double rolling_return=daily[index].close/older-1.0;
   if(rolling_return>InpMarkovThreshold) return 2;
   if(rolling_return<-InpMarkovThreshold) return 0;
   return 1;
}

bool AAA_MarkovAllowsDirection(const int direction)
{
   if(!InpUseMarkovRegimeFilter) return true;
   int available=Bars(_Symbol,PERIOD_D1);
   int requested=MathMin(InpMarkovHistoryBars,available-1);
   if(requested<=InpMarkovReturnWindow+InpMarkovMinLabels) return false;
   MqlRates daily[];
   ArraySetAsSeries(daily,true);
   int copied=CopyRates(_Symbol,PERIOD_D1,1,requested,daily);
   int labels=copied-InpMarkovReturnWindow;
   if(labels<=InpMarkovMinLabels) return false;
   double counts[3][3];
   for(int row=0;row<3;row++) for(int col=0;col<3;col++) counts[row][col]=0.0;
   int oldest=labels-1;
   // Count only transitions ending before the newest completed D1 state.
   // This matches the research walk-forward rule and prevents lookahead.
   for(int newer=oldest-1;newer>=1;newer--)
   {
      int from=AAA_MarkovStateAt(daily,newer+1);
      int to=AAA_MarkovStateAt(daily,newer);
      counts[from][to]+=1.0;
   }
   int state=AAA_MarkovStateAt(daily,0);
   double total=counts[state][0]+counts[state][1]+counts[state][2];
   if(total<=0.0) return false;
   double signal=(counts[state][2]-counts[state][0])/total;
   return (direction>0 ? signal>InpMarkovSignalGate : signal<-InpMarkovSignalGate);
}

void AAA_RunEMA3()
{
   if(InpUseTrailing) AAA_TrailR(_Symbol,InpMagic,InpTrailStartR,InpTrailDistanceR);
   if(!AAA_NewBar(_Symbol,PERIOD_H4,g_last_bar) || !InpEnableTrading || !AAA_SpreadOK()) return;
   if(AAA_HasExposure(_Symbol,InpMagic)) return;
   MqlRates r[];
   int needed=MathMax(InpPivotBars+3,12);
   if(!AAA_LoadRates(PERIOD_H4,needed,r)) return;
   double trend=AAA_MA(_Symbol,PERIOD_H4,InpTrendEMA,1);
   double trend_old=AAA_MA(_Symbol,PERIOD_H4,InpTrendEMA,1+InpTrendSlopeBars);
   double fast=AAA_MA(_Symbol,PERIOD_H4,20,1);
   double medium=AAA_MA(_Symbol,PERIOD_H4,50,1);
   if(trend==EMPTY_VALUE || trend_old==EMPTY_VALUE) return;
   double prior_high=-DBL_MAX,prior_low=DBL_MAX;
   for(int i=2;i<2+InpPivotBars;i++) { prior_high=MathMax(prior_high,r[i].high); prior_low=MathMin(prior_low,r[i].low); }
   if(r[1].close>prior_high && r[1].close>trend && fast>medium && trend>trend_old)
      AAA_SendMarket(_Symbol,1,prior_low,InpRewardRisk,InpRiskPercent,InpMagic,"AAA EMA3");
   else if(r[1].close<prior_low && r[1].close<trend && fast<medium && trend<trend_old)
      AAA_SendMarket(_Symbol,-1,prior_high,InpRewardRisk,InpRiskPercent,InpMagic,"AAA EMA3");
}

void AAA_RunAsiaBreakout()
{
   if(InpUseTrailing) AAA_TrailR(_Symbol,InpMagic,2.0,0.5);
   if(!AAA_NewBar(_Symbol,PERIOD_H1,g_last_bar) || !InpEnableTrading || !AAA_SpreadOK()) return;
   if(AAA_HasExposure(_Symbol,InpMagic) || AAA_TradedToday(_Symbol,InpMagic)) return;
   MqlDateTime utc; TimeToStruct(AAA_ToUTC(TimeCurrent()),utc);
   if(utc.hour<8 || utc.hour>13) return;
   double high,low;
   if(!AAA_SessionRangeUTC(_Symbol,PERIOD_M15,0,8,high,low)) return;
   MqlRates r[]; if(!AAA_LoadRates(PERIOD_H1,3,r)) return;
   double buffer=(high-low)*InpAsiaBufferPercent;
   double midpoint=(high+low)/2.0;
   if(r[1].close>high+buffer && r[1].low<=high+buffer)
      AAA_SendMarket(_Symbol,1,midpoint,InpRewardRisk,InpRiskPercent,InpMagic,"AAA Asia confirmed retest");
   else if(r[1].close<low-buffer && r[1].high>=low-buffer)
      AAA_SendMarket(_Symbol,-1,midpoint,InpRewardRisk,InpRiskPercent,InpMagic,"AAA Asia confirmed retest");
}

void AAA_RunDmC()
{
   if(!AAA_NewBar(_Symbol,PERIOD_H1,g_last_bar) || !InpEnableTrading || !AAA_SpreadOK()) return;
   if(AAA_HasExposure(_Symbol,InpMagic) || AAA_TradedToday(_Symbol,InpMagic)) return;
   MqlRates day[],hour[];
   if(!AAA_LoadRates(PERIOD_D1,3,day) || !AAA_LoadRates(PERIOD_H1,3,hour)) return;
   double body_high=MathMax(day[1].open,day[1].close);
   double body_low=MathMin(day[1].open,day[1].close);
   MqlTick tick; if(!SymbolInfoTick(_Symbol,tick)) return;
   if(hour[1].low<=body_low && hour[1].close>body_low && hour[1].close>hour[1].open && AAA_MarkovAllowsDirection(1))
      AAA_SendMarket(_Symbol,1,tick.ask-InpDmCFixedStopPrice,InpRewardRisk,InpRiskPercent,InpMagic,"AAA DmC body reaction");
   else if(hour[1].high>=body_high && hour[1].close<body_high && hour[1].close<hour[1].open && AAA_MarkovAllowsDirection(-1))
      AAA_SendMarket(_Symbol,-1,tick.bid+InpDmCFixedStopPrice,InpRewardRisk,InpRiskPercent,InpMagic,"AAA DmC body reaction");
}

void AAA_RunAMD()
{
   if(!AAA_NewBar(_Symbol,PERIOD_M15,g_last_bar) || !InpEnableTrading || !AAA_SpreadOK()) return;
   if(AAA_HasExposure(_Symbol,InpMagic) || AAA_TradedToday(_Symbol,InpMagic)) return;
   MqlDateTime utc; TimeToStruct(AAA_ToUTC(TimeCurrent()),utc);
   if(utc.hour<8 || utc.hour>11) return;
   double high,low;
   if(!AAA_SessionRangeUTC(_Symbol,PERIOD_M15,0,8,high,low)) return;
   MqlRates r[]; if(!AAA_LoadRates(PERIOD_M15,3,r)) return;
   double range=high-low;
   double sweep_min=range*0.0002;
   double stop_buffer=range*InpAMDStopBufferRange;
   if(r[1].high>high+sweep_min && r[1].close<high)
      AAA_SendMarket(_Symbol,-1,r[1].high+stop_buffer,InpRewardRisk,InpRiskPercent,InpMagic,"AAA AMD London fade");
   else if(r[1].low<low-sweep_min && r[1].close>low)
      AAA_SendMarket(_Symbol,1,r[1].low-stop_buffer,InpRewardRisk,InpRiskPercent,InpMagic,"AAA AMD London fade");
}

void AAA_RunReferencePairOCO()
{
   AAA_ManageOCO(_Symbol,InpMagic);
   if(!AAA_NewBar(_Symbol,PERIOD_M15,g_last_bar) || !InpEnableTrading || !AAA_SpreadOK()) return;
   if(AAA_HasExposure(_Symbol,InpMagic) || AAA_TradedToday(_Symbol,InpMagic)) return;
   MqlRates eval[]; if(!AAA_LoadRates(PERIOD_M15,3,eval)) return;
   datetime closed_ny=AAA_ToNewYork(eval[1].time);
   MqlDateTime ny; TimeToStruct(closed_ny,ny);
   if(ny.hour!=10 || ny.min!=0) return;
   MqlDateTime refpart=ny; refpart.hour=9; refpart.min=15; refpart.sec=0;
   datetime ref_server=AAA_NewYorkToServer(StructToTime(refpart));
   int shift=iBarShift(_Symbol,PERIOD_M15,ref_server,true);
   if(shift<1) return;
   double ref_high=iHigh(_Symbol,PERIOD_M15,shift);
   double ref_low=iLow(_Symbol,PERIOD_M15,shift);
   double london_high,london_low;
   if(!AAA_SessionRangeNY(_Symbol,PERIOD_M15,3,8,london_high,london_low)) return;
   refpart.hour=12; refpart.min=0;
   datetime expiry=AAA_NewYorkToServer(StructToTime(refpart));
   if(expiry<=TimeCurrent()) expiry=TimeCurrent()+60*60;
   double half_risk=InpRiskPercent/2.0;
   if(eval[1].close>eval[1].open && london_high>ref_high && london_high>ref_low)
   {
      AAA_SendPending(_Symbol,ORDER_TYPE_SELL_LIMIT,ref_high,london_high,InpRewardRisk,half_risk,InpMagic,expiry,"AAA weakness limit");
      AAA_SendPending(_Symbol,ORDER_TYPE_SELL_STOP,ref_low,london_high,InpRewardRisk,half_risk,InpMagic,expiry,"AAA weakness stop");
   }
   else if(eval[1].close<eval[1].open && london_low<ref_low && london_low<ref_high)
   {
      AAA_SendPending(_Symbol,ORDER_TYPE_BUY_LIMIT,ref_low,london_low,InpRewardRisk,half_risk,InpMagic,expiry,"AAA weakness limit");
      AAA_SendPending(_Symbol,ORDER_TYPE_BUY_STOP,ref_high,london_low,InpRewardRisk,half_risk,InpMagic,expiry,"AAA weakness stop");
   }
}

bool AAA_FindUpcomingPPI(datetime &event_time,long &event_id)
{
   if((bool)MQLInfoInteger(MQL_TESTER))
   {
      // Official BLS release dates inside the requested 2025-08-05 through
      // 2026-08-04 test window. Economic-calendar APIs are unavailable in MT5 tests.
      int dates[10]={20250814,20250910,20251125,20260114,20260130,20260227,20260318,20260414,20260513,20260611};
      int extra_date=20260715;
      datetime now_ny=AAA_ToNewYork(TimeCurrent());
      MqlDateTime p; TimeToStruct(now_ny,p);
      int key=p.year*10000+p.mon*100+p.day;
      bool match=(key==extra_date);
      for(int i=0;i<ArraySize(dates);i++) if(key==dates[i]) { match=true; break; }
      if(!match) return false;
      MqlDateTime release=p; release.hour=8; release.min=30; release.sec=0;
      event_time=AAA_NewYorkToServer(StructToTime(release));
      event_id=key;
      return TimeCurrent()>=event_time-InpNewsExpiryMinutes*60 && TimeCurrent()<=event_time+60;
   }
   if(!InpUseEconomicCalendar) return false;
   MqlCalendarValue values[];
   datetime now=TimeCurrent();
   int total=CalendarValueHistory(values,now-60,now+InpNewsExpiryMinutes*60,NULL,"USD");
   if(total<=0) return false;
   for(int i=0;i<total;i++)
   {
      MqlCalendarEvent event;
      if(!CalendarEventById(values[i].event_id,event)) continue;
      if(StringFind(event.name,"Producer Price")<0 && StringFind(event.name,"PPI")<0) continue;
      if(values[i].time>=now-60 && values[i].time<=now+InpNewsExpiryMinutes*60)
      {
         event_time=values[i].time;
         event_id=(long)values[i].event_id;
         return true;
      }
   }
   return false;
}

void AAA_RunNewsPulse()
{
   AAA_ManageOCO(_Symbol,InpMagic);
   if(!AAA_NewBar(_Symbol,PERIOD_M1,g_last_bar) || !InpEnableTrading || !AAA_SpreadOK()) return;
   if(AAA_HasExposure(_Symbol,InpMagic) || AAA_TradedToday(_Symbol,InpMagic)) return;
   datetime event_time=0; long event_id=0;
   if(!AAA_FindUpcomingPPI(event_time,event_id) || event_id==g_last_event_id) return;
   MqlRates r[]; if(!AAA_LoadRates(PERIOD_M1,4,r)) return;
   double entry_buffer=MathMax(SymbolInfoDouble(_Symbol,SYMBOL_POINT)*10,AAA_ATR(_Symbol,PERIOD_M1,14,1)*0.10);
   double buy_entry=r[1].high+entry_buffer;
   double sell_entry=r[1].low-entry_buffer;
   datetime expiry=event_time+InpNewsExpiryMinutes*60;
   bool a=AAA_SendPending(_Symbol,ORDER_TYPE_BUY_STOP,buy_entry,buy_entry-InpNewsStopPrice,InpRewardRisk,InpRiskPercent/2.0,InpMagic,expiry,"AAA PPI buy");
   bool b=AAA_SendPending(_Symbol,ORDER_TYPE_SELL_STOP,sell_entry,sell_entry+InpNewsStopPrice,InpRewardRisk,InpRiskPercent/2.0,InpMagic,expiry,"AAA PPI sell");
   if(a || b) g_last_event_id=event_id;
}

void AAA_RunWeekend()
{
   if(!AAA_NewBar(_Symbol,PERIOD_M15,g_last_bar) || !InpEnableTrading || !InpAllowProvisionalWeekend || !AAA_SpreadOK()) return;
   if(AAA_HasExposure(_Symbol,InpMagic) || AAA_TradedToday(_Symbol,InpMagic)) return;
   MqlDateTime utc; TimeToStruct(AAA_ToUTC(TimeCurrent()),utc);
   if(utc.day_of_week!=5 || utc.hour<19 || utc.hour>21) return;
   MqlRates r[]; if(!AAA_LoadRates(PERIOD_M15,22,r)) return;
   double momentum=r[1].close-r[21].open;
   MqlTick tick; if(!SymbolInfoTick(_Symbol,tick)) return;
   if(momentum>0.0) AAA_SendMarket(_Symbol,1,tick.ask-30.0,InpRewardRisk,InpRiskPercent,InpMagic,"AAA weekend momentum");
   else if(momentum<0.0) AAA_SendMarket(_Symbol,-1,tick.bid+30.0,InpRewardRisk,InpRiskPercent,InpMagic,"AAA weekend momentum");
}

void AAA_RunXAUGrid()
{
   AAA_ManageOCO(_Symbol,InpMagic);
   if(!AAA_NewBar(_Symbol,PERIOD_M15,g_last_bar) || !InpEnableTrading || !AAA_SpreadOK()) return;
   if(AAA_HasExposure(_Symbol,InpMagic)) return;
   MqlDateTime utc; TimeToStruct(AAA_ToUTC(TimeCurrent()),utc);
   if(utc.hour<6 || utc.hour>=19) return;
   MqlRates r[]; if(!AAA_LoadRates(PERIOD_M15,16,r)) return;
   double atr=AAA_ATR(_Symbol,PERIOD_M15,14,1);
   double rsi=AAA_RSI(_Symbol,PERIOD_M15,14,1);
   double adx=AAA_ADX(_Symbol,PERIOD_H1,14,1);
   double h1_50=AAA_MA(_Symbol,PERIOD_H1,50,1),h1_200=AAA_MA(_Symbol,PERIOD_H1,200,1);
   double h1_50_old=AAA_MA(_Symbol,PERIOD_H1,50,4);
   double h4_20=AAA_MA(_Symbol,PERIOD_H4,20,1),h4_50=AAA_MA(_Symbol,PERIOD_H4,50,1),h4_20_old=AAA_MA(_Symbol,PERIOD_H4,20,3);
   if(atr<=0.0 || adx<18.0 || adx>50.0) return;
   double prior_high=-DBL_MAX,prior_low=DBL_MAX;
   for(int i=2;i<=13;i++){ prior_high=MathMax(prior_high,r[i].high); prior_low=MathMin(prior_low,r[i].low); }
   int direction=0;
   if(r[1].close>prior_high && r[1].close>r[1].open && rsi>=55.0 && h1_50>h1_200 && h1_50>h1_50_old && h4_20>=h4_50 && h4_20>h4_20_old) direction=1;
   if(r[1].close<prior_low && r[1].close<r[1].open && rsi<=45.0 && h1_50<h1_200 && h1_50<h1_50_old && h4_20<=h4_50 && h4_20<h4_20_old) direction=-1;
   if(direction==0) return;
   double anchor=(direction>0 ? r[1].high : r[1].low);
   double offsets[3]={0.10,0.35,0.60};
   double deepest=anchor+direction*offsets[2]*atr;
   double common_stop=anchor-direction*1.0*atr;
   datetime expiry=TimeCurrent()+8*60*60;
   int levels=MathMax(1,MathMin(InpGridLevels,3));
   for(int i=0;i<levels;i++)
   {
      double entry=anchor+direction*offsets[i]*atr;
      AAA_SendPending(_Symbol,(direction>0 ? ORDER_TYPE_BUY_STOP : ORDER_TYPE_SELL_STOP),entry,common_stop,2.0,InpGridRiskPercent/levels,InpMagic,expiry,"AAA XAU grid");
   }
}

void AAA_RunXAUWeakness()
{
   AAA_ManageOCO(_Symbol,InpMagic);
   if(!AAA_NewBar(_Symbol,PERIOD_M15,g_last_bar) || !InpEnableTrading || !AAA_SpreadOK()) return;
   if(AAA_HasExposure(_Symbol,InpMagic)) return;
   MqlRates r[]; if(!AAA_LoadRates(PERIOD_M15,36,r)) return;
   double atr=AAA_ATR(_Symbol,PERIOD_M15,14,1);
   if(atr<=0.0) return;
   double tolerance=0.20*atr;
   int first_high=-1,second_high=-1,first_low=-1,second_low=-1;
   for(int newer=4;newer<=16;newer++)
   {
      for(int older=newer+4;older<=MathMin(newer+16,30);older++)
      {
         if(first_high<0 && MathAbs(r[newer].high-r[older].high)<=tolerance){ second_high=newer; first_high=older; }
         if(first_low<0 && MathAbs(r[newer].low-r[older].low)<=tolerance){ second_low=newer; first_low=older; }
      }
   }
   datetime expiry=TimeCurrent()+8*15*60;
   if(first_high>0)
   {
      double resistance=MathMax(r[first_high].high,r[second_high].high);
      double range_low=DBL_MAX; for(int i=1;i<=first_high;i++) range_low=MathMin(range_low,r[i].low);
      double impulse=r[first_high+1].close-r[MathMin(first_high+12,35)].open;
      if(impulse>=InpWeaknessATRImpulse*atr)
         AAA_SendPending(_Symbol,ORDER_TYPE_BUY_STOP,resistance+0.05*atr,range_low-0.05*atr,2.0,InpRiskPercent,InpMagic,expiry,"AAA XAU weakness breakout");
   }
   else if(first_low>0)
   {
      double support=MathMin(r[first_low].low,r[second_low].low);
      double range_high=-DBL_MAX; for(int i=1;i<=first_low;i++) range_high=MathMax(range_high,r[i].high);
      double impulse=r[MathMin(first_low+12,35)].open-r[first_low+1].close;
      if(impulse>=InpWeaknessATRImpulse*atr)
         AAA_SendPending(_Symbol,ORDER_TYPE_SELL_STOP,support-0.05*atr,range_high+0.05*atr,2.0,InpRiskPercent,InpMagic,expiry,"AAA XAU weakness breakout");
   }
}

int OnInit()
{
   if(!DTS_InputsValid()) return INIT_PARAMETERS_INCORRECT;
   AAA_TesterServerOffsetMode=InpTesterServerClockMode;
   AAA_Trade.SetExpertMagicNumber((ulong)InpMagic);
   AAA_Trade.SetTypeFillingBySymbol(_Symbol);
   Print(AAA_STRATEGY_NAME," loaded on ",_Symbol,". Trading enabled=",InpEnableTrading,"; risk=",DoubleToString(InpRiskPercent,2),"%.");
   return INIT_SUCCEEDED;
}

void OnTick()
{
   DTS_ManageDynamicTrailing(InpMagic);
   if(AAA_STRATEGY_ID==AAA_ID_EMA3) AAA_RunEMA3();
   else if(AAA_STRATEGY_ID==AAA_ID_ASIA) AAA_RunAsiaBreakout();
   else if(AAA_STRATEGY_ID==AAA_ID_DMC) AAA_RunDmC();
   else if(AAA_STRATEGY_ID==AAA_ID_AMD) AAA_RunAMD();
   else if(AAA_STRATEGY_ID==AAA_ID_US100_WEAKNESS || AAA_STRATEGY_ID==AAA_ID_XAU_US100_PORT) AAA_RunReferencePairOCO();
   else if(AAA_STRATEGY_ID==AAA_ID_NEWS_PULSE) AAA_RunNewsPulse();
   else if(AAA_STRATEGY_ID==AAA_ID_WEEKEND) AAA_RunWeekend();
   else if(AAA_STRATEGY_ID==AAA_ID_XAU_GRID) AAA_RunXAUGrid();
   else if(AAA_STRATEGY_ID==AAA_ID_XAU_WEAKNESS) AAA_RunXAUWeakness();
}

#endif
