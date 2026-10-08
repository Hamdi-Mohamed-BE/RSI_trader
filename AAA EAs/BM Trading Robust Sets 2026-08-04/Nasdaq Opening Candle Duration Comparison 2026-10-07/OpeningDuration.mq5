// Entry-only adapter. Original production source and management are included unchanged.
#define ProcessNewBar N5ProductionProcessNewBar
#define OnInit N5ProductionOnInit
#define OnTick N5ProductionOnTick
#include "..\Nasdaq 5M DI ATR Deployment 2026-09-28\EA\Nasdaq 5M DI Wide ATR EA.mq5"
#undef ProcessNewBar
#undef OnInit
#undef OnTick

input group "Research only: opening candle duration"
input ENUM_TIMEFRAMES InpOpeningCandleTimeframe=PERIOD_M5;

void ProcessOpeningCandle()
  {
   MqlRates rates[];
   ArraySetAsSeries(rates,true);
   if(CopyRates(_Symbol,InpOpeningCandleTimeframe,0,3,rates)!=3) return;
   if(!IsNewYorkTime(rates[1].time,InpSignalHourNY,InpSignalMinuteNY)) return;
   int date_key=NewYorkDateKey(rates[1].time);
   ulong ticket=0;
   if(SelectOurPosition(ticket) || AlreadyTradedOnNewYorkDate(date_key) || !InpEnableTrading)
     {
      PrintFormat("NDC_CHECK|%d|%s|SKIP_POSITION_OR_DISABLED",(int)InpOpeningCandleTimeframe,TimeToString(TimeCurrent(),TIME_DATE|TIME_SECONDS));
      return;
     }
   double ema=0.0,previous_ema=0.0,atr=0.0;
   if(!ReadIndicatorValue(g_ema_handle,1,ema) || !ReadIndicatorValue(g_ema_handle,2,previous_ema) ||
      !ReadIndicatorValue(g_atr_handle,1,atr)) return;
   if(!CurrentSpreadPasses(atr)) return;
   int direction=(rates[1].close>ema ? 1 : (rates[1].close<ema ? -1 : 0));
   if(direction==0 || (direction>0 && !InpAllowLong) || (direction<0 && !InpAllowShort)) return;
   bool quality=SignalQualityPasses(direction,rates[1],ema,previous_ema,atr);
   bool di=DIAgrees(direction);
   PrintFormat("NDC_CHECK|%d|%s|%s|%s|%.8f|%.8f|%.8f|%d|%d|%d",(int)InpOpeningCandleTimeframe,
      TimeToString(TimeCurrent(),TIME_DATE|TIME_SECONDS),TimeToString(rates[1].time,TIME_DATE|TIME_SECONDS),
      TimeToString(iTime(_Symbol,InpSignalTimeframe,1),TIME_DATE|TIME_SECONDS),rates[1].close,ema,atr,direction,(int)quality,(int)di);
   if(!quality || !di) return;
   SendEntry(direction,atr,rates[1],SelectedRewardRisk(rates[1],atr));
  }

int OnInit()
  {
   if(!(bool)MQLInfoInteger(MQL_TESTER))
     {
      Print("RESEARCH ONLY: opening-duration comparison refuses live execution.");
      return INIT_FAILED;
     }
   if(InpSignalTimeframe!=PERIOD_M5 ||
      !(InpOpeningCandleTimeframe==PERIOD_M1 || InpOpeningCandleTimeframe==PERIOD_M3 ||
        InpOpeningCandleTimeframe==PERIOD_M5 || InpOpeningCandleTimeframe==PERIOD_M10 ||
        InpOpeningCandleTimeframe==PERIOD_M15)) return INIT_PARAMETERS_INCORRECT;
   int result=N5ProductionOnInit();
   if(result!=INIT_SUCCEEDED) return result;
   g_last_bar_time=iTime(_Symbol,InpOpeningCandleTimeframe,0);
   return INIT_SUCCEEDED;
  }

void OnTick()
  {
   DTS_ManageDynamicTrailing(InpMagic);
   ManagePosition();
   datetime bar_time=iTime(_Symbol,InpOpeningCandleTimeframe,0);
   if(bar_time<=0 || bar_time==g_last_bar_time) return;
   g_last_bar_time=bar_time;
   ProcessOpeningCandle();
  }
